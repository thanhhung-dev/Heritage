"""Check email constraints and data"""
import asyncio
import sys

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def check_constraints():
    from sqlalchemy import text
    from apps.backend.db.base import configure_database
    from apps.backend.core.config import validate_startup_config
    
    settings = validate_startup_config()
    engine = configure_database(settings.database_url)
    
    async with engine.begin() as conn:
        # Check constraints on admin_account
        print("Checking constraints on admin_account...")
        result = await conn.execute(text("""
            SELECT conname, pg_get_constraintdef(oid) as definition
            FROM pg_constraint
            WHERE conrelid = 'admin_account'::regclass
            ORDER BY conname
        """))
        constraints = result.fetchall()
        print("\nConstraints:")
        for name, definition in constraints:
            print(f"  {name}: {definition}")
        
        # Check indexes
        print("\n\nChecking indexes...")
        result = await conn.execute(text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'admin_account'
            ORDER BY indexname
        """))
        indexes = result.fetchall()
        print("\nIndexes:")
        for name, definition in indexes:
            print(f"  {name}: {definition}")
        
        # Check current data
        print("\n\nChecking current admin_account data...")
        result = await conn.execute(text("""
            SELECT id, username, email, is_active, created_at
            FROM admin_account
            ORDER BY created_at DESC
        """))
        rows = result.fetchall()
        print(f"\nFound {len(rows)} accounts:")
        for row in rows:
            print(f"  - {row.username} | {row.email} | active={row.is_active}")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_constraints())
