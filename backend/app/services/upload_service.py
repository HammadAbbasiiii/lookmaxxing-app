import cloudinary
import cloudinary.uploader
from app.config import settings
import uuid
from PIL import Image
import io
import logging

logger = logging.getLogger(__name__)

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET
)

UPLOAD_MAX_PX = 1200    # max dimension before upload (was 2000)
UPLOAD_QUALITY = 70     # JPEG quality (was 85)
UPLOAD_WEBP_QUALITY = 75  # WebP quality (25-35% smaller than JPEG at same quality)

# Folder every upload is filed under — see upload_to_cloudinary().
CLOUDINARY_FOLDER = "lookmaxx/photos"


def compress_for_upload(image_bytes: bytes) -> bytes:
    """
    Aggressively compress an image for fast upload.
    Reduces 5-10MB photos to 100-300KB while preserving face analysis quality.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        original_size = len(image_bytes)
        original_dims = img.size

        # Convert RGBA/P to RGB
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # Resize if larger than max dimension
        if img.width > UPLOAD_MAX_PX or img.height > UPLOAD_MAX_PX:
            img.thumbnail((UPLOAD_MAX_PX, UPLOAD_MAX_PX), Image.Resampling.LANCZOS)

        # Save with compression
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=UPLOAD_QUALITY, optimize=True)
        compressed = buf.getvalue()

        compressed_size = len(compressed)
        reduction = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
        logger.info(
            f"📸 Compressed: {original_dims} → {img.size}, "
            f"{original_size // 1024}KB → {compressed_size // 1024}KB "
            f"({reduction:.0f}% smaller)"
        )
        return compressed
    except Exception as exc:
        logger.warning(f"Image compression failed, returning original: {exc}")
        return image_bytes


def convert_to_webp(image_bytes: bytes, quality: int = UPLOAD_WEBP_QUALITY) -> bytes:
    """
    Convert image to WebP format for better compression.
    WebP is 25-35% smaller than JPEG at equivalent visual quality.
    All major browsers and iOS 14+ support WebP.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=quality, optimize=True)
        webp_bytes = buf.getvalue()
        logger.info(
            f"🖼 WebP conversion: {len(image_bytes) // 1024}KB → {len(webp_bytes) // 1024}KB "
            f"({(1 - len(webp_bytes) / len(image_bytes)) * 100:.0f}% smaller)"
        )
        return webp_bytes
    except Exception as e:
        logger.warning(f"WebP conversion failed, returning original: {e}")
        return image_bytes


def upload_to_cloudinary(file_content: bytes, filename: str) -> str:
    """
    Compress and upload image to Cloudinary, return secure URL.
    """
    # Compress before uploading to Cloudinary — saves 5-6s on upload time
    compressed = compress_for_upload(file_content)

    # Upload to Cloudinary with auto-optimization
    result = cloudinary.uploader.upload(
        compressed,
        folder=CLOUDINARY_FOLDER,
        public_id=f"user_{uuid.uuid4().hex[:8]}",
        resource_type="image",
        quality="auto",          # Cloudinary auto-optimizes quality
        fetch_format="auto",     # Converts to WebP when supported
        flags="attachment",      # Enables further optimization
    )

    return result.get("secure_url")

def delete_from_cloudinary(public_id: str) -> dict:
    """Delete image from Cloudinary, raising if the provider didn't confirm.

    ``destroy()`` reports failure in its *return value* (``{"result": "not
    found"}``) rather than by raising, so a bare call can look like a success
    while deleting nothing. We inspect the result explicitly.
    """
    result = cloudinary.uploader.destroy(public_id, invalidate=True)
    outcome = (result or {}).get("result")
    if outcome == "ok":
        logger.info(f"🗑 Deleted from Cloudinary: {public_id}")
        return result
    if outcome == "not found":
        # Already gone (e.g. a retried delete) — the desired end state holds.
        logger.warning(f"Cloudinary asset already absent: {public_id}")
        return result
    raise RuntimeError(f"Cloudinary delete failed for {public_id}: {result}")


def public_id_from_url(url: str | None) -> str | None:
    """Recover the Cloudinary ``public_id`` from a stored delivery URL.

    ``destroy()`` needs the exact public_id we uploaded with —
    ``lookmaxx/photos/user_ab12cd34`` — not the bare filename. The previous
    implementation split the URL on ``/`` and re-prefixed the result, yielding
    ``lookmaxx/photos/user_user_ab12cd34``: a public_id that never matched, so
    every delete silently no-oped and the image stayed live at the provider.

    Returns ``None`` when the URL isn't one of ours, so callers can fail loudly
    instead of reporting an image as deleted when it isn't.
    """
    if not url:
        return None
    path = url.split("?", 1)[0].split("#", 1)[0]
    marker = f"{CLOUDINARY_FOLDER}/"
    idx = path.find(marker)
    if idx == -1:
        return None
    public_id = path[idx:]
    head, _, tail = public_id.rpartition(".")
    if head and "/" not in tail:  # strip a trailing file extension
        public_id = head
    return public_id or None
