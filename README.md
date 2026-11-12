# 🏛️ National Scheme & Fund Portal
> **AI-Powered Government Welfare Schemes & Patent Prototype Grants Portal for Indian Citizens & Engineering Innovators**

[![Tests](https://img.shields.io/badge/pytest-15%20passed-brightgreen.svg)](#testing)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![UI](https://img.shields.io/badge/UI-Streamlit-red.svg)](https://streamlit.io/)
[![LLM](https://img.shields.io/badge/Gemini-3.5--flash--lite-orange.svg)](https://ai.google.dev/)
[![Deploy](https://img.shields.io/badge/Deploy-Render-46e3b7.svg)](https://render.com/)

---

## 📌 Overview

The **National Scheme & Fund Portal** unifies two vital discovery channels into a single, intuitive web application:
1. **🏛️ Government Welfare Schemes:** Helps Indian citizens, students, farmers, and families discover central & state welfare benefits, scholarships (CSSS, SSP Post-Matric, Yuva Nidhi), healthcare (Ayushman Bharat), and financial support based on personal profile and criteria.
2. **🚀 Fund & Patent Support Navigator:** Helps engineering students and tech innovators evaluate prototype development grants (DST NIDHI-PRAYAS up to ₹10 Lakhs, KSCST SPP), 100% patent filing fee reimbursement (KAPILA AICTE, SIPP), and verify Section 29–34 novelty protection under the Indian Patents Act 1970.

---

## ✨ Key Features

- **Distraction-Free 2-Card Gateway:** Clean first-page landing with two prominent pathways (`Explore Govt Schemes` and `Explore Funds & Grants`) with zero clutter.
- **Separate AI Chatbots:**
  - `🤖 Government Scheme AI Assistant`: Welfare schemes, scholarships, eligibility rules, and application cycles.
  - `🚀 Patent & Grant AI Assistant`: Prototype grants, incubation funding, patent novelty rules, and provisional patent drafting.
- **💬 Instant "Ask AI" Buttons on Every Card:** Each scheme card features a side-by-side `🌐 Official Website & Apply ↗` link and `💬 Ask AI About This Scheme/Grant` button for instant, grounded breakdowns.
- **Fast Chat Responses (<0.1s):** In-memory caching for instant answers to common questions and scheme inquiries.
- **Zero Hallucination:** Deterministic rule engines backed by 100% verified official government portals (`scholarships.gov.in`, `ipindia.gov.in`, `mic.gov.in`, `kscst.org.in`, `dst.gov.in`).
- **Ordered Action Checklists:** Downloadable personalized Markdown (`.md`) roadmaps for institutional endorsement and patent filing.

---

## 📂 Project Directory Structure

```
grantpath/
├── .streamlit/
│   └── config.toml           # Production Streamlit headless & port config
├── data/
│   └── welfare_schemes.json  # 18 verified central & state welfare schemes
├── tests/
│   ├── test_engine.py        # 9 student grant engine & novelty unit tests
│   ├── test_extractor.py     # 2 schema extraction and persistence unit tests
│   └── test_welfare_engine.py# 4 welfare matching and URL verification unit tests
├── .env.example              # Environment variables template
├── .gitignore                # Production git ignore (secrets, venv, cache)
├── app.py                    # Streamlit responsive frontend & dual chatbots
├── demo_cli.py               # CLI runner for terminal evaluations
├── engine.py                 # Pure Python deterministic grant & patent engine
├── extractor.py              # Gemini LLM scheme extractor & grounded advisor
├── Procfile                  # Web process definition for cloud hosts
├── README.md                 # Complete documentation & deployment guide
├── render.yaml               # Render Blueprint (Infrastructure-as-Code)
├── requirements.txt          # Python dependencies
├── runtime.txt               # Python 3.11.9 runtime specification
├── schemes.json              # 5 verified student patent & prototype schemes
└── welfare_engine.py         # Deterministic matching engine for welfare schemes
```

---

## 🚀 Local Setup & Running

### 1. Clone & Enter Directory
```bash
git clone <your-github-repo-url>
cd grantpath
```

### 2. Set Up Virtual Environment
```bash
python -m venv .venv

# Windows:
.\.venv\Scripts\Activate.ps1

# Linux / macOS:
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Add your Gemini API Key in `.env`:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash-lite
```
*(Note: If `GEMINI_API_KEY` is not provided, the application gracefully falls back to deterministic local knowledge bases without crashing).*

### 5. Run Automated Tests
```bash
python -m pytest tests/ -v
```
*(All 15 tests should pass in ~1.2s)*

### 6. Launch Application
```bash
streamlit run app.py
```
Open **`http://localhost:8501`** in your browser.

---

## 🌐 Deploy to Render

### Method 1: One-Click Render Blueprint (Recommended)
1. Push this repository to GitHub.
2. In the [Render Dashboard](https://dashboard.render.com/), click **New +** → **Blueprint**.
3. Select your GitHub repository.
4. Render will automatically detect [`render.yaml`](file:///C:/Users/HP/.gemini/antigravity/scratch/grantpath/render.yaml) and configure:
   - **Environment:** Python 3.11.9
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.enableCORS false --server.enableXsrfProtection false --server.headless true`
5. In the **Environment Variables** prompt, add:
   - `GEMINI_API_KEY`: *(Your Google Gemini API Key from [Google AI Studio](https://aistudio.google.com/))*
6. Click **Apply** to deploy.

---

### Method 2: Manual Web Service on Render
1. In Render Dashboard, click **New +** → **Web Service**.
2. Connect your GitHub repository.
3. Configure the settings:
   - **Name:** `national-scheme-fund-portal`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.enableCORS false --server.enableXsrfProtection false --server.headless true`
4. Under **Environment Variables**, add:
   - `PYTHON_VERSION`: `3.11.9`
   - `GEMINI_API_KEY`: `your_gemini_api_key`
5. Click **Deploy Web Service**.

---

## 🧪 Testing Summary

- 15 unit tests covering:
  - Persona matching for prototype grants
  - Disqualification checks for early idea stages
  - Patent novelty destruction under Section 29–34 Indian Patents Act
  - State residence and institutional criteria
  - Welfare matching for students, farmers, senior citizens, and PwD
  - 100% verified HTTP status for all official government portals

---

## ⚖️ Ethics & Grounding
- **Zero Hallucination:** Eligibility scoring and matching are 100% deterministic. AI assists strictly in natural-language query guidance and unstructured circular parsing.
- **Official Portals:** All schemes include direct links to verified `.gov.in` and `.nic.in` domains.
