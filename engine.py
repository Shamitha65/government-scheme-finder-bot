"""
GrantPath - Pure Python Rule-Matching Engine
Deterministic, fully unit-testable evaluation of student project profiles against
government and organization patent-filing, grant, and funding schemes.
"""

from enum import Enum
import re
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class SchemeType(str, Enum):
    PATENT_FEE_SUPPORT = "patent_fee_support"
    GRANT = "grant"
    TECHNICAL_ASSISTANCE = "technical_assistance"
    FELLOWSHIP = "fellowship"
    INCUBATION_SEED = "incubation_seed"


class WhoApplies(str, Enum):
    STUDENT = "student"
    IEDC = "iedc"
    INSTITUTE = "institute"
    FACULTY = "faculty"


class ConfidenceLevel(str, Enum):
    VERIFIED = "verified"
    NEEDS_VERIFICATION = "needs_verification"


class Benefit(BaseModel):
    description: str
    amount_inr: Optional[float] = None
    notes: str = ""


class Eligibility(BaseModel):
    applicant_status: List[str] = Field(default_factory=list)
    college_types: List[str] = Field(default_factory=list)
    states: List[str] = Field(default_factory=list)
    project_stages: List[str] = Field(default_factory=list)
    requires_iedc: Optional[bool] = None
    other_conditions: List[str] = Field(default_factory=list)
    # Organization domain and theme matching rules:
    domains: List[str] = Field(default_factory=list)
    technology_keywords: List[str] = Field(default_factory=list)
    target_sdgs: List[str] = Field(default_factory=list)
    open_theme: bool = False
    min_amount_inr: Optional[float] = None
    max_amount_inr: Optional[float] = None
    requires_faculty: Optional[bool] = None


class Scheme(BaseModel):
    id: str
    name: str
    authority: str
    type: SchemeType
    who_applies: WhoApplies
    eligibility: Eligibility
    benefit: Benefit
    documents_required: List[str] = Field(default_factory=list)
    deadline: Optional[str] = None
    application_steps: List[str] = Field(default_factory=list)
    source_url: str
    last_verified: str
    confidence: ConfidenceLevel


class EvaluationStatus(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    POSSIBLY_ELIGIBLE = "POSSIBLY ELIGIBLE"
    NOT_ELIGIBLE = "NOT ELIGIBLE"


class StudentProfile(BaseModel):
    student_status: str  # "UG", "PG", "PhD"
    college_type: str    # "autonomous", "VTU-affiliated", "other"
    state: str           # "Karnataka", etc.
    project_domain: str  # e.g. "Agriculture, Plant & Animal Sciences / Crop Protection"
    project_stage: str   # "idea", "prototype", "working model", "already published"
    has_iedc: str        # "yes", "no", "not sure"
    faculty_mentor_available: bool = True
    project_title: str = ""
    college_name: str = ""
    selected_sdgs: List[str] = Field(default_factory=list)
    funding_amount_required: float = 0.0
    abstract: str = ""
    literature_survey: str = ""
    technical_approach: str = ""
    innovation_novelty: str = ""
    existing_solutions: str = ""
    research_papers: str = ""


class SchemeEvaluation(BaseModel):
    scheme: Scheme
    status: EvaluationStatus
    reasons: List[str] = Field(default_factory=list)
    missing_info: List[str] = Field(default_factory=list)
    action_note: str = ""
    matched_sdgs: List[str] = Field(default_factory=list)
    domain_match_type: str = "direct"  # "direct", "open_theme", "technology_partial", "none"
    funding_fit_note: str = ""


class ActionItem(BaseModel):
    step_number: int
    title: str
    description: str
    related_schemes: List[str] = Field(default_factory=list)


class EvaluationReport(BaseModel):
    profile: StudentProfile
    evaluations: List[SchemeEvaluation]
    eligible_schemes: List[SchemeEvaluation]
    possibly_eligible_schemes: List[SchemeEvaluation]
    not_eligible_schemes: List[SchemeEvaluation]
    action_checklist: List[ActionItem]


def analyze_project_documentation(profile: StudentProfile) -> Dict[str, Any]:
    """
    Evaluates project documentation dossier and calculates readiness score (0-100%)
    for submission to grant screening committees.
    """
    scores: Dict[str, int] = {}
    strengths: List[str] = []
    recommendations: List[str] = []

    # 1. Abstract
    abs_len = len(profile.abstract.strip().split()) if profile.abstract else 0
    if abs_len >= 40:
        scores["abstract"] = 20
        strengths.append("Comprehensive abstract summarizing problem, method, and impact.")
    elif abs_len >= 15:
        scores["abstract"] = 12
        recommendations.append("Expand abstract to at least 40-50 words detailing expected societal or scientific outcome.")
    elif abs_len > 0:
        scores["abstract"] = 5
        recommendations.append("Provide a clear 2-3 paragraph abstract highlighting the problem and expected results.")
    else:
        scores["abstract"] = 0
        recommendations.append("Add an executive summary / abstract to communicate the project value proposition.")

    # 2. Literature Survey
    lit_len = len(profile.literature_survey.strip().split()) if profile.literature_survey else 0
    if lit_len >= 30:
        scores["literature_survey"] = 15
        strengths.append("Structured literature survey establishing state-of-the-art context.")
    elif lit_len >= 10:
        scores["literature_survey"] = 8
        recommendations.append("Include comparison against recent existing models or benchmarks in literature survey.")
    elif lit_len > 0:
        scores["literature_survey"] = 3
        recommendations.append("Document at least 2-3 prior methods or existing published approaches.")
    else:
        scores["literature_survey"] = 0
        recommendations.append("Add a literature survey section to demonstrate knowledge of prior work.")

    # 3. Technical Approach
    tech_len = len(profile.technical_approach.strip().split()) if profile.technical_approach else 0
    if tech_len >= 40:
        scores["technical_approach"] = 20
        strengths.append("Thorough technical methodology covering architecture, data, and execution steps.")
    elif tech_len >= 15:
        scores["technical_approach"] = 12
        recommendations.append("Specify technical architecture diagrams, algorithms, or hardware components.")
    elif tech_len > 0:
        scores["technical_approach"] = 5
        recommendations.append("Detail the step-by-step engineering methodology or algorithm pipeline.")
    else:
        scores["technical_approach"] = 0
        recommendations.append("Add technical approach details outlining system pipeline and workflow.")

    # 4. Innovation & Novelty
    nov_len = len(profile.innovation_novelty.strip().split()) if profile.innovation_novelty else 0
    if nov_len >= 30:
        scores["novelty"] = 20
        strengths.append("Clear articulation of inventive step and novelty over baseline systems.")
    elif nov_len >= 10:
        scores["novelty"] = 12
        recommendations.append("Emphasize the unique inventive contribution (what new research was done in this project).")
    elif nov_len > 0:
        scores["novelty"] = 5
        recommendations.append("Explicitly state what new research or improvement is introduced over existing solutions.")
    else:
        scores["novelty"] = 0
        recommendations.append("Highlight innovation & new research elements to satisfy patent/grant novelty committees.")

    # 5. Existing Solutions & Limitations
    sol_len = len(profile.existing_solutions.strip().split()) if profile.existing_solutions else 0
    if sol_len >= 20:
        scores["existing_solutions"] = 15
        strengths.append("Critical analysis of existing solutions and unsolved gaps.")
    elif sol_len >= 8:
        scores["existing_solutions"] = 8
        recommendations.append("Highlight specific limitations of current products (e.g. high cost, low accuracy, slow latency).")
    elif sol_len > 0:
        scores["existing_solutions"] = 3
        recommendations.append("List 1-2 existing market or research solutions and why your approach outperforms them.")
    else:
        scores["existing_solutions"] = 0
        recommendations.append("Analyze existing solutions and their specific bottlenecks.")

    # 6. Research Papers & Citations
    papers_len = len(profile.research_papers.strip()) if profile.research_papers else 0
    if papers_len >= 20:
        scores["citations"] = 10
        strengths.append("Academic citations and research papers documented.")
    elif papers_len >= 5:
        scores["citations"] = 5
        recommendations.append("Format research papers with Authors, Title, Journal/Conference, and Year.")
    elif papers_len > 0:
        scores["citations"] = 2
        recommendations.append("Include 2-3 key research papers or standard datasets referred to in your research.")
    else:
        scores["citations"] = 0
        recommendations.append("Add research papers and academic references consulted.")

    total_score = min(100, sum(scores.values()))

    if total_score >= 80:
        verdict = "Excellent — Ready for Grant Screening Committee"
        badge_color = "#10b981"
    elif total_score >= 50:
        verdict = "Good — Meets Initial Eligibility Criteria"
        badge_color = "#3b82f6"
    elif total_score >= 25:
        verdict = "Preliminary — Expand Research Dossier"
        badge_color = "#f59e0b"
    else:
        verdict = "Basic Profile — Documentation Needed"
        badge_color = "#6366f1"

    return {
        "score": total_score,
        "verdict": verdict,
        "badge_color": badge_color,
        "scores": scores,
        "strengths": strengths,
        "recommendations": recommendations,
    }


def evaluate_scheme(profile: StudentProfile, scheme: Scheme) -> SchemeEvaluation:
    """
    Deterministically evaluates a student profile against a single scheme/organization.
    Checks institutional criteria, stage, novelty, organization domain rules, SDG mapping,
    and funding limits.
    """
    disqualifications: List[str] = []
    uncertainties: List[str] = []
    matched_reasons: List[str] = []
    matched_sdgs: List[str] = []
    domain_match_type = "direct"
    funding_fit_note = ""

    # 1. Patent Novelty Check (Crucial for IP / Patent filing schemes)
    if profile.project_stage.lower() == "already published" and scheme.type == SchemeType.PATENT_FEE_SUPPORT:
        disqualifications.append(
            "Novelty is destroyed: Project is already published publicly prior to filing provisional patent."
        )

    # 2. State eligibility check
    if scheme.eligibility.states:
        norm_states = [s.strip().lower() for s in scheme.eligibility.states]
        if profile.state.strip().lower() not in norm_states:
            disqualifications.append(
                f"State mismatch: Scheme is restricted to {', '.join(scheme.eligibility.states)}, but applicant is in '{profile.state}'."
            )

    # 3. Applicant Status Check (UG / PG / PhD)
    if scheme.eligibility.applicant_status:
        norm_statuses = [s.strip().lower() for s in scheme.eligibility.applicant_status]
        # Normalize status, e.g. "UG (Undergraduate)" -> "ug"
        user_status = profile.student_status.strip().lower().split()[0]
        matched_status = any(user_status == st.lower() or user_status in st.lower() for st in norm_statuses)
        if not matched_status:
            disqualifications.append(
                f"Student status mismatch: Requires {', '.join(scheme.eligibility.applicant_status)}, but applicant is '{profile.student_status}'."
            )

    # 4. College Type Check
    if scheme.eligibility.college_types:
        norm_colleges = [c.strip().lower() for c in scheme.eligibility.college_types]
        user_coll = profile.college_type.strip().lower()
        if user_coll not in norm_colleges and "other" not in norm_colleges and not any(user_coll in c for c in norm_colleges):
            disqualifications.append(
                f"College type mismatch: Requires {', '.join(scheme.eligibility.college_types)}, but college is '{profile.college_type}'."
            )

    # 5. Project Stage Check
    if scheme.eligibility.project_stages:
        norm_stages = [st.strip().lower() for st in scheme.eligibility.project_stages]
        user_stg = profile.project_stage.strip().lower()
        if user_stg not in norm_stages:
            disqualifications.append(
                f"Project stage mismatch: Scheme requires {', '.join(scheme.eligibility.project_stages)}, but project is at '{profile.project_stage}' stage."
            )

    # 6. IEDC Requirement Check
    if scheme.eligibility.requires_iedc is True:
        if profile.has_iedc.lower() == "no":
            disqualifications.append(
                "Missing college IEDC: Scheme strictly requires an active college IEDC / NAIN incubation cell."
            )
        elif profile.has_iedc.lower() == "not sure":
            uncertainties.append(
                "Verify with college administration whether an active IEDC / incubation center exists."
            )

    # 7. Faculty Mentor Availability Check
    if (scheme.who_applies == WhoApplies.FACULTY or scheme.eligibility.requires_faculty is True) and not profile.faculty_mentor_available:
        disqualifications.append(
            "Faculty mentor required: Application must be filed by faculty or requires faculty endorsement, but no mentor is available."
        )

    # 8. Check for incomplete skeleton entries
    if scheme.confidence == ConfidenceLevel.NEEDS_VERIFICATION and not scheme.eligibility.applicant_status and not scheme.eligibility.college_types and not scheme.eligibility.domains:
        uncertainties.append(
            f"Scheme '{scheme.name}' is currently pending official verification; eligibility criteria must be checked on source site."
        )

    # 9. Domain & Theme Rules Check (CRITICAL)
    full_text = f"{profile.project_title} {profile.project_domain} {profile.technical_approach} {profile.innovation_novelty} {profile.abstract}".lower()

    if scheme.eligibility.open_theme or not scheme.eligibility.domains or "*" in scheme.eligibility.domains or "General / Open Theme" in scheme.eligibility.domains:
        domain_match_type = "open_theme"
        matched_reasons.append("✓ General Problem Statement: Organization accepts open / interdisciplinary problem statements across engineering & science branches.")
    else:
        user_domain_norm = profile.project_domain.strip().lower()
        allowed_domains_norm = [d.strip().lower() for d in scheme.eligibility.domains]

        # Direct domain match check
        direct_domain_match = any(user_domain_norm in d or d in user_domain_norm for d in allowed_domains_norm)

        # Keyword match in domain (e.g. "areca nut leaf disease" in text matching agriculture/plant domain)
        keyword_domain_match = False
        if any(term in full_text for term in ["areca", "leaf", "plant", "crop", "agriculture", "botany", "pest", "farm", "horticulture", "harvest"]) and any("agriculture" in d or "plant" in d for d in allowed_domains_norm):
            keyword_domain_match = True

        if direct_domain_match or keyword_domain_match:
            domain_match_type = "direct"
            matched_reasons.append(f"✓ Direct Sector Match: Project aligns directly with organization mandate for '{scheme.authority}'.")
        else:
            # Check for Applied Technology / Interdisciplinary Partial Match
            tech_match = False
            matched_tech_kw: List[str] = []
            if scheme.eligibility.technology_keywords:
                for kw in scheme.eligibility.technology_keywords:
                    # Match whole words or clean boundaries
                    pattern = r'\b' + re.escape(kw.lower()) + r'\b'
                    if re.search(pattern, full_text):
                        tech_match = True
                        if kw not in matched_tech_kw:
                            matched_tech_kw.append(kw)

            if tech_match:
                domain_match_type = "technology_partial"
                matched_reasons.append(
                    f"⚡ Interdisciplinary Technology Match: Organization focuses on {', '.join(scheme.eligibility.domains[:2])}. Your project applies {', '.join(matched_tech_kw[:3])} methods to your application domain."
                )
                uncertainties.append(
                    f"Technical focus check: Ensure grant proposal highlights the innovation and novelty of the {', '.join(matched_tech_kw[:2])} algorithmic / hardware component."
                )
            else:
                domain_match_type = "none"
                disqualifications.append(
                    f"Domain mismatch: {scheme.authority} strictly funds projects in {', '.join(scheme.eligibility.domains[:2])}. Your project ('{profile.project_title or profile.project_domain}') is in a different domain."
                )

    # 10. SDG Alignment
    if profile.selected_sdgs:
        user_clean_sdgs = [s.strip() for s in profile.selected_sdgs if not s.lower().startswith("none")]
        if user_clean_sdgs and scheme.eligibility.target_sdgs:
            for u_sdg in user_clean_sdgs:
                u_code = u_sdg.split(":")[0].strip().lower()
                for t_sdg in scheme.eligibility.target_sdgs:
                    t_code = t_sdg.split(":")[0].strip().lower()
                    if u_code == t_code or u_sdg.lower() == t_sdg.lower():
                        if u_sdg not in matched_sdgs:
                            matched_sdgs.append(u_sdg)
            if matched_sdgs:
                matched_reasons.append(f"🎯 Target SDG Match: Aligned with organization's core goals: {', '.join(matched_sdgs)}.")

    # 11. Funding Amount Fit Check
    if profile.funding_amount_required > 0 and scheme.eligibility.max_amount_inr:
        if profile.funding_amount_required > scheme.eligibility.max_amount_inr:
            funding_fit_note = f"Budget Note: Requested ₹{profile.funding_amount_required:,.0f} exceeds typical grant cap of ₹{scheme.eligibility.max_amount_inr:,.0f}."
            uncertainties.append(f"Budget adjustment needed: Requested ₹{profile.funding_amount_required:,.0f} vs organization grant limit of ₹{scheme.eligibility.max_amount_inr:,.0f}.")
        else:
            funding_fit_note = f"Budget Fit: Requested ₹{profile.funding_amount_required:,.0f} fits within grant budget (up to ₹{scheme.eligibility.max_amount_inr:,.0f})."
            matched_reasons.append(funding_fit_note)

    # Determine Final Status
    if disqualifications:
        return SchemeEvaluation(
            scheme=scheme,
            status=EvaluationStatus.NOT_ELIGIBLE,
            reasons=disqualifications,
            missing_info=[],
            action_note="Application not recommended due to domain or eligibility restrictions.",
            matched_sdgs=matched_sdgs,
            domain_match_type=domain_match_type,
            funding_fit_note=funding_fit_note,
        )

    if uncertainties:
        return SchemeEvaluation(
            scheme=scheme,
            status=EvaluationStatus.POSSIBLY_ELIGIBLE,
            reasons=matched_reasons,
            missing_info=uncertainties,
            action_note=f"Action needed: Route application via {scheme.who_applies.value.upper()} after verifying conditions.",
            matched_sdgs=matched_sdgs,
            domain_match_type=domain_match_type,
            funding_fit_note=funding_fit_note,
        )

    if not matched_reasons:
        matched_reasons = ["All profile criteria match official scheme rules."]
    else:
        matched_reasons.insert(0, "All profile criteria match official scheme rules.")
    for cond in scheme.eligibility.other_conditions:
        matched_reasons.append(f"Institutional requirement: {cond}")

    return SchemeEvaluation(
        scheme=scheme,
        status=EvaluationStatus.ELIGIBLE,
        reasons=matched_reasons,
        missing_info=[],
        action_note=f"Recommended! Submit application via: {scheme.who_applies.value.upper()}.",
        matched_sdgs=matched_sdgs,
        domain_match_type=domain_match_type,
        funding_fit_note=funding_fit_note,
    )


def generate_action_checklist(matched_evaluations: List[SchemeEvaluation]) -> List[ActionItem]:
    """
    Generates an ordered, actionable checklist for engineering students
    based on the set of eligible and possibly eligible schemes.
    """
    if not matched_evaluations:
        return [
            ActionItem(
                step_number=1,
                title="Develop Project to Prototype Stage",
                description="Most patent and grant schemes require at least a functional prototype. Advance your design before re-evaluating.",
                related_schemes=[]
            ),
            ActionItem(
                step_number=2,
                title="Maintain Confidentiality (Non-Disclosure)",
                description="Do not publish conference papers, YouTube videos, or public GitHub repositories until a provisional patent is filed.",
                related_schemes=[]
            )
        ]

    scheme_names = [e.scheme.name for e in matched_evaluations]
    who_set = {e.scheme.who_applies for e in matched_evaluations}

    items: List[ActionItem] = []
    step = 1

    # Step 1: Prior Art Search & Novelty Check
    items.append(
        ActionItem(
            step_number=step,
            title="Conduct Prior-Art Search & Protect Novelty",
            description="Search Indian Patent Office (InPASS) and Google Patents. Ensure no public disclosure, paper publication, or open demo has occurred.",
            related_schemes=scheme_names
        )
    )
    step += 1

    # Step 2: Institutional Coordination
    coord_desc = []
    if WhoApplies.IEDC in who_set:
        coord_desc.append("Contact your college IEDC / NAIN coordinator to request incubation proposal endorsement.")
    if WhoApplies.INSTITUTE in who_set:
        coord_desc.append("Meet your college Institution's Innovation Council (IIC) / KAPILA coordinator to initiate institute-routed filing.")
    if WhoApplies.FACULTY in who_set:
        coord_desc.append("Align with your faculty project mentor for joint technical declaration.")
    if WhoApplies.STUDENT in who_set:
        coord_desc.append("For direct student schemes (like KSCST), prepare student team identification and college bonafide certificate.")

    items.append(
        ActionItem(
            step_number=step,
            title="Engage College Filing Authority",
            description=" ".join(coord_desc) if coord_desc else "Engage college IP coordinator to confirm routing requirements.",
            related_schemes=[e.scheme.name for e in matched_evaluations]
        )
    )
    step += 1

    # Step 3: Document Assembly
    all_docs = set()
    for e in matched_evaluations:
        all_docs.update(e.scheme.documents_required)
    doc_sample = list(all_docs)[:4] if all_docs else ["Project specification draft", "College bonafide"]

    items.append(
        ActionItem(
            step_number=step,
            title="Draft Specification & Assemble Documents",
            description=f"Prepare provisional patent claims, drawings, and mandatory certificates: {', '.join(doc_sample)}.",
            related_schemes=scheme_names
        )
    )
    step += 1

    # Step 4: Formal Submission & Receipt Logging
    items.append(
        ActionItem(
            step_number=step,
            title="File Application on Official Portal",
            description="Submit the verified application package to the respective portal. Secure CBR (Cash Book Receipt) and filing confirmation numbers for fee reimbursement.",
            related_schemes=scheme_names
        )
    )

    return items


def run_engine(profile: StudentProfile, schemes: List[Scheme]) -> EvaluationReport:
    """
    Executes the full evaluation pipeline across all schemes and compiles
    the structured EvaluationReport.
    """
    evaluations: List[SchemeEvaluation] = []
    eligible: List[SchemeEvaluation] = []
    possibly_eligible: List[SchemeEvaluation] = []
    not_eligible: List[SchemeEvaluation] = []

    for s in schemes:
        res = evaluate_scheme(profile, s)
        evaluations.append(res)
        if res.status == EvaluationStatus.ELIGIBLE:
            eligible.append(res)
        elif res.status == EvaluationStatus.POSSIBLY_ELIGIBLE:
            possibly_eligible.append(res)
        else:
            not_eligible.append(res)

    viable = eligible + possibly_eligible
    checklist = generate_action_checklist(viable)

    return EvaluationReport(
        profile=profile,
        evaluations=evaluations,
        eligible_schemes=eligible,
        possibly_eligible_schemes=possibly_eligible,
        not_eligible_schemes=not_eligible,
        action_checklist=checklist
    )
