"""Service layer for Profile gamification — badges and milestones.

Schema: badge_definition/user_badge, milestone_level_definition/
milestone_task_definition/user_milestone_task (apps.backend.models.user).

award_badge() and complete_milestone_task() are placeholder hooks only:
nothing in the application currently calls them automatically based on user
behavior (e.g. visiting a heritage site, chatting N times). They exist so a
future event system can plug in without redesigning the data model, per the
confirmed design decision to ship real DB-backed CRUD without automated
unlock-by-behavior in this iteration.
"""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.models.user import (
    BadgeDefinition,
    MilestoneLevelDefinition,
    MilestoneTaskDefinition,
    UserBadge,
    UserMilestoneTask,
)


class GamificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_badges(self, account_id: uuid.UUID) -> list[dict]:
        """Return every badge in the catalogue merged with this account's unlock state."""
        definitions = (
            await self.db.execute(
                select(BadgeDefinition).order_by(BadgeDefinition.sort_order)
            )
        ).scalars().all()

        earned_rows = (
            await self.db.execute(
                select(UserBadge).where(UserBadge.account_id == account_id)
            )
        ).scalars().all()
        earned_by_badge_id = {row.badge_id: row for row in earned_rows}

        return [
            {
                "code": d.code,
                "title": d.title,
                "description": d.description,
                "icon_key": d.icon_key,
                "is_unlocked": d.id in earned_by_badge_id,
                "earned_at": earned_by_badge_id[d.id].earned_at if d.id in earned_by_badge_id else None,
            }
            for d in definitions
        ]

    async def list_milestones(self, account_id: uuid.UUID) -> list[dict]:
        """Return every milestone level/task in the catalogue merged with completion state."""
        levels = (
            await self.db.execute(
                select(MilestoneLevelDefinition).order_by(MilestoneLevelDefinition.sort_order)
            )
        ).scalars().all()

        tasks = (
            await self.db.execute(
                select(MilestoneTaskDefinition).order_by(
                    MilestoneTaskDefinition.level_id, MilestoneTaskDefinition.sort_order
                )
            )
        ).scalars().all()

        completed_rows = (
            await self.db.execute(
                select(UserMilestoneTask).where(UserMilestoneTask.account_id == account_id)
            )
        ).scalars().all()
        completed_task_ids = {row.task_id for row in completed_rows}

        tasks_by_level: dict[int, list[MilestoneTaskDefinition]] = {}
        for task in tasks:
            tasks_by_level.setdefault(task.level_id, []).append(task)

        result: list[dict] = []
        for level in levels:
            level_tasks = tasks_by_level.get(level.id, [])
            is_unlocked = any(t.id in completed_task_ids for t in level_tasks) or level.sort_order == 0
            result.append(
                {
                    "code": level.code,
                    "level_name": level.level_name,
                    "description": level.description,
                    "is_unlocked": is_unlocked,
                    "tasks": [
                        {
                            "code": t.code,
                            "title": t.title,
                            "is_completed": t.id in completed_task_ids,
                        }
                        for t in level_tasks
                    ],
                }
            )
        return result

    async def award_badge(self, account_id: uuid.UUID, badge_code: str) -> UserBadge | None:
        """Placeholder hook: grant a badge to an account.

        Not wired to any real event yet. A future feature (e.g. "visited 5
        heritage sites") would call this once that behavior is tracked.
        """
        definition = (
            await self.db.execute(select(BadgeDefinition).where(BadgeDefinition.code == badge_code))
        ).scalar_one_or_none()
        if definition is None:
            return None

        already_earned = (
            await self.db.execute(
                select(UserBadge).where(
                    UserBadge.account_id == account_id, UserBadge.badge_id == definition.id
                )
            )
        ).scalar_one_or_none()
        if already_earned is not None:
            return already_earned

        badge = UserBadge(account_id=account_id, badge_id=definition.id, earned_at=date.today())
        self.db.add(badge)
        await self.db.commit()
        await self.db.refresh(badge)
        return badge

    async def complete_milestone_task(self, account_id: uuid.UUID, task_code: str) -> UserMilestoneTask | None:
        """Placeholder hook: mark a milestone task complete for an account.

        Not wired to any real event yet — see module docstring.
        """
        task = (
            await self.db.execute(
                select(MilestoneTaskDefinition).where(MilestoneTaskDefinition.code == task_code)
            )
        ).scalar_one_or_none()
        if task is None:
            return None

        already_completed = (
            await self.db.execute(
                select(UserMilestoneTask).where(
                    UserMilestoneTask.account_id == account_id, UserMilestoneTask.task_id == task.id
                )
            )
        ).scalar_one_or_none()
        if already_completed is not None:
            return already_completed

        completion = UserMilestoneTask(account_id=account_id, task_id=task.id)
        self.db.add(completion)
        await self.db.commit()
        await self.db.refresh(completion)
        return completion


