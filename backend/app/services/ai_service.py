import os
from openai import OpenAI
from app.config import settings
import json

# Initialize OpenAI client for DeepSeek
client = OpenAI(
    api_key=settings.DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)


def analyze_face_with_deepseek(score_data: dict, image_url: str) -> dict:
    """
    Send face analysis to DeepSeek for detailed breakdown and action plan.
    """
    # Build the prompt
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
        response = client.chat.completions.create(
            model="deepseek-v4-pro",
            messages=[
                {"role": "system", "content": "You are an expert facial aesthetics consultant."},
                {"role": "user", "content": prompt}
            ],
            reasoning_effort="high",
            temperature=0.7
        )

        # Parse the JSON response
        result = response.choices[0].message.content
        # Try to extract JSON from the response
        try:
            # Find JSON block if wrapped in code blocks
            if "```json" in result:
                result = result.split("```json")[1].split("```")[0]
            elif "```" in result:
                result = result.split("```")[1].split("```")[0]
            parsed_result = json.loads(result)
            return {"success": True, "data": parsed_result}
        except json.JSONDecodeError:
            # If not valid JSON, return raw text
            return {"success": True, "data": {"raw_analysis": result}}

    except Exception as e:
        return {"success": False, "error": str(e)}


def generate_action_plan(score_data: dict, deepseek_analysis: dict) -> dict:
    """
    Generate a structured 90-day action plan combining scores and AI analysis.
    """
    # Extract data from deepseek analysis
    strengths = deepseek_analysis.get("data", {}).get("strengths", [])
    weaknesses = deepseek_analysis.get("data", {}).get("weaknesses", [])
    skincare = deepseek_analysis.get("data", {}).get("skincare_routine", [])
    grooming = deepseek_analysis.get("data", {}).get("grooming_advice", "")
    exercises = deepseek_analysis.get("data", {}).get("exercise_tips", [])
    diet = deepseek_analysis.get("data", {}).get("diet_advice", [])
    products = deepseek_analysis.get("data", {}).get("recommended_products", [])

    # Build 90-day plan structure
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