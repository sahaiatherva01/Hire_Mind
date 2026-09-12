# HireMind AI — Agent Development & Engineering Guidelines

This document outlines the architectural rules, agent contracts, and coding standards for the HireMind AI platform.

---

## 1. Project Organization Principle
- The codebase follows a flat, high-cohesion module structure (`core/`, `db/`, `resume/`, `interview/`, `recruit/`).
- Avoid "AI-sprawl":
  - Group related agents in domain-specific `agents.py` modules rather than scattering one class per file.
  - No boilerplate placeholder files (`utils2.py`, `helpers.py`, `_v2.py`).
  - Keep configuration consolidated in `config.py`.

---

## 2. Agent Response Contract
Every specialist agent must inherit from `core.evaluation.BaseAgent` and return a typed output conforming to:
```json
{
  "result": { ... },
  "evidence": [
    {
      "source_collection": "kb_resume_best_practices",
      "doc_id": "rbp-001",
      "content": "Explanation or rule excerpt",
      "similarity": 0.89
    }
  ],
  "confidence": 0.95
}
```
All runs automatically log an entry to the `evaluations` database table via `db_client.log_evaluation`.

---

## 3. RAG Retrieval (`core/retrieval.py`)
- Call `core.retrieval.retrieve(query, collection, top_k, filter_criteria)` for knowledge-grounded operations.
- Collections:
  1. `kb_interview_questions`: Technical, project defense, and behavioral questions.
  2. `kb_skills_taxonomy`: Canonical skills, categories, synonyms, and weighted adjacencies.
  3. `kb_jd_corpus`: Anonymized job descriptions with skill weights and seniority levels.
  4. `kb_resume_best_practices`: Google XYZ formulas, action verbs, and ATS layout guidelines.
  5. `kb_company_interview_style`: Left empty (`[]`) until populated through authenticated enterprise tenant ingestion.
- The retrieval function executes Supabase `pgvector` RPC matches when connected, or deterministic local vector cosine calculations when offline.

---

## 4. Multi-Tenant Isolation
- In `recruit/routes.py`, every operation is tenant-scoped via `company_id`.
- Recruiters can only access jobs, candidate submissions, and assessment data matching their assigned `company_id`.
- Tenant violations must return `403 Forbidden`.

---

## 5. Non-Negotiables
- **No Hallucinated Scores**: ATS+ and interview scores must be genuinely calculated from candidate input data using the rubrics in `core/scoring.py`.
- **Evidence-Backed**: Every AI score or recommendation must cite retrieved knowledge base rules or explicit document features.
- **No Personality / Emotion / Honesty Inference**: The interview engine evaluates technical correctness, problem-solving structure, and communication clarity without making subjective psychological inferences.
