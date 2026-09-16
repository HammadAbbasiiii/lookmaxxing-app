"""Profile CRUD, onboarding, GDPR deletion, progress endpoints and streak engine."""

import uuid
from datetime import datetime, timedelta

from app.dependencies import create_access_token
from app.models import Photo, Plan, User
from app.services.progress_engine import update_streak
from app.services.upload_service import CLOUDINARY_FOLDER


def _h(token):
    return {"Authorization": f"Bearer {token}"}


def _plan(db_session, user):
    plan = Plan(
        id=str(uuid.uuid4()),
        user_id=user.id,
        data={"phases": {}},
        phases={},
        current_phase="phase_1",
        current_week=1,
        current_day=0,
        is_active=True,
    )
    db_session.add(plan)
    db_session.commit()
    return plan


def _add_photo(db_session, user, url=None):
    """Attach a photo row to `user`, in the URL layout Cloudinary gives us back."""
    photo = Photo(
        id=str(uuid.uuid4()),
        user_id=user.id,
        file_url=url
        or (
            "https://res.cloudinary.com/lookmaxx/image/upload/v1/"
            f"{CLOUDINARY_FOLDER}/user_ab12cd34.jpg"
        ),
    )
    db_session.add(photo)
    db_session.commit()
    return photo


class TestProfile:
    def test_get_profile(self, client, auth_token):
        res = client.get("/api/v1/profile", headers=_h(auth_token))
        assert res.status_code == 200
        assert res.json()["email"] == "test@example.com"

    def test_get_profile_requires_auth(self, client):
        assert client.get("/api/v1/profile").status_code == 401

    def test_update_age(self, client, auth_token):
        res = client.put("/api/v1/profile", json={"age": 25}, headers=_h(auth_token))
        assert res.status_code == 200
        assert res.json()["age"] == 25

    def test_update_invalid_gender(self, client, auth_token):
        res = client.put(
            "/api/v1/profile", json={"gender": "alien"}, headers=_h(auth_token)
        )
        assert res.status_code == 400
        assert "gender must be one of" in res.json()["detail"]

    def test_update_invalid_goal(self, client, auth_token):
        res = client.put(
            "/api/v1/profile", json={"goals": ["fly"]}, headers=_h(auth_token)
        )
        assert res.status_code == 400
        assert "Invalid goal" in res.json()["detail"]

    def test_update_invalid_skin_type(self, client, auth_token):
        res = client.put(
            "/api/v1/profile", json={"skin_type": "glass"}, headers=_h(auth_token)
        )
        assert res.status_code == 400

    def test_update_invalid_commitment(self, client, auth_token):
        res = client.put(
            "/api/v1/profile", json={"commitment": "whenever"}, headers=_h(auth_token)
        )
        assert res.status_code == 400

    def test_update_age_out_of_bounds(self, client, auth_token):
        res = client.put("/api/v1/profile", json={"age": 5}, headers=_h(auth_token))
        assert res.status_code == 422

    def test_update_empty_body(self, client, auth_token):
        res = client.put("/api/v1/profile", json={}, headers=_h(auth_token))
        assert res.status_code == 400
        assert "No fields" in res.json()["detail"]

    def test_onboarding_completes(self, client, auth_token):
        res = client.post(
            "/api/v1/profile/onboarding",
            json={"age": 25, "gender": "male", "goals": ["jawline"]},
            headers=_h(auth_token),
        )
        assert res.status_code == 200
        assert res.json()["onboarding_completed"] is True

    def test_onboarding_invalid_gender(self, client, auth_token):
        res = client.post(
            "/api/v1/profile/onboarding",
            json={"gender": "alien"},
            headers=_h(auth_token),
        )
        assert res.status_code == 400

    def test_delete_account_gdpr(self, client, auth_token):
        res = client.delete("/api/v1/profile/delete", headers=_h(auth_token))
        assert res.status_code == 200
        assert res.json()["success"] is True

        # Token is now orphaned — /me must 401.
        assert client.get("/api/v1/auth/me", headers=_h(auth_token)).status_code == 401

    def test_delete_account_aborts_when_provider_delete_fails(
        self, client, auth_token, test_user, db_session, monkeypatch
    ):
        """GDPR: nothing is erased until the provider confirms the image is gone."""
        import app.routes.profile as profile_routes

        _add_photo(db_session, test_user)

        def _provider_down(public_id):  # noqa: ARG001 — mirrors the real signature
            raise RuntimeError("provider unavailable")

        monkeypatch.setattr(profile_routes, "delete_from_cloudinary", _provider_down)

        res = client.delete("/api/v1/profile/delete", headers=_h(auth_token))

        assert res.status_code == 502
        assert res.json()["detail"]["code"] == "image_deletion_failed"

        # The account must survive the failure: if the rows were already gone,
        # the retry would have no public_id left and the photo would stay live
        # at the provider forever.
        assert client.get("/api/v1/auth/me", headers=_h(auth_token)).status_code == 200

        # A retry that reaches the provider completes the erasure.
        monkeypatch.setattr(
            profile_routes, "delete_from_cloudinary", lambda public_id: {"result": "ok"}
        )
        assert client.delete("/api/v1/profile/delete", headers=_h(auth_token)).status_code == 200
        assert client.get("/api/v1/auth/me", headers=_h(auth_token)).status_code == 401

    def test_delete_account_aborts_on_unrecognized_url(
        self, client, auth_token, test_user, db_session, monkeypatch
    ):
        """A stored URL we can't map to a public_id must not be silently skipped."""
        import app.routes.profile as profile_routes

        called = []
        monkeypatch.setattr(
            profile_routes, "delete_from_cloudinary", lambda public_id: called.append(public_id)
        )
        _add_photo(db_session, test_user, url="https://example.com/selfie.jpg")

        res = client.delete("/api/v1/profile/delete", headers=_h(auth_token))

        assert res.status_code == 502
        assert called == []
        assert client.get("/api/v1/auth/me", headers=_h(auth_token)).status_code == 200

    def test_delete_account_passes_full_public_id(
        self, client, auth_token, test_user, db_session, monkeypatch
    ):
        """Guards the `user_user_…` bug: the provider needs our exact public_id."""
        import app.routes.profile as profile_routes

        seen = []
        monkeypatch.setattr(
            profile_routes, "delete_from_cloudinary", lambda public_id: seen.append(public_id)
        )
        _add_photo(db_session, test_user)

        assert client.delete("/api/v1/profile/delete", headers=_h(auth_token)).status_code == 200
        assert seen == [f"{CLOUDINARY_FOLDER}/user_ab12cd34"]


class TestStreakEngine:
    def test_first_checkin(self):
        u = User()
        u.current_streak = 0
        u.longest_streak = 0
        u.total_checkins = 0
        u.last_checkin_date = None
        r = update_streak(u)
        assert r["streak_updated"] is True
        assert u.current_streak == 1
        assert u.longest_streak == 1
        assert u.total_checkins == 1

    def test_consecutive_day(self):
        u = User()
        u.current_streak = 3
        u.longest_streak = 5
        u.total_checkins = 3
        u.last_checkin_date = datetime.utcnow() - timedelta(days=1)
        update_streak(u)
        assert u.current_streak == 4
        assert u.longest_streak == 5  # longest preserved
        assert u.total_checkins == 4

    def test_gap_resets_streak(self):
        u = User()
        u.current_streak = 7
        u.longest_streak = 7
        u.total_checkins = 7
        u.last_checkin_date = datetime.utcnow() - timedelta(days=3)
        update_streak(u)
        assert u.current_streak == 1
        assert u.longest_streak == 7

    def test_same_day_is_idempotent(self):
        u = User()
        u.current_streak = 4
        u.longest_streak = 4
        u.total_checkins = 4
        u.last_checkin_date = datetime.utcnow()
        r = update_streak(u)
        assert r["streak_updated"] is False
        assert u.current_streak == 4
        assert u.total_checkins == 4

    def test_longest_streak_updates_on_tie_break(self):
        u = User()
        u.current_streak = 5
        u.longest_streak = 5
        u.total_checkins = 5
        u.last_checkin_date = datetime.utcnow() - timedelta(days=1)
        update_streak(u)
        assert u.current_streak == 6
        assert u.longest_streak == 6


class TestProgressEndpoints:
    def test_history_empty(self, client, auth_token):
        res = client.get("/api/v1/progress/history", headers=_h(auth_token))
        assert res.status_code == 200

    def test_checkins_empty(self, client, auth_token):
        res = client.get("/api/v1/progress/checkins", headers=_h(auth_token))
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_streak(self, client, auth_token):
        res = client.get("/api/v1/progress/streak", headers=_h(auth_token))
        assert res.status_code == 200
        assert "current_streak" in res.json()

    def test_milestones(self, client, auth_token):
        res = client.get("/api/v1/progress/milestones", headers=_h(auth_token))
        assert res.status_code == 200
        assert "completed" in res.json() and "upcoming" in res.json()

    def test_photos_empty(self, client, auth_token):
        res = client.get("/api/v1/progress/photos", headers=_h(auth_token))
        assert res.status_code == 200
        assert res.json()["total"] == 0
        assert res.json()["has_baseline"] is False

    def test_photos_lists_photo(self, client, auth_token, db_session, test_user):
        db_session.add(
            Photo(
                user_id=test_user.id,
                file_url="https://example.com/p.jpg",
                is_baseline=True,
                week_number=1,
            )
        )
        db_session.commit()
        res = client.get("/api/v1/progress/photos", headers=_h(auth_token))
        assert res.status_code == 200
        assert res.json()["total"] == 1
        assert res.json()["has_baseline"] is True

    def test_baseline_not_found(self, client, auth_token):
        res = client.get("/api/v1/progress/photos/baseline", headers=_h(auth_token))
        assert res.status_code == 404

    def test_checkin_requires_plan(self, client, auth_token):
        res = client.post(
            "/api/v1/progress/checkin",
            json={"completed_tasks": [], "notes": ""},
            headers=_h(auth_token),
        )
        assert res.status_code == 404

    def test_checkin_success_then_duplicate(self, client, auth_token, db_session, test_user):
        _plan(db_session, test_user)
        res = client.post(
            "/api/v1/progress/checkin",
            json={"completed_tasks": [], "notes": ""},
            headers=_h(auth_token),
        )
        assert res.status_code == 200
        assert res.json()["success"] is True

        dup = client.post(
            "/api/v1/progress/checkin",
            json={"completed_tasks": [], "notes": ""},
            headers=_h(auth_token),
        )
        assert dup.status_code == 409
        assert "already checked in" in dup.json()["detail"]

