-- supabase/migrations/001_kb_quality_control.sql
-- 2026-04-15 KB Quality Control
--
-- WARNING: After running this migration, ALL kb_chunks become unapproved.
-- The bot will return no KB results until chunks are approved via the UI.
-- Emergency rollback: UPDATE kb_chunks SET approved = TRUE;

-- 1. Add is_campaign flag to qa_pairs
ALTER TABLE qa_pairs ADD COLUMN IF NOT EXISTS is_campaign BOOLEAN DEFAULT FALSE;

-- 2. Add approved flag to kb_chunks (all existing rows → pending)
ALTER TABLE kb_chunks ADD COLUMN IF NOT EXISTS approved BOOLEAN DEFAULT FALSE;
UPDATE kb_chunks SET approved = FALSE;

-- 3. Update match_kb_chunks RPC to filter approved=true
CREATE OR REPLACE FUNCTION match_kb_chunks(
  query_embedding vector(1536),
  match_brand     text,
  match_count     int
)
RETURNS TABLE (
  id       bigint,
  brand    text,
  category text,
  title    text,
  content  text,
  similarity float
)
LANGUAGE sql STABLE
AS $$
  SELECT
    id, brand, category, title, content,
    1 - (embedding <=> query_embedding) AS similarity
  FROM kb_chunks
  WHERE brand = match_brand
    AND approved = TRUE
  ORDER BY embedding <=> query_embedding
  LIMIT match_count;
$$;
