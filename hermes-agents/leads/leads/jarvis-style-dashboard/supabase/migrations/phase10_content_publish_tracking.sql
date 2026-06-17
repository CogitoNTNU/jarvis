-- Phase 10: Content publish tracking fields
-- Adds publish lifecycle telemetry to content_vault.

ALTER TABLE content_vault
  ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS publish_status TEXT,
  ADD COLUMN IF NOT EXISTS publish_channel TEXT,
  ADD COLUMN IF NOT EXISTS external_post_id TEXT,
  ADD COLUMN IF NOT EXISTS publish_error TEXT;

CREATE INDEX IF NOT EXISTS content_vault_status_updated_idx
  ON content_vault (status, updated_at DESC);

CREATE INDEX IF NOT EXISTS content_vault_publish_status_idx
  ON content_vault (publish_status, updated_at DESC);
