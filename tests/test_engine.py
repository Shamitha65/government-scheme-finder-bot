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
    extract_document_text,
    parse_document_sections,
    analyze_project_documentation,
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


def test_areca_nut_leaf_disease_organization_matching(sample_schemes):
    """
    Test 10: User's Areca Nut Leaf Disease Detection project scenario:
    - 1st Org (General Problem Statement, e.g. MSME): ELIGIBLE
    - 2nd Org (Plant/Animal/Agriculture, e.g. ICAR-RAFTAAR): ELIGIBLE
    - 3rd Org (AI/ML Only, e.g. MeitY TIDE 2.0): POSSIBLY ELIGIBLE (Applied Tech Track)
    - 4th Org (Cybersecurity Only, e.g. C3iHub): NOT ELIGIBLE (Disqualified)
    - 5th Org (FinTech Only, e.g. RBIH): NOT ELIGIBLE (Disqualified)
    """
    areca_profile = StudentProfile(
        student_status="UG",
        college_type="autonomous",
        state="Karnataka",
        project_title="Areca Nut Leaf Disease Detection using Deep Learning",
        project_domain="Agriculture, Plant & Animal Sciences / Crop Protection",
        project_stage="prototype",
        has_iedc="yes",
        faculty_mentor_available=True,
        selected_sdgs=["SDG 2: Zero Hunger", "SDG 15: Life on Land"],
        funding_amount_required=200000.0,
        abstract="Deep learning convolutional neural network pipeline for early detection of areca nut yellow leaf and koleroga diseases directly from field leaf imagery.",
        technical_approach="Custom CNN and YOLOv8 model trained on 5,000 Karnataka field images with mobile deployment.",
        innovation_novelty="Lightweight offline edge inference model designed for low-connectivity farm environments."
    )
    report = run_engine(areca_profile, sample_schemes)

    eligible_ids = {e.scheme.id for e in report.eligible_schemes}
    possible_ids = {e.scheme.id for e in report.possibly_eligible_schemes}
    disqualified_ids = {e.scheme.id for e in report.not_eligible_schemes}

    # 1. General Problem Statement orgs approved
    assert "msme-idea-hackathon" in eligible_ids
    assert "dst-nidhi-prayas-prototype-grant" in eligible_ids

    # 2. Plant / Agriculture orgs approved
    assert "icar-raftaar-agribi-grant" in eligible_ids
    assert "nabard-rural-innovation-fund" in eligible_ids

    # 3. AI/ML only orgs partially approved under Applied Tech track
    assert "meity-tide-2-innovation-grant" in possible_ids or "meity-tide-2-innovation-grant" in eligible_ids
    assert "meity-genesis-deeptech-support" in possible_ids or "meity-genesis-deeptech-support" in eligible_ids

    # 4. Cybersecurity strictly disqualified
    assert "c3ihub-cybersecurity-grant" in disqualified_ids
    assert "dsci-cyber-bharat-grant" in disqualified_ids

    # 5. FinTech strictly disqualified
    assert "rbih-swanidhi-fintech-grant" in disqualified_ids
    assert "ifsca-gift-city-fintech-grant" in disqualified_ids


def test_docx_and_pdf_text_extraction():
    """Test 11: Text extraction from in-memory Word and PDF byte streams."""
    import io

    # Test DOCX
    import docx
    d = docx.Document()
    d.add_heading("Automated Detection of Areca Nut Foliar Blight", level=1)
    d.add_paragraph("Abstract: Early stage identification using transfer learning on field cameras.")
    d.add_paragraph("Methodology: Deep CNN MobileNetV3 trained with focal loss.")
    docx_buf = io.BytesIO()
    d.save(docx_buf)
    docx_bytes = docx_buf.getvalue()

    extracted_docx = extract_document_text(docx_bytes, "areca_study.docx")
    assert "Automated Detection" in extracted_docx
    assert "MobileNetV3" in extracted_docx

    # Test PDF
    from pypdf import PdfWriter
    w = PdfWriter()
    w.add_blank_page(width=72, height=72)
    pdf_buf = io.BytesIO()
    w.write(pdf_buf)
    pdf_bytes = pdf_buf.getvalue()
    extracted_pdf = extract_document_text(pdf_bytes, "project_doc.pdf")
    assert isinstance(extracted_pdf, str)


def test_uploaded_document_evaluates_readiness():
    """Test 12: Uploaded document text triggers comprehensive dossier scoring and section parsing."""
    doc_sample = (
        "Project Report: Solar-Powered IoT Irrigation and Crop Disease Monitoring System\n\n"
        "Abstract: This research addresses water scarcity and crop pests by proposing an autonomous edge AI node. "
        "The system achieved 94.2% accuracy in real-time pest diagnosis while reducing water usage by 38% across test farms.\n\n"
        "Literature Survey: Prior art in precision agriculture relies heavily on cloud-connected sensors which fail in low-bandwidth rural setups. "
        "Recent benchmarks from IEEE Transactions on Agri-Informatics show latency exceeding 12 seconds.\n\n"
        "Technical Approach: We designed a custom PCB housing an ESP32 microcontroller interfaced with multispectral cameras, soil moisture probes, "
        "and a lightweight quantized CNN deployed on an onboard neural accelerator.\n\n"
        "Innovation and Novelty: Unlike conventional cloud telemetry, our system operates 100% offline with zero cloud dependency. "
        "The novel dual-spectrum filtering algorithm separates specular glare from leaf lesions.\n\n"
        "Existing Solutions: Existing commercial drip timers lack adaptive vision feedback, leading to over-watering and fungal spread.\n\n"
        "References and Citations:\n"
        "1. K. Rao et al., 'Edge AI in Smart Agriculture', IEEE IoT Journal, 2023.\n"
        "2. S. Patel, 'Low-Power Vision Sensors for Crop Protection', AgriTech Conf, 2024."
    )

    sections = parse_document_sections(doc_sample)
    assert len(sections["abstract"]) > 0
    assert len(sections["technical_approach"]) > 0
    assert len(sections["innovation_novelty"]) > 0

    profile = StudentProfile(
        student_status="UG",
        college_type="autonomous",
        state="Karnataka",
        project_title="Solar IoT Irrigation",
        project_domain="Agriculture, Plant & Animal Sciences / Crop Protection",
        project_stage="prototype",
        has_iedc="yes",
        uploaded_document_name="Solar_IoT_Project.docx",
        uploaded_document_text=doc_sample,
        uploaded_document_size_kb=45.2,
    )

    eval_result = analyze_project_documentation(profile)
    assert eval_result["score"] >= 80
    assert "Ready for Grant Screening" in eval_result["verdict"]
    assert any("Solar_IoT_Project.docx" in s for s in eval_result["strengths"])
