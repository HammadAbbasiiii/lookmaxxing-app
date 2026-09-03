"""
Direct Cloudinary Upload API
=============================
Allows clients to upload directly to Cloudinary (bypassing the server),
then register the resulting URL with the backend.

Flow:
  1. Client calls GET /signature → receives signed upload params
  2. Client uploads directly to Cloudinary using those params (1-2s)
  3. Client calls POST /save with the resulting secure_url + public_id
  4. Server creates the Photo record and returns the photo_id
"""

import time
import uuid
from datetime import datetime

import cloudinary.utils
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Photo, Plan, User
from app.services.prediction_service import prediction_service
from app.services.entitlements_service import enforce_photo_limit

router = APIRouter(prefix="/upload", tags=["Upload"])


# ── GET /signature ──────────────────────────────────────────────────────────


@router.get("/signature")
async def get_upload_signature(
    current_user: User = Depends(get_current_user),
):
    """
    Generate signed upload credentials so the client can upload
    directly to Cloudinary without routing image bytes through the server.

    The returned fields are used by the Cloudinary iOS SDK to perform
    a direct, authenticated upload.
    """
    timestamp = int(time.time())
    public_id = f"user_{current_user.id[:8]}_{uuid.uuid4().hex[:8]}"
    folder = f"lookmaxx/photos/{current_user.id}"

    params_to_sign = {
        "timestamp": str(timestamp),
        "folder": folder,
        "public_id": public_id,
    }

    # Include upload preset in signature only if configured
    if settings.CLOUDINARY_UPLOAD_PRESET:
        params_to_sign["upload_preset"] = settings.CLOUDINARY_UPLOAD_PRESET

    signature = cloudinary.utils.api_sign_request(
        params_to_sign,
        api_secret=settings.CLOUDINARY_API_SECRET,
    )

    resp = {
        "signature": signature,
        "timestamp": timestamp,
        "cloud_name": settings.CLOUDINARY_CLOUD_NAME,
        "api_key": settings.CLOUDINARY_API_KEY,
        "folder": folder,
        "public_id": public_id,
    }

    if settings.CLOUDINARY_UPLOAD_PRESET:
        resp["upload_preset"] = settings.CLOUDINARY_UPLOAD_PRESET

    return resp


# ── POST /save ──────────────────────────────────────────────────────────────


@router.post("/save")
async def save_direct_upload(
    file_url: str,
    public_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Register a photo that was uploaded directly to Cloudinary by the client.

    The client should call this AFTER a successful direct upload.
    This creates the Photo record and returns the photo_id so the client
    can immediately request analysis.
    """
    # Validate the URL belongs to our Cloudinary account
    if settings.CLOUDINARY_CLOUD_NAME not in file_url:
        raise HTTPException(
            status_code=400,
            detail="Invalid file_url — must be a Cloudinary URL",
        )

    # Freemium gate: free users can save only their free allowance of photos.
    enforce_photo_limit(current_user, db)

    # Check if this is the user's first photo (baseline)
    is_baseline = (
        db.query(Photo).filter(Photo.user_id == current_user.id).count() == 0
    )

    # Determine week_number from the active plan
    plan = (
        db.query(Plan)
        .filter(Plan.user_id == current_user.id, Plan.is_active == True)
        .order_by(Plan.created_at.desc())
        .first()
    )
    week_number = plan.current_week if (plan and plan.current_week) else 1

    # Save photo record
    new_photo = Photo(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        file_url=file_url,
        file_size=0,  # Unknown — client handled upload
        file_type=".jpg",  # Cloudinary delivers auto-format
        is_baseline=is_baseline,
        week_number=week_number,
    )

    db.add(new_photo)
    db.commit()
    db.refresh(new_photo)

    return {
        "photo_id": new_photo.id,
        "file_url": new_photo.file_url,
        "is_baseline": new_photo.is_baseline,
        "week_number": new_photo.week_number,
    }