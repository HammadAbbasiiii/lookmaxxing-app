"""Plan, dashboard, product browse, explore, health, upload signature, analysis."""

import uuid

from app.dependencies import create_access_token, get_password_hash
from app.models import Photo, Plan, User


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


class TestPlan:
    def test_plan_without_plan(self, client, auth_token):
        res = client.get("/api/v1/plan", headers=_h(auth_token))
        assert res.status_code == 200
        assert res.json()["has_plan"] is False

    def test_plan_with_active_plan(self, client, auth_token, db_session, test_user):
        _plan(db_session, test_user)
        res = client.get("/api/v1/plan", headers=_h(auth_token))
        assert res.status_code == 200
        assert res.json()["has_plan"] is True

    def test_plan_requires_auth(self, client):
        assert client.get("/api/v1/plan").status_code == 401

    def test_plan_progress(self, client, auth_token):
        res = client.get("/api/v1/plan/progress", headers=_h(auth_token))
        assert res.status_code == 200


class TestDashboard:
    def test_dashboard_shape(self, client, auth_token):
        res = client.get("/api/v1/dashboard", headers=_h(auth_token))
        assert res.status_code == 200
        body = res.json()
        assert "profile" in body
        assert "next_action" in body

    def test_dashboard_requires_auth(self, client):
        assert client.get("/api/v1/dashboard").status_code == 401


class TestProductsBrowse:
    def test_categories(self, client, auth_token):
        res = client.get("/api/v1/products/categories", headers=_h(auth_token))
        assert res.status_code == 200
        assert res.json()["success"] is True

    def test_category_products(self, client, auth_token):
        res = client.get("/api/v1/products/category/skin_quality", headers=_h(auth_token))
        assert res.status_code == 200
        assert res.json()["success"] is True

    def test_category_invalid(self, client, auth_token):
        res = client.get("/api/v1/products/category/bogus", headers=_h(auth_token))
        assert res.status_code == 400

    def test_category_invalid_tier(self, client, auth_token):
        res = client.get(
            "/api/v1/products/category/skin_quality",
            params={"tier": "platinum"},
            headers=_h(auth_token),
        )
        assert res.status_code == 400

    def test_recommendations_without_analysis(self, client, auth_token):
        res = client.get("/api/v1/products/recommendations", headers=_h(auth_token))
        assert res.status_code == 200
        assert res.json()["success"] is True
        assert res.json()["total"] == 0

    def test_products_require_auth(self, client):
        assert client.get("/api/v1/products/categories").status_code == 401


class TestExplore:
    def test_explore_shape(self, client, auth_token):
        res = client.get("/api/v1/explore", headers=_h(auth_token))
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert isinstance(body["transformations"], list)
        assert len(body["articles"]) == 6

    def test_explore_requires_auth(self, client):
        assert client.get("/api/v1/explore").status_code == 401


class TestAnalysis:
    def test_analysis_owner_scored(self, client, auth_token, db_session, test_user):
        p = Photo(
            user_id=test_user.id,
            file_url="https://example.com/a.jpg",
            score=72.0,
            symmetry_score=70.0,
            skin_score=68.0,
            jawline_score=75.0,
            eye_score=74.0,
            face_shape="oval",
        )
        db_session.add(p)
        db_session.commit()
        db_session.refresh(p)
        res = client.get(f"/api/v1/analysis/{p.id}", headers=_h(auth_token))
        assert res.status_code == 200
        assert res.json()["photo_id"] == p.id
        assert res.json()["scores"]["overall"] == 72.0

    def test_analysis_unscored(self, client, auth_token, db_session, test_user):
        p = Photo(user_id=test_user.id, file_url="https://example.com/b.jpg")
        db_session.add(p)
        db_session.commit()
        db_session.refresh(p)
        res = client.get(f"/api/v1/analysis/{p.id}", headers=_h(auth_token))
        assert res.status_code == 404

    def test_analysis_nonexistent(self, client, auth_token):
        res = client.get("/api/v1/analysis/does-not-exist", headers=_h(auth_token))
        assert res.status_code == 404

    def test_analysis_requires_auth(self, client):
        assert client.get("/api/v1/analysis/x").status_code == 401


class TestHealth:
    def test_health(self, client):
        res = client.get("/api/v1/health")
        assert res.status_code == 200
        assert res.json()["status"] == "healthy"

    def test_root(self, client):
        res = client.get("/api/v1/")
        assert res.status_code == 200
        assert "message" in res.json()


class TestUploadSignature:
    def test_requires_auth(self, client):
        assert client.get("/api/v1/upload/signature").status_code == 401

    def test_returns_signature(self, client, auth_token):
        res = client.get("/api/v1/upload/signature", headers=_h(auth_token))
        assert res.status_code == 200
        body = res.json()
        assert "signature" in body
        assert "public_id" in body


