-- KrowLive database schema
-- Run this entire script in Supabase SQL Editor (Dashboard → SQL → New query)
--
-- ID types in production:
--   countries, states → SERIAL (integer)
--   companies, executives, jobs → UUID

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
-- Hierarchy: countries → states (integer IDs)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS countries (
  id          SERIAL PRIMARY KEY,
  code        TEXT NOT NULL UNIQUE,
  name        TEXT NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS states (
  id          SERIAL PRIMARY KEY,
  country_id  INTEGER NOT NULL REFERENCES countries (id) ON DELETE CASCADE,
  name        TEXT NOT NULL,
  slug        TEXT NOT NULL,
  code        TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (country_id, slug)
);

CREATE INDEX IF NOT EXISTS idx_states_country_id ON states (country_id);

INSERT INTO countries (code, name)
VALUES ('CA', 'Canada'), ('AU', 'Australia')
ON CONFLICT (code) DO NOTHING;

-- ---------------------------------------------------------------------------
-- Companies (UUID primary key; integer hierarchy FKs)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS companies (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name                TEXT NOT NULL,
  address             TEXT,
  city                TEXT,
  state               TEXT,
  country             country_code NOT NULL,
  country_id          INTEGER REFERENCES countries (id),
  state_id            INTEGER REFERENCES states (id),
  phone               TEXT,
  website             TEXT NOT NULL UNIQUE,
  google_rating       NUMERIC(2, 1),
  google_review_count INTEGER,
  lead_score          INTEGER CHECK (lead_score >= 0 AND lead_score <= 100),
  summary             TEXT,
  tech_stack_signals  JSONB NOT NULL DEFAULT '[]'::jsonb,
  social_links        JSONB NOT NULL DEFAULT '{}'::jsonb,
  source              company_source NOT NULL DEFAULT 'google_places',
  last_scraped_at     TIMESTAMPTZ,
  source_url          TEXT,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_companies_country ON companies (country);
CREATE INDEX IF NOT EXISTS idx_companies_country_id ON companies (country_id);
CREATE INDEX IF NOT EXISTS idx_companies_state_id ON companies (state_id);
CREATE INDEX IF NOT EXISTS idx_companies_state ON companies (state);
CREATE INDEX IF NOT EXISTS idx_companies_city ON companies (city);
CREATE INDEX IF NOT EXISTS idx_companies_lead_score ON companies (lead_score DESC);
CREATE INDEX IF NOT EXISTS idx_companies_source ON companies (source);
CREATE INDEX IF NOT EXISTS idx_companies_social_links ON companies USING gin (social_links);

-- ---------------------------------------------------------------------------
-- Executives
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
  source_url      TEXT,
  scraped_at      TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_executives_company_id ON executives (company_id);
CREATE INDEX IF NOT EXISTS idx_executives_consent_status ON executives (consent_status);

-- ---------------------------------------------------------------------------
-- Jobs
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

INSERT INTO jobs (job_type, status, message)
SELECT 'discovery', 'idle', 'Ready'
WHERE NOT EXISTS (SELECT 1 FROM jobs LIMIT 1);

-- ---------------------------------------------------------------------------
-- lead_status, saved_searches, webhooks (see migration_features.sql)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS lead_status (
  company_id UUID PRIMARY KEY REFERENCES companies (id) ON DELETE CASCADE,
  status TEXT NOT NULL DEFAULT 'new'
    CHECK (status IN ('new', 'contacted', 'replied', 'not_interested')),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS saved_searches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  industry TEXT NOT NULL,
  country TEXT NOT NULL,
  states JSONB NOT NULL DEFAULT '[]'::jsonb,
  cities JSONB NOT NULL DEFAULT '[]'::jsonb,
  max_results INTEGER NOT NULL DEFAULT 5,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_run_at TIMESTAMPTZ,
  last_result_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS webhooks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  url TEXT NOT NULL,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

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

DROP TRIGGER IF EXISTS trg_countries_updated_at ON countries;
CREATE TRIGGER trg_countries_updated_at
  BEFORE UPDATE ON countries FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_states_updated_at ON states;
CREATE TRIGGER trg_states_updated_at
  BEFORE UPDATE ON states FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ---------------------------------------------------------------------------
-- Row Level Security
-- ---------------------------------------------------------------------------
ALTER TABLE countries ENABLE ROW LEVEL SECURITY;
ALTER TABLE states ENABLE ROW LEVEL SECURITY;
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

DROP POLICY IF EXISTS "Service role full access on countries" ON countries;
DROP POLICY IF EXISTS "Service role full access on states" ON states;

CREATE POLICY "Service role full access on countries"
  ON countries FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on states"
  ON states FOR ALL USING (true) WITH CHECK (true);
