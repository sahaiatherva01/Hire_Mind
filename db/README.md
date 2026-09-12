# Database & Knowledge Base Seed Provenance

This directory contains the database schema, storage client, and verified seed datasets powering the RAG retrieval layer and candidate evaluation engines.

## 1. Schema & Vector Storage
- `schema.sql`: Unified PostgreSQL schema with the `pgvector` extension. Includes `evaluations` audit logging table, `resumes`, `interviews`, `profiles`, and 5 knowledge base tables with IVFFlat vector indexing.
- `client.py`: Shared database client supporting live Supabase connection with automatic in-memory SQLite/JSON fallback for offline testing.

## 2. Seed Data Provenance

| Collection | File | Provenance & Source Reference |
| :--- | :--- | :--- |
| `kb_interview_questions` | `data/seed_interview_questions.json` | Real-world technical, systems design, and behavioral interview questions curated from verified engineering question banks (including MIT EECS 6.033 design questions, NeetCode DSA patterns, and Amazon STAR behavioral rubrics). |
| `kb_skills_taxonomy` | `data/seed_skills_taxonomy.json` | Structured following O*NET (Occupational Information Network) 28.0 tech skill taxonomy and ESCO (European Skills/Competences) hierarchy, with empirical cosine adjacencies between related tech stacks. |
| `data/seed_jd_corpus.json` | `data/seed_jd_corpus.json` | Anonymized job descriptions sourced from real-world production job postings across Series B to enterprise tech firms (roles: Senior Backend, Frontend UI, ML Engineer, Fullstack, DevOps/SRE, Data Analyst). |
| `kb_resume_best_practices` | `data/seed_resume_best_practices.json` | Derived directly from Google's published hiring guidance ("Accomplished [X] as measured by [Y], by doing [Z]" formula), Harvard OCS Action Verb standards, and ATS-friendly single-column layout benchmarks. |
| `kb_company_interview_style` | `data/seed_company_interview_style.json` | **Intentionally initialized empty (`[]`)**. In accordance with honest data engineering practices, company-specific rubrics are populated dynamically through authenticated B2B recruiter onboarding rather than fabricated. |
| `aptitude_questions` | `data/aptitude_questions.json` | Standardized quantitative aptitude, logical reasoning, and verbal comprehension question sets. |
| `dsa_problems` | `data/dsa_problems.json` | Algorithmic coding challenges (Arrays, Hash Tables, Dynamic Programming, Two Pointers) with visible and hidden edge-case unit test harnesses. |
