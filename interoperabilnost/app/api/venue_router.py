"""API za lokale - javna lista (seed pri startu)."""
from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.venue import PublicVenueRead, VenueRead
from app.services import get_venue_service, VenueService, VenueNotFoundError

router = APIRouter(prefix="/venues", tags=["venues"])


@router.get("/", response_model=list[PublicVenueRead])
async def list_venues(service: VenueService = Depends(get_venue_service)):
    """Lista aktivnih lokala (javno)."""
    return await service.list_all()


@router.get("/{venue_id}", response_model=PublicVenueRead)
async def get_venue(venue_id: int, service: VenueService = Depends(get_venue_service)):
    try:
        return await service.get_by_id(venue_id)
    except VenueNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
