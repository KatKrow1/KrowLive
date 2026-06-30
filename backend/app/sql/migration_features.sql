-- KrowLive feature migration: provenance, lead status, saved searches, webhooks
-- Paste this entire script into Supabase SQL Editor and run once.

-- ---------------------------------------------------------------------------
-- companies: scrape provenance
-- ---------------------------------------------------------------------------
ALTER TABLE companies
  ADD COLUMN IF NOT EXISTS last_scraped_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS source_url TEXT;

CREATE INDEX IF NOT EXISTS idx_companies_last_scraped_at ON companies (last_scraped_at DESC);

-- ---------------------------------------------------------------------------
-- executives: CASL / Spam Act provenance
-- ---------------------------------------------------------------------------
ALTER TABLE executives
  ADD COLUMN IF NOT EXISTS source_url TEXT,
  ADD COLUMN IF NOT EXISTS scraped_at TIMESTAMPTZ;

-- ---------------------------------------------------------------------------
-- lead_status (CRM pipeline stage per company)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS lead_status (
  company_id UUID PRIMARY KEY REFERENCES companies (id) ON DELETE CASCADE,
  status TEXT NOT NULL DEFAULT 'new'
    CHECK (status IN ('new', 'contacted', 'replied', 'not_interested')),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lead_status_status ON lead_status (status);

-- Backfill existing companies as 'new'
INSERT INTO lead_status (company_id, status)
SELECT c.id, 'new'
FROM companies c
WHERE NOT EXISTS (
  SELECT 1 FROM lead_status ls WHERE ls.company_id = c.id
);

DROP TRIGGER IF EXISTS trg_lead_status_updated_at ON lead_status;
CREATE TRIGGER trg_lead_status_updated_at
  BEFORE UPDATE ON lead_status
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

ALTER TABLE lead_status ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role full access on lead_status" ON lead_status;
CREATE POLICY "Service role full access on lead_status"
  ON lead_status FOR ALL USING (true) WITH CHECK (true);

-- ---------------------------------------------------------------------------
-- saved_searches
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS saved_searches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  industry TEXT NOT NULL,
  country TEXT NOT NULL,
  states JSONB NOT NULL DEFAULT '[]'::jsonb,
  cities JSONB NOT NULL DEFAULT '[]'::jsonb,
  max_results INTEGER NOT NULL DEFAULT 5 CHECK (max_results >= 1 AND max_results <= 20),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_run_at TIMESTAMPTZ,
  last_result_count INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_saved_searches_created_at ON saved_searches (created_at DESC);

ALTER TABLE saved_searches ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role full access on saved_searches" ON saved_searches;
CREATE POLICY "Service role full access on saved_searches"
  ON saved_searches FOR ALL USING (true) WITH CHECK (true);

-- ---------------------------------------------------------------------------
-- webhooks (outbound integration targets)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS webhooks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  url TEXT NOT NULL,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_webhooks_active ON webhooks (active) WHERE active = TRUE;

ALTER TABLE webhooks ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role full access on webhooks" ON webhooks;
CREATE POLICY "Service role full access on webhooks"
  ON webhooks FOR ALL USING (true) WITH CHECK (true);
