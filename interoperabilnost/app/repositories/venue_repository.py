"""Repozitorijum za Venue."""
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.venue_model import Venue
from app.repositories.base import BaseRepository


class VenueRepository(BaseRepository[Venue]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Venue)

    async def get_all(self) -> List[Venue]:
        result = await self._session.execute(
            select(Venue)
            .where(Venue.is_active.is_(True), Venue.is_deleted.is_(False))
            .order_by(Venue.id)
        )
        return list(result.scalars().all())
