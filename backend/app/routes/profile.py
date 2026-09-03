"""
Profile Routes — User profile management.
Covers: GET/PUT profile, onboarding completion, account deletion (GDPR).
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import UserResponse, ProfileUpdate, OnboardingUpdate
from app.dependencies import get_current_user

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
    This is GDPR-compliant — cascades to photos, plans, checkins.
    """
    db.delete(current_user)
    db.commit()

    return {
        "success": True,
        "message": "Account and all associated data have been permanently deleted.",
    }