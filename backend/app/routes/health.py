from fastapi import APIRouter
from datetime import datetime

router = APIRouter()

@router.get("/health")
async def health_check():
    """Check if the API is running"""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "lookmaxx-api"
    }

@router.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to LookMaxx API",
        "version": "0.1.0",
        "docs": "/docs"
    }