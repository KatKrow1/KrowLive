-- Add per-executive scrape confidence (high / medium / low)
ALTER TABLE executives
  ADD COLUMN IF NOT EXISTS extraction_confidence TEXT NOT NULL DEFAULT 'low'
    CHECK (extraction_confidence IN ('high', 'medium', 'low'));
