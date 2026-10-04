"""HTTP pozivi ka Rezervo API-ju (partner integracija)."""
import json
from typing import Any, Dict, List

import httpx
from fastapi import HTTPException, status

from restaurant.app.config import settings

_FIELD_LABELS = {
    "weekday_open": "Pon-Pet, početak radnog vremena",
    "weekday_close": "Pon-Pet, kraj radnog vremena",
    "weekend_open": "Vikend, početak radnog vremena",
    "weekend_close": "Vikend, kraj radnog vremena",
    "table_count": "Broj stolova",
    "name": "Naziv lokala",
    "email": "Email",
}


def _clean_msg(msg: str) -> str:
    if msg.startswith("Value error, "):
        return msg[len("Value error, ") :]
    return msg


def _format_rezervo_detail(detail: Any) -> str:
    if isinstance(detail, str):
        prefix = "Rezervo nije kreirao lokal: "
        if detail.startswith(prefix):
            inner = detail[len(prefix) :].strip()
            try:
                parsed = json.loads(inner)
                return _format_rezervo_detail(parsed.get("detail", parsed))
            except (json.JSONDecodeError, TypeError, AttributeError):
                pass
        return detail
    if isinstance(detail, list):
        parts: List[str] = []
        for item in detail:
            if not isinstance(item, dict):
                parts.append(str(item))
                continue
            loc = item.get("loc") or []
            field = loc[-1] if loc else ""
            label = _FIELD_LABELS.get(str(field), str(field) if field else "Podaci")
            msg = _clean_msg(str(item.get("msg") or item))
            parts.append(f"{label}: {msg}")
        return " ".join(parts) if parts else "Neispravni podaci lokala."
    return str(detail)


def _webhook_headers() -> Dict[str, str]:
    if not settings.rezervo_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="REZERVO_WEBHOOK_SECRET nije podešen",
        )
    return {"X-Webhook-Secret": settings.rezervo_webhook_secret}


async def create_rezervo_venue(payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{settings.rezervo_api_url.rstrip('/')}/webhooks/venues"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=payload,
                headers=_webhook_headers(),
                timeout=15.0,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Rezervo nije dostupan ({exc})",
        ) from exc
    if response.status_code not in (200, 201):
        try:
            body = response.json()
            detail = _format_rezervo_detail(body.get("detail", body))
        except Exception:
            detail = response.text[:500]
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail,
        )
    data = response.json()
    if not isinstance(data, dict) or "id" not in data:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Neočekivan odgovor Rezerva")
    return data
