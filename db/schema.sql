-- =========================================================
-- HireMind AI — Unified Schema with pgvector
-- Run this in Supabase SQL Editor.
-- =========================================================

-- Enable pgvector and pgcrypto extensions
create extension if not exists vector;
create extension if not exists pgcrypto;

-- ---------------------------------------------------------
-- 1. Knowledge Base Collections (RAG Layer)
-- ---------------------------------------------------------

-- 1.1 Interview Questions Collection
create table if not exists public.kb_interview_questions (
    id uuid primary key default gen_random_uuid(),
    question_text text not null,
    role text not null,                      -- e.g. 'Backend Engineer', 'Frontend Engineer', 'Fullstack', 'ML Engineer', 'DevOps', 'General'
    skill text not null,                     -- e.g. 'Java', 'Python', 'React', 'System Design', 'Behavioral', 'Concurrency'
    difficulty text check (
        difficulty in ('easy', 'medium', 'hard')
    ) default 'medium',
    stage text check (
        stage in ('technical', 'project_defense', 'hr', 'aptitude')
    ) not null,
    company_tags text[] default '{}',        -- e.g. ['Amazon', 'Google', 'Startup']
    sample_criteria text,                   -- What a strong answer includes
    embedding vector(768),                  -- Gemini text-embedding-004 (768 dimensions)
    metadata jsonb default '{}'::jsonb,
    created_at timestamptz default now()
);

-- Index for fast cosine similarity search
create index if not exists kb_interview_questions_embedding_idx
on public.kb_interview_questions
using ivfflat (embedding vector_cosine_ops)
with (lists = 100);


-- 1.2 Skills Taxonomy Collection
create table if not exists public.kb_skills_taxonomy (
    id uuid primary key default gen_random_uuid(),
    canonical_skill text not null unique,    -- e.g. 'Spring Boot'
    category text not null,                  -- 'Languages', 'Frameworks', 'Databases', 'Cloud & DevOps', 'AI & ML', 'Core CS'
    synonyms text[] default '{}',            -- e.g. ['SpringBoot', 'Spring-Boot', 'Spring framework']
    adjacent_skills jsonb default '{}'::jsonb, -- e.g. {"Java": 0.95, "Microservices": 0.85, "REST API": 0.90}
    description text,
    embedding vector(768),
    created_at timestamptz default now()
);

create index if not exists kb_skills_taxonomy_embedding_idx
on public.kb_skills_taxonomy
using ivfflat (embedding vector_cosine_ops)
with (lists = 100);


-- 1.3 Real-World Job Description Corpus
create table if not exists public.kb_jd_corpus (
    id uuid primary key default gen_random_uuid(),
    role_title text not null,                -- e.g. 'Senior Backend Engineer'
    domain text not null,                    -- e.g. 'FinTech', 'Cloud Infrastructure', 'E-Commerce'
    seniority text check (
        seniority in ('intern', 'entry', 'mid', 'senior', 'staff', 'lead')
    ) default 'mid',
    raw_text text not null,
    required_skills text[] default '{}',
    preferred_skills text[] default '{}',
    core_responsibilities text[] default '{}',
    importance_weights jsonb default '{}'::jsonb,
    embedding vector(768),
    created_at timestamptz default now()
);

create index if not exists kb_jd_corpus_embedding_idx
on public.kb_jd_corpus
using ivfflat (embedding vector_cosine_ops)
with (lists = 100);


-- 1.4 Resume Best Practices & Bullet Patterns
create table if not exists public.kb_resume_best_practices (
    id uuid primary key default gen_random_uuid(),
    category text not null,                  -- 'xyz_metric_bullet', 'strong_action_verbs', 'ats_layout_rules', 'leadership_phrasing'
    domain_tags text[] default '{}',         -- e.g. ['Backend', 'Frontend', 'Data', 'Management']
    rule_description text not null,
    before_example text,
    after_example text not null,
    impact_explanation text,
    embedding vector(768),
    created_at timestamptz default now()
);

create index if not exists kb_resume_best_practices_embedding_idx
on public.kb_resume_best_practices
using ivfflat (embedding vector_cosine_ops)
with (lists = 100);


-- 1.5 Company Interview Style Collection
create table if not exists public.kb_company_interview_style (
    id uuid primary key default gen_random_uuid(),
    company_name text not null,              -- e.g. 'Amazon', 'Google', 'Meta', 'Microsoft', 'Startup'
    culture_principles jsonb default '[]'::jsonb, -- e.g. ["Customer Obsession", "Ownership", "Bias for Action"]
    question_patterns jsonb default '[]'::jsonb,
    evaluation_focus text not null,
    rubric_weights jsonb default '{}'::jsonb,
    embedding vector(768),
    created_at timestamptz default now()
);

create index if not exists kb_company_interview_style_embedding_idx
on public.kb_company_interview_style
using ivfflat (embedding vector_cosine_ops)
with (lists = 100);


-- ---------------------------------------------------------
-- 2. Core Platform Tables
-- ---------------------------------------------------------

-- 2.1 Users / Profiles
create table if not exists public.profiles (
    id uuid primary key default gen_random_uuid(),
    email text unique not null,
    full_name text,
    target_role text default 'Software Engineer',
    preferred_track text default 'default',   -- 'default', 'amazon', 'startup'
    created_at timestamptz default now()
);

-- 2.2 Resumes & Canonical Extractions
create table if not exists public.resumes (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references public.profiles(id) on delete set null,
    session_id text not null,
    file_name text,
    file_path text,
    raw_text text,
    parsed_json jsonb,                      -- Canonical profile from Module A
    ats_scores jsonb,                       -- ATS+ 105-pt rubric scores
    completeness_report jsonb,
    created_at timestamptz default now()
);

-- 2.3 Interview Sessions
create table if not exists public.interview_sessions (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references public.profiles(id) on delete set null,
    resume_id uuid references public.resumes(id) on delete set null,
    voice_preference text check (
        voice_preference in ('male', 'female')
    ) default 'male',
    target_role text default 'Software Engineer',
    mode text check (
        mode in ('practice', 'simulation')
    ) default 'practice',
    company_track text default 'default',
    status text check (
        status in ('in_progress', 'completed', 'abandoned')
    ) default 'in_progress',
    overall_score numeric,
    summary_report jsonb,
    created_at timestamptz default now(),
    completed_at timestamptz
);

-- 2.4 Question Bank for Interview Sessions
create table if not exists public.question_bank (
    id uuid primary key default gen_random_uuid(),
    session_id uuid references public.interview_sessions(id) on delete cascade,
    seed_question text not null,
    source_tag text,
    stage text default 'technical',
    topic text default 'general',
    difficulty text default 'medium',
    topic_question_count int default 0,
    status text check (
        status in ('pending', 'active', 'done')
    ) default 'pending',
    order_index int
);

-- 2.5 Live Transcript & Evaluated Turns
create table if not exists public.transcript (
    id uuid primary key default gen_random_uuid(),
    session_id uuid references public.interview_sessions(id) on delete cascade,
    question_bank_id uuid references public.question_bank(id) on delete cascade,
    question_text text not null,
    answer_text text null,                   -- Nullable for pre-created follow-up rows
    is_followup boolean default false,
    gemini_evaluation text,
    reasoning_tag text,
    score numeric,
    created_at timestamptz default now()
);

-- 2.6 Round Progress & Cutoff Tracking (Simulation Mode)
create table if not exists public.round_progress (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references public.profiles(id) on delete cascade,
    round_name text not null check (
        round_name in ('resume_screening', 'aptitude', 'dsa', 'technical', 'project_defense', 'hr')
    ),
    mode text check (
        mode in ('practice', 'simulation')
    ) default 'simulation',
    score numeric not null,
    cutoff numeric not null,
    passed boolean not null,
    breakdown jsonb default '{}'::jsonb,
    attempts int default 1,
    created_at timestamptz default now(),
    unique (user_id, round_name, mode)
);

-- 2.7 Recruiter Portal (Module C)
create table if not exists public.recruit_jobs (
    id uuid primary key default gen_random_uuid(),
    company_id uuid not null,                -- Multi-tenant isolation boundary
    title text not null,
    department text,
    jd_text text not null,
    parsed_requirements jsonb not null,
    status text default 'active',
    created_at timestamptz default now()
);

create table if not exists public.recruit_candidates (
    id uuid primary key default gen_random_uuid(),
    company_id uuid not null,
    job_id uuid references public.recruit_jobs(id) on delete cascade,
    candidate_name text not null,
    email text,
    resume_id uuid references public.resumes(id) on delete set null,
    match_score numeric not null,
    ranking_category text check (
        ranking_category in ('Strong Match', 'Review Needed', 'Weak Match')
    ) not null,
    evidence_summary jsonb not null,
    created_at timestamptz default now()
);

create table if not exists public.recruit_assessments (
    id uuid primary key default gen_random_uuid(),
    company_id uuid not null,
    job_id uuid references public.recruit_jobs(id) on delete cascade,
    title text not null,
    questions jsonb not null,
    duration_minutes int default 30,
    created_at timestamptz default now()
);

-- 2.8 Unified Evaluations & Audit Log (Every Agent Output & RAG retrieval)
create table if not exists public.evaluations (
    id uuid primary key default gen_random_uuid(),
    entity_type text not null,               -- 'resume', 'interview_turn', 'interview_final', 'jd_match', 'bullet_rewrite', 'recruit_rank', 'assessment_gen'
    entity_id text not null,
    orchestrator text not null,              -- 'module_a_orchestrator', 'module_b_orchestrator', 'module_c_orchestrator'
    agent_name text not null,                -- e.g. 'SkillExtractionAgent', 'JDMatchAgent', 'TechnicalAgent'
    result_json jsonb not null,
    evidence_json jsonb not null,
    confidence float not null,
    retrieval_logs jsonb default '[]'::jsonb, -- List of {collection, top_k, query, returned_ids, scores}
    created_at timestamptz default now()
);

-- ---------------------------------------------------------
-- 3. Stored RPC Functions for Vector Similarity Search
-- ---------------------------------------------------------

create or replace function match_interview_questions (
    query_embedding vector(768),
    match_threshold float default 0.3,
    match_count int default 5,
    filter_role text default null,
    filter_stage text default null
)
returns table (
    id uuid,
    question_text text,
    role text,
    skill text,
    difficulty text,
    stage text,
    company_tags text[],
    sample_criteria text,
    similarity float
)
language sql stable
as $$
    select
        q.id,
        q.question_text,
        q.role,
        q.skill,
        q.difficulty,
        q.stage,
        q.company_tags,
        q.sample_criteria,
        1 - (q.embedding <=> query_embedding) as similarity
    from public.kb_interview_questions q
    where
        (filter_role is null or q.role ilike '%' || filter_role || '%' or q.role = 'General')
        and (filter_stage is null or q.stage = filter_stage)
        and (1 - (q.embedding <=> query_embedding)) > match_threshold
    order by q.embedding <=> query_embedding
    limit match_count;
$$;

create or replace function match_skills_taxonomy (
    query_embedding vector(768),
    match_threshold float default 0.3,
    match_count int default 5
)
returns table (
    id uuid,
    canonical_skill text,
    category text,
    synonyms text[],
    adjacent_skills jsonb,
    description text,
    similarity float
)
language sql stable
as $$
    select
        s.id,
        s.canonical_skill,
        s.category,
        s.synonyms,
        s.adjacent_skills,
        s.description,
        1 - (s.embedding <=> query_embedding) as similarity
    from public.kb_skills_taxonomy s
    where (1 - (s.embedding <=> query_embedding)) > match_threshold
    order by s.embedding <=> query_embedding
    limit match_count;
$$;

create or replace function match_jd_corpus (
    query_embedding vector(768),
    match_threshold float default 0.3,
    match_count int default 5,
    filter_domain text default null
)
returns table (
    id uuid,
    role_title text,
    domain text,
    seniority text,
    raw_text text,
    required_skills text[],
    preferred_skills text[],
    core_responsibilities text[],
    importance_weights jsonb,
    similarity float
)
language sql stable
as $$
    select
        j.id,
        j.role_title,
        j.domain,
        j.seniority,
        j.raw_text,
        j.required_skills,
        j.preferred_skills,
        j.core_responsibilities,
        j.importance_weights,
        1 - (j.embedding <=> query_embedding) as similarity
    from public.kb_jd_corpus j
    where
        (filter_domain is null or j.domain ilike '%' || filter_domain || '%')
        and (1 - (j.embedding <=> query_embedding)) > match_threshold
    order by j.embedding <=> query_embedding
    limit match_count;
$$;

create or replace function match_resume_best_practices (
    query_embedding vector(768),
    match_threshold float default 0.3,
    match_count int default 5,
    filter_category text default null
)
returns table (
    id uuid,
    category text,
    domain_tags text[],
    rule_description text,
    before_example text,
    after_example text,
    impact_explanation text,
    similarity float
)
language sql stable
as $$
    select
        b.id,
        b.category,
        b.domain_tags,
        b.rule_description,
        b.before_example,
        b.after_example,
        b.impact_explanation,
        1 - (b.embedding <=> query_embedding) as similarity
    from public.kb_resume_best_practices b
    where
        (filter_category is null or b.category = filter_category)
        and (1 - (b.embedding <=> query_embedding)) > match_threshold
    order by b.embedding <=> query_embedding
    limit match_count;
$$;

create or replace function match_company_interview_style (
    query_embedding vector(768),
    match_threshold float default 0.3,
    match_count int default 3,
    filter_company text default null
)
returns table (
    id uuid,
    company_name text,
    culture_principles jsonb,
    question_patterns jsonb,
    evaluation_focus text,
    rubric_weights jsonb,
    similarity float
)
language sql stable
as $$
    select
        c.id,
        c.company_name,
        c.culture_principles,
        c.question_patterns,
        c.evaluation_focus,
        c.rubric_weights,
        1 - (c.embedding <=> query_embedding) as similarity
    from public.kb_company_interview_style c
    where
        (filter_company is null or c.company_name ilike '%' || filter_company || '%')
        and (1 - (c.embedding <=> query_embedding)) > match_threshold
    order by c.embedding <=> query_embedding
    limit match_count;
$$;

-- Tell PostgREST to reload schema
notify pgrst, 'reload schema';
