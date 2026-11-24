-- Two world GLBs per heritage. Columns may already exist on databases
-- that were altered by hand; IF NOT EXISTS keeps this safe to apply later.
ALTER TABLE heritage
    ADD COLUMN IF NOT EXISTS exterior_model_url TEXT,
    ADD COLUMN IF NOT EXISTS interior_model_url TEXT;

ALTER TABLE scene
    ADD COLUMN IF NOT EXISTS use_interior_model BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN heritage.exterior_model_url IS
    'Default world GLB (exterior). Missing assets remain NULL.';
COMMENT ON COLUMN heritage.interior_model_url IS
    'Interior world GLB. Used only by scenes with use_interior_model.';
COMMENT ON COLUMN scene.use_interior_model IS
    'Select heritage.interior_model_url when true. No fallback if that URL is NULL.';
