"""
Entitlements endpoint — the client's read-only view of what the user can access.
Purely advisory for UX (lock chips + teasers); the backend is the real gate.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.services.entitlements_service import get_entitlements

router = APIRouter(tags=["Entitlements"])


@router.get("/entitlements")
async def entitlements(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the user's tier, usage limits, and the locked/unlocked feature list."""
    return get_entitlements(current_user, db)
