# Copilot Instructions for Multi-Tenant Student Management SaaS

## Repository state

This repository contains a Next.js frontend and an incremental Django backend foundation. The backend now includes PostgreSQL configuration, a custom user model, a versioned health API, OpenAPI documentation, and development Compose support. The broader SaaS architecture in the root documentation remains aspirational: tenant membership, RBAC, authentication workflows, and student-management domains are not implemented.

Treat the current repository as the real implementation baseline. Do not assume the backend or full tenant model exists unless code is present.

## Actual stack

### Frontend

- Next.js 16
- React 19
- TypeScript
- Tailwind CSS
- Testing Library + Jest

### Backend

- Python 3.14
- Django 6.0 and Django REST Framework
- PostgreSQL for development; isolated SQLite test settings; production hosting is not configured
- pytest + pytest-django and Ruff
- drf-spectacular for protected OpenAPI/Swagger documentation
- Docker Compose for the backend and PostgreSQL development services

### Intended stack from project documentation

The README and `.env.example` describe a broader architecture that includes:

- Redis and Celery
- Full multi-tenant enforcement, authentication, and RBAC
- Domain modules for institutions, students, enrollment, and finance

Redis/Celery and these business capabilities are not implemented. If a task requires them, create them intentionally and explicitly rather than assuming they already exist.

## Working conventions

### Engineering philosophy

Follow these principles in all work:

- SOLID
- DRY
- KISS
- YAGNI
- Separation of concerns
- Composition over unnecessary inheritance
- Explicit interfaces and contracts
- High cohesion and low coupling
- Defensive programming
- Secure-by-default design
- Database integrity
- Maintainability
- Observability
- Testability

Avoid unnecessary abstractions, premature optimization, and speculative architecture.

### Architecture guidance

- Respect the existing frontend architecture unless a justified improvement is necessary.
- Keep UI presentation separate from business logic.
- Prefer small, reusable components over large monolithic ones.
- Keep styling and behavior predictable and maintainable.
- Avoid circular dependencies and overengineering.
- Maintain explicit API contracts where APIs exist.
- Do not introduce microservices without a clear product need.
- If backend features are added later, keep business logic in service layers and avoid view-layer/domain leakage.

### Code quality

Every change must have:

- Clear naming
- Small, focused functions
- Appropriate error handling
- Type safety
- Input validation
- Useful logging where needed
- Minimal, necessary documentation
- No unnecessary comments
- No duplicated logic
- No dead code
- No unexplained magic values

Do not silence errors with broad exception handling. Do not use `any` as an escape hatch in TypeScript.

### Security requirements

Security is a core engineering requirement.

For any new or modified feature, consider:

- Authentication requirements
- Authorization boundaries
- Object-level permissions
- Tenant isolation and cross-tenant data leakage
- Input validation and sanitization
- SQL injection and ORM misuse
- XSS and unsafe rendering
- CSRF and CORS concerns
- Rate limiting and abuse protections
- Secrets management
- Dependency updates and known vulnerabilities
- Audit logging

For a multi-tenant application, never trust a tenant ID supplied by the frontend as proof of authorization. Tenant isolation must be enforced at the backend boundary.

## Testing requirements

Write meaningful tests for new functionality.

Use:

- Unit tests for isolated business logic
- Integration tests for component interactions
- API tests for endpoint behavior
- Permission tests for access control
- Regression tests for previously fixed bugs

Test normal, invalid, boundary, failure, and unauthorized conditions.

Do not weaken assertions just to make tests pass.

## Frontend standards

- Prefer reusable components and semantic UI structure
- Keep layouts responsive and accessible
- Provide loading, empty, and error states where appropriate
- Keep forms validated and user-friendly
- Preserve consistency in layout and spacing
- Favor maintainable component composition over complex abstraction

## Database standards

When a database layer is introduced:

- Use foreign keys and proper constraints
- Add unique constraints where required
- Add indexes for frequent queries
- Use transactions for multi-step operations
- Use decimal precision for financial values
- Prefer UTC timestamps
- Maintain migration discipline
- Avoid destructive migrations without explicit review

## Repository commands

From `frontend/`:

- `npm install`
- `npm run dev`
- `npm test -- --runInBand`
- `npm run typecheck`
- `npm run build`

From `backend/`:

- `python -m pip install -r requirements/development.txt`
- `python -m pytest`
- `ruff check .`
- `ruff format --check .`
- `python manage.py check`
- `python manage.py makemigrations --check --dry-run`
- `python manage.py spectacular --file openapi.yaml --validate`

## Verification policy

Do not claim a change is complete unless it has been validated with the relevant command.

The frontend has previously verified health via:

- `npm test -- --runInBand` -> PASS
- `npm run typecheck` -> PASS
- `npm run build` -> PASS

The backend foundation is verified with its API/model tests, Ruff, Django checks,
migration checks, OpenAPI schema validation, and local Docker/PostgreSQL checks.

The project still emits a CSS warning from the Tailwind `@theme inline` syntax during build output, which should be reviewed during normal frontend maintenance but does not block the build.

## Implementation expectations

When adding new work:

1. Understand the exact requirement
2. Inspect the relevant implementation area
3. Identify affected modules and edge cases
4. Consider security and tenant boundaries
5. Implement the smallest maintainable solution
6. Add tests for the behavior
7. Validate with the smallest relevant command

Do not refactor unrelated code without justification.

## Documentation expectations

If a feature or architectural decision has long-term impact, document it in the relevant engineering or architecture docs under `docs/`.

For this repository, the current audit document is:

- `docs/engineering/REPOSITORY_AUDIT.md`

## Important note for future work

The backend remains a foundation rather than a complete SaaS application. Every new backend or database feature should be introduced deliberately, with explicit architecture, security, and test coverage, rather than assumed from the original product narrative.
