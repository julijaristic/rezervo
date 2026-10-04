"""Webhook - drugi sistem (ESB potrošač) šalje potvrdu ili odbijanje rezervacije."""
import hmac
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.schemas.notification import WebhookReservationStatus
from app.schemas.venue import VenueCreate, VenueRead
from app.services import get_reservation_service, get_venue_service, ReservationService, VenueService
from app.services.exceptions import ReservationNotFoundError, ReservationValidationError
from app.services.system_user import get_or_create_system_owner_id

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _check_webhook_secret(x_webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret")) -> None:
    if not settings.webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook nije konfigurisan (WEBHOOK_SECRET)",
        )
    if not x_webhook_secret or not hmac.compare_digest(
        x_webhook_secret, settings.webhook_secret
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Neispravan webhook secret")


@router.post("/reservation-status", status_code=status.HTTP_200_OK)
async def reservation_status_webhook(
    payload: WebhookReservationStatus,
    service: ReservationService = Depends(get_reservation_service),
    x_webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret"),
):
    """Drugi sistem poziva ovaj endpoint da potvrdi ili odbije rezervaciju. Kreira notifikaciju korisniku."""
    _check_webhook_secret(x_webhook_secret)

    try:
        reservation = await service.set_reservation_status(
            payload.reservation_id,
            payload.status,
            message=payload.message,
            external_id=payload.external_id,
            table_number=payload.table_number,
        )
    except ReservationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ReservationValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)

    return {
        "ok": True,
        "reservation_id": reservation.id,
        "status": reservation.status,
        "table_number": reservation.table_number,
    }


@router.post("/venues", response_model=VenueRead, status_code=status.HTTP_201_CREATED)
async def partner_create_venue(
    payload: VenueCreate,
    service: VenueService = Depends(get_venue_service),
    db: AsyncSession = Depends(get_db),
    x_webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret"),
) -> VenueRead:
    """Restoran partner kreira lokal u Rezervu - odmah je vidljiv gostima"""
    _check_webhook_secret(x_webhook_secret)
    owner_id = await get_or_create_system_owner_id(db)
    venue = await service.create_venue(payload, owner_id=owner_id)
    return venue
