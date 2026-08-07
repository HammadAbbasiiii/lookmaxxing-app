"""
Profile Routes — User profile management.
Covers: GET/PUT profile, onboarding completion, account deletion (GDPR).
"""

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import UserResponse, ProfileUpdate, APIResponse
from app.dependencies import get_current_user

router = APIRouter(prefix="/profile", tags=["Profile"])


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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Mark the onboarding flow as completed.
    Called from iOS after the user finishes the initial setup wizard.
    """
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