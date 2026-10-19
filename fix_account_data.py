"""
Fix existing admin accounts - populate proper email values
"""
import asyncio
import sys

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def fix_accounts():
    from sqlalchemy import text
    from apps.backend.db.base import configure_database
    from apps.backend.core.config import validate_startup_config
    
    settings = validate_startup_config()
    engine = configure_database(settings.database_url)
    
    async with engine.begin() as conn:
        # Get current accounts
        result = await conn.execute(text("""
            SELECT id, username, email
            FROM admin_account
        """))
        accounts = result.fetchall()
        
        print(f"Found {len(accounts)} accounts to check:")
        for acc in accounts:
            print(f"  - id={acc.id}")
            print(f"    username={acc.username}")
            print(f"    email={acc.email}")
        
        # Fix accounts where email == username but username doesn't look like email
        for acc in accounts:
            if acc.email == acc.username and "@" not in acc.username:
                # Generate email from username
                new_email = f"{acc.username}@example.com"
                
                print(f"\n  Updating {acc.username}:")
                print(f"    Old email: {acc.email}")
                print(f"    New email: {new_email}")
                
                await conn.execute(
                    text("UPDATE admin_account SET email = :email WHERE id = :id"),
                    {"email": new_email, "id": acc.id}
                )
        
        # Verify updates
        result = await conn.execute(text("""
            SELECT username, email
            FROM admin_account
            ORDER BY created_at DESC
        """))
        accounts = result.fetchall()
        
        print("\n\nFinal state:")
        for acc in accounts:
            print(f"  {acc.username} -> {acc.email}")
    
    await engine.dispose()
    print("\n✅ Done!")

if __name__ == "__main__":
    asyncio.run(fix_accounts())
