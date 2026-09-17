"""Payment lifecycle suite (§12): grant, revoke, downgrade, and the $1 first-month offer.

Covers the pieces of the Stripe flow that run locally without a Stripe account:
  - price-id → tier reverse mapping (for subscription.updated downgrades/upgrades)
  - grant_subscription / revoke_subscription helpers + their audit rows
  - webhook fulfillment (checkout.session.completed) incl. consuming the $1 offer
  - webhook revocation (customer.subscription.deleted)
  - webhook plan-switch sync (customer.subscription.updated)
  - webhook signature rejection
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.config import settings
from app.dependencies import get_password_hash, is_premium
from app.models import AdminAction, StripeEvent, User
from app.routes.payments import (
    _tier_for_price,
    grant_subscription,
    revoke_subscription,
)
from app.services.entitlements_service import get_tier


def _make_user(db_session, email="pay@example.com", tier="free"):
    u = User(
        email=email,
        hashed_password=get_password_hash("pass1234"),
        full_name="Pay User",
        is_subscribed=tier != "free",
        subscription_tier=tier,
        current_day=0,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


class TestPriceTierMapping:
    def test_tier_for_price_maps_all_four_prices(self, monkeypatch):
        monkeypatch.setattr(settings, "STRIPE_PRICE_PRO_MONTHLY", "price_pro_monthly")
        monkeypatch.setattr(settings, "STRIPE_PRICE_PRO_ANNUAL", "price_pro_annual")
        monkeypatch.setattr(settings, "STRIPE_PRICE_ELITE_MONTHLY", "price_elite_monthly")
        monkeypatch.setattr(settings, "STRIPE_PRICE_ELITE_ANNUAL", "price_elite_annual")

        assert _tier_for_price("price_pro_monthly") == "pro"
        assert _tier_for_price("price_pro_annual") == "pro"
        assert _tier_for_price("price_elite_monthly") == "elite"
        assert _tier_for_price("price_elite_annual") == "elite"

    def test_tier_for_price_unknown_or_missing(self, monkeypatch):
        monkeypatch.setattr(settings, "STRIPE_PRICE_PRO_MONTHLY", "price_pro_monthly")
        assert _tier_for_price("price_unknown") is None
        assert _tier_for_price(None) is None
        assert _tier_for_price("") is None


class TestSubscriptionLifecycle:
    def test_grant_subscription_sets_tier_and_writes_audit(self, db_session):
        u = _make_user(db_session)
        grant_subscription(db_session, u, "pro", 365)

        assert u.subscription_tier == "pro"
        assert u.is_subscribed is True
        assert u.subscription_end is not None

        audit = (
            db_session.query(AdminAction)
            .filter_by(entity_id=u.id, action="grant_subscription")
            .first()
        )
        assert audit is not None
        assert audit.details["tier"] == "pro"

    def test_revoke_subscription_resets_to_free_and_writes_audit(self, db_session):
        u = _make_user(db_session, tier="pro")
        revoke_subscription(db_session, u, reason="stripe_subscription_deleted")

        assert u.subscription_tier == "free"
        assert u.is_subscribed is False

        audit = (
            db_session.query(AdminAction)
            .filter_by(entity_id=u.id, action="revoke_subscription")
            .first()
        )
        assert audit is not None
        assert audit.details["reason"] == "stripe_subscription_deleted"


class TestStripeWebhook:
    def _post_webhook(self, client, event_type, obj, monkeypatch, event_id=None):
        import stripe

        monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_test")
        monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test")

        def _construct_event(payload, sig, secret):
            event = {"type": event_type, "data": {"object": obj}}
            if event_id:
                event["id"] = event_id
            return event

        monkeypatch.setattr(stripe.Webhook, "construct_event", _construct_event)
        return client.post(
            "/api/v1/payments/webhook",
            json={},
            headers={"stripe-signature": "sig"},
        )

    def test_checkout_completed_grants_and_consumes_first_month_offer(
        self, client, db_session, monkeypatch
    ):
        u = _make_user(db_session)
        self._post_webhook(
            client,
            "checkout.session.completed",
            {
                "metadata": {"user_id": u.id, "tier": "pro", "first_month_offer": "true"},
                "customer": "cus_123",
                "subscription": "sub_123",
            },
            monkeypatch,
        )

        db_session.refresh(u)
        assert u.subscription_tier == "pro"
        assert u.is_subscribed is True
        assert u.has_used_first_month_offer is True
        assert u.subscription_customer_id == "cus_123"
        assert u.subscription_stripe_id == "sub_123"

    def test_subscription_created_syncs_stripe_id_cancel_flag_and_term(
        self, client, db_session, monkeypatch
    ):
        u = _make_user(db_session)
        period_end_ts = int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp())
        monkeypatch.setattr(settings, "STRIPE_PRICE_PRO_MONTHLY", "price_pro_monthly")

        self._post_webhook(
            client,
            "customer.subscription.created",
            {
                "id": "sub_123",
                "customer": "cus_123",
                "status": "active",
                "cancel_at_period_end": True,
                "current_period_end": period_end_ts,
                "metadata": {"user_id": u.id},
                "items": {"data": [{"price": {"id": "price_pro_monthly"}}]},
            },
            monkeypatch,
        )

        db_session.refresh(u)
        assert u.subscription_stripe_id == "sub_123"
        assert u.subscription_customer_id == "cus_123"
        assert u.subscription_cancels_at_period_end is True
        assert u.subscription_tier == "pro"
        assert u.subscription_end is not None

    def test_subscription_deleted_revokes_access(self, client, db_session, monkeypatch):
        u = _make_user(db_session, tier="pro")
        res = self._post_webhook(
            client,
            "customer.subscription.deleted",
            {"metadata": {"user_id": u.id}},
            monkeypatch,
        )

        assert res.status_code == 200
        db_session.refresh(u)
        assert u.subscription_tier == "free"
        assert u.is_subscribed is False

    def test_subscription_updated_canceled_status_revokes(self, client, db_session, monkeypatch):
        u = _make_user(db_session, tier="pro")
        self._post_webhook(
            client,
            "customer.subscription.updated",
            {"metadata": {"user_id": u.id}, "status": "canceled"},
            monkeypatch,
        )

        db_session.refresh(u)
        assert u.subscription_tier == "free"
        assert u.is_subscribed is False

    def test_subscription_updated_syncs_tier_from_price(self, client, db_session, monkeypatch):
        u = _make_user(db_session, tier="pro")
        monkeypatch.setattr(settings, "STRIPE_PRICE_ELITE_MONTHLY", "price_elite_monthly")

        self._post_webhook(
            client,
            "customer.subscription.updated",
            {
                "metadata": {"user_id": u.id, "tier": "elite"},
                "status": "active",
                "items": {"data": [{"price": {"id": "price_elite_monthly"}}]},
            },
            monkeypatch,
        )

        db_session.refresh(u)
        assert u.subscription_tier == "elite"

    def test_webhook_invalid_signature_returns_400(self, client, monkeypatch):
        import stripe

        monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_test")
        monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test")

        def _raise(payload, sig, secret):
            raise Exception("bad signature")

        monkeypatch.setattr(stripe.Webhook, "construct_event", _raise)
        res = client.post(
            "/api/v1/payments/webhook",
            json={},
            headers={"stripe-signature": "sig"},
        )
        assert res.status_code == 400

    def test_invoice_paid_extends_term_and_preserves_tier(self, client, db_session, monkeypatch):
        u = _make_user(db_session, tier="pro")
        u.subscription_customer_id = "cus_123"
        db_session.commit()

        future_ts = int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp())
        res = self._post_webhook(
            client,
            "invoice.paid",
            {"customer": "cus_123", "id": "in_1", "period_end": future_ts},
            monkeypatch,
        )

        assert res.status_code == 200
        db_session.refresh(u)
        assert u.subscription_tier == "pro"  # renewal never downgrades
        assert u.subscription_end is not None
        expected = datetime.fromtimestamp(future_ts, tz=timezone.utc).replace(tzinfo=None)
        assert u.subscription_end == expected

    def test_invoice_payment_failed_audits_without_revoking(self, client, db_session, monkeypatch):
        u = _make_user(db_session, tier="pro")
        u.subscription_customer_id = "cus_123"
        db_session.commit()

        res = self._post_webhook(
            client,
            "invoice.payment_failed",
            {"customer": "cus_123", "id": "in_1"},
            monkeypatch,
        )

        assert res.status_code == 200
        db_session.refresh(u)
        assert u.subscription_tier == "pro"  # grace period — Stripe retries
        audit = (
            db_session.query(AdminAction)
            .filter_by(entity_id=u.id, action="invoice_payment_failed")
            .first()
        )
        assert audit is not None

    def test_updated_prefers_price_over_stale_metadata(self, client, db_session, monkeypatch):
        u = _make_user(db_session, tier="pro")
        monkeypatch.setattr(settings, "STRIPE_PRICE_ELITE_MONTHLY", "price_elite_monthly")

        self._post_webhook(
            client,
            "customer.subscription.updated",
            {
                "metadata": {"user_id": u.id, "tier": "pro"},  # stale, set at checkout
                "status": "active",
                "items": {"data": [{"price": {"id": "price_elite_monthly"}}]},
            },
            monkeypatch,
        )

        db_session.refresh(u)
        assert u.subscription_tier == "elite"

    def test_duplicate_event_is_processed_once(self, client, db_session, monkeypatch):
        u = _make_user(db_session)
        obj = {
            "metadata": {"user_id": u.id, "tier": "pro", "first_month_offer": "true"},
            "customer": "cus_123",
        }

        self._post_webhook(client, "checkout.session.completed", obj, monkeypatch, event_id="evt_1")
        self._post_webhook(client, "checkout.session.completed", obj, monkeypatch, event_id="evt_1")

        db_session.refresh(u)
        assert u.subscription_tier == "pro"
        grants = (
            db_session.query(AdminAction)
            .filter_by(entity_id=u.id, action="grant_subscription")
            .count()
        )
        assert grants == 1
        assert db_session.query(StripeEvent).filter_by(event_id="evt_1").count() == 1


class TestSubscriptionManagement:
    def _auth(self, user):
        from app.dependencies import create_access_token

        return {"Authorization": f"Bearer {create_access_token(data={'sub': user.id})}"}

    @staticmethod
    def _sub(sub_id="sub_1", price_id="price_pro_monthly", period_end=None,
             cancel_at_period_end=False, created=1):
        return {
            "id": sub_id,
            "status": "active",
            "cancel_at_period_end": cancel_at_period_end,
            "created": created,
            "current_period_end": period_end,
            "items": {"data": [{"id": "si_1", "price": {"id": price_id}}]},
        }

    def test_cancel_at_period_end_schedules(self, client, db_session, monkeypatch):
        import stripe

        u = _make_user(db_session, tier="pro")
        u.subscription_customer_id = "cus_1"
        u.subscription_stripe_id = "sub_1"
        db_session.commit()
        monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test")

        period_end_ts = int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp())
        subs = [self._sub(period_end=period_end_ts)]
        modified = []

        def _list(*a, **k):
            return type("ListObj", (), {"data": subs})()

        def _modify(sub_id, **kwargs):
            modified.append((sub_id, kwargs))
            return {}

        monkeypatch.setattr(stripe.Subscription, "list", _list)
        monkeypatch.setattr(stripe.Subscription, "modify", _modify)

        res = client.post(
            "/api/v1/payments/cancel",
            json={"cancel_immediately": False},
            headers=self._auth(u),
        )

        assert res.status_code == 200
        body = res.json()
        assert body["cancel_at_period_end"] is True
        assert modified == [("sub_1", {"cancel_at_period_end": True})]

        db_session.refresh(u)
        assert u.subscription_cancels_at_period_end is True
        assert u.subscription_tier == "pro"  # access persists until period end
        assert u.subscription_end is not None

    def test_cancel_immediately_revokes(self, client, db_session, monkeypatch):
        import stripe

        u = _make_user(db_session, tier="pro")
        u.subscription_customer_id = "cus_1"
        u.subscription_stripe_id = "sub_1"
        db_session.commit()
        monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test")

        subs = [self._sub()]
        deleted = []

        def _list(*a, **k):
            return type("ListObj", (), {"data": subs})()

        def _delete(sub_id):
            deleted.append(sub_id)
            return {}

        monkeypatch.setattr(stripe.Subscription, "list", _list)
        monkeypatch.setattr(stripe.Subscription, "delete", _delete)

        res = client.post(
            "/api/v1/payments/cancel",
            json={"cancel_immediately": True},
            headers=self._auth(u),
        )

        assert res.status_code == 200
        assert deleted == ["sub_1"]
        db_session.refresh(u)
        assert u.subscription_tier == "free"
        assert u.is_subscribed is False

    def test_cancel_without_stripe_subscription_revokes_locally(
        self, client, db_session, monkeypatch
    ):
        u = _make_user(db_session, tier="pro")  # no customer id
        db_session.commit()
        monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test")

        res = client.post(
            "/api/v1/payments/cancel",
            json={"cancel_immediately": False},
            headers=self._auth(u),
        )

        assert res.status_code == 200
        db_session.refresh(u)
        assert u.subscription_tier == "free"

    def test_cancel_without_stripe_key_schedules_locally(self, client, db_session, monkeypatch):
        u = _make_user(db_session, tier="pro")
        db_session.commit()
        monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "")

        res = client.post(
            "/api/v1/payments/cancel",
            json={"cancel_immediately": False},
            headers=self._auth(u),
        )

        assert res.status_code == 200
        body = res.json()
        assert body["cancel_at_period_end"] is True
        db_session.refresh(u)
        assert u.subscription_cancels_at_period_end is True
        assert u.subscription_tier == "pro"  # access persists until period end

    def test_cancel_now_without_stripe_key_revokes(self, client, db_session, monkeypatch):
        u = _make_user(db_session, tier="pro")
        db_session.commit()
        monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "")

        res = client.post(
            "/api/v1/payments/cancel",
            json={"cancel_immediately": True},
            headers=self._auth(u),
        )

        assert res.status_code == 200
        db_session.refresh(u)
        assert u.subscription_tier == "free"
        assert u.is_subscribed is False

    def test_resume_without_stripe_key_clears_flag(self, client, db_session, monkeypatch):
        u = _make_user(db_session, tier="pro")
        u.subscription_cancels_at_period_end = True
        db_session.commit()
        monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "")

        res = client.post("/api/v1/payments/resume", headers=self._auth(u))

        assert res.status_code == 200
        db_session.refresh(u)
        assert u.subscription_cancels_at_period_end is False

    def test_change_plan_without_stripe_key_swaps_locally(self, client, db_session, monkeypatch):
        u = _make_user(db_session, tier="pro")
        db_session.commit()
        monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "")

        res = client.post(
            "/api/v1/payments/change-plan",
            json={"tier": "elite", "annual": False},
            headers=self._auth(u),
        )

        assert res.status_code == 200
        body = res.json()
        assert body["tier"] == "elite"
        db_session.refresh(u)
        assert u.subscription_tier == "elite"
        assert u.subscription_cancels_at_period_end is False

    def test_resume_clears_cancel_flag(self, client, db_session, monkeypatch):
        import stripe

        u = _make_user(db_session, tier="pro")
        u.subscription_customer_id = "cus_1"
        u.subscription_stripe_id = "sub_1"
        u.subscription_cancels_at_period_end = True
        db_session.commit()
        monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test")

        subs = [self._sub(cancel_at_period_end=True)]
        modified = []

        def _list(*a, **k):
            return type("ListObj", (), {"data": subs})()

        def _modify(sub_id, **kwargs):
            modified.append((sub_id, kwargs))
            return {}

        monkeypatch.setattr(stripe.Subscription, "list", _list)
        monkeypatch.setattr(stripe.Subscription, "modify", _modify)

        res = client.post("/api/v1/payments/resume", headers=self._auth(u))

        assert res.status_code == 200
        assert modified == [("sub_1", {"cancel_at_period_end": False})]
        db_session.refresh(u)
        assert u.subscription_cancels_at_period_end is False

    def test_change_plan_switches_tier_and_price(self, client, db_session, monkeypatch):
        import stripe

        u = _make_user(db_session, tier="pro")
        u.subscription_customer_id = "cus_1"
        u.subscription_stripe_id = "sub_1"
        db_session.commit()
        monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test")
        monkeypatch.setattr(settings, "STRIPE_PRICE_ELITE_MONTHLY", "price_elite_monthly")
        monkeypatch.setattr(settings, "STRIPE_PRICE_ELITE_ANNUAL", "price_elite_annual")

        period_end_ts = int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp())
        subs = [self._sub(price_id="price_pro_monthly", period_end=period_end_ts)]
        modified = []

        def _list(*a, **k):
            return type("ListObj", (), {"data": subs})()

        def _modify(sub_id, **kwargs):
            modified.append((sub_id, kwargs))
            return {}

        monkeypatch.setattr(stripe.Subscription, "list", _list)
        monkeypatch.setattr(stripe.Subscription, "modify", _modify)

        res = client.post(
            "/api/v1/payments/change-plan",
            json={"tier": "elite", "annual": False},
            headers=self._auth(u),
        )

        assert res.status_code == 200
        assert modified == [
            ("sub_1", {"items": [{"id": "si_1", "price": "price_elite_monthly"}]})
        ]
        body = res.json()
        assert body["tier"] == "elite"
        db_session.refresh(u)
        assert u.subscription_tier == "elite"
        assert u.subscription_cancels_at_period_end is False

    def test_change_plan_without_active_subscription_returns_409(
        self, client, db_session, monkeypatch
    ):
        import stripe

        u = _make_user(db_session, tier="pro")
        db_session.commit()
        monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test")
        monkeypatch.setattr(settings, "STRIPE_PRICE_ELITE_MONTHLY", "price_elite_monthly")

        def _list(*a, **k):
            return type("ListObj", (), {"data": []})()

        monkeypatch.setattr(stripe.Subscription, "list", _list)

        res = client.post(
            "/api/v1/payments/change-plan",
            json={"tier": "elite", "annual": False},
            headers=self._auth(u),
        )

        assert res.status_code == 409


class TestExpiryEnforcement:
    def test_expired_subscription_reads_as_free(self, db_session):
        u = _make_user(db_session, tier="pro")
        u.subscription_end = datetime.utcnow() - timedelta(days=1)
        db_session.commit()

        assert get_tier(u) == "free"
        assert is_premium(u) is False

    def test_active_subscription_stays_premium(self, db_session):
        u = _make_user(db_session, tier="pro")
        u.subscription_end = datetime.utcnow() + timedelta(days=30)
        db_session.commit()

        assert get_tier(u) == "pro"
        assert is_premium(u) is True

    def test_free_user_with_no_end_is_not_premium(self, db_session):
        u = _make_user(db_session, tier="free")
        assert get_tier(u) == "free"
        assert is_premium(u) is False


# ── DEF-015: the £1 first-month offer must be server-authoritative ──────────
# The upgrade page advertises the price the *checkout* will honour, and the
# success page prints what Stripe actually charged. Both endpoints are covered
# here with Stripe stubbed out, so the numbers can't drift from the copy.


def _auth_headers(user):
    from app.dependencies import create_access_token

    return {"Authorization": f"Bearer {create_access_token(data={'sub': user.id})}"}


class TestFirstMonthOfferEndpoint:
    def _patch_stripe(self, monkeypatch, regular_minor=999, discount_minor=899):
        import stripe

        monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test")
        monkeypatch.setattr(settings, "STRIPE_FIRST_MONTH_COUPON_ID", "FIRST_MONTH_1")
        monkeypatch.setattr(
            stripe.Price,
            "retrieve",
            lambda *a, **k: {"unit_amount": regular_minor, "currency": "gbp"},
        )
        monkeypatch.setattr(
            stripe.Coupon,
            "retrieve",
            lambda *a, **k: {"amount_off": discount_minor, "currency": "gbp", "duration": "once"},
        )

    def test_eligible_free_user_is_offered_the_coupon_price(self, client, db_session, monkeypatch):
        u = _make_user(db_session, email="offer-free@example.com", tier="free")
        self._patch_stripe(monkeypatch)

        body = client.get("/api/v1/payments/offer", headers=_auth_headers(u)).json()

        assert body["eligible"] is True
        assert body["reason"] == "eligible"
        assert body["regular_amount"] == 9.99
        assert body["first_month_amount"] == 1.0
        assert body["source"] == "stripe"
        assert body["verified"] is True

    def test_used_offer_is_not_offered_again(self, client, db_session, monkeypatch):
        u = _make_user(db_session, email="offer-used@example.com", tier="free")
        u.has_used_first_month_offer = True
        db_session.commit()
        self._patch_stripe(monkeypatch)

        body = client.get("/api/v1/payments/offer", headers=_auth_headers(u)).json()

        assert body["eligible"] is False
        assert body["reason"] == "used"

    def test_subscriber_is_not_offered_the_first_month_deal(self, client, db_session, monkeypatch):
        u = _make_user(db_session, email="offer-sub@example.com", tier="pro")
        self._patch_stripe(monkeypatch)

        body = client.get("/api/v1/payments/offer", headers=_auth_headers(u)).json()

        assert body["eligible"] is False
        assert body["reason"] == "already_subscribed"

    def test_unconfigured_coupon_is_reported_as_such(self, client, db_session, monkeypatch):
        u = _make_user(db_session, email="offer-unconf@example.com", tier="free")
        self._patch_stripe(monkeypatch)
        monkeypatch.setattr(settings, "STRIPE_FIRST_MONTH_COUPON_ID", "")

        body = client.get("/api/v1/payments/offer", headers=_auth_headers(u)).json()

        assert body["eligible"] is False
        assert body["reason"] == "not_configured"

    def test_stripe_outage_falls_back_to_config_prices(self, client, db_session, monkeypatch):
        u = _make_user(db_session, email="offer-outage@example.com", tier="free")
        self._patch_stripe(monkeypatch)
        import stripe

        def _boom(*a, **k):
            raise RuntimeError("stripe unreachable")

        monkeypatch.setattr(stripe.Price, "retrieve", _boom)

        res = client.get("/api/v1/payments/offer", headers=_auth_headers(u))

        assert res.status_code == 200
        body = res.json()
        assert body["eligible"] is True
        assert body["source"] == "config"
        assert body["verified"] is False
        assert body["first_month_amount"] == 1.0


class TestCheckoutReceiptEndpoint:
    """Stripe stubs are attribute-only objects.

    A real `StripeObject` is *not* a dict — `obj.get(...)` raises
    "…'get' is a dict method, but a StripeObject is not a dict". Passing plain
    dicts here hid exactly that crash in `GET /payments/checkout/{id}` (found by
    the live test-mode run), so the stubs below deliberately expose only
    attributes and item access.
    """

    def _session(self, user_id, *, amount_total=100, discount=899, first_month="true"):
        def ns(**kwargs):
            return SimpleNamespace(**kwargs)

        return ns(
            status="complete",
            payment_status="paid",
            currency="gbp",
            amount_total=amount_total,
            total_details=ns(amount_discount=discount),
            metadata=ns(user_id=user_id, tier="pro", first_month_offer=first_month),
            subscription=ns(
                items=ns(
                    data=[
                        ns(price=ns(unit_amount=999, recurring=ns(interval="month")))
                    ]
                ),
                current_period_end=1_800_000_000,
            ),
            customer_details=ns(email="buyer@example.com"),
        )

    def test_returns_the_actual_charge_and_next_payment(self, client, db_session, monkeypatch):
        u = _make_user(db_session, email="receipt@example.com", tier="pro")
        monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test")
        import stripe

        monkeypatch.setattr(
            stripe.checkout.Session, "retrieve", lambda *a, **k: self._session(u.id)
        )

        res = client.get("/api/v1/payments/checkout/cs_test_1", headers=_auth_headers(u))

        assert res.status_code == 200, res.text
        body = res.json()
        assert body["paid"] is True
        assert body["amount_charged"] == 1.0
        assert body["amount_discount"] == 8.99
        assert body["first_month_offer"] is True
        assert body["next_payment_amount"] == 9.99
        assert body["next_payment_date"] is not None
        assert body["interval"] == "month"
        assert body["email"] == "buyer@example.com"

    def test_full_price_session_reports_the_full_charge(self, client, db_session, monkeypatch):
        """No coupon → the receipt must show £9.99, not the offer price."""
        u = _make_user(db_session, email="receipt-full@example.com", tier="pro")
        monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test")
        import stripe

        session = self._session(u.id, amount_total=999, discount=0, first_month="false")
        monkeypatch.setattr(stripe.checkout.Session, "retrieve", lambda *a, **k: session)

        body = client.get("/api/v1/payments/checkout/cs_test_full", headers=_auth_headers(u)).json()

        assert body["amount_charged"] == 9.99
        assert body["first_month_offer"] is False
        assert body["next_payment_amount"] == 9.99

    def test_another_users_session_is_not_readable(self, client, db_session, monkeypatch):
        owner = _make_user(db_session, email="receipt-owner@example.com", tier="pro")
        other = _make_user(db_session, email="receipt-other@example.com", tier="pro")
        monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test")
        import stripe

        monkeypatch.setattr(
            stripe.checkout.Session, "retrieve", lambda *a, **k: self._session(owner.id)
        )

        res = client.get("/api/v1/payments/checkout/cs_test_2", headers=_auth_headers(other))

        assert res.status_code == 404

    def test_unknown_session_is_a_404(self, client, db_session, monkeypatch):
        u = _make_user(db_session, email="receipt-missing@example.com", tier="pro")
        monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test")
        import stripe

        def _boom(*a, **k):
            raise RuntimeError("no such session")

        monkeypatch.setattr(stripe.checkout.Session, "retrieve", _boom)

        res = client.get("/api/v1/payments/checkout/cs_missing", headers=_auth_headers(u))

        assert res.status_code == 404

class TestCheckoutCouponFallback:
    """A coupon Stripe refuses must cost the discount, not the sale (DEF-017).

    The live-mode trap: `FIRST_MONTH_1` exists in the test account only, so a live
    checkout either 502'd outright or — worse — took list price while the page
    still advertised £1. The rejection is now caught, logged with its exact
    type/code/param/request-id, and retried without the coupon.
    """

    def _patch_stripe(self, monkeypatch, *, error=None, fail_times=1):
        import stripe

        calls: list[dict] = []

        def create(**kwargs):
            calls.append(kwargs)
            if len(calls) <= fail_times:
                raise error if error is not None else stripe.StripeError(
                    "No such coupon: 'FIRST_MONTH_1'"
                )
            return SimpleNamespace(url="https://checkout.stripe.com/c/pay/cs_test_stub#fid")

        monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test")
        monkeypatch.setattr(settings, "STRIPE_PRICE_PRO_MONTHLY", "price_pro_monthly")
        monkeypatch.setattr(settings, "STRIPE_FIRST_MONTH_COUPON_ID", "FIRST_MONTH_1")
        monkeypatch.setattr(stripe.checkout.Session, "create", create)
        return calls

    def _checkout(self, client, user):
        return client.post(
            "/api/v1/payments/checkout",
            json={"tier": "pro", "annual": False, "first_month_offer": True},
            headers=_auth_headers(user),
        )

    def test_a_rejected_coupon_is_retried_at_list_price(self, client, db_session, monkeypatch):
        u = _make_user(db_session, email="coupon-fallback@example.com", tier="free")
        calls = self._patch_stripe(monkeypatch)

        res = self._checkout(client, u)

        assert res.status_code == 200, res.text
        body = res.json()
        assert body["offer_applied"] is False
        assert body["checkout_url"].startswith("https://checkout.stripe.com/")
        # The coupon was attempted once, then dropped for the retry — and the
        # session metadata must not claim the offer the customer isn't getting.
        assert calls[0]["discounts"] == [{"coupon": "FIRST_MONTH_1"}]
        assert calls[1]["discounts"] is None
        assert calls[1]["metadata"]["first_month_offer"] == "false"

    def test_an_accepted_coupon_reports_the_offer_as_applied(
        self, client, db_session, monkeypatch
    ):
        u = _make_user(db_session, email="coupon-applied@example.com", tier="free")
        calls = self._patch_stripe(monkeypatch, fail_times=0)

        res = self._checkout(client, u)

        assert res.status_code == 200, res.text
        assert res.json()["offer_applied"] is True
        assert len(calls) == 1
        assert calls[0]["discounts"] == [{"coupon": "FIRST_MONTH_1"}]

    def test_a_failure_that_is_not_the_coupon_is_not_retried(
        self, client, db_session, monkeypatch
    ):
        import stripe

        u = _make_user(db_session, email="coupon-hardfail@example.com", tier="free")
        calls = self._patch_stripe(
            monkeypatch,
            fail_times=99,
            error=stripe.AuthenticationError("Invalid API Key provided"),
        )

        res = self._checkout(client, u)

        # A dead key is not something a retry can fix, and it must never be
        # disguised as a full-price sale.
        assert res.status_code == 502
        assert res.json()["detail"]["code"] == "stripe_error"
        assert len(calls) == 1

    def test_an_expired_coupon_also_falls_back_at_list_price(
        self, client, db_session, monkeypatch
    ):
        import stripe

        u = _make_user(db_session, email="coupon-expired@example.com", tier="free")
        calls = self._patch_stripe(
            monkeypatch,
            error=stripe.StripeError("This coupon has expired (param: discounts.0.coupon)"),
        )

        res = self._checkout(client, u)

        assert res.status_code == 200, res.text
        assert res.json()["offer_applied"] is False
        assert len(calls) == 2

