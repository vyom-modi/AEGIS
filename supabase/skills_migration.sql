-- ============================================
-- AEGIS — Skills Migration
-- Run this in Supabase SQL Editor AFTER schema.sql
-- ============================================

-- ── Skills table ─────────────────────────────
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

-- ── Add skill linkage to tools ───────────────
ALTER TABLE tools ADD COLUMN IF NOT EXISTS skill_id uuid REFERENCES skills(id);
ALTER TABLE tools ADD COLUMN IF NOT EXISTS auto_installed boolean DEFAULT false;

-- ── RLS ──────────────────────────────────────
ALTER TABLE skills ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access" ON skills FOR ALL USING (true) WITH CHECK (true);
