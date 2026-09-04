"""Security & abuse-resistance suite (§7, §13, §19).

Brutal-tester coverage for the attack surface:
  - authentication / authorization (401 vs 403)
  - IDOR (cross-user object access) is blocked
  - password & email validation (Pydantic 422s)
  - JWT tampering / expiry / wrong-key / malformed tokens
  - rate limiting (anonymous bucket + per-user authenticated bucket)
  - secrets never leak in responses (no password hashes)
  - email normalization dedupes case/whitespace variations
"""

from datetime import timedelta

import pytest
from jose import jwt as jose_jwt

from app.config import settings
from app.dependencies import create_access_token, get_password_hash
from app.models import Photo, User


def _h(token):
    return {"Authorization": f"Bearer {token}"}


def _user(db_session, email, tier="free", admin=False):
    u = User(
        email=email,
        hashed_password=get_password_hash("pass1234"),
        full_name="Security User",
        is_subscribed=tier != "free",
        subscription_tier=tier,
        is_admin=admin,
        current_day=0,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


class TestPasswordAndEmailValidation:
    def test_signup_rejects_short_password(self, client):
        res = client.post(
            "/api/v1/auth/signup",
            json={"email": "short@example.com", "password": "12345"},
        )
        assert res.status_code == 422

    def test_signup_rejects_missing_password(self, client):
        res = client.post(
            "/api/v1/auth/signup", json={"email": "nopass@example.com"}
        )
        assert res.status_code == 422

    def test_signup_rejects_invalid_email(self, client):
        res = client.post(
            "/api/v1/auth/signup",
            json={"email": "not-an-email", "password": "pass1234"},
        )
        assert res.status_code == 422

    def test_signup_rejects_missing_email(self, client):
        res = client.post(
            "/api/v1/auth/signup", json={"password": "pass1234"}
        )
        assert res.status_code == 422

    def test_login_with_malformed_email_is_not_found(self, client):
        # OAuth2 form doesn't validate email format; a malformed email simply
        # matches no user, so it must 401 (never leak whether the user exists).
        res = client.post(
            "/api/v1/auth/login",
            data={"username": "not-an-email", "password": "pass1234"},
        )
        assert res.status_code == 401


class TestEmailNormalization:
    def test_signup_lowercases_email(self, client):
        res = client.post(
            "/api/v1/auth/signup",
            json={"email": "Mixed.Case@Example.com", "password": "pass1234"},
        )
        assert res.status_code == 200
        assert res.json()["email"] == "mixed.case@example.com"

    def test_signup_duplicate_case_insensitive(self, client):
        first = client.post(
            "/api/v1/auth/signup",
            json={"email": "Dup@Example.com", "password": "pass1234"},
        )
        assert first.status_code == 200
        second = client.post(
            "/api/v1/auth/signup",
            json={"email": "dup@example.com", "password": "pass1234"},
        )
        assert second.status_code == 400
        assert "already registered" in second.json()["detail"]


class TestSecretsNeverLeak:
    def test_signup_response_hides_hash(self, client):
        res = client.post(
            "/api/v1/auth/signup",
            json={"email": "noleak@example.com", "password": "pass1234"},
        )
        assert res.status_code == 200
        body = res.json()
        assert "hashed_password" not in body
        assert "password" not in body

    def test_me_hides_hash(self, client, auth_token):
        res = client.get("/api/v1/auth/me", headers=_h(auth_token))
        assert res.status_code == 200
        assert "hashed_password" not in res.json()

    def test_admin_user_list_hides_hash(self, client, db_session):
        admin = _user(db_session, "adminsec@example.com", tier="elite", admin=True)
        res = client.get(
            "/api/v1/admin/users",
            headers=_h(create_access_token(data={"sub": admin.id})),
        )
        assert res.status_code == 200
        for u in res.json()["users"]:
            assert "hashed_password" not in u


class TestJwtSecurity:
    def test_tampered_signature_rejected(self, client, auth_token):
        tampered = auth_token[:-1] + ("a" if auth_token[-1] != "a" else "b")
        res = client.get("/api/v1/auth/me", headers=_h(tampered))
        assert res.status_code == 401

    def test_expired_token_rejected(self, client):
        expired = create_access_token(
            data={"sub": "whatever"}, expires_delta=timedelta(seconds=-10)
        )
        res = client.get("/api/v1/auth/me", headers=_h(expired))
        assert res.status_code == 401

    def test_wrong_key_token_rejected(self, client):
        forged = jose_jwt.encode(
            {"sub": "victim"}, "attacker-secret", algorithm=settings.ALGORITHM
        )
        res = client.get("/api/v1/auth/me", headers=_h(forged))
        assert res.status_code == 401

    def test_none_algorithm_token_rejected(self, client):
        # jose refuses to *encode* with alg=none, so build the header/payload/
        # empty-signature form by hand — the server must still reject it.
        import base64
        import json

        def _b64(data: bytes) -> str:
            return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

        header = _b64(json.dumps({"alg": "none", "typ": "JWT"}).encode())
        payload = _b64(json.dumps({"sub": "victim"}).encode())
        forged = f"{header}.{payload}."
        res = client.get("/api/v1/auth/me", headers=_h(forged))
        assert res.status_code == 401

    def test_malformed_token_rejected(self, client):
        res = client.get("/api/v1/auth/me", headers=_h("not.a.jwt"))
        assert res.status_code == 401

    def test_missing_auth_header(self, client):
        res = client.get("/api/v1/auth/me")
        assert res.status_code == 401

    def test_empty_bearer_rejected(self, client):
        res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer "})
        assert res.status_code == 401


class TestIdorProtection:
    def test_cannot_read_another_users_photo(self, client, db_session, test_user, auth_token):
        victim = _user(db_session, "victim@example.com")
        photo = Photo(
            user_id=victim.id, file_url="https://example.com/victim.jpg", score=75.0
        )
        db_session.add(photo)
        db_session.commit()
        db_session.refresh(photo)

        res = client.get(f"/api/v1/analysis/{photo.id}", headers=_h(auth_token))
        assert res.status_code == 404

    def test_pro_cannot_read_another_users_report(self, client, db_session):
        victim = _user(db_session, "victim2@example.com")
        photo = Photo(
            user_id=victim.id, file_url="https://example.com/victim2.jpg", score=75.0
        )
        db_session.add(photo)
        db_session.commit()
        db_session.refresh(photo)

        attacker = _user(db_session, "attacker@example.com", tier="pro")
        res = client.get(
            f"/api/v1/analysis/{photo.id}/report",
            headers=_h(create_access_token(data={"sub": attacker.id})),
        )
        assert res.status_code == 404

    def test_cannot_access_admin_users_as_free_user(self, client, auth_token):
        res = client.get("/api/v1/admin/users", headers=_h(auth_token))
        assert res.status_code == 403


class TestRateLimiting:
    def test_anonymous_bucket_returns_429(self, client, monkeypatch):
        from app.middleware import rate_limit as rl

        monkeypatch.setattr(rl, "ANONYMOUS_LIMIT", 3)
        rl._fallback_store.clear()
        try:
            for _ in range(3):
                assert client.get("/api/v1/health").status_code == 200
            res = client.get("/api/v1/health")
            assert res.status_code == 429
            assert "Rate limit" in res.json()["detail"]
        finally:
            rl._fallback_store.clear()

    def test_authenticated_uses_separate_bucket(self, client, monkeypatch, auth_token):
        from app.middleware import rate_limit as rl

        monkeypatch.setattr(rl, "ANONYMOUS_LIMIT", 1)
        rl._fallback_store.clear()
        try:
            res = client.get("/api/v1/auth/me", headers=_h(auth_token))
            assert res.status_code == 200
        finally:
            rl._fallback_store.clear()

    def test_authenticated_bucket_returns_429(self, client, monkeypatch, auth_token):
        from app.middleware import rate_limit as rl

        monkeypatch.setattr(rl, "AUTHENTICATED_LIMIT", 2)
        rl._fallback_store.clear()
        try:
            for _ in range(2):
                assert (
                    client.get("/api/v1/auth/me", headers=_h(auth_token)).status_code
                    == 200
                )
            assert (
                client.get("/api/v1/auth/me", headers=_h(auth_token)).status_code == 429
            )
        finally:
            rl._fallback_store.clear()


class TestAdminEmailFallback:
    def test_email_in_admin_emails_is_admin(self, client, db_session):
        from app.dependencies import is_admin_user

        u = _user(db_session, "hammadabbasi732@gmail.com", tier="free")
        assert is_admin_user(u) is True

        res = client.get(
            "/api/v1/admin/overview",
            headers=_h(create_access_token(data={"sub": u.id})),
        )
        assert res.status_code == 200



