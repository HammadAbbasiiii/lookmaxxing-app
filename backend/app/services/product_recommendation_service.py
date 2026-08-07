"""
Product Recommendation Engine

Recommends products based on a user's category breakdown and scores.
Uses a combination of score matching, rating weighting, and budget tiering
to surface the most relevant products for the user's weakest areas.

Psychology principles applied:
- Reciprocity: Recommend genuinely helpful products → users trust recommendations
- Social Proof: Display rating and review counts prominently
- Authority: Products from dermatologist-recommended / clinically-tested brands
- The Decoy Effect: Return products across budget/mid/premium tiers so users self-select mid
- Loss Aversion: Products targeted at exactly what the user needs to improve
"""
import json
import os
from typing import Optional

# ─── Category display name mapping ───
CATEGORY_DISPLAY = {
    "skin_quality": "Skin Quality",
    "jawline_definition": "Jawline Definition",
    "eye_appeal": "Eye Appeal",
    "facial_structure": "Facial Structure",
    "grooming": "Grooming",
    "general": "General Wellness",
}

# ─── Human-readable rationale templates by category ───
RATIONALE_TEMPLATES = {
    "skin_quality": "Your skin quality score is {score}/100. This product targets {focus} to improve texture and clarity.",
    "jawline_definition": "Your jawline definition score is {score}/100. This tool helps {focus} for a sharper jawline.",
    "eye_appeal": "Your eye area score is {score}/100. This formula addresses {focus} to brighten and refresh.",
    "facial_structure": "Your facial structure score is {score}/100. This device/tool supports {focus} for better definition.",
    "grooming": "Your grooming metric can improve. This product elevates {focus} for a polished look.",
    "general": "General wellness affects all scores. This supports {focus} — foundational to your transformation.",
}


# ─── Load product database ───
def _load_product_database() -> list[dict]:
    """Load products from the JSON database file."""
    db_path = os.path.join(os.path.dirname(__file__), "product_database.json")
    try:
        with open(db_path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


# ─── Sort key helpers ───
def _sort_key_rating(product: dict) -> float:
    """Sort by rating × log(reviews) to balance quality and social proof volume."""
    import math
    return product.get("rating", 0) * math.log(product.get("reviews_count", 10) + 1)


# ─── Category→display key mapping for category_breakdown lookup ───
CATEGORY_KEY_MAP = {
    "skin_quality": ["skin_quality", "skin_score", "skin"],
    "jawline_definition": ["jawline_definition", "jawline_score", "jawline"],
    "eye_appeal": ["eye_appeal", "eye_score", "eye_area", "eyes"],
    "facial_structure": ["facial_structure", "structure_score", "facial_structure_score", "face_structure"],
    "grooming": ["grooming", "grooming_score"],
    "general": ["general", "overall_score", "overall"],
}


def _get_category_score(category: str, category_breakdown: dict) -> Optional[float]:
    """Extract a category score from the breakdown dict, trying multiple possible key names."""
    keys_to_try = CATEGORY_KEY_MAP.get(category, [category])
    for key in keys_to_try:
        val = category_breakdown.get(key)
        if isinstance(val, (int, float)):
            return float(val)
    return None


def _get_product_category_list(category_breakdown: dict, products: list[dict]) -> list[str]:
    """Return categories sorted by ascending score (weakest first)."""
    scored = []
    for cat in ["skin_quality", "jawline_definition", "eye_appeal", "facial_structure", "grooming"]:
        score = _get_category_score(cat, category_breakdown)
        if score is not None:
            scored.append((cat, score))
    scored.sort(key=lambda x: x[1])
    # Ensure all categories are represented
    categories = [c for c, _ in scored]
    if "general" not in categories:
        categories.append("general")
    return categories


def _deduplicate_products(products: list[dict]) -> list[dict]:
    """Remove duplicate products by ID, preserving order."""
    seen = set()
    result = []
    for p in products:
        if p["id"] not in seen:
            seen.add(p["id"])
            result.append(p)
    return result


# ─── Main recommendation function ───
def get_product_recommendations(
    category_breakdown: dict,
    overall_score: Optional[float] = None,
    user_profile: Optional[dict] = None,
    max_products: int = 8,
    budget_tier: Optional[str] = None,
) -> list[dict]:
    """
    Generate personalised product recommendations.

    Args:
        category_breakdown: Dict with per-category scores, e.g.:
            {"skin_quality": 45, "jawline_definition": 62, "eye_appeal": 71,
             "facial_structure": 55, "grooming": 40, "overall": 54.6}
        overall_score: Optional aggregate score (used if individual categories missing).
        user_profile: Optional user metadata (budget preference, etc.).
        max_products: Maximum number of products to return (default 8).
        budget_tier: Force a specific tier ("budget" | "mid_range" | "premium").
            If None, defaults to "mid_range" but mix-in logic applies.

    Returns:
        List of recommendation dicts:
        {
            "product": {...product fields...},
            "reason": "Human-readable rationale",
            "category": "skin_quality",
            "tier": "mid_range"
        }
    """
    products = _load_product_database()
    if not products:
        return []

    user_tier = budget_tier or "mid_range"
    category_order = _get_product_category_list(category_breakdown, products)

    # Strategy: iterate through weakest categories and collect products.
    # For each weak category (score < 70), prioritise:
    #   1. Exact tier match
    #   2. Rating × log(reviews) for tie-breaking
    # For categories where score >= 70, still include at most 1 product.
    recommendations_raw = []
    for cat in category_order:
        score = _get_category_score(cat, category_breakdown) or (overall_score or 50)
        cat_products = [p for p in products if p.get("category") == cat]

        if not cat_products:
            continue

        # Sort by rating-adjusted metric
        cat_products_sorted = sorted(cat_products, key=_sort_key_rating, reverse=True)

        # Score-based allocation
        if score < 45:
            # Weakest — recommend 3 products
            take = 3
        elif score < 70:
            # Moderate — recommend 2 products
            take = 2
        else:
            # Strong — recommend 1 product
            take = 1

        # Pick products prioritising budget tier but also mixing tiers for decoy effect
        selected_for_cat = []
        # First pass: exact tier match
        for p in cat_products_sorted:
            if len(selected_for_cat) >= take:
                break
            if p.get("tier") == user_tier:
                selected_for_cat.append(p)

        # Second pass: fill remaining slots with other tiers
        for p in cat_products_sorted:
            if len(selected_for_cat) >= take:
                break
            if p not in selected_for_cat:
                selected_for_cat.append(p)

        recommendations_raw.extend(selected_for_cat)

    # Deduplicate and trim
    recommendations_raw = _deduplicate_products(recommendations_raw)
    recommendations_raw = recommendations_raw[:max_products]

    # Build final response with rationales
    result = []
    for p in recommendations_raw:
        cat = p.get("category", "general")
        score = _get_category_score(cat, category_breakdown) or (overall_score or 50)
        tags = p.get("tags", [])
        focus = _format_focus(score, tags, cat)
        rationale = RATIONALE_TEMPLATES.get(
            cat,
            "Based on your analysis, this product helps address key improvement areas.",
        ).format(score=int(score), focus=focus)

        result.append({
            "product": {
                "id": p.get("id"),
                "name": p.get("name"),
                "brand": p.get("brand"),
                "price": p.get("price"),
                "currency": p.get("currency", "USD"),
                "affiliate_link": p.get("affiliate_link"),
                "image_url": p.get("image_url"),
                "rating": p.get("rating"),
                "reviews_count": p.get("reviews_count"),
                "social_proof": p.get("social_proof"),
            },
            "reason": rationale,
            "category": cat,
            "tier": p.get("tier", "mid_range"),
        })

    return result


def _format_focus(score: float, tags: list[str], category: str) -> str:
    """Build a human-readable 'focus' phrase for the rationale template."""
    focus_map = {
        "skin_quality": {
            "brightening": "brightening and evening skin tone",
            "antioxidant": "antioxidant protection against environmental damage",
            "vitamin_c": "boosting collagen and fading dark spots",
            "niacinamide": "minimising pores and controlling oil",
            "retinol": "accelerating cell turnover and smoothing fine lines",
            "exfoliant": "decongesting pores and refining texture",
            "bha": "unclogging pores and clearing blackheads",
            "hydration": "deep hydration and barrier repair",
            "cleanser": "gentle cleansing without stripping the skin barrier",
            "sunscreen": "protecting against UV damage and preventing premature aging",
            "spf": "daily sun protection to maintain results",
            "essence": "boosting hydration and skin barrier function",
            "anti_aging": "targeting visible signs of aging",
            "cell_turnover": "renewing skin for a smoother complexion",
            "barrier_repair": "repairing the skin's protective barrier",
            "oil_control": "balancing oil production and reducing shine",
            "pores": "refining pore appearance",
            "blemish": "reducing blemishes and preventing breakouts",
        },
        "jawline_definition": {
            "jaw_exercise": "building masseter muscle strength",
            "resistance_training": "resistance training for jaw definition",
            "facial_fitness": "toning facial muscles",
            "chewing": "natural chewing resistance for muscle engagement",
            "posture": "improving neck and head alignment",
            "neck_alignment": "correcting forward head posture",
            "gua_sha": "lymphatic drainage and facial sculpting",
            "lymphatic_drainage": "reducing puffiness and defining contours",
            "sculpting": "sculpting jaw and cheek contours",
            "facial_massage": "stimulating circulation for a defined jawline",
            "tongue_posture": "retraining tongue posture for facial development",
            "myofunctional": "myofunctional therapy for jaw and airway health",
        },
        "eye_appeal": {
            "eye_serum": "targeting dark circles and puffiness",
            "caffeine": "depuffing and brightening the under-eye area",
            "dark_circles": "reducing the appearance of dark circles",
            "eye_cream": "hydrating and smoothing fine lines",
            "hydration": "nourishing the delicate eye area",
            "fine_lines": "softening fine lines and crow's feet",
            "eye_masks": "instant brightening and de-puffing",
            "gold": "luxury-grade under-eye rejuvenation",
            "lash_serum": "enhancing lash and brow fullness",
            "brow_serum": "framing the eyes with fuller brows",
            "night_repair": "overnight repair and renewal",
            "anti_aging": "reversing visible signs of eye-area aging",
            "de_puffing": "reducing morning puffiness",
        },
        "facial_structure": {
            "facial_roller": "promoting circulation and sculpting",
            "gua_sha": "lymphatic drainage and tension release",
            "sculpting": "defining cheekbones and jawline",
            "microcurrent": "lifting and toning facial muscles",
            "facial_toning": "strengthening supporting facial muscles",
            "face_yoga": "natural muscle training for structure",
            "led_therapy": "stimulating collagen production",
            "collagen": "firming and plumping from within",
            "lymphatic_drainage": "draining puffiness for sharper definition",
            "cheekbone_definition": "enhancing natural cheekbone structure",
            "jaw_sculpting": "carving jawline definition",
        },
        "grooming": {
            "beard": "maintaining a well-groomed beard",
            "grooming": "elevating your daily grooming routine",
            "trimming": "precision trimming for a clean look",
            "beard_oil": "conditioning and softening facial hair",
            "eyebrow": "defining and grooming eyebrows",
            "tweezers": "precision hair removal for a polished look",
            "dermaplaning": "removing peach fuzz for smoother application",
            "exfoliation": "smoothing skin texture",
            "razor": "achieving the closest possible shave",
            "shaving": "irritation-free shaving experience",
        },
        "general": {
            "sleep": "optimising deep sleep for cellular repair",
            "hydration": "ensuring optimal daily water intake",
            "tracking": "building consistency with habit tracking",
            "posture": "aligning body posture for confidence and health",
            "collagen": "supporting skin elasticity and joint health",
            "supplement": "filling nutritional gaps for peak appearance",
            "skincare_education": "building knowledge for long-term results",
            "routine_building": "establishing effective daily routines",
            "deep_sleep": "maximising overnight recovery",
        },
    }

    cat_focus = focus_map.get(category, {})
    for tag in tags:
        if tag in cat_focus:
            return cat_focus[tag]

    # Fallback
    fallbacks = {
        "skin_quality": "skin texture, clarity, and radiance",
        "jawline_definition": "muscle tone and jaw definition",
        "eye_appeal": "brightness and freshness around the eyes",
        "facial_structure": "facial contours and structure",
        "grooming": "a clean, polished appearance",
        "general": "overall health and wellness",
    }
    return fallbacks.get(category, "key areas of improvement")


def get_products_by_category(category: str, tier: Optional[str] = None) -> list[dict]:
    """
    Return all products for a given category, optionally filtered by budget tier.

    Args:
        category: One of "skin_quality", "jawline_definition", "eye_appeal",
                  "facial_structure", "grooming", "general"
        tier: Optional filter: "budget", "mid_range", or "premium"

    Returns:
        List of product dicts (full product objects).
    """
    products = _load_product_database()
    result = [p for p in products if p.get("category") == category]
    if tier:
        result = [p for p in result if p.get("tier") == tier]
    return sorted(result, key=_sort_key_rating, reverse=True)


def get_categories() -> list[dict]:
    """Return all available categories with display names and product counts."""
    products = _load_product_database()
    cat_counts = {}
    for p in products:
        cat = p.get("category", "general")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    return [
        {
            "id": cat,
            "name": CATEGORY_DISPLAY.get(cat, cat.replace("_", " ").title()),
            "product_count": count,
        }
        for cat, count in cat_counts.items()
    ]