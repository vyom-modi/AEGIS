-- ============================================
-- AEGIS — Supabase Schema
-- Run this in Supabase SQL Editor
-- ============================================

-- Enable pgvector for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- ── Goals ────────────────────────────────────

CREATE TABLE IF NOT EXISTS goals (
    id          uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    title       text NOT NULL,
    description text NOT NULL DEFAULT '',
    status      text NOT NULL DEFAULT 'pending',
    schedule    text,
    created_at  timestamptz DEFAULT now(),
    last_run_at timestamptz
);

CREATE INDEX idx_goals_status ON goals(status);
CREATE INDEX idx_goals_created ON goals(created_at DESC);


-- ── Plans ────────────────────────────────────

CREATE TABLE IF NOT EXISTS plans (
    id          uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    goal_id     uuid REFERENCES goals(id) ON DELETE CASCADE,
    plan_json   jsonb NOT NULL DEFAULT '{}',
    score       float DEFAULT 0.0,
    created_at  timestamptz DEFAULT now()
);

CREATE INDEX idx_plans_goal ON plans(goal_id);


-- ── Tasks ────────────────────────────────────

CREATE TABLE IF NOT EXISTS tasks (
    id             uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    plan_id        uuid REFERENCES plans(id) ON DELETE CASCADE,
    name           text NOT NULL,
    description    text NOT NULL DEFAULT '',
    status         text NOT NULL DEFAULT 'pending',
    assigned_agent text,
    retries        integer DEFAULT 0,
    created_at     timestamptz DEFAULT now()
);

CREATE INDEX idx_tasks_plan ON tasks(plan_id);
CREATE INDEX idx_tasks_status ON tasks(status);


-- ── Runs ─────────────────────────────────────

CREATE TABLE IF NOT EXISTS runs (
    id          uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    task_id     uuid REFERENCES tasks(id) ON DELETE CASCADE,
    logs        text,
    success     boolean DEFAULT false,
    token_cost  float DEFAULT 0.0,
    latency     float DEFAULT 0.0,
    created_at  timestamptz DEFAULT now()
);

CREATE INDEX idx_runs_task ON runs(task_id);


-- ── Tools ────────────────────────────────────

CREATE TABLE IF NOT EXISTS tools (
    id          uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    name        text NOT NULL,
    code        text NOT NULL,
    description text NOT NULL DEFAULT '',
    trust_score float DEFAULT 0.0,
    created_at  timestamptz DEFAULT now()
);


-- ── Metrics ──────────────────────────────────

CREATE TABLE IF NOT EXISTS metrics (
    id          uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    metric_name text NOT NULL,
    value       float NOT NULL DEFAULT 0.0,
    timestamp   timestamptz DEFAULT now()
);

CREATE INDEX idx_metrics_name ON metrics(metric_name);
CREATE INDEX idx_metrics_time ON metrics(timestamp DESC);


-- ── Strategies ───────────────────────────────

CREATE TABLE IF NOT EXISTS strategies (
    id           uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    name         text NOT NULL,
    parameters   jsonb NOT NULL DEFAULT '{}',
    success_rate float DEFAULT 0.0
);


-- ── Skills ───────────────────────────────────

CREATE TABLE IF NOT EXISTS skills (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name            text NOT NULL,
    slug            text UNIQUE,
    description     text DEFAULT '',
    version         text,
    license         text,
    source_url      text,
    raw_markdown    text,
    metadata        jsonb DEFAULT '{}',
    trust_score     float DEFAULT 0,
    installed       boolean DEFAULT false,
    installed_at    timestamptz,
    last_scanned_at timestamptz,
    created_at      timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_skills_slug ON skills(slug);
CREATE INDEX IF NOT EXISTS idx_skills_installed ON skills(installed);
CREATE INDEX IF NOT EXISTS idx_skills_trust ON skills(trust_score DESC);


-- ── Row Level Security ───────────────────────
-- Disable RLS for service_role access (backend uses service key)

ALTER TABLE goals      ENABLE ROW LEVEL SECURITY;
ALTER TABLE plans      ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks      ENABLE ROW LEVEL SECURITY;
ALTER TABLE runs       ENABLE ROW LEVEL SECURITY;
ALTER TABLE tools      ENABLE ROW LEVEL SECURITY;
ALTER TABLE metrics    ENABLE ROW LEVEL SECURITY;
ALTER TABLE strategies ENABLE ROW LEVEL SECURITY;
ALTER TABLE skills     ENABLE ROW LEVEL SECURITY;

-- Allow full access for service_role
CREATE POLICY "Service role full access" ON goals      FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON plans      FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON tasks      FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON runs       FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON tools      FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON metrics    FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON strategies FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON skills     FOR ALL USING (true) WITH CHECK (true);

