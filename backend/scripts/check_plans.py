#!/usr/bin/env python3
"""Which plans a deployment can actually sell — the DEF-019 check, from outside.

Both annual plans once died with `stripe_error` ("Couldn't start checkout. Try
again in a moment.") because the price ids on the box named prices Stripe had
archived; monthly kept working, so nothing looked broken. This starts (and
abandons) one Checkout session per plan with a throwaway account, so a stale
price id shows up here instead of in a customer's face.

No payment is ever completed, nothing is charged, and the throwaway account is
deleted afterwards.

Usage:
  python scripts/check_plans.py                        # localhost:8000
  python scripts/check_plans.py https://lookmaxx-api.onrender.com

Exit code 0 when all four plans can start a checkout, 1 otherwise (runbook/CI
friendly). It needs no Stripe key of its own — it only talks to the API.
"""
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
if not BASE.endswith("/api/v1"):
    BASE += "/api/v1"
EMAIL = f"cline-plans-check-{int(time.time())}@mailinator.com"
PASSWORD = "PlansCheck1234"

PLANS = (("pro", False), ("pro", True), ("elite", False), ("elite", True))


def call(path, body=None, token=None, form=None, method=None):
    headers, data = {}, None
    if form is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        data = urllib.parse.urlencode(form).encode()
    elif body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw


def main() -> int:
    print(f"checking {BASE}")
    status, body = call("/auth/signup", body={"email": EMAIL, "password": PASSWORD})
    if status not in (200, 201):
        print(f"  (signup said {status} {body} — continuing, the account may exist)")

    status, body = call("/auth/login", form={"username": EMAIL, "password": PASSWORD})
    if status != 200:
        print(f"❌ could not sign in as the throwaway account: {status} {body}")
        return 1
    token = body["access_token"]

    failures = 0
    for tier, annual in PLANS:
        label = f"{tier:5} {'annual ' if annual else 'monthly'}"
        status, body = call(
            "/payments/checkout",
            {"tier": tier, "annual": annual, "first_month_offer": False},
            token=token,
        )
        detail = body.get("detail") if isinstance(body, dict) else body
        if status == 200 and body.get("checkout_url"):
            print(f"  ✅ {label} → HTTP {status} (session started)")
        else:
            failures += 1
            code = detail.get("code") if isinstance(detail, dict) else None
            print(f"  ❌ {label} → HTTP {status} {json.dumps(detail)[:160]}")
            if code == "plan_unavailable":
                print(
                    "       ↳ that plan's price env var is stale: repoint it at an "
                    "ACTIVE price with the right interval, then re-run this."
                )

    call("/profile/delete", token=token, method="DELETE")
    print(f"throwaway account {EMAIL} deleted")
    if failures:
        print(f"\n❌ {failures} of {len(PLANS)} plans cannot start a checkout")
    else:
        print(f"\n✅ all {len(PLANS)} plans can start a checkout")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
