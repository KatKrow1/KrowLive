-- KrowLive database schema
-- Run this entire script in Supabase SQL Editor (Dashboard → SQL → New query)

-- ---------------------------------------------------------------------------
-- Extensions
-- ---------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ---------------------------------------------------------------------------
-- Enums
-- ---------------------------------------------------------------------------
DO $$ BEGIN
  CREATE TYPE country_code AS ENUM ('CA', 'AU');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE company_source AS ENUM ('google_places', 'csv_upload');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE consent_status AS ENUM ('unknown', 'opted_in', 'opted_out');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE job_status AS ENUM ('idle', 'running', 'completed', 'failed');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

-- ---------------------------------------------------------------------------
-- Companies
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS companies (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name                TEXT NOT NULL,
  address             TEXT,
  city                TEXT,
  state               TEXT,
  country             country_code NOT NULL,
  phone               TEXT,
  website             TEXT NOT NULL UNIQUE,
  category            TEXT,
  google_rating       NUMERIC(2, 1),
  google_review_count INTEGER,
  lead_score          INTEGER CHECK (lead_score >= 0 AND lead_score <= 100),
  summary             TEXT,
  tech_stack_signals  JSONB NOT NULL DEFAULT '[]'::jsonb,
  social_links        JSONB NOT NULL DEFAULT '{}'::jsonb,
  source              company_source NOT NULL DEFAULT 'google_places',
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_companies_country ON companies (country);
CREATE INDEX IF NOT EXISTS idx_companies_state ON companies (state);
CREATE INDEX IF NOT EXISTS idx_companies_city ON companies (city);
CREATE INDEX IF NOT EXISTS idx_companies_category ON companies (category);
CREATE INDEX IF NOT EXISTS idx_companies_lead_score ON companies (lead_score DESC);
CREATE INDEX IF NOT EXISTS idx_companies_source ON companies (source);
CREATE INDEX IF NOT EXISTS idx_companies_social_links ON companies USING gin (social_links);

-- ---------------------------------------------------------------------------
-- Executives (consent_status required for CASL / Spam Act compliance)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS executives (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id      UUID NOT NULL REFERENCES companies (id) ON DELETE CASCADE,
  name            TEXT NOT NULL,
  title           TEXT,
  email           TEXT,
  phone           TEXT,
  linkedin_url    TEXT,
  consent_status  consent_status NOT NULL DEFAULT 'unknown',
  extraction_confidence TEXT NOT NULL DEFAULT 'low' CHECK (extraction_confidence IN ('high', 'medium', 'low')),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_executives_company_id ON executives (company_id);
CREATE INDEX IF NOT EXISTS idx_executives_consent_status ON executives (consent_status);

-- ---------------------------------------------------------------------------
-- Jobs (single-row progress tracker for discovery / upload tasks)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS jobs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_type        TEXT NOT NULL DEFAULT 'discovery',
  status          job_status NOT NULL DEFAULT 'idle',
  progress        INTEGER NOT NULL DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
  message         TEXT,
  total_items     INTEGER NOT NULL DEFAULT 0,
  processed_items INTEGER NOT NULL DEFAULT 0,
  error           TEXT,
  started_at      TIMESTAMPTZ,
  completed_at    TIMESTAMPTZ,
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed a single idle job row the API can update (only if table is empty)
INSERT INTO jobs (job_type, status, message)
SELECT 'discovery', 'idle', 'Ready'
WHERE NOT EXISTS (SELECT 1 FROM jobs LIMIT 1);

-- ---------------------------------------------------------------------------
-- updated_at trigger
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_companies_updated_at ON companies;
CREATE TRIGGER trg_companies_updated_at
  BEFORE UPDATE ON companies
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_executives_updated_at ON executives;
CREATE TRIGGER trg_executives_updated_at
  BEFORE UPDATE ON executives
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_jobs_updated_at ON jobs;
CREATE TRIGGER trg_jobs_updated_at
  BEFORE UPDATE ON jobs
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ---------------------------------------------------------------------------
-- Row Level Security (service role bypasses; enable for future auth)
-- ---------------------------------------------------------------------------
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE executives ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on companies"
  ON companies FOR ALL
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Service role full access on executives"
  ON executives FOR ALL
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Service role full access on jobs"
  ON jobs FOR ALL
  USING (true)
  WITH CHECK (true);
