# HireMind AI — Agentic Career Intelligence & Interview Simulator

A unified career intelligence and recruitment platform combining Resume Intelligence, ATS+ 105-Point Rubric Scoring, Adaptive Multi-Stage Technical & Behavioral Interview Simulation, and Recruiter Semantic Screening with pgvector RAG.

---

## 1. Clean Architectural Layout

Organized deliberately for clarity, high cohesion, and minimal surface area:

```
HireMind/
├── app.py                     # Flask application factory, routes, and asset dispatch
├── config.py                  # Single source of configuration, pinned models, and paths
├── requirements.txt           # Minimal Python runtime dependencies
├── .env.example               # Environment variables template
├── README.md                  # System overview and quickstart
├── AGENTS.md                  # Multi-agent architecture and development guidelines
│
├── core/                      # Shared platform intelligence
│   ├── gemini.py              # Pinned Gemini model API wrapper and embeddings
│   ├── retrieval.py           # Shared RAG retrieve() with pgvector & cosine fallback
│   ├── evaluation.py          # BaseAgent contract {result, evidence, confidence} & audit logger
│   └── scoring.py             # ATS+ 105-point rubric & simulation progression authority
│
├── db/                        # Database schema, storage client, and verified seed data
│   ├── client.py              # Unified Supabase client with local JSON fallback
│   ├── schema.sql             # PostgreSQL schema with pgvector IVFFlat indexes
│   ├── README.md              # Seed data source provenance notes
│   └── data/                  # Verified JSON datasets for RAG and practice problems
│
├── resume/                    # Module A: Resume Intelligence & ATS+ Engine
│   ├── parsing.py             # PyMuPDF and python-docx layout and text parser
│   ├── agents.py              # Skill extraction, ATS rubric, JD match, and bullet rewrite agents
│   └── routes.py              # Flask API endpoints for resume scanning and analysis
│
├── interview/                 # Module B: Interview Simulator & Practice Track
│   ├── agents.py              # Planning, Technical, Project Defense, HR, and Evaluation agents
│   ├── sandbox.py             # Subprocess Python execution sandbox with test cases
│   └── routes.py              # Endpoints for live interviews, aptitude tests, and DSA challenges
│
├── recruit/                   # Module C: B2B Recruiter Screening & Ranking
│   ├── agents.py              # JD parser, bulk semantic matcher, ranking, and assessment agents
│   └── routes.py              # Recruiter endpoints with strict multi-tenant isolation (company_id)
│
├── dashboard/                 # Candidate progression & readiness score endpoints
│   └── routes.py
│
├── auth/                      # Authentication & session endpoints
│   └── routes.py
│
├── static/                    # Glassmorphic UI stylesheets and vanilla JS modules
│   ├── css/
│   └── js/
│
├── templates/                 # Semantic HTML views (SPA & standalone pages)
│
└── tests/                     # Automated test suites
    ├── test_agentic_rag.py    # End-to-end verification of all agents & RAG collections
    ├── test_tenant_isolation.py # Verifies strict cross-company isolation
    ├── test_input_dependence.py # Verifies differential scoring based on real resume inputs
    └── test_api_endpoints.py  # Full suite verification across all HTTP routes
```

---

## 2. Core Modules

1. **Resume Intelligence (Module A)**:
   - Evaluates documents against an **ATS+ 105-point rubric** (Contact Info, Document Structure, Keyword Relevance, Content Quality, Skills Representation, Quantifiable Metrics, Formatting).
   - Identifies skill gaps against target Job Descriptions.
   - Rewrites weak resume bullets using the **Google XYZ formula** ("Accomplished [X] as measured by [Y], by doing [Z]") grounded in retrieved exemplars.

2. **Adaptive AI Interviewer (Module B)**:
   - Simulates multi-stage technical, project defense, and behavioral STAR interviews.
   - Dynamic follow-up cross-questioning responding directly to the candidate's actual answers.
   - Built-in **Python Code Sandbox** for real-time algorithmic coding challenges with visible and hidden edge-case tests.

3. **Recruiter Portal (Module C)**:
   - Batch resume parsing, semantic matching, and normalized ranking.
   - Auto-generates customized assessment questions for target job requisitions.
   - **Strict Multi-Tenant Isolation**: Enforces tenant authorization (`company_id`) on all job listings, candidate submissions, and assessment data.

4. **Simulation Track & Unified Readiness (Module D)**:
   - 6 sequential simulation rounds guarded by backend cutoff rules (Resume Screening 70 $\rightarrow$ Aptitude 65 $\rightarrow$ DSA 70 $\rightarrow$ Technical 70 $\rightarrow$ Project Defense 75 $\rightarrow$ HR 70).
   - Computes weighted overall Candidate Readiness (0–100 scale).

---

## 3. Getting Started

### Prerequisites
- Python 3.10+
- (Optional) Gemini API Key & Supabase URL/Key

### Installation
```bash
git clone https://github.com/your-username/Hire_Mind.git
cd Hire_Mind

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env
```

### Running Locally
```bash
python3 app.py
```
Open [http://127.0.0.1:5001](http://127.0.0.1:5001) in your browser.

### Running Test Suites
```bash
# Run full regression suite (9/9 tests)
pytest tests/ -v
```

---

## 4. Deploying to Render

HireMind AI is production-ready for deployment as a Web Service on [Render](https://render.com/).

### 1. Build & Start Configuration
- **Environment**: `Python`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT` (or use the included `Procfile`)

### 2. Environment Variables on Render Dashboard
Set these in **Environment** under your Render Web Service:

| Variable | Recommended Value | Notes |
| :--- | :--- | :--- |
| `HIREMIND_SECRET_KEY` | *(Generated random 32+ char string)* | Production Flask session secret |
| `FLASK_DEBUG` | `0` | Disables debug mode in production |
| `GEMINI_API_KEY` | *(Your Gemini API key)* | Required for live LLM reasoning and embeddings |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Pinned Flash model |
| `SUPABASE_URL` | `https://<your-project>.supabase.co` | Remote Supabase project URL |
| `SUPABASE_KEY` | *(Your Supabase service_role key)* | Used for server-side PostgreSQL & pgvector queries |
| `SUPABASE_ANON_KEY`| *(Your Supabase anon public key)* | Supabase client authentication |

### 3. Remote Supabase Setup Checklist
1. **Execute Schema**: Copy and run the contents of [`db/schema.sql`](file:///Users/sahaiatherva/Desktop/Hire_Mind/db/schema.sql) in your **Supabase SQL Editor** to create pgvector tables, match RPC functions, and IVFFlat indexes.
2. **Storage Bucket**: In the Supabase Dashboard under **Storage**, create a bucket named `resumes` (public or authenticated) so candidate uploads persist across Render dyno restarts.
3. **Verify Deployment**: Hit `https://<your-render-subdomain>.onrender.com/api/health` and verify:
   ```json
   {
     "status": "healthy",
     "supabase_connected": true,
     "gemini_active": true,
     "schema_status": "schema_ready"
   }
   ```

