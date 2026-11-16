# Backend development

The backend is a Django modular monolith. Django settings and server entry
points live in `config/`; reusable cross-cutting API functionality lives in
`apps/common/`; the foundational custom user model lives in `apps/accounts/`.
No tenant membership, RBAC, or student-domain workflows are implemented yet.

## Requirements

- Python 3.14
- PostgreSQL for local development; production hosting is not configured
- SQLite is used by the default isolated test settings; PostgreSQL test
  settings are available for CI and database-specific local verification

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
- `config.settings.test_postgres` keeps the test settings but uses the
  PostgreSQL database configuration from `config.settings.base`.

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
isolated from the configured PostgreSQL service. Use
`python -m pytest --ds=config.settings.test_postgres -vv` with PostgreSQL
environment variables set to run the suite against PostgreSQL, as CI does.
Development and production settings use PostgreSQL. Create and review
migrations deliberately, and do not change `AUTH_USER_MODEL` casually now
that its first migration exists. See
[`../docs/engineering/CI.md`](../docs/engineering/CI.md) for workflow details
and complete local reproduction instructions.

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

## Browser session authentication

The backend uses Django's database-backed sessions and DRF
`SessionAuthentication`; it does not issue JWTs or expose session identifiers
in JSON. Authentication identifies a global user only. Institution
memberships, tenant resolution, tenant authorization, registration, email
verification, password recovery, MFA, and account/device management remain
unimplemented.

Versioned endpoints:

| Method | Path | Behavior |
|---|---|---|
| `GET` | `/api/v1/auth/csrf/` | Returns `{"csrfToken":"..."}` and sets the CSRF cookie |
| `POST` | `/api/v1/auth/login/` | Accepts `{"email":"...","password":"..."}`; success returns `{"user":{"id":"...","email":"..."}}`; invalid credentials return the same generic `401` |
| `POST` | `/api/v1/auth/logout/` | Requires an authenticated session and CSRF proof; invalidates the current session |
| `GET` | `/api/v1/auth/me/` | Returns only the authenticated user's UUID and email |

Unauthenticated requests to protected endpoints are denied (`403` with DRF's
session authentication). Login credential failures are `401`; missing or
invalid CSRF proof is `403`; malformed login input is `400`; throttled login
attempts return `429`. The login response deliberately does not distinguish an
unknown email, wrong password, or inactive account.

The frontend API client includes cookies on requests and obtains a fresh
masked CSRF token before each unsafe request, submitting it in `X-CSRFToken`.
The CSRF endpoint also returns the token in JSON because both the session and
CSRF cookies are `HttpOnly`. Do not copy session identifiers or passwords
into browser storage. The existing `NEXT_PUBLIC_API_BASE_URL` is a public URL,
not a secret.

### Cookie, CSRF, and deployment assumptions

- Prefer serving Next.js and Django under the same origin. The local default
  uses `http://localhost:3000` for Next.js and `http://localhost:8000` for
  Django; development explicitly allows those origins with credentialed CORS.
  Use the same hostname for both local URLs (`localhost` or `127.0.0.1`);
  browsers treat those hostnames as different sites for `SameSite` cookies.
- If deployment uses separate origins, configure exact
  `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`; in production only set
  `CORS_ALLOW_CREDENTIALS=True` when required and never combine it with
  wildcard origins. The current cookies use `SameSite=Lax`; cross-site
  deployments are not supported by this configuration.
- Session and CSRF cookies are host-only (`*_COOKIE_DOMAIN=None`), use path
  `/`, and `SameSite=Lax`. Both are `Secure` in production and the session
  cookie is always `HttpOnly`. The CSRF cookie is also `HttpOnly`; frontend
  code must use the CSRF endpoint response, not read the cookie.
- Production redirects to HTTPS and enables secure cookies. The reverse proxy
  must overwrite `X-Forwarded-Proto` with the actual client protocol before
  Django trusts `SECURE_PROXY_SSL_HEADER`; do not expose Django directly to
  untrusted forwarded headers. The production environment must set an
  explicit secret, allowed hosts, and appropriate trusted origins.
- `SESSION_COOKIE_AGE` defaults to a one-hour sliding inactivity expiry;
  authenticated sessions also expire after the 12-hour absolute maximum in
  `AUTH_SESSION_ABSOLUTE_AGE`. `SESSION_SAVE_EVERY_REQUEST` refreshes the
  inactivity window. Schedule Django's `clearsessions` management command to
  remove expired database session rows in deployed environments.
- CSRF protection applies to login and to unsafe requests authenticated by
  `SessionAuthentication`; the CSRF failure response is generic. Do not
  disable CSRF middleware or exempt future cookie-authenticated write APIs.

### Login throttling and remaining limitations

Login uses DRF `ScopedRateThrottle`, defaulting to `AUTH_LOGIN_RATE=10/minute`
per client IP. The repository has no shared cache or distributed rate-limiting
service; Django's default local-memory cache is process-local, so multiple
workers do not share counters. IP throttling also does not stop distributed
credential stuffing and depends on a trusted proxy sanitizing forwarded IP
headers. Treat it as a basic abuse control, not robust production rate
limiting; configure and verify a shared cache/gateway policy before a
multi-worker production deployment. No account lockout or password recovery
workflow is implemented.

### Run authentication tests

From `backend/`, apply migrations (the session table uses Django's built-in
sessions app), then run the auth tests locally against SQLite:

```powershell
python manage.py migrate
python -m pytest tests\test_authentication_api.py -vv
```

The tests use Django's CSRF-enforcing client. To verify the complete suite on
PostgreSQL, start the development database and set the documented PostgreSQL
environment before running:

```powershell
python -m pytest --ds=config.settings.test_postgres -vv
```

CI runs the backend suite against PostgreSQL. SQLite remains the fast local
default; it is not evidence for PostgreSQL concurrency or locking behavior.

## Development containers

From the repository root, copy `.env.example` to `.env`, then start the
development backend and PostgreSQL:

```powershell
docker compose up --build --wait
docker compose exec backend python manage.py migrate
```

The API is bound to `127.0.0.1:8000`; PostgreSQL is bound to loopback on
`DB_HOST_PORT` (default `5432`). The PostgreSQL data volume persists across
container restarts. The backend connects to the `db` service on the Compose
network. The frontend remains a local Next.js development process, and Redis
is intentionally deferred.

This Compose configuration and Django `runserver` image are for local
development only. They are not a production deployment configuration.
