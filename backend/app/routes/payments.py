"""
Payments (Stripe) — the one place subscriptions get granted.

Honesty rule (§12.4): we never fake a charge. In production, checkout requires a
real STRIPE_SECRET_KEY; if it's missing the endpoint returns 503 with a clear
code so the client can show a waitlist instead of a broken checkout.
"""

from datetime import datetime, timedelta, timezone
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import AdminAction, StripeEvent, User
from app.schemas import (
    CancelSubscriptionIn,
    ChangePlanIn,
    CheckoutIn,
    CheckoutSessionOut,
    OfferOut,
)

logger = logging.getLogger(__name__)

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


def _is_coupon_error(exc: Exception) -> bool:
    """True when a Stripe rejection is about the discount we attached.

    Stripe words these as `InvalidRequestError: No such coupon:
    'FIRST_MONTH_1'` (sometimes with `param: discounts.0.coupon`). Matching on
    the text keeps the list-price retry from masking unrelated failures — a dead
    API key or a missing price must still surface as an error, not as a silently
    full-priced checkout.
    """
    text = f"{exc} {getattr(exc, 'param', None) or ''}".lower()
    return "coupon" in text or "discount" in text


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
            price_id = (item.get("price") or {}).get("id")
            if not price_id:
                # Stripe 2026+ invoice lines nest the price under
                # `pricing.price_details.price` instead of a top-level `price`.
                pricing = item.get("pricing") or {}
                price_id = (pricing.get("price_details") or {}).get("price")
            tier = _tier_for_price(price_id)
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


def _get(obj, key, default=None):
    """Read a field from a Stripe object whether it's a dict or an SDK object."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _sub_item_ids(sub) -> list:
    """Line-item ids on a subscription (the plan-switch API targets these)."""
    items = _get(sub, "items", None)
    data = _get(items, "data", None) if items is not None else None
    ids = []
    for item in data or []:
        item_id = _get(item, "id", None)
        if item_id:
            ids.append(item_id)
    return ids


def _obj_period_end(obj: dict) -> datetime | None:
    """Read the authoritative period end from a (webhook) subscription dict.

    Stripe's 2026+ API versions moved ``current_period_end`` from the top-level
    subscription object to each line item, so fall back to the first item's
    period end. This keeps upgrade/downgrade/renewal expiry accurate.
    """
    end = obj.get("current_period_end")
    if not end:
        items = obj.get("items") or {}
        data = items.get("data") or []
        if data:
            end = data[0].get("current_period_end")
    return _unix_to_datetime(end)


def _sub_period_end(sub) -> datetime | None:
    """The subscription's current period end (authoritative access expiry)."""
    end = _get(sub, "current_period_end", None)
    if not end:
        items = _get(sub, "items", None)
        data = _get(items, "data", None) if items is not None else None
        if data:
            end = _get(data[0], "current_period_end", None)
    return _unix_to_datetime(end)


def _list_active_subscriptions(stripe, user: User) -> list:
    """All non-terminal Stripe subscriptions for this customer (newest last).

    Covers the multiple-subscription edge case: a user who switched plans through
    the old checkout flow could have more than one live subscription, so cancel
    iterates the whole list while plan-change targets a single, explicit sub.
    """
    if not user.subscription_customer_id:
        return []
    try:
        data = stripe.Subscription.list(
            customer=user.subscription_customer_id, status="all", limit=100
        ).data
    except Exception:
        return []
    out = [
        s for s in (data or [])
        if _get(s, "status", "") not in ("canceled", "incomplete_expired")
    ]
    # Stripe returns oldest-first by default; put the most recent subscription first.
    out.sort(key=lambda s: _get(s, "created", 0) or 0, reverse=True)
    return out


def _status_response(user: User) -> dict:
    """Shared shape for cancel / resume / plan-change responses."""
    return {
        "success": True,
        "tier": user.subscription_tier or "free",
        "is_subscribed": bool(user.is_subscribed),
        "subscription_end": user.subscription_end.isoformat() if user.subscription_end else None,
        "cancel_at_period_end": bool(user.subscription_cancels_at_period_end),
    }


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
    def _create_session(apply_discount: bool):
        """Build the Checkout session, with or without the £1 coupon.

        `discounts` is resolved per attempt so a coupon Stripe refuses can be
        dropped without rebuilding anything else about the session.
        """
        return stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            subscription_data=subscription_data,
            discounts=discounts if apply_discount else None,
            success_url=(
                f"{settings.FRONTEND_URL}/upgrade/success"
                "?session_id={CHECKOUT_SESSION_ID}"
            ),
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

    try:
        session = _create_session(first_month)
    except Exception as exc:
        # One handler for every Stripe failure, deliberately not keyed on Stripe's
        # exception *classes* (those have moved between SDK majors): what decides
        # the fallback is whether the rejection names the coupon we attached.
        if not (first_month and _is_coupon_error(exc)):
            logger.exception(
                "Stripe rejected checkout (tier=%s annual=%s first_month=%s "
                "type=%s code=%s param=%s request_id=%s)",
                tier,
                payload.annual,
                first_month,
                type(exc).__name__,
                getattr(exc, "code", None),
                getattr(exc, "param", None),
                getattr(exc, "request_id", None),
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "code": "stripe_error",
                    "message": "Couldn't start checkout. Try again in a moment.",
                },
            )
        # The coupon exists in Stripe but Stripe won't apply it — typically it was
        # created in the test account while this deployment runs on live keys.
        # Losing the discount is survivable; losing the sale is not. Retry at list
        # price, log loudly, and report `offer_applied: false`. /payments/offer
        # already answers `verified: false` for the same misconfiguration, so the
        # UI is telling the customer the truth rather than promising £1.
        logger.warning(
            "£1 coupon %s was rejected by Stripe (%s: %s) — retrying checkout at list price",
            settings.STRIPE_FIRST_MONTH_COUPON_ID,
            type(exc).__name__,
            exc,
        )
        first_month = False
        try:
            session = _create_session(False)
        except Exception as retry_exc:
            logger.exception(
                "Stripe checkout failed again on the list-price retry (tier=%s type=%s)",
                tier,
                type(retry_exc).__name__,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "code": "stripe_error",
                    "message": "Couldn't start checkout. Try again in a moment.",
                },
            ) from retry_exc

    # `offer_applied` distinguishes "£1 session" from "the coupon was dropped and
    # this is a list-price session" — the client can't tell from the URL alone.
    return {"checkout_url": session.url, "offer_applied": first_month}


# ── Offer state + checkout receipt ──────────────────────────────────────────
# DEF-015: the UI used to hardcode "£1 first month" and, after paying, showed
# nothing at all — it landed on /dashboard?upgraded=1, which no frontend code
# ever handled. These two endpoints are the single source of truth for what the
# customer will be charged and what they actually were charged.

# Fallbacks used only when Stripe can't be reached: the launch configuration
# documented in config.py (Pro £9.99/month, £8.99 off for the first month).
_FALLBACK_PRO_MONTHLY_MINOR = 999
_FALLBACK_FIRST_MONTH_DISCOUNT_MINOR = 899


def _minor_to_major(minor: int | None) -> float | None:
    return None if minor is None else round(minor / 100, 2)


@router.get("/offer", response_model=OfferOut)
async def get_offer(user: User = Depends(get_current_user)):
    """Is this user eligible for the £1 first month, and at what prices?

    Always answers 200 — an unreachable Stripe is reported as
    `source: "config", verified: false` rather than an error, so the upgrade page
    can render *something* truthful instead of guessing at a price.
    """
    tier = (user.subscription_tier or "free").lower()
    coupon_id = settings.STRIPE_FIRST_MONTH_COUPON_ID

    regular_minor = _FALLBACK_PRO_MONTHLY_MINOR
    discount_minor = _FALLBACK_FIRST_MONTH_DISCOUNT_MINOR
    currency = "gbp"
    source = "config"
    verified = False

    if settings.STRIPE_SECRET_KEY:
        try:
            import stripe

            stripe.api_key = settings.STRIPE_SECRET_KEY
            price = stripe.Price.retrieve(_price_id("pro", False))
            regular_minor = int(_get(price, "unit_amount", 0) or 0) or regular_minor
            currency = str(_get(price, "currency", currency) or currency)
            if coupon_id:
                coupon = stripe.Coupon.retrieve(coupon_id)
                amount_off = _get(coupon, "amount_off", None)
                # A percentage coupon can't be shown as "£1 first month" — fall
                # back to the configured amount rather than inventing a price.
                if amount_off:
                    discount_minor = int(amount_off)
                    currency = str(_get(coupon, "currency", currency) or currency)
                source = "stripe"
                verified = True
        except Exception as exc:
            logger.warning(f"Offer lookup fell back to config: {exc}")

    if tier != "free":
        reason, eligible = "already_subscribed", False
    elif coupon_id and user.has_used_first_month_offer:
        reason, eligible = "used", False
    elif not coupon_id:
        reason, eligible = "not_configured", False
    else:
        reason, eligible = "eligible", True

    first_month_minor = max(regular_minor - discount_minor, 0)
    return {
        "eligible": eligible,
        "reason": reason,
        "tier": "pro",
        "interval": "month",
        "currency": currency.upper(),
        "first_month_amount": _minor_to_major(first_month_minor),
        "first_month_amount_minor": first_month_minor,
        "regular_amount": _minor_to_major(regular_minor),
        "regular_amount_minor": regular_minor,
        "source": source,
        "verified": verified,
    }


@router.get("/checkout/{session_id}", response_model=CheckoutSessionOut)
async def get_checkout_session(
    session_id: str,
    user: User = Depends(get_current_user),
):
    """What the customer was actually charged for a checkout session.

    Ownership-checked against `client_reference_id`/metadata, and read live from
    Stripe — no amount is inferred from the app's own price constants.
    """
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "payments_unconfigured",
                "message": "Payments aren't configured yet.",
            },
        )

    not_found = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "session_not_found", "message": "We couldn't find that checkout."},
    )

    try:
        import stripe

        stripe.api_key = settings.STRIPE_SECRET_KEY
        session = stripe.checkout.Session.retrieve(session_id, expand=["subscription"])
    except Exception as exc:
        logger.warning(f"Could not read checkout session {session_id}: {exc}")
        raise not_found

    metadata = _get(session, "metadata", None) or {}
    owner = _get(metadata, "user_id", None) or _get(session, "client_reference_id", None)
    if owner != user.id:
        raise not_found

    currency = str(_get(session, "currency", "gbp") or "gbp")
    amount_total = _get(session, "amount_total", None)
    total_details = _get(session, "total_details", None)
    amount_discount = _get(total_details, "amount_discount", None) if total_details else None
    # `_get` (attribute access) everywhere: a real StripeObject is not a dict, so
    # `metadata.get(...)` raises "…is a dict method, but a StripeObject is not a
    # dict" in production (caught by the live test-mode run, not by unit tests
    # that stub plain dicts).
    first_month = str(_get(metadata, "first_month_offer", "false")) == "true"

    # Next payment: the subscription's own recurring price + its period end.
    sub = _get(session, "subscription", None)
    next_amount = None
    interval = None
    next_date = None
    if sub is not None and not isinstance(sub, str):
        items = _get(sub, "items", None)
        data = _get(items, "data", None) if items is not None else None
        if data:
            price = _get(data[0], "price", None)
            if price is not None:
                next_amount = _get(price, "unit_amount", None)
                recurring = _get(price, "recurring", None)
                if recurring is not None:
                    interval = _get(recurring, "interval", None)
        next_date = _sub_period_end(sub)

    details = _get(session, "customer_details", None)
    email = _get(details, "email", None) if details is not None else None

    return {
        "status": str(_get(session, "status", "open")),
        "paid": str(_get(session, "payment_status", "")) in ("paid", "no_payment_required"),
        "tier": str(_get(metadata, "tier", None) or "pro"),
        "interval": interval,
        "currency": currency.upper(),
        "amount_charged": _minor_to_major(amount_total),
        "amount_charged_minor": amount_total,
        "amount_discount": _minor_to_major(amount_discount),
        "amount_discount_minor": amount_discount,
        "first_month_offer": first_month,
        "next_payment_amount": _minor_to_major(next_amount),
        "next_payment_amount_minor": next_amount,
        "next_payment_date": next_date,
        "email": email,
    }


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

    # The Stripe SDK returns a stripe.Event (with nested Stripe objects), not a
    # plain dict, so `.get()` doesn't exist on it. Normalize to a real dict once
    # so the `.get()` calls below — and the dict-based helpers like
    # _resolve_user/_tier_from_obj/_plan_days/_invoice_period_end — work uniformly.
    # (Guarded so a dict-like mock in tests still passes through unchanged.)
    if hasattr(event, "to_dict"):
        event = event.to_dict()

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
            if obj.get("subscription") and not user.subscription_stripe_id:
                user.subscription_stripe_id = obj["subscription"]
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
            if obj.get("id"):
                user.subscription_stripe_id = obj["id"]
            user.subscription_cancels_at_period_end = bool(obj.get("cancel_at_period_end"))
            grant_subscription(
                db, user, _tier_from_obj(obj),
                days=_plan_days(obj),
                end_at=_obj_period_end(obj),
                event_id=event_id,
            )

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
            user.subscription_cancels_at_period_end = False
            revoke_subscription(db, user, reason="stripe_subscription_deleted", event_id=event_id)

    # ── Plan switch / status change ────────────────────────────────────────
    elif event_type == "customer.subscription.updated":
        if user:
            if obj.get("id"):
                user.subscription_stripe_id = obj["id"]
            user.subscription_cancels_at_period_end = bool(obj.get("cancel_at_period_end"))
            status = obj.get("status")
            if status in REVOKE_STATUSES:
                revoke_subscription(db, user, reason=f"stripe_subscription_{status}", event_id=event_id)
            elif status in ("active", "trialing"):
                # `items` (expanded) reflects the *new* plan, so this correctly
                # follows the upgrades/downgrades Stripe reports; the period end
                # keeps `cancel_at_period_end` expiries accurate.
                grant_subscription(
                    db, user, _tier_from_obj(obj),
                    days=_plan_days(obj),
                    end_at=_obj_period_end(obj),
                    event_id=event_id,
                )
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


@router.post("/cancel")
async def cancel_subscription(
    payload: CancelSubscriptionIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel the current subscription.

    ``cancel_immediately=False`` (default) schedules cancellation for the end of
    the current billing period — access persists until ``subscription_end``.
    ``cancel_immediately=True`` deletes the subscription now and revokes access.
    """
    if not settings.STRIPE_SECRET_KEY:
        # No live Stripe (local/dev) — manage the local subscription
        # record directly so the user can always cancel, even before payments
        # are wired up. There's no Stripe subscription to modify here.
        if payload.cancel_immediately:
            revoke_subscription(db, user, reason="stripe_unconfigured_cancel_immediate")
        else:
            user.subscription_cancels_at_period_end = True
            db.commit()
            db.refresh(user)
        return _status_response(user)

    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    subs = _list_active_subscriptions(stripe, user)
    if not subs:
        # No live Stripe subscription, but the user may still be flagged paid
        # locally (or a missed webhook) — revoke to stay honest.
        revoke_subscription(db, user, reason="stripe_subscription_missing")
        return _status_response(user)

    try:
        period_end = None
        for sub in subs:
            sub_id = _get(sub, "id", None)
            if not sub_id:
                continue
            period_end = _sub_period_end(sub) or period_end
            if payload.cancel_immediately:
                stripe.Subscription.delete(sub_id)
            else:
                stripe.Subscription.modify(sub_id, cancel_at_period_end=True)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "stripe_error", "message": "Couldn't cancel your subscription. Try again in a moment."},
        )

    if payload.cancel_immediately:
        revoke_subscription(db, user, reason="stripe_cancel_immediate")
    else:
        user.subscription_cancels_at_period_end = True
        if period_end is not None:
            user.subscription_end = period_end
        db.commit()
        db.refresh(user)

    return _status_response(user)


@router.post("/resume")
async def resume_subscription(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Undo a scheduled cancellation (``cancel_at_period_end``) and keep access."""
    if not settings.STRIPE_SECRET_KEY:
        # No live Stripe (local/dev) — clear the local cancellation flag directly.
        user.subscription_cancels_at_period_end = False
        db.commit()
        db.refresh(user)
        return _status_response(user)

    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        for sub in _list_active_subscriptions(stripe, user):
            if _get(sub, "cancel_at_period_end", False):
                stripe.Subscription.modify(_get(sub, "id"), cancel_at_period_end=False)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "stripe_error", "message": "Couldn't resume your subscription. Try again in a moment."},
        )

    user.subscription_cancels_at_period_end = False
    db.commit()
    db.refresh(user)
    return _status_response(user)


@router.post("/change-plan")
async def change_plan(
    payload: ChangePlanIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Swap an existing subscription between Pro ↔ Elite (and monthly ↔ annual).

    Stripe prorates the difference on the same subscription, so there's never a
    second live subscription and access never lapses mid-switch.
    """
    tier = payload.tier.lower()
    if not settings.STRIPE_SECRET_KEY:
        # No live Stripe (local/dev) — swap the local subscription record directly,
        # so plan changes work before payments are wired.
        grant_subscription(db, user, tier, days=365 if payload.annual else 30)
        user.subscription_cancels_at_period_end = False
        db.commit()
        db.refresh(user)
        return _status_response(user)

    price_id = _price_id(tier, bool(payload.annual))
    if not price_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "price_missing", "message": "This plan's price isn't configured yet."},
        )
    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    subs = _list_active_subscriptions(stripe, user)
    if not subs:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "no_active_subscription", "message": "No active subscription to change — start a new plan instead."},
        )

    sub = None
    if user.subscription_stripe_id:
        sub = next((s for s in subs if _get(s, "id") == user.subscription_stripe_id), None)
    if sub is None:
        sub = subs[0]

    sub_id = _get(sub, "id")
    item_ids = _sub_item_ids(sub)
    period_end = _sub_period_end(sub)
    if not item_ids:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "subscription_not_changeable", "message": "This subscription can't be changed here right now."},
        )

    try:
        updated = stripe.Subscription.modify(
            sub_id,
            items=[{"id": item_ids[0], "price": price_id}],
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "stripe_error", "message": "Couldn't change your plan. Try again in a moment."},
        )

    # Stripe prorates on the same subscription and re-anchors the period end for
    # a monthly↔annual switch, so read the authoritative new expiry from the
    # modify response rather than the pre-switch period end (which would
    # otherwise under-grant annual upgrades by ~11 months).
    if hasattr(updated, "to_dict"):
        updated = updated.to_dict()
    new_period_end = _obj_period_end(updated) or period_end

    grant_subscription(
        db, user, tier,
        days=365 if payload.annual else 30,
        end_at=new_period_end,
    )
    user.subscription_cancels_at_period_end = False
    db.commit()
    db.refresh(user)
    return _status_response(user)

