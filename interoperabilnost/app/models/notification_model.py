"""Model za notifikacije korisniku (potvrda/odbijanje rezervacije)."""
from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base_model import BaseModel


class Notification(BaseModel):
    __tablename__ = "notifications"
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    reservation_id: Mapped[int] = mapped_column(Integer, ForeignKey("reservations.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    # confirmed | rejected | cancelled | reservation_created | reservation_updated
    message: Mapped[str] = mapped_column(String(500), nullable=True)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
