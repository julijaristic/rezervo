"""Sistemski korisnik (FK vlasnik za partner-kreirane lokale)."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user_model import User
from app.services.seed_data import SYSTEM_USERNAME


async def get_or_create_system_owner_id(session: AsyncSession) -> int:
    result = await session.execute(select(User).where(User.username == SYSTEM_USERNAME))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            username=SYSTEM_USERNAME,
            password=hash_password("not-used-system-account"),
            name="System",
            phone="0",
            email="system@rezervo.local",
            is_venue_owner=True,
        )
        session.add(user)
        await session.flush()
    return user.id
