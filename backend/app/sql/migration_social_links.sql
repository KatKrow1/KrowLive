-- KrowLive migration: add social_links to companies (Phase 6b)
-- Run in Supabase SQL Editor if you already applied the base schema.sql

ALTER TABLE companies
  ADD COLUMN IF NOT EXISTS social_links JSONB NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_companies_social_links ON companies USING gin (social_links);
