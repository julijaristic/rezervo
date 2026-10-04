from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from restaurant.app.api.auth_router import get_current_staff
from restaurant.app.database import get_db
from restaurant.app.models.staff_model import Staff
from restaurant.app.schemas.inbox import ApproveInboxBody, DecisionResponse, InboxRead, RejectInboxBody
from restaurant.app.services.inbox_service import (
    get_inbox_row,
    list_inbox,
    send_decision_to_rezervo,
)

router = APIRouter(prefix="/inbox", tags=["inbox"])


@router.get("/", response_model=list[InboxRead])
async def inbox_list(
    staff: Staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
    date: Optional[str] = Query(None, description="Filter: tačan datum YYYY-MM-DD"),
) -> list[InboxRead]:
    rows = await list_inbox(db, staff.venue_id, slot_date=date)
    return [InboxRead.model_validate(r) for r in rows]


def _ensure_staff_venue(staff: Staff, row) -> None:
    if row.venue_id != staff.venue_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Zahtev pripada drugom lokalu")


@router.post("/{inbox_id}/approve", response_model=DecisionResponse)
async def approve_inbox(
    inbox_id: int,
    body: ApproveInboxBody,
    staff: Staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
) -> DecisionResponse:
    row = await get_inbox_row(db, inbox_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zahtev nije pronađen")
    _ensure_staff_venue(staff, row)
    max_tables = int(staff.table_count or 30)
    if body.table_number > max_tables:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Broj stola mora biti između 1 i {max_tables}",
        )
    ok, detail, rezervo = await send_decision_to_rezervo(
        db,
        row,
        "confirmed",
        "Rezervacija je potvrđena od strane restorana (partner servis).",
        table_number=body.table_number,
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail or "Webhook neuspešan")
    return DecisionResponse(
        ok=True,
        inbox_id=row.id,
        rezervo_reservation_id=row.rezervo_reservation_id,
        decision_status=row.decision_status,
        rezervo_response=rezervo,
    )


@router.post("/{inbox_id}/reject", response_model=DecisionResponse)
async def reject_inbox(
    inbox_id: int,
    body: RejectInboxBody = Body(default_factory=RejectInboxBody),
    staff: Staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
) -> DecisionResponse:
    row = await get_inbox_row(db, inbox_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zahtev nije pronađen")
    _ensure_staff_venue(staff, row)
    reason = (body.reason or "").strip()
    if reason:
        guest_message = f"Rezervacija nije prihvaćena. Razlog: {reason}"
    else:
        guest_message = "Rezervacija nije prihvaćena od strane restorana (partner servis)."
    ok, detail, rezervo = await send_decision_to_rezervo(
        db,
        row,
        "rejected",
        guest_message,
        rejection_reason=reason or None,
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail or "Webhook neuspešan")
    return DecisionResponse(
        ok=True,
        inbox_id=row.id,
        rezervo_reservation_id=row.rezervo_reservation_id,
        decision_status=row.decision_status,
        rezervo_response=rezervo,
    )
