"""Šeme za Venue API."""
from datetime import time
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def _parse_time(v):
    if isinstance(v, time):
        return v
    if isinstance(v, str) and len(v) >= 5:
        parts = v.split(":")
        return time(int(parts[0]), int(parts[1]))
    raise ValueError("Očekivano vreme HH:MM")


class VenueHoursMixin(BaseModel):
    weekday_open: time = Field(default=time(10, 0))
    weekday_close: time = Field(default=time(22, 0))
    weekend_open: time = Field(default=time(10, 0))
    weekend_close: time = Field(default=time(22, 0))

    @field_validator("weekday_open", "weekday_close", "weekend_open", "weekend_close", mode="before")
    @classmethod
    def parse_times(cls, v):
        if v is None:
            return v
        return _parse_time(v)

class VenueCreate(VenueHoursMixin):
    name: str = Field(..., max_length=200)
    address: str = Field(..., max_length=200)
    city: str = Field(..., max_length=200)
    country: str = Field(..., max_length=200)
    phone: str = Field(..., max_length=200)
    email: EmailStr
    table_count: int = Field(default=30, ge=1, le=200)

    @field_validator("weekday_close", "weekend_close")
    @classmethod
    def close_after_open_pair(cls, v, info):
        key = info.field_name.replace("_close", "_open")
        open_v = info.data.get(key)
        if open_v is not None and v <= open_v:
            raise ValueError("Kraj radnog vremena mora biti posle početka")
        return v


class PublicVenueRead(VenueHoursMixin):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    address: str
    city: str
    country: str
    phone: str
    email: str
    table_count: int = 30
    is_active: bool = True


class VenueRead(PublicVenueRead):
    owner_id: int
