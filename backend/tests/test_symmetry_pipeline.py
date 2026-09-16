"""Symmetry pipeline (DEF-014): synthetic landmarks must never look measured.

The production bug: `POST /photos/analyze/{id}` scored the old *mock ellipse*
landmarks whenever MediaPipe couldn't load. The ellipse's "mirror" pairs are not
actually mirrored, so every pair measured ~0.4 of the image width and
`100 - dist * 250` clamped to exactly 0 — while jawline (42.9) and eyes (37.4)
landed in plausible-looking ranges, so the row looked measured. Users saw
"Symmetry 0" on a real face.

Three defences are pinned here:
  1. a degraded detection result is never classified as a measurement,
  2. `calculate_symmetry` returns None ("not measured") instead of 0/70,
  3. the API never persists or returns a 0 score.
"""

import math

import cv2
import numpy as np

from app.dependencies import create_access_token, get_password_hash
from app.models import Photo, Plan, User
from app.services.face_service import (
    MAX_MIRROR_DISTANCE,
    calculate_symmetry,
    detect_face_landmarks,
    landmark_measurement,
    mediapipe_status,
    unavailable_reason,
)

# MediaPipe's symmetric pairs used by calculate_symmetry.
SYMMETRY_PAIRS = [(33, 263), (133, 362), (54, 284), (61, 291), (152, 377), (21, 251)]


def _old_mock_ellipse() -> list:
    """The exact landmark generator that shipped the 0 (pre-DEF-014)."""
    landmarks = []
    for i in range(468):
        angle = (i / 468.0) * 2 * math.pi
        x = 0.5 + 0.3 * math.cos(angle) * (1.0 - abs(i - 234) / 468.0)
        y = 0.5 + 0.4 * math.sin(angle)
        landmarks.append({"x": float(x), "y": float(y), "z": math.cos(angle) * 0.01, "index": i})
    return landmarks


def _legacy_score(landmarks: list) -> float:
    """The pre-fix formula, to prove the mock ellipse really did score 0."""
    distances = []
    for l_idx, r_idx in SYMMETRY_PAIRS:
        left, right = landmarks[l_idx], landmarks[r_idx]
        dx = left["x"] - (1.0 - right["x"])
        dy = left["y"] - right["y"]
        distances.append(math.sqrt(dx**2 + dy**2))
    avg = sum(distances) / len(distances)
    return max(0, min(100, 100 - avg * 250))


def _realistic_face() -> list:
    """468 landmarks whose mirror pairs genuinely are mirrored (score ≈ 100)."""
    landmarks = [{"x": 0.5, "y": 0.5, "z": 0.0} for _ in range(468)]
    for l_idx, r_idx in SYMMETRY_PAIRS:
        landmarks[l_idx] = {"x": 0.42, "y": 0.45, "z": 0.0}
        landmarks[r_idx] = {"x": 0.58, "y": 0.45, "z": 0.0}
    return landmarks


def _jpeg_bytes() -> bytes:
    img = np.zeros((64, 64, 3), dtype=np.uint8)
    img[:, :] = (180, 150, 120)  # skin-ish tone for the skin estimator
    ok, buf = cv2.imencode(".jpg", img)
    assert ok
    return buf.tobytes()


class _FakeResponse:
    def __init__(self, content: bytes):
        self.content = content

    def raise_for_status(self):
        return None


def _make_user(db, email: str, tier: str = "pro") -> User:
    user = User(
        email=email,
        hashed_password=get_password_hash("pass1234"),
        full_name="Symmetry Tester",
        is_subscribed=tier != "free",
        subscription_tier=tier,
        current_day=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_photo(db, user: User, tag: str = "face") -> Photo:
    photo = Photo(
        id=f"photo-{user.email.split('@')[0]}-{tag}",
        user_id=user.id,
        file_url=f"https://example.com/{tag}.jpg",
        analysis_status="processing",
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return photo


class TestSyntheticLandmarksAreNotMeasurements:
    def test_unavailable_detection_is_not_a_measurement(self, monkeypatch):
        """With no MediaPipe on this host, detection must fail closed."""
        import app.services.face_service as fs

        monkeypatch.setattr(fs, "MEDIAPIPE_AVAILABLE", False)
        monkeypatch.setattr(fs, "_options", None)

        result = detect_face_landmarks(_jpeg_bytes())

        assert result["success"] is False
        assert result["mock"] is True
        assert result["landmarks"] == []
        assert landmark_measurement(result) == "unavailable"
        assert unavailable_reason(result)

    def test_mock_result_is_never_classified_as_measured(self):
        assert (
            landmark_measurement(
                {"success": True, "mock": True, "landmarks": [{"x": 0.0, "y": 0.0}] * 468}
            )
            == "unavailable"
        )
        assert landmark_measurement({"success": False, "landmarks": []}) == "unavailable"
        # A successful detection with too few landmarks is also unusable.
        assert (
            landmark_measurement({"success": True, "landmarks": [{"x": 0.5, "y": 0.5}] * 50})
            == "unavailable"
        )
        assert (
            landmark_measurement({"success": True, "landmarks": _realistic_face()}) == "measured"
        )


class TestCalculateSymmetryNeverReturnsZero:
    def test_the_old_mock_ellipse_used_to_score_zero(self):
        """Documented regression: the fabricated geometry scored exactly 0."""
        ellipse = _old_mock_ellipse()
        assert _legacy_score(ellipse) == 0
        # ...and is now reported as not measured instead.
        assert calculate_symmetry(ellipse) is None

    def test_missing_landmarks_return_none_not_a_default(self):
        assert calculate_symmetry([]) is None
        assert calculate_symmetry(None) is None
        assert calculate_symmetry([{"x": 0.5, "y": 0.5}]) is None

    def test_unusable_geometry_returns_none(self):
        # Both "sides" at the same coordinates → mirror distance 0.8, far above
        # the plausibility gate. Must be None, never a clamped 0.
        degen = [{"x": 0.1, "y": 0.5} for _ in range(468)]
        assert calculate_symmetry(degen) is None
        assert MAX_MIRROR_DISTANCE < 0.8

    def test_realistic_face_scores_above_zero(self):
        score = calculate_symmetry(_realistic_face())
        assert score is not None
        assert 70 <= score <= 100

    def test_mediapipe_status_is_reported(self):
        status = mediapipe_status()
        assert set(status) == {"available", "model_path", "model_path_exists", "reason"}
        if not status["available"]:
            assert status["reason"], "an unavailable pipeline must say why"


class TestAnalyzeEndpointFailsClosed:
    def test_synthetic_landmarks_are_refused_and_nothing_is_persisted(
        self, client, db_session, monkeypatch
    ):
        user = _make_user(db_session, "sym-mock@example.com", tier="pro")
        photo = _make_photo(db_session, user, tag="mock")
        token = create_access_token(data={"sub": user.id})

        import app.routes.photos as photos_route

        monkeypatch.setattr(
            photos_route,
            "detect_face_landmarks",
            lambda _bytes: {
                "success": False,
                "landmarks": [],
                "mock": True,
                "reason": "mediapipe_unavailable",
                "error": "Not enough free memory on this worker",
            },
        )
        monkeypatch.setattr("requests.get", lambda *a, **k: _FakeResponse(_jpeg_bytes()))

        res = client.post(
            f"/api/v1/photos/analyze/{photo.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert res.status_code == 422, res.text
        assert "measure" in res.json()["detail"].lower()

        db_session.expire_all()
        stored = db_session.query(Photo).filter(Photo.id == photo.id).first()
        assert stored.symmetry_score is None
        assert stored.skin_score is None
        assert stored.jawline_score is None
        assert stored.score is None
        assert stored.analysis_status == "failed"
        assert stored.analysis_details["landmark_measurement"] == "unavailable"
        # No plan may be generated from a measurement that never happened.
        assert db_session.query(Plan).filter(Plan.photo_id == photo.id).count() == 0

    def test_real_landmarks_are_scored_and_marked_measured(
        self, client, db_session, monkeypatch
    ):
        user = _make_user(db_session, "sym-real@example.com", tier="pro")
        photo = _make_photo(db_session, user, tag="real")
        token = create_access_token(data={"sub": user.id})

        import app.routes.photos as photos_route

        monkeypatch.setattr(
            photos_route,
            "detect_face_landmarks",
            lambda _bytes: {"success": True, "landmarks": _realistic_face(), "face_count": 1},
        )
        monkeypatch.setattr("requests.get", lambda *a, **k: _FakeResponse(_jpeg_bytes()))

        res = client.post(
            f"/api/v1/photos/analyze/{photo.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert res.status_code == 200, res.text
        db_session.expire_all()
        stored = db_session.query(Photo).filter(Photo.id == photo.id).first()
        assert stored.symmetry_score is not None
        assert stored.symmetry_score > 0
        assert stored.analysis_details["landmark_measurement"] == "measured"


class TestAnalysisApiNeverReturnsZero:
    def test_stored_zero_reads_as_not_measured(self, client, db_session):
        user = _make_user(db_session, "sym-zero@example.com", tier="pro")
        photo = _make_photo(db_session, user, tag="zero")
        photo.score = 71.0
        photo.symmetry_score = 0.0
        photo.skin_score = 67.0
        photo.jawline_score = 43.0
        photo.eye_score = 37.0
        db_session.commit()
        token = create_access_token(data={"sub": user.id})

        res = client.get(
            f"/api/v1/analysis/{photo.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert res.status_code == 200, res.text
        body = res.json()
        # The whole point: 0 is never served as a measurement.
        assert body["scores"]["symmetry"] is None
        assert body["scores"]["skin"] == 67.0
        assert body["measurement"]["not_measured"] == ["symmetry"]

    def test_estimates_are_not_borrowed_when_landmarks_were_unavailable(
        self, client, db_session
    ):
        """A heuristic breakdown is an estimate — it must not fill a score row."""
        user = _make_user(db_session, "sym-est@example.com", tier="pro")
        photo = _make_photo(db_session, user, tag="estimate")
        photo.score = 60.0
        photo.analysis_details = {
            "landmark_measurement": "unavailable",
            "category_breakdown": {"facial_harmony": {"score": 72.0, "description": "Estimate"}},
        }
        db_session.commit()
        token = create_access_token(data={"sub": user.id})

        body = client.get(
            f"/api/v1/analysis/{photo.id}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()

        assert body["scores"]["symmetry"] is None
        assert body["measurement"]["landmarks"] == "unavailable"

    def test_measured_row_serves_its_score(self, client, db_session):
        user = _make_user(db_session, "sym-ok@example.com", tier="pro")
        photo = _make_photo(db_session, user, tag="measured")
        photo.score = 78.0
        photo.symmetry_score = 88.0
        photo.analysis_details = {"landmark_measurement": "measured"}
        db_session.commit()
        token = create_access_token(data={"sub": user.id})

        body = client.get(
            f"/api/v1/analysis/{photo.id}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()

        assert body["scores"]["symmetry"] == 88.0
        assert body["measurement"]["measured"] is True


class TestHealthReportsMediapipe:
    def test_health_exposes_mediapipe_state(self, client):
        body = client.get("/api/v1/health").json()
        assert "mediapipe" in body
        mp = body["mediapipe"]
        assert mp is not None
        assert set(mp) == {"available", "model_path", "model_path_exists", "reason"}


class TestBackgroundAnalysisIsHonest:
    """The upload path (`run_analysis_in_background`) must fail closed too.

    It already ignored synthetic landmarks, but it used to finish with
    `analysis_status="completed"` and `score=NULL` plus a plan generated from a
    fabricated 50 — which the client renders as an empty report with no reason.
    """

    def _bind_background_session(self, monkeypatch, db_session):
        from sqlalchemy.orm import sessionmaker

        import app.services.background_analysis as bg

        monkeypatch.setattr(
            bg,
            "SessionLocal",
            sessionmaker(bind=db_session.get_bind(), autocommit=False, autoflush=False),
        )
        # The synthetic image isn't a real photo, so bypass quality validation:
        # this test is about what happens *after* validation passes.
        monkeypatch.setattr(bg, "validate_image", lambda _b: {"valid": True, "error": None})
        return bg

    def test_unmeasurable_upload_fails_with_a_reason_and_no_plan(
        self, db_session, monkeypatch
    ):
        bg = self._bind_background_session(monkeypatch, db_session)
        user = _make_user(db_session, "bg-mock@example.com", tier="pro")
        photo = _make_photo(db_session, user, tag="bgmock")

        monkeypatch.setattr(
            bg,
            "detect_face_landmarks",
            lambda _b: {
                "success": False,
                "landmarks": [],
                "mock": True,
                "reason": "mediapipe_unavailable",
                "error": "MediaPipe face-landmark model unavailable",
            },
        )
        monkeypatch.setattr(
            bg.prediction_service,
            "predict",
            lambda *a, **k: {"score_100": None, "raw_score": None, "model_used": False},
        )

        bg.run_analysis_background(photo.id, user.id, _jpeg_bytes(), gender="male")

        db_session.expire_all()
        stored = db_session.query(Photo).filter(Photo.id == photo.id).first()
        assert stored.analysis_status == "failed"
        assert stored.score is None
        assert stored.symmetry_score is None
        assert stored.analysis_details["landmark_measurement"] == "unavailable"
        assert "couldn't measure" in stored.analysis_details["validation_error"]
        assert db_session.query(Plan).filter(Plan.photo_id == photo.id).count() == 0

    def test_measured_upload_completes_with_real_scores(self, db_session, monkeypatch):
        bg = self._bind_background_session(monkeypatch, db_session)
        user = _make_user(db_session, "bg-real@example.com", tier="pro")
        photo = _make_photo(db_session, user, tag="bgreal")

        monkeypatch.setattr(
            bg,
            "detect_face_landmarks",
            lambda _b: {"success": True, "landmarks": _realistic_face(), "face_count": 1},
        )
        monkeypatch.setattr(
            bg.prediction_service,
            "predict",
            lambda *a, **k: {"score_100": 72.0, "raw_score": 0.5, "model_used": True},
        )

        bg.run_analysis_background(photo.id, user.id, _jpeg_bytes(), gender="male")

        db_session.expire_all()
        stored = db_session.query(Photo).filter(Photo.id == photo.id).first()
        assert stored.analysis_status == "completed"
        assert stored.score == 72.0
        assert stored.symmetry_score is not None and stored.symmetry_score > 0
        assert stored.analysis_details["landmark_measurement"] == "measured"
        assert db_session.query(Plan).filter(Plan.photo_id == photo.id).count() == 1