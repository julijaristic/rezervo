"""Bazni repozitorijum - drži sesiju i zajedničke operacije."""
from typing import Generic, Optional, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Bazna klasa za repozitorijume. Sesija se prosleđuje spolja (dependency)."""

    def __init__(self, session: AsyncSession, model: type[ModelT]):
        self._session = session
        self._model = model

    async def get_by_id(self, id: int) -> Optional[ModelT]:
        result = await self._session.execute(
            select(self._model).where(self._model.id == id)
        )
        return result.scalar_one_or_none()

    async def add(self, entity: ModelT) -> ModelT:
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity
