"""Smoke testovi glavnih poslovnih pravila (gost + webhook, seed lokali)."""
from datetime import date, timedelta
from typing import Optional


def _future_weekday(days_ahead: int = 10) -> str:
    d = date.today() + timedelta(days=days_ahead)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d.isoformat()


def _register(client, username: str):
    client.post(
        "/auth/register",
        json=dict(
            username=username,
            password="secret1",
            name=username,
            phone="1",
            email=f"{username}@example.com",
        ),
    )


def _token(client, username: str) -> str:
    return client.post("/auth/login", json=dict(username=username, password="secret1")).json()[
        "access_token"
    ]


def _seeded_venue(client, name: Optional[str] = None) -> dict:
    venues = client.get("/venues/").json()
    assert venues, "Očekivani demo lokali iz seed-a"
    if name:
        match = next((v for v in venues if v["name"] == name), None)
        assert match is not None, f"Lokal {name!r} nije u seed-u"
        return match
    return venues[0]


def _webhook_confirm(client, reservation_id: int, table_number: int = 5):
    return client.post(
        "/webhooks/reservation-status",
        json=dict(
            reservation_id=reservation_id,
            status="confirmed",
            message="Potvrđeno partnerom",
            external_id=f"test-{reservation_id}",
            table_number=table_number,
        ),
        headers={"X-Webhook-Secret": "whsec-test"},
    )


def test_table_only_on_confirm_via_webhook(client):
    _register(client, "gst1")
    gh = {"Authorization": "Bearer " + _token(client, "gst1")}
    future = _future_weekday(10)
    vid = _seeded_venue(client)["id"]
    r1 = client.post(
        "/reservations/",
        json=dict(venue_id=vid, date=future, start_time="18:00", end_time="20:00", guest_count=2),
        headers=gh,
    ).json()
    assert r1["table_number"] is None
    wh = _webhook_confirm(client, r1["id"])
    assert wh.status_code == 200
    r1b = client.get(f"/reservations/{r1['id']}", headers=gh).json()
    assert r1b["table_number"] is not None
    notifs = client.get("/notifications/", headers=gh).json()
    assert any(n["kind"] == "confirmed" for n in notifs)


def test_opening_hours_rejected(client):
    _register(client, "gst3")
    gh = {"Authorization": "Bearer " + _token(client, "gst3")}
    future = _future_weekday(12)
    kafe = _seeded_venue(client, "Demo Kafe")
    bad = client.post(
        "/reservations/",
        json=dict(
            venue_id=kafe["id"],
            date=future,
            start_time="09:00",
            end_time="10:30",
            guest_count=2,
        ),
        headers=gh,
    )
    assert bad.status_code == 400


def test_guest_can_cancel_confirmed(client):
    _register(client, "gst4")
    gh = {"Authorization": "Bearer " + _token(client, "gst4")}
    future = _future_weekday(13)
    vid = _seeded_venue(client)["id"]
    r = client.post(
        "/reservations/",
        json=dict(venue_id=vid, date=future, start_time="18:00", end_time="20:00", guest_count=2),
        headers=gh,
    ).json()
    _webhook_confirm(client, r["id"])
    cancel = client.delete(f"/reservations/{r['id']}", headers=gh)
    assert cancel.status_code == 200
    updated = client.get(f"/reservations/{r['id']}", headers=gh).json()
    assert updated["status"] == "cancelled"
    notifs = client.get("/notifications/", headers=gh).json()
    assert any(n["kind"] == "cancelled" and n["reservation_id"] == r["id"] for n in notifs)


def test_public_venues_hide_owner_id(client):
    venues = client.get("/venues/").json()
    assert venues
    for v in venues:
        assert "owner_id" not in v


def test_confirm_assigns_table_number(client):
    _register(client, "gst5")
    gh = {"Authorization": "Bearer " + _token(client, "gst5")}
    future = _future_weekday(14)
    vid = _seeded_venue(client)["id"]
    r1 = client.post(
        "/reservations/",
        json=dict(venue_id=vid, date=future, start_time="18:00", end_time="19:00", guest_count=2),
        headers=gh,
    ).json()
    _webhook_confirm(client, r1["id"])
    confirmed = client.get(f"/reservations/{r1['id']}", headers=gh).json()
    assert confirmed["table_number"] == 5


def test_confirm_requires_table_number(client):
    _register(client, "gst5b")
    gh = {"Authorization": "Bearer " + _token(client, "gst5b")}
    future = _future_weekday(16)
    vid = _seeded_venue(client)["id"]
    r = client.post(
        "/reservations/",
        json=dict(venue_id=vid, date=future, start_time="18:00", end_time="20:00", guest_count=2),
        headers=gh,
    ).json()
    bad = client.post(
        "/webhooks/reservation-status",
        json=dict(reservation_id=r["id"], status="confirmed", message="bez stola"),
        headers={"X-Webhook-Secret": "whsec-test"},
    )
    assert bad.status_code == 422


def test_webhook_idempotent(client):
    _register(client, "gst6")
    gh = {"Authorization": "Bearer " + _token(client, "gst6")}
    future = _future_weekday(15)
    vid = _seeded_venue(client, "Demo Restoran")["id"]
    r = client.post(
        "/reservations/",
        json=dict(venue_id=vid, date=future, start_time="18:00", end_time="20:00", guest_count=2),
        headers=gh,
    ).json()
    first = _webhook_confirm(client, r["id"], table_number=10)
    assert first.status_code == 200, first.text
    before = len(client.get("/notifications/", headers=gh).json())
    wh = client.post(
        "/webhooks/reservation-status",
        json=dict(
            reservation_id=r["id"],
            status="confirmed",
            message="dup",
            table_number=10,
        ),
        headers={"X-Webhook-Secret": "whsec-test"},
    )
    assert wh.status_code == 200, wh.text
    after = len(client.get("/notifications/", headers=gh).json())
    assert after == before


def test_seeded_venues_public_list(client):
    venues = client.get("/venues/").json()
    names = {v["name"] for v in venues}
    assert "Demo Restoran" in names
    assert len(venues) >= 3


def test_confirm_rejects_table_above_venue_capacity(client):
    created = client.post(
        "/webhooks/venues",
        json=dict(
            name="Mali Lokal",
            address="Test 2",
            city="Beograd",
            country="RS",
            phone="+381998",
            email="mali@lokal.rs",
            weekday_open="10:00",
            weekday_close="22:00",
            weekend_open="10:00",
            weekend_close="22:00",
            table_count=3,
        ),
        headers={"X-Webhook-Secret": "whsec-test"},
    )
    assert created.status_code == 201, created.text
    vid = created.json()["id"]
    _register(client, "gst_cap")
    gh = {"Authorization": "Bearer " + _token(client, "gst_cap")}
    future = _future_weekday(17)
    r = client.post(
        "/reservations/",
        json=dict(venue_id=vid, date=future, start_time="18:00", end_time="20:00", guest_count=2),
        headers=gh,
    ).json()
    bad = client.post(
        "/webhooks/reservation-status",
        json=dict(
            reservation_id=r["id"],
            status="confirmed",
            message="prevelik sto",
            table_number=5,
        ),
        headers={"X-Webhook-Secret": "whsec-test"},
    )
    assert bad.status_code == 400


def test_partner_webhook_creates_venue_visible_to_guests(client):
    created = client.post(
        "/webhooks/venues",
        json=dict(
            name="Partner Novi Lokal",
            address="Test 1",
            city="Beograd",
            country="RS",
            phone="+381999",
            email="novi@lokal.rs",
            weekday_open="10:00",
            weekday_close="22:00",
            weekend_open="10:00",
            weekend_close="22:00",
        ),
        headers={"X-Webhook-Secret": "whsec-test"},
    )
    assert created.status_code == 201, created.text
    vid = created.json()["id"]
    names = {v["name"] for v in client.get("/venues/").json()}
    assert "Partner Novi Lokal" in names
    assert client.get(f"/venues/{vid}").status_code == 200
