# HireMind — MVP1

AI-powered placement preparation and hiring simulation platform. Two modes on
one evaluation engine: **Practice** (everything open) and **Simulation**
(rounds unlock only after you clear the previous round's cutoff — decided
entirely by the Flask backend, never the frontend).

This build implements the first slice of the roadmap in the product spec:
auth, dashboard, and two fully-wired rounds (**Aptitude**, **DSA**) in both
modes, with the server-side lock/cutoff engine that every later round will
plug into.

## What's actually working right now

- **Auth** — signup/login/logout/session, backed by Supabase Auth (or a local
  JSON store if Supabase isn't configured — see below).
- **Dashboard** — Practice Mode round cards + a Simulation Mode track rail,
  both rendered from what the backend reports, not assumed client-side.
- **Round engine** (`backend/services/round_engine.py`) — the single source
  of truth for lock/unlock/cleared status and cutoffs. Resume Screening isn't
  built yet, so it's marked auto-cleared for now rather than permanently
  blocking everything downstream — remove it from `AUTO_CLEARED_ROUNDS` once
  its scoring route exists.
- **Aptitude round** — 8-question sets pulled from a bank of 12 (quant /
  logical / verbal), 15-minute timer, per-question review with explanations,
  weak-topic detection, and the exact accuracy/speed/difficulty weighting
  from the spec (60/20/20).
- **DSA round** — 4 problems, in-browser code editor, "Run" against public
  tests, "Submit" against public + hidden tests inside a resource-limited
  subprocess sandbox (CPU/memory/time-capped, `-I` isolated interpreter, no
  network). Scored on correctness/complexity/code quality/speed (50/20/15/15)
  — complexity and code quality currently come from a lightweight static
  heuristic (loop-depth + structure use), flagged in code as the seam to
  swap in an LLM code reviewer later.
- **Cutoff-gated progression** — verified end-to-end: DSA simulation mode
  returns 403 until Aptitude simulation mode is cleared; clearing it unlocks
  DSA immediately.

## What's scaffolded but not yet built

Everything else in the spec (Technical/Project Defense/HR rounds, the voice
interview engine, resume parsing/RAG, company-specific tracks, analytics) has
its home already staked out — `Config.SCORING_WEIGHTS`, `Config.ROUND_ORDER`,
`Config.COMPANY_TRACKS`, and the dashboard's "Coming soon" cards are all
wired for them — but no evaluation logic exists yet. Building one of these is
the natural next step; say which one and it's next.

## Run it

```bash
cd backend
pip install -r requirements.txt   # or: pip install flask python-dotenv (supabase optional for local dev)
python app.py
```

Open `http://localhost:5000`. No Supabase account needed to try it — without
`SUPABASE_URL`/`SUPABASE_ANON_KEY` set, `services/supabase_client.py`
transparently falls back to `backend/data/local_db.json`. Wiring up real
Supabase later is a matter of setting those two env vars (see `.env.example`)
— no route code changes, since routes only ever talk to `supabase_service`.

## Project layout

```
backend/
  app.py                    Flask app + static frontend serving
  config.py                 Round order, cutoffs, company tracks, scoring weights
  routes/                   auth, dashboard, aptitude, dsa (one blueprint each)
  services/
    supabase_client.py      Supabase wrapper w/ local-JSON fallback
    round_engine.py         Lock/unlock/cutoff authority (backend-only, per spec)
    scoring.py               Per-round weighted scoring formulas
    code_sandbox.py         Resource-limited subprocess runner for DSA
  data/                     Question/problem banks + local dev "database"
frontend/
  index.html, login.html, signup.html, dashboard.html
  practice/aptitude.html, practice/dsa.html
  css/style.css             Design tokens + base components
  css/pages.css             Page-specific layout (track rail, editor, timer, report)
  js/                       Vanilla JS only, no build step, no React (per spec)
```

## Design notes

Visual direction is "interview room," not "SaaS dashboard": deep
charcoal-navy background, one warm amber accent used as a recurring
**status light** (the studio tally-light metaphor) that shows round state
everywhere — pulsing amber mid-round, solid green cleared, dim locked.
Numbers (scores, timers, cutoffs) are always set in monospace to read like a
scoreboard.

## Known limitations to flag before real deployment

- The DSA sandbox is subprocess + `resource` limits, which is fine for a
  prototype but not a real isolation boundary — `code_sandbox.py` has a
  comment marking where to swap in gVisor/Firecracker/a hosted judge before
  Phase 14 (Security & Testing).
- Local-store passwords are plaintext (dev-only fallback); real Supabase
  Auth handles hashing once credentials are configured.
- No rate limiting on `/api/dsa/run` yet — worth adding before this is
  public-facing.
