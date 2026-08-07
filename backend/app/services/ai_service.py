import os
import json
import time
import logging
from openai import OpenAI
from app.config import settings

logger = logging.getLogger(__name__)

# Timeout in seconds for DeepSeek API calls
DEEPSEEK_TIMEOUT_SECONDS = 25

# Initialize OpenAI client for DeepSeek
client = OpenAI(
    api_key=settings.DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com",
    timeout=DEEPSEEK_TIMEOUT_SECONDS,
)


def analyze_face_with_deepseek(score_data: dict, image_url: str) -> dict:
    """
    Send face analysis to DeepSeek for detailed breakdown.

    Uses deepseek-chat (fast model) with 25s timeout.
    If DeepSeek is unavailable or times out, returns template-based fallback.
    """
    prompt = f"""
    You are an expert facial aesthetics and grooming consultant.
    
    I have analyzed a user's face and gathered the following data:
    - Overall attractiveness score: {score_data.get('overall_score', 70)}/100
    - Symmetry score: {score_data.get('symmetry_score', 70)}/100
    - Skin quality score: {score_data.get('skin_score', 70)}/100
    - Jawline definition score: {score_data.get('jawline_score', 70)}/100
    - Eye symmetry score: {score_data.get('eye_score', 70)}/100
    - Face shape: {score_data.get('face_shape', 'Oval')}
    
    Based on this data, provide:
    
    1. TOP 3 STRENGTHS: What are this person's best facial features?
    2. TOP 3 WEAKNESSES: What needs the most improvement?
    3. ACTIONABLE ADVICE: Specific, practical steps for improvement in:
       - Skincare (products, routine)
       - Grooming (hair, beard/eyebrows)
       - Exercise (jawline, posture)
       - Diet (what to eat/avoid)
    
    4. A 7-DAY STARTER PLAN: Day-by-day tasks for week 1.
    
    5. IMPROVEMENT POTENTIAL: How many points they can realistically improve in 90 days.
    
    Be specific, practical, and encouraging. Use product names when recommending skincare.
    Return the response as JSON with these keys:
    - strengths (array of 3)
    - weaknesses (array of 3)
    - skincare_routine (array of steps)
    - grooming_advice (string)
    - exercise_tips (array)
    - diet_advice (array)
    - seven_day_plan (array of 7 days, each with tasks)
    - improvement_potential (string)
    - recommended_products (array of {{name, category, reason}})
    """

    try:
        start = time.time()
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are an expert facial aesthetics consultant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000,
        )
        elapsed = (time.time() - start) * 1000
        logger.info(f"DeepSeek analysis completed in {elapsed:.0f}ms")

        result = response.choices[0].message.content
        try:
            if "```json" in result:
                result = result.split("```json")[1].split("```")[0]
            elif "```" in result:
                result = result.split("```")[1].split("```")[0]
            parsed_result = json.loads(result)
            return {"success": True, "data": parsed_result, "source": "deepseek"}
        except json.JSONDecodeError:
            return {"success": True, "data": {"raw_analysis": result}, "source": "deepseek"}

    except Exception as e:
        logger.warning(f"DeepSeek analysis failed (falling back to template): {e}")
        return {"success": False, "error": str(e), "source": "fallback"}


def generate_fallback_analysis(score_data: dict) -> dict:
    """
    Generate template-based analysis without calling DeepSeek.
    Returns immediately (<1ms) with sensible defaults based on scores.
    """
    overall = score_data.get("overall_score", 70)
    symmetry = score_data.get("symmetry_score", 70)
    skin = score_data.get("skin_score", 70)
    jawline = score_data.get("jawline_score", 70)
    eyes = score_data.get("eye_score", 70)
    face_shape = score_data.get("face_shape", "Oval")

    # Score-based templates
    if overall >= 80:
        strengths = [
            "Excellent facial structure and proportions",
            f"Well-defined {face_shape} face shape",
            "Strong overall facial harmony"
        ]
        weaknesses = [
            "Minor asymmetry that can be improved with targeted exercises",
            "Potential for enhanced skin radiance",
            "Jawline definition could be further refined"
        ]
        potential = "10-15 points improvement possible in 90 days with consistent effort"
    elif overall >= 60:
        strengths = [
            "Good foundation for improvement",
            f"Distinct {face_shape} face shape with character",
            "Balanced eye positioning"
        ]
        weaknesses = [
            "Skin quality needs improvement",
            "Facial asymmetry can be addressed",
            "Jawline definition requires work"
        ]
        potential = "15-25 points improvement possible in 90 days with dedicated routine"
    else:
        strengths = [
            "Every face has potential for dramatic improvement",
            "Commitment to change is the strongest foundation",
            "Individual features with character"
        ]
        weaknesses = [
            "Skin quality needs significant attention",
            "Facial symmetry exercises recommended",
            "Overall grooming routine should be established"
        ]
        potential = "25-35+ points improvement possible in 90 days with consistent effort"

    # Skin routine based on skin score
    if skin >= 75:
        skincare_routine = [
            "AM: Gentle cleanse → Vitamin C serum → SPF 50",
            "PM: Double cleanse → Retinol (alternate nights) → Night cream",
            "Weekly: Chemical exfoliation (AHA/BHA)"
        ]
    elif skin >= 50:
        skincare_routine = [
            "AM: Cleanse → Moisturiser with SPF 30",
            "PM: Double cleanse → Moisturiser",
            "Weekly: Gentle exfoliation"
        ]
    else:
        skincare_routine = [
            "AM: Gentle cleanser → Light moisturiser → SPF 30",
            "PM: Cleanse → Niacinamide serum → Moisturiser",
            "Weekly: Gentle physical exfoliation"
        ]

    # Grooming advice
    grooming_advice = "Keep eyebrows well-groomed, maintain a clean hairstyle that suits your face shape, and ensure facial hair (if any) is trimmed and shaped."

    # Exercise tips based on jawline score
    if jawline >= 75:
        exercise_tips = [
            "Maintain tongue posture (mewing) throughout the day",
            "Gua sha facial massage 3 min daily",
            "Neck stretches for posture maintenance"
        ]
    elif jawline >= 50:
        exercise_tips = [
            "Chew sugar-free mastic gum 15 min daily (alternate sides)",
            "Practice tongue posture (mewing)",
            "Jaw resistance exercises 3x/week",
            "Chin tucks for neck posture"
        ]
    else:
        exercise_tips = [
            "Chew mastic gum 20 min daily",
            "Consistent tongue posture practice",
            "Jawzrsize or similar resistance training",
            "Daily neck and chin exercises"
        ]

    # Diet advice
    diet_advice = [
        "Drink 2-3 litres of water daily",
        "Eat protein with every meal (1.6g/kg bodyweight)",
        "Reduce processed sugar and fried foods",
        "Include collagen-rich foods (bone broth, fish, eggs)",
        "Eat antioxidant-rich fruits and vegetables daily"
    ]

    # 7-day starter plan
    seven_day_plan = [
        {"day": 1, "tasks": ["Start AM cleanse + SPF routine", "Drink 2L water", "Take baseline progress photo"]},
        {"day": 2, "tasks": ["Establish PM skincare routine", "Chew gum 15 min", "8 hours sleep"]},
        {"day": 3, "tasks": ["Full AM + PM routine", "Start tongue posture practice", "Walk 8,000 steps"]},
        {"day": 4, "tasks": ["Maintain skincare routine", "Jawline exercises", "Reduce sugar intake"]},
        {"day": 5, "tasks": ["Full routine", "Neck posture exercises", "Protein with every meal"]},
        {"day": 6, "tasks": ["Gentle exfoliation", "Gua sha massage", "Meal prep for the week"]},
        {"day": 7, "tasks": ["Review first week progress", "Plan next week's routine", "Rest and recover"]},
    ]

    recommended_products = [
        {"name": "Cerave Hydrating Cleanser", "category": "skincare", "reason": "Gentle, non-stripping cleanser for all skin types"},
        {"name": "La Roche-Posay Anthelios SPF 50", "category": "skincare", "reason": "Essential daily sun protection"},
        {"name": "The Ordinary Niacinamide 10% + Zinc 1%", "category": "skincare", "reason": "Reduces inflammation and evens skin tone"},
        {"name": "Mastic Gum (Chios)", "category": "exercise", "reason": "Natural jaw exercise for definition"},
        {"name": "Rose Quartz Gua Sha Stone", "category": "tool", "reason": "Facial massage for circulation and definition"},
    ]

    return {
        "success": True,
        "source": "template",
        "data": {
            "strengths": strengths,
            "weaknesses": weaknesses,
            "skincare_routine": skincare_routine,
            "grooming_advice": grooming_advice,
            "exercise_tips": exercise_tips,
            "diet_advice": diet_advice,
            "seven_day_plan": seven_day_plan,
            "improvement_potential": potential,
            "recommended_products": recommended_products,
        }
    }


def generate_action_plan(score_data: dict, deepseek_analysis: dict) -> dict:
    """
    Generate a structured 90-day action plan combining scores and AI analysis.
    """
    data = deepseek_analysis.get("data", {})
    strengths = data.get("strengths", [])
    weaknesses = data.get("weaknesses", [])
    skincare = data.get("skincare_routine", [])
    grooming = data.get("grooming_advice", "")
    exercises = data.get("exercise_tips", [])
    diet = data.get("diet_advice", [])
    products = data.get("recommended_products", [])

    plan = {
        "total_days": 90,
        "phases": {
            "week_1": {
                "title": "Foundation: Skincare Reset",
                "tasks": skincare[:5] if skincare else ["Cleanse twice daily", "Apply SPF", "Stay hydrated"]
            },
            "week_2_4": {
                "title": "Building: Grooming & Diet",
                "tasks": [grooming] + diet[:2] if grooming else ["Start grooming routine", "Improve diet"]
            },
            "week_5_8": {
                "title": "Advanced: Jawline & Posture",
                "tasks": exercises[:3] if exercises else ["Jawline exercises", "Posture correction"]
            },
            "week_9_12": {
                "title": "Mastery: Maintenance & Refinement",
                "tasks": ["Review progress", "Adjust routine", "Maintain results"]
            }
        },
        "products": products[:5],
        "weaknesses": weaknesses,
        "strengths": strengths
    }

    return plan