from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base_model import BaseModel

class User(BaseModel):
    __tablename__ = "users"
    username: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False)
    password: Mapped[str] = mapped_column(String(200), nullable=False)
    is_venue_owner: Mapped[bool] = mapped_column(Boolean, default=False)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username!r})>"
