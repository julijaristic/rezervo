from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from restaurant.app.api.auth_router import get_current_staff
from restaurant.app.database import get_db
from restaurant.app.models.notification_model import StaffNotification
from restaurant.app.models.staff_model import Staff
from restaurant.app.schemas.notification import StaffNotificationRead

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/", response_model=List[StaffNotificationRead])
async def list_notifications(
    staff: Staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
    unread_only: Optional[bool] = Query(False),
) -> List[StaffNotificationRead]:
    q = (
        select(StaffNotification)
        .where(StaffNotification.venue_id == staff.venue_id)
        .order_by(StaffNotification.id.desc())
    )
    if unread_only:
        q = q.where(StaffNotification.read.is_(False))
    result = await db.execute(q)
    return list(result.scalars().all())


@router.patch("/{notification_id}/read", response_model=StaffNotificationRead)
async def mark_read(
    notification_id: int,
    staff: Staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
) -> StaffNotificationRead:
    result = await db.execute(
        select(StaffNotification).where(
            StaffNotification.id == notification_id,
            StaffNotification.venue_id == staff.venue_id,
        )
    )
    notification = result.scalar_one_or_none()
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notifikacija nije pronađena")
    notification.read = True
    return notification
