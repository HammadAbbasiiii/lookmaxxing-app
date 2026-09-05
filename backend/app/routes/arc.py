from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, is_premium, require_pro
from app.models import User
from app.services import arc_service

router = APIRouter(prefix="/arc", tags=["Arc"])


@router.get("/state")
async def arc_state(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return arc_service.get_state(current_user, db, premium=is_premium(current_user))


@router.post("/quests/{quest_id}/claim")
async def arc_claim_quest(
    quest_id: str,
    current_user: User = Depends(require_pro),
    db: Session = Depends(get_db),
):
    result = arc_service.claim_quest(current_user, db, quest_id)
    error = result.get("error")
    if error == "quest_not_found":
        raise HTTPException(status_code=404, detail={"code": "quest_not_found", "message": "Quest not found."})
    if error in ("already_claimed", "not_done"):
        raise HTTPException(
            status_code=409,
            detail={"code": error, "message": "Complete the task in today's check-in before claiming."},
        )
    return result


@router.get("/badges")
async def arc_badges(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"badges": arc_service.get_badges(current_user, db)}
