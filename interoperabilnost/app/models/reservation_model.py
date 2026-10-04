from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base_model import BaseModel


class Reservation(BaseModel):
    __tablename__ = "reservations"
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    venue_id: Mapped[int] = mapped_column(Integer, ForeignKey("venues.id"), nullable=False)
    table_number: Mapped[int] = mapped_column(Integer, nullable=True)  # nasumičan broj stola (npr. za potvrdu "Sto br 6")
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    guest_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(200), nullable=False)
    notes: Mapped[str] = mapped_column(String(200), nullable=True)
    external_id: Mapped[str] = mapped_column(String(200), nullable=True)

    def __repr__(self) -> str:
        return f"<Reservation(id={self.id}, user_id={self.user_id}, venue_id={self.venue_id}, table_number={self.table_number}, date={self.date}, status={self.status})>"
