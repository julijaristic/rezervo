"""Testovi restoran partner servisa."""
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REST_DB = Path("/tmp/restaurant_pytest.db")


def _seed_test_staff() -> None:
    import asyncio

    from sqlalchemy import select

    from restaurant.app.core.security import hash_password
    from restaurant.app.database import async_session_maker
    from restaurant.app.models.staff_model import Staff

    async def _run() -> None:
        async with async_session_maker() as session:
            existing = await session.execute(
                select(Staff).where(Staff.username == "stafftest")
            )
            if existing.scalar_one_or_none() is not None:
                return
            session.add(
                Staff(
                    username="stafftest",
                    password_hash=hash_password("staffpass123"),
                    display_name="Test osoblje",
                    venue_id=1,
                    venue_name="Test lokal 1",
                )
            )
            await session.commit()

    asyncio.run(_run())


@pytest.fixture(scope="module")
def restaurant_client():
    if REST_DB.exists():
        REST_DB.unlink()
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{REST_DB}"
    os.environ["SECRET_KEY"] = "restaurant-test-secret-key-32-chars-min"
    os.environ["RABBITMQ_URL"] = ""
    os.environ["HANDLED_VENUE_IDS"] = "1,2"
    os.environ["REZERVO_API_URL"] = "http://127.0.0.1:8000"
    os.environ["REZERVO_WEBHOOK_SECRET"] = "whsec-test"

    from restaurant.app.main import app

    with TestClient(app) as c:
        _seed_test_staff()
        yield c

    if REST_DB.exists():
        REST_DB.unlink()


def _staff_token(client: TestClient) -> str:
    r = client.post("/auth/login", json={"username": "stafftest", "password": "staffpass123"})
    assert r.status_code == 200
    return r.json()["access_token"]


def test_ingest_idempotent(restaurant_client):
    import asyncio

    from restaurant.app.services.inbox_service import ingest_reservation_event

    body = {
        "reservation_id": 9991,
        "venue_id": 1,
        "user_id": 2,
        "guest_count": 3,
        "date": "2026-12-01",
        "start_time": "18:00:00",
        "end_time": "20:00:00",
        "status": "pending",
    }
    first = asyncio.run(ingest_reservation_event(body))
    second = asyncio.run(ingest_reservation_event(body))
    assert first is True
    assert second is False


def test_inbox_and_webhook_mock(restaurant_client, monkeypatch):
    import restaurant.app.api.inbox_router as inbox_router_mod
    import restaurant.app.services.inbox_service as inbox_mod

    async def fake_send(session, row, status, message, table_number=None):
        row.decision_status = "sent_confirmed" if status == "confirmed" else "sent_rejected"
        row.external_id = f"REST-inbox-{row.id}"
        if status == "confirmed" and table_number is not None:
            row.table_number = int(table_number)
        return True, None, {"ok": True, "table_number": table_number}

    monkeypatch.setattr(inbox_router_mod, "send_decision_to_rezervo", fake_send)

    import asyncio

    body = {
        "reservation_id": 42,
        "venue_id": 1,
        "user_id": 1,
        "guest_count": 2,
        "date": "2026-12-02",
        "start_time": "19:00:00",
        "end_time": "21:00:00",
        "status": "pending",
    }
    asyncio.run(inbox_mod.ingest_reservation_event(body))

    token = _staff_token(restaurant_client)
    headers = {"Authorization": f"Bearer {token}"}
    inbox = restaurant_client.get("/inbox/", headers=headers)
    assert inbox.status_code == 200
    rows = [r for r in inbox.json() if r["rezervo_reservation_id"] == 42]
    assert len(rows) == 1
    inbox_id = rows[0]["id"]

    approve = restaurant_client.post(
        f"/inbox/{inbox_id}/approve",
        headers=headers,
        json={"table_number": 12},
    )
    assert approve.status_code == 200
    assert approve.json()["decision_status"] == "sent_confirmed"


def test_ingest_updated_modifies_inbox(restaurant_client):
    import asyncio

    from restaurant.app.services.inbox_service import (
        ingest_reservation_event,
        ingest_reservation_updated,
    )

    body = {
        "reservation_id": 888,
        "venue_id": 1,
        "user_id": 1,
        "guest_count": 2,
        "date": "2026-12-04",
        "start_time": "18:00:00",
        "end_time": "20:00:00",
        "status": "pending",
    }
    asyncio.run(ingest_reservation_event(body))
    asyncio.run(
        ingest_reservation_updated(
            {
                "reservation_id": 888,
                "venue_id": 1,
                "guest_count": 4,
                "date": "2026-12-05",
                "start_time": "19:00:00",
                "end_time": "21:00:00",
                "status": "pending",
            }
        )
    )

    token = _staff_token(restaurant_client)
    headers = {"Authorization": f"Bearer {token}"}
    inbox = restaurant_client.get("/inbox/", headers=headers).json()
    row = next(r for r in inbox if r["rezervo_reservation_id"] == 888)
    assert row["slot_date"] == "2026-12-05"
    assert row["guest_count"] == 4


def test_ingest_cancelled_notifies_staff(restaurant_client):
    import asyncio

    from restaurant.app.services.inbox_service import (
        ingest_reservation_cancelled,
        ingest_reservation_event,
    )

    body = {
        "reservation_id": 777,
        "venue_id": 1,
        "user_id": 1,
        "guest_count": 2,
        "date": "2026-12-03",
        "start_time": "18:00:00",
        "end_time": "20:00:00",
        "status": "pending",
    }
    asyncio.run(ingest_reservation_event(body))
    asyncio.run(
        ingest_reservation_cancelled(
            {
                "reservation_id": 777,
                "venue_id": 1,
                "date": "2026-12-03",
                "start_time": "18:00:00",
                "end_time": "20:00:00",
                "status": "cancelled",
            }
        )
    )

    token = _staff_token(restaurant_client)
    headers = {"Authorization": f"Bearer {token}"}
    inbox = restaurant_client.get("/inbox/", headers=headers).json()
    row = next(r for r in inbox if r["rezervo_reservation_id"] == 777)
    assert row["rezervo_status"] == "cancelled"

    notifs = restaurant_client.get("/notifications/", headers=headers).json()
    assert any(n["kind"] == "reservation_cancelled" for n in notifs)


def test_inbox_scoped_to_staff_venue(restaurant_client, monkeypatch):
    import asyncio

    import restaurant.app.api.auth_router as auth_router_mod
    from restaurant.app.services.inbox_service import ingest_reservation_event

    async def fake_create(_payload):
        return {"id": 2, "name": "Lokal 2"}

    monkeypatch.setattr(auth_router_mod, "register_new_venue_in_rezervo", fake_create)

    reg = restaurant_client.post(
        "/auth/register",
        json={
            "username": "kafe_mgr",
            "password": "secret12",
            "new_venue": {
                "name": "Test Kafe",
                "address": "A",
                "city": "BG",
                "country": "RS",
                "phone": "1",
                "email": "k@k.rs",
            },
        },
    )
    assert reg.status_code == 201, reg.text
    token_kafe = reg.json()["access_token"]
    headers_kafe = {"Authorization": f"Bearer {token_kafe}"}

    asyncio.run(
        ingest_reservation_event(
            {
                "reservation_id": 5001,
                "venue_id": 1,
                "user_id": 1,
                "guest_count": 2,
                "date": "2026-12-10",
                "start_time": "18:00:00",
                "end_time": "20:00:00",
                "status": "pending",
            }
        )
    )
    asyncio.run(
        ingest_reservation_event(
            {
                "reservation_id": 5002,
                "venue_id": 2,
                "user_id": 1,
                "guest_count": 2,
                "date": "2026-12-10",
                "start_time": "19:00:00",
                "end_time": "21:00:00",
                "status": "pending",
            }
        )
    )

    inbox_kafe = restaurant_client.get("/inbox/", headers=headers_kafe).json()
    ids = {r["rezervo_reservation_id"] for r in inbox_kafe}
    assert 5002 in ids
    assert 5001 not in ids

    token_staff1 = _staff_token(restaurant_client)
    inbox_r1 = restaurant_client.get(
        "/inbox/", headers={"Authorization": f"Bearer {token_staff1}"}
    ).json()
    ids_r1 = {r["rezervo_reservation_id"] for r in inbox_r1}
    assert 5001 in ids_r1
    assert 5002 not in ids_r1


def test_partner_register_creates_venue_in_rezervo(client, restaurant_client, monkeypatch):
    import asyncio

    import restaurant.app.api.auth_router as auth_router_mod

    venue_name = "E2E Partner Lokal"

    async def create_via_rezervo_webhook(payload):
        loop = asyncio.get_running_loop()

        def _post():
            return client.post(
                "/webhooks/venues",
                json=payload,
                headers={"X-Webhook-Secret": "whsec-test"},
            )

        response = await loop.run_in_executor(None, _post)
        assert response.status_code in (200, 201), response.text
        return response.json()

    monkeypatch.setattr(auth_router_mod, "register_new_venue_in_rezervo", create_via_rezervo_webhook)

    reg = restaurant_client.post(
        "/auth/register",
        json={
            "username": "e2e_partner",
            "password": "secret12",
            "new_venue": {
                "name": venue_name,
                "address": "E2E 1",
                "city": "Beograd",
                "country": "RS",
                "phone": "+381111",
                "email": "e2e@partner.rs",
                "weekday_open": "10:00",
                "weekday_close": "22:00",
                "weekend_open": "10:00",
                "weekend_close": "22:00",
                "table_count": 12,
            },
        },
    )
    assert reg.status_code == 201, reg.text
    me = restaurant_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {reg.json()['access_token']}"},
    ).json()
    assert me["table_count"] == 12
    names = {v["name"] for v in client.get("/venues/").json()}
    assert venue_name in names


def test_register_rejects_invalid_opening_hours(restaurant_client):
    reg = restaurant_client.post(
        "/auth/register",
        json={
            "username": "bad_hours",
            "password": "secret12",
            "new_venue": {
                "name": "Bad Hours",
                "address": "X",
                "city": "Beograd",
                "country": "RS",
                "phone": "+381",
                "email": "bad@hours.rs",
                "weekday_open": "10:00",
                "weekday_close": "00:00",
                "weekend_open": "10:00",
                "weekend_close": "22:00",
                "table_count": 10,
            },
        },
    )
    assert reg.status_code == 422


def test_inbox_date_filter(restaurant_client):
    import asyncio

    from restaurant.app.services.inbox_service import ingest_reservation_event

    asyncio.run(
        ingest_reservation_event(
            {
                "reservation_id": 7001,
                "venue_id": 1,
                "user_id": 1,
                "guest_count": 2,
                "date": "2026-11-01",
                "start_time": "18:00:00",
                "end_time": "20:00:00",
                "status": "pending",
            }
        )
    )
    asyncio.run(
        ingest_reservation_event(
            {
                "reservation_id": 7002,
                "venue_id": 1,
                "user_id": 1,
                "guest_count": 2,
                "date": "2026-12-01",
                "start_time": "18:00:00",
                "end_time": "20:00:00",
                "status": "pending",
            }
        )
    )
    token = _staff_token(restaurant_client)
    headers = {"Authorization": f"Bearer {token}"}
    nov = restaurant_client.get("/inbox/?date=2026-11-01", headers=headers)
    assert nov.status_code == 200
    ids = {r["rezervo_reservation_id"] for r in nov.json()}
    assert 7001 in ids
    assert 7002 not in ids
    all_rows = restaurant_client.get("/inbox/", headers=headers).json()
    assert 7001 in {r["rezervo_reservation_id"] for r in all_rows}
    assert 7002 in {r["rezervo_reservation_id"] for r in all_rows}


def test_reject_inbox_with_reason(restaurant_client, monkeypatch):
    import asyncio

    import restaurant.app.api.inbox_router as inbox_router_mod
    import restaurant.app.services.inbox_service as inbox_mod

    captured = {}

    async def fake_send(session, row, status, message, table_number=None, rejection_reason=None):
        captured["message"] = message
        captured["rejection_reason"] = rejection_reason
        row.decision_status = "sent_rejected"
        return True, None, {"ok": True}

    monkeypatch.setattr(inbox_router_mod, "send_decision_to_rezervo", fake_send)

    asyncio.run(
        inbox_mod.ingest_reservation_event(
            {
                "reservation_id": 7777,
                "venue_id": 1,
                "user_id": 1,
                "guest_count": 2,
                "date": "2026-12-03",
                "start_time": "19:00:00",
                "end_time": "21:00:00",
                "status": "pending",
            }
        )
    )
    token = _staff_token(restaurant_client)
    headers = {"Authorization": f"Bearer {token}"}
    rows = [r for r in restaurant_client.get("/inbox/", headers=headers).json() if r["rezervo_reservation_id"] == 7777]
    assert rows
    reject = restaurant_client.post(
        f"/inbox/{rows[0]['id']}/reject",
        headers=headers,
        json={"reason": "Pun kapacitet"},
    )
    assert reject.status_code == 200
    assert "Pun kapacitet" in captured["message"]
    assert captured["rejection_reason"] == "Pun kapacitet"
