import asyncio

from sqlalchemy import select

from apps.backend.db.base import AsyncSessionLocal
from apps.backend.models.heritage import Heritage


async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Heritage)
            .where(Heritage.slug == "chua-thien-mu")
        )

        heritage = result.scalar_one_or_none()

        if heritage is None:
            print("Không tìm thấy heritage: chua-thien-mu")
            return

        print("\n=== HERITAGE ===")
        print("ID:", heritage.id)
        print("Slug:", heritage.slug)
        print("Title:", heritage.title)

        print("\n=== LANGUAGE ===")
        print("Language 1:", heritage.language1)
        print("Language 2:", heritage.language2)

        print("\n=== SCENES ===")

        for scene in heritage.scenes:
            print(f"\nScene {scene.sequence}: {scene.title}")

            print("  Sky:", scene.sky_preset)

            print("  Models:")
            for model in scene.model_assets:
                print("   -", model.file_url)

            print("  Voices:")
            for clip in scene.voice_clips:
                print("   -", clip.voice)

            print("  Media:")
            for media in scene.media_items:
                print("   -", media.asset_url)

            print("  Interactives:")
            for interactive in scene.interactives:
                print("   -", interactive.mode)

            print("  Scene Highlights:")
            for highlight in scene.scene_highlights:
                print("   -", highlight.model_url)


if __name__ == "__main__":
    asyncio.run(main())