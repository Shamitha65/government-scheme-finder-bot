"""
GrantPath - LLM Scheme Extraction & Grounded Explanation Module
Uses Google Gemini API (`google-genai` SDK) to parse raw scheme notifications
into Pydantic-validated Scheme models, and provide grounded result explanations.
"""

import json
import logging
import os
import re
from datetime import date
from typing import Any, Dict, Optional, Tuple

from dotenv import load_dotenv
from google import genai
from google.genai import types

from engine import (
    Scheme,
    SchemeType,
    WhoApplies,
    ConfidenceLevel,
    StudentProfile,
    EvaluationReport,
)

load_dotenv()
logger = logging.getLogger(__name__)

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")


def get_gemini_client() -> Tuple[Optional[genai.Client], Optional[str]]:
    """
    Returns an initialized Gemini Client if GEMINI_API_KEY is present and valid.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    placeholders = {"", "your_gemini_api_key_here", "none", "null"}
    if api_key.lower() in placeholders:
        return None, "GEMINI_API_KEY is missing or set to placeholder in .env"
    try:
        client = genai.Client(api_key=api_key)
        return client, None
    except Exception as e:
        return None, f"Failed to initialize Gemini Client: {e}"


EXTRACTION_SYSTEM_INSTRUCTION = """You are a strict, factual information extraction specialist for Indian patent and academic grant schemes.
Extract ONLY facts explicitly present in the provided notification or website text.

CRITICAL RULES:
1. Do NOT guess, extrapolate, or invent deadlines, eligibility criteria, monetary amounts, or URLs.
2. If any field is NOT explicitly mentioned in the text, you MUST set it to null (or an empty list [] for array fields).
3. 'type' MUST be exactly one of: 'patent_fee_support', 'grant', 'technical_assistance'.
4. 'who_applies' MUST be exactly one of: 'student', 'iedc', 'institute', 'faculty'.
5. 'confidence' MUST ALWAYS be set to 'needs_verification'.
6. Return a valid JSON object matching the exact schema provided.
"""

EXTRACTION_SCHEMA_PROMPT = """JSON SCHEMA:
{
  "id": "kebab-case-unique-identifier",
  "name": "Full official name of the scheme",
  "authority": "Government agency, ministry, or council offering the scheme",
  "type": "patent_fee_support" | "grant" | "technical_assistance",
  "who_applies": "student" | "iedc" | "institute" | "faculty",
  "eligibility": {
    "applicant_status": ["UG", "PG", "PhD", ...],
    "college_types": ["autonomous", "VTU-affiliated", "other", ...],
    "states": ["Karnataka", ...],
    "project_stages": ["idea", "prototype", "working model", ...],
    "requires_iedc": true | false | null,
    "other_conditions": ["any specific institutional or project conditions explicitly mentioned"]
  },
  "benefit": {
    "description": "Clear description of support provided",
    "amount_inr": number | null,
    "notes": "Specific disbursement or reimbursement details"
  },
  "documents_required": ["document 1", "document 2"],
  "deadline": "YYYY-MM-DD or specific deadline text" | null,
  "application_steps": ["Step 1", "Step 2", "Step 3"],
  "source_url": "Official URL where information was published",
  "last_verified": "YYYY-MM-DD",
  "confidence": "needs_verification"
}
"""


def extract_scheme_from_text(
    raw_text: str, source_url: str = ""
) -> Tuple[Optional[Scheme], Optional[str]]:
    """
    Extracts structured Scheme JSON from raw official text using Gemini.
    Validates with Pydantic Scheme model before returning.
    Returns (Scheme, None) on success or (None, error_message) on failure.
    """
    trimmed = raw_text.strip()
    if not trimmed:
        return None, "Input scheme text is empty. Please paste the official scheme notification."

    client, err = get_gemini_client()
    if not client:
        return None, err or "Gemini API client unavailable."

    model_name = os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
    today_str = date.today().isoformat()

    user_prompt = f"""Official Source URL: {source_url or 'Not specified'}
Today's Date: {today_str}

Please extract the scheme details from the text below according to the schema:
---
{trimmed}
---
{EXTRACTION_SCHEMA_PROMPT}
"""

    # Try configured model first, followed by resilient fallbacks
    candidate_models = [model_name]
    for alt in ["gemini-3.5-flash-lite", "gemini-3.1-pro-preview"]:
        if alt not in candidate_models:
            candidate_models.append(alt)

    response = None
    last_err = None
    import time

    for candidate in candidate_models:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=candidate,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=EXTRACTION_SYSTEM_INSTRUCTION,
                        temperature=0.0,
                        response_mime_type="application/json",
                    ),
                )
                if response and (response.text or "").strip():
                    break
            except Exception as exc:
                last_err = exc
                if "503" in str(exc) or "UNAVAILABLE" in str(exc):
                    time.sleep(1.0)
                    continue
                break
        if response and (response.text or "").strip():
            break

    if not response or not (response.text or "").strip():
        return None, f"Extraction failed: {last_err or 'Empty response from model'}"

    try:
        output_text = (response.text or "").strip()

        data = json.loads(output_text)

        # Ensure sensible defaults if LLM omitted them
        if not data.get("source_url") and source_url:
            data["source_url"] = source_url
        if not data.get("last_verified"):
            data["last_verified"] = today_str
        data["confidence"] = "needs_verification"

        # Validate with Pydantic model
        validated_scheme = Scheme(**data)
        return validated_scheme, None

    except json.JSONDecodeError as jde:
        return None, f"Failed to parse LLM response as JSON: {jde}"
    except Exception as exc:
        return None, f"Extraction failed: {exc}"


def explain_evaluation_results(
    profile: StudentProfile, report: EvaluationReport
) -> str:
    """
    Generates a concise, plain-English summary of the student's evaluation results.
    Strictly grounded in the matched Scheme JSON data.
    """
    client, _ = get_gemini_client()
    model_name = os.getenv("GEMINI_MODEL", DEFAULT_MODEL)

    eligible_summary = [
        {
            "name": e.scheme.name,
            "who_applies": e.scheme.who_applies.value,
            "type": e.scheme.type.value,
            "benefit": e.scheme.benefit.description,
            "documents": e.scheme.documents_required,
        }
        for e in report.eligible_schemes
    ]

    possible_summary = [
        {
            "name": e.scheme.name,
            "who_applies": e.scheme.who_applies.value,
            "missing_info": e.missing_info,
        }
        for e in report.possibly_eligible_schemes
    ]

    not_eligible_summary = [
        {
            "name": e.scheme.name,
            "disqualifications": e.reasons,
        }
        for e in report.not_eligible_schemes
    ]

    # Fallback template if Gemini is unavailable
    fallback_text = (
        f"**Summary for {profile.student_status} Student ({profile.college_type}, {profile.state})**:\n\n"
        f"• **Directly Eligible Schemes ({len(report.eligible_schemes)})**: "
        f"{', '.join(e.scheme.name for e in report.eligible_schemes) if report.eligible_schemes else 'None at this stage.'}\n"
        f"• **Conditionally / Possibly Eligible Schemes ({len(report.possibly_eligible_schemes)})**: "
        f"{', '.join(e.scheme.name for e in report.possibly_eligible_schemes) if report.possibly_eligible_schemes else 'None.'}\n"
        f"• **Next Crucial Step**: Review the action checklist below. Ensure you do not publicly disclose "
        f"your project until provisional patent documentation is drafted."
    )

    if not client:
        return fallback_text

    prompt = f"""You are the GrantPath Navigator Advisor. Explain the following student evaluation results in clear, encouraging, plain English.
CRITICAL CONSTRAINT: Base your explanation ONLY on the provided JSON data. Never make outside claims or invent benefits.

STUDENT PROFILE:
- Status: {profile.student_status}
- College: {profile.college_type} in {profile.state}
- Project Stage: {profile.project_stage}
- Has IEDC: {profile.has_iedc}
- Mentor Available: {profile.faculty_mentor_available}

EVALUATION DATA:
- Eligible Schemes: {json.dumps(eligible_summary)}
- Possibly Eligible Schemes: {json.dumps(possible_summary)}
- Not Eligible Schemes: {json.dumps(not_eligible_summary)}

Highlight:
1. Which schemes they can pursue right now and WHO must apply (student, IEDC, or institute).
2. What specific gap or verification is needed for any 'Possibly Eligible' schemes.
3. The most critical immediate action regarding prior art and non-disclosure.
Keep response under 200 words. Format with clean bullet points.
"""

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=350,
            ),
        )
        return (response.text or fallback_text).strip()
    except Exception as exc:
        logger.warning("Gemini explanation failed (%s); using fallback.", exc)
        return fallback_text


def save_scheme_to_store(scheme: Scheme, filepath: str = "schemes.json") -> Tuple[bool, str]:
    """
    Appends or updates a verified Scheme object into the local schemes.json file.
    """
    try:
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = []

        # Convert scheme to dict
        scheme_dict = scheme.model_dump(mode="json")

        # Replace existing if ID matches, else append
        existing_idx = next((i for i, s in enumerate(data) if s.get("id") == scheme.id), None)
        if existing_idx is not None:
            data[existing_idx] = scheme_dict
            msg = f"Updated existing scheme '{scheme.name}' (ID: {scheme.id})."
        else:
            data.append(scheme_dict)
            msg = f"Appended new scheme '{scheme.name}' (ID: {scheme.id}) to schemes.json."

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return True, msg
    except Exception as e:
        return False, f"Failed to save scheme to {filepath}: {e}"
