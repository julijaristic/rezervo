from datetime import time

from sqlalchemy import ForeignKey, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base_model import BaseModel


class Venue(BaseModel):
    __tablename__ = "venues"
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str] = mapped_column(String(200), nullable=False)
    city: Mapped[str] = mapped_column(String(200), nullable=False)
    country: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    weekday_open: Mapped[time] = mapped_column(Time, nullable=False, default=time(10, 0))
    weekday_close: Mapped[time] = mapped_column(Time, nullable=False, default=time(22, 0))
    weekend_open: Mapped[time] = mapped_column(Time, nullable=False, default=time(10, 0))
    weekend_close: Mapped[time] = mapped_column(Time, nullable=False, default=time(22, 0))
    table_count: Mapped[int] = mapped_column(Integer, nullable=False, default=30)