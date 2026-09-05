from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_elite
from app.models import User
from app.services import glowups_service

router = APIRouter(prefix="/glowups", tags=["Glow-Ups"])


class ConsentRequest(BaseModel):
    share_enabled: bool


@router.get("/feed")
async def glowups_feed(
    cursor: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return glowups_service.get_feed(current_user, db, cursor=cursor)


@router.post("/consent")
async def glowups_consent(
    payload: ConsentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return glowups_service.set_consent(current_user, db, payload.share_enabled)


@router.get("/consent")
async def glowups_get_consent(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return glowups_service.get_consent(current_user, db)


@router.get("/movie")
async def glowups_movie(current_user: User = Depends(require_elite), db: Session = Depends(get_db)):
    return glowups_service.get_movie(current_user, db)


@router.post("/movie/generate")
async def glowups_generate(current_user: User = Depends(require_elite), db: Session = Depends(get_db)):
    return glowups_service.generate_movie(current_user, db)


@router.post("/items/{item_id}/report")
async def glowups_report(
    item_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return glowups_service.report_item(current_user, db, item_id)
