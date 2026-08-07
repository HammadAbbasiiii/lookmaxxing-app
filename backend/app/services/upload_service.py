import cloudinary
import cloudinary.uploader
from app.config import settings
import uuid
from PIL import Image
import io

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET
)

def upload_to_cloudinary(file_content: bytes, filename: str) -> str:
    """
    Upload image to Cloudinary and return URL.
    """
    # Resize image if too large (max 2000px width/height)
    image = Image.open(io.BytesIO(file_content))
    max_size = 2000
    if image.width > max_size or image.height > max_size:
        image.thumbnail((max_size, max_size))
        # Save to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG', quality=85)
        file_content = img_byte_arr.getvalue()
    
    # Upload to Cloudinary
    result = cloudinary.uploader.upload(
        file_content,
        folder="lookmaxx/photos",
        public_id=f"user_{uuid.uuid4().hex[:8]}",
        resource_type="image"
    )
    
    return result.get("secure_url")

def delete_from_cloudinary(public_id: str):
    """
    Delete image from Cloudinary.
    """
    cloudinary.uploader.destroy(public_id)