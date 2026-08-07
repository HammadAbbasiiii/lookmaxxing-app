import pytest
from app.dependencies import get_password_hash, verify_password, create_access_token
from jose import jwt
from app.config import settings


class TestAuth:
    """Test authentication"""

    def test_password_hashing(self):
        """Test password hashing and verification"""
        password = "secure_password_123"
        hashed = get_password_hash(password)

        # Hash should be different from original
        assert hashed != password

        # Verification should work
        assert verify_password(password, hashed) is True

        # Wrong password should fail
        assert verify_password("wrong_password", hashed) is False

    def test_jwt_creation(self):
        """Test JWT token creation"""
        user_id = "test-user-id-123"
        token = create_access_token(data={"sub": user_id})

        # Token should be a string
        assert isinstance(token, str)
        assert len(token) > 20

        # Decode token
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert payload.get("sub") == user_id
        assert "exp" in payload

    def test_signup_success(self, client):
        """Test successful signup"""
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "email": "newuser@example.com",
                "password": "testpass123",
                "full_name": "New User",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New User"
        assert data["is_subscribed"] is False
        assert "id" in data
        assert "hashed_password" not in data  # Should not expose password

    def test_signup_duplicate_email(self, client):
        """Test signup with existing email"""
        # First signup
        client.post(
            "/api/v1/auth/signup",
            json={"email": "duplicate@example.com", "password": "testpass123"},
        )

        # Second signup with same email
        response = client.post(
            "/api/v1/auth/signup",
            json={"email": "duplicate@example.com", "password": "testpass123"},
        )

        assert response.status_code == 400
        assert "Email already registered" in response.json().get("detail")

    def test_login_success(self, client):
        """Test successful login"""
        # Create user
        client.post(
            "/api/v1/auth/signup",
            json={"email": "login@example.com", "password": "testpass123"},
        )

        # Login
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "login@example.com", "password": "testpass123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["email"] == "login@example.com"

    def test_login_wrong_password(self, client):
        """Test login with wrong password"""
        # Create user
        client.post(
            "/api/v1/auth/signup",
            json={"email": "wrongpass@example.com", "password": "testpass123"},
        )

        # Login with wrong password
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "wrongpass@example.com", "password": "wrongpassword"},
        )

        assert response.status_code == 401
        assert "Incorrect email or password" in response.json().get("detail")

    def test_login_nonexistent_user(self, client):
        """Test login with nonexistent email"""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "testpass123",
            },
        )

        assert response.status_code == 401
        assert "Incorrect email or password" in response.json().get("detail")

    def test_me_endpoint_valid_token(self, client, auth_token):
        """Test /me endpoint with valid token"""
        response = client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["full_name"] == "Test User"

    def test_me_endpoint_invalid_token(self, client):
        """Test /me endpoint with invalid token"""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token_here"},
        )

        assert response.status_code == 401
        assert "Could not validate credentials" in response.json().get("detail")

    def test_me_endpoint_no_token(self, client):
        """Test /me endpoint with no token"""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401
        assert "Not authenticated" in response.json().get("detail")