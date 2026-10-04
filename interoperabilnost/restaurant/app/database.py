"""Async SQLAlchemy za restoran servis."""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from restaurant.app.config import settings

engine = create_async_engine(settings.database_url, echo=False)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def _sqlite_migrate_staff_and_notifications(connection) -> None:
    from sqlalchemy import text

    def column_names(table: str):
        rows = connection.execute(text(f"PRAGMA table_info({table})")).fetchall()
        return {row[1] for row in rows}

    staff_cols = column_names("staff")
    if staff_cols and "venue_id" not in staff_cols:
        connection.execute(text("ALTER TABLE staff ADD COLUMN venue_id INTEGER NOT NULL DEFAULT 1"))
    if staff_cols and "venue_name" not in staff_cols:
        connection.execute(
            text("ALTER TABLE staff ADD COLUMN venue_name VARCHAR(200) NOT NULL DEFAULT 'Lokal'")
        )

    notif_cols = column_names("staff_notifications")
    if notif_cols and "venue_id" not in notif_cols:
        connection.execute(
            text("ALTER TABLE staff_notifications ADD COLUMN venue_id INTEGER NOT NULL DEFAULT 1")
        )

    inbox_cols = column_names("incoming_reservations")
    if inbox_cols:
        for col, ddl in (
            ("guest_username", "VARCHAR(200) NOT NULL DEFAULT ''"),
            ("guest_name", "VARCHAR(200) NOT NULL DEFAULT ''"),
            ("guest_phone", "VARCHAR(200) NOT NULL DEFAULT ''"),
            ("guest_email", "VARCHAR(200) NOT NULL DEFAULT ''"),
        ):
            if col not in inbox_cols:
                connection.execute(text(f"ALTER TABLE incoming_reservations ADD COLUMN {col} {ddl}"))
        if "table_number" not in inbox_cols:
            connection.execute(
                text("ALTER TABLE incoming_reservations ADD COLUMN table_number INTEGER")
            )
        if "rejection_reason" not in inbox_cols:
            connection.execute(
                text("ALTER TABLE incoming_reservations ADD COLUMN rejection_reason VARCHAR(500)")
            )

    staff_cols2 = column_names("staff")
    if staff_cols2 and "table_count" not in staff_cols2:
        connection.execute(
            text("ALTER TABLE staff ADD COLUMN table_count INTEGER NOT NULL DEFAULT 30")
        )


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_sqlite_migrate_staff_and_notifications)
