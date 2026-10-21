"""
Database migration script: Add email column to admin_account
Run this script to update the database schema
"""
import asyncio
import os
import sys

# Fix Windows ProactorEventLoop issue with psycopg
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy import text
from apps.backend.db.base import AsyncSessionLocal, configure_database

async def run_migration():
    """Run the migration to add email column."""
    
    # Configure database first
    database_url = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/heritagegraph")
    print(f"Connecting to database: {database_url.split('@')[1] if '@' in database_url else database_url}")
    configure_database(database_url)
    
    async with AsyncSessionLocal() as session:
        try:
            print("\nStarting migration: Add email column to admin_account")
            print("=" * 60)
            
            # Check if email column already exists
            result = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'admin_account' AND column_name = 'email'
            """))
            existing = result.fetchone()
            
            if existing:
                print("⚠️  Email column already exists, skipping migration")
                return
            
            # Add email column
            await session.execute(text("""
                ALTER TABLE admin_account 
                ADD COLUMN email TEXT
            """))
            print("✓ Added email column")
            
            # Copy username to email for existing records
            await session.execute(text("""
                UPDATE admin_account 
                SET email = username 
                WHERE email IS NULL
            """))
            print("✓ Populated email from username for existing records")
            
            # Make email NOT NULL
            await session.execute(text("""
                ALTER TABLE admin_account 
                ALTER COLUMN email SET NOT NULL
            """))
            print("✓ Set email as NOT NULL")
            
            # Add unique constraint
            await session.execute(text("""
                ALTER TABLE admin_account 
                ADD CONSTRAINT admin_account_email_unique UNIQUE (email)
            """))
            print("✓ Added UNIQUE constraint on email")
            
            # Commit changes
            await session.commit()
            
            print("=" * 60)
            print("✅ Migration completed successfully!")
            print("   admin_account now has email column (NOT NULL, UNIQUE)")
            
        except Exception as e:
            await session.rollback()
            print(f"\n❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            raise

if __name__ == "__main__":
    asyncio.run(run_migration())

