"""Login and JWT auth."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import create_access_token, decode_token, hash_password, verify_password
from app.models.user_model import User
from app.repositories import get_user_repository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, Token

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    repo: UserRepository = Depends(get_user_repository),
) -> dict:
    if await repo.exists_by_username(payload.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Korisničko ime već postoji",
        )
    user = User(
        username=payload.username,
        password=hash_password(payload.password),
        name=payload.name,
        phone=payload.phone,
        email=payload.email,
        is_venue_owner=False,
    )
    await repo.add(user)
    return {"id": user.id, "username": user.username}


@router.post("/login", response_model=Token)
async def login(
    payload: LoginRequest,
    repo: UserRepository = Depends(get_user_repository),
) -> Token:
    user = await repo.get_by_username(payload.username)
    if user is None or not verify_password(payload.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Pogrešno korisničko ime ili lozinka",
        )
    token = create_access_token(subject=user.id)
    return Token(access_token=token)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    repo: UserRepository = Depends(get_user_repository),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nije prosleđen token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = decode_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Neispravan ili istekao token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = await repo.get_by_id(int(user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Korisnik nije pronađen",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)) -> dict:
    """Primer zaštićene rute - vraća trenutnog korisnika."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "name": current_user.name,
        "email": current_user.email,
    }
