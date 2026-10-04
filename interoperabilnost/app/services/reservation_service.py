"""Servis za rezervacije - gost i webhook (restoran partner)."""
from datetime import date as date_type, datetime, time
from typing import List, Optional

from app.models.notification_model import Notification
from app.models.reservation_model import Reservation
from app.repositories.notification_repository import NotificationRepository
from app.repositories.reservation_repository import ReservationRepository
from app.repositories.user_repository import UserRepository
from app.repositories.venue_repository import VenueRepository
from app.schemas.reservation import ReservationCreate, ReservationUpdate
from app.services.opening_hours import ensure_within_opening_hours
from app.services.exceptions import (
    ReservationForbiddenError,
    ReservationNotFoundError,
    ReservationValidationError,
    VenueNotFoundError,
)


class ReservationService:
    def __init__(
        self,
        reservation_repo: ReservationRepository,
        venue_repo: VenueRepository,
        notification_repo: NotificationRepository,
        user_repo: UserRepository,
    ):
        self._reservation_repo = reservation_repo
        self._venue_repo = venue_repo
        self._notification_repo = notification_repo
        self._user_repo = user_repo

    async def _add_notification(
        self, user_id: int, reservation_id: int, kind: str, message: str
    ) -> None:
        await self._notification_repo.add(
            Notification(
                user_id=user_id,
                reservation_id=reservation_id,
                kind=kind,
                message=message,
                read=False,
            )
        )

    def _validate_schedule(
        self, res_date: date_type, start_time: time, end_time: time
    ) -> tuple[datetime, datetime, datetime]:
        if end_time <= start_time:
            raise ReservationValidationError("Kraj rezervacije mora biti posle početka")
        start_dt = datetime.combine(res_date, start_time)
        end_dt = datetime.combine(res_date, end_time)
        if start_dt < datetime.now():
            raise ReservationValidationError("Datum i vreme rezervacije ne mogu biti u prošlosti")
        date_dt = datetime.combine(res_date, time(0, 0, 0))
        return start_dt, end_dt, date_dt

    async def create_reservation(self, user_id: int, payload: ReservationCreate) -> Reservation:
        venue = await self._venue_repo.get_by_id(payload.venue_id)
        if venue is None:
            raise VenueNotFoundError("Lokal nije pronađen")
        if not venue.is_active or venue.is_deleted:
            raise ReservationValidationError("Lokal trenutno ne prima rezervacije")

        start_dt, end_dt, date_dt = self._validate_schedule(
            payload.date, payload.start_time, payload.end_time
        )
        ensure_within_opening_hours(venue, payload.date, payload.start_time, payload.end_time)

        reservation = Reservation(
            user_id=user_id,
            venue_id=payload.venue_id,
            table_number=None,
            date=date_dt,
            start_time=start_dt,
            end_time=end_dt,
            guest_count=payload.guest_count,
            status="pending",
            notes=payload.notes,
        )
        await self._reservation_repo.add(reservation)
        return reservation

    async def get_by_id(self, reservation_id: int) -> Reservation:
        reservation = await self._reservation_repo.get_by_id(reservation_id)
        if reservation is None:
            raise ReservationNotFoundError("Rezervacija nije pronađena")
        return reservation

    async def list_by_user(self, user_id: int) -> List[Reservation]:
        return await self._reservation_repo.get_by_user_id(user_id)

    async def get_my_reservation(self, reservation_id: int, user_id: int) -> Reservation:
        reservation = await self.get_by_id(reservation_id)
        if reservation.user_id != user_id:
            raise ReservationForbiddenError("Nemaš pravo pristupa ovoj rezervaciji")
        return reservation

    async def cancel_reservation(self, reservation_id: int, user_id: int) -> Reservation:
        reservation = await self.get_my_reservation(reservation_id, user_id)
        if reservation.status not in ("pending", "confirmed"):
            raise ReservationValidationError(
                f"Rezervaciju u statusu '{reservation.status}' nije moguće otkazati"
            )
        reservation.status = "cancelled"
        await self._add_notification(
            user_id,
            reservation.id,
            "cancelled",
            "Otkazali ste rezervaciju.",
        )
        return reservation

    async def update_reservation(
        self, reservation_id: int, user_id: int, payload: ReservationUpdate
    ) -> Reservation:
        reservation = await self.get_my_reservation(reservation_id, user_id)
        if reservation.status != "pending":
            raise ReservationValidationError(
                f"Rezervaciju u statusu '{reservation.status}' nije moguće menjati"
            )

        res_date = (
            reservation.date.date()
            if hasattr(reservation.date, "date")
            else reservation.date
        )
        if payload.date is not None:
            res_date = payload.date
            reservation.date = datetime.combine(payload.date, time(0, 0, 0))
            if payload.start_time is None and hasattr(reservation.start_time, "time"):
                reservation.start_time = datetime.combine(res_date, reservation.start_time.time())
            if payload.end_time is None and hasattr(reservation.end_time, "time"):
                reservation.end_time = datetime.combine(res_date, reservation.end_time.time())
        if payload.start_time is not None:
            reservation.start_time = datetime.combine(res_date, payload.start_time)
        if payload.end_time is not None:
            reservation.end_time = datetime.combine(res_date, payload.end_time)
        if payload.guest_count is not None:
            reservation.guest_count = payload.guest_count
        if payload.notes is not None:
            reservation.notes = payload.notes

        res_start = (
            reservation.start_time.time()
            if hasattr(reservation.start_time, "time")
            else reservation.start_time
        )
        res_end = (
            reservation.end_time.time()
            if hasattr(reservation.end_time, "time")
            else reservation.end_time
        )
        start_dt, end_dt, date_dt = self._validate_schedule(res_date, res_start, res_end)
        venue = await self._venue_repo.get_by_id(reservation.venue_id)
        if venue:
            ensure_within_opening_hours(venue, res_date, res_start, res_end)
        reservation.date = date_dt
        reservation.start_time = start_dt
        reservation.end_time = end_dt
        return reservation

    async def _apply_table_number(self, reservation: Reservation, table_number: int) -> None:
        venue = await self._venue_repo.get_by_id(reservation.venue_id)
        max_tables = int(venue.table_count) if venue and venue.table_count else 30
        if table_number < 1 or table_number > max_tables:
            raise ReservationValidationError(
                f"Broj stola mora biti između 1 i {max_tables}"
            )
        start_dt = reservation.start_time
        end_dt = reservation.end_time
        if not hasattr(start_dt, "hour"):
            raise ReservationValidationError("Neispravan termin rezervacije")
        used = await self._reservation_repo.get_used_table_numbers(
            reservation.venue_id, start_dt, end_dt, exclude_reservation_id=reservation.id
        )
        if table_number in set(used):
            raise ReservationValidationError(
                f"Sto {table_number} je već rezervisan u tom terminu"
            )
        reservation.table_number = table_number

    async def set_reservation_status(
        self,
        reservation_id: int,
        status: str,
        message: Optional[str] = None,
        external_id: Optional[str] = None,
        table_number: Optional[int] = None,
    ) -> Reservation:
        reservation = await self._reservation_repo.get_by_id(reservation_id)
        if reservation is None:
            raise ReservationNotFoundError("Rezervacija nije pronađena")
        if status not in ("confirmed", "rejected"):
            raise ReservationValidationError("Status mora biti confirmed ili rejected")

        if reservation.status == status:
            if external_id is not None and reservation.external_id != external_id:
                reservation.external_id = external_id
            return reservation

        if reservation.status not in ("pending",):
            raise ReservationValidationError(
                f"Rezervaciju u statusu '{reservation.status}' nije moguće potvrditi/odbiti"
            )

        reservation.status = status
        if external_id is not None:
            reservation.external_id = external_id

        if status == "confirmed":
            if table_number is None:
                raise ReservationValidationError(
                    "Broj stola (table_number) je obavezan pri potvrdi rezervacije"
                )
            await self._apply_table_number(reservation, table_number)

        sto_txt = f" Sto br {reservation.table_number}." if reservation.table_number else ""
        msg = message or (
            f"Rezervacija je potvrđena.{sto_txt}" if status == "confirmed" else "Rezervacija je odbijena."
        )
        await self._add_notification(
            reservation.user_id,
            reservation.id,
            status,
            msg,
        )
        return reservation
