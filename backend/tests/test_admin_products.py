"""Admin product catalogue CRUD + audit log + analytics admin gating."""

import pytest

from app.dependencies import create_access_token, get_password_hash
from app.models import AdminAction, Product, User


def _admin(db_session):
    u = User(
        email="prodadmin@example.com",
        hashed_password=get_password_hash("pass1234"),
        full_name="Prod Admin",
        is_subscribed=False,
        subscription_tier="free",
        is_admin=True,
        current_day=0,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


def _tok(user):
    return {"Authorization": f"Bearer {create_access_token(data={'sub': user.id})}"}


def _raw(token):
    return {"Authorization": f"Bearer {token}"}


class TestAdminProductGating:
    def test_list_requires_admin(self, client, auth_token):
        assert client.get("/api/v1/admin/products", headers=_raw(auth_token)).status_code == 403

    def test_create_requires_admin(self, client, auth_token):
        res = client.post(
            "/api/v1/admin/products",
            json={"name": "X", "category": "skin_quality"},
            headers=_raw(auth_token),
        )
        assert res.status_code == 403

    def test_update_requires_admin(self, client, auth_token, db_session):
        admin = _admin(db_session)
        p = Product(name="Y", category="skin_quality", price=1.0)
        db_session.add(p)
        db_session.commit()
        db_session.refresh(p)
        res = client.put(
            f"/api/v1/admin/products/{p.id}", json={"price": 2.0}, headers=_raw(auth_token)
        )
        assert res.status_code == 403

    def test_delete_requires_admin(self, client, auth_token, db_session):
        admin = _admin(db_session)
        p = Product(name="Z", category="skin_quality", price=1.0)
        db_session.add(p)
        db_session.commit()
        db_session.refresh(p)
        res = client.delete(f"/api/v1/admin/products/{p.id}", headers=_raw(auth_token))
        assert res.status_code == 403

    def test_activity_requires_admin(self, client, auth_token):
        assert client.get("/api/v1/admin/activity", headers=_raw(auth_token)).status_code == 403


class TestAdminProductCrud:
    def test_create_product(self, client, db_session):
        admin = _admin(db_session)
        res = client.post(
            "/api/v1/admin/products",
            json={
                "name": "Test Serum",
                "brand": "BrandX",
                "category": "skin_quality",
                "price": 19.99,
                "tier": "mid_range",
                "rating": 4.5,
                "review_count": 10,
            },
            headers=_tok(admin),
        )
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert body["product"]["name"] == "Test Serum"
        assert body["product"]["is_active"] is True
        assert body["product"]["id"]

    def test_create_product_invalid_category(self, client, db_session):
        admin = _admin(db_session)
        res = client.post(
            "/api/v1/admin/products",
            json={"name": "X", "category": "bogus"},
            headers=_tok(admin),
        )
        assert res.status_code == 400
        assert "Invalid category" in res.json()["detail"]

    def test_create_product_invalid_tier(self, client, db_session):
        admin = _admin(db_session)
        res = client.post(
            "/api/v1/admin/products",
            json={"name": "X", "category": "skin_quality", "tier": "platinum"},
            headers=_tok(admin),
        )
        assert res.status_code == 400
        assert "Invalid tier" in res.json()["detail"]

    def test_create_product_negative_price(self, client, db_session):
        admin = _admin(db_session)
        res = client.post(
            "/api/v1/admin/products",
            json={"name": "X", "category": "skin_quality", "price": -5.0},
            headers=_tok(admin),
        )
        assert res.status_code == 422

    def test_create_product_rating_out_of_range(self, client, db_session):
        admin = _admin(db_session)
        res = client.post(
            "/api/v1/admin/products",
            json={"name": "X", "category": "skin_quality", "rating": 9.9},
            headers=_tok(admin),
        )
        assert res.status_code == 422

    def test_create_product_missing_name(self, client, db_session):
        admin = _admin(db_session)
        res = client.post(
            "/api/v1/admin/products",
            json={"category": "skin_quality"},
            headers=_tok(admin),
        )
        assert res.status_code == 422

    def test_list_and_search(self, client, db_session):
        admin = _admin(db_session)
        client.post(
            "/api/v1/admin/products",
            json={"name": "UniqueZzz", "category": "jawline_definition", "price": 9.99},
            headers=_tok(admin),
        )
        res = client.get("/api/v1/admin/products", headers=_tok(admin))
        assert res.status_code == 200
        assert res.json()["success"] is True

        res2 = client.get(
            "/api/v1/admin/products", params={"search": "UniqueZzz"}, headers=_tok(admin)
        )
        assert res2.status_code == 200
        names = [p["name"] for p in res2.json()["products"]]
        assert "UniqueZzz" in names

    def test_list_filter_by_category(self, client, db_session):
        admin = _admin(db_session)
        client.post(
            "/api/v1/admin/products",
            json={"name": "CatFiltered", "category": "eye_appeal", "price": 9.99},
            headers=_tok(admin),
        )
        res = client.get(
            "/api/v1/admin/products", params={"category": "eye_appeal"}, headers=_tok(admin)
        )
        assert res.status_code == 200
        assert all(p["category"] == "eye_appeal" for p in res.json()["products"])


    def test_update_product(self, client, db_session):
        admin = _admin(db_session)
        created = client.post(
            "/api/v1/admin/products",
            json={"name": "ToUpdate", "category": "skin_quality", "price": 10.0},
            headers=_tok(admin),
        ).json()["product"]

        res = client.put(
            f"/api/v1/admin/products/{created['id']}",
            json={"price": 25.0, "name": "Updated Name"},
            headers=_tok(admin),
        )
        assert res.status_code == 200
        assert res.json()["product"]["price"] == 25.0
        assert res.json()["product"]["name"] == "Updated Name"

    def test_update_nonexistent(self, client, db_session):
        admin = _admin(db_session)
        res = client.put(
            "/api/v1/admin/products/does-not-exist",
            json={"price": 1.0},
            headers=_tok(admin),
        )
        assert res.status_code == 404

    def test_update_empty_body(self, client, db_session):
        admin = _admin(db_session)
        created = client.post(
            "/api/v1/admin/products",
            json={"name": "NoChange", "category": "skin_quality", "price": 10.0},
            headers=_tok(admin),
        ).json()["product"]
        res = client.put(
            f"/api/v1/admin/products/{created['id']}", json={}, headers=_tok(admin)
        )
        assert res.status_code == 400
        assert "No fields" in res.json()["detail"]

    def test_delete_soft_archives(self, client, db_session):
        admin = _admin(db_session)
        created = client.post(
            "/api/v1/admin/products",
            json={"name": "ToDelete", "category": "skin_quality", "price": 10.0},
            headers=_tok(admin),
        ).json()["product"]
        assert created["is_active"] is True

        res = client.delete(
            f"/api/v1/admin/products/{created['id']}", headers=_tok(admin)
        )
        assert res.status_code == 200
        assert res.json()["product"]["is_active"] is False

        row = db_session.query(Product).filter(Product.id == created["id"]).first()
        assert row.is_active is False

    def test_activate(self, client, db_session):
        admin = _admin(db_session)
        created = client.post(
            "/api/v1/admin/products",
            json={"name": "ToActivate", "category": "skin_quality", "price": 10.0},
            headers=_tok(admin),
        ).json()["product"]
        client.delete(f"/api/v1/admin/products/{created['id']}", headers=_tok(admin))

        res = client.post(
            f"/api/v1/admin/products/{created['id']}/activate", headers=_tok(admin)
        )
        assert res.status_code == 200
        assert res.json()["product"]["is_active"] is True

    def test_delete_nonexistent(self, client, db_session):
        admin = _admin(db_session)
        res = client.delete("/api/v1/admin/products/nope", headers=_tok(admin))
        assert res.status_code == 404

    def test_mutations_are_audited(self, client, db_session):
        admin = _admin(db_session)
        created = client.post(
            "/api/v1/admin/products",
            json={"name": "Audited", "category": "skin_quality", "price": 10.0},
            headers=_tok(admin),
        ).json()["product"]
        client.put(
            f"/api/v1/admin/products/{created['id']}",
            json={"price": 11.0},
            headers=_tok(admin),
        )
        client.delete(f"/api/v1/admin/products/{created['id']}", headers=_tok(admin))

        res = client.get("/api/v1/admin/activity", headers=_tok(admin))
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        actions = [a["action"] for a in body["actions"]]
        assert "create" in actions
        assert "update" in actions
        assert "delete" in actions


class TestAdminAnalytics:
    def test_track_anonymous(self, client):
        res = client.post(
            "/api/v1/track",
            json={"events": [{"event_name": "page_view", "page": "/"}]},
        )
        assert res.status_code == 200
        assert res.json()["logged"] == 1

    def test_track_authenticated(self, client, auth_token):
        res = client.post(
            "/api/v1/track",
            json={"events": [{"event_name": "cta_click", "page": "/upgrade"}]},
            headers=_raw(auth_token),
        )
        assert res.status_code == 200
        assert res.json()["logged"] == 1

    def test_track_empty_events(self, client):
        res = client.post("/api/v1/track", json={"events": []})
        assert res.status_code == 200
        assert res.json()["logged"] == 0

    def test_overview_requires_admin(self, client, auth_token):
        assert (
            client.get("/api/v1/admin/overview", headers=_raw(auth_token)).status_code
            == 403
        )

    def test_overview_shape(self, client, db_session):
        admin = _admin(db_session)
        res = client.get("/api/v1/admin/overview", headers=_tok(admin))
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        for key in ("users", "engagement", "monetization", "traffic"):
            assert key in body

    def test_events_requires_admin(self, client, auth_token):
        assert (
            client.get("/api/v1/admin/events", headers=_raw(auth_token)).status_code
            == 403
        )

    def test_events_shape(self, client, db_session):
        admin = _admin(db_session)
        res = client.get("/api/v1/admin/events", headers=_tok(admin))
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert "events" in body

    def test_events_invalid_start_date(self, client, db_session):
        admin = _admin(db_session)
        res = client.get(
            "/api/v1/admin/events", params={"start": "not-a-date"}, headers=_tok(admin)
        )
        assert res.status_code == 400

    def test_funnel_and_retention_require_admin(self, client, auth_token):
        assert (
            client.get("/api/v1/admin/funnel", headers=_raw(auth_token)).status_code
            == 403
        )
        assert (
            client.get("/api/v1/admin/retention", headers=_raw(auth_token)).status_code
            == 403
        )

    def test_funnel_shape(self, client, db_session):
        admin = _admin(db_session)
        res = client.get("/api/v1/admin/funnel", headers=_tok(admin))
        assert res.status_code == 200
        assert res.json()["success"] is True

    def test_events_summary_shape(self, client, db_session):
        admin = _admin(db_session)
        res = client.get("/api/v1/admin/events/summary", headers=_tok(admin))
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert "top_pages" in body and "daily" in body



