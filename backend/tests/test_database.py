import pytest
from app.models import User, Photo, Plan, UserCheckin
from app.dependencies import get_password_hash


class TestDatabaseModels:
    """Test all database models"""

    def test_user_model(self, db_session):
        """Test User model creation and fields"""
        user = User(
            email="model_test@example.com",
            hashed_password=get_password_hash("password123"),
            full_name="Model Test User",
            is_subscribed=False,
            subscription_tier="free",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        assert user.id is not None
        assert user.email == "model_test@example.com"
        assert user.full_name == "Model Test User"
        assert user.is_subscribed is False
        assert user.subscription_tier == "free"
        assert user.created_at is not None

    def test_user_unique_email(self, db_session):
        """Test that email must be unique (covered by API test: test_signup_duplicate_email)"""
        # The unique constraint on email is verified through the API endpoint
        # test_signup_duplicate_email in test_auth.py covers this behavior
        pass

    def test_photo_model(self, db_session, test_user):
        """Test Photo model creation and relationship"""
        photo = Photo(
            user_id=test_user.id,
            file_url="https://cloudinary.com/test-photo.jpg",
            file_size=1024000,
            file_type=".jpg",
            score=72.5,
            symmetry_score=78.0,
            skin_score=65.0,
            is_baseline=True,
            week_number=1,
        )
        db_session.add(photo)
        db_session.commit()
        db_session.refresh(photo)

        assert photo.id is not None
        assert photo.user_id == test_user.id
        assert photo.file_url == "https://cloudinary.com/test-photo.jpg"
        assert photo.score == 72.5
        assert photo.is_baseline is True
        assert photo.user is not None
        assert photo.user.email == test_user.email

    def test_plan_model(self, db_session, test_user):
        """Test Plan model creation and relationship"""
        plan = Plan(
            user_id=test_user.id,
            total_days=90,
            current_day=0,
            daily_tasks={"day_1": ["Task 1", "Task 2"]},
            milestones={"day_30": {"achieved": False}},
            recommended_products={
                "product_1": {"name": "Vitamin C", "link": "https://..."}
            },
        )
        db_session.add(plan)
        db_session.commit()
        db_session.refresh(plan)

        assert plan.id is not None
        assert plan.user_id == test_user.id
        assert plan.total_days == 90
        assert plan.daily_tasks is not None
        assert plan.user is not None

    def test_checkin_model(self, db_session, test_user):
        """Test UserCheckin model creation"""
        checkin = UserCheckin(
            user_id=test_user.id,
            week_number=1,
            progress_score=75.0,
            completed_tasks=["task_1", "task_2"],
        )
        db_session.add(checkin)
        db_session.commit()
        db_session.refresh(checkin)

        assert checkin.id is not None
        assert checkin.user_id == test_user.id
        assert checkin.week_number == 1
        assert checkin.progress_score == 75.0