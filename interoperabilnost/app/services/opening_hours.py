"""Provera radnog vremena lokala (radni dan vs vikend)."""
from datetime import date, time

from app.models.venue_model import Venue
from app.services.exceptions import ReservationValidationError

DEFAULT_OPEN = time(10, 0)
DEFAULT_CLOSE = time(22, 0)


def is_weekend(res_date: date) -> bool:
    return res_date.weekday() >= 5


def opening_window(venue: Venue, res_date: date) -> tuple[time, time]:
    if is_weekend(res_date):
        open_t = venue.weekend_open or DEFAULT_OPEN
        close_t = venue.weekend_close or DEFAULT_CLOSE
    else:
        open_t = venue.weekday_open or DEFAULT_OPEN
        close_t = venue.weekday_close or DEFAULT_CLOSE
    return open_t, close_t


def ensure_within_opening_hours(
    venue: Venue, res_date: date, start_time: time, end_time: time
) -> None:
    open_t, close_t = opening_window(venue, res_date)
    if close_t <= open_t:
        raise ReservationValidationError("Lokal nema definisano radno vreme za izabrani dan")
    if start_time < open_t or end_time > close_t:
        raise ReservationValidationError(
            f"Termin mora biti u radnom vremenu lokala ({open_t.strftime('%H:%M')}-{close_t.strftime('%H:%M')})"
        )


def format_hours_label(venue: Venue) -> str:
    wo = venue.weekday_open or DEFAULT_OPEN
    wc = venue.weekday_close or DEFAULT_CLOSE
    so = venue.weekend_open or DEFAULT_OPEN
    sc = venue.weekend_close or DEFAULT_CLOSE
    return (
        f"Pon-Pet {wo.strftime('%H:%M')}-{wc.strftime('%H:%M')}, "
        f"Vikend {so.strftime('%H:%M')}-{sc.strftime('%H:%M')}"
    )
