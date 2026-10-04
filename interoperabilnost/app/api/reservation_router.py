"""API za rezervacije - gost."""
from fastapi import APIRouter, BackgroundTasks, Depends, status

from app.messaging import (
    publish_reservation_cancelled_payload,
    publish_reservation_created_payload,
    publish_reservation_updated_payload,
    reservation_cancelled_payload,
    reservation_created_payload,
    reservation_updated_payload,
)
from app.api.auth_router import get_current_user
from app.models.user_model import User
from app.api.errors import reservation_error_to_http
from app.repositories import get_user_repository, get_venue_repository
from app.repositories.user_repository import UserRepository
from app.repositories.venue_repository import VenueRepository
from app.schemas.reservation import ReservationCreate, ReservationRead, ReservationUpdate
from app.services import (
    get_reservation_service,
    ReservationService,
    ReservationForbiddenError,
    ReservationNotFoundError,
    ReservationValidationError,
    VenueNotFoundError,
)

router = APIRouter(prefix="/reservations", tags=["reservations"])


async def _enrich_reservation_read(
    reservation,
    venue_repo: VenueRepository,
    user_repo: UserRepository,
) -> ReservationRead:
    venue = await venue_repo.get_by_id(reservation.venue_id) if reservation else None
    guest = await user_repo.get_by_id(reservation.user_id) if reservation else None
    data = ReservationRead.model_validate(reservation).model_dump()
    data["venue_name"] = venue.name if venue else None
    data["venue_address"] = venue.address if venue else None
    data["venue_phone"] = venue.phone if venue else None
    data["guest_name"] = guest.name if guest else None
    data["guest_phone"] = guest.phone if guest else None
    return ReservationRead(**data)


@router.post("/", response_model=ReservationRead, status_code=status.HTTP_201_CREATED)
async def make_reservation(
    payload: ReservationCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    service: ReservationService = Depends(get_reservation_service),
    venue_repo: VenueRepository = Depends(get_venue_repository),
    user_repo: UserRepository = Depends(get_user_repository),
):
    try:
        reservation = await service.create_reservation(current_user.id, payload)
        background_tasks.add_task(
            publish_reservation_created_payload,
            reservation_created_payload(reservation, current_user),
        )
        return await _enrich_reservation_read(reservation, venue_repo, user_repo)
    except (VenueNotFoundError, ReservationValidationError) as e:
        raise reservation_error_to_http(e)


@router.get("/", response_model=list[ReservationRead])
async def list_reservations(
    current_user: User = Depends(get_current_user),
    service: ReservationService = Depends(get_reservation_service),
    venue_repo: VenueRepository = Depends(get_venue_repository),
    user_repo: UserRepository = Depends(get_user_repository),
):
    reservations = await service.list_by_user(current_user.id)
    return [await _enrich_reservation_read(r, venue_repo, user_repo) for r in reservations]


@router.get("/{reservation_id}", response_model=ReservationRead)
async def get_reservation(
    reservation_id: int,
    current_user: User = Depends(get_current_user),
    service: ReservationService = Depends(get_reservation_service),
    venue_repo: VenueRepository = Depends(get_venue_repository),
    user_repo: UserRepository = Depends(get_user_repository),
):
    try:
        reservation = await service.get_my_reservation(reservation_id, current_user.id)
        return await _enrich_reservation_read(reservation, venue_repo, user_repo)
    except (ReservationNotFoundError, ReservationForbiddenError) as e:
        raise reservation_error_to_http(e)


@router.patch("/{reservation_id}", response_model=ReservationRead)
async def update_reservation(
    reservation_id: int,
    payload: ReservationUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    service: ReservationService = Depends(get_reservation_service),
    venue_repo: VenueRepository = Depends(get_venue_repository),
    user_repo: UserRepository = Depends(get_user_repository),
):
    try:
        reservation = await service.update_reservation(reservation_id, current_user.id, payload)
        if reservation.status == "pending":
            background_tasks.add_task(
                publish_reservation_updated_payload,
                reservation_updated_payload(reservation, current_user),
            )
        return await _enrich_reservation_read(reservation, venue_repo, user_repo)
    except (
        ReservationNotFoundError,
        ReservationForbiddenError,
        ReservationValidationError,
    ) as e:
        raise reservation_error_to_http(e)


@router.delete("/{reservation_id}", response_model=ReservationRead)
async def cancel_reservation(
    reservation_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    service: ReservationService = Depends(get_reservation_service),
    venue_repo: VenueRepository = Depends(get_venue_repository),
    user_repo: UserRepository = Depends(get_user_repository),
):
    try:
        reservation = await service.cancel_reservation(reservation_id, current_user.id)
        background_tasks.add_task(
            publish_reservation_cancelled_payload,
            reservation_cancelled_payload(reservation, current_user),
        )
        return await _enrich_reservation_read(reservation, venue_repo, user_repo)
    except (ReservationNotFoundError, ReservationForbiddenError, ReservationValidationError) as e:
        raise reservation_error_to_http(e)
