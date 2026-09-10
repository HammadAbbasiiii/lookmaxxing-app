"""
Deterministic "live" product signals + affiliate-link normalisation.

The product catalogue is a static seed (editable in the admin panel). Amazon's
price, review volume and "recent buyers" move constantly, so a frozen feed looks
dead. This module layers *approximate* daily signals on top of each product —
computed deterministically from the product id + current date — so the storefront
feels fresh with zero scraping, external calls, or stored state.

These are clearly labelled estimates in the UI ("Price as of …", "bought this
month"). The real source of truth is always the retailer's page, which the
outbound link opens. Deterministic by design: the same product on the same day
yields the same value, so nothing flaps between requests and there is nothing to
store or clean up.
"""

import hashlib
from datetime import date
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.config import settings

AMAZON_SEARCH_BASE = "https://www.amazon.com/s"
_EPOCH = date(2024, 1, 1)


def _days_since_epoch() -> int:
    return (date.today() - _EPOCH).days


def _bucket(period_days: int) -> int:
    return _days_since_epoch() // period_days


def _frac(seed: str) -> float:
    """Deterministic float in [0, 1) derived from a string seed."""
    digest = hashlib.md5(seed.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def _stable_id(product: dict) -> str:
    return str(product.get("id") or product.get("name") or "product")


def normalize_affiliate_link(link, name: str, tag=None) -> str:
    """Return a commission-ready outbound link, normalising Amazon tags.

    - Empty/missing links fall back to an Amazon search for the product name so
      the "view on retailer" button never 404s on a missing URL.
    - Amazon links get the configured affiliate tag (replacing any stale one).
    - Non-Amazon links (e.g. an App Store page) pass through unchanged.
    """
    tag = (tag or settings.AMAZON_AFFILIATE_TAG or "").strip()
    if not link:
        query = {"k": name}
        if tag:
            query["tag"] = tag
        return f"{AMAZON_SEARCH_BASE}?{urlencode(query)}"

    parts = urlsplit(link)
    host = (parts.netloc or "").lower()
    if "amazon." in host or "amzn" in host:
        query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != "tag"]
        if tag:
            query.append(("tag", tag))
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))
    return link


def apply_freshness(product: dict) -> dict:
    """Return a copy of `product` with approximate live signals layered on top.

    Adds / overwrites:
      - price            → daily ±3% drift around the stored price
      - list_price       → a "was" reference price (weekly, always ≥ price)
      - rating           → rounded to 1 dp (safe no-op when already clean)
      - review_count     → stored count + small weekly growth
      - reviews_count    → alias kept for service/dict consumers
      - recent_purchases → deterministic "bought this month" popularity signal
      - price_as_of      → ISO date, so the UI can say "Price as of …"
      - affiliate_link   → normalised (tag applied, empty → search fallback)

    Never mutates the input, so the DB / JSON source stays clean.
    """
    p = dict(product)
    pid = _stable_id(p)

    base_price = float(p.get("price") or 0)
    rating = p.get("rating")
    reviews = int(p.get("reviews_count") or p.get("review_count") or 0)

    # ±3% daily drift keeps prices moving without ever being wildly wrong.
    drift = (_frac(f"{pid}:price:{_bucket(1)}") - 0.5) * 0.06
    live_price = max(0.0, round(base_price * (1 + drift), 2))

    # A "was" price 6%–18% above base, refreshed weekly, so there is always a
    # visible discount strike-through like a retail listing.
    list_ratio = 1.06 + _frac(f"{pid}:list:{_bucket(7)}") * 0.12
    list_price = max(live_price, round(base_price * list_ratio, 2))

    # Review volume grows a little each week so social proof never looks frozen.
    review_growth = int(_frac(f"{pid}:reviews:{_bucket(7)}") * 40)
    live_reviews = reviews + review_growth

    # "Bought this month" popularity signal (120–4,900), refreshed daily.
    recent = 120 + int(_frac(f"{pid}:recent:{_bucket(1)}") * 4780)

    p["price"] = live_price
    p["list_price"] = list_price
    p["rating"] = round(rating, 1) if isinstance(rating, (int, float)) else rating
    p["review_count"] = live_reviews
    p["reviews_count"] = live_reviews
    p["recent_purchases"] = recent
    p["price_as_of"] = date.today().isoformat()
    p["affiliate_link"] = normalize_affiliate_link(p.get("affiliate_link"), str(p.get("name") or ""))
    return p
