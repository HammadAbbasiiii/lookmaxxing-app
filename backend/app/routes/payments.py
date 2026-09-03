"""
Payments (Stripe) — the one place subscriptions get granted.

Honesty rule (§12.4): we never fake a charge. In production, checkout requires a
real STRIPE_SECRET_KEY; if it's missing the endpoint returns 503 with a clear
code so the client can show a waitlist instead of a broken checkout.

A test-only upgrade endpoint is available when `ALLOW_TEST_PAYMENTS=1` AND
`ENVIRONMENT != "production"`, so the owner can preview Pro/Elite locally without
touching Stripe.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import AdminAction, User
from app.schemas import CheckoutIn, TestUpgradeIn

router = APIRouter(prefix="/payments", tags=["Payments"])


def _price_id(tier: str, annual: bool) -> str:
    mapping = {
        ("pro", True): settings.STRIPE_PRICE_PRO_ANNUAL,
        ("pro", False): settings.STRIPE_PRICE_PRO_MONTHLY,
        ("elite", True): settings.STRIPE_PRICE_ELITE_ANNUAL,
        ("elite", False): settings.STRIPE_PRICE_ELITE_MONTHLY,
    }
    return mapping.get((tier, bool(annual)), "")


def grant_subscription(db: Session, user: User, tier: str, days: int = 365) -> User:
    """Flip a user onto a paid tier and write an audit row."""
    user.subscription_tier = tier
    user.is_subscribed = True
    user.subscription_start = datetime.utcnow()
    user.subscription_end = datetime.utcnow() + timedelta(days=days)
    db.add(
        AdminAction(
            admin_email=user.email,
            action="grant_subscription",
            entity_type="user",
            entity_id=user.id,
            details={"tier": tier, "days": days},
        )
    )
    db.commit()
    db.refresh(user)
    return user


@router.post("/checkout")
async def create_checkout(
    payload: CheckoutIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Checkout session and return its URL."""
    tier = payload.tier.lower()
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "payments_unconfigured",
                "message": "Payments aren't configured yet — join the waitlist and we'll email you.",
            },
        )

    try:
        import stripe  # noqa: F401
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "payments_unconfigured",
                "message": "Payments aren't configured yet — join the waitlist and we'll email you.",
            },
        )

    price_id = _price_id(tier, bool(payload.annual))
    if not price_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "price_missing", "message": "This plan isn't available yet."},
        )

    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{settings.FRONTEND_URL}/dashboard?upgraded=1",
            cancel_url=f"{settings.FRONTEND_URL}/upgrade",
            client_reference_id=user.id,
            customer_email=user.email,
            metadata={"user_id": user.id, "tier": tier, "annual": str(payload.annual)},
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "stripe_error", "message": "Couldn't start checkout. Try again in a moment."},
        )

    return {"checkout_url": session.url}


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """Fulfill a subscription when Stripe confirms payment."""
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=503,
            detail={"code": "payments_unconfigured", "message": "Webhook not configured."},
        )

    try:
        import stripe
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail={"code": "payments_unconfigured", "message": "Webhook not configured."},
        )

    stripe.api_key = settings.STRIPE_SECRET_KEY
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig, settings.STRIPE_WEBHOOK_SECRET)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook signature.")

    if event["type"] in ("checkout.session.completed", "invoice.paid", "customer.subscription.created"):
        obj = event["data"]["object"]
        metadata = obj.get("metadata") or {}
        user_id = metadata.get("user_id") or obj.get("client_reference_id")
        tier = metadata.get("tier") or "pro"
        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                grant_subscription(db, user, tier if tier in ("pro", "elite") else "pro", 365)

    return {"success": True}


@router.post("/test-upgrade")
async def test_upgrade(
    payload: TestUpgradeIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Dev/test only: flip the current user onto a paid tier without charging.

    Refuses to run in production regardless of the flag, and refuses to run
    anywhere unless ALLOW_TEST_PAYMENTS=1.
    """
    tier = payload.tier.lower()
    allowed = settings.ALLOW_TEST_PAYMENTS and settings.ENVIRONMENT != "production"
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "test_payments_disabled",
                "message": "Test upgrades are disabled in production.",
            },
        )
    grant_subscription(db, user, tier, 365)
    return {
        "success": True,
        "tier": tier,
        "is_subscribed": user.is_subscribed,
        "subscription_end": user.subscription_end.isoformat() if user.subscription_end else None,
    }

