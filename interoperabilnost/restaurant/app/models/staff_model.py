from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from restaurant.app.models.base_model import BaseModel


class Staff(BaseModel):
    __tablename__ = "staff"
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False, default="Osoblje")
    venue_id: Mapped[int] = mapped_column(nullable=False, index=True)
    venue_name: Mapped[str] = mapped_column(String(200), nullable=False, default="Lokal")
    table_count: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
