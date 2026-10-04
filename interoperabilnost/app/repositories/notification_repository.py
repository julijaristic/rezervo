"""Repozitorijum za Notification."""
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification_model import Notification
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Notification)

    async def get_by_user_id(self, user_id: int, unread_only: bool = False) -> List[Notification]:
        q = select(Notification).where(Notification.user_id == user_id).order_by(Notification.id.desc())
        if unread_only:
            q = q.where(Notification.read.is_(False))
        result = await self._session.execute(q)
        return list(result.scalars().all())

    async def get_for_user(self, notification_id: int, user_id: int) -> Optional[Notification]:
        result = await self._session.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()
