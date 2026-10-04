"""Servis za lokale (venues) - poslovna logika."""
from typing import List

from app.models.venue_model import Venue
from app.repositories.reservation_repository import ReservationRepository
from app.repositories.venue_repository import VenueRepository
from app.schemas.venue import VenueCreate
from app.services.exceptions import VenueNotFoundError


class VenueService:
    def __init__(self, venue_repo: VenueRepository, reservation_repo: ReservationRepository):
        self._venue_repo = venue_repo
        self._reservation_repo = reservation_repo

    async def create_venue(self, payload: VenueCreate, owner_id: int) -> Venue:
        venue = Venue(
            name=payload.name,
            address=payload.address,
            city=payload.city,
            country=payload.country,
            phone=payload.phone,
            email=str(payload.email),
            owner_id=owner_id,
            weekday_open=payload.weekday_open,
            weekday_close=payload.weekday_close,
            weekend_open=payload.weekend_open,
            weekend_close=payload.weekend_close,
            table_count=payload.table_count,
        )
        await self._venue_repo.add(venue)
        return venue

    async def list_all(self) -> List[Venue]:
        return await self._venue_repo.get_all()

    async def get_by_id(self, venue_id: int) -> Venue:
        venue = await self._venue_repo.get_by_id(venue_id)
        if venue is None:
            raise VenueNotFoundError("Lokal nije pronađen")
        return venue
