"""Password strength validation (§7, §13).

Locks in the minimum password bar: 8+ chars, at least two character classes,
no trivially-common passwords, and no password that mirrors the account email.
"""

from app.dependencies import validate_password_strength


class TestPasswordStrengthUnit:
    def test_accepts_mixed_lower_digit(self):
        ok, _ = validate_password_strength("testpass123")
        assert ok is True

    def test_accepts_symbols(self):
        ok, _ = validate_password_strength("C0rrect-horse!")
        assert ok is True

    def test_rejects_common_password(self):
        ok, msg = validate_password_strength("password123")
        assert ok is False
        assert "common" in msg

    def test_rejects_single_class(self):
        ok, msg = validate_password_strength("abcdefghij")
        assert ok is False
        assert "two of" in msg

    def test_rejects_email_as_password(self):
        ok, msg = validate_password_strength("newuser@example.com", "newuser@example.com")
        assert ok is False
        assert "email" in msg

    def test_rejects_local_part_of_email(self):
        ok, _ = validate_password_strength("lookmaxxpass", "lookmaxx@example.com")
        assert ok is False


class TestSignupPasswordStrength:
    def test_signup_rejects_common_password(self, client):
        r = client.post(
            "/api/v1/auth/signup",
            json={"email": "common@example.com", "password": "password123"},
        )
        assert r.status_code == 422
        assert "common" in r.json()["detail"]

    def test_signup_rejects_single_class_password(self, client):
        r = client.post(
            "/api/v1/auth/signup",
            json={"email": "weak@example.com", "password": "abcdefghij"},
        )
        assert r.status_code == 422

    def test_signup_accepts_strong_password(self, client):
        r = client.post(
            "/api/v1/auth/signup",
            json={"email": "strong@example.com", "password": "Str0ng-Pass!"},
        )
        assert r.status_code == 200
