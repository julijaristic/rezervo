"""Repozitorijum za Reservation."""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reservation_model import Reservation
from app.repositories.base import BaseRepository

class ReservationRepository(BaseRepository[Reservation]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Reservation)

    async def get_by_user_id(self, user_id: int) -> List[Reservation]:
        result = await self._session.execute(
            select(Reservation)
            .where(Reservation.user_id == user_id)
            .order_by(Reservation.date.desc(), Reservation.start_time.desc())
        )
        return list(result.scalars().all())

    async def get_used_table_numbers(
        self,
        venue_id: int,
        start_dt: datetime,
        end_dt: datetime,
        exclude_reservation_id: Optional[int] = None,
    ) -> List[int]:
        q = select(Reservation.table_number).where(
            Reservation.venue_id == venue_id,
            Reservation.status == "confirmed",
            Reservation.table_number.isnot(None),
            Reservation.start_time < end_dt,
            Reservation.end_time > start_dt,
        )
        if exclude_reservation_id is not None:
            q = q.where(Reservation.id != exclude_reservation_id)
        result = await self._session.execute(q)
        return [n for n in result.scalars().all() if n is not None]
