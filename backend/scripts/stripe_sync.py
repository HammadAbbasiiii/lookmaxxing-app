#!/usr/bin/env python3
"""Replay a Stripe customer's recent webhook events to the local backend.

Fixes local users whose checkout completed in Stripe but whose webhooks were
delivered elsewhere (e.g. the Render production endpoint) instead of here.

Usage:  cd backend && .venv/bin/python scripts/stripe_sync.py <customer_id|email> ...
"""
import os, sys, json, time, hmac, hashlib, urllib.request
import stripe
from dotenv import load_dotenv

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = os.path.join(BACKEND_DIR, ".env")
load_dotenv(ENV)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
WHSEC = os.getenv("STRIPE_WEBHOOK_SECRET")
WEBHOOK_URL = "http://127.0.0.1:8000/api/v1/payments/webhook"
HANDLED = {"checkout.session.completed", "customer.subscription.created",
           "customer.subscription.updated", "customer.subscription.deleted",
           "invoice.paid", "invoice.payment_failed"}

def sign(payload):
    t = int(time.time())
    s = f"{t}.{payload}".encode()
    return f"t={t},v1={hmac.new(WHSEC.encode(), s, hashlib.sha256).hexdigest()}"

def post(evt):
    payload = json.dumps(evt, default=str)
    req = urllib.request.Request(WEBHOOK_URL, data=payload.encode(),
        headers={"Content-Type": "application/json", "stripe-signature": sign(payload)})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

def resolve_customer_id(arg):
    if arg.startswith("cus_"):
        return arg
    for c in stripe.Customer.list(email=arg, limit=5).data:
        return c.id
    return None

def sync(customer_id):
    print(f"=== syncing {customer_id} ===")
    collected = []
    for typ in HANDLED:
        for e in stripe.Event.list(type=typ, limit=100).data:
            obj = e.data.object if hasattr(e, "data") else {}
            if obj and getattr(obj, "customer", None) == customer_id:
                collected.append((e.created, e))
    collected.sort(key=lambda x: x[0])
    if not collected:
        print("  no handled events found")
        return
    for _, e in collected:
        d = e.to_dict() if hasattr(e, "to_dict") else e
        st, body = post(d)
        print(f"  ↻ {d['id']} {d['type']} -> HTTP {st} {body[:60]}")

if __name__ == "__main__":
    for arg in sys.argv[1:]:
        cid = resolve_customer_id(arg)
        if not cid:
            print(f"!! no customer for {arg}")
            continue
        sync(cid)
