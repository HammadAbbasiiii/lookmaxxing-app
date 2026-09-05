"""Glow — daily variable-reward reveal: weights, streaks, pity, idempotency, gating."""

import datetime as dt

from app.dependencies import create_access_token, get_password_hash
from app.models import GlowState, Photo, User
from app.services import glow_service
from app.services.glow_service import WEIGHTS, blur_for_day, _decide_rarity, _roll_rarity


def _h(token):
    return {"Authorization": f"Bearer {token}"}


def _user(db_session, email, tier="free"):
    u = User(
        email=email,
        hashed_password=get_password_hash("pass1234"),
        full_name="Glow User",
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


def _scored_photo(db_session, user, score=70.0, days_ago=0):
    p = Photo(
        user_id=user.id,
        file_url=f"https://example.com/{user.id}-{score}-{days_ago}.jpg",
        score=score,
        face_shape="Oval",
        captured_at=dt.datetime.utcnow() - dt.timedelta(days=days_ago),
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


class TestBlurFormula:
    def test_day1_is_fully_blurred(self):
        assert blur_for_day(1) == 24

    def test_day90_is_fully_sharp(self):
        assert blur_for_day(90) == 0

    def test_midpoint(self):
        assert blur_for_day(45) == 12

    def test_monotonic_and_clamped(self):
        values = [blur_for_day(d) for d in range(1, 91)]
        assert values == sorted(values, reverse=True)
        assert blur_for_day(0) == 24
        assert blur_for_day(999) == 0


class TestWeights:
    def test_weights_sum_to_100(self):
        for tier, w in WEIGHTS.items():
            assert sum(w.values()) == 100, tier

    def test_pro_elite_richer_than_free(self):
        assert WEIGHTS["pro"]["common"] < WEIGHTS["free"]["common"]
        assert WEIGHTS["elite"]["legendary"] > WEIGHTS["free"]["legendary"]

    def test_roll_returns_valid_rarity(self):
        for _ in range(200):
            assert _roll_rarity("pro") in ("common", "rare", "epic", "legendary")


class TestDecideRarity:
    def _state(self, streak=0, flags=None):
        return GlowState(
            user_id="u1", glow_streak=streak, opens_count=0,
            consecutive_commons=0, milestone_flags=flags or {},
        )

    def test_day90_forces_legendary(self):
        assert _decide_rarity("free", self._state(), 90, {}, 10, 0) == "legendary"

    def test_streak7_forces_rare(self):
        assert _decide_rarity("pro", self._state(streak=7), 10, {}, 5, 0) == "rare"

    def test_streak30_forces_epic(self):
        assert _decide_rarity("pro", self._state(streak=30), 10, {}, 5, 0) == "epic"

    def test_streak7_claimed_does_not_force_again(self, monkeypatch):
        monkeypatch.setattr(glow_service, "_roll_rarity", lambda tier: "common")
        s = self._state(streak=7, flags={"streak7_claimed": True})
        assert _decide_rarity("pro", s, 8, s.milestone_flags, 5, 0) == "common"

    def test_first_open_free_forces_rare(self):
        assert _decide_rarity("free", self._state(), 1, {}, 0, 0) == "rare"

    def test_pity_timer_forces_rare(self):
        s = self._state()
        s.consecutive_commons = 2
        assert _decide_rarity("pro", s, 1, {}, 5, 2) == "rare"

    def test_otherwise_rolls(self, monkeypatch):
        monkeypatch.setattr(glow_service, "_roll_rarity", lambda tier: "common")
        assert _decide_rarity("pro", self._state(), 1, {}, 5, 0) == "common"


class TestGlowAPI:
    def test_state_defaults(self, client, db_session):
        u = _user(db_session, "glowstate@example.com")
        res = client.get("/api/v1/glow/state", headers=_h(_token(u)))
        assert res.status_code == 200
        body = res.json()
        assert body["can_open"] is True
        assert body["opened_today"] is False
        assert body["state"]["glow_streak"] == 0
        assert body["state"]["journey_day"] == 1

    def test_open_is_idempotent(self, client, db_session):
        u = _user(db_session, "glowidem@example.com")
        headers = _h(_token(u))
        first = client.post("/api/v1/glow/open", headers=headers).json()
        second = client.post("/api/v1/glow/open", headers=headers).json()
        assert first["already_opened"] is False
        assert second["already_opened"] is True
        assert second["reveal"]["id"] == first["reveal"]["id"]

    def test_first_open_sets_streak_to_one(self, client, db_session):
        u = _user(db_session, "glowstreak1@example.com")
        res = client.post("/api/v1/glow/open", headers=_h(_token(u))).json()
        assert res["state"]["glow_streak"] == 1
        assert res["state"]["opens_count"] == 1

    def test_streak_rolls_over_next_day(self, client, db_session):
        u = _user(db_session, "glowrollover@example.com")
        _scored_photo(db_session, u)
        st = glow_service._get_state(u, db_session)
        st.last_open_date = dt.date.today() - dt.timedelta(days=1)
        st.glow_streak = 3
        st.opens_count = 3
        db_session.commit()
        res = client.post("/api/v1/glow/open", headers=_h(_token(u))).json()
        assert res["state"]["glow_streak"] == 4

    def test_missed_day_resets_streak(self, client, db_session):
        u = _user(db_session, "glowreset@example.com")
        _scored_photo(db_session, u)
        st = glow_service._get_state(u, db_session)
        st.last_open_date = dt.date.today() - dt.timedelta(days=3)
        st.glow_streak = 9
        st.opens_count = 9
        db_session.commit()
        res = client.post("/api/v1/glow/open", headers=_h(_token(u))).json()
        assert res["state"]["glow_streak"] == 1

    def test_free_first_open_is_rare_glimpse_with_photo(self, client, db_session):
        u = _user(db_session, "glowglimpse@example.com")
        _scored_photo(db_session, u, score=68.0)
        res = client.post("/api/v1/glow/open", headers=_h(_token(u))).json()
        assert res["reveal"]["rarity"] == "rare"
        assert res["reveal"]["reward_type"] == "glimpse"
        assert res["reveal"]["payload"]["photo_url"]

    def test_no_photo_falls_back_to_micro_win(self, client, db_session):
        u = _user(db_session, "glownophoto@example.com")
        res = client.post("/api/v1/glow/open", headers=_h(_token(u))).json()
        assert res["reveal"]["rarity"] == "rare"
        assert res["reveal"]["reward_type"] == "micro_win"

    def test_pity_timer_guarantees_glimpse(self, client, db_session):
        u = _user(db_session, "glowpity@example.com")
        _scored_photo(db_session, u)
        st = glow_service._get_state(u, db_session)
        st.consecutive_commons = 2
        st.opens_count = 5
        st.last_open_date = dt.date.today() - dt.timedelta(days=1)
        db_session.commit()
        res = client.post("/api/v1/glow/open", headers=_h(_token(u))).json()
        assert res["reveal"]["rarity"] == "rare"

    def test_full_reveal_forbidden_for_free(self, client, db_session):
        u = _user(db_session, "glowfullfree@example.com")
        res = client.get("/api/v1/glow/full-reveal", headers=_h(_token(u)))
        assert res.status_code == 403
        assert res.json()["detail"]["code"] == "upgrade_required"

    def test_full_reveal_allowed_for_elite(self, client, db_session):
        u = _user(db_session, "glowfullelite@example.com", tier="elite")
        _scored_photo(db_session, u, score=60.0, days_ago=30)
        _scored_photo(db_session, u, score=78.0, days_ago=0)
        res = client.get("/api/v1/glow/full-reveal", headers=_h(_token(u)))
        assert res.status_code == 200
        fr = res.json()["full_reveal"]
        assert fr is not None
        assert fr["kind"] == "full_reveal"
        assert fr["before_url"] and fr["after_url"]

    def test_reveals_history(self, client, db_session):
        u = _user(db_session, "glowhistory@example.com")
        _scored_photo(db_session, u)
        client.post("/api/v1/glow/open", headers=_h(_token(u)))
        res = client.get("/api/v1/glow/reveals", headers=_h(_token(u)))
        assert res.status_code == 200
        body = res.json()
        assert body["total"] == 1
        assert len(body["reveals"]) == 1

