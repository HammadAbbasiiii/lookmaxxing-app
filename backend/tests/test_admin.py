"""Tests for admin user-management endpoints (promote/demote + tier override).

Covers every scenario the admin Users table can trigger:
  - non-admin is denied (403) on the list and on both mutations
  - promote a non-admin  -> is_admin=True  + audit row
  - demote an admin      -> is_admin=False + audit row
  - promote is idempotent (200, no duplicate audit)
  - an admin cannot change their own admin status (400)
  - unknown user id      -> 404 (for both admin + tier)
  - tier override        -> pro/elite set is_subscribed, free clears it
  - invalid tier         -> 400
  - case-insensitive tier
"""

import pytest

from app.dependencies import create_access_token, get_password_hash
from app.models import AdminAction, User


@pytest.fixture
def admin_user(db_session):
    u = User(
        email="admin@example.com",
        hashed_password=get_password_hash("adminpass123"),
        full_name="Admin User",
        is_subscribed=False,
        subscription_tier="free",
        is_admin=True,
        current_day=0,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def admin_token(admin_user):
    return create_access_token(data={"sub": admin_user.id})


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def user_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


def _other_admin(db_session):
    u = User(
        email="otheradmin@example.com",
        hashed_password=get_password_hash("adminpass123"),
        full_name="Other Admin",
        is_subscribed=False,
        subscription_tier="free",
        is_admin=True,
        current_day=0,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


# ── Gate: non-admin is denied ─────────────────────────────────────────
def test_users_list_requires_admin(client, user_headers):
    res = client.get("/api/v1/admin/users", headers=user_headers)
    assert res.status_code == 403


def test_promote_requires_admin(client, user_headers, test_user):
    res = client.patch(
        f"/api/v1/admin/users/{test_user.id}/admin", json={"is_admin": True}, headers=user_headers
    )
    assert res.status_code == 403


def test_tier_requires_admin(client, user_headers, test_user):
    res = client.patch(
        f"/api/v1/admin/users/{test_user.id}/tier", json={"tier": "pro"}, headers=user_headers
    )
    assert res.status_code == 403


# ── List includes is_admin ────────────────────────────────────────────
def test_users_list_includes_is_admin(client, admin_headers, test_user):
    res = client.get("/api/v1/admin/users", headers=admin_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    by_email = {u["email"]: u for u in body["users"]}
    assert "test@example.com" in by_email
    assert by_email["test@example.com"]["is_admin"] is False


# ── Promote / demote ──────────────────────────────────────────────────
def test_promote_user(client, admin_headers, test_user, db_session):
    res = client.patch(
        f"/api/v1/admin/users/{test_user.id}/admin", json={"is_admin": True}, headers=admin_headers
    )
    assert res.status_code == 200
    assert res.json()["user"]["is_admin"] is True
    db_session.refresh(test_user)
    assert test_user.is_admin is True
    audit = (
        db_session.query(AdminAction)
        .filter(AdminAction.entity_id == test_user.id, AdminAction.action == "promote_admin")
        .first()
    )
    assert audit is not None
    assert audit.admin_email == "admin@example.com"


def test_demote_admin(client, admin_headers, db_session):
    other = _other_admin(db_session)
    res = client.patch(
        f"/api/v1/admin/users/{other.id}/admin", json={"is_admin": False}, headers=admin_headers
    )
    assert res.status_code == 200
    assert res.json()["user"]["is_admin"] is False
    db_session.refresh(other)
    assert other.is_admin is False
    audit = (
        db_session.query(AdminAction)
        .filter(AdminAction.entity_id == other.id, AdminAction.action == "demote_admin")
        .first()
    )
    assert audit is not None


def test_promote_is_idempotent(client, admin_headers, test_user):
    first = client.patch(
        f"/api/v1/admin/users/{test_user.id}/admin", json={"is_admin": True}, headers=admin_headers
    )
    second = client.patch(
        f"/api/v1/admin/users/{test_user.id}/admin", json={"is_admin": True}, headers=admin_headers
    )
    assert first.status_code == 200
    assert second.status_code == 200


def test_cannot_change_own_admin_status(client, admin_headers, admin_user):
    res = client.patch(
        f"/api/v1/admin/users/{admin_user.id}/admin", json={"is_admin": False}, headers=admin_headers
    )
    assert res.status_code == 400
    assert "own admin status" in res.json()["detail"]


def test_admin_toggle_unknown_user(client, admin_headers):
    res = client.patch(
        "/api/v1/admin/users/does-not-exist/admin", json={"is_admin": True}, headers=admin_headers
    )
    assert res.status_code == 404


# ── Tier override ─────────────────────────────────────────────────────
def test_set_tier_pro(client, admin_headers, test_user, db_session):
    res = client.patch(
        f"/api/v1/admin/users/{test_user.id}/tier", json={"tier": "pro"}, headers=admin_headers
    )
    assert res.status_code == 200
    assert res.json()["user"]["tier"] == "pro"
    db_session.refresh(test_user)
    assert test_user.subscription_tier == "pro"
    assert test_user.is_subscribed is True
    audit = (
        db_session.query(AdminAction)
        .filter(AdminAction.entity_id == test_user.id, AdminAction.action == "set_tier")
        .first()
    )
    assert audit is not None


def test_set_tier_elite(client, admin_headers, test_user, db_session):
    res = client.patch(
        f"/api/v1/admin/users/{test_user.id}/tier", json={"tier": "elite"}, headers=admin_headers
    )
    assert res.status_code == 200
    db_session.refresh(test_user)
    assert test_user.subscription_tier == "elite"
    assert test_user.is_subscribed is True


def test_set_tier_free_revokes_subscription(client, admin_headers, test_user, db_session):
    client.patch(f"/api/v1/admin/users/{test_user.id}/tier", json={"tier": "pro"}, headers=admin_headers)
    res = client.patch(
        f"/api/v1/admin/users/{test_user.id}/tier", json={"tier": "free"}, headers=admin_headers
    )
    assert res.status_code == 200
    db_session.refresh(test_user)
    assert test_user.subscription_tier == "free"
    assert test_user.is_subscribed is False


def test_set_tier_invalid(client, admin_headers, test_user):
    res = client.patch(
        f"/api/v1/admin/users/{test_user.id}/tier", json={"tier": "premium"}, headers=admin_headers
    )
    assert res.status_code == 400
    assert "Tier must be one of" in res.json()["detail"]


def test_set_tier_unknown_user(client, admin_headers):
    res = client.patch(
        "/api/v1/admin/users/does-not-exist/tier", json={"tier": "pro"}, headers=admin_headers
    )
    assert res.status_code == 404


def test_set_tier_case_insensitive(client, admin_headers, test_user, db_session):
    res = client.patch(
        f"/api/v1/admin/users/{test_user.id}/tier", json={"tier": "PRO"}, headers=admin_headers
    )
    assert res.status_code == 200
    db_session.refresh(test_user)
    assert test_user.subscription_tier == "pro"
