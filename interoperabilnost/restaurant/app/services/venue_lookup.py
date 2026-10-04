"""Lokali u Rezervu - lista, provera i kreiranje pri registraciji restorana."""
from typing import Any, Dict, Set
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from restaurant.app.config import settings
from restaurant.app.models.staff_model import Staff
from restaurant.app.services.rezervo_client import create_rezervo_venue


async def accepted_venue_ids_for_messaging(session: AsyncSession) -> Set[int]:
    """Redovi RabbitMQ za lokale iz HANDLED_VENUE_IDS + svi venue_id registrovanog osoblja."""
    ids = set(settings.parsed_handled_venue_ids())
    result = await session.execute(select(Staff.venue_id).distinct())
    for row in result.all():
        ids.add(int(row[0]))
    return ids


async def register_new_venue_in_rezervo(venue_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Kreira lokal u Rezervu preko partner webhook-a."""
    return await create_rezervo_venue(venue_payload)
