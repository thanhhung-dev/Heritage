"""Test database connection"""
import asyncio
import sys

# Fix Windows ProactorEventLoop issue
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def test_db():
    from sqlalchemy import text
    from apps.backend.db.base import configure_database
    from apps.backend.core.config import validate_startup_config
    
    settings = validate_startup_config()
    engine = configure_database(settings.database_url)
    
    # Test raw connection
    print("Testing database connection...")
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT version()"))
        version = result.scalar()
        print(f"✅ PostgreSQL version: {version}")
        
        # Test table exists
        result = await conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'admin_account'
            ORDER BY ordinal_position
        """))
        columns = result.fetchall()
        print(f"\n✅ admin_account columns:")
        for col, dtype in columns:
            print(f"   - {col}: {dtype}")
        
        # Count records
        result = await conn.execute(text("SELECT COUNT(*) FROM admin_account"))
        count = result.scalar()
        print(f"\n✅ Total admin accounts: {count}")
    
    await engine.dispose()
    print("\n✅ Database connection test passed!")

if __name__ == "__main__":
    asyncio.run(test_db())
