"""Password reset (forgot password) — full security scenario suite.

Covers: anti-enumeration, hashed token storage, single-use, expiry, throttle,
short/invalid input, session revocation, and end-to-end reset → login.
"""
import re
from datetime import datetime, timedelta

from app.dependencies import create_access_token
from app.models import PasswordResetToken
from app.services.password_reset_service import generate_reset_token, hash_token


FORGOT_URL = "/api/v1/auth/forgot-password"
RESET_URL = "/api/v1/auth/reset-password"
VERIFY_URL = "/api/v1/auth/reset-password/verify"
LOGIN_URL = "/api/v1/auth/login"


def _request_reset(client, email):
    return client.post(FORGOT_URL, json={"email": email})


def _extract_token_from_email_output(capsys):
    """Parse the reset token out of the console email output."""
    captured = capsys.readouterr().out
    match = re.search(r"/reset-password\?token=([A-Za-z0-9_-]+)", captured)
    return match.group(1) if match else None


class TestForgotPassword:
    def test_existing_email_returns_generic_200(self, client, test_user):
        r = _request_reset(client, test_user.email)
        assert r.status_code == 200
        body = r.json()
        assert "token" not in body
        assert "hash" not in body
        assert "link" in body["message"]

    def test_unknown_email_returns_identical_response(self, client):
        r = _request_reset(client, "nobody@example.com")
        assert r.status_code == 200
        # Anti-enumeration: exact same body as the existing-account case.
        assert r.json()["message"] == "If an account exists for that email, a reset link is on its way."

    def test_invalid_email_rejected(self, client):
        r = client.post(FORGOT_URL, json={"email": "not-an-email"})
        assert r.status_code == 422

    def test_only_known_email_creates_token(self, client, test_user, db_session):
        _request_reset(client, "nobody@example.com")
        assert db_session.query(PasswordResetToken).count() == 0

        _request_reset(client, test_user.email)
        tokens = db_session.query(PasswordResetToken).all()
        assert len(tokens) == 1
        assert tokens[0].user_id == test_user.id

    def test_token_stored_hashed_not_raw(self, client, test_user, db_session, capsys):
        _request_reset(client, test_user.email)
        raw = _extract_token_from_email_output(capsys)
        assert raw and len(raw) >= 32

        token = db_session.query(PasswordResetToken).one()
        # Stored value is a SHA-256 hex digest, not the raw token.
        assert token.token_hash != raw
        assert len(token.token_hash) == 64
        assert token.token_hash == hash_token(raw)

    def test_new_request_invalidates_previous_token(self, client, test_user, db_session):
        _request_reset(client, test_user.email)
        _request_reset(client, test_user.email)
        # Only the latest unused token survives.
        unused = db_session.query(PasswordResetToken).filter(
            PasswordResetToken.used_at.is_(None)
        ).all()
        assert len(unused) == 1


class TestResetPassword:
    def _get_valid_token(self, client, test_user, capsys):
        _request_reset(client, test_user.email)
        return _extract_token_from_email_output(capsys)

    def test_reset_with_valid_token_then_login(self, client, test_user, capsys):
        token = self._get_valid_token(client, test_user, capsys)
        r = client.post(RESET_URL, json={"token": token, "new_password": "newpass456"})
        assert r.status_code == 200

        # Old password no longer works.
        old = client.post(LOGIN_URL, data={"username": test_user.email, "password": "testpass123"})
        assert old.status_code == 401

        # New password works.
        new = client.post(LOGIN_URL, data={"username": test_user.email, "password": "newpass456"})
        assert new.status_code == 200
        assert new.json()["access_token"]

    def test_reset_token_is_single_use(self, client, test_user, capsys):
        token = self._get_valid_token(client, test_user, capsys)
        assert client.post(RESET_URL, json={"token": token, "new_password": "newpass456"}).status_code == 200
        # Replay the same token → rejected.
        assert client.post(RESET_URL, json={"token": token, "new_password": "another789"}).status_code == 400

    def test_reset_with_forged_token_rejected(self, client):
        forged = generate_reset_token()
        r = client.post(RESET_URL, json={"token": forged, "new_password": "newpass456"})
        assert r.status_code == 400

    def test_reset_with_expired_token_rejected(self, client, test_user, db_session):
        raw = generate_reset_token()
        db_session.add(PasswordResetToken(
            user_id=test_user.id,
            token_hash=hash_token(raw),
            expires_at=datetime.utcnow() - timedelta(minutes=1),
        ))
        db_session.commit()

        r = client.post(RESET_URL, json={"token": raw, "new_password": "newpass456"})
        assert r.status_code == 400

    def test_reset_short_password_rejected(self, client, test_user, capsys):
        token = self._get_valid_token(client, test_user, capsys)
        r = client.post(RESET_URL, json={"token": token, "new_password": "12345"})
        assert r.status_code == 422

    def test_reset_revokes_existing_sessions(self, client, test_user, db_session):
        old_token = create_access_token(data={"sub": test_user.id, "ver": test_user.token_version or 0})

        raw = generate_reset_token()
        db_session.add(PasswordResetToken(
            user_id=test_user.id,
            token_hash=hash_token(raw),
            expires_at=datetime.utcnow() + timedelta(minutes=30),
        ))
        db_session.commit()

        # Token valid before reset.
        assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {old_token}"}).status_code == 200

        assert client.post(RESET_URL, json={"token": raw, "new_password": "newpass456"}).status_code == 200

        # Old access token is now revoked.
        assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {old_token}"}).status_code == 401


class TestResetTokenVerify:
    def test_verify_valid_token(self, client, test_user, db_session):
        raw = generate_reset_token()
        db_session.add(PasswordResetToken(
            user_id=test_user.id,
            token_hash=hash_token(raw),
            expires_at=datetime.utcnow() + timedelta(minutes=30),
        ))
        db_session.commit()

        r = client.get(VERIFY_URL, params={"token": raw})
        assert r.status_code == 200
        assert r.json()["valid"] is True

    def test_verify_invalid_token(self, client):
        r = client.get(VERIFY_URL, params={"token": generate_reset_token()})
        assert r.status_code == 400


class TestForgotPasswordThrottle:
    def test_throttle_returns_429_after_limit(self, client):
        email = "victim@example.com"
        statuses = [_request_reset(client, email).status_code for _ in range(6)]
        assert statuses.count(429) >= 1
