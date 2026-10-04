"""Inbox, notifikacije osoblju i webhook ka Rezervu."""
import logging
from typing import List, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from restaurant.app.config import settings
from restaurant.app.models.incoming_reservation_model import IncomingReservation
from restaurant.app.models.notification_model import StaffNotification
from restaurant.app.services.venue_lookup import accepted_venue_ids_for_messaging

logger = logging.getLogger(__name__)

QUEUE_RESERVATION_CREATED = "reservation.created"
QUEUE_RESERVATION_CANCELLED = "reservation.cancelled"
QUEUE_RESERVATION_UPDATED = "reservation.updated"


def _table_from_payload(body: dict) -> Optional[int]:
    raw = body.get("table_number")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _guest_fields_from_payload(body: dict) -> dict[str, str]:
    return {
        "guest_username": str(body.get("guest_username") or ""),
        "guest_name": str(body.get("guest_name") or ""),
        "guest_phone": str(body.get("guest_phone") or ""),
        "guest_email": str(body.get("guest_email") or ""),
    }


def _slot_from_payload(body: dict) -> tuple[str, str, str]:
    date_val = body.get("date") or ""
    if isinstance(date_val, str) and "T" in date_val:
        date_val = date_val.split("T")[0]
    start = body.get("start_time") or ""
    end = body.get("end_time") or ""
    if isinstance(start, str) and "T" in start:
        start = start.split("T")[1][:5]
    if isinstance(end, str) and "T" in end:
        end = end.split("T")[1][:5]
    return str(date_val)[:10], str(start)[:32], str(end)[:32]


async def _add_staff_notification(
    session: AsyncSession,
    venue_id: int,
    kind: str,
    message: str,
    incoming_id: Optional[int] = None,
) -> None:
    session.add(
        StaffNotification(
            kind=kind,
            message=message,
            venue_id=int(venue_id),
            incoming_reservation_id=incoming_id,
            read=False,
        )
    )


async def ingest_reservation_event(body: dict) -> bool:
    """Upis iz RabbitMQ poruke. True ako je novi inbox red."""
    venue_id = body.get("venue_id")
    reservation_id = body.get("reservation_id")
    if reservation_id is None or venue_id is None:
        return False
    slot_date, start_time, end_time = _slot_from_payload(body)
    guest_count = int(body.get("guest_count") or 0)
    user_id = int(body.get("user_id") or 0)
    rezervo_status = str(body.get("status") or "pending")

    from restaurant.app.database import async_session_maker

    async with async_session_maker() as session:
        allowed = await accepted_venue_ids_for_messaging(session)
        if int(venue_id) not in allowed:
            return False

        existing = await session.execute(
            select(IncomingReservation).where(
                IncomingReservation.rezervo_reservation_id == int(reservation_id)
            )
        )
        if existing.scalar_one_or_none() is not None:
            return False

        guest_fields = _guest_fields_from_payload(body)
        row = IncomingReservation(
            rezervo_reservation_id=int(reservation_id),
            venue_id=int(venue_id),
            user_id=user_id,
            guest_count=guest_count,
            table_number=_table_from_payload(body),
            slot_date=slot_date,
            start_time=start_time,
            end_time=end_time,
            rezervo_status=rezervo_status,
            decision_status="new",
            **guest_fields,
        )
        session.add(row)
        try:
            await session.flush()
        except IntegrityError:
            await session.rollback()
            return False

        msg = (
            f"Novi zahtev Rezervo #{reservation_id}: "
            f"{slot_date} {start_time}-{end_time}, {guest_count} gostiju."
        )
        await _add_staff_notification(session, int(venue_id), "reservation_created", msg, row.id)
        await session.commit()
        logger.info("Inbox: rezervo_reservation_id=%s", reservation_id)
        return True


async def ingest_reservation_cancelled(body: dict) -> None:
    """Obavesti osoblje da je gost otkazao rezervaciju u Rezervu."""
    venue_id = body.get("venue_id")
    reservation_id = body.get("reservation_id")
    if reservation_id is None or venue_id is None:
        return
    slot_date, start_time, end_time = _slot_from_payload(body)
    from restaurant.app.database import async_session_maker

    async with async_session_maker() as session:
        allowed = await accepted_venue_ids_for_messaging(session)
        if int(venue_id) not in allowed:
            return

        result = await session.execute(
            select(IncomingReservation).where(
                IncomingReservation.rezervo_reservation_id == int(reservation_id)
            )
        )
        row = result.scalar_one_or_none()
        incoming_id = None
        if row is not None:
            row.rezervo_status = "cancelled"
            guest_fields = _guest_fields_from_payload(body)
            for key, val in guest_fields.items():
                if val:
                    setattr(row, key, val)
            table = _table_from_payload(body)
            if table is not None:
                row.table_number = table
            incoming_id = row.id

        msg = (
            f"Gost je otkazao Rezervo #{reservation_id} "
            f"({slot_date} {start_time}-{end_time})."
        )
        await _add_staff_notification(session, int(venue_id), "reservation_cancelled", msg, incoming_id)
        await session.commit()
        logger.info("Otkaz primljen: rezervo_reservation_id=%s", reservation_id)


async def ingest_reservation_updated(body: dict) -> None:
    """Ažuriraj inbox red kad gost izmeni pending rezervaciju."""
    venue_id = body.get("venue_id")
    reservation_id = body.get("reservation_id")
    if reservation_id is None or venue_id is None:
        return

    slot_date, start_time, end_time = _slot_from_payload(body)
    guest_count = int(body.get("guest_count") or 0)
    rezervo_status = str(body.get("status") or "pending")

    from restaurant.app.database import async_session_maker

    async with async_session_maker() as session:
        allowed = await accepted_venue_ids_for_messaging(session)
        if int(venue_id) not in allowed:
            return

        result = await session.execute(
            select(IncomingReservation).where(
                IncomingReservation.rezervo_reservation_id == int(reservation_id)
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return
        if row.decision_status != "new":
            return

        row.slot_date = slot_date
        row.start_time = start_time
        row.end_time = end_time
        row.guest_count = guest_count
        row.rezervo_status = rezervo_status
        guest_fields = _guest_fields_from_payload(body)
        for key, val in guest_fields.items():
            if val:
                setattr(row, key, val)
        table = _table_from_payload(body)
        if table is not None:
            row.table_number = table

        msg = (
            f"Gost je izmenio Rezervo #{reservation_id}: "
            f"{slot_date} {start_time}-{end_time}, {guest_count} gostiju."
        )
        await _add_staff_notification(
            session, int(venue_id), "reservation_updated", msg, row.id
        )
        await session.commit()
        logger.info("Update primljen: rezervo_reservation_id=%s", reservation_id)


async def list_inbox(
    session: AsyncSession,
    venue_id: int,
    slot_date: Optional[str] = None,
) -> List[IncomingReservation]:
    q = select(IncomingReservation).where(IncomingReservation.venue_id == venue_id)
    if slot_date:
        q = q.where(IncomingReservation.slot_date == slot_date)
    q = q.order_by(
        IncomingReservation.slot_date.desc(),
        IncomingReservation.start_time.desc(),
        IncomingReservation.id.desc(),
    )
    result = await session.execute(q)
    return list(result.scalars().all())


async def get_inbox_row(session: AsyncSession, inbox_id: int) -> Optional[IncomingReservation]:
    result = await session.execute(
        select(IncomingReservation).where(IncomingReservation.id == inbox_id)
    )
    return result.scalar_one_or_none()


async def send_decision_to_rezervo(
    session: AsyncSession,
    row: IncomingReservation,
    status: str,
    message: str,
    table_number: Optional[int] = None,
    rejection_reason: Optional[str] = None,
) -> tuple[bool, Optional[str], Optional[dict]]:
    if row.decision_status != "new":
        return False, f"Zahtev je već obrađen ({row.decision_status})", None
    if not settings.rezervo_webhook_secret:
        return False, "REZERVO_WEBHOOK_SECRET nije podešen", None

    external_id = f"REST-inbox-{row.id}"
    payload = {
        "reservation_id": row.rezervo_reservation_id,
        "status": status,
        "message": message,
        "external_id": external_id,
    }
    if status == "confirmed":
        if table_number is None:
            return False, "Broj stola je obavezan pri odobrenju", None
        payload["table_number"] = int(table_number)
    url = f"{settings.rezervo_api_url.rstrip('/')}/webhooks/reservation-status"
    headers = {"X-Webhook-Secret": settings.rezervo_webhook_secret}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=15.0)
    except httpx.HTTPError as exc:
        await _add_staff_notification(
            session,
            row.venue_id,
            "webhook_error",
            f"Webhook greška za #{row.rezervo_reservation_id}: {exc}",
            row.id,
        )
        return False, str(exc), None

    if response.status_code != 200:
        detail = response.text[:500]
        await _add_staff_notification(
            session,
            row.venue_id,
            "webhook_error",
            f"Rezervo vratio {response.status_code} za #{row.rezervo_reservation_id}: {detail}",
            row.id,
        )
        return False, detail, None

    try:
        data = response.json()
    except Exception:
        data = {"raw": response.text}

    row.decision_status = "sent_confirmed" if status == "confirmed" else "sent_rejected"
    row.rezervo_status = "confirmed" if status == "confirmed" else "rejected"
    row.external_id = external_id
    if status == "rejected" and rejection_reason:
        row.rejection_reason = rejection_reason.strip()
    if status == "confirmed" and isinstance(data, dict):
        table = data.get("table_number")
        if table is not None:
            try:
                row.table_number = int(table)
            except (TypeError, ValueError):
                pass
    if status == "confirmed":
        staff_msg = f"Zahtev #{row.rezervo_reservation_id} je potvrđen."
        if table_number is not None:
            staff_msg += f" Sto {table_number}."
        staff_msg += " Gost je obavešten."
    else:
        staff_msg = f"Zahtev #{row.rezervo_reservation_id} je odbijen. Gost je obavešten."
    await _add_staff_notification(
        session,
        row.venue_id,
        "webhook_ok",
        staff_msg,
        row.id,
    )
    return True, None, data
