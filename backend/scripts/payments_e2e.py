#!/usr/bin/env python3
"""
End-to-end payments lifecycle test — no UI, no browser.
Drives the REAL Stripe test account + local FastAPI backend, replaying signed
webhooks to the local endpoint so app state reflects real Stripe events.

Scenarios: Free->Pro(£1 offer), upgrade Pro->Elite annual, downgrade Elite->Pro,
cancel at period end, resume, cancel immediately, re-subscribe, end-of-period expiry.

Run:  cd backend && .venv/bin/python scripts/payments_e2e.py

Point it at a deployment instead of localhost:

  LOOKMAXX_API_URL=https://lookmaxx-api.onrender.com .venv/bin/python scripts/payments_e2e.py

⚠️ This script *replays signed webhooks*, so against a deployed box it mutates the
throwaway account it creates (which is the point). To only ask "can this box even
start a checkout for each plan?" — the read-only DEF-019 question — use
`scripts/check_plans.py` instead.

Requires: backend running on 127.0.0.1:8000 (or LOOKMAXX_API_URL), and
STRIPE_SECRET_KEY / STRIPE_WEBHOOK_SECRET / STRIPE_PRICE_* in backend/.env
(Stripe test mode).
"""
import json, os, sys, time, hmac, hashlib, urllib.request, urllib.parse
import stripe
from dotenv import load_dotenv

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BACKEND_DIR, ".env")
load_dotenv(ENV_PATH)
sys.path.insert(0, BACKEND_DIR)  # make `import app.*` work from any CWD
BASE = "http://127.0.0.1:8000/api/v1"
WEBHOOK_URL = BASE + "/payments/webhook"
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
WHSEC = os.getenv("STRIPE_WEBHOOK_SECRET")
PRICES = {
    "pro_monthly": os.getenv("STRIPE_PRICE_PRO_MONTHLY"),
    "pro_annual": os.getenv("STRIPE_PRICE_PRO_ANNUAL"),
    "elite_monthly": os.getenv("STRIPE_PRICE_ELITE_MONTHLY"),
    "elite_annual": os.getenv("STRIPE_PRICE_ELITE_ANNUAL"),
}
COUPON = os.getenv("STRIPE_FIRST_MONTH_COUPON_ID")
HANDLED_EVENTS = {
    "checkout.session.completed", "customer.subscription.created",
    "customer.subscription.updated", "customer.subscription.deleted",
    "invoice.paid", "invoice.payment_failed",
}
RUN = int(time.time())
PASS = 0
FAIL = 0
FAILURES = []

def check(cond, msg):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {msg}")
    else:
        FAIL += 1
        FAILURES.append(msg)
        print(f"  ❌ {msg}")

def eq(got, want, msg):
    check(got == want, f"{msg} (got={got!r}, want={want!r})")

def http(method, path, token=None, json_body=None, form=None):
    url = BASE + path
    headers = {"Content-Type": "application/json"}
    data = None
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif json_body is not None:
        data = json.dumps(json_body).encode()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read().decode()
            return r.status, (json.loads(body) if body else {})
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"raw": body}

def sign(payload_str):
    t = int(time.time())
    signed = f"{t}.{payload_str}".encode()
    sig = hmac.new(WHSEC.encode(), signed, hashlib.sha256).hexdigest()
    return f"t={t},v1={sig}"

def post_webhook(event_dict):
    payload = json.dumps(event_dict, default=str)
    req = urllib.request.Request(
        WEBHOOK_URL, data=payload.encode(),
        headers={"Content-Type": "application/json", "stripe-signature": sign(payload)},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

def replay_event(event_dict, label=""):
    st, body = post_webhook(event_dict)
    check(st == 200, f"webhook {event_dict.get('type')}{label} -> HTTP {st} ({body[:80]})")
    return st, body

def replay_customer_events(customer_id, since):
    collected = []
    for typ in HANDLED_EVENTS:
        try:
            evts = stripe.Event.list(type=typ, created={"gte": int(since) - 5}, limit=100).data
        except Exception as e:
            print(f"    (list {typ} err: {e})")
            continue
        for e in evts:
            obj = e.data.object if hasattr(e, "data") else None
            if not obj:
                continue
            cust = getattr(obj, "customer", None)
            if cust == customer_id:
                collected.append((e.created, e))
    collected.sort(key=lambda x: x[0])
    replayed = []
    for _, e in collected:
        d = e.to_dict() if hasattr(e, "to_dict") else e
        st, body = post_webhook(d)
        print(f"    ↻ replay {d['id']} {d['type']} -> HTTP {st}")
        replayed.append(d["type"])
    return replayed

def stripe_new_customer(email, user_id):
    c = stripe.Customer.create(email=email, metadata={"user_id": user_id})
    pm = stripe.PaymentMethod.attach("pm_card_visa", customer=c.id)
    stripe.Customer.modify(c.id, invoice_settings={"default_payment_method": pm.id})
    return c

def stripe_create_subscription(customer_id, price_id, user_id, tier, coupon=None):
    kwargs = dict(customer=customer_id, items=[{"price": price_id}], metadata={"user_id": user_id, "tier": tier})
    if coupon:
        kwargs["discounts"] = [{"coupon": coupon}]
    return stripe.Subscription.create(**kwargs)

def session_id_from_url(url):
    if url and ("cs_test_" in url or "cs_live_" in url):
        idx = url.find("cs_")
        return url[idx:].split("#")[0].split("?")[0]
    return None

def create_app_user(email):
    password = "TestPass123!"
    st, body = http("POST", "/auth/signup", json_body={"email": email, "password": password})
    if st not in (200, 201, 400):
        check(False, f"signup {email} -> HTTP {st} {body}")
        return None
    st, tok = http("POST", "/auth/login", form={"username": email, "password": password})
    if st != 200:
        check(False, f"login {email} -> HTTP {st} {tok}")
        return None
    return {"id": tok["user_id"], "token": tok["access_token"], "email": email}

def me(user):
    st, body = http("GET", "/auth/me", token=user["token"])
    return body

def entitlements(user):
    st, body = http("GET", "/entitlements", token=user["token"])
    return body

def checkout_via_api(user, tier, annual, first_month_offer=False):
    st, body = http("POST", "/payments/checkout", token=user["token"],
                    json_body={"tier": tier, "annual": annual, "first_month_offer": first_month_offer})
    check(st == 200, f"POST /payments/checkout {tier} annual={annual} -> HTTP {st}")
    return body.get("checkout_url")

def change_plan_via_api(user, tier, annual):
    st, body = http("POST", "/payments/change-plan", token=user["token"],
                    json_body={"tier": tier, "annual": annual})
    check(st == 200, f"POST /payments/change-plan {tier} annual={annual} -> HTTP {st} {body}")
    return body

def cancel_via_api(user, cancel_immediately):
    st, body = http("POST", "/payments/cancel", token=user["token"],
                    json_body={"cancel_immediately": cancel_immediately})
    check(st == 200, f"POST /payments/cancel immediate={cancel_immediately} -> HTTP {st} {body}")
    return body

def resume_via_api(user):
    st, body = http("POST", "/payments/resume", token=user["token"])
    check(st == 200, f"POST /payments/resume -> HTTP {st} {body}")
    return body

def scenario_1():
    print("\n=== Scenario 1: Free -> Pro monthly (£1 first-month offer) ===")
    user = create_app_user(f"e2e.pay.api.{RUN}.a@example.com")
    m = me(user)
    eq(m.get("subscription_tier"), "free", "starts free")
    eq(m.get("is_subscribed"), False, "starts unsubscribed")
    eq(m.get("has_used_first_month_offer"), False, "offer unused")

    url = checkout_via_api(user, "pro", annual=False, first_month_offer=True)
    check(bool(url), "checkout returned a URL")
    sid = session_id_from_url(url or "")
    sess = stripe.checkout.Session.retrieve(sid).to_dict()
    eq(sess.get("mode"), "subscription", "session mode = subscription")
    eq((sess.get("metadata") or {}).get("tier"), "pro", "session metadata.tier = pro")
    eq((sess.get("metadata") or {}).get("first_month_offer"), "true", "session first_month_offer = true")
    # NB: subscription_data is a write-only param — Stripe doesn't return it on
    # retrieve. The subscription it produces carries the metadata (verified by
    # the user's real webhook payload), so we don't assert it here.
    disc_ids = [d.get("coupon") for d in (sess.get("discounts") or [])]
    check(COUPON in disc_ids, f"session carries the £1 coupon {COUPON}")

    cust = stripe_new_customer(user["email"], user["id"])
    sub = stripe_create_subscription(cust.id, PRICES["pro_monthly"], user["id"], "pro", coupon=COUPON)

    sess_dict = dict(sess)
    sess_dict["customer"] = cust.id
    sess_dict["subscription"] = sub.id
    replay_event({"id": f"evt_e2e_1_{RUN}", "type": "checkout.session.completed", "data": {"object": sess_dict}})
    replay_customer_events(cust.id, since=sub.created)

    m = me(user)
    eq(m.get("subscription_tier"), "pro", "now Pro")
    eq(m.get("is_subscribed"), True, "now subscribed")
    eq(m.get("has_used_first_month_offer"), True, "£1 offer consumed")

    ent = entitlements(user)
    eq(ent.get("tier"), "pro", "entitlements tier = pro")
    eq(ent["limits"]["analyses"]["unlimited"], True, "unlimited analyses unlocked")
    golden = next((f for f in ent["features"] if f["key"] == "golden_ratio"), None)
    eq(bool(golden and golden["locked"]), True, "Elite-only feature still locked on Pro")
    return user, cust

def scenario_upgrade_downgrade(user, cust):
    print("\n=== Scenario 2/3: Pro -> Elite annual, then Elite -> Pro annual ===")
    body = change_plan_via_api(user, "elite", annual=True)
    eq(body.get("tier"), "elite", "change-plan -> elite")
    m = me(user)
    eq(m.get("subscription_tier"), "elite", "me = elite")
    end = m.get("subscription_end")
    check(end is not None, "subscription_end set after upgrade")
    if end:
        from datetime import datetime
        end_dt = datetime.fromisoformat(end)
        days = (end_dt - datetime.utcnow()).days
        check(days > 300, f"annual upgrade extends ~1yr (days left={days})")

    since = int(time.time()) - 60
    for e in stripe.Event.list(type="customer.subscription.updated", created={"gte": since}, limit=50).data:
        obj = e.data.object
        if obj and getattr(obj, "customer", None) == cust.id:
            replay_event(e.to_dict(), label=" (upgrade)")
            break
    m = me(user)
    eq(m.get("subscription_tier"), "elite", "still elite after updated webhook")

    body = change_plan_via_api(user, "pro", annual=True)
    eq(body.get("tier"), "pro", "change-plan -> pro")
    m = me(user)
    eq(m.get("subscription_tier"), "pro", "me = pro after downgrade")
    for e in stripe.Event.list(type="customer.subscription.updated", created={"gte": int(time.time()) - 60}, limit=50).data:
        obj = e.data.object
        if obj and getattr(obj, "customer", None) == cust.id:
            replay_event(e.to_dict(), label=" (downgrade)")
            break
    m = me(user)
    eq(m.get("subscription_tier"), "pro", "still pro after downgrade webhook")
    return user, cust

def scenario_cancel_resume(user, cust):
    print("\n=== Scenario 4/5: Cancel at period end, then Resume ===")
    body = cancel_via_api(user, cancel_immediately=False)
    eq(body.get("cancel_at_period_end"), True, "cancel schedules end-of-period")
    eq(body.get("is_subscribed"), True, "access persists after scheduling cancel")
    m = me(user)
    eq(m.get("subscription_cancels_at_period_end"), True, "me.cancel_at_period_end = true")
    eq(m.get("subscription_tier"), "pro", "tier still pro while cancellation pending")

    for e in stripe.Event.list(type="customer.subscription.updated", created={"gte": int(time.time()) - 60}, limit=50).data:
        obj = e.data.object
        if obj and getattr(obj, "customer", None) == cust.id and getattr(obj, "cancel_at_period_end", False):
            replay_event(e.to_dict(), label=" (cancel at period end)")
            break
    m = me(user)
    eq(m.get("subscription_cancels_at_period_end"), True, "webhook keeps cancel_at_period_end")

    body = resume_via_api(user)
    eq(body.get("cancel_at_period_end"), False, "resume clears the flag")
    m = me(user)
    eq(m.get("subscription_cancels_at_period_end"), False, "me.cancel_at_period_end = false")
    return user, cust

def scenario_cancel_immediate(user, cust):
    print("\n=== Scenario 6: Cancel immediately (revoke -> free) ===")
    body = cancel_via_api(user, cancel_immediately=True)
    eq(body.get("tier"), "free", "cancel immediate -> free")
    eq(body.get("is_subscribed"), False, "cancel immediate -> unsubscribed")
    m = me(user)
    eq(m.get("subscription_tier"), "free", "me = free after immediate cancel")
    eq(m.get("is_subscribed"), False, "me unsubscribed")

    for e in stripe.Event.list(type="customer.subscription.deleted", created={"gte": int(time.time()) - 60}, limit=50).data:
        obj = e.data.object
        if obj and getattr(obj, "customer", None) == cust.id:
            replay_event(e.to_dict(), label=" (deleted)")
            break
    m = me(user)
    eq(m.get("subscription_tier"), "free", "still free after deleted webhook (idempotent)")
    return user, cust

def scenario_resubscribe(user, cust):
    print("\n=== Scenario 7: Re-subscribe after cancellation ===")
    sub = stripe_create_subscription(cust.id, PRICES["pro_monthly"], user["id"], "pro")
    replay_customer_events(cust.id, since=sub.created)
    m = me(user)
    eq(m.get("subscription_tier"), "pro", "re-subscribed -> pro")
    eq(m.get("is_subscribed"), True, "re-subscribed")
    return user, cust

def scenario_expiry():
    print("\n=== Scenario 8: End-of-period expiry (safety net) ===")
    from datetime import datetime, timedelta
    user = create_app_user(f"e2e.pay.api.{RUN}.b@example.com")
    from app.database import SessionLocal
    from app.models import User
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.id == user["id"]).first()
        u.subscription_tier = "pro"
        u.is_subscribed = True
        u.subscription_end = datetime.utcnow() - timedelta(days=1)
        db.commit()
    finally:
        db.close()

    m = me(user)
    eq(m.get("subscription_tier"), "free", "expired pro reads as free on /auth/me")
    ent = entitlements(user)
    eq(ent.get("tier"), "free", "expired pro reads as free on /entitlements")
    eq(ent["limits"]["analyses"]["unlimited"], False, "expired user has no unlimited analyses")
    return user

def main():
    print(f"Stripe test account; prices: {json.dumps(PRICES, indent=2)}")
    print(f"Coupon: {COUPON}")
    check(bool(WHSEC), "webhook secret loaded")
    check(bool(stripe.api_key), "stripe secret key loaded")
    try:
        user, cust = scenario_1()
        user, cust = scenario_upgrade_downgrade(user, cust)
        user, cust = scenario_cancel_resume(user, cust)
        user, cust = scenario_cancel_immediate(user, cust)
        user, cust = scenario_resubscribe(user, cust)
        scenario_expiry()
    except Exception as e:
        import traceback
        traceback.print_exc()
        FAILURES.append(f"EXCEPTION: {e}")
        global FAIL
        FAIL += 1
    print(f"\n{'='*60}\nRESULT: {PASS} passed, {FAIL} failed")
    if FAILURES:
        print("Failures:")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("ALL PAYMENT SCENARIOS PASSED ✅")
    sys.exit(0)

if __name__ == "__main__":
    main()
