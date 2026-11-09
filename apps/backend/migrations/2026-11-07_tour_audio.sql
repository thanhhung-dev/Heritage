-- Add authored tour ambience, transition SFX, and interactive highlight audio.
-- Apply manually to an existing database after approval (schema.sql is for new DBs).
-- Idempotent: safe to apply repeatedly. No asset backfill or data updates.

ALTER TABLE heritage
    ADD COLUMN IF NOT EXISTS ambient_audio_url TEXT,
    ADD COLUMN IF NOT EXISTS ambient_audio_alt_url TEXT,
    ADD COLUMN IF NOT EXISTS transition_sfx_url TEXT;

ALTER TABLE scene
    ADD COLUMN IF NOT EXISTS use_ambient_audio_alt BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE interactive_highlight
    ADD COLUMN IF NOT EXISTS audio_url TEXT;

COMMENT ON COLUMN heritage.ambient_audio_url IS
    'Main authored ambience URL (exterior). Missing assets remain NULL.';
COMMENT ON COLUMN heritage.ambient_audio_alt_url IS
    'Alternate authored ambience URL (interior). Missing assets remain NULL.';
COMMENT ON COLUMN heritage.transition_sfx_url IS
    'Authored scene transition sound effect URL. Missing assets remain NULL.';
COMMENT ON COLUMN scene.use_ambient_audio_alt IS
    'Select alternate heritage ambience when true, main when false. No fallback if the selected URL is NULL.';
COMMENT ON COLUMN interactive_highlight.audio_url IS
    'Authored interactive highlight audio URL. Missing assets remain NULL.';
