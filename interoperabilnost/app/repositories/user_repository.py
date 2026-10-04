"""Repozitorijum za User."""
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_model import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_username(self, username: str) -> Optional[User]:
        result = await self._session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def exists_by_username(self, username: str) -> bool:
        user = await self.get_by_username(username)
        return user is not None

    async def get_all(self) -> List[User]:
        result = await self._session.execute(select(User).order_by(User.id))
        return list(result.scalars().all())
