# Engineering Backlog

This is the dependency-aware engineering backlog for the Django SaaS backend.
It distinguishes the next foundational work from later product capabilities.
Items are proposals, not evidence that the feature exists. The current backend
contains only the initial Django foundation; see
[`REPOSITORY_AUDIT.md`](./REPOSITORY_AUDIT.md) and
[`MULTI_TENANCY.md`](../architecture/MULTI_TENANCY.md).

## Immediate: agree and prepare the foundation

| Priority | Work item | Dependencies / exit criteria |
|---|---|---|
| P0 | Review and approve the tenant and authentication decision register | Explicitly accept or amend each decision in [the register](../architecture/decisions/TENANT_AND_AUTH_DECISIONS.md), including the proposed [institution role/permission matrix](../architecture/INSTITUTION_ROLE_PERMISSION_MATRIX.md); existing session auth, models, tenant context, and generic role permission are implementation baseline, not policy approval; do not add business authorization grants or workflows until the applicable decisions are accepted |
| P0 | Review and approve the proposed tenant architecture | Depends on the decision register; no schema work until institution lifecycle, role semantics, invitation lifecycle, slug policy, authentication direction, ownership safeguards, and platform support boundaries are agreed |
| P0 | Establish automated backend and frontend CI quality gates | **Completed:** separate PR/push workflows run backend and frontend checks; configure required checks on `main` per [CI guidance](./CI.md). This item does not include deployment automation |
| P0 | Run backend tests and migration checks against PostgreSQL in CI | **Completed:** CI explicitly selects PostgreSQL test settings and executes system, migration, and pytest checks against a PostgreSQL service; tenant-specific tests remain future work |
| P0 | Document the tenant-isolation test strategy and regression matrix | **Completed:** [strategy](../architecture/TENANT_ISOLATION_TEST_STRATEGY.md) defines threats, test cases, reusable fixtures, database requirements, and phased implementation; the existing tenant-resolution and generic role-permission tests cover foundations only |
| P0 | Extend tenant-isolation fixtures and regression tests | Depends on approved tenant/authentication contracts and domain APIs; add reusable two-institution domain-resource, relationship, query, and denied-access coverage for each endpoint, then run database-specific cases in PostgreSQL CI |
| P0 | Approve the authentication contract and remaining account workflows | The session-based browser foundation is implemented, but decision `AUTH-01` remains Proposed in the [decision register](../architecture/decisions/TENANT_AND_AUTH_DECISIONS.md); approve the contract and decide email verification, recovery, MFA, and operational abuse controls before account lifecycle or membership flows |

**Exit gate:** relevant decision-register entries explicitly accepted by the
project owner, auth direction selected, CI checks in place, and the tenant
security test plan agreed. The decision register and test strategy are
documentation, not approval or implemented controls. No business API should
ship before the tenant isolation tests are enforceable in CI.

## Next: identity, tenancy, and institution administration

| Priority | Work item | Dependencies / exit criteria |
|---|---|---|
| P1 | Implement authentication and account lifecycle | **Partially implemented:** session login/logout/current-user/CSRF endpoints, session expiry, and IP throttling exist; verified email, recovery, MFA, per-device management, stronger shared rate limiting, and broader account lifecycle remain |
| P1 | Implement institution and membership model foundation | **Completed:** Institution and Membership models, migrations, database constraints, and focused model tests exist; invitation models, lifecycle workflows, invitation tokens, audit events, and owner protection remain future work |
| P1 | Implement institution invitations and lifecycle workflows | Depends on the approved membership and ownership contracts; reviewed migrations, lifecycle transitions, invitation token hashing/expiry, audit events, and last-owner protection |
| P1 | Implement tenant resolution and authorization policy | **Partially implemented:** path-based tenant context and reusable default-deny DRF permissions with explicit membership-role declarations and current-membership revalidation exist; review and approve the [proposed matrix](../architecture/INSTITUTION_ROLE_PERMISSION_MATRIX.md) before applying grants to business endpoints, then implement object-level checks and endpoint-specific isolation tests with those APIs |
| P1 | Implement institution management APIs | Depends on tenant resolution and authorization; create/update/status rules, slug policy, member listing/invites, role assignment, and cross-tenant denial tests |
| P1 | Establish audit logging, observability, and operational alerts | Begin before privileged production workflows; log actor, institution, action, outcome without credentials or sensitive student payloads; trace request and job context |
| P1 | Define backup and restore objectives and runbooks | Required before production data; encrypted backups, retention, recovery point/time objectives, restore drills, and tenant-data export/delete policy |
| P1 | Establish deployment and release pipeline | Depends on CI baseline; environment/secrets management, reviewed migrations, rollback strategy, health checks, and no development-only settings in production |

## Later: domain capabilities

| Priority | Work item | Dependencies / key safeguards |
|---|---|---|
| P2 | Admissions | Depends on institution management, authentication, and authorization; model applicant and application lifecycle without exposing records across institutions |
| P2 | Student management | Depends on institution/membership foundation; identity matching, student lifecycle, privacy classification, tenant-scoped profiles, and object-level access tests |
| P2 | Academics | Depends on institution and student foundations; academic years, terms, departments/programs, classes/courses, and institution-scoped uniqueness/relationships |
| P2 | Attendance | Depends on students and academic/class assignments; teacher assignment checks, timezone-aware dates, correction audit, and student/guardian access rules |
| P2 | Examinations and results | Depends on academics and student records; role separation, publishing lifecycle, result privacy, and immutable/audited changes where required |
| P2 | Notifications | Depends on authentication, membership/invitation lifecycle, and a concrete delivery requirement; tenant-aware templates, consent/preferences, retries, and secret-safe logs |
| P2 | Finance and institution billing workflows | Depends on institution, student/enrollment, authorization, and finance requirements; decimal money, currency, ledger/reconciliation policy, and restricted financial access |
| P2 | Reporting and exports | Depends on the underlying domain modules and isolation tests; tenant-scoped aggregates, export authorization, retention, and safe download links |

Implement domain areas as modular Django apps in the monolith. Each feature
must preserve institution ownership in queries, create/update rules, nested
references, background jobs, admin actions, and exports. Avoid introducing
Redis/Celery until asynchronous workloads and operational ownership are
specified.

## Future: commercial and scale capabilities

| Priority | Work item | Dependencies / decision points |
|---|---|---|
| P3 | SaaS subscription billing and entitlement enforcement | Depends on institution lifecycle and commercial plan/provider decisions; separate platform subscription billing from institution student/fee finance; define webhook idempotency, retries, and suspension/grace behavior |
| P3 | Advanced analytics and cross-institution platform reporting | Depends on domain data governance and explicit platform authorization; aggregate/minimize personal data and audit privileged access |
| P3 | Evaluate PostgreSQL Row-Level Security or stronger tenant isolation | Triggered by risk, compliance, or scale evidence; prove transaction context, connection-pool behavior, admin/task operation, migration safety, and rollback |
| P3 | Evaluate asynchronous infrastructure | Triggered by delivery/export workload; choose broker, task ownership, tenant context propagation, idempotency, retries, and monitoring before adding Redis/Celery |
| P3 | Production scale and disaster-recovery exercises | Depends on deployed service and data; load tests, restore drills, incident response, and capacity/tenant-noisy-neighbor controls |

## Dependency outline

```text
Architecture approval ─┬─> Authentication design ─> Authentication
                       ├─> CI + PostgreSQL CI ──────────────┐
                       └─> Tenant test plan ────────────────┤
                                                            v
Authentication + institution/membership models ─> Tenant authorization
                                                     │
                                                     v
                                           Institution management
                                                     │
                         ┌───────────────────────────┼──────────────────────┐
                         v                           v                      v
                    Admissions                  Students              Notifications
                                                     │
                                                     v
                                                 Academics
                                               /      |      \
                                              v       v       v
                                         Attendance Exams   Finance
                                              \       |       /
                                               Reporting/exports

Institution lifecycle + commercial decisions ─> SaaS subscription billing
CI baseline ─> PostgreSQL CI, deployment pipeline, release gates
Observability + backup/restore ─> production operations and recovery
```

Dependencies in the diagram are architectural ordering, not a requirement to
build every product module before starting another. Each domain can be
prioritized independently once its listed foundations and authorization tests
are satisfied.
