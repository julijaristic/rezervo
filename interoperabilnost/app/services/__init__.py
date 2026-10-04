"""Servisni sloj - poslovna logika."""
from fastapi import Depends

from app.repositories import (
    get_notification_repository,
    get_reservation_repository,
    get_user_repository,
    get_venue_repository,
)
from app.repositories.user_repository import UserRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.reservation_repository import ReservationRepository
from app.repositories.venue_repository import VenueRepository
from app.services.exceptions import (
    ReservationError,
    ReservationForbiddenError,
    ReservationNotFoundError,
    ReservationValidationError,
    VenueNotFoundError,
)
from app.services.reservation_service import ReservationService
from app.services.venue_service import VenueService

__all__ = [
    "ReservationService",
    "VenueService",
    "ReservationError",
    "VenueNotFoundError",
    "ReservationValidationError",
    "ReservationNotFoundError",
    "ReservationForbiddenError",
    "get_reservation_service",
    "get_venue_service",
]


def get_venue_service(
    venue_repo: VenueRepository = Depends(get_venue_repository),
    reservation_repo: ReservationRepository = Depends(get_reservation_repository),
) -> VenueService:
    return VenueService(venue_repo, reservation_repo)


def get_reservation_service(
    reservation_repo: ReservationRepository = Depends(get_reservation_repository),
    venue_repo: VenueRepository = Depends(get_venue_repository),
    notification_repo: NotificationRepository = Depends(get_notification_repository),
    user_repo: UserRepository = Depends(get_user_repository),
) -> ReservationService:
    return ReservationService(reservation_repo, venue_repo, notification_repo, user_repo)
