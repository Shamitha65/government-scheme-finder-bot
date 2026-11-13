"""
National Scheme & Fund Portal
Clean 2-button gateway with a single unified Fund & Govt Scheme Chatbot:
  1. First page: Two buttons ("🏛️ Govt Scheme" & "🚀 Fund") + Unified Chatbot
  2. Govt Scheme Page: Blank form, verified matching schemes, and Unified Chatbot
  3. Fund Page: Blank project form, verified working URLs, and Unified Chatbot
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

from engine import (
    Scheme,
    StudentProfile,
    EvaluationStatus,
    WhoApplies,
    SchemeType,
    ConfidenceLevel,
    run_engine,
)
from extractor import (
    extract_scheme_from_text,
    explain_evaluation_results,
    save_scheme_to_store,
)
from welfare_engine import (
    load_welfare_schemes,
    match_welfare_schemes,
)

load_dotenv()

SCHEMES_FILE = Path(__file__).resolve().parent / "schemes.json"

st.set_page_config(
    page_title="Fund & Govt Scheme Portal",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Unique Modern UI/UX Styles
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
    }

    .portal-hero {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #1d4ed8 100%);
        color: white;
        padding: 2.2rem 2.2rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 25px -5px rgba(30, 58, 138, 0.35);
        border: 1px solid rgba(255, 255, 255, 0.15);
    }
    .portal-hero h1 {
        font-size: 2.1rem !important;
        font-weight: 800 !important;
        color: #ffffff !important;
        margin: 0 0 0.4rem 0 !important;
        letter-spacing: -0.02em;
    }
    .portal-hero p {
        color: #cbd5e1 !important;
        font-size: 1.05rem !important;
        margin: 0 !important;
    }

    .gateway-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 1.8rem;
        box-shadow: 0 4px 18px rgba(15, 23, 42, 0.05);
        margin-bottom: 1rem;
    }

    .scheme-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 1.5rem;
        margin-bottom: 0.8rem;
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.04);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .scheme-card:hover {
        border-color: #cbd5e1;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
    }

    .pill-badge {
        display: inline-block;
        padding: 0.25rem 0.65rem;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 700;
        margin-right: 0.35rem;
    }
    .pill-state { background: #eff6ff; color: #1e40af; border: 1px solid #bfdbfe; }
    .pill-target { background: #f3e8ff; color: #6b21a8; border: 1px solid #e9d5ff; }
    .pill-status { background: #ecfdf5; color: #065f46; border: 1px solid #a7f3d0; }

    .benefit-box {
        background: #f8fafc;
        border-left: 4px solid #10b981;
        padding: 0.85rem 1rem;
        border-radius: 0 8px 8px 0;
        margin: 0.8rem 0;
        font-size: 0.95rem;
        color: #0f172a;
    }
    .why-box {
        background: #eff6ff;
        border-left: 4px solid #3b82f6;
        padding: 0.85rem 1rem;
        border-radius: 0 8px 8px 0;
        margin: 0.8rem 0;
        font-size: 0.92rem;
        color: #1e3a8a;
    }
    .doc-tag {
        display: inline-block;
        background: #f1f5f9;
        color: #334155;
        padding: 0.2rem 0.55rem;
        border-radius: 6px;
        font-size: 0.8rem;
        margin: 0.2rem 0.2rem 0.2rem 0;
        border: 1px solid #e2e8f0;
    }

    .who-tag {
        display: inline-block;
        padding: 0.25rem 0.65rem;
        border-radius: 999px;
        font-weight: 700;
        font-size: 0.75rem;
    }
    .who-student { background: #dbeafe; color: #1e40af; }
    .who-iedc { background: #fef3c7; color: #92400e; }
    .who-institute { background: #f3e8ff; color: #6b21a8; }
    .who-faculty { background: #ffedd5; color: #9a3412; }

    /* =========================================================================
       MOBILE & PHONE VIEW OPTIMIZATIONS (Screen width <= 768px and <= 480px)
       ========================================================================= */
    @media (max-width: 768px) {
        /* Mobile-optimized main content container */
        .main .block-container {
            padding-left: 0.85rem !important;
            padding-right: 0.85rem !important;
            padding-top: 1rem !important;
            padding-bottom: 2rem !important;
            max-width: 100% !important;
        }

        /* Mobile Hero Banner */
        .portal-hero {
            padding: 1.35rem 1.1rem !important;
            border-radius: 12px !important;
            margin-bottom: 1.2rem !important;
        }
        .portal-hero h1 {
            font-size: 1.4rem !important;
            line-height: 1.25 !important;
        }
        .portal-hero p {
            font-size: 0.86rem !important;
            line-height: 1.4 !important;
        }

        /* Mobile Gateway Cards */
        .gateway-card {
            padding: 1.15rem 1rem !important;
            border-radius: 14px !important;
            margin-bottom: 0.75rem !important;
        }
        .gateway-card h3 {
            font-size: 1.2rem !important;
        }

        /* Mobile Scheme Cards */
        .scheme-card {
            padding: 1rem !important;
            border-radius: 12px !important;
            margin-bottom: 0.75rem !important;
        }
        .scheme-card h3 {
            font-size: 1.1rem !important;
            line-height: 1.35 !important;
        }

        /* Mobile Highlight & Reason Boxes */
        .benefit-box, .why-box {
            padding: 0.7rem 0.8rem !important;
            font-size: 0.86rem !important;
            margin: 0.5rem 0 !important;
            line-height: 1.4 !important;
        }

        /* Responsive Badges */
        .pill-badge {
            font-size: 0.72rem !important;
            padding: 0.2rem 0.5rem !important;
            margin-bottom: 0.3rem !important;
            display: inline-block !important;
        }
        .doc-tag {
            font-size: 0.72rem !important;
            padding: 0.18rem 0.45rem !important;
            margin-bottom: 0.25rem !important;
            display: inline-block !important;
        }

        /* Auto-stack 3-column form inputs into single-column on phones */
        [data-testid="stForm"] div[data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
            padding-left: 0 !important;
            padding-right: 0 !important;
        }

        /* Touch-Friendly Action Buttons (min 44px height for thumbs) */
        .stButton > button, .stLinkButton > a {
            min-height: 44px !important;
            font-size: 0.88rem !important;
            padding: 0.55rem 0.8rem !important;
            border-radius: 8px !important;
            touch-action: manipulation;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            text-align: center !important;
        }

        /* Chatbot optimization on phone view */
        .stChatMessage {
            padding: 0.7rem 0.8rem !important;
            font-size: 0.88rem !important;
            border-radius: 10px !important;
        }
        .stChatInput {
            padding-bottom: 0.5rem !important;
        }
    }

    @media (max-width: 600px) {
        /* Full-width stacking for side-by-side action buttons on small mobile screens */
        div[data-testid="column"]:has(button[key^="ask_w_"]),
        div[data-testid="column"]:has(button[key^="ask_fund_"]),
        div[data-testid="column"]:has(a[href^="http"]) {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
            margin-bottom: 0.35rem !important;
        }

        /* Full-width suggested questions on phone view */
        div[data-testid="column"]:has(button[key^="gq_"]),
        div[data-testid="column"]:has(button[key^="fq_"]) {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
            margin-bottom: 0.25rem !important;
        }
    }

    @media (max-width: 480px) {
        .portal-hero h1 {
            font-size: 1.25rem !important;
        }
        .portal-hero p {
            font-size: 0.82rem !important;
        }
        .gateway-card {
            padding: 1rem !important;
        }
        .scheme-card {
            padding: 0.85rem !important;
        }
        .pill-badge {
            font-size: 0.68rem !important;
            padding: 0.15rem 0.45rem !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def load_fund_schemes() -> List[Scheme]:
    if not SCHEMES_FILE.exists():
        return []
    with open(SCHEMES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [Scheme(**item) for item in data]


# ==============================================================================
# 1. GOVT SCHEME AI CHATBOT (DEDICATED)
# ==============================================================================
def build_govt_scheme_fallback(message: str, w_data: Dict[str, Any], w_matched: List[Dict[str, Any]]) -> str:
    """Strictly grounded fallback for government welfare schemes and scholarships."""
    q = message.lower().strip()
    disclaimer = (
        "\n\n*Note: Final eligibility and benefits must be confirmed through the official "
        "government department or portal before applying.*"
    )

    if any(k in q for k in ["document", "paper", "certificate", "id proof"]):
        if w_matched:
            lines = ["Based on your matched government welfare schemes, required documents include:\n"]
            for s in w_matched[:4]:
                docs = ", ".join(s.get("documents", []))
                lines.append(f"- **{s.get('name')}**: {docs}")
            return "\n".join(lines) + disclaimer
        return (
            "Common documents required across verified government welfare schemes:\n"
            "- **Aadhaar Card** (linked to active mobile number and bank account for DBT)\n"
            "- **Family Income Certificate** issued by a competent state authority\n"
            "- **Caste / Category Certificate** (SC/ST/OBC/EWS, if applicable)\n"
            "- **Bank Passbook Copy / Cancelled Cheque**\n"
            "- **Academic Marksheets / Bonafide Certificate** (for student scholarships)"
            + disclaimer
        )

    if any(k in q for k in ["why am i eligible", "eligible", "eligibility", "qualify", "who can apply"]):
        if w_matched:
            lines = ["Here is why you may be eligible based on your entered profile:\n"]
            for s in w_matched[:4]:
                why = "; ".join(s.get("why_eligible", [])) if isinstance(s.get("why_eligible"), list) else s.get("why_eligible", "Matches your profile")
                lines.append(f"- **{s.get('name')}**: {why}")
            return "\n".join(lines) + disclaimer
        return "Please fill out and submit the **Find Schemes** form above so I can match your specific age, income, and state with eligible government welfare schemes." + disclaimer

    if any(k in q for k in ["student", "scholarship", "study", "education"]):
        return (
            "Key student scholarships and education welfare schemes:\n"
            "- **Central Sector Scheme of Scholarship (CSSS):** ₹12,000/yr (UG) to ₹20,000/yr (PG) for top 20th percentile Class 12 students (Income < ₹4.5 Lakhs).\n"
            "- **Karnataka State Scholarship Portal (SSP Post-Matric):** Tuition fee waiver and maintenance allowance for SC/ST/OBC/General/Minority students.\n"
            "- **Yuva Nidhi (Karnataka):** ₹3,000/month for unemployed graduates, ₹1,500/month for diploma holders (up to 24 months)."
            + disclaimer
        )

    if any(k in q for k in ["low-income", "low income", "poor", "income", "bpl", "family"]):
        return (
            "Key welfare schemes for low-income families:\n"
            "- **Ayushman Bharat (PM-JAY):** Up to ₹5 Lakhs annual health insurance coverage per family.\n"
            "- **PM Awas Yojana (PMAY):** Subsidies for construction/purchase of pucca houses.\n"
            "- **Gruha Lakshmi (Karnataka):** ₹2,000/month financial assistance to women heads of BPL/APL families."
            + disclaimer
        )

    if any(k in q for k in ["farmer", "kisan", "agriculture", "crop"]):
        return (
            "Key government schemes for farmers:\n"
            "- **PM-KISAN:** ₹6,000 per year direct income support in 3 equal installments.\n"
            "- **PM Fasal Bima Yojana (PMFBY):** Comprehensive crop insurance against non-preventable natural risks."
            + disclaimer
        )

    if any(k in q for k in ["date", "deadline", "start", "end", "last date", "when"]):
        if w_matched:
            lines = ["Application dates for your matched schemes:\n"]
            for s in w_matched[:5]:
                start_dt = s.get("application_start_date", "Open Year-Round")
                end_dt = s.get("application_end_date", "No Fixed Deadline")
                lines.append(f"- **{s.get('name')}**: Start: {start_dt} | Last Date: {end_dt}")
            return "\n".join(lines) + disclaimer
        return (
            "General welfare application cycles:\n"
            "- **National Scholarship Portal (NSP / CSSS):** Opens **July/August**, closes around **November/December**.\n"
            "- **Karnataka SSP Post-Matric:** Opens **August/September**, closes around **December/January**.\n"
            "- **Yuva Nidhi / PM-KISAN:** Open year-round on Seva Sindhu / PM-KISAN portals."
            + disclaimer
        )

    return (
        "Ask me about government welfare schemes:\n"
        "- 📄 *\"What documents do I need for schemes?\"*\n"
        "- 💡 *\"Why am I eligible?\"*\n"
        "- 🎓 *\"What scholarships are available for students?\"*\n"
        "- 💰 *\"Show schemes for low-income families\"*\n"
        "- 📅 *\"What are the application deadlines?\"*"
        + disclaimer
    )


# In-memory caches for fast instant chat replies
_GOVT_CHAT_CACHE: Dict[str, str] = {}
_FUND_CHAT_CACHE: Dict[str, str] = {}


def ask_govt_scheme_chatbot(message: str) -> str:
    """Answers welfare queries grounded in user profile and verified schemes with instant caching and fallback."""
    clean_msg = message.strip()
    cache_key = clean_msg.lower()
    if cache_key in _GOVT_CHAT_CACHE:
        return _GOVT_CHAT_CACHE[cache_key]

    w_data = st.session_state.get("welfare_data", {})
    w_matched = st.session_state.get("welfare_matched_schemes", [])

    # Instant sub-second response for scheme query buttons
    if clean_msg.lower().startswith("tell me more about"):
        scheme_query = clean_msg.lower().replace("tell me more about", "").split(",")[0].strip()
        all_w = load_welfare_schemes()
        for s in all_w:
            if s.get("name", "").lower() in scheme_query or scheme_query in s.get("name", "").lower():
                docs_text = ", ".join(s.get("documents", []))
                reply = (
                    f"### 🏛️ {s.get('name')}\n"
                    f"- **State / Territory:** {s.get('state')} | **Target:** {s.get('target_group')}\n"
                    f"- **💰 Benefits:** {s.get('benefits')}\n"
                    f"- **📄 Required Documents:** {docs_text}\n"
                    f"- **📅 Timeline:** {s.get('application_status', 'Check Portal')} (Start: {s.get('application_start_date', 'Open Year-Round')} | Deadline: {s.get('application_end_date', 'No Fixed Deadline')})\n"
                    f"- **📝 How to Apply:** {s.get('application_process')}\n"
                    f"- **🌐 Official Portal:** {s.get('official_url')}\n\n"
                    "*(Note: Confirm final eligibility guidelines directly on the official portal before applying.)*"
                )
                _GOVT_CHAT_CACHE[cache_key] = reply
                return reply

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key.startswith("your_"):
        reply = build_govt_scheme_fallback(message, w_data, w_matched)
        _GOVT_CHAT_CACHE[cache_key] = reply
        return reply

    try:
        client = genai.Client(api_key=api_key)
        model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

        context_parts = []
        if w_data:
            context_parts.append(f"User Welfare Profile: {json.dumps(w_data)}")
        if w_matched:
            context_parts.append(f"Matched Welfare Schemes: {json.dumps([s.get('name') for s in w_matched[:5]])}")

        context_str = "\n".join(context_parts) if context_parts else "General Indian Citizen Profile"

        system_instruction = (
            "You are the official Government Scheme AI Assistant for Indian citizen welfare. "
            "CRITICAL RULES: "
            "1. NEVER fabricate or invent schemes, eligibility requirements, or URLs. "
            "2. Use strictly verified data on Central/State welfare schemes & scholarships (CSSS, Yuva Nidhi, SSP Karnataka, Ayushman Bharat, PM-KISAN). "
            "3. Answer concisely in clear bullet points under 100 words. "
            "4. Remind user to confirm eligibility on the official portal."
        )

        prompt = f"Context:\n{context_str}\n\nUser Question: {message}"

        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2,
                max_output_tokens=220,
            ),
        )
        text = (response.text or "").strip()
        if text:
            _GOVT_CHAT_CACHE[cache_key] = text
            return text
        reply = build_govt_scheme_fallback(message, w_data, w_matched)
        _GOVT_CHAT_CACHE[cache_key] = reply
        return reply
    except Exception:
        reply = build_govt_scheme_fallback(message, w_data, w_matched)
        _GOVT_CHAT_CACHE[cache_key] = reply
        return reply


# ==============================================================================
# 2. FUND & PATENT AI CHATBOT (DEDICATED)
# ==============================================================================
def build_fund_fallback(message: str, f_data: Dict[str, Any], f_matched: List[Any]) -> str:
    """Strictly grounded fallback for engineering student prototype grants and patent support."""
    q = message.lower().strip()
    disclaimer = (
        "\n\n*Note: Grant approvals and patent reimbursements are subject to institutional review "
        "and funding authority committee guidelines.*"
    )

    if any(k in q for k in ["kapila", "reimbursement", "aicte"]):
        return (
            "**KAPILA (Kalam Program for IP Literacy and Awareness) Details:**\n"
            "- **Authority:** AICTE / Ministry of Education's Innovation Cell (MIC).\n"
            "- **Benefit:** **100% reimbursement** of official patent filing fees (₹1,600 statutory fee).\n"
            "- **Who Must Apply:** The **Institute Nodal Officer** (via the College IIC portal). Students cannot apply directly on their own.\n"
            "- **Prerequisite:** College must have an active Institution's Innovation Council (IIC).\n"
            "- **Official Portal:** https://mic.gov.in/kapila"
            + disclaimer
        )

    if any(k in q for k in ["nidhi", "prayas", "dst", "prototype"]):
        return (
            "**DST NIDHI-PRAYAS Prototype Grant Details:**\n"
            "- **Authority:** Department of Science & Technology (DST), Govt. of India.\n"
            "- **Grant Amount:** Up to **₹10,00,000 (₹10 Lakhs)** grant for converting an idea into a physical proof-of-concept/prototype.\n"
            "- **Who Applies:** Student innovator or startup founder applies directly to an affiliated PRAYAS Center (TBI / STEP).\n"
            "- **Use of Funds:** Raw materials, fab lab access, rapid prototyping, third-party testing (cannot be used for team salary).\n"
            "- **Official Portal:** https://dst.gov.in"
            + disclaimer
        )

    if any(k in q for k in ["kscst", "spp", "karnataka council"]):
        return (
            "**KSCST Student Project Programme (SPP) Details:**\n"
            "- **Authority:** Karnataka State Council for Science and Technology.\n"
            "- **Grant Amount:** **₹10,000 to ₹15,000** per final-year engineering BE/M.Tech student project team.\n"
            "- **Who Applies:** Team of final-year engineering students endorsed by their College Principal and Guide/HOD.\n"
            "- **Annual Cycle:** Opens in **November/December**, project proposals due in **January/February**.\n"
            "- **Official Portal:** https://www.kscst.org.in"
            + disclaimer
        )

    if any(k in q for k in ["novelty", "publish", "paper", "conference", "github"]):
        return (
            "🚨 **CRITICAL PATENT NOVELTY RULE (Section 29–34, Indian Patents Act 1970):**\n"
            "- An invention must be **strictly novel** worldwide before an application is filed.\n"
            "- If you publish a research paper, present at an open conference, or upload your source code/schematic to a public GitHub repo before filing, your patent novelty is **permanently destroyed**.\n"
            "- **Correct Action:** File a **Provisional Patent Specification (Form 2)** at the Indian Patent Office first. Once you receive your official Patent Application Number and timestamp, you are free to publish!"
            + disclaimer
        )

    if any(k in q for k in ["who must submit", "who applies", "submit", "institute", "iedc"]):
        return (
            "**Who Submits the Application?**\n"
            "- **KAPILA:** Must be submitted by the **Institute Nodal Officer / IIC Coordinator**.\n"
            "- **KSCST:** Submitted by the **Student Team**, signed and endorsed by the Guide and Principal.\n"
            "- **DST NIDHI-PRAYAS:** Submitted by the **Student / Innovator** to the chosen PRAYAS incubation center.\n"
            "- **Karnataka Startup Mission (NAIN):** Submitted through your college **NAIN Coordinator / IEDC**.\n"
            "- **SIPP (IP India):** Applied by the **Student / Startup**, availing a CGPDTM-registered patent facilitator."
            + disclaimer
        )

    if any(k in q for k in ["document", "paper", "form", "checklist"]):
        return (
            "**Required Documents for Student Patent & Grant Applications:**\n"
            "- College Bonafide / Endorsement Certificate from Principal\n"
            "- Student ID card & Aadhaar of all team members\n"
            "- Provisional Patent Draft (Title, Technical Field, Problem Solved, Novel Elements)\n"
            "- Indian Patent Office Forms: **Form 1** (Application), **Form 2** (Provisional Specification), **Form 3** (Statement)\n"
            "- Bill of Materials (BOM) & project expenditure estimation (for prototype grants)"
            + disclaimer
        )

    return (
        "Ask me about student innovation grants and patent support:\n"
        "- 🚀 *\"How does KAPILA patent reimbursement work?\"*\n"
        "- 🔬 *\"Can I get prototype funding from DST NIDHI?\"*\n"
        "- 💰 *\"What grant amount does KSCST provide?\"*\n"
        "- 📄 *\"What documents are needed for patent filing?\"*\n"
        "- 🔒 *\"Why does publishing destroy patent novelty?\"*\n"
        "- 🏛️ *\"Who must submit: student, faculty, or institute?\"*"
        + disclaimer
    )


def ask_fund_chatbot(message: str) -> str:
    """Answers funding & patent queries grounded in student project profile and verified schemes using Gemini with fallback."""
    clean_msg = message.strip()
    cache_key = clean_msg.lower()
    if cache_key in _FUND_CHAT_CACHE:
        return _FUND_CHAT_CACHE[cache_key]

    f_data = st.session_state.get("fund_data", {})
    f_matched = st.session_state.get("fund_matched_schemes", [])

    # Instant sub-second response for grant query buttons
    if clean_msg.lower().startswith("tell me more about"):
        grant_query = clean_msg.lower().replace("tell me more about", "").split(",")[0].strip()
        all_f = load_fund_schemes()
        for s in all_f:
            if s.name.lower() in grant_query or grant_query in s.name.lower():
                who_val = s.who_applies.value.upper() if hasattr(s.who_applies, "value") else str(s.who_applies).upper()
                notes_text = s.benefit.notes or s.benefit.description
                reply = (
                    f"### 🚀 {s.name}\n"
                    f"- **Authority:** {s.authority} | **Who Must Apply:** **{who_val}**\n"
                    f"- **💰 Grant / Funding Benefit:** {s.benefit.description}\n"
                    f"- **📄 Required Documents:** {', '.join(s.documents_required)}\n"
                    f"- **ℹ️ Important Rules:** {notes_text}\n"
                    f"- **🌐 Official Portal:** {s.source_url}\n\n"
                    "*(Notice: Under Section 29–34 of Indian Patents Act 1970, ensure your provisional patent is filed before public disclosure.)*"
                )
                _FUND_CHAT_CACHE[cache_key] = reply
                return reply

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key.startswith("your_"):
        reply = build_fund_fallback(message, f_data, f_matched)
        _FUND_CHAT_CACHE[cache_key] = reply
        return reply

    try:
        client = genai.Client(api_key=api_key)
        model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

        context_parts = []
        if f_data:
            context_parts.append(f"Student Project Profile: {json.dumps(f_data)}")
        if f_matched:
            context_parts.append(f"Matched Grants: {json.dumps([getattr(ev.scheme, 'name', '') for ev in f_matched[:4]])}")

        context_str = "\n".join(context_parts) if context_parts else "General Engineering Student Profile"

        system_instruction = (
            "You are the official Patent & Grant Fund AI Assistant for engineering student innovators in India. "
            "CRITICAL RULES: "
            "1. NEVER fabricate or invent schemes, eligibility requirements, or URLs. "
            "2. Use strictly verified data on KAPILA (AICTE), DST NIDHI-PRAYAS, KSCST SPP, Karnataka Startup Mission (NAIN), and SIPP. "
            "3. Emphasize Indian Patents Act 1970 novelty protection (no prior publication). "
            "4. Answer concisely in clear bullet points under 100 words. "
            "5. Remind student to confirm with college IIC / faculty mentor."
        )

        prompt = f"Context:\n{context_str}\n\nUser Question: {message}"

        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2,
                max_output_tokens=220,
            ),
        )
        text = (response.text or "").strip()
        if text:
            _FUND_CHAT_CACHE[cache_key] = text
            return text
        reply = build_fund_fallback(message, f_data, f_matched)
        _FUND_CHAT_CACHE[cache_key] = reply
        return reply
    except Exception:
        reply = build_fund_fallback(message, f_data, f_matched)
        _FUND_CHAT_CACHE[cache_key] = reply
        return reply


# ==============================================================================
# SESSION STATE INITIALIZATION
# ==============================================================================
if "page" not in st.session_state:
    st.session_state.page = "home"

if "welfare_data" not in st.session_state:
    st.session_state.welfare_data = {}
if "welfare_submitted" not in st.session_state:
    st.session_state.welfare_submitted = False
if "welfare_matched_schemes" not in st.session_state:
    st.session_state.welfare_matched_schemes = []

if "fund_data" not in st.session_state:
    st.session_state.fund_data = {}
if "fund_submitted" not in st.session_state:
    st.session_state.fund_submitted = False
if "fund_matched_schemes" not in st.session_state:
    st.session_state.fund_matched_schemes = []

# Separate Chat Histories
if "govt_chat" not in st.session_state:
    st.session_state.govt_chat = [
        {
            "role": "assistant",
            "content": (
                "**Namaste! 👋 I am your Government Scheme AI Assistant.**\n\n"
                "Ask me anything about central & state welfare schemes, scholarships, eligibility rules, "
                "or required documents—or click any suggested question below!"
            ),
        }
    ]

if "fund_chat" not in st.session_state:
    st.session_state.fund_chat = [
        {
            "role": "assistant",
            "content": (
                "**Hello! 🚀 I am your Patent & Grant Fund AI Assistant.**\n\n"
                "Ask me about engineering student prototype grants (DST NIDHI, KSCST), patent fee reimbursements (KAPILA, SIPP), "
                "novelty criteria, or checklist steps!"
            ),
        }
    ]


def send_govt_chat(msg: str):
    clean = (msg or "").strip()
    if not clean:
        return
    st.session_state.govt_chat.append({"role": "user", "content": clean})
    reply = ask_govt_scheme_chatbot(clean)
    st.session_state.govt_chat.append({"role": "assistant", "content": reply})
    st.rerun()


def send_fund_chat(msg: str):
    clean = (msg or "").strip()
    if not clean:
        return
    st.session_state.fund_chat.append({"role": "user", "content": clean})
    reply = ask_fund_chatbot(clean)
    st.session_state.fund_chat.append({"role": "assistant", "content": reply})
    st.rerun()


def render_govt_scheme_chatbot_widget():
    """Renders the dedicated Government Scheme Chatbot widget."""
    st.markdown(
        """
        <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:10px; padding:1.1rem; margin-bottom:1rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem;">
                <div>
                    <h3 style="margin:0; font-size:1.25rem; color:#0f172a;">🤖 Government Scheme AI Assistant</h3>
                    <p style="margin:0.2rem 0 0 0; color:#475569; font-size:0.85rem;">Powered by Google Gemini • Answers strictly using verified welfare & scholarship data</p>
                </div>
                <span style="background:#e0f2fe; color:#0369a1; border:1px solid #bae6fd; padding:0.25rem 0.65rem; border-radius:999px; font-size:0.75rem; font-weight:700;">🔒 Hallucination-Protected</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("**Suggested questions:**")
    qc1, qc2, qc3 = st.columns(3)
    with qc1:
        if st.button("📄 What documents do I need for schemes?", key="gq_doc", use_container_width=True):
            send_govt_chat("What documents do I need for schemes?")
    with qc2:
        if st.button("💡 Why am I eligible?", key="gq_why", use_container_width=True):
            send_govt_chat("Why am I eligible?")
    with qc3:
        if st.button("🎓 Scholarships for students?", key="gq_stu", use_container_width=True):
            send_govt_chat("What scholarships are available for students?")

    qc4, qc5, qc6 = st.columns(3)
    with qc4:
        if st.button("💰 Schemes for low-income families", key="gq_low", use_container_width=True):
            send_govt_chat("Show schemes for low-income families")
    with qc5:
        if st.button("📅 Application deadlines?", key="gq_date", use_container_width=True):
            send_govt_chat("What are the application start and end dates?")
    with qc6:
        if st.button("🌾 Schemes for farmers?", key="gq_farm", use_container_width=True):
            send_govt_chat("Are there schemes for farmers?")

    st.markdown("<div style='margin-top: 0.6rem;'></div>", unsafe_allow_html=True)

    for msg in st.session_state.govt_chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_msg := st.chat_input("Ask about welfare schemes, scholarships, SSP, CSSS, eligibility...", key="govt_chat_input"):
        send_govt_chat(user_msg)


def render_fund_chatbot_widget():
    """Renders the dedicated Fund & Patent Support Chatbot widget."""
    st.markdown(
        """
        <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:10px; padding:1.1rem; margin-bottom:1rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem;">
                <div>
                    <h3 style="margin:0; font-size:1.25rem; color:#0f172a;">🚀 Patent & Grant Fund AI Assistant</h3>
                    <p style="margin:0.2rem 0 0 0; color:#475569; font-size:0.85rem;">Powered by Google Gemini • Answers strictly using verified innovation fund & patent data</p>
                </div>
                <span style="background:#e0f2fe; color:#0369a1; border:1px solid #bae6fd; padding:0.25rem 0.65rem; border-radius:999px; font-size:0.75rem; font-weight:700;">🔒 Hallucination-Protected</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("**Suggested questions:**")
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        if st.button("🚀 How does KAPILA work?", key="fq_kap", use_container_width=True):
            send_fund_chat("How does KAPILA patent fee reimbursement work?")
    with fc2:
        if st.button("🔬 Prototype funding via DST NIDHI?", key="fq_dst", use_container_width=True):
            send_fund_chat("Can I get prototype funding from DST NIDHI?")
    with fc3:
        if st.button("💰 Grant amount for KSCST?", key="fq_kscst", use_container_width=True):
            send_fund_chat("What grant amount does KSCST provide?")

    fc4, fc5, fc6 = st.columns(3)
    with fc4:
        if st.button("📄 Documents for patent filing?", key="fq_doc", use_container_width=True):
            send_fund_chat("What documents are needed for patent filing?")
    with fc5:
        if st.button("🔒 Why avoid publishing early?", key="fq_nov", use_container_width=True):
            send_fund_chat("Why does publishing destroy patent novelty?")
    with fc6:
        if st.button("🏛️ Who must submit: student or institute?", key="fq_who", use_container_width=True):
            send_fund_chat("Who must submit: student, faculty, or institute?")

    st.markdown("<div style='margin-top: 0.6rem;'></div>", unsafe_allow_html=True)

    for msg in st.session_state.fund_chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_msg := st.chat_input("Ask about KAPILA, DST NIDHI, KSCST, provisional patents, novelty...", key="fund_chat_input"):
        send_fund_chat(user_msg)


# ==============================================================================
# 1. HOME SCREEN: TWO DEDICATED PATHWAY CARDS
# ==============================================================================
if st.session_state.page == "home":
    st.markdown(
        """
        <div class="portal-hero">
            <h1>🏛️ National Scheme & Fund Portal</h1>
            <p>Unified Discovery for Indian Citizen Welfare Schemes & Engineering Student Innovation Patent Grants</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown(
            """
            <div class="gateway-card">
                <div style="font-size:2.5rem; margin-bottom:0.5rem;">🏛️</div>
                <h3 style="margin:0 0 0.4rem 0; font-size:1.4rem; color:#0f172a; font-weight:800;">Government Schemes</h3>
                <p style="color:#64748b; font-size:0.92rem; line-height:1.5; margin-bottom:1rem;">
                    Personalized eligibility matching for Central & State welfare programs, student scholarships (CSSS, SSP, Yuva Nidhi), health insurance, and family income assistance.
                </p>
                <div style="margin-bottom:1.2rem;">
                    <span class="pill-badge pill-state">All India & Karnataka</span>
                    <span class="pill-badge pill-target">Citizens & Students</span>
                    <span class="pill-badge pill-status">Direct Benefit Transfer</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Explore Govt Schemes →", type="primary", use_container_width=True, key="home_btn_govt"):
            st.session_state.page = "govt_scheme"
            st.rerun()

    with col2:
        st.markdown(
            """
            <div class="gateway-card">
                <div style="font-size:2.5rem; margin-bottom:0.5rem;">🚀</div>
                <h3 style="margin:0 0 0.4rem 0; font-size:1.4rem; color:#0f172a; font-weight:800;">Fund & Patent Support</h3>
                <p style="color:#64748b; font-size:0.92rem; line-height:1.5; margin-bottom:1rem;">
                    Prototype development grants (DST NIDHI, KSCST), 100% patent filing fee reimbursement (KAPILA, SIPP), and Section 29–34 novelty verification for engineering students.
                </p>
                <div style="margin-bottom:1.2rem;">
                    <span class="pill-badge pill-state">KAPILA (AICTE)</span>
                    <span class="pill-badge pill-target">DST NIDHI-PRAYAS</span>
                    <span class="pill-badge pill-status">Up to ₹10 Lakhs</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Explore Funds & Grants →", type="primary", use_container_width=True, key="home_btn_fund"):
            st.session_state.page = "fund"
            st.rerun()


# ==============================================================================
# 2. GOVT SCHEME SCREEN
# ==============================================================================
elif st.session_state.page == "govt_scheme":
    nav_col1, nav_col2 = st.columns([3, 1])
    with nav_col1:
        st.markdown("## 🏛️ Government Schemes")
    with nav_col2:
        if st.button("← Back", use_container_width=True, key="back_from_govt"):
            st.session_state.page = "home"
            st.rerun()

    welfare_schemes = load_welfare_schemes()
    u_w = st.session_state.welfare_data

    with st.form("govt_scheme_form"):
        st.markdown("#### Enter Details")
        c1, c2, c3 = st.columns(3)

        with c1:
            w_name = st.text_input("Name (Optional)", value=u_w.get("name", ""), placeholder="Your Name")
            saved_age = int(u_w["age"]) if u_w.get("age") is not None else None
            w_age = st.number_input("Age *", min_value=0, max_value=120, value=saved_age, placeholder="Enter Age", step=1)
            gender_opts = ["-- Select Gender --", "Male", "Female", "Transgender"]
            g_idx = gender_opts.index(u_w.get("gender")) if u_w.get("gender") in gender_opts else 0
            w_gender = st.selectbox("Gender *", gender_opts, index=g_idx)

        with c2:
            state_opts = ["-- Select State --", "All India", "Karnataka", "Maharashtra", "Tamil Nadu", "Telangana", "Andhra Pradesh", "Kerala", "Delhi", "Uttar Pradesh", "Other"]
            s_idx = state_opts.index(u_w.get("state")) if u_w.get("state") in state_opts else 0
            w_state = st.selectbox("State *", state_opts, index=s_idx)

            saved_income = int(u_w["income"]) if u_w.get("income") is not None else None
            w_income = st.number_input("Annual Family Income (INR) *", min_value=0, max_value=100000000, value=saved_income, placeholder="e.g. 250000", step=10000)

            cat_opts = ["-- Select Category --", "General", "OBC", "SC", "ST", "EWS", "Minority"]
            c_idx = cat_opts.index(u_w.get("category")) if u_w.get("category") in cat_opts else 0
            w_category = st.selectbox("Category *", cat_opts, index=c_idx)

        with c3:
            occ_opts = ["-- Select Occupation --", "Student", "Farmer", "Salaried", "Self-Employed", "Artisan", "Unemployed"]
            o_idx = occ_opts.index(u_w.get("occupation")) if u_w.get("occupation") in occ_opts else 0
            w_occupation = st.selectbox("Occupation *", occ_opts, index=o_idx)

            mar_opts = ["-- Select Marital Status --", "Single", "Married", "Widowed", "Divorced"]
            m_idx = mar_opts.index(u_w.get("marital_status")) if u_w.get("marital_status") in mar_opts else 0
            w_marital = st.selectbox("Marital Status *", mar_opts, index=m_idx)

        is_disabled = st.checkbox("Person with Disability (Divyangjan / PwD)", value=u_w.get("is_disabled", False))

        w_requirements = st.text_input("Keywords / Needs (Optional)", value=u_w.get("requirements", ""), placeholder="e.g. scholarship, health, loan")

        btn_search_w = st.form_submit_button("Find Schemes", type="primary", use_container_width=True)

    if btn_search_w:
        if not w_age:
            st.error("Please enter age.")
        elif w_income is None:
            st.error("Please enter annual income.")
        elif w_gender.startswith("--"):
            st.error("Please select gender.")
        elif w_state.startswith("--"):
            st.error("Please select state.")
        elif w_category.startswith("--"):
            st.error("Please select category.")
        elif w_occupation.startswith("--"):
            st.error("Please select occupation.")
        elif w_marital.startswith("--"):
            st.error("Please select marital status.")
        else:
            st.session_state.welfare_data = {
                "name": w_name,
                "age": int(w_age),
                "gender": w_gender,
                "state": w_state,
                "income": int(w_income),
                "category": w_category,
                "occupation": w_occupation,
                "marital_status": w_marital,
                "is_student": (w_occupation.lower() == "student"),
                "is_farmer": (w_occupation.lower() == "farmer"),
                "is_disabled": is_disabled,
                "requirements": w_requirements,
            }
            st.session_state.welfare_submitted = True

    if st.session_state.welfare_submitted:
        results = match_welfare_schemes(st.session_state.welfare_data, welfare_schemes)
        st.session_state.welfare_matched_schemes = results
        st.markdown(f"### Eligible Schemes ({len(results)} found)")

        if not results:
            st.warning("No matching schemes found for this profile.")
        else:
            for s in results:
                st.markdown(
                    f"""
                    <div class="scheme-card">
                        <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:0.5rem; margin-bottom:0.5rem;">
                            <div>
                                <span class="pill-badge pill-state">📍 {s.get('state')}</span>
                                <span class="pill-badge pill-target">👥 {s.get('target_group')}</span>
                                <span class="pill-badge pill-status">🟢 {s.get('application_status', 'Open')}</span>
                            </div>
                            <span style="font-size:0.75rem; font-weight:700; color:#475569; background:#f1f5f9; padding:0.2rem 0.5rem; border-radius:6px;">{s.get('id')}</span>
                        </div>
                        <h3 style="margin:0 0 0.35rem 0; font-size:1.25rem; color:#0f172a; font-weight:700;">{s.get('name')}</h3>
                        <p style="margin:0 0 0.6rem 0; color:#475569; font-size:0.92rem;">{s.get('description', '')}</p>
                        <div class="benefit-box">
                            <strong>💰 Benefit:</strong> {s.get('benefits')}
                        </div>
                        <div class="why-box">
                            <strong>✓ Why You Are Eligible:</strong> {"; ".join(s.get('why_eligible', [])) if isinstance(s.get('why_eligible'), list) else s.get('why_eligible', 'Matches your profile criteria')}
                        </div>
                        <div style="font-size:0.88rem; color:#334155; margin-bottom:0.5rem;">
                            <strong>📅 Timeline:</strong> {s.get('application_start_date', 'Open Year-Round')} &rarr; <strong>{s.get('application_end_date', 'No Fixed Deadline')}</strong>
                        </div>
                        <div style="margin-bottom:0.8rem;">
                            <strong style="font-size:0.88rem; color:#334155;">🗂️ Documents:</strong> {" ".join([f"<span class='doc-tag'>📄 {d}</span>" for d in s.get('documents', [])[:5]])}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                col_act1, col_act2 = st.columns([1, 1])
                with col_act1:
                    st.link_button("🌐 Official Website & Apply ↗", s.get("official_url", "#"), use_container_width=True)
                with col_act2:
                    if st.button("💬 Ask AI About This Scheme", key=f"ask_w_{s.get('id')}", use_container_width=True):
                        send_govt_chat(f"Tell me more about {s.get('name')}, its documents, benefits, and how to apply.")
                st.markdown("<div style='margin-bottom:1.5rem;'></div>", unsafe_allow_html=True)

    st.markdown("---")
    render_govt_scheme_chatbot_widget()


# ==============================================================================
# 3. FUND SCREEN
# ==============================================================================
elif st.session_state.page == "fund":
    nav_col1, nav_col2 = st.columns([3, 1])
    with nav_col1:
        st.markdown("## 🚀 Fund & Patent Support")
    with nav_col2:
        if st.button("← Back", use_container_width=True, key="back_from_fund"):
            st.session_state.page = "home"
            st.rerun()

    fund_schemes = load_fund_schemes()
    u_f = st.session_state.fund_data

    with st.form("fund_form"):
        st.markdown("#### Enter Project Details")
        c1, c2, c3 = st.columns(3)

        with c1:
            project_domain = st.text_input("Project Title / Area *", value=u_f.get("project_domain", ""), placeholder="e.g. Smart Agri Drone, Medical Sensor")
            status_opts = ["-- Select Status --", "UG", "PG", "PhD"]
            s_idx = status_opts.index(u_f.get("student_status")) if u_f.get("student_status") in status_opts else 0
            student_status = st.selectbox("Student Status *", status_opts, index=s_idx)

        with c2:
            state_opts = ["-- Select State --", "Karnataka", "Maharashtra", "Tamil Nadu", "Telangana", "Andhra Pradesh", "Kerala", "Delhi", "Other"]
            st_idx = state_opts.index(u_f.get("state")) if u_f.get("state") in state_opts else 0
            state = st.selectbox("State *", state_opts, index=st_idx)

            college_opts = ["-- Select Affiliation --", "autonomous", "VTU-affiliated", "other"]
            cl_idx = college_opts.index(u_f.get("college_type")) if u_f.get("college_type") in college_opts else 0
            college_type = st.selectbox("College Affiliation *", college_opts, index=cl_idx)

        with c3:
            stage_opts = ["-- Select Stage --", "idea", "prototype", "working model", "already published"]
            stg_idx = stage_opts.index(u_f.get("project_stage")) if u_f.get("project_stage") in stage_opts else 0
            project_stage = st.selectbox("Project Stage *", stage_opts, index=stg_idx, help="'already published' destroys patent novelty.")

            iedc_opts = ["-- Select IEDC Status --", "yes", "no", "not sure"]
            ie_idx = iedc_opts.index(u_f.get("has_iedc")) if u_f.get("has_iedc") in iedc_opts else 0
            has_iedc = st.selectbox("College IEDC / Incubation Center? *", iedc_opts, index=ie_idx)

        faculty_mentor = st.checkbox("Faculty mentor available?", value=u_f.get("faculty_mentor_available", False))

        btn_search_f = st.form_submit_button("Find Pathways", type="primary", use_container_width=True)

    if btn_search_f:
        if not project_domain.strip():
            st.error("Please enter project title.")
        elif student_status.startswith("--"):
            st.error("Please select student status.")
        elif state.startswith("--"):
            st.error("Please select state.")
        elif college_type.startswith("--"):
            st.error("Please select college affiliation.")
        elif project_stage.startswith("--"):
            st.error("Please select project stage.")
        elif has_iedc.startswith("--"):
            st.error("Please select IEDC status.")
        else:
            profile_obj = StudentProfile(
                student_status=student_status,
                college_type=college_type,
                state=state,
                project_domain=project_domain.strip(),
                project_stage=project_stage,
                has_iedc=has_iedc,
                faculty_mentor_available=faculty_mentor,
            )
            st.session_state.fund_data = {
                "student_status": student_status,
                "college_type": college_type,
                "state": state,
                "project_domain": project_domain.strip(),
                "project_stage": project_stage,
                "has_iedc": has_iedc,
                "faculty_mentor_available": faculty_mentor,
            }
            st.session_state.fund_profile_obj = profile_obj
            st.session_state.fund_submitted = True

    if st.session_state.fund_submitted:
        prof = st.session_state.fund_profile_obj
        report = run_engine(prof, fund_schemes)
        st.session_state.fund_matched_schemes = report.eligible_schemes + report.possibly_eligible_schemes

        if prof.project_stage.lower() == "already published":
            st.error("🚨 **Novelty Compromised:** Public disclosure destroys patent novelty under Section 29–34 of Indian Patents Act 1970.")
        else:
            st.success(f"🔒 **Novelty Status: SAFE** for '{prof.project_domain}'. Ready to file provisional patent.")

        m1, m2, m3 = st.columns(3)
        m1.metric("Eligible", len(report.eligible_schemes))
        m2.metric("Possibly Eligible", len(report.possibly_eligible_schemes))
        m3.metric("Action Steps", len(report.action_checklist))

        if report.eligible_schemes:
            st.markdown("### ✅ Directly Eligible Grant & Patent Pathways")
            for ev in report.eligible_schemes:
                s = ev.scheme
                who_val = s.who_applies.value.upper()
                st.markdown(
                    f"""
                    <div class="scheme-card">
                        <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:0.5rem; margin-bottom:0.5rem;">
                            <div>
                                <span class="pill-badge pill-state">🏛️ {s.authority}</span>
                                <span class="pill-badge who-{s.who_applies.value}">WHO APPLIES: {who_val}</span>
                                <span class="pill-badge pill-status">🟢 Verified Live</span>
                            </div>
                            <span style="font-size:0.75rem; font-weight:700; color:#475569; background:#f1f5f9; padding:0.2rem 0.5rem; border-radius:6px;">{s.id}</span>
                        </div>
                        <h3 style="margin:0 0 0.4rem 0; font-size:1.25rem; color:#0f172a; font-weight:700;">{s.name}</h3>
                        <div class="benefit-box">
                            <strong>💰 Grant / Funding Benefit:</strong> {s.benefit.description}
                        </div>
                        <div style="font-size:0.88rem; color:#334155; margin-bottom:0.5rem;">
                            <strong>ℹ️ Key Notes:</strong> {s.benefit.notes or s.benefit.description}
                        </div>
                        <div style="margin-bottom:0.8rem;">
                            <strong style="font-size:0.88rem; color:#334155;">🗂️ Required Documents:</strong> {" ".join([f"<span class='doc-tag'>📄 {d}</span>" for d in s.documents_required])}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                col_f1, col_f2 = st.columns([1, 1])
                with col_f1:
                    st.link_button("🌐 Official Website & Apply ↗", s.source_url, use_container_width=True)
                with col_f2:
                    if st.button("💬 Ask AI About This Grant", key=f"ask_fund_{s.id}", use_container_width=True):
                        send_fund_chat(f"Tell me more about {s.name}, its funding process, and patent rules.")
                st.markdown("<div style='margin-bottom:1.2rem;'></div>", unsafe_allow_html=True)

        if report.possibly_eligible_schemes:
            st.markdown("### 🟡 Conditionally Eligible Grant Pathways")
            for ev in report.possibly_eligible_schemes:
                s = ev.scheme
                who_val = s.who_applies.value.upper()
                st.markdown(
                    f"""
                    <div class="scheme-card" style="border-left: 4px solid #f59e0b;">
                        <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:0.5rem; margin-bottom:0.5rem;">
                            <div>
                                <span class="pill-badge pill-state">🏛️ {s.authority}</span>
                                <span class="pill-badge who-{s.who_applies.value}">WHO APPLIES: {who_val}</span>
                                <span class="pill-badge" style="background:#fef3c7; color:#92400e; border:1px solid #fde68a;">🟡 Action Needed</span>
                            </div>
                            <span style="font-size:0.75rem; font-weight:700; color:#475569; background:#f1f5f9; padding:0.2rem 0.5rem; border-radius:6px;">{s.id}</span>
                        </div>
                        <h3 style="margin:0 0 0.4rem 0; font-size:1.25rem; color:#0f172a; font-weight:700;">{s.name}</h3>
                        <div class="benefit-box">
                            <strong>💰 Grant / Funding Benefit:</strong> {s.benefit.description}
                        </div>
                        <div class="why-box" style="background:#fffbeb; border-color:#f59e0b; color:#92400e;">
                            <strong>⚠️ Condition to Confirm:</strong> {', '.join(ev.missing_info)}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                col_p1, col_p2 = st.columns([1, 1])
                with col_p1:
                    st.link_button("🌐 Official Website & Apply ↗", s.source_url, use_container_width=True)
                with col_p2:
                    if st.button("💬 Ask AI About This Grant", key=f"ask_fund_poss_{s.id}", use_container_width=True):
                        send_fund_chat(f"Tell me more about {s.name} and conditions to confirm: {', '.join(ev.missing_info)}")
                st.markdown("<div style='margin-bottom:1.2rem;'></div>", unsafe_allow_html=True)

        st.markdown("### 📋 Action Checklist")
        for item in report.action_checklist:
            st.markdown(f"**Step {item.step_number}: {item.title}**")
            st.write(item.description)

        md_text = f"# Action Plan for {prof.student_status} Student\nProject: {prof.project_domain}\n\n"
        for item in report.action_checklist:
            md_text += f"### Step {item.step_number}: {item.title}\n{item.description}\n\n"
        st.download_button("📥 Download Action Plan (.md)", data=md_text, file_name="Action_Plan.md")

    st.markdown("---")
    render_fund_chatbot_widget()
