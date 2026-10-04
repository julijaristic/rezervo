from pydantic import BaseModel, EmailStr, Field, model_validator

from restaurant.app.schemas.opening_hours import ensure_close_after_open


class LoginRequest(BaseModel):
    username: str
    password: str


class NewVenueRegister(BaseModel):
    name: str = Field(..., max_length=200)
    address: str = Field(..., max_length=200)
    city: str = Field(..., max_length=200)
    country: str = Field(default="Srbija", max_length=200)
    phone: str = Field(..., max_length=200)
    email: EmailStr
    weekday_open: str = Field(default="10:00")
    weekday_close: str = Field(default="22:00")
    weekend_open: str = Field(default="10:00")
    weekend_close: str = Field(default="22:00")
    table_count: int = Field(default=30, ge=1, le=200)

    @model_validator(mode="after")
    def validate_opening_hours(self) -> "NewVenueRegister":
        ensure_close_after_open(self.weekday_open, self.weekday_close, "Pon-Pet")
        ensure_close_after_open(self.weekend_open, self.weekend_close, "Vikend")
        return self


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=6, max_length=200)
    new_venue: NewVenueRegister


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class StaffRead(BaseModel):
    id: int
    username: str
    display_name: str
    venue_id: int
    venue_name: str
    table_count: int = 30
