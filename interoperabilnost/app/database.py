"""SQLAlchemy async engine i sesija za FastAPI."""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# Async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
)

# Async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Bazna klasa za sve ORM modele."""

    pass


async def get_db() -> AsyncSession:
    """Dependency za FastAPI - daje async sesiju u ruti."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def apply_migrations() -> None:
    """Primeni Alembic migracije (idempotentno)."""
    import asyncio
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    ini = root / "alembic.ini"
    if not ini.is_file():
        return

    def _run() -> None:
        from alembic import command
        from alembic.config import Config

        cfg = Config(str(ini))
        cfg.set_main_option("sqlalchemy.url", settings.database_url)
        command.upgrade(cfg, "head")

    await asyncio.to_thread(_run)


def _sqlite_ensure_venue_table_count(connection) -> None:
    from sqlalchemy import text

    rows = connection.execute(text("PRAGMA table_info(venues)")).fetchall()
    if not rows:
        return
    cols = {row[1] for row in rows}
    if "table_count" not in cols:
        connection.execute(
            text("ALTER TABLE venues ADD COLUMN table_count INTEGER NOT NULL DEFAULT 30")
        )


async def init_db() -> None:
    """Migracije + create_all za tabele koje migracije još ne pokrivaju."""
    await apply_migrations()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_sqlite_ensure_venue_table_count)
