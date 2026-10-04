"""Publikovanje događaja rezervacije u RabbitMQ."""
import json
import logging
from datetime import datetime

from app.config import settings
from typing import TYPE_CHECKING, Optional

from app.models.reservation_model import Reservation

if TYPE_CHECKING:
    from app.models.user_model import User

logger = logging.getLogger(__name__)

QUEUE_RESERVATION_CREATED = "reservation.created"
QUEUE_RESERVATION_CANCELLED = "reservation.cancelled"
QUEUE_RESERVATION_UPDATED = "reservation.updated"


def _guest_payload(user: Optional["User"]) -> dict:
    if user is None:
        return {}
    return {
        "guest_username": user.username,
        "guest_name": user.name,
        "guest_phone": user.phone,
        "guest_email": user.email,
    }


def _base_payload(reservation: Reservation, user: Optional["User"] = None) -> dict:
    body = {
        "reservation_id": reservation.id,
        "user_id": reservation.user_id,
        "venue_id": reservation.venue_id,
        "table_number": reservation.table_number,
        "date": reservation.date.isoformat() if hasattr(reservation.date, "isoformat") else str(reservation.date),
        "start_time": reservation.start_time.isoformat()
        if hasattr(reservation.start_time, "isoformat")
        else str(reservation.start_time),
        "end_time": reservation.end_time.isoformat()
        if hasattr(reservation.end_time, "isoformat")
        else str(reservation.end_time),
        "guest_count": reservation.guest_count,
        "status": reservation.status,
    }
    body.update(_guest_payload(user))
    return body


def reservation_created_payload(reservation: Reservation, user: Optional["User"] = None) -> dict:
    body = _base_payload(reservation, user)
    body["created_at"] = datetime.utcnow().isoformat() + "Z"
    return body


def reservation_cancelled_payload(reservation: Reservation, user: Optional["User"] = None) -> dict:
    body = _base_payload(reservation, user)
    body["cancelled_at"] = datetime.utcnow().isoformat() + "Z"
    return body


def reservation_updated_payload(reservation: Reservation, user: Optional["User"] = None) -> dict:
    body = _base_payload(reservation, user)
    body["updated_at"] = datetime.utcnow().isoformat() + "Z"
    return body


async def _publish_json(queue_name: str, body: dict) -> None:
    if not settings.rabbitmq_url:
        logger.debug("RabbitMQ nije podešen, preskačem publish.")
        return
    try:
        import aio_pika

        connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        async with connection:
            channel = await connection.channel()
            await channel.declare_queue(queue_name, durable=True)
            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(body).encode(),
                    content_type="application/json",
                ),
                routing_key=queue_name,
            )
        logger.info("Poslata poruka %s za id=%s", queue_name, body.get("reservation_id"))
    except Exception as e:
        logger.warning("Neuspelo slanje u RabbitMQ (%s): %s", queue_name, e)


async def publish_reservation_created_payload(body: dict) -> None:
    await _publish_json(QUEUE_RESERVATION_CREATED, body)


async def publish_reservation_cancelled_payload(body: dict) -> None:
    await _publish_json(QUEUE_RESERVATION_CANCELLED, body)


async def publish_reservation_updated_payload(body: dict) -> None:
    await _publish_json(QUEUE_RESERVATION_UPDATED, body)
