"""
Unit tests for extractor.py and storage functionality.
"""

import json
from pathlib import Path
from engine import Scheme, SchemeType, WhoApplies, ConfidenceLevel, Eligibility, Benefit
from extractor import extract_scheme_from_text, save_scheme_to_store


def test_extract_scheme_empty_input():
    """Verify extractor returns clean error on empty input."""
    scheme, err = extract_scheme_from_text("   ")
    assert scheme is None
    assert "empty" in err.lower()


def test_save_scheme_to_store_creates_and_updates(tmp_path):
    """Verify save_scheme_to_store appends and updates in schemes.json."""
    filepath = str(tmp_path / "schemes.json")

    mock_scheme = Scheme(
        id="test-grant-scheme",
        name="Test Innovation Grant",
        authority="Test Science Council",
        type=SchemeType.GRANT,
        who_applies=WhoApplies.STUDENT,
        eligibility=Eligibility(
            applicant_status=["UG", "PG"],
            college_types=["autonomous"],
            states=["Karnataka"],
            project_stages=["prototype"],
            requires_iedc=False,
            other_conditions=["Must have guide approval"]
        ),
        benefit=Benefit(
            description="Up to Rs. 2,00,000 prototype grant",
            amount_inr=200000.0,
            notes="Direct milestone release"
        ),
        documents_required=["Project Proposal", "Student ID"],
        deadline="2026-12-31",
        application_steps=["Submit online", "Interview"],
        source_url="https://example.gov.in/test",
        last_verified="2026-11-12",
        confidence=ConfidenceLevel.NEEDS_VERIFICATION
    )

    # 1. Save new
    success, msg = save_scheme_to_store(mock_scheme, filepath=filepath)
    assert success is True
    assert "Appended" in msg

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) == 1
    assert data[0]["id"] == "test-grant-scheme"
    assert data[0]["benefit"]["amount_inr"] == 200000.0

    # 2. Update existing
    updated_scheme = mock_scheme.model_copy(
        update={"benefit": Benefit(description="Updated description", amount_inr=250000.0)}
    )
    success2, msg2 = save_scheme_to_store(updated_scheme, filepath=filepath)
    assert success2 is True
    assert "Updated" in msg2

    with open(filepath, "r", encoding="utf-8") as f:
        data2 = json.load(f)
    assert len(data2) == 1
    assert data2[0]["benefit"]["amount_inr"] == 250000.0
