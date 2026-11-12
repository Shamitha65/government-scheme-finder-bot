"""
Unit tests for Government Welfare Schemes Matching Engine (tests/test_welfare_engine.py).
"""

from welfare_engine import load_welfare_schemes, match_welfare_schemes


def test_load_welfare_schemes():
    schemes = load_welfare_schemes()
    assert len(schemes) >= 15
    ids = [s["id"] for s in schemes]
    assert "SCH-001" in ids  # CSSS Scholarship
    assert "SCH-008" in ids  # Ayushman Bharat


def test_student_welfare_matches():
    schemes = load_welfare_schemes()
    profile = {
        "age": 19,
        "income": 200000,
        "state": "Karnataka",
        "gender": "Female",
        "occupation": "Student",
        "category": "General",
        "marital_status": "Single",
        "is_student": True,
        "is_farmer": False,
        "is_disabled": False,
        "requirements": "scholarship tuition",
    }
    matches = match_welfare_schemes(profile, schemes)
    matched_ids = [m["id"] for m in matches]
    # CSSS scholarship (SCH-001) must match student under income cap
    assert "SCH-001" in matched_ids
    # PM-KISAN (farmer-only) must NOT match
    assert "SCH-006" not in matched_ids


def test_farmer_welfare_matches():
    schemes = load_welfare_schemes()
    profile = {
        "age": 45,
        "income": 100000,
        "state": "Karnataka",
        "gender": "Male",
        "occupation": "Farmer",
        "category": "OBC",
        "marital_status": "Married",
        "is_student": False,
        "is_farmer": True,
        "is_disabled": False,
        "requirements": "agriculture",
    }
    matches = match_welfare_schemes(profile, schemes)
    matched_ids = [m["id"] for m in matches]
    # PM-KISAN (SCH-006) and PMFBY (SCH-007) must match
    assert "SCH-006" in matched_ids
    assert "SCH-007" in matched_ids
    # CSSS student scholarship must NOT match
    assert "SCH-001" not in matched_ids


def test_all_official_urls_present():
    schemes = load_welfare_schemes()
    for s in schemes:
        url = s.get("official_url", "")
        assert url.startswith("http://") or url.startswith("https://")
        assert "example.gov.in" not in url
