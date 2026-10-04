from typing import Optional

from pydantic import BaseModel, ConfigDict


class StaffNotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    message: str
    incoming_reservation_id: Optional[int] = None
    read: bool
