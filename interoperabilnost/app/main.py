"""FastAPI aplikacija - ulazna tačka."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.errors import reservation_error_to_http
from app.services.exceptions import ReservationError

from app.api.auth_router import router as auth_router
from app.api.reservation_router import router as reservation_router
from app.api.notification_router import router as notification_router
from app.api.venue_router import router as venue_router
from app.api.webhook_router import router as webhook_router
from app.config import settings
from app.database import init_db
from app.services.seed_data import ensure_demo_data

# Uvoz svih modela da se tabele registruju pre init_db()
from app.models import Notification, Reservation, User, Venue  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle: kreiranje tabela pri startu."""
    await init_db()
    await ensure_demo_data()
    yield
    # cleanup ako treba


app = FastAPI(
    title="Rezervo API",
    description="Rezervo - rezervacije stolova (FastAPI, SQLAlchemy, integracije)",
    version="0.1.0",
    lifespan=lifespan,
)


@app.exception_handler(ReservationError)
async def reservation_error_handler(_request: Request, exc: ReservationError) -> JSONResponse:
    http_exc = reservation_error_to_http(exc)
    return JSONResponse(status_code=http_exc.status_code, content={"detail": http_exc.detail})

# CORS - dozvoli zahteve sa frontenda (drugi domen/port)
origins = [o.strip() for o in settings.cors_origins.split(",")] if settings.cors_origins != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=(origins != ["*"]),  # sa "*" credentials moraju biti False (CORS spec)
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(reservation_router)
app.include_router(venue_router)
app.include_router(notification_router)
app.include_router(webhook_router)


@app.get("/")
async def root() -> dict:
    return {"message": "API radi. Dokumentacija: /docs"}
