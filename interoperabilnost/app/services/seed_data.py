"""Demo lokali i sistemski korisnik (vlasnik FK u bazi, nije u UI)."""
from datetime import time

from sqlalchemy import func, select

from app.core.security import hash_password
from app.database import async_session_maker
from app.models.user_model import User
from app.models.venue_model import Venue

SYSTEM_USERNAME = "__system__"


async def ensure_demo_data() -> None:
    async with async_session_maker() as session:
        count = await session.scalar(select(func.count()).select_from(Venue))
        if count and count > 0:
            return

        result = await session.execute(select(User).where(User.username == SYSTEM_USERNAME))
        system_user = result.scalar_one_or_none()
        if system_user is None:
            system_user = User(
                username=SYSTEM_USERNAME,
                password=hash_password("not-used-system-account"),
                name="System",
                phone="0",
                email="system@rezervo.local",
                is_venue_owner=True,
            )
            session.add(system_user)
            await session.flush()

        owner_id = system_user.id
        demos = [
            dict(
                name="Demo Restoran",
                address="Knez Mihailova 1",
                city="Beograd",
                country="RS",
                phone="+381111111",
                email="demo1@restoran.local",
                weekday_open=time(10, 0),
                weekday_close=time(22, 0),
                weekend_open=time(10, 0),
                weekend_close=time(22, 0),
                table_count=30,
            ),
            dict(
                name="Demo Kafe",
                address="Obilićev venac 2",
                city="Beograd",
                country="RS",
                phone="+381222222",
                email="demo2@restoran.local",
                weekday_open=time(11, 0),
                weekday_close=time(21, 0),
                weekend_open=time(11, 0),
                weekend_close=time(21, 0),
                table_count=30,
            ),
            dict(
                name="Demo Bistro",
                address="Savska 3",
                city="Beograd",
                country="RS",
                phone="+381333333",
                email="demo3@restoran.local",
                weekday_open=time(10, 0),
                weekday_close=time(22, 0),
                weekend_open=time(10, 0),
                weekend_close=time(22, 0),
                table_count=30,
            ),
        ]
        for d in demos:
            session.add(Venue(owner_id=owner_id, **d))
        await session.commit()
