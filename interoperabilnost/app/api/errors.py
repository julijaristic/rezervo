"""Mapiranje servisnih izuzetaka na HTTP odgovore."""
from fastapi import HTTPException, status

from app.services.exceptions import (
    ReservationError,
    ReservationForbiddenError,
    ReservationNotFoundError,
    ReservationValidationError,
    VenueNotFoundError,
)


def reservation_error_to_http(exc: ReservationError) -> HTTPException:
    if isinstance(exc, VenueNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
    if isinstance(exc, ReservationNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
    if isinstance(exc, ReservationForbiddenError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exc.message)
    if isinstance(exc, ReservationValidationError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)
