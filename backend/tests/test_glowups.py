"""Glow-Ups — movie status, consent, anonymized feed, moderation."""

import datetime as dt

from app.dependencies import create_access_token, get_password_hash
from app.models import Photo, Plan, User
from app.services import glowups_service
from app.services.glowups_service import SEED_FEED


def _h(token):
    return {"Authorization": f"Bearer {token}"}


def _user(db_session, email, tier="free", age=25, full_name="Jordan Smith"):
    u = User(
        email=email,
        hashed_password=get_password_hash("pass1234"),
        full_name=full_name,
        age=age,
        is_subscribed=tier != "free",
        subscription_tier=tier,
        current_day=0,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


def _token(user):
    return create_access_token(data={"sub": user.id})


def _photo(db_session, user, score, days_ago=0):
    p = Photo(
        user_id=user.id,
        file_url=f"https://example.com/{user.id}-{score}.jpg",
        score=score,
        face_shape="Oval",
        captured_at=dt.datetime.utcnow() - dt.timedelta(days=days_ago),
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


class TestFeed:
    def test_minor_sees_locked_feed(self, client, db_session):
        u = _user(db_session, "feedminor@example.com", age=16)
        res = client.get("/api/v1/glowups/feed", headers=_h(_token(u)))
        assert res.status_code == 200
        body = res.json()
        assert body["locked"] is True
        assert body["items"] == []

    def test_empty_feed_returns_seeded_examples(self, client, db_session):
        u = _user(db_session, "feedempty@example.com", age=30)
        res = client.get("/api/v1/glowups/feed", headers=_h(_token(u)))
        body = res.json()
        assert body["locked"] is False
        assert [i["id"] for i in body["items"]] == [s["id"] for s in SEED_FEED]

    def test_feed_includes_anonymized_opted_in_user(self, client, db_session):
        owner = _user(db_session, "feedowner@example.com", age=19, full_name="Jordan Alexander")
        _photo(db_session, owner, score=60.0, days_ago=30)
        _photo(db_session, owner, score=71.0, days_ago=0)
        glowups_service.set_consent(owner, db_session, True)

        viewer = _user(db_session, "feedviewer@example.com", age=30)
        res = client.get("/api/v1/glowups/feed", headers=_h(_token(viewer)))
        items = res.json()["items"]
        assert len(items) == 1
        item = items[0]
        assert item["first_name"] == "Jordan"
        assert item["age"] == 19
        assert item["delta"] == 11.0
        assert item["blur"] is True
        assert item["seed"] is False
        assert item["cover_url"]

    def test_own_item_excluded_from_feed(self, client, db_session):
        u = _user(db_session, "feedself@example.com", age=30)
        _photo(db_session, u, score=60.0, days_ago=30)
        _photo(db_session, u, score=70.0, days_ago=0)
        glowups_service.set_consent(u, db_session, True)
        res = client.get("/api/v1/glowups/feed", headers=_h(_token(u)))
        assert res.json()["items"] == SEED_FEED  # own item hidden → seeds shown


class TestConsent:
    def test_minor_cannot_opt_in(self, client, db_session):
        u = _user(db_session, "consentminor@example.com", age=16)
        res = client.post("/api/v1/glowups/consent", json={"share_enabled": True}, headers=_h(_token(u)))
        assert res.json()["share_enabled"] is False
        assert res.json()["error"] == "adults_only"

    def test_adult_opt_in_then_out(self, client, db_session):
        u = _user(db_session, "consentadult@example.com", age=25)
        headers = _h(_token(u))
        on = client.post("/api/v1/glowups/consent", json={"share_enabled": True}, headers=headers).json()
        assert on["share_enabled"] is True
        off = client.post("/api/v1/glowups/consent", json={"share_enabled": False}, headers=headers).json()
        assert off["share_enabled"] is False

    def test_get_consent_reflects_state(self, client, db_session):
        u = _user(db_session, "consentget@example.com", age=25)
        headers = _h(_token(u))
        assert client.get("/api/v1/glowups/consent", headers=headers).json()["share_enabled"] is False
        client.post("/api/v1/glowups/consent", json={"share_enabled": True}, headers=headers)
        assert client.get("/api/v1/glowups/consent", headers=headers).json()["share_enabled"] is True


class TestMovie:
    def test_movie_requires_elite(self, client, db_session):
        u = _user(db_session, "moviefree@example.com", tier="free")
        res = client.get("/api/v1/glowups/movie", headers=_h(_token(u)))
        assert res.status_code == 403

    def test_movie_pending_without_photos(self, client, db_session):
        u = _user(db_session, "moviepending@example.com", tier="elite")
        res = client.get("/api/v1/glowups/movie", headers=_h(_token(u)))
        assert res.status_code == 200
        assert res.json()["status"] == "pending"

    def test_generate_needs_two_photos(self, client, db_session):
        u = _user(db_session, "genone@example.com", tier="elite")
        _photo(db_session, u, score=60.0)
        res = client.post("/api/v1/glowups/movie/generate", headers=_h(_token(u)))
        assert res.json()["error"] == "needs_more_photos"

    def test_generate_then_throttled(self, client, db_session):
        u = _user(db_session, "genthrottle@example.com", tier="elite")
        _photo(db_session, u, score=60.0, days_ago=30)
        _photo(db_session, u, score=70.0, days_ago=0)
        headers = _h(_token(u))
        first = client.post("/api/v1/glowups/movie/generate", headers=headers).json()
        assert first["status"] == "trailer"
        second = client.post("/api/v1/glowups/movie/generate", headers=headers).json()
        assert second["throttled"] is True

    def test_movie_ready_at_day_90(self, client, db_session):
        u = _user(db_session, "movieready@example.com", tier="elite")
        _photo(db_session, u, score=60.0, days_ago=90)
        _photo(db_session, u, score=80.0, days_ago=0)
        plan = Plan(
            user_id=u.id, is_active=True, total_days=90,
            created_at=dt.datetime.utcnow() - dt.timedelta(days=90),
        )
        db_session.add(plan)
        db_session.commit()
        res = client.get("/api/v1/glowups/movie", headers=_h(_token(u)))
        assert res.status_code == 200
        assert res.json()["status"] == "ready"
        assert res.json()["delta"] == 20.0


class TestReport:
    def test_report_hides_item(self, client, db_session):
        owner = _user(db_session, "reportowner@example.com", age=20)
        _photo(db_session, owner, score=60.0, days_ago=30)
        _photo(db_session, owner, score=70.0, days_ago=0)
        glowups_service.set_consent(owner, db_session, True)

        viewer = _user(db_session, "reportviewer@example.com", age=30)
        feed = client.get("/api/v1/glowups/feed", headers=_h(_token(viewer))).json()
        item_id = feed["items"][0]["id"]
        res = client.post(f"/api/v1/glowups/items/{item_id}/report", headers=_h(_token(viewer)))
        assert res.json()["reported"] is True

        again = client.get("/api/v1/glowups/feed", headers=_h(_token(viewer))).json()
        ids = [i["id"] for i in again["items"]]
        assert item_id not in ids

