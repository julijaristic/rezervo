from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class InboxRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rezervo_reservation_id: int
    venue_id: int
    user_id: int
    guest_username: str = ""
    guest_name: str = ""
    guest_phone: str = ""
    guest_email: str = ""
    table_number: Optional[int] = None
    guest_count: int
    slot_date: str
    start_time: str
    end_time: str
    rezervo_status: str
    decision_status: str
    external_id: Optional[str] = None
    rejection_reason: Optional[str] = None


class ApproveInboxBody(BaseModel):
    table_number: int = Field(..., ge=1, le=200)


class RejectInboxBody(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)


class DecisionResponse(BaseModel):
    ok: bool
    inbox_id: int
    rezervo_reservation_id: int
    decision_status: str
    rezervo_response: Optional[dict] = None
    detail: Optional[str] = None
