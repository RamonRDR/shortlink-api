# ShortLink API

**English (primary)** | [Português (Brasil)](README.pt-BR.md) | [Español](README.es.md)

[![CI](https://github.com/RamonRDR/shortlink-api/actions/workflows/ci.yml/badge.svg)](https://github.com/RamonRDR/shortlink-api/actions/workflows/ci.yml)

A security-conscious REST URL shortener built with **Python 3.14, FastAPI,
SQLAlchemy, Alembic, and PostgreSQL**. Designed as a backend portfolio project
to demonstrate REST API design, transactional data integrity, concurrent
requests, automated testing, and security-minded engineering.

**Audience:** backend, Python, automation, and software engineering recruiters.
This `README.md` is the canonical documentation; the Portuguese and Spanish
versions mirror the same features, limitations, and setup instructions.

## Features

- Random unique short links and customizable aliases (HTTP 201; alias conflicts 409).
- Public HTTP 302 redirect for active, unexpired links; other codes return 404.
- Administrative detail, paginated list, active filter, updates and soft deletion.
- Total clicks, UTC daily aggregates, last visit and top-link reporting.
- Constant-time API key authentication and an in-process admin rate limiter.
- Strict HTTP/HTTPS URL validation; private IP targets and credentials rejected.
- OpenAPI documentation at /docs and database readiness at /health.
- Alembic migrations, PostgreSQL integration tests, and GitHub Actions CI.

## Project structure

| Path | Responsibility |
| --- | --- |
| `src/shortlink/main.py` | Routes, dependency injection, and HTTP responses |
| `src/shortlink/schemas.py` | Validated request and response contracts |
| `src/shortlink/services.py` | Short-code and link lifecycle business rules |
| `src/shortlink/repositories.py` | SQLAlchemy queries and atomic redirect updates |
| `src/shortlink/analytics.py` | Aggregated reporting |
| `src/shortlink/security.py`, `rate_limit.py` | Admin authentication and request limits |
| `migrations/` | Database schema versioning with Alembic |
| `tests/` | Automated tests against a disposable PostgreSQL database |
| `.github/workflows/ci.yml` | GitHub Actions quality and integration checks |

## Architecture

    API client
      | X-API-Key (admin only)
      v
    FastAPI routes -> validation / rate limiting -> business services
                                                    |
                                                SQLAlchemy
                                                    |
                                               PostgreSQL
                                               links
                                               daily_clicks
    Browser -> GET /{code} -> atomic counter + daily upsert -> HTTP 302

No Redis, message queue, user-registration service or external tracking service.
Technical choices and trade-offs are documented in [decisions](docs/decisions.md).

## Requirements and installation

Python **3.14**, PostgreSQL **16**, or Docker Engine with Compose.

### Docker Compose (recommended)

    cp .env.example .env
    # Edit .env: choose a strong POSTGRES_PASSWORD and a random
    # SHORTLINK_ADMIN_API_KEY with at least 32 characters.
    docker compose up --build -d
    curl http://localhost:8000/health

The Compose app waits for the database health check and runs Alembic migrations.
Use only test/development credentials. The actual .env is ignored by Git.

### Local Python

Start PostgreSQL and configure these environment variables:

| Variable | Description |
| --- | --- |
| SHORTLINK_DATABASE_URL | postgresql+psycopg://user:password@localhost:5432/shortlink |
| SHORTLINK_ADMIN_API_KEY | Random secret with at least 32 characters |
| SHORTLINK_BASE_URL | Public base URL, for example http://localhost:8000 |
| SHORTLINK_MAX_REQUESTS_PER_MINUTE | Per-process admin request limit; default 60 |

    python3.14 -m venv .venv
    . .venv/bin/activate
    pip install -e ".[dev]"
    alembic upgrade head
    uvicorn shortlink.main:app --reload

Windows PowerShell activation: .venv\Scripts\Activate.ps1.

## Endpoint reference

Public routes include `GET /{code}`, `GET /health`, `GET /docs`, and
`GET /openapi.json`. Link-management and analytics endpoints under
`/api/v1` require the `X-API-Key` request header.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/links` | Create a short link or custom alias |
| `GET` | `/api/v1/links` | List links with `limit`, `offset`, and optional `active` filter |
| `GET` | `/api/v1/links/{code}` | Get administrative link details |
| `PATCH` | `/api/v1/links/{code}` | Update active status or expiry |
| `DELETE` | `/api/v1/links/{code}` | Soft-delete a link (`204`) |
| `GET` | `/api/v1/links/{code}/analytics` | Click totals and UTC daily history (`days`) |
| `GET` | `/api/v1/analytics` | Total links, clicks, and popular links (`top`) |
| `GET` | `/{code}` | Public HTTP `302` redirect when valid |
| `GET` | `/health` | Database health check |
| `GET` | `/docs` | Interactive OpenAPI documentation |

## API requests and responses

Replace YOUR_ADMIN_KEY with the value configured in the environment.

**Create a short link (201):**

    curl -X POST http://localhost:8000/api/v1/links \
      -H "X-API-Key: YOUR_ADMIN_KEY" \
      -H "Content-Type: application/json" \
      -d '{"target_url":"https://example.org/docs","alias":"my-docs"}'

Response fields include:

    {
      "code": "my-docs",
      "target_url": "https://example.org/docs",
      "short_url": "http://localhost:8000/my-docs",
      "is_active": true,
      "expires_at": null,
      "created_at": "2026-11-07T12:00:00Z",
      "updated_at": "2026-11-07T12:00:00Z",
      "click_count": 0,
      "last_accessed_at": null
    }

The timestamps above are illustrative, not measured results.

**Follow the redirect (302):**

    curl -i http://localhost:8000/my-docs

The response has a Location header pointing to the original URL.
Only GET is supported, so avoid curl -I (HEAD).

**Other admin operations:**

    curl -H "X-API-Key: YOUR_ADMIN_KEY" \
      'http://localhost:8000/api/v1/links?limit=20&offset=0&active=true'
    curl -H "X-API-Key: YOUR_ADMIN_KEY" \
      http://localhost:8000/api/v1/links/my-docs
    curl -X PATCH -H "X-API-Key: YOUR_ADMIN_KEY" \
      -H "Content-Type: application/json" -d '{"is_active":false}' \
      http://localhost:8000/api/v1/links/my-docs
    curl -X DELETE -H "X-API-Key: YOUR_ADMIN_KEY" \
      http://localhost:8000/api/v1/links/my-docs
    curl -H "X-API-Key: YOUR_ADMIN_KEY" \
      'http://localhost:8000/api/v1/links/my-docs/analytics?days=30'
    curl -H "X-API-Key: YOUR_ADMIN_KEY" \
      'http://localhost:8000/api/v1/analytics?top=10'

Complete field types, status codes, validation and interactive requests are
provided by OpenAPI at http://localhost:8000/docs. All admin operations require
the API key header; unauthorized requests return 401. Rate-limited requests
return 429 with Retry-After.

## Analytics and privacy

Metrics record total redirect responses prepared by the server, UTC calendar
day counts and last access timestamp. They do not confirm that the destination
loaded successfully. No IP addresses, user agents, or referrers are
stored by the application. Default Docker/Compose commands disable Uvicorn HTTP
access logs; a reverse proxy or hosting platform may still log requests and
must be configured separately. A PostgreSQL transaction keeps aggregate counters
consistent under concurrent redirects.

## Testing and GitHub Actions

With a dedicated test database (its name must end in _test) and configured environment variables:

    ruff check .
    ruff format --check .
    mypy src/shortlink
    alembic upgrade head
    pytest
    python -m build --wheel
    docker build .

GitHub Actions runs Ruff lint/format, mypy, Alembic migration and drift checks,
PostgreSQL integration tests, Python wheel packaging, and Docker image build
on pull requests targeting `main` and pushes to `main`. Workflows use hosted
runners and temporary test credentials; they **do not deploy or publish**.

## Security and known limitations

Link creation and management are admin-only. The redirect target is not
fetched on the server, so there is no server-side request to arbitrary hosts.
The implementation blocks unsafe schemes and non-public IP targets, but it does
not verify domain reputation or guarantee that trusted-looking URLs are safe.
A public anonymous link shortener needs additional anti-abuse controls.

One shared administrator key, process-local rate limiting, no distributed
tracing exporter, no scheduled retention job, no user accounts, no unique
visitor tracking, and no automatic deployment. Deleted codes remain reserved.
See [architecture decisions](docs/decisions.md).

## License

[MIT](LICENSE) Copyright (c) 2026 Ramon Rodriguez.
