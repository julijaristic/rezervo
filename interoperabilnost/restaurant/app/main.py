"""Restoran partner servis - port 8001."""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from restaurant.app.api.auth_router import router as auth_router
from restaurant.app.api.inbox_router import router as inbox_router
from restaurant.app.api.notification_router import router as notification_router
from restaurant.app.config import settings
from restaurant.app.database import init_db
from restaurant.app.messaging.consumer import run_reservation_consumer
from restaurant.app.models import IncomingReservation, Staff, StaffNotification  # noqa: F401
from restaurant.app.services.seed import ensure_default_staff

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await ensure_default_staff()
    stop_event = asyncio.Event()
    consumer_task = asyncio.create_task(run_reservation_consumer(stop_event))
    logger.info(
        "Restoran servis spreman. Handled venue_ids=%s",
        settings.parsed_handled_venue_ids(),
    )
    yield
    stop_event.set()
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Restoran partner API",
    description="Spoljni sistem lokala - RabbitMQ inbox + webhook ka Rezervu",
    version="0.1.0",
    lifespan=lifespan,
)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(inbox_router)
app.include_router(notification_router)


@app.get("/")
async def root() -> dict:
    return {
        "message": "Restoran partner servis. Dokumentacija: /docs",
        "handled_venue_ids": sorted(settings.parsed_handled_venue_ids()),
    }
