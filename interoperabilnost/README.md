# Rezervo - rezervacije stolova

**Rezervo** je aplikacija za **goste**: pregled lokala (demo seed + partner registracije), slanje zahteva za rezervaciju, notifikacije i otkaz. **Odluke o terminu** donosi **restoran partner servis** (inbox + Odobri/Odbij) i vraća ih u Rezervo preko **webhook-a**. Novi zahtevi, izmene `pending` rezervacija i otkazi idu preko **RabbitMQ** (`reservation.created`, `reservation.updated`, `reservation.cancelled`).

*(Radni nazivi u dokumentaciji: Miza, StoLink - isti domen, drugačiji brend.)*

## Zahtevi

- Python **3.9+** (preporučeno 3.11+)

## Instalacija

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r restaurant/requirements.txt
```

## Konfiguracija

Kopiraj `.env.example` u `.env` i podesi:

```bash
cp .env.example .env
cp restaurant/.env.example restaurant/.env
```

Obavezno: **`SECRET_KEY`** (JWT), **`WEBHOOK_SECRET`** (webhook), **`RABBITMQ_URL`** za integracioni demo.

U `restaurant/.env`: **`REZERVO_WEBHOOK_SECRET`** mora biti **isti** kao `WEBHOOK_SECRET`; **`HANDLED_VENUE_IDS`** = id-jevi demo lokala iz seed-a (obično `1,2,3`) - RabbitMQ filter za te lokale; lokali registrovanog osoblja se automatski uključuju u obradu.

**Registracija restorana** uvek kreira **novi** lokal u Rezervu. Ako kreiranje staff naloga padne posle toga, lokal može ostati u Rezervu bez naloga - uklonite ga ručno u bazi/API-ju ako treba (nema DELETE webhook-a).

Podrazumevano: SQLite (`app.db` u korenu, `restaurant/restaurant.db` u `restaurant/`).

## RabbitMQ

```bash
docker compose up -d
```

Management UI: http://127.0.0.1:15672 (guest/guest)

Alternativa bez Dockera: lokalni RabbitMQ (npr. `brew services start rabbitmq`).

## Pokretanje

**Rezervo API:**

```bash
uvicorn app.main:app --reload --port 8000
```

- Swagger: http://127.0.0.1:8000/docs  

**Restoran partner API** (iz korena repozitorijuma):

```bash
uvicorn restaurant.app.main:app --reload --port 8001
```

**Frontend gosta:** `cd frontend && python3 serve.py` → http://127.0.0.1:3000  

**Frontend osoblja:** `cd restaurant/frontend && python3 serve.py` → http://127.0.0.1:3001  

Restoran UI ima **prijavu i registraciju**: registracija kreira novi lokal u Rezervu i nalog osoblja vezan za taj `venue_id`; inbox i zvono vide samo zahtev/obaveštenja tog lokala. **Nema demo staff naloga** - za demo uvek registrujte novi lokal (mora raditi Rezervo API :8000 i isti `WEBHOOK_SECRET`).

Pri startu Rezerva automatski nastaju **tri demo lokala** ako baza nema venue redove.

### Demo scenariji

1. **Samo Rezervo (bez RabbitMQ)**  
   Registruj gosta → izaberi demo lokal → pošalji zahtev. Status ostaje `pending` dok ne pozoveš webhook ručno (Swagger `POST /webhooks/reservation-status`) ili ne uključiš restoran servis.

2. **Dva servisa (preporučeno za odbranu)**  
   RabbitMQ + oba API-ja + oba UI-ja. Gost rezerviše → inbox u restoranu → **Odobri** (unesite broj stola) / **Odbij** → gost vidi potvrdu i isti broj stola. Otkaz gosta → poruka osoblju u restoran servisu.

3. **Testovi**  
   `pytest tests/ -q`

Brza priprema: `./scripts/start-integration-demo.sh`

## Integracija

| Kanal | Opis |
|--------|------|
| REST JSON | `/auth`, `GET /venues`, `/reservations`, `/notifications` |
| Webhook | `POST /webhooks/reservation-status` - header **`X-Webhook-Secret`**; pri potvrdi obavezno **`table_number`** (1 do broja stolova lokala) |
| RabbitMQ | Redovi **`reservation.created`**, **`reservation.updated`**, **`reservation.cancelled`** |

Detalji: [docs/tehnologije.md](docs/tehnologije.md)

## Seminarski rad (.docx)

Izvorni tekst: [docs/seminarski_rad.md](docs/seminarski_rad.md) (usklađen sa trenutnom implementacijom).

```bash
pip install -r requirements-docs.txt
python scripts/generate_seminarski_docx.py
```

## Struktura projekta

```
app/                 # Rezervo (gost)
restaurant/          # partner servis
frontend/            # gost UI
docs/
scripts/
docker-compose.yml
```

## Migracije (Alembic)

```bash
alembic upgrade head
```

Za čist dev: obriši `app.db` i restartuj API (seed lokala pri praznoj bazi).

## Testovi

```bash
pytest tests/ -q
```

Smoke testovi: seed lokali, radno vreme, webhook potvrda, dodela stola, otkaz gosta, idempotentnost webhook-a.
