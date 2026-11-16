# Continuous integration

The repository has two independent GitHub Actions workflows:

- **Backend CI** checks out the code, starts PostgreSQL 17, installs the
  pinned backend requirements with Python 3.14, verifies a live PostgreSQL
  connection, then runs Ruff lint and format checks, Django system checks,
  migration consistency validation, and the complete pytest suite.
- **Frontend CI** uses Node.js 24 and installs from
  `frontend/package-lock.json` with `npm ci`, then runs Jest, TypeScript type
  checking, and the production build. Next.js 16 requires Node.js 20.9 or
  later; the repository does not otherwise pin a Node.js range.

Both workflows run for pull requests targeting `main` and pushes to `main`.
They use read-only `contents` permissions, do not require repository secrets,
and use `pull_request` rather than `pull_request_target`, so fork contributions
run without receiving write credentials. Third-party actions are pinned to
full commit SHAs. Per-workflow concurrency groups cancel superseded runs for
the same pull request or branch. No deployment steps are included.

## Backend and PostgreSQL tests

`backend/pyproject.toml` selects `config.settings.test` for normal local pytest
runs. That settings module uses in-memory SQLite to keep the default test
workflow convenient and isolated. `config.settings.test_postgres` reuses the
same test behavior but takes `DATABASES` from `config.settings.base`, which
uses the PostgreSQL connection environment variables. CI sets this settings
module explicitly and also passes `--ds=config.settings.test_postgres` to
pytest, overriding the SQLite default. A preflight command opens a Django
connection and asserts that its vendor is PostgreSQL before the checks run.
Pytest-django then creates its normal temporary test database using that
PostgreSQL connection; database-marked tests execute against it.

The PostgreSQL service uses the same major version as `compose.yaml`. Its
health check must pass before any job steps start. CI database credentials
are disposable service-container values, not repository secrets.

### Run backend checks locally

From `backend/`, install the declared development dependencies and run the
standard checks:

```powershell
python -m pip install -r requirements\development.txt
ruff check .
ruff format --check .
python manage.py check
python manage.py makemigrations --check --dry-run
python -m pytest
```

Ensure local PostgreSQL is running for Django management and migration checks.
By default, pytest uses SQLite as configured in `pyproject.toml`.
To reproduce the CI database path, first start the PostgreSQL service from the
repository root with `docker compose up -d --wait db`. Set `DB_NAME`, `DB_USER`,
`DB_PASSWORD`, `DB_HOST`, and `DB_PORT` in the environment to match that
service, then from `backend/` run:

```powershell
$env:DJANGO_SETTINGS_MODULE = "config.settings.test_postgres"
python manage.py shell -c "from django.db import connection; connection.ensure_connection(); assert connection.vendor == 'postgresql'; print('Connected to PostgreSQL')"
python manage.py check
python manage.py makemigrations --check --dry-run
python -m pytest --ds=config.settings.test_postgres -vv
```

Do not treat a SQLite test run as evidence that the PostgreSQL CI suite passed.
The pytest output should report `config.settings.test_postgres` and show
creation of a PostgreSQL test database. A connection error or a failed vendor
assertion is a configuration failure, not a reason to fall back to SQLite.

## Run frontend checks locally

From `frontend/`, use the committed lockfile and the same commands as CI:

```powershell
npm ci
npm test -- --runInBand
npm run typecheck
npm run build
```

The current build does not require environment variables. Do not add secrets
to a client-side Next.js build; any future public build-time configuration
should be non-sensitive and explicitly documented.

## Adding tests and reproducing failures

- Add backend tests under `backend/tests/` or the relevant app test package.
  Mark tests that access the database with `pytest.mark.django_db`. Keep
  database-independent tests unmarked. Tests of PostgreSQL-specific behavior
  must be exercised by the PostgreSQL CI suite, not only local SQLite.
- Add frontend tests using the existing Jest configuration and test setup.
  Keep assertions meaningful; CI runs Jest in-band and non-watch mode.
- Run the same command shown in the failing workflow step from its documented
  working directory. Reproduce backend database failures with
  `config.settings.test_postgres`, and verify the service is reachable before
  rerunning pytest.
- A Ruff or format failure is a Python source-quality issue. A Django or
  migration failure points to settings, checks, or model/migration drift. A
  pytest failure is a backend behavior regression; confirm it is running on
  PostgreSQL in CI. Jest failures identify frontend behavior regressions,
  typecheck failures identify TypeScript errors, and build failures identify
  production compilation or prerendering problems.
- Do not skip tests, relax strict TypeScript settings, bypass migrations, or
  switch CI to SQLite to make a check green.

## Protecting `main`

Configure these settings in GitHub repository rules; this document does not
change repository settings:

- Require pull requests before merging.
- Require the **Backend CI / backend-quality-gates** and
  **Frontend CI / frontend-quality-gates** checks to pass. Select the exact
  check names shown by GitHub after the first workflow run.
- Require branches to be up to date before merging when that matches the
  repository's merge policy.
- Prevent force pushes.
- Restrict direct pushes to `main` where project governance allows.
