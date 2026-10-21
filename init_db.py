"""Database initialization script for Heritage application.

Creates the Profile & Gamification tables (user_profile, user_consent,
badge_definition, user_badge, milestone_level_definition,
milestone_task_definition, user_milestone_task) and seeds the badge/milestone
catalogues to match the FE's static presentation data (profileData.tsx).

IMPORTANT: This script drops and recreates the Profile/Gamification tables
only. It does NOT drop `admin_account` (real user accounts) or any other
feature's tables — `user_profile`/`user_consent`/gamification tables are
foreign-keyed to `admin_account.id`, so that table must already exist.

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
from apps.backend.models.admin import AdminAccount  # noqa: F401 (FK target, must exist)
from apps.backend.models.user import (
    BadgeDefinition,
    MilestoneLevelDefinition,
    MilestoneTaskDefinition,
    UserBadge,
    UserConsent,
    UserMilestoneTask,
    UserProfile,
)

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

PROFILE_TABLES = [
    "user_milestone_task",
    "milestone_task_definition",
    "milestone_level_definition",
    "user_badge",
    "badge_definition",
    "user_consent",
    "user_profile",
]


try:
    print("\n🗑️  Dropping existing Profile/Gamification tables (if any)...")
    with engine.connect() as conn:
        # Drop in dependency order with CASCADE. admin_account is NOT dropped —
        # it's owned by the auth feature and other data depends on it.
        for table in PROFILE_TABLES:
            conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
        conn.commit()
        print("   ✓ Old Profile/Gamification tables dropped successfully")

    # Create only the Profile/Gamification tables from Base metadata.
    # admin_account must already exist (created by the auth feature / its own
    # init); we only ensure it via create_all(tables=...) would also recreate
    # it if missing, which is safe since create_all is idempotent (CREATE
    # TABLE IF NOT EXISTS semantics via checkfirst=True, the default).
    print("\n📦 Creating Profile/Gamification tables...")
    tables_to_create = [
        Base.metadata.tables[name]
        for name in [
            "admin_account",
            "user_profile",
            "user_consent",
            "badge_definition",
            "user_badge",
            "milestone_level_definition",
            "milestone_task_definition",
            "user_milestone_task",
        ]
    ]
    Base.metadata.create_all(engine, tables=tables_to_create, checkfirst=True)
    print("   ✓ Tables created")

    # Seed badge catalogue (must match apps/frontend/features/profile/profileData.tsx PROFILE_BADGES)
    print("\n🌱 Seeding badge catalogue...")
    badges = [
        ("first-explorer", "First Explorer", "Explore a site for the first time and start your journey.", "BankOutlined", 0),
        ("culture-explorer", "Culture Explorer", "See the world through a questioned cultural lens.", "CompassOutlined", 1),
        ("storyteller", "Storyteller", "Read 3 short stories about heritage.", "BookOutlined", 2),
        ("collector", "Collector", "Collect 5 images about a landmark.", "BarsOutlined", 3),
        ("wayfinder", "Wayfinder", "Find 5 waypoints on the heritage map.", "EnvironmentOutlined", 4),
        ("tour-guide", "Tour Guide", "Share 5 tours of destinations.", "GlobalOutlined", 5),
        ("deep-diver", "Deep Diver", "Explore 3 sites with the same theme.", "SearchOutlined", 6),
        ("steady-explorer", "Steady Explorer", "Explore for 7 days in a row.", "CalendarOutlined", 7),
        ("culture-scholar", "Culture Scholar", "Read 5 articles about common heritage topics.", "BookOutlined", 8),
        ("detail-detective", "Detail Detective", "Find 10 hidden details in artifacts.", "SearchOutlined", 9),
        ("fast-explorer", "Fast Explorer", "Explore 5 sites in 1 week.", "EnvironmentOutlined", 10),
        ("conversationalist", "Conversationalist", "Ask the chatbot 15 questions and learn more.", "RobotOutlined", 11),
        ("quick-explorer", "Quick Explorer", "Explore 3 sites in 1 day.", "SendOutlined", 12),
    ]
    with engine.connect() as conn:
        for code, title, description, icon_key, sort_order in badges:
            conn.execute(
                text(
                    "INSERT INTO badge_definition (code, title, description, icon_key, sort_order) "
                    "VALUES (:code, :title, :description, :icon_key, :sort_order)"
                ),
                {"code": code, "title": title, "description": description, "icon_key": icon_key, "sort_order": sort_order},
            )
        conn.commit()
        print(f"   ✓ Inserted {len(badges)} badge definitions")

    # Seed milestone catalogue (must match apps/frontend/features/profile/profileData.tsx EXPLORATION_LEVELS)
    print("\n🌱 Seeding milestone catalogue...")
    levels = [
        (
            "explorer", "Explorer", "Begin your cultural heritage journey.", 0,
            [
                ("e1", "Create your profile", 0),
                ("e2", "Explore your first heritage site", 1),
                ("e3", "Ask the chatbot a question", 2),
            ],
        ),
        (
            "heritage-seeker", "Heritage Seeker", "Discover your first sites and learn the stories behind them.", 1,
            [
                ("t1", "Explore your first heritage site", 0),
                ("t2", "Discover 5 heritage sites", 1),
                ("t3", "Read a site's history", 2),
                ("t4", "Explore a heritage map", 3),
                ("t5", "Ask the chatbot about a site", 4),
                ("t6", "Learn about a local custom", 5),
                ("t7", "Discover a traditional festival", 6),
                ("t8", "Read 3 cultural stories", 7),
                ("t9", "Share a heritage story", 8),
            ],
        ),
        (
            "culture-scholar", "Culture Scholar", "Deepen your knowledge of history, architecture, and living traditions.", 2,
            [
                ("c1", "Read 5 articles about heritage topics", 0),
                ("c2", "Complete a guided cultural tour", 1),
                ("c3", "Find 10 hidden details in artifacts", 2),
            ],
        ),
        (
            "journey-pathfinder", "Journey Pathfinder", "Connect heritage sites through meaningful cultural journeys.", 3,
            [
                ("j1", "Create your first custom journey", 0),
                ("j2", "Share 5 tours of destinations", 1),
                ("j3", "Invite a friend to a journey", 2),
            ],
        ),
        (
            "heritage-ambassador", "Heritage Ambassador",
            "Explore for 7 days in a row and share the cultural stories you discover.", 4,
            [
                ("a1", "Explore for 7 days in a row", 0),
                ("a2", "Publish a cultural story", 1),
                ("a3", "Reach 100 total exploration hours", 2),
            ],
        ),
    ]
    with engine.connect() as conn:
        level_count = 0
        task_count = 0
        for code, level_name, description, sort_order, tasks in levels:
            level_id = conn.execute(
                text(
                    "INSERT INTO milestone_level_definition (code, level_name, description, sort_order) "
                    "VALUES (:code, :level_name, :description, :sort_order) RETURNING id"
                ),
                {"code": code, "level_name": level_name, "description": description, "sort_order": sort_order},
            ).scalar_one()
            level_count += 1
            for task_code, title, task_sort_order in tasks:
                conn.execute(
                    text(
                        "INSERT INTO milestone_task_definition (level_id, code, title, sort_order) "
                        "VALUES (:level_id, :code, :title, :sort_order)"
                    ),
                    {"level_id": level_id, "code": task_code, "title": title, "sort_order": task_sort_order},
                )
                task_count += 1
        conn.commit()
        print(f"   ✓ Inserted {level_count} milestone levels with {task_count} tasks")


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
    print("\n📋 Created/ensured tables:")
    print("   - admin_account (ensured only, owned by auth feature)")
    print("   - user_profile (id, account_id[UUID], display_name, handle, avatar_url, banner_url, bio,")
    print("                   country, city, display_email, socials, featured_badges,")
    print("                   show_activity_on_profile, total_hours, level, created_at, updated_at)")
    print("   - user_consent (id, account_id[UUID], analytics_opt_in, created_at, updated_at)")
    print("   - badge_definition (id, code, title, description, icon_key, sort_order)")
    print("   - user_badge (id, account_id[UUID], badge_id, earned_at, created_at)")
    print("   - milestone_level_definition (id, code, level_name, description, sort_order)")
    print("   - milestone_task_definition (id, level_id, code, title, sort_order)")
    print("   - user_milestone_task (id, account_id[UUID], task_id, completed_at)")
    print("\n🎯 Ready to test Profile & Gamification endpoints!")
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
    print("   5. Ensure admin_account table exists (run the auth feature's own init first)")
    raise
finally:
    engine.dispose()

