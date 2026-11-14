# Backend development

The backend is a Django modular monolith. Django settings and server entry
points live in `config/`; reusable cross-cutting API functionality lives in
`apps/common/`; the foundational custom user model lives in `apps/accounts/`.
No tenant membership, RBAC, or student-domain workflows are implemented yet.

## Requirements

- Python 3.14
- PostgreSQL for local development and deployment
- SQLite is used only by the isolated test settings

From `backend/`, create an environment and install the pinned dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements\development.txt
```

The repository-root `.env.example` is the canonical local environment template.
Copy it to `.env` at the repository root and adjust the local database values.
Never use its development values in a deployed environment.

## Settings and environment

- `config.settings.base` contains shared apps, middleware, API defaults,
  PostgreSQL connection settings, static/media paths, logging, and timezone.
- `config.settings.development` enables local development defaults and local
  frontend CORS/CSRF origins.
- `config.settings.production` requires a non-placeholder secret and explicit
  allowed hosts, disables debug, and enables HTTPS-related security settings.
- `config.settings.test` uses an in-memory SQLite database and a test-only key.

Run production checks only with deployment-specific environment variables set:

```powershell
$env:DJANGO_SECRET_KEY = "<strong unique secret>"
$env:DJANGO_ALLOWED_HOSTS = "api.example.com"
python manage.py check --deploy --settings=config.settings.production
```

## Common commands

Run commands from `backend/`:

```powershell
python manage.py check
python manage.py migrate
python -m pytest
ruff check .
ruff format --check .
python manage.py makemigrations --check --dry-run
python manage.py spectacular --file openapi.yaml --validate
```

Pytest selects `config.settings.test` from `pyproject.toml`; its database is
isolated from the configured PostgreSQL service. Development and production
settings use PostgreSQL. Create and review migrations deliberately, and do not
change `AUTH_USER_MODEL` casually now that its first migration exists.

## API integration

- Local backend base URL: `http://localhost:8000`
- Versioned API prefix: `/api/v1/`
- Frontend base URL variable: `NEXT_PUBLIC_API_BASE_URL`, normally
  `http://localhost:8000/api/v1`
- Configure `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` with explicit
  frontend origins; do not use wildcard origins.
- Liveness: `GET /api/v1/health/` returns
  `{"status":"ok","service":"student-management-api"}` and does not query the
  database.
- Database readiness: `GET /api/v1/health/ready/` checks the database and
  returns HTTP 503 with a generic response if it is unavailable.
- OpenAPI schema and Swagger UI: `/api/schema/` and `/api/docs/`. Both require
  an authenticated staff user.

The health endpoint intentionally does not prove database readiness; use the
readiness endpoint for that purpose. Neither response exposes connection
details or exception messages.
