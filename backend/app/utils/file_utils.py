"""
Utilities for handling file uploads and validations.
"""

import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import UploadFile, HTTPException
from PIL import Image

from app.config import settings


async def validate_image(file: UploadFile) -> None:
    """
    Validate that an uploaded file is an allowed image type and
    does not exceed the maximum upload size.

    Raises:
        HTTPException 400 if validation fails.
    """
    # Check file extension
    if file.filename:
        ext = f".{file.filename.rsplit('.', 1)[-1].lower()}"
    else:
        ext = ""

    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"File extension {ext} is not allowed. "
                f"Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            ),
        )

    # Read content and check size
    contents = await file.read()
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=(
                f"File too large. Maximum size is "
                f"{settings.MAX_FILE_SIZE_MB} MB."
            ),
        )

    # Verify it's an actual image using Pillow
    try:
        img = Image.open(file.file)
        img.verify()
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is not a valid image.",
        ) from exc

    # Reset file pointer so downstream consumers can read again
    await file.seek(0)


async def save_upload(file: UploadFile, sub_dir: Optional[str] = None) -> str:
    """
    Save an uploaded file to the configured upload directory.

    Args:
        file: The uploaded file from FastAPI.
        sub_dir: Optional subdirectory (e.g., 'analyses') within uploads/.

    Returns:
        Relative file path (e.g. 'uploads/analyses/abc123.jpg').
    """
    # Determine save path
    base = Path("./uploads")
    if sub_dir:
        base = base / sub_dir
    base.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename else "jpg"
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    file_path = base / unique_name

    # Write file
    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    await file.seek(0)

    return str(file_path)