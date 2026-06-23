-- Normalized hierarchy: countries → states → companies
-- Run in Supabase SQL Editor. Safe to re-run (idempotent where noted).

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

ALTER TABLE companies ADD COLUMN IF NOT EXISTS country_id INTEGER REFERENCES countries (id);
ALTER TABLE companies ADD COLUMN IF NOT EXISTS state_id INTEGER REFERENCES states (id);
CREATE INDEX IF NOT EXISTS idx_companies_country_id ON companies (country_id);
CREATE INDEX IF NOT EXISTS idx_companies_state_id ON companies (state_id);

INSERT INTO countries (code, name)
VALUES ('CA', 'Canada'), ('AU', 'Australia')
ON CONFLICT (code) DO NOTHING;

DO $$
DECLARE
  rec RECORD;
  cid INTEGER;
  sid INTEGER;
  state_name TEXT;
  state_slug TEXT;
  country_code TEXT;
BEGIN
  FOR rec IN SELECT * FROM companies WHERE country_id IS NULL OR state_id IS NULL LOOP
    country_code := rec.country::TEXT;

    SELECT id INTO cid FROM countries WHERE code = country_code;
    IF cid IS NULL THEN
      INSERT INTO countries (code, name)
      VALUES (country_code, CASE country_code WHEN 'CA' THEN 'Canada' WHEN 'AU' THEN 'Australia' ELSE country_code END)
      RETURNING id INTO cid;
    END IF;

    state_name := COALESCE(NULLIF(TRIM(rec.state), ''), 'Unknown');
    state_slug := lower(regexp_replace(regexp_replace(state_name, '[^a-zA-Z0-9]+', '-', 'g'), '(^-|-$)', '', 'g'));

    SELECT id INTO sid FROM states WHERE country_id = cid AND slug = state_slug;
    IF sid IS NULL THEN
      INSERT INTO states (country_id, name, slug)
      VALUES (cid, state_name, state_slug)
      RETURNING id INTO sid;
    END IF;

    UPDATE companies
    SET country_id = cid, state_id = sid
    WHERE id = rec.id;
  END LOOP;
END $$;

DROP TRIGGER IF EXISTS trg_countries_updated_at ON countries;
CREATE TRIGGER trg_countries_updated_at
  BEFORE UPDATE ON countries FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_states_updated_at ON states;
CREATE TRIGGER trg_states_updated_at
  BEFORE UPDATE ON states FOR EACH ROW EXECUTE FUNCTION set_updated_at();

ALTER TABLE countries ENABLE ROW LEVEL SECURITY;
ALTER TABLE states ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role full access on countries" ON countries;
DROP POLICY IF EXISTS "Service role full access on states" ON states;

CREATE POLICY "Service role full access on countries" ON countries FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access on states" ON states FOR ALL USING (true) WITH CHECK (true);
