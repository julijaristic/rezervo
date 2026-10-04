"""Repozitorijumski sloj - komunikacija sa bazom."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.base import BaseRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.reservation_repository import ReservationRepository
from app.repositories.user_repository import UserRepository
from app.repositories.venue_repository import VenueRepository

__all__ = [
    "BaseRepository",
    "UserRepository",
    "VenueRepository",
    "ReservationRepository",
    "NotificationRepository",
    "get_user_repository",
    "get_venue_repository",
    "get_reservation_repository",
    "get_notification_repository",
]


def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_venue_repository(db: AsyncSession = Depends(get_db)) -> VenueRepository:
    return VenueRepository(db)


def get_reservation_repository(db: AsyncSession = Depends(get_db)) -> ReservationRepository:
    return ReservationRepository(db)


def get_notification_repository(db: AsyncSession = Depends(get_db)) -> NotificationRepository:
    return NotificationRepository(db)

