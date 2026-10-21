-- Migration: Add email column to admin_account table
-- Date: 2026-10-19
-- Purpose: Separate email from username for proper authentication

-- Add email column
ALTER TABLE admin_account 
ADD COLUMN IF NOT EXISTS email TEXT;

-- For existing records, copy username to email if email is null
UPDATE admin_account 
SET email = username 
WHERE email IS NULL;

-- Make email NOT NULL and UNIQUE after populating
ALTER TABLE admin_account 
ALTER COLUMN email SET NOT NULL;

ALTER TABLE admin_account 
ADD CONSTRAINT admin_account_email_unique UNIQUE (email);

-- Add comment
COMMENT ON COLUMN admin_account.email IS 'Email address for authentication';

-- Verify migration
DO $$
BEGIN
    RAISE NOTICE 'Migration completed successfully';
    RAISE NOTICE 'admin_account now has email column';
END $$;
