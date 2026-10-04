"""Šeme za Reservation API."""
from datetime import date as date_type, datetime, time as time_type
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ReservationCreate(BaseModel):
    venue_id: int
    date: date_type = Field(..., description="Datum rezervacije (YYYY-MM-DD)")
    start_time: time_type = Field(..., description="Početak (npr. 18:00)")
    end_time: time_type = Field(..., description="Kraj (npr. 20:00)")
    guest_count: int = Field(..., ge=1, le=30, description="Broj gostiju")
    notes: Optional[str] = Field(None, max_length=200)


class ReservationUpdate(BaseModel):
    """Samo polja koja šalješ se menjaju (partial update)."""
    date: Optional[date_type] = None
    start_time: Optional[time_type] = None
    end_time: Optional[time_type] = None
    guest_count: Optional[int] = Field(None, ge=1, le=30)
    notes: Optional[str] = Field(None, max_length=200)


class ReservationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    venue_id: int
    venue_name: Optional[str] = None
    venue_address: Optional[str] = None
    venue_phone: Optional[str] = None
    guest_name: Optional[str] = None
    guest_phone: Optional[str] = None
    table_number: Optional[int] = None
    date: datetime
    start_time: datetime
    end_time: datetime
    guest_count: int
    status: str
    notes: Optional[str] = None
    external_id: Optional[str] = None
