"""
Unit tests for GrantPath Rule Engine (tests/test_engine.py).
Tests deterministic evaluation of student profiles against patent/grant support schemes.
"""

import json
from pathlib import Path
import pytest

from engine import (
    Scheme,
    StudentProfile,
    EvaluationStatus,
    WhoApplies,
    SchemeType,
    evaluate_scheme,
    run_engine,
    generate_action_checklist,
)


@pytest.fixture
def sample_schemes():
    schemes_path = Path(__file__).resolve().parent.parent / "schemes.json"
    with open(schemes_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [Scheme(**item) for item in data]


@pytest.fixture
def persona_a():
    """Demo Persona A: 3rd-year CSE, Autonomous college in Karnataka, Working prototype, Has IEDC"""
    return StudentProfile(
        student_status="UG",
        college_type="autonomous",
        state="Karnataka",
        project_domain="IoT Agricultural Sensor",
        project_stage="prototype",
        has_iedc="yes",
        faculty_mentor_available=True,
    )


@pytest.fixture
def persona_b():
    """Demo Persona B: 2nd-year, Non-IEDC, Idea stage"""
    return StudentProfile(
        student_status="UG",
        college_type="VTU-affiliated",
        state="Karnataka",
        project_domain="AI EdTech App",
        project_stage="idea",
        has_iedc="no",
        faculty_mentor_available=True,
    )


def test_persona_a_matches_karnataka_startup(sample_schemes, persona_a):
    """Test 1: Persona A with prototype and IEDC qualifies for Karnataka Startup scheme."""
    karnataka_scheme = next(s for s in sample_schemes if s.id == "karnataka-startup-patent-support")
    eval_result = evaluate_scheme(persona_a, karnataka_scheme)
    # Since other_conditions exist, it should be at least POSSIBLY_ELIGIBLE with no disqualification
    assert eval_result.status in [EvaluationStatus.ELIGIBLE, EvaluationStatus.POSSIBLY_ELIGIBLE]
    assert len(eval_result.reasons) == 0 or "All profile criteria" in eval_result.reasons[0]


def test_persona_b_disqualified_from_karnataka_startup(sample_schemes, persona_b):
    """Test 2: Persona B without IEDC and at idea stage is NOT ELIGIBLE for Karnataka Startup."""
    karnataka_scheme = next(s for s in sample_schemes if s.id == "karnataka-startup-patent-support")
    eval_result = evaluate_scheme(persona_b, karnataka_scheme)
    assert eval_result.status == EvaluationStatus.NOT_ELIGIBLE
    # Must list both missing IEDC and project stage mismatch
    reasons_text = " ".join(eval_result.reasons)
    assert "Missing college IEDC" in reasons_text
    assert "Project stage mismatch" in reasons_text


def test_already_published_destroys_novelty(sample_schemes, persona_a):
    """Test 3: If a project is already published, patent fee support must be NOT ELIGIBLE."""
    published_profile = persona_a.model_copy(update={"project_stage": "already published"})
    kapila = next(s for s in sample_schemes if s.id == "aicte-kapila-patent-support")
    eval_result = evaluate_scheme(published_profile, kapila)
    assert eval_result.status == EvaluationStatus.NOT_ELIGIBLE
    assert any("Novelty is destroyed" in r for r in eval_result.reasons)


def test_state_mismatch_disqualification(sample_schemes, persona_a):
    """Test 4: Out-of-state student cannot access Karnataka-only schemes."""
    delhi_profile = persona_a.model_copy(update={"state": "Delhi"})
    kscst = next(s for s in sample_schemes if s.id == "kscst-ip-technical-assistance")
    eval_result = evaluate_scheme(delhi_profile, kscst)
    assert eval_result.status == EvaluationStatus.NOT_ELIGIBLE
    assert any("State mismatch" in r for r in eval_result.reasons)


def test_kscst_idea_stage_allowed(sample_schemes, persona_b):
    """Test 5: KSCST technical assistance accepts idea stage projects."""
    kscst = next(s for s in sample_schemes if s.id == "kscst-ip-technical-assistance")
    eval_result = evaluate_scheme(persona_b, kscst)
    # KSCST does not require IEDC and supports idea stage
    assert eval_result.status in [EvaluationStatus.ELIGIBLE, EvaluationStatus.POSSIBLY_ELIGIBLE]


def test_iedc_not_sure_becomes_possibly_eligible(sample_schemes, persona_a):
    """Test 6: When IEDC presence is 'not sure', result is POSSIBLY ELIGIBLE with missing info."""
    unsure_profile = persona_a.model_copy(update={"has_iedc": "not sure"})
    karnataka_scheme = next(s for s in sample_schemes if s.id == "karnataka-startup-patent-support")
    eval_result = evaluate_scheme(unsure_profile, karnataka_scheme)
    assert eval_result.status == EvaluationStatus.POSSIBLY_ELIGIBLE
    assert any("Verify with college administration" in m for m in eval_result.missing_info)


def test_scheme_todo_flagged_for_verification(sample_schemes, persona_a):
    """Test 7: Empty TODO skeleton schemes are flagged as POSSIBLY ELIGIBLE with verification note."""
    todo_scheme = next(s for s in sample_schemes if s.id == "scheme-4-todo")
    eval_result = evaluate_scheme(persona_a, todo_scheme)
    assert eval_result.status == EvaluationStatus.POSSIBLY_ELIGIBLE
    assert any("pending official verification" in m for m in eval_result.missing_info)


def test_persona_a_vs_persona_b_distinct_outcomes(sample_schemes, persona_a, persona_b):
    """Test 8: Demo Persona A and B produce distinct evaluation counts."""
    report_a = run_engine(persona_a, sample_schemes)
    report_b = run_engine(persona_b, sample_schemes)

    viable_a_ids = {e.scheme.id for e in (report_a.eligible_schemes + report_a.possibly_eligible_schemes)}
    viable_b_ids = {e.scheme.id for e in (report_b.eligible_schemes + report_b.possibly_eligible_schemes)}

    # Karnataka Startup and KAPILA require prototype/working model and IEDC
    assert "karnataka-startup-patent-support" in viable_a_ids
    assert "karnataka-startup-patent-support" not in viable_b_ids
    assert len(report_a.not_eligible_schemes) < len(report_b.not_eligible_schemes)


def test_action_checklist_generation(sample_schemes, persona_a):
    """Test 9: Action checklist includes numbered, sequential steps and highlights who applies."""
    report = run_engine(persona_a, sample_schemes)
    checklist = report.action_checklist
    assert len(checklist) >= 3
    assert checklist[0].step_number == 1
    assert "Prior-Art" in checklist[0].title
    # Check that institutional coordination mentions IEDC or Institute
    titles = [item.title for item in checklist]
    assert any("Engage College" in t for t in titles)
