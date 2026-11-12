"""
GrantPath - Pure Python Rule-Matching Engine
Deterministic, fully unit-testable evaluation of student project profiles against
government patent-filing and grant schemes.
"""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class SchemeType(str, Enum):
    PATENT_FEE_SUPPORT = "patent_fee_support"
    GRANT = "grant"
    TECHNICAL_ASSISTANCE = "technical_assistance"


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
    project_domain: str  # free text
    project_stage: str   # "idea", "prototype", "working model", "already published"
    has_iedc: str        # "yes", "no", "not sure"
    faculty_mentor_available: bool = True


class SchemeEvaluation(BaseModel):
    scheme: Scheme
    status: EvaluationStatus
    reasons: List[str] = Field(default_factory=list)
    missing_info: List[str] = Field(default_factory=list)
    action_note: str = ""


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


def evaluate_scheme(profile: StudentProfile, scheme: Scheme) -> SchemeEvaluation:
    """
    Deterministically evaluates a student profile against a single scheme.
    Returns EvaluationStatus (ELIGIBLE, POSSIBLY ELIGIBLE, NOT ELIGIBLE) with
    actionable reasons or missing info requirements.
    """
    disqualifications: List[str] = []
    uncertainties: List[str] = []

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
        if profile.student_status.strip().lower() not in norm_statuses:
            disqualifications.append(
                f"Student status mismatch: Requires {', '.join(scheme.eligibility.applicant_status)}, but applicant is '{profile.student_status}'."
            )

    # 4. College Type Check
    if scheme.eligibility.college_types:
        norm_colleges = [c.strip().lower() for c in scheme.eligibility.college_types]
        if profile.college_type.strip().lower() not in norm_colleges:
            disqualifications.append(
                f"College type mismatch: Requires {', '.join(scheme.eligibility.college_types)}, but college is '{profile.college_type}'."
            )

    # 5. Project Stage Check
    if scheme.eligibility.project_stages:
        norm_stages = [st.strip().lower() for st in scheme.eligibility.project_stages]
        if profile.project_stage.strip().lower() not in norm_stages:
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

    # 7. Faculty Mentor Availability Check (for faculty-routed schemes)
    if scheme.who_applies == WhoApplies.FACULTY and not profile.faculty_mentor_available:
        disqualifications.append(
            "Faculty mentor required: Application must be filed by faculty, but no mentor is available."
        )

    # 8. Check for incomplete skeleton entries
    if scheme.confidence == ConfidenceLevel.NEEDS_VERIFICATION and not scheme.eligibility.applicant_status and not scheme.eligibility.college_types:
        uncertainties.append(
            f"Scheme '{scheme.name}' is currently pending official verification; eligibility criteria must be checked on source site."
        )

    # Determine Final Status
    if disqualifications:
        return SchemeEvaluation(
            scheme=scheme,
            status=EvaluationStatus.NOT_ELIGIBLE,
            reasons=disqualifications,
            missing_info=[],
            action_note="Do not proceed until disqualifying conditions are resolved."
        )

    if uncertainties:
        return SchemeEvaluation(
            scheme=scheme,
            status=EvaluationStatus.POSSIBLY_ELIGIBLE,
            reasons=[],
            missing_info=uncertainties,
            action_note=f"Action needed: Route application via {scheme.who_applies.value.upper()} after verifying conditions."
        )

    matched_reasons = ["All profile criteria match official scheme rules."]
    for cond in scheme.eligibility.other_conditions:
        matched_reasons.append(f"Institutional requirement: {cond}")

    return SchemeEvaluation(
        scheme=scheme,
        status=EvaluationStatus.ELIGIBLE,
        reasons=matched_reasons,
        missing_info=[],
        action_note=f"Ready to apply! Must be submitted by: {scheme.who_applies.value.upper()}."
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

    # Step 3: Document Compilation
    all_docs = set()
    for e in matched_evaluations:
        all_docs.update(e.scheme.documents_required)
    doc_sample = list(all_docs)[:4]

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

    # Action checklist is generated from viable schemes (ELIGIBLE + POSSIBLY ELIGIBLE)
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
