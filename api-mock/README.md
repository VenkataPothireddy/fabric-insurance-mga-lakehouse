# Mock IMS API

FastAPI service that stands in for Vertafore MGA Systems' API. Loads the
Phase 1 synthetic CSVs into memory at startup and serves them as JSON over HTTP.

## Why this exists

Citadel's real IMS API is not accessible to this prototype. The bronze layer
must prove it can ingest from APIs, not just files — that's a stated requirement
in the Data Warehouse Engineer JD. This mock is the API the bronze API-ingestion
notebook calls.

## Setup

From the repo root:

```bash
cd api-mock
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app:app --reload --port 8000
```

Then open:
- http://localhost:8000/         — health check
- http://localhost:8000/docs     — interactive Swagger UI
- http://localhost:8000/policies — first page of policies as JSON

## Endpoints

| Method | Path                  | Notes                                              |
|--------|-----------------------|----------------------------------------------------|
| GET    | `/`                   | Health + endpoint listing                          |
| GET    | `/policies`           | `limit`, `offset`, `updated_since`, `program_code` |
| GET    | `/policies/{id}`      | Single policy or 404                               |
| GET    | `/claims`             | `limit`, `offset`, `updated_since`                 |
| GET    | `/claims/{id}`        | Single claim or 404                                |
| GET    | `/agents`             | `limit`, `offset`                                  |
| GET    | `/agents/{id}`        | Single agent or 404                                |

## What a real Vertafore API would add

Intentionally out of scope for the prototype:

- **Authentication** — API key, OAuth 2.0, or mTLS
- **Rate limiting** — typically 60–600 req/min per client
- **Webhooks** — push notifications on policy changes instead of polling
- **Schema versioning** — `/v1/policies`, `/v2/policies` with deprecation headers
- **Backed by a real DB** — Postgres or SQL Server, not in-memory pandas