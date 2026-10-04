from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from restaurant.app.models.base_model import BaseModel


class StaffNotification(BaseModel):
    __tablename__ = "staff_notifications"
    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    venue_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    incoming_reservation_id: Mapped[int] = mapped_column(Integer, nullable=True)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
