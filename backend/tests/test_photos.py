import pytest
from unittest.mock import patch
from app.models import Photo


class TestPhotos:
    """Test photo upload functionality"""

    def test_upload_without_auth(self, client):
        """Test upload without authentication"""
        response = client.post(
            "/api/v1/photos/upload",
            files={"file": ("test.jpg", b"fake image data", "image/jpeg")},
        )

        assert response.status_code == 401

    def test_upload_invalid_file_type(self, client, auth_token):
        """Test upload with invalid file type"""
        response = client.post(
            "/api/v1/photos/upload",
            headers={"Authorization": f"Bearer {auth_token}"},
            files={"file": ("test.txt", b"not an image", "text/plain")},
        )

        assert response.status_code == 400
        assert "Unsupported file format" in response.json().get("detail")

    @patch("app.routes.photos.upload_to_cloudinary")
    def test_upload_success(self, mock_upload, client, auth_token, db_session):
        """Test successful photo upload"""
        # Mock Cloudinary upload
        mock_upload.return_value = "https://cloudinary.com/test-photo.jpg"

        # Create a valid JPEG header so PIL can read it
        from PIL import Image
        import io

        img = Image.new("RGB", (10, 10), color="red")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        jpeg_bytes = buf.getvalue()

        response = client.post(
            "/api/v1/photos/upload",
            headers={"Authorization": f"Bearer {auth_token}"},
            files={"file": ("test.jpg", jpeg_bytes, "image/jpeg")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["file_url"] == "https://cloudinary.com/test-photo.jpg"
        assert data["is_baseline"] is True  # First photo
        assert "id" in data

        # Verify photo was saved in database
        photo = db_session.query(Photo).filter(Photo.id == data["id"]).first()
        assert photo is not None
        assert photo.user_id is not None

    def test_get_photos(self, client, auth_token, db_session, test_user):
        """Test getting all photos for a user"""
        # Create test photos
        photo1 = Photo(
            user_id=test_user.id,
            file_url="https://cloudinary.com/photo1.jpg",
            file_size=1000,
            file_type=".jpg",
            is_baseline=True,
        )
        photo2 = Photo(
            user_id=test_user.id,
            file_url="https://cloudinary.com/photo2.jpg",
            file_size=2000,
            file_type=".jpg",
            is_baseline=False,
        )
        db_session.add_all([photo1, photo2])
        db_session.commit()

        # Get photos
        response = client.get(
            "/api/v1/photos/all",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        urls = {d["file_url"] for d in data}
        assert "https://cloudinary.com/photo1.jpg" in urls
        assert "https://cloudinary.com/photo2.jpg" in urls
