import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
from app.models import User
from app.dependencies import get_password_hash

# Test database (file-based SQLite)
TEST_DATABASE_URL = "sqlite:///./test_lookmaxx.db"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override DB dependency for testing - creates a fresh session"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def db_engine():
    """Create test database tables once per session, drop at end"""
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Get a database session that commits and cleans up after each test"""
    session = TestingSessionLocal()

    yield session

    # Clean up all data after each test
    from app.models import User, Photo, Plan, UserCheckin, PasswordResetToken
    from app.models import GlowState, GlowReveal, ArcState, UserBadge, Transformation
    session.query(PasswordResetToken).delete()
    session.query(GlowReveal).delete()
    session.query(GlowState).delete()
    session.query(ArcState).delete()
    session.query(UserBadge).delete()
    session.query(Transformation).delete()
    session.query(UserCheckin).delete()
    session.query(Photo).delete()
    session.query(Plan).delete()
    session.query(User).delete()
    session.commit()
    session.close()


@pytest.fixture(scope="function", autouse=True)
def _reset_password_reset_throttle():
    """Start each test with a clean per-email reset throttle."""
    from app.services.password_reset_service import reset_throttle

    reset_throttle()
    yield
    reset_throttle()


@pytest.fixture(scope="function", autouse=True)
def _reset_login_throttle():
    """Start each test with a clean failed-login throttle."""
    from app.routes.auth import _login_failures

    _login_failures.clear()
    yield
    _login_failures.clear()


@pytest.fixture(scope="function", autouse=True)
def _reset_rate_limiter():
    """Start each test with a clean in-memory rate-limit window.

    The middleware's in-memory fallback store is module-global, so a test that
    hammers a bucket would otherwise poison the next test's requests with 429s.
    """
    from app.middleware.rate_limit import _fallback_store

    _fallback_store.clear()
    yield
    _fallback_store.clear()


@pytest.fixture(scope="function")
def client(db_session):
    """Test client for API calls"""
    return TestClient(app)


@pytest.fixture(scope="function")
def test_user(db_session):
    """Create a test user (committed to DB so API can see it)"""
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Test User",
        is_subscribed=False,
        subscription_tier="free",
        current_day=0,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_token(test_user):
    """Get auth token for test user (generated directly, no API call needed)"""
    from app.dependencies import create_access_token

    return create_access_token(data={"sub": test_user.id})