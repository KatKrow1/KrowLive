-- Drop category hierarchy (run after migration_hierarchy.sql if categories were created)
-- Safe to run multiple times.

ALTER TABLE companies DROP COLUMN IF EXISTS category_id;
DROP INDEX IF EXISTS idx_companies_category_id;
DROP INDEX IF EXISTS idx_companies_category;

DROP TRIGGER IF EXISTS trg_categories_updated_at ON categories;
DROP POLICY IF EXISTS "Service role full access on categories" ON categories;
DROP TABLE IF EXISTS categories;
