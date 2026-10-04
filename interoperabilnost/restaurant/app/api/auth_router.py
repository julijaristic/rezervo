from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from restaurant.app.core.security import create_access_token, decode_token, hash_password, verify_password
from restaurant.app.database import get_db
from restaurant.app.models.staff_model import Staff
from restaurant.app.schemas.auth import LoginRequest, RegisterRequest, StaffRead, Token
from restaurant.app.services.venue_lookup import register_new_venue_in_rezervo

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


def staff_to_read(staff: Staff) -> StaffRead:
    return StaffRead(
        id=staff.id,
        username=staff.username,
        display_name=staff.display_name,
        venue_id=staff.venue_id,
        venue_name=staff.venue_name,
        table_count=staff.table_count,
    )


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> Token:
    venue = await register_new_venue_in_rezervo(payload.new_venue.model_dump(mode="json"))
    staff = Staff(
        username=payload.username.strip(),
        password_hash=hash_password(payload.password),
        display_name=payload.username.strip(),
        venue_id=int(venue["id"]),
        venue_name=str(venue.get("name") or f"Lokal #{venue['id']}"),
        table_count=int(venue.get("table_count") or payload.new_venue.table_count),
    )
    db.add(staff)
    try:
        await db.flush()
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Korisničko ime je već zauzeto. Lokal je već kreiran u Rezervu "
                f"(id {venue['id']}). Uklonite ga ručno u Rezervu ako registracija nije završena."
            ),
        ) from exc
    token = create_access_token(staff.id)
    return Token(access_token=token)


@router.post("/login", response_model=Token)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> Token:
    result = await db.execute(select(Staff).where(Staff.username == payload.username))
    staff = result.scalar_one_or_none()
    if staff is None or not verify_password(payload.password, staff.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Pogrešno korisničko ime ili lozinka",
        )
    token = create_access_token(staff.id)
    return Token(access_token=token)


async def get_current_staff(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Staff:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nije prosleđen token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    sub = decode_token(credentials.credentials)
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Neispravan token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    result = await db.execute(select(Staff).where(Staff.id == int(sub)))
    staff = result.scalar_one_or_none()
    if staff is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Korisnik nije pronađen")
    return staff


@router.get("/me", response_model=StaffRead)
async def me(staff: Staff = Depends(get_current_staff)) -> StaffRead:
    return staff_to_read(staff)
