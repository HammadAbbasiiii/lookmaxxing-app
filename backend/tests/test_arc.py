"""The Arc — XP curve, levels, quests, badges, gating."""

import datetime as dt

from app.dependencies import create_access_token, get_password_hash
from app.models import ArcState, Photo, User, UserCheckin
from app.services import arc_service
from app.services.arc_service import level_for_xp, xp_to_next_level, title_for


def _h(token):
    return {"Authorization": f"Bearer {token}"}


def _user(db_session, email, tier="pro"):
    u = User(
        email=email,
        hashed_password=get_password_hash("pass1234"),
        full_name="Arc User",
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


def _scored_photo(db_session, user, score=70.0):
    p = Photo(
        user_id=user.id,
        file_url=f"https://example.com/{user.id}-{score}.jpg",
        score=score,
        face_shape="Oval",
        captured_at=dt.datetime.utcnow(),
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


class TestXPLevels:
    def test_level_curve(self):
        assert level_for_xp(0) == 1
        assert level_for_xp(99) == 1
        assert level_for_xp(100) == 2
        assert level_for_xp(400) == 3
        assert level_for_xp(9999) == 10

    def test_xp_to_next(self):
        assert xp_to_next_level(0) == 100
        assert xp_to_next_level(100) == 300   # level 2 → next threshold 400
        assert xp_to_next_level(399) == 1

    def test_title(self):
        assert title_for(None, 1) == "The Rookie, Level 1"
        assert title_for("Sculptor", 14) == "The Sculptor, Level 14"


class TestArcStateAPI:
    def test_free_sees_locked_quests(self, client, db_session):
        u = _user(db_session, "arcfree@example.com", tier="free")
        res = client.get("/api/v1/arc/state", headers=_h(_token(u)))
        assert res.status_code == 200
        body = res.json()
        assert body["premium"] is False
        assert len(body["today_quests"]) == 3
        assert all(q["locked"] is True for q in body["today_quests"])

    def test_pro_sees_unlocked_quests(self, client, db_session):
        u = _user(db_session, "arcpro@example.com", tier="pro")
        _scored_photo(db_session, u)
        res = client.get("/api/v1/arc/state", headers=_h(_token(u)))
        body = res.json()
        assert body["premium"] is True
        assert len(body["today_quests"]) == 3
        assert all(q["locked"] is False for q in body["today_quests"])

    def test_free_claim_forbidden(self, client, db_session):
        u = _user(db_session, "arcfreeclaim@example.com", tier="free")
        res = client.post("/api/v1/arc/quests/whatever/claim", headers=_h(_token(u)))
        assert res.status_code == 403
        assert res.json()["detail"]["code"] == "upgrade_required"

    def test_claim_without_checkin_rejected(self, client, db_session):
        u = _user(db_session, "arcnocheck@example.com", tier="pro")
        _scored_photo(db_session, u)
        state = client.get("/api/v1/arc/state", headers=_h(_token(u))).json()
        qid = state["today_quests"][0]["id"]
        res = client.post(f"/api/v1/arc/quests/{qid}/claim", headers=_h(_token(u)))
        assert res.status_code == 409
        assert res.json()["detail"]["code"] == "not_done"

    def test_claim_requires_matching_task(self, client, db_session):
        u = _user(db_session, "arcwrongtask@example.com", tier="pro")
        _scored_photo(db_session, u)
        state = client.get("/api/v1/arc/state", headers=_h(_token(u))).json()
        qid = state["today_quests"][0]["id"]
        checkin = UserCheckin(
            user_id=u.id, week_number=1, completed_tasks=["some unrelated task"],
        )
        db_session.add(checkin)
        db_session.commit()
        res = client.post(f"/api/v1/arc/quests/{qid}/claim", headers=_h(_token(u)))
        assert res.status_code == 409

    def test_claim_success_awards_xp_and_levels(self, client, db_session):
        u = _user(db_session, "arcclaim@example.com", tier="pro")
        _scored_photo(db_session, u)
        state = client.get("/api/v1/arc/state", headers=_h(_token(u))).json()
        q = state["today_quests"][0]
        checkin = UserCheckin(
            user_id=u.id, week_number=1, completed_tasks=[q["task"]],
        )
        db_session.add(checkin)
        db_session.commit()
        res = client.post(f"/api/v1/arc/quests/{q['id']}/claim", headers=_h(_token(u)))
        assert res.status_code == 200
        body = res.json()
        assert body["xp_awarded"] == 100
        assert body["level"] == 2
        assert body["leveled_up"] is True
        assert body["new_title"]

    def test_double_claim_rejected(self, client, db_session):
        u = _user(db_session, "arcdouble@example.com", tier="pro")
        _scored_photo(db_session, u)
        state = client.get("/api/v1/arc/state", headers=_h(_token(u))).json()
        q = state["today_quests"][0]
        checkin = UserCheckin(
            user_id=u.id, week_number=1, completed_tasks=[q["task"]],
        )
        db_session.add(checkin)
        db_session.commit()
        headers = _h(_token(u))
        assert client.post(f"/api/v1/arc/quests/{q['id']}/claim", headers=headers).status_code == 200
        res = client.post(f"/api/v1/arc/quests/{q['id']}/claim", headers=headers)
        assert res.status_code == 409
        assert res.json()["detail"]["code"] == "already_claimed"

    def test_badge_idempotency(self, client, db_session):
        u = _user(db_session, "arcbadge@example.com", tier="pro")
        _scored_photo(db_session, u)
        headers = _h(_token(u))
        first = client.get("/api/v1/arc/state", headers=headers).json()
        second = client.get("/api/v1/arc/state", headers=headers).json()
        assert len(first["badges"]) == 1  # first_score
        assert len(second["badges"]) == 1
        assert first["badges"][0]["badge_key"] == "first_score"

    def test_quests_regenerate_on_new_utc_day(self, client, db_session):
        u = _user(db_session, "arcregen@example.com", tier="pro")
        _scored_photo(db_session, u)
        headers = _h(_token(u))
        first = client.get("/api/v1/arc/state", headers=headers).json()
        st = arc_service._get_state(u, db_session)
        st.quest_date = dt.date.today() - dt.timedelta(days=1)
        st.quests = []
        db_session.commit()
        second = client.get("/api/v1/arc/state", headers=headers).json()
        assert len(second["today_quests"]) == 3
        first_ids = {q["id"] for q in first["today_quests"]}
        second_ids = {q["id"] for q in second["today_quests"]}
        assert not first_ids.intersection(second_ids)

