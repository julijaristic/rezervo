"""Šeme za Notification i webhook."""
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    reservation_id: int
    kind: str
    message: Optional[str] = None
    read: bool


class WebhookReservationStatus(BaseModel):
    """Body za webhook - drugi sistem šalje potvrdu ili odbijanje."""
    reservation_id: int
    status: str = Field(..., pattern="^(confirmed|rejected)$")
    external_id: Optional[str] = None
    message: Optional[str] = None
    table_number: Optional[int] = Field(None, ge=1, le=200)

    @model_validator(mode="after")
    def confirmed_requires_table(self) -> "WebhookReservationStatus":
        if self.status == "confirmed" and self.table_number is None:
            raise ValueError("table_number je obavezan pri potvrdi rezervacije")
        return self
