"""Auth request/response schemas."""
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=200)
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=200)
    password: str = Field(..., min_length=6, max_length=200)
    name: str = Field(..., min_length=1, max_length=200)
    phone: str = Field(..., min_length=1, max_length=200)
    email: EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
