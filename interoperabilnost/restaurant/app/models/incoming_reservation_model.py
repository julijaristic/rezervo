from typing import Optional

from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from restaurant.app.models.base_model import BaseModel


class IncomingReservation(BaseModel):
    __tablename__ = "incoming_reservations"
    __table_args__ = (UniqueConstraint("rezervo_reservation_id", name="uq_rezervo_reservation_id"),)

    rezervo_reservation_id: Mapped[int] = mapped_column(Integer, nullable=False)
    venue_id: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    guest_username: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    guest_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    guest_phone: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    guest_email: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    table_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    guest_count: Mapped[int] = mapped_column(Integer, nullable=False)
    slot_date: Mapped[str] = mapped_column(String(32), nullable=False)
    start_time: Mapped[str] = mapped_column(String(32), nullable=False)
    end_time: Mapped[str] = mapped_column(String(32), nullable=False)
    rezervo_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    decision_status: Mapped[str] = mapped_column(String(32), nullable=False, default="new")
    external_id: Mapped[str] = mapped_column(String(64), nullable=True)

    
    rejection_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
