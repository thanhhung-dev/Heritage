#!/usr/bin/env python3
"""Import approved address candidates vào place_location table.

Usage:
    1. Review corpus/address_candidates.json
    2. Set review_status = "approved" cho entries đúng
    3. Chạy: python scripts/import_address_candidates.py

Script sẽ:
- Đọc candidates.json
- Filter chỉ "approved" entries
- Upsert vào place_location (skip nếu entity không tồn tại)
"""
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import json
import uuid
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.base import engine, AsyncSessionLocal
from backend.models.kg import Entity, PlaceLocation
from backend.core.textutil import strip_accents


async def import_approved_candidates() -> tuple[int, int]:
    """Import approved candidates vào DB.

    Returns:
        (imported_count, skipped_count)
    """
    # Load candidates
    candidates_path = Path('corpus/address_candidates.json')
    candidates = json.loads(candidates_path.read_text())

    # Filter approved
    approved = [c for c in candidates if c.get('review_status') == 'approved']
    if not approved:
        print("No approved candidates found.")
        print("Please review corpus/address_candidates.json and set review_status='approved'")
        return 0, 0

    print(f"Importing {len(approved)} approved candidates...")
    print()

    imported = 0
    skipped = 0

    async with AsyncSessionLocal() as session:
        for cand in approved:
            entity_name = cand['entity_name']

            # Validate required fields
            if not cand.get('province'):
                print(f"✗ {entity_name}: missing province (skipped)")
                skipped += 1
                continue

            # Find entity by normalized name
            normalized = strip_accents(entity_name).lower().strip()
            result = await session.execute(
                select(Entity).where(Entity.normalized_name == normalized, Entity.type == 'place')
            )
            entity = result.scalar_one_or_none()

            if not entity:
                print(f"✗ Entity not found: {entity_name}")
                skipped += 1
                continue

            # Check if verified location already exists
            result = await session.execute(
                select(PlaceLocation).where(
                    PlaceLocation.entity_id == entity.id,
                    PlaceLocation.verification_status == 'verified'
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing
                existing.address = cand['address']
                existing.ward = cand.get('ward')
                existing.district = cand.get('district')
                existing.province = cand.get('province')
                existing.source_url = cand.get('source_url', '')
                existing.source_sentence = cand.get('source_sentence', '')
                existing.verified_at = datetime.now()
                print(f"✓ {entity_name} (updated)")
            else:
                # Insert new
                new_loc = PlaceLocation(
                    id=uuid.uuid4(),
                    entity_id=entity.id,
                    address=cand['address'],
                    ward=cand.get('ward'),
                    district=cand.get('district'),
                    province=cand.get('province'),
                    source_url=cand.get('source_url', ''),
                    source_sentence=cand.get('source_sentence', ''),
                    verification_status='verified',
                    verified_at=datetime.now(),
                )
                session.add(new_loc)
                print(f"✓ {entity_name}")

            print(f"  Address: {cand['address']}")
            imported += 1

        await session.commit()

    return imported, skipped


async def main():
    imported, skipped = await import_approved_candidates()
    print()
    print(f"Imported: {imported}, Skipped: {skipped}")


if __name__ == '__main__':
    asyncio.run(main())
