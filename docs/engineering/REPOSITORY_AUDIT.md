# Repository Audit

## Executive Summary

This audit records the repository state after the backend foundation milestone
(2026-11-14), updated on 2026-11-17 to reflect merged CI quality gates and
architecture/test documentation, and the initial session authentication
foundation. The project now contains a Next.js frontend and a Django
REST Framework backend foundation with PostgreSQL configuration, a UUID/email
custom user model and initial migration, health/readiness endpoints, protected
OpenAPI docs, and development Compose support for the API and PostgreSQL.

This is not yet a complete multi-tenant academic platform. Basic session
authentication endpoints exist, but account recovery and lifecycle workflows,
tenant membership and isolation, RBAC, and business domains remain future
work; Redis/Celery and production deployment are also not configured.

## Scope and Verification

The following findings are based on direct repository inspection and execution of project commands.

### Verified commands

- `npm test -- --runInBand` -> passed (6 tests); `npm run typecheck` -> passed;
  `npm run build` -> passed with a Next.js security advisory and the existing
  Tailwind `@theme inline` parsing warning
- Backend SQLite pytest suite -> passed (26 tests)
- Ruff lint and format checks -> passed
- Django development/test system checks and migration drift check -> passed
- drf-spectacular schema validation -> passed
- PostgreSQL CI workflow is configured; local PostgreSQL verification was not
  available during the authentication milestone because Docker was not running
  and localhost:5432 was unreachable

## What actually exists

### VERIFIED

- A Next.js 16 frontend application under `frontend/`
- TypeScript configuration and strict TS setup
- Tailwind CSS styling and reusable UI primitives
- A basic landing page with product positioning content
- Jest + Testing Library smoke tests for the home page
- A Django 6.0 / Django REST Framework backend under `backend/`
- Environment-based base, development, production, SQLite test, and
  PostgreSQL test settings
- PostgreSQL integration and an initial migration for the custom UUID/email user model
- Versioned liveness and database-readiness endpoints
- Versioned session-based login, logout, current-user, and CSRF endpoints with
  CSRF enforcement, session rotation/expiry, safe user serialization, and
  basic IP-based login throttling
- Protected OpenAPI schema and Swagger UI
- pytest-django, Ruff, and Docker Compose development configuration for backend/PostgreSQL
- Separate PostgreSQL-backed backend and frontend GitHub Actions quality-gate workflows
- Root-level project documentation in `README.md`
- Root-level environment example in `.env.example`
- Git remotes configured for both the fork and upstream repository

### PARTIALLY IMPLEMENTED

- Product scaffolding and product copy: present in README and home page
- Frontend tests cover the landing page and auth API client; backend tests cover
  health/readiness, schema, user model, and session authentication
- Frontend component library foundation: present, but not yet extended into a product UI

### NOT IMPLEMENTED

- Email verification, password recovery, MFA, per-device session management,
  and complete account lifecycle workflows
- Tenant membership and authorization policies
- Multi-tenant enforcement in backend logic
- Role-based access control
- Student, academic, enrollment, and course management APIs
- Reporting and analytics APIs
- Redis / Celery integration
- Production deployment and release pipeline configuration
- Production deployment infrastructure

### UNVERIFIED

- Claims that a backend will be implemented in a future phase
- Any business logic that is not represented in checked-in code

## Repository Reality Check

### Technology stack in code

The implemented codebase reflects this state:

- Frontend framework: Next.js 16
- UI library: React 19
- Styling: Tailwind CSS
- Language: TypeScript
- Frontend test stack: Jest + Testing Library
- Backend: Python 3.14, Django 6.0, Django REST Framework
- Backend development database: PostgreSQL; default local pytest settings use
  in-memory SQLite; CI explicitly selects PostgreSQL test settings
- Backend quality/test stack: Ruff, pytest, pytest-django
- API schema: drf-spectacular

The backend is a foundation, not the complete platform described in the project handover.

### Architecture mismatch

The README and `.env.example` describe a broader architecture that includes:

- Redis + Celery
- Complete multi-tenant SaaS infrastructure and business features

The Django/PostgreSQL baseline now exists, but the broader architecture should not be treated as implemented until its remaining components are built and verified.

## Verified project health

### Current working state

The frontend checks passed during this milestone:

- Jest smoke tests: PASS
- TypeScript type checking: PASS
- Production build: PASS

The backend foundation and session authentication tests currently pass:

- Twenty-six API, authentication, and custom-user tests: PASS on SQLite
- Ruff lint and format checks: PASS
- Django development/test system checks: PASS
- Migration drift check: PASS
- OpenAPI generation and validation: PASS
- PostgreSQL-backed verification for this milestone: NOT RUN (Docker daemon
  unavailable and localhost:5432 unreachable); prior Compose checks do not
  establish current PostgreSQL authentication behavior

### Current caveat

The project still emits one warning during the Next.js build:

- Tailwind CSS `@theme inline` syntax produces a CSS parsing warning during the build output
- Next.js also reported that the installed version is affected by a known
  security vulnerability; upgrade Next.js in a separate dependency-focused
  change before treating the frontend dependency set as suitable for release.

The build completed, but these warnings should be resolved before release.

## Architectural strengths

- Clean, modern frontend foundation using Next.js + TypeScript
- Simple component structure and understandable project layout
- Initial backend settings, database integration, migrations, and test tooling
- Health and readiness APIs distinguish process liveness from database readiness
- Custom user model was created before the first migration
- Development API and PostgreSQL run with loopback-only ports and a persistent database volume
- Clear product vision and high-level domain breakdown
- Separation between configuration, API presentation, and applications

## Architectural weaknesses

- The backend has a limited session-authentication foundation; recovery,
  email verification, MFA, and full account lifecycle are not implemented
- No multi-tenant isolation logic is implemented
- No tenant-aware authorization or object-level permission model exists
- No student, academic, enrollment, or finance domain APIs are built
- Compose is development-only; PostgreSQL-backed backend and frontend CI
  quality-gate workflows now exist, but no production deployment or release
  pipeline is configured
- Redis/Celery integration is deferred

## Security concerns

### SECURITY WORK REMAINS

The foundation provides secret-based settings, secure production cookie
defaults, explicit CORS/CSRF origin configuration, a non-querying liveness
endpoint, staff-protected API documentation, and session-based account
authentication. The following requirements remain unimplemented:

- No email verification, password recovery, MFA, or per-device session
  management
- No tenant membership, tenant authorization, or object-level business
  authorization policies
- No database-level tenant isolation
- No tenant-aware permissions, RBAC, or object-level access controls
- No production secret-management service or deployment configuration
- No audit logging or security monitoring

## Testing gaps

- Frontend tests cover landing-page rendering and basic auth API-client behavior
- Backend tests cover health/readiness, schema access, custom-user manager,
  session authentication, CSRF, cookie/session behavior, and throttling
- No tenant-isolation, business authorization, recovery, MFA, or permission-
  boundary tests exist
- PostgreSQL-backed CI quality gates are configured; tenant-specific
  authorization, isolation, relationship, and operational regression tests do
  not yet exist
- No regression tests exist for domain features that are still absent

## Technical debt

- Product documentation still describes features that are not implemented
- The frontend is still a landing-page prototype
- The API contract currently covers authentication, health, and OpenAPI
  endpoints; no tenant or business APIs exist
- The data model includes the custom user plus `Institution` and `Membership`
  foundation models; tenant resolution, authorization, and business models remain absent
- Styling warnings indicate a config/detail cleanup opportunity

## Dependencies and infrastructure concerns

- Frontend and backend dependency manifests are separate and version-pinned
- Development Compose includes only the backend and PostgreSQL; frontend remains locally run and Redis is deferred
- Root `.env.example` contains local-only values and must not be used as production configuration
- CI quality gates exist; deployment automation and production environment governance are not yet implemented

## Architecture and backlog

The proposed shared-schema tenant boundary, membership lifecycle, request
resolution, and isolation requirements are documented in
[`../architecture/MULTI_TENANCY.md`](../architecture/MULTI_TENANCY.md). This is
a design proposal for review; tenant resolution and authorization remain
unimplemented. The threat model and planned regression matrix are documented
in [`../architecture/TENANT_ISOLATION_TEST_STRATEGY.md`](../architecture/TENANT_ISOLATION_TEST_STRATEGY.md);
the strategy does not mean tenant tests or enforcement exist.

The dependency-aware implementation plan, including CI/CD, authentication,
domain modules, observability, backups, and subscription billing, is maintained
in [`ENGINEERING_BACKLOG.md`](./ENGINEERING_BACKLOG.md).

## Status Summary

| Area | Status |
|---|---|
| Frontend foundation | VERIFIED |
| Landing page app | VERIFIED |
| Django/PostgreSQL backend foundation | VERIFIED |
| Custom user model and initial migration | VERIFIED |
| Health/readiness APIs and OpenAPI | VERIFIED |
| Development backend/PostgreSQL Compose | VERIFIED |
| Full multi-tenant backend | NOT IMPLEMENTED |
| Institution and membership database models | VERIFIED |
| Tenant/business database models | PARTIALLY IMPLEMENTED |
| Session authentication | IMPLEMENTED |
| Recovery, email verification, MFA, and full account lifecycle | NOT IMPLEMENTED |
| Tenant/domain authorization | NOT IMPLEMENTED |
| Role-based access control | NOT IMPLEMENTED |
| Student-management domain features | NOT IMPLEMENTED |
| Reporting and analytics | NOT IMPLEMENTED |
| Testing infra | PARTIALLY IMPLEMENTED |
| CI quality gates | CONFIGURED; tenant-specific tests not implemented |
| Production deployment/release pipeline | NOT IMPLEMENTED |

## Conclusion

The repository now has a verified backend starting point, session
authentication, and Institution/Membership foundation models, but is not yet the
realized multi-tenant student management SaaS described in the project README.
The tenant architecture is documented as a proposal and still requires review.
Backend and frontend CI quality gates, including PostgreSQL-backed test
settings, are now configured. The frontend build reports an upstream Next.js
security advisory; resolve it in a separate dependency-upgrade change. The
next steps are to approve remaining account lifecycle decisions, implement
tenant models and authorization deliberately, and build the regression suite in
[`../architecture/TENANT_ISOLATION_TEST_STRATEGY.md`](../architecture/TENANT_ISOLATION_TEST_STRATEGY.md)
before exposing tenant-scoped business workflows.
