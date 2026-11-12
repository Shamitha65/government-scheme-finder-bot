"""
GrantPath - Government Welfare Schemes Matching Engine
Loads verified central & state welfare schemes (scholarships, agriculture, health, housing)
and matches user profiles deterministically.
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
WELFARE_SCHEMES_FILE = BASE_DIR / "data" / "welfare_schemes.json"


def load_welfare_schemes() -> List[Dict[str, Any]]:
    """Loads all verified central and state welfare schemes."""
    if not WELFARE_SCHEMES_FILE.exists():
        # Fallback to parent directory if running from tests
        alt_path = BASE_DIR.parent / "government-scheme-finder-bot" / "data" / "schemes.json"
        if alt_path.exists():
            with open(alt_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    with open(WELFARE_SCHEMES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def match_welfare_schemes(
    profile: Dict[str, Any], schemes: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Deterministically filters and ranks government welfare schemes for a citizen/student profile.
    Returns matched schemes enriched with 'why_eligible' explanations.
    """
    age = int(profile.get("age", 20))
    income = float(profile.get("income", 250000))
    gender = str(profile.get("gender", "All")).strip().lower()
    state = str(profile.get("state", "All India")).strip().lower()
    occupation = str(profile.get("occupation", "Student")).strip().lower()
    is_student = bool(profile.get("is_student", occupation == "student"))
    is_farmer = bool(profile.get("is_farmer", occupation == "farmer"))
    is_disabled = bool(profile.get("is_disabled", False))
    category = str(profile.get("category", "General")).strip().lower()
    marital_status = str(profile.get("marital_status", "Single")).strip().lower()
    keywords_text = str(profile.get("requirements", "")).strip().lower()
    user_words = set(re.findall(r"[a-z0-9]+", keywords_text))

    matched: List[Dict[str, Any]] = []

    for scheme in schemes:
        # 1. State filter (All India or matching state)
        scheme_state = str(scheme.get("state", "All India")).strip()
        if scheme_state.lower() != "all india" and scheme_state.lower() != state:
            continue

        # 2. Age filter
        min_age = scheme.get("minimum_age", 0)
        max_age = scheme.get("maximum_age", 120)
        if age < min_age or age > max_age:
            continue

        # Special sub-eligibility for NSAP Pension (SCH-018)
        if scheme.get("id") == "SCH-018":
            qualifies_old_age = age >= 60
            qualifies_widow = gender == "female" and marital_status == "widowed" and age >= 40
            qualifies_disability = is_disabled and age >= 18
            if not (qualifies_old_age or qualifies_widow or qualifies_disability):
                continue

        # 3. Gender filter
        scheme_gender = str(scheme.get("gender", "All")).strip().lower()
        if scheme_gender != "all" and scheme_gender != gender:
            continue

        # 4. Income limit filter (Senior 70+ exemption on Ayushman Bharat SCH-008)
        income_limit = scheme.get("income_limit")
        senior_ayushman_override = scheme.get("id") == "SCH-008" and age >= 70
        if income_limit is not None and not senior_ayushman_override:
            if income > income_limit:
                continue

        # 5. Student / Farmer / Disability target flags
        if scheme.get("student_only") and not is_student:
            continue
        if scheme.get("farmer_only") and not is_farmer:
            continue
        if scheme.get("disability_only") and not is_disabled:
            continue

        # 6. Category filter
        scheme_cats = scheme.get("category", ["All"])
        if isinstance(scheme_cats, str):
            scheme_cats = [scheme_cats]
        scheme_cats_lower = [c.lower() for c in scheme_cats]
        if "all" not in scheme_cats_lower and category not in scheme_cats_lower:
            continue

        # 7. Marital status filter
        scheme_marital = scheme.get("marital_status", ["All"])
        if isinstance(scheme_marital, str):
            scheme_marital = [scheme_marital]
        scheme_marital_lower = [m.lower() for m in scheme_marital]
        if "all" not in scheme_marital_lower and marital_status not in scheme_marital_lower:
            continue

        # 8. Occupation filter
        scheme_occs = scheme.get("occupation", ["All"])
        if isinstance(scheme_occs, str):
            scheme_occs = [scheme_occs]
        scheme_occs_lower = [o.lower() for o in scheme_occs]
        occ_matches = (
            "all" in scheme_occs_lower
            or occupation in scheme_occs_lower
            or (is_student and "student" in scheme_occs_lower)
            or (is_farmer and "farmer" in scheme_occs_lower)
        )
        if not occ_matches:
            continue

        # Compile reasons why eligible
        reasons = [
            f"Age {age} falls within allowable bracket ({min_age}–{max_age} years).",
            f"Annual income ₹{income:,.0f} meets scheme limit (Max: ₹{income_limit:,.0f})." if income_limit else "No restrictive income ceiling specified.",
            f"Valid for domicile: {scheme.get('state', 'All India')}."
        ]
        if is_student and scheme.get("student_only"):
            reasons.append("Matched target profile: Enrolled student in recognized academic institution.")
        if is_farmer and scheme.get("farmer_only"):
            reasons.append("Matched target profile: Agricultural landholder / cultivator.")
        if is_disabled and scheme.get("disability_only"):
            reasons.append("Matched target profile: Person with benchmark disability (PwD).")

        # Relevance scoring based on user keyword search
        score = 1
        scheme_keywords = [k.lower() for k in scheme.get("keywords", [])]
        scheme_text = (scheme.get("name", "") + " " + scheme.get("description", "") + " " + scheme.get("benefits", "")).lower()

        if user_words:
            matched_keywords = [kw for kw in scheme_keywords if kw in user_words]
            score += len(matched_keywords) * 3
            for w in user_words:
                if w in scheme_text:
                    score += 1

        scheme_copy = dict(scheme)
        scheme_copy["why_eligible"] = reasons
        scheme_copy["relevance_score"] = score
        matched.append(scheme_copy)

    # Sort matched schemes by relevance score descending
    matched.sort(key=lambda s: s.get("relevance_score", 0), reverse=True)
    return matched


def ask_welfare_assistant(question: str, matched_schemes: List[Dict[str, Any]]) -> str:
    """Answers citizen questions regarding welfare schemes using Gemini with strict grounding."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key.startswith("your_"):
        return (
            "To activate AI chat assistance, configure a valid GEMINI_API_KEY in your .env file.\n\n"
            "In the meantime, you can review the verified scheme details, eligibility requirements, "
            "and official application links listed above."
        )

    try:
        client = genai.Client(api_key=api_key)
        model_name = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

        # Provide compact representation of top 5 matched schemes
        compact_context = [
            {
                "id": s.get("id"),
                "name": s.get("name"),
                "target_group": s.get("target_group"),
                "benefits": s.get("benefits"),
                "documents": s.get("documents", []),
                "application_process": s.get("application_process"),
                "official_url": s.get("official_url")
            }
            for s in matched_schemes[:5]
        ]

        prompt = f"""You are the Government Scheme Finder Assistant.
Answer the user's question about Indian government welfare schemes and scholarships clearly, respectfully, and factually.

CRITICAL INSTRUCTIONS:
1. Base your answer strictly on official Indian central/state government procedures and the provided schemes context.
2. If citing a scheme from the context, mention its exact name, required documents, and official portal URL.
3. Keep the response under 150 words and use structured bullet points.

USER QUESTION:
{question}

SCHEMES CONTEXT:
{json.dumps(compact_context, indent=2)}
"""

        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=300
            )
        )
        return (response.text or "No response generated.").strip()
    except Exception as e:
        return f"AI Assistant is currently unavailable: {e}. Please refer to the verified scheme cards above for exact details."
