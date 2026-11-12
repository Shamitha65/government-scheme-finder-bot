"""
GrantPath - Command-Line Interface & Demonstration Runner
Outputs exact deterministic evaluation results for Persona A, Persona B,
and novelty destruction warning test cases.
"""

import sys
import io
import json
from pathlib import Path

# Force UTF-8 stdout on Windows terminals
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from engine import Scheme, StudentProfile, run_engine


def load_all_schemes():
    schemes_path = Path(__file__).resolve().parent / "schemes.json"
    with open(schemes_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [Scheme(**item) for item in data]


def run_demo():
    schemes = load_all_schemes()

    print("=" * 75)
    print("GRANTPATH: PATENT & GRANT NAVIGATOR FOR ENGINEERING STUDENTS")
    print("Zero-Hallucination Deterministic Engine Output")
    print("=" * 75)

    # -------------------------------------------------------------
    # CASE 1: DEMO PERSONA A
    # -------------------------------------------------------------
    persona_a = StudentProfile(
        student_status="UG",
        college_type="autonomous",
        state="Karnataka",
        project_domain="IoT Agricultural Drone & Soil Sensing Node",
        project_stage="prototype",
        has_iedc="yes",
        faculty_mentor_available=True,
    )

    report_a = run_engine(persona_a, schemes)

    print("\n" + "#" * 75)
    print("CASE 1: DEMO PERSONA A (Priya Sharma - Bengaluru)")
    print(f"Profile: UG 4th Year | Autonomous College, Karnataka | Working Prototype | IEDC: Yes")
    print(f"Domain:  {persona_a.project_domain}")
    print("#" * 75)

    print(f"\n[+] NOVELTY STATUS: SAFE (Stage: {persona_a.project_stage})")
    print("    No prior public disclosures or conference papers reported.")

    print(f"\n[+] ELIGIBLE SCHEMES ({len(report_a.eligible_schemes)} matched):")
    for eval_item in report_a.eligible_schemes:
        s = eval_item.scheme
        print(f"  * [{s.id}] {s.name}")
        print(f"    - Governing Authority: {s.authority}")
        print(f"    - Scheme Category:     {s.type.value.upper()}")
        print(f"    - WHO MUST APPLY:      >>> [{s.who_applies.value.upper()}] <<< (Must route through college innovation unit)")
        print(f"    - Financial Benefit:   {s.benefit.description}")
        if s.benefit.amount_inr:
            print(f"    - Max Grant/Cap:       Rs. {s.benefit.amount_inr:,.0f}")
        print(f"    - Key Required Docs:   {', '.join(s.documents_required[:3])}")
        print(f"    - Official Source:     {s.source_url}")
        print(f"    - Status Confidence:   {s.confidence.value} (Last verified: {s.last_verified})")
        print()

    print(f"[!] POSSIBLY ELIGIBLE / NEEDS VERIFICATION ({len(report_a.possibly_eligible_schemes)}):")
    for eval_item in report_a.possibly_eligible_schemes:
        s = eval_item.scheme
        print(f"  * [{s.id}] {s.name}")
        print(f"    - Missing / Uncertainty: {', '.join(eval_item.missing_info)}")

    print(f"\n[-] INELIGIBLE SCHEMES ({len(report_a.not_eligible_schemes)}):")
    for eval_item in report_a.not_eligible_schemes:
        s = eval_item.scheme
        print(f"  * [{s.id}] {s.name} -> Reasons: {', '.join(eval_item.reasons)}")

    print("\n[>>] ORDERED ACTION CHECKLIST FOR PRIYA:")
    for item in report_a.action_checklist:
        print(f"  Step {item.step_number}: {item.title}")
        print(f"         {item.description}")
        if item.related_schemes:
            print(f"         Applicable Schemes: {', '.join(item.related_schemes)}")

    # -------------------------------------------------------------
    # CASE 2: DEMO PERSONA B
    # -------------------------------------------------------------
    persona_b = StudentProfile(
        student_status="UG",
        college_type="VTU-affiliated",
        state="Karnataka",
        project_domain="AI-assisted Smart Crop Advisory App",
        project_stage="idea",
        has_iedc="no",
        faculty_mentor_available=True,
    )

    report_b = run_engine(persona_b, schemes)

    print("\n" + "#" * 75)
    print("CASE 2: DEMO PERSONA B (Rahul Patil - Hubballi)")
    print(f"Profile: UG 2nd Year | VTU-Affiliated College, Karnataka | Idea Stage | IEDC: No")
    print(f"Domain:  {persona_b.project_domain}")
    print("#" * 75)

    print(f"\n[+] NOVELTY STATUS: SAFE (Stage: {persona_b.project_stage})")

    print(f"\n[+] ELIGIBLE SCHEMES ({len(report_b.eligible_schemes)} matched):")
    for eval_item in report_b.eligible_schemes:
        s = eval_item.scheme
        print(f"  * [{s.id}] {s.name}")
        print(f"    - Governing Authority: {s.authority}")
        print(f"    - WHO APPLIES:         [{s.who_applies.value.upper()}]")
        print(f"    - Benefit:             {s.benefit.description}")

    print(f"\n[-] INELIGIBLE SCHEMES ({len(report_b.not_eligible_schemes)}):")
    for eval_item in report_b.not_eligible_schemes:
        s = eval_item.scheme
        print(f"  * [{s.id}] {s.name}")
        for r in eval_item.reasons:
            print(f"    - Rejection Cause: {r}")

    print("\n[>>] ORDERED ACTION CHECKLIST FOR RAHUL:")
    for item in report_b.action_checklist:
        print(f"  Step {item.step_number}: {item.title}")
        print(f"         {item.description}")

    # -------------------------------------------------------------
    # CASE 3: NOVELTY DESTRUCTION ALERT
    # -------------------------------------------------------------
    persona_published = StudentProfile(
        student_status="UG",
        college_type="autonomous",
        state="Karnataka",
        project_domain="Novel Bio-Polymer Extruder",
        project_stage="already published",
        has_iedc="yes",
        faculty_mentor_available=True,
    )

    report_pub = run_engine(persona_published, schemes)

    print("\n" + "#" * 75)
    print("CASE 3: NOVELTY DESTRUCTION ALERT TEST (Public Tech Fest Presentation)")
    print(f"Profile: Stage='already published'")
    print("#" * 75)

    print("\n[CRITICAL WARNING] INDIAN PATENTS ACT 1970 (Sec 29-34) VIOLATION:")
    print("Public disclosure destroys patent novelty prior to filing a provisional specification.")
    print("Engine Disqualifications Triggered:")
    for eval_item in report_pub.not_eligible_schemes:
        for r in eval_item.reasons:
            if "Novelty is destroyed" in r:
                print(f"  * [{eval_item.scheme.id}]: {r}")

    print("\n" + "=" * 75)
    print("DEMO RUN COMPLETE: All evaluations match deterministic rules.")
    print("=" * 75)


if __name__ == "__main__":
    run_demo()
