"""
Product Recommendation API

Endpoints:
- GET /api/v1/products/recommendations — personalised recommendations based on user's latest analysis
- GET /api/v1/products/category/{category} — browse all products in a category
- GET /api/v1/products/categories — list available categories

All endpoints require authentication.
Recommendations are generated from the user's most recent photo analysis category breakdown.
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Photo
from app.dependencies import get_current_user
from app.services.product_recommendation_service import (
    get_product_recommendations,
    get_products_by_category,
    get_categories,
)

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("/recommendations")
async def get_recommendations(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    tier: str = Query(default="mid_range", description="Budget tier preference: budget, mid_range, or premium"),
    max_results: int = Query(default=8, ge=1, le=12, description="Max products to return"),
):
    """
    Get personalised product recommendations based on the user's latest face analysis.

    Identifies the 3 weakest categories from the most recent photo analysis and recommends
    products targeting those areas. Products are ranked by rating × review count and
    filtered by the user's preferred budget tier.

    Returns an empty list with a fallback message if no analysis has been done yet.
    """
    # Get the latest analysed photo with category breakdown
    latest_photo = (
        db.query(Photo)
        .filter(
            Photo.user_id == user.id,
            Photo.analysis_details.isnot(None),
        )
        .order_by(Photo.captured_at.desc())
        .first()
    )

    if not latest_photo or not latest_photo.analysis_details:
        return {
            "success": True,
            "recommendations": [],
            "total": 0,
            "message": "No face analysis found. Upload and analyse a photo first to get personalised recommendations.",
        }

    # Extract category breakdown from analysis_details
    analysis = latest_photo.analysis_details
    category_breakdown = {}

    # Try to get category_breakdown directly if present
    if isinstance(analysis, dict) and "category_breakdown" in analysis:
        category_breakdown = analysis["category_breakdown"]
    else:
        # Fall back to individual score fields on the photo
        category_breakdown = {
            "skin_quality": latest_photo.skin_score or 50,
            "jawline_definition": latest_photo.jawline_score or 50,
            "eye_appeal": latest_photo.eye_score or 50,
            "facial_structure": getattr(latest_photo, 'nose_score', None) or 50,
        }

    overall_score = latest_photo.score or 50
    recommended = get_product_recommendations(
        category_breakdown=category_breakdown,
        overall_score=overall_score,
        user_profile={"id": user.id, "email": user.email},
        max_products=max_results,
        budget_tier=tier if tier in ("budget", "mid_range", "premium") else "mid_range",
    )

    if not recommended:
        return {
            "success": True,
            "recommendations": [],
            "total": 0,
            "message": "Product recommendations coming soon.",
        }

    return {
        "success": True,
        "recommendations": recommended,
        "total": len(recommended),
        "message": f"Based on your analysis, these {len(recommended)} products target your weakest areas.",
    }


@router.get("/category/{category}")
async def get_category_products(
    category: str,
    tier: str = Query(default=None, description="Optional: filter by budget tier"),
    user: User = Depends(get_current_user),
):
    """
    Browse all products in a specific category.

    Valid categories: skin_quality, jawline_definition, eye_appeal,
    facial_structure, grooming, general

    Optionally filter by budget tier: budget, mid_range, premium
    """
    valid_categories = {
        "skin_quality", "jawline_definition", "eye_appeal",
        "facial_structure", "grooming", "general",
    }
    if category not in valid_categories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category '{category}'. Must be one of: {', '.join(sorted(valid_categories))}",
        )

    valid_tiers = {None, "budget", "mid_range", "premium"}
    if tier not in valid_tiers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier '{tier}'. Must be one of: budget, mid_range, premium",
        )

    products = get_products_by_category(category, tier=tier)

    if not products:
        return {
            "success": True,
            "category": category,
            "products": [],
            "total": 0,
            "message": f"No products found in category '{category}'{' with tier ' + tier if tier else ''}.",
        }

    return {
        "success": True,
        "category": category,
        "products": products,
        "total": len(products),
        "tier_filter": tier,
    }


@router.get("/categories")
async def list_categories(
    user: User = Depends(get_current_user),
):
    """
    List all product categories with display names and product counts.

    Useful for building browse UIs in the iOS app.
    """
    cats = get_categories()
    return {
        "success": True,
        "categories": cats,
        "total": len(cats),
    }