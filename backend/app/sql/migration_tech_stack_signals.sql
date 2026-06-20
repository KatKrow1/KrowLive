-- KrowLive migration: tech_stack_signals column (Phase 6 enrichment)
-- Run in Supabase SQL Editor if you already applied the base schema + social_links migration

ALTER TABLE companies
  ADD COLUMN IF NOT EXISTS tech_stack_signals JSONB NOT NULL DEFAULT '[]'::jsonb;
