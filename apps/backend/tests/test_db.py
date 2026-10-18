import asyncio

from sqlalchemy import text

from db.session import engine


async def main():
    async with engine.connect() as connection:
        result = await connection.execute(text("SELECT 1"))
        print("Database connected:", result.scalar())

    await engine.dispose()


asyncio.run(main())