"""
DeepSeek AI Service - Experience Layer
Generates personalized action plans, category breakdowns, and motivational messages.
Uses OpenAI-compatible DeepSeek API with professional, coach-like tone.
Includes Redis caching to reduce API costs by ~90%.
"""
import json
import hashlib
import logging
from openai import OpenAI
import redis
from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DeepSeek client (lazy init after config load)
# ---------------------------------------------------------------------------
_client: OpenAI | None = None


def _get_client() -> OpenAI:
    """Return a cached OpenAI client pointed at DeepSeek."""
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
        )
    return _client


# ---------------------------------------------------------------------------
# Redis cache helpers
# ---------------------------------------------------------------------------
_redis: redis.Redis | None = None


def _get_redis() -> redis.Redis:
    """Return a cached Redis connection."""
    global _redis
    if _redis is None:
        redis_url = settings.REDIS_URL
        if redis_url and redis_url != "redis://localhost:6379":
            try:
                _redis = redis.Redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=5)
                _redis.ping()
                logger.info("✅ Redis connected — caching enabled")
            except Exception as exc:
                logger.warning(f"⚠️ Redis connection failed: {exc}")
                _redis = None
        else:
            logger.info("⚠️ Redis unavailable — caching disabled (no REDIS_URL set)")
            _redis = None
    return _redis


def _cache_key(score: float, gender: str, weakest_categories: list[str]) -> str:
    """Generate a deterministic cache key from request parameters."""
    raw = f"{score:.1f}|{gender.lower()}|{','.join(sorted(weakest_categories))}"
    digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"deepseek:plan:{digest}"


def _get_cached_plan(cache_key: str) -> dict | None:
    """Try to retrieve a cached plan from Redis."""
    r = _get_redis()
    if r is None:
        return None
    try:
        cached = r.get(cache_key)
        if cached:
            logger.info(f"Cache HIT: {cache_key}")
            return json.loads(cached)
    except Exception as exc:
        logger.warning(f"Redis get failed: {exc}")
    return None


def _set_cached_plan(cache_key: str, data: dict, ttl: int = 86400):
    """Store a plan in Redis with a 24-hour TTL."""
    r = _get_redis()
    if r is None:
        return
    try:
        r.setex(cache_key, ttl, json.dumps(data))
        logger.info(f"Cache SET: {cache_key} (TTL={ttl}s)")
    except Exception as exc:
        logger.warning(f"Redis set failed: {exc}")


def invalidate_user_cache(user_id: str):
    """Clear all cached plans for a user (call on new photo upload or score change)."""
    r = _get_redis()
    if r is None:
        return
    try:
        pattern = f"deepseek:user:{user_id}:*"
        count = 0
        for key in r.scan_iter(match=pattern):
            r.delete(key)
            count += 1
        if count:
            logger.info(f"Invalidated {count} cache keys for user {user_id}")
    except Exception as exc:
        logger.warning(f"Cache invalidation failed for user {user_id}: {exc}")


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------
def _build_prompt(score: float, gender: str, weakest_categories: list[str]) -> str:
    """Build a professional, encouraging prompt for the DeepSeek model."""

    categories_text = ", ".join(weakest_categories) if weakest_categories else "general presentation"

    return f"""You are a professional appearance and grooming coach. You help people improve their natural appeal through practical, science-backed advice.

Your tone is warm, respectful, and encouraging — like a trusted personal trainer or coach. You never use slang, meme language, or objectifying terms. You address the user as a client who wants to look and feel their best.

---

**Client Profile**
- Appeal score: {score}/100
- Gender: {gender}
- Primary areas to improve: {categories_text}

---

**Instructions**

Please return a single JSON object with exactly these three top-level keys:

1. **"action_plan"** — A 90-day improvement plan divided into 3 phases of 30 days each:
   - *Phase 1 – Foundation (Days 1-30)*: Build core daily habits. Focus on skincare fundamentals, hydration, sleep, and basic grooming.
   - *Phase 2 – Building (Days 31-60)*: Introduce targeted routines for the client's weak areas. Add exercise, nutrition tips, and style guidance.
   - *Phase 3 – Mastery (Days 61-90)*: Refine and personalise. Advanced techniques, consistency, and long-term maintenance strategies.

   For each phase, include:
   - "title": a short, inspiring name
   - "focus": a 1-2 sentence overview
   - "weekly_tasks": an array of 4-6 actionable tasks per week (be specific — name actual products, exercises, or routines where possible)

2. **"motivational_message"** — A personalised, encouraging message (3-5 sentences). Acknowledge the current score honestly, highlight that improvement is achievable with consistency, and inspire confidence. Keep it simple and clear for non-native English speakers.

3. **"category_tips"** — For EACH category in this list: {categories_text}, provide:
   - "category": the category name
   - "current_level": a brief, honest assessment (1 sentence)
   - "target": what good looks like (1 sentence)
   - "daily_actions": 2-3 simple, specific actions the client can do every day
   - "weekly_actions": 1-2 slightly bigger actions for the week
   - "recommended_products": array of 2-3 specific product types or ingredients (do NOT invent brand names unless they are universally known, e.g. "CeraVe cleanser")

---

**Important rules**
- Never use words like Chad, Stacy, GigaChad, mog, looksmax, or any internet slang.
- Use words like appeal, presence, confidence, well-groomed, polished, healthy, vibrant.
- Keep sentences short and easy to understand — many clients are non-native English speakers.
- Be specific but kind. Frame weaknesses as "areas to develop", not flaws.
- Return ONLY the JSON object. No markdown fences, no preamble, no commentary."""


# ---------------------------------------------------------------------------
# Fallback response builder
# ---------------------------------------------------------------------------
def _build_fallback(score: float, gender: str, weakest_categories: list[str]) -> dict:
    """Return a sensible fallback plan when the DeepSeek API is unavailable."""

    pronoun = "he" if gender.lower() == "male" else "she" if gender.lower() == "female" else "they"
    possessive = "his" if gender.lower() == "male" else "her" if gender.lower() == "female" else "their"

    category_tips = []
    for cat in weakest_categories:
        category_tips.append({
            "category": cat,
            "current_level": f"Your {cat.lower()} has room to grow with consistent care.",
            "target": f"A healthier, more defined {cat.lower()} that enhances your natural features.",
            "daily_actions": [
                f"Dedicate 5 minutes to {cat.lower()}-focused care each morning",
                f"Apply products suited to your {cat.lower()} type",
                f"Track changes with weekly photos to monitor progress"
            ],
            "weekly_actions": [
                f"Research one new technique for {cat.lower()} improvement",
                f"Review your {cat.lower()} routine and adjust as needed"
            ],
            "recommended_products": [
                "A quality cleanser matched to your skin type",
                "SPF 30+ sunscreen (daily, rain or shine)",
                "A hydrating moisturiser with niacinamide"
            ]
        })

    return {
        "action_plan": {
            "phase_1": {
                "title": "Foundation – Building Your Routine",
                "focus": "Establish the core daily habits that form the backbone of lasting improvement.",
                "weekly_tasks": [
                    "Cleanse your face morning and night with a gentle cleanser",
                    "Apply SPF 30+ every morning, regardless of weather",
                    "Drink 2-3 litres of water daily",
                    "Aim for 7-8 hours of quality sleep each night",
                    "Take a baseline photo in good natural lighting"
                ]
            },
            "phase_2": {
                "title": "Building – Targeted Improvement",
                "focus": "Introduce specific techniques and products for your priority areas.",
                "weekly_tasks": [
                    "Add a treatment serum (vitamin C in the morning, retinol at night)",
                    "Start a basic exercise routine — 20 minutes, 3 times per week",
                    "Review your diet: reduce processed sugar, increase protein and vegetables",
                    "Practice good posture — shoulders back, chin parallel to the ground",
                    "Experiment with a grooming routine (hair, eyebrows, skincare layering)"
                ]
            },
            "phase_3": {
                "title": "Mastery – Refinement & Sustainability",
                "focus": "Polish your routine and build systems that keep you on track long-term.",
                "weekly_tasks": [
                    "Fine-tune your product lineup based on what's working",
                    "Increase exercise intensity or variety",
                    "Schedule a professional grooming service (barber, facial, stylist)",
                    "Take a progress photo and compare to your baseline",
                    "Set your next 90-day goal based on progress made"
                ]
            }
        },
        "motivational_message": (
            f"Your current appeal score of {score}/100 is a solid starting point — "
            f"and with consistent effort over the next 90 days, {pronoun} can absolutely raise it. "
            f"Every small daily action adds up. Focus on progress, not perfection. "
            f"Many clients see noticeable improvement within the first 4 weeks. "
            f"You've taken the first step. Now let's build on it."
        ),
        "category_tips": category_tips
    }


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------
def generate_personalized_content(
    score: float,
    gender: str,
    weakest_categories: list[str],
) -> dict:
    """
    Generate a personalised action plan, motivational message, and category tips
    using the DeepSeek API.

    Args:
        score: Appeal score (0-100).
        gender: "male", "female", or other.
        weakest_categories: List of category names that need the most improvement.

    Returns:
        dict with keys: success (bool), data (dict containing action_plan,
        motivational_message, category_tips), and optional error (str).
    """
    # Quick validation
    if not isinstance(score, (int, float)) or score < 0 or score > 100:
        return {"success": False, "error": f"Invalid score: {score}. Must be 0-100."}
    if not isinstance(gender, str) or not gender.strip():
        return {"success": False, "error": "Gender is required."}
    if not isinstance(weakest_categories, list):
        return {"success": False, "error": "weakest_categories must be a list."}

    # If no API key is configured, return fallback immediately
    if not settings.DEEPSEEK_API_KEY or settings.DEEPSEEK_API_KEY == "your_api_key_here":
        logger.info("DeepSeek API key not configured — using fallback plan.")
        return {"success": True, "data": _build_fallback(score, gender, weakest_categories), "fallback": True}

    # ── Redis cache check ──
    cache_key = _cache_key(score, gender, weakest_categories)
    cached = _get_cached_plan(cache_key)
    if cached:
        return {"success": True, "data": cached, "cached": True}

    prompt = _build_prompt(score, gender, weakest_categories)

    try:
        client = _get_client()
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a professional appearance and grooming coach. "
                        "You always respond with valid JSON only — no markdown, no code fences, no extra text."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=2048,
            timeout=15.0,
        )

        raw_content = response.choices[0].message.content or ""

        # Strip markdown code fences if present
        cleaned = raw_content.strip()
        if cleaned.startswith("```"):
            # Remove opening fence (```json or ```)
            cleaned = cleaned.split("\n", 1)[-1] if "\n" in cleaned else cleaned[3:]
            # Remove closing fence
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("DeepSeek returned non-JSON content. Attempting extraction.")
            # Last resort: try to find JSON object in the response
            brace_start = raw_content.find("{")
            brace_end = raw_content.rfind("}")
            if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
                try:
                    parsed = json.loads(raw_content[brace_start:brace_end + 1])
                except json.JSONDecodeError:
                    return {
                        "success": False,
                        "error": "DeepSeek response could not be parsed as JSON.",
                        "raw": raw_content[:500],
                    }
            else:
                return {
                    "success": False,
                    "error": "DeepSeek response contained no JSON object.",
                    "raw": raw_content[:500],
                }

        # Validate required keys exist
        required_keys = {"action_plan", "motivational_message", "category_tips"}
        missing = required_keys - set(parsed.keys())
        if missing:
            logger.warning(f"DeepSeek response missing keys: {missing}. Merging with fallback.")
            fallback = _build_fallback(score, gender, weakest_categories)
            for key in missing:
                parsed[key] = fallback[key]

        # ── Cache the successful result ──
        _set_cached_plan(cache_key, parsed)

        return {"success": True, "data": parsed}

    except TimeoutError:
        logger.warning("⚠️ DeepSeek API timeout — using fallback plan")
        return {
            "success": True,
            "data": _build_fallback(score, gender, weakest_categories),
            "fallback": True,
            "error_detail": "API timed out after 15s",
        }
    except Exception as exc:
        logger.error(f"DeepSeek API call failed: {exc}")
        # Return fallback on any error so the app keeps working
        return {
            "success": True,
            "data": _build_fallback(score, gender, weakest_categories),
            "fallback": True,
            "error_detail": str(exc)[:200],
        }
