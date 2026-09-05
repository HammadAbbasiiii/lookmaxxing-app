from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_elite
from app.models import User
from app.services import glow_service

router = APIRouter(prefix="/glow", tags=["Glow"])


@router.get("/state")
async def glow_state(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return glow_service.get_glow_state(current_user, db)


@router.post("/open")
async def glow_open(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return glow_service.open_today(current_user, db)


@router.get("/reveals")
async def glow_reveals(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return glow_service.get_reveals(current_user, db)


@router.get("/full-reveal")
async def glow_full_reveal(current_user: User = Depends(require_elite), db: Session = Depends(get_db)):
    return {"full_reveal": glow_service.get_full_reveal(current_user, db)}
