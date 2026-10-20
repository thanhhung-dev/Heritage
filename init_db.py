"""Database initialization script for Heritage application.

Creates all authentication tables (role, account, user_profile, user_consent)
and seeds default roles (USER, ADMIN).

IMPORTANT: This script drops existing tables to ensure clean state with proper sequences.

Usage:
    python init_db.py
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()

# Import Base and all models to register them with metadata
from apps.backend.db.base import Base
from apps.backend.models.user import Role, Account, UserProfile, UserConsent

# Get database URL from environment
db_url = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/heritagegraph")

# Convert async psycopg driver to sync psycopg2 for create_all
if "postgresql+psycopg://" in db_url:
    db_url = db_url.replace("postgresql+psycopg://", "postgresql://")
    print(f"📌 Converted async URL to sync format")

print(f"🔌 Connecting to database...")
print(f"   URL: {db_url.split('@')[1] if '@' in db_url else 'localhost'}")  # Hide credentials

# Create synchronous engine for schema creation
engine = create_engine(db_url, echo=True)

try:
    print("\n🗑️  Dropping existing authentication tables (if any)...")
    with engine.connect() as conn:
        # Drop tables in reverse dependency order with CASCADE
        # This ensures all foreign key constraints are handled
        conn.execute(text("DROP TABLE IF EXISTS user_consent CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS user_profile CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS account CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS role CASCADE"))
        conn.commit()
        print("   ✓ Old tables dropped successfully")
    
    # Create all tables from Base metadata with proper sequences
    print("\n📦 Creating database tables with auto-increment sequences...")
    Base.metadata.create_all(engine)
    print("   ✓ Tables created with proper sequences")
    
    # Seed default roles
    print("\n🌱 Seeding default roles...")
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "INSERT INTO role (id, name) VALUES (1, 'USER'), (2, 'ADMIN')"
            )
        )
        conn.commit()
        print(f"   ✓ Inserted {result.rowcount} roles (USER, ADMIN)")
    
    # Verify sequences exist
    print("\n🔍 Verifying auto-increment sequences...")
    with engine.connect() as conn:
        sequences = conn.execute(
            text(
                "SELECT sequence_name FROM information_schema.sequences "
                "WHERE sequence_name LIKE '%_id_seq'"
            )
        ).fetchall()
        print(f"   ✓ Found {len(sequences)} sequences:")
        for seq in sequences:
            print(f"      - {seq[0]}")
    
    print("\n✅ DATABASE TABLES CREATED AND SEEDED SUCCESSFULLY!")
    print("\n📋 Created tables:")
    print("   - role (id, name)")
    print("   - account (id, email, username, password_hash, is_active, role_id, locked_until, created_at, updated_at)")
    print("   - user_profile (id, account_id, display_name, avatar_url, bio, created_at, updated_at)")
    print("   - user_consent (id, account_id, analytics_opt_in, created_at, updated_at)")
    print("\n🎯 Ready to test authentication endpoints!")
    print("\n💡 Next steps:")
    print("   1. Start server: uvicorn apps.backend.app:app --reload --host 0.0.0.0 --port 8000")
    print("   2. Test at: http://localhost:8000/docs")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print("\n💡 Troubleshooting:")
    print("   1. Ensure PostgreSQL is running: docker-compose up -d postgres")
    print("   2. Verify DATABASE_URL in .env matches your setup")
    print("   3. Check database exists: psql -U postgres -c '\\l' -h 127.0.0.1")
    print("   4. Check connection: psql -U postgres -h 127.0.0.1 -d heritagegraph")
    raise
finally:
    engine.dispose()
