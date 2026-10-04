"""API za notifikacije korisnika (potvrda/odbijanje rezervacije)."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.auth_router import get_current_user
from app.models.user_model import User
from app.repositories import get_notification_repository
from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification import NotificationRead

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/", response_model=List[NotificationRead])
async def list_my_notifications(
    current_user: User = Depends(get_current_user),
    repo: NotificationRepository = Depends(get_notification_repository),
    unread_only: Optional[bool] = Query(False, description="Samo nepročitane"),
):
    """Lista notifikacija trenutnog korisnika (najnovije prvo)."""
    notifications = await repo.get_by_user_id(current_user.id, unread_only=unread_only)
    return notifications


@router.patch("/{notification_id}/read", response_model=NotificationRead)
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    repo: NotificationRepository = Depends(get_notification_repository),
):
    """Označava notifikaciju kao pročitanu."""
    notification = await repo.get_for_user(notification_id, current_user.id)
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notifikacija nije pronađena")
    notification.read = True
    return notification
