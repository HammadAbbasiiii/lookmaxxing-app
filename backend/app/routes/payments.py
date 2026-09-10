"""
Payments (Stripe) — the one place subscriptions get granted.

Honesty rule (§12.4): we never fake a charge. In production, checkout requires a
real STRIPE_SECRET_KEY; if it's missing the endpoint returns 503 with a clear
code so the client can show a waitlist instead of a broken checkout.

A test-only upgrade endpoint is available when `ALLOW_TEST_PAYMENTS=1` AND
`ENVIRONMENT != "production"`, so the owner can preview Pro/Elite locally without
touching Stripe.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import AdminAction, StripeEvent, User
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


def _tier_for_price(price_id: str | None) -> str | None:
    """Reverse-map a Stripe price id back to a tier (for subscription updates).

    Used by the webhook's ``customer.subscription.updated`` handler so a
    downgrade/upgrade (Pro ↔ Elite) is reflected without trusting the client.
    """
    if not price_id:
        return None
    mapping = {
        settings.STRIPE_PRICE_PRO_MONTHLY: "pro",
        settings.STRIPE_PRICE_PRO_ANNUAL: "pro",
        settings.STRIPE_PRICE_ELITE_MONTHLY: "elite",
        settings.STRIPE_PRICE_ELITE_ANNUAL: "elite",
    }
    return mapping.get(price_id)


def _unix_to_datetime(ts) -> datetime | None:
    """Convert a Stripe unix timestamp to a naive UTC datetime (the app stores
    naive UTC everywhere, so we match that convention)."""
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).replace(tzinfo=None)
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def _plan_days(obj: dict) -> int:
    """Days covered by a subscription line item (365 for annual, 30 otherwise)."""
    items = obj.get("items") or {}
    data = items.get("data") or []
    if data:
        plan = (data[0].get("plan") or {}) or {}
        if plan.get("interval") == "year":
            return 365
    return 30


def _invoice_period_end(obj: dict) -> datetime | None:
    """The invoice's `period.end` — the authoritative new subscription expiry."""
    lines = obj.get("lines") or {}
    data = lines.get("data") or []
    if data:
        period = data[0].get("period") or {}
        if period.get("end"):
            return _unix_to_datetime(period["end"])
    if obj.get("period_end"):
        return _unix_to_datetime(obj["period_end"])
    return None


def _tier_from_obj(obj: dict, default: str = "pro") -> str:
    """Best-effort tier for a Stripe object.

    The line item's price id is the most authoritative signal of the *current*
    plan (it reflects upgrades/downgrades the checkout-time metadata does not),
    so it wins over `metadata.tier`.
    """
    for container in ("items", "lines"):
        data = (obj.get(container) or {}).get("data") or []
        for item in data:
            tier = _tier_for_price((item.get("price") or {}).get("id"))
            if tier:
                return tier
    metadata = obj.get("metadata") or {}
    tier = metadata.get("tier")
    if tier in ("pro", "elite"):
        return tier
    return default if default in ("pro", "elite") else "pro"


def _resolve_user(db: Session, obj: dict) -> User | None:
    """Map a Stripe object back to a user.

    Checkout sessions and subscriptions carry `metadata.user_id` (and sessions
    carry `client_reference_id`). Invoices carry neither, so we fall back to the
    Stripe customer id we persist on the user at fulfillment time.
    """
    metadata = obj.get("metadata") or {}
    user_id = metadata.get("user_id") or obj.get("client_reference_id")
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            return user
    customer = obj.get("customer")
    if customer:
        return db.query(User).filter(User.subscription_customer_id == customer).first()
    return None


def grant_subscription(
    db: Session,
    user: User,
    tier: str,
    days: int = 365,
    end_at: datetime | None = None,
    event_id: str | None = None,
) -> User:
    """Grant (or extend) a paid tier and audit the change.

    Idempotent for Stripe redeliveries: already on `tier` with an equal-or-later
    expiry → no-op, so a retried event neither spams the audit log nor shortens a
    valid subscription. Renewals extend `subscription_end` without a new audit row.
    """
    now = datetime.utcnow()
    new_end = end_at or (now + timedelta(days=days))
    tier_changed = (user.subscription_tier or "free").lower() != tier

    if (
        not tier_changed
        and user.is_subscribed
        and user.subscription_end is not None
        and user.subscription_end >= new_end
    ):
        return user

    user.subscription_tier = tier
    user.is_subscribed = True
    if tier_changed or user.subscription_start is None:
        user.subscription_start = now
    if user.subscription_end is None or new_end >= user.subscription_end:
        user.subscription_end = new_end

    if tier_changed:
        db.add(
            AdminAction(
                admin_email=user.email,
                action="grant_subscription",
                entity_type="user",
                entity_id=user.id,
                details={
                    "tier": tier,
                    "days": days if end_at is None else None,
                    "event_id": event_id,
                },
            )
        )
    db.commit()
    db.refresh(user)
    return user


def revoke_subscription(
    db: Session,
    user: User,
    reason: str = "subscription_cancelled",
    event_id: str | None = None,
) -> User:
    """Revoke a paid tier — drop to Free and write an audit row.

    Fired on Stripe ``customer.subscription.deleted`` / ``.updated`` (status
    ``canceled``, ``unpaid``, ``incomplete_expired``) so access is revoked the
    moment a customer cancels or a payment lapses. Honesty rule §12.4: we never
    keep gating a user who is no longer paying.
    """
    if (user.subscription_tier or "free").lower() == "free" and not user.is_subscribed:
        return user  # already free — idempotent for redelivered events

    user.subscription_tier = "free"
    user.is_subscribed = False
    user.subscription_end = datetime.utcnow()
    db.add(
        AdminAction(
            admin_email=user.email,
            action="revoke_subscription",
            entity_type="user",
            entity_id=user.id,
            details={"reason": reason, "event_id": event_id},
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
            detail={"code": "price_missing", "message": "This plan's price isn't configured yet."},
        )

    # 7-day free trial on Elite — Stripe collects the card up front and charges
    # after the trial ends (loss aversion: the user is already "invested").
    trial_days = None
    if tier == "elite" and settings.STRIPE_ELITE_TRIAL_DAYS > 0:
        trial_days = settings.STRIPE_ELITE_TRIAL_DAYS

    # "£1 first month" — Pro monthly only, one-time. The coupon must exist in
    # Stripe; if it's missing (or already used) we silently fall back to the
    # regular price — we never fake a discount.
    discounts = None
    first_month = False
    if payload.first_month_offer and tier == "pro" and not payload.annual:
        if not user.has_used_first_month_offer and settings.STRIPE_FIRST_MONTH_COUPON_ID:
            discounts = [{"coupon": settings.STRIPE_FIRST_MONTH_COUPON_ID}]
            first_month = True

    # Carry the user id + tier on the *subscription* itself (not just the
    # checkout session) so lifecycle events — cancellation, downgrade, plan
    # switch — can be resolved back to this user inside the webhook.
    subscription_data = {"metadata": {"user_id": user.id, "tier": tier}}
    if trial_days:
        subscription_data["trial_period_days"] = trial_days

    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY
    # Reuse the Stripe customer when we already know them so every subscription
    # lands on one customer object (cleaner billing + Customer Portal).
    customer_kwargs = (
        {"customer": user.subscription_customer_id}
        if user.subscription_customer_id
        else {"customer_email": user.email}
    )
    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            subscription_data=subscription_data,
            discounts=discounts,
            success_url=f"{settings.FRONTEND_URL}/dashboard?upgraded=1",
            cancel_url=f"{settings.FRONTEND_URL}/upgrade",
            client_reference_id=user.id,
            metadata={
                "user_id": user.id,
                "tier": tier,
                "annual": str(payload.annual),
                "first_month_offer": "true" if first_month else "false",
            },
            **customer_kwargs,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "stripe_error", "message": "Couldn't start checkout. Try again in a moment."},
        )

    return {"checkout_url": session.url}


# Event types we act on. Anything else is acknowledged (200) so Stripe stops
# retrying, but ignored — no surprise event type can reach our handlers.
HANDLED_EVENTS = {
    "checkout.session.completed",
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.paid",
    "invoice.payment_failed",
}

# Stripe states that mean "the customer is no longer paying". `past_due` is
# deliberately absent — that is the grace period while Stripe retries the card;
# we revoke only after retries are exhausted (`unpaid`) or the sub is gone.
REVOKE_STATUSES = ("canceled", "unpaid", "incomplete_expired")


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """Fulfill, extend, or revoke a subscription when Stripe confirms an event."""
    if not settings.STRIPE_WEBHOOK_SECRET or not settings.STRIPE_SECRET_KEY:
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

    # 1) Signature — the only proof the event genuinely came from Stripe.
    try:
        event = stripe.Webhook.construct_event(payload, sig, settings.STRIPE_WEBHOOK_SECRET)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook signature.")

    event_type = event.get("type")

    # 2) Allowlist — ignore anything we don't explicitly handle.
    if event_type not in HANDLED_EVENTS:
        return {"success": True, "ignored": event_type}

    # 3) Never let a sandbox/test-mode event grant live access.
    if settings.ENVIRONMENT == "production" and event.get("livemode") is not True:
        raise HTTPException(status_code=400, detail="Test-mode event rejected in production.")

    # 4) Idempotency — Stripe redelivers events; process each event id once.
    event_id = event.get("id")
    if event_id:
        seen = db.query(StripeEvent).filter(StripeEvent.event_id == event_id).first()
        if seen:
            return {"success": True, "duplicate": True}

    obj = event.get("data", {}).get("object", {}) or {}
    user = _resolve_user(db, obj)

    # ── Fulfillment: new subscription confirmed ────────────────────────────
    if event_type == "checkout.session.completed":
        if user:
            if obj.get("customer") and not user.subscription_customer_id:
                user.subscription_customer_id = obj["customer"]
            metadata = obj.get("metadata") or {}
            tier = _tier_from_obj(obj)
            days = 365 if metadata.get("annual") == "true" else 30
            grant_subscription(db, user, tier, days=days, event_id=event_id)
            # The one-time "£1 first month" offer is now consumed.
            if metadata.get("first_month_offer") == "true" and not user.has_used_first_month_offer:
                user.has_used_first_month_offer = True
                db.commit()

    elif event_type == "customer.subscription.created":
        if user:
            if obj.get("customer") and not user.subscription_customer_id:
                user.subscription_customer_id = obj["customer"]
            grant_subscription(db, user, _tier_from_obj(obj), days=_plan_days(obj), event_id=event_id)

    # ── Renewal: invoice paid → extend the term (authoritative period end) ──
    elif event_type == "invoice.paid":
        if user:
            if obj.get("customer") and not user.subscription_customer_id:
                user.subscription_customer_id = obj["customer"]
            end_at = _invoice_period_end(obj)
            current = (user.subscription_tier or "free").lower()
            if current in ("pro", "elite"):
                # Extend the expiry only; an invoice carries no tier metadata and
                # we must never downgrade an active subscriber on a renewal.
                grant_subscription(db, user, current, days=365, end_at=end_at, event_id=event_id)
            else:
                # Re-subscribe after a gap — derive the tier from the invoice.
                grant_subscription(db, user, _tier_from_obj(obj), days=365, end_at=end_at, event_id=event_id)

    # ── Revocation: subscription gone → drop to Free ───────────────────────
    elif event_type == "customer.subscription.deleted":
        if user:
            revoke_subscription(db, user, reason="stripe_subscription_deleted", event_id=event_id)

    # ── Plan switch / status change ────────────────────────────────────────
    elif event_type == "customer.subscription.updated":
        if user:
            status = obj.get("status")
            if status in REVOKE_STATUSES:
                revoke_subscription(db, user, reason=f"stripe_subscription_{status}", event_id=event_id)
            elif status in ("active", "trialing"):
                # `items` (expanded) reflects the *new* plan, so this correctly
                # follows the upgrades/downgrades Stripe reports.
                grant_subscription(db, user, _tier_from_obj(obj), days=_plan_days(obj), event_id=event_id)
            # `past_due` / `incomplete` → leave access in place; Stripe retries.

    # ── Payment failure → audit only; Stripe Smart Retries handle recovery ──
    elif event_type == "invoice.payment_failed":
        if user:
            db.add(
                AdminAction(
                    admin_email=user.email,
                    action="invoice_payment_failed",
                    entity_type="user",
                    entity_id=user.id,
                    details={"event_id": event_id, "invoice": obj.get("id")},
                )
            )
            db.commit()

    # Record the event id only AFTER successful processing, so a crash mid-way
    # lets Stripe redeliver and us reprocess (handlers are idempotent).
    if event_id:
        db.add(StripeEvent(event_id=event_id, type=event_type))
        db.commit()

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

