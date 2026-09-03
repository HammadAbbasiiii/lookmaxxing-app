"""Admin product catalogue CRUD + audit log.

Every mutating action is recorded in `admin_actions` so the owner can see who
changed what, when. Products use soft-delete (`is_active=False`) so history and
existing recommendations are never lost.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.models import AdminAction, Product, User
from app.schemas import ProductCreate, ProductUpdate
from app.services.product_recommendation_service import _load_product_database

router = APIRouter(prefix="/admin", tags=["Admin"])

VALID_CATEGORIES = {
    "skin_quality", "jawline_definition", "eye_appeal",
    "facial_structure", "grooming", "general",
}
VALID_TIERS = {"budget", "mid_range", "premium"}


def _product_dict(p: Product) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "brand": p.brand,
        "category": p.category,
        "price": p.price,
        "currency": p.currency,
        "tier": p.tier,
        "image_url": p.image_url,
        "affiliate_url": p.affiliate_url,
        "description": p.description,
        "rating": p.rating,
        "review_count": p.review_count,
        "tags": p.tags or [],
        "recommended_for": p.recommended_for or [],
        "social_proof": p.social_proof,
        "commission": p.commission,
        "is_active": p.is_active,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


def _log_action(
    db: Session,
    admin: User,
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    details: Optional[dict] = None,
) -> None:
    db.add(
        AdminAction(
            admin_email=admin.email,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
        )
    )


def _validate(payload: dict) -> None:
    if "category" in payload and payload["category"] not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category. Must be one of: {', '.join(sorted(VALID_CATEGORIES))}",
        )
    if "tier" in payload and payload["tier"] not in VALID_TIERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier. Must be one of: {', '.join(sorted(VALID_TIERS))}",
        )


# ─────────────────────────────────────────────────────────────────────
# GET /admin/products — list + search + filter + pagination
# ─────────────────────────────────────────────────────────────────────
@router.get("/products")
async def list_products(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    search: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    tier: Optional[str] = Query(default=None),
    active: Optional[bool] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    q = db.query(Product)
    if search:
        like = f"%{search}%"
        q = q.filter(Product.name.ilike(like) | Product.brand.ilike(like))
    if category:
        q = q.filter(Product.category == category)
    if tier:
        q = q.filter(Product.tier == tier)
    if active is not None:
        q = q.filter(Product.is_active.is_(active))

    total = q.count()
    rows = q.order_by(Product.created_at.desc()).offset(offset).limit(limit).all()
    return {"success": True, "total": total, "products": [_product_dict(p) for p in rows]}


# ─────────────────────────────────────────────────────────────────────
# POST /admin/products — create
# ─────────────────────────────────────────────────────────────────────
@router.post("/products")
async def create_product(
    payload: ProductCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    data = payload.model_dump()
    _validate(data)
    try:
        product = Product(**data, is_active=True)
        db.add(product)
        db.flush()
        _log_action(db, admin, "create", "product", product.id, {"name": product.name})
        db.commit()
        db.refresh(product)
        return {"success": True, "product": _product_dict(product)}
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create product: {exc}")

# ─────────────────────────────────────────────────────────────────────
# PUT /admin/products/{id} — update (partial)
# ─────────────────────────────────────────────────────────────────────
@router.put("/products/{product_id}")
async def update_product(
    product_id: str,
    payload: ProductUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields provided for update.")
    _validate(data)

    try:
        for field, value in data.items():
            setattr(product, field, value)
        _log_action(db, admin, "update", "product", product.id, data)
        db.commit()
        db.refresh(product)
        return {"success": True, "product": _product_dict(product)}
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update product: {exc}")


# ─────────────────────────────────────────────────────────────────────
# DELETE /admin/products/{id} — soft delete (archive)
# ─────────────────────────────────────────────────────────────────────
@router.delete("/products/{product_id}")
async def delete_product(
    product_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    try:
        product.is_active = False
        _log_action(db, admin, "delete", "product", product.id, {"name": product.name})
        db.commit()
        return {"success": True, "product": _product_dict(product)}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to archive product: {exc}")


# ─────────────────────────────────────────────────────────────────────
# POST /admin/products/{id}/activate — re-enable an archived product
# ─────────────────────────────────────────────────────────────────────
@router.post("/products/{product_id}/activate")
async def activate_product(
    product_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    try:
        product.is_active = True
        _log_action(db, admin, "activate", "product", product.id, {"name": product.name})
        db.commit()
        return {"success": True, "product": _product_dict(product)}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to activate product: {exc}")

# ─────────────────────────────────────────────────────────────────────
# POST /admin/products/import — bulk import from JSON (idempotent upsert)
# ─────────────────────────────────────────────────────────────────────
@router.post("/products/import")
async def import_products(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    source = _load_product_database()
    if not source:
        raise HTTPException(status_code=400, detail="No products found in JSON source.")

    created, updated = 0, 0
    try:
        for sp in source:
            existing = db.query(Product).filter(Product.id == sp.get("id")).first()
            fields = {
                "name": sp.get("name", ""),
                "brand": sp.get("brand"),
                "category": sp.get("category", "general"),
                "price": float(sp.get("price") or 0),
                "currency": sp.get("currency", "USD"),
                "tier": sp.get("tier", "mid_range"),
                "image_url": sp.get("image_url"),
                "affiliate_url": sp.get("affiliate_link"),
                "description": sp.get("social_proof"),
                "rating": sp.get("rating"),
                "review_count": int(sp.get("reviews_count") or 0),
                "tags": sp.get("tags"),
                "recommended_for": sp.get("recommended_for"),
                "social_proof": sp.get("social_proof"),
            }
            if existing:
                for f, v in fields.items():
                    setattr(existing, f, v)
                updated += 1
            else:
                db.add(Product(id=sp.get("id"), **fields, is_active=True))
                created += 1
        _log_action(db, admin, "import", "product", None, {"created": created, "updated": updated})
        db.commit()
        return {"success": True, "created": created, "updated": updated}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Import failed: {exc}")


# ─────────────────────────────────────────────────────────────────────
# GET /admin/activity — audit log of admin actions
# ─────────────────────────────────────────────────────────────────────
@router.get("/activity")
async def admin_activity(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    total = db.query(func.count(AdminAction.id)).scalar() or 0
    rows = (
        db.query(AdminAction)
        .order_by(AdminAction.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "success": True,
        "total": total,
        "actions": [
            {
                "id": a.id,
                "admin_email": a.admin_email,
                "action": a.action,
                "entity_type": a.entity_type,
                "entity_id": a.entity_id,
                "details": a.details,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in rows
        ],
    }


