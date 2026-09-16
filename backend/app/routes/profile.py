"""
Profile Routes — User profile management.
Covers: GET/PUT profile, onboarding completion, account deletion (GDPR).
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Photo
from app.schemas import UserResponse, ProfileUpdate, OnboardingUpdate
from app.dependencies import get_current_user
from app.services.upload_service import delete_from_cloudinary, public_id_from_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profile", tags=["Profile"])

VALID_GENDERS = {"male", "female", "other"}
VALID_GOALS = {"improve_skin", "jawline", "confidence", "symmetry", "general"}
VALID_SKIN_TYPES = {"oily", "dry", "combination", "normal", "sensitive"}
VALID_COMMITMENT = {"casual", "consistent", "locked_in"}


def _validate_profile_update(data: dict) -> None:
    """Reject invalid profile values with a clean 400 (server-side validation)."""
    if "gender" in data and data["gender"] is not None and data["gender"] not in VALID_GENDERS:
        raise HTTPException(status_code=400, detail="gender must be one of: male, female, other.")
    if "goals" in data and data["goals"] is not None:
        invalid = [g for g in data["goals"] if g not in VALID_GOALS]
        if invalid:
            raise HTTPException(status_code=400, detail=f"Invalid goal(s): {', '.join(invalid)}.")
    if "skin_type" in data and data["skin_type"] is not None and data["skin_type"] not in VALID_SKIN_TYPES:
        raise HTTPException(status_code=400, detail="skin_type must be one of: oily, dry, combination, normal, sensitive.")
    if "commitment" in data and data["commitment"] is not None and data["commitment"] not in VALID_COMMITMENT:
        raise HTTPException(status_code=400, detail="commitment must be one of: casual, consistent, locked_in.")


# ---------------------------------------------------------------------------
# GET /profile — Get current user's full profile
# ---------------------------------------------------------------------------
@router.get("", response_model=UserResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return the current user's profile with all fields:
    age, gender, goals, onboarding status, subscription, streaks.
    """
    return current_user


# ---------------------------------------------------------------------------
# PUT /profile — Update profile fields
# ---------------------------------------------------------------------------
@router.put("", response_model=UserResponse)
async def update_profile(
    updates: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update profile fields. Only the fields provided will be changed.
    Accepts: age, gender, goals, height, weight, location, bio, full_name.
    """
    update_data = updates.model_dump(exclude_unset=True)
    _validate_profile_update(update_data)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update.",
        )

    for field, value in update_data.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)
    return current_user


# ---------------------------------------------------------------------------
# POST /profile/onboarding — Mark onboarding as complete
# ---------------------------------------------------------------------------
@router.post("/onboarding")
async def complete_onboarding(
    payload: Optional[OnboardingUpdate] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Mark onboarding complete, optionally saving the wizard's answers in the same
    call (age, gender, goals, skin type/concerns, height/weight, commitment).
    """
    if payload is not None:
        update_data = payload.model_dump(exclude_unset=True)
        _validate_profile_update(update_data)
        for field, value in update_data.items():
            setattr(current_user, field, value)

    current_user.onboarding_completed = True
    db.commit()

    return {
        "success": True,
        "message": "Onboarding marked as complete.",
        "onboarding_completed": True,
    }


# ---------------------------------------------------------------------------
# DELETE /profile/delete — Delete user account (GDPR compliance)
# ---------------------------------------------------------------------------
@router.delete("/delete")
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Permanently delete the user account and all associated data.

    GDPR-compliant, and fail *closed*. The DB cascades to photos, plans and
    checkins, but a cascade only removes rows — it cannot touch Cloudinary.
    Deleting the rows first would leave every face photo the user ever uploaded
    live on a public URL with nothing left to retry from, so the provider pass
    runs first and the whole request is aborted if any image is unconfirmed.

    Retrying is safe: `delete_from_cloudinary` treats "not found" as success, so
    an image already removed before a later failure reads as gone instead of
    blocking the retry forever.
    """
    user_id = current_user.id  # capture before the row is deleted

    photo_urls = [
        url
        for (url,) in db.query(Photo.file_url).filter(Photo.user_id == user_id).all()
    ]

    unconfirmed: list[str] = []
    for url in photo_urls:
        public_id = public_id_from_url(url)
        if not public_id:
            unconfirmed.append(url)
            logger.error(
                "Account deletion (user %s): could not derive a Cloudinary public_id "
                "from %s — aborting so the image isn't orphaned.",
                user_id,
                url,
            )
            continue
        try:
            delete_from_cloudinary(public_id)
        except Exception:
            unconfirmed.append(public_id)
            logger.exception(
                "Account deletion (user %s): provider delete failed for %s — aborting.",
                user_id,
                public_id,
            )

    if unconfirmed:
        logger.error(
            "Account deletion (user %s) aborted: %s of %s image(s) were not confirmed "
            "removed from the image provider. No rows were deleted; the request can be "
            "retried.",
            user_id,
            len(unconfirmed),
            len(photo_urls),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "image_deletion_failed",
                "message": (
                    "We couldn't delete all of your photos from our image provider, so "
                    "nothing was deleted — your account is unchanged. Please try again."
                ),
            },
        )

    db.delete(current_user)
    db.commit()

    return {
        "success": True,
        "message": "Account and all associated data have been permanently deleted.",
    }
