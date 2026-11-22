# Institution Ownership and Lifecycle Architecture

**Status:** Proposed architecture. The project owner selected a dedicated
`owner` membership role distinct from `institution_admin`; the role and
workflows are not implemented. Details below require review before models,
migrations, endpoints, or operational workflows are built.

## 1. Current implementation boundary

The current code defines:

- `Institution.Status`: `draft`, `active`, `suspended`, `closed`.
- `Membership.Role`: `institution_admin`, `academic_staff`,
  `finance_staff`, `student`, `guardian`.
- `Membership.Status`: `active`, `suspended`, `removed`.
- One unique Membership per `(institution, user)`, with one `role` field.
- Tenant resolution that admits `draft` and `active` institutions, and returns
  404 for `suspended` and `closed`; active membership is required.
- A default-deny role permission that uses the role on the resolved
  institution's current active membership.
- Django session authentication. Neither authentication nor the tenant
  context currently establishes ownership.

There is no owner role, ownership field, owner service, institution creation or
lifecycle API, audit-event store, or final-owner enforcement. Model-level
validation alone is not protection against bulk updates or direct database
writes. The selected owner-role direction requires a future schema migration;
this architecture PR makes no application or schema changes.

## 2. Ownership representation

### Selected direction

Represent institution ownership with a dedicated `owner` value on the
institution's Membership role, distinct from `institution_admin`. Do not
equate ownership with Django `is_staff`, `is_superuser`, global permissions,
or platform support access.

### Proposed semantics

1. **One Membership row per person/institution remains the relationship.**
   Multiple owners are supported as multiple users, each with an active
   Membership whose role is `owner`. The existing unique pair constraint is
   compatible with this; one user cannot create duplicate memberships in the
   same institution.
2. **One role per membership.** The current schema has a single role column,
   not a role set. A person cannot simultaneously hold `owner` and
   `institution_admin` on the same membership without a schema redesign.
   Recommend retaining the single-role model. An owner may perform a defined
   subset of ordinary administrative operations only when the corresponding
   view explicitly permits `owner`; this is explicit permission reuse, not
   implicit role inheritance. Final grants belong in the separately approved
   role/action matrix.
3. **Ownership is not unrestricted data access.** Owner status should cover
   institution governance and narrowly approved settings/membership operations.
   It should not by itself grant access to all student, safeguarding,
   assessment, results, finance, or export data. Those still require
   purpose- and object-scoped authorization.
4. **No self-elevation.** A current owner or separately authorized,
   auditable recovery operation must approve another user's owner assignment.
   An institution administrator cannot make themselves owner. A client
   supplied role, membership ID, or institution ID is never authority.
5. **Bootstrap assignment.** Proposed default: create an institution in
   `draft` and assign its initial owner membership in the same database
   transaction. The owner is derived from the authenticated creator or an
   explicitly authorized provisioning actor; ignore/reject a client-provided
   role. Verification, self-service creation, and platform provisioning are
   unresolved. Email verification is not currently implemented.
6. **Ordinary administration.** Recommend permitting owners to perform a
   reviewed set of routine institution-administration operations, but not
   treating `owner` as a synonym for `institution_admin`. Each operation must
   list both roles explicitly where appropriate. Sensitive administrator
   grants remain denied unless separately approved.
7. **Multiple owners and transfer.** Support more than one active owner to
   allow continuity. A transfer promotes an eligible active member to owner
   before demoting/removing the outgoing owner, in one transaction. Require
   the incoming owner's explicit acceptance and audit the old/new owner,
   reason, actor, and outcome. The outgoing owner may remain an active
   `institution_admin` only if that is the explicitly selected new role.
8. **Relinquishment.** An owner may demote or leave only if another available
   active owner remains after the transaction. Otherwise require an atomic
   transfer/add-owner operation first.
9. **Suspension, removal, and disabled accounts.** An owner membership with
   `suspended` or `removed` status does not count toward the invariant. An
   inactive global user (`User.is_active=False`) is unavailable and should not
   count either. Preserve removed membership history. Account deactivation is
   global, so a future workflow must check every non-closed institution the
   user owns before disabling that account.
10. **Succession.** Prefer maintaining at least two active owners where
    operationally appropriate, but do not make a two-owner minimum an
    invariant without product approval. If all owners are unavailable, use a
    separate, evidence-based, time-bounded platform recovery process with
    independent approval and audit; do not silently elevate an administrator.
    No recovery role or workflow exists today.

## 3. Final active-owner invariant

### Proposed invariant

Every institution whose status is not `closed` must have at least one
Membership with role `owner`, status `active`, and an associated active global
user account. Preserve the active owner through `draft`, `active`, and
`suspended` so a suspended institution can be reinstated without losing its
accountable owner. On closure, require an active owner to authorize and be
recorded in the closure event; subsequent membership/account cleanup for a
closed institution follows the separately approved retention process.

This invariant does not grant tenant API access while an institution is
suspended or closed. The existing resolver continues to govern ordinary
tenant access.

### Transaction and database strategy

Use one shared PostgreSQL lock protocol for every transaction that can change
whether an owner is available: initial/additional owner assignment, transfer,
relinquishment, membership role/status changes, ownership recovery/succession,
global account activation/deactivation, and institution lifecycle changes
that affect the invariant.

1. Start `transaction.atomic()` on the primary PostgreSQL database.
2. Lock every known relevant global User row that participates in the
   operation (actor, assignment/transfer/recovery participants, or account
   whose status is changing) with `select_for_update()` in deterministic UUID
   order. For account deactivation, the target User row must be among these
   locks; once the sorted known User-lock set is held, discover the affected
   institution set. Any pre-lock membership lookup is discovery only, never
   authorization or final invariant evidence.
3. For global account deactivation, after locking the target User row,
   re-query all institutions in which that user currently has an owner
   membership. Do not use an institution list discovered before acquiring the
   User lock. For other workflows, resolve the affected institution set from
   their requested membership/transfer targets.
4. Lock all affected Institution rows with `select_for_update()` in
   deterministic UUID order.
5. After both lock sets are held, re-read and validate actor/target account
   status, membership role/status, institution status, current active-owner
   set, and the proposed resulting invariant. Do not trust pre-lock reads.
6. Apply all membership, account, and lifecycle changes plus their successful
   audit event atomically. Reject any transition that would leave a non-closed
   institution without an available active owner; do not leave partial changes.
   The exact external conflict/retry contract remains unapproved.

The lock set is for users whose rows this operation reads as its authorization
principal or mutates, not every owner whose status is counted. Current owner
membership and account states are re-read after the affected Institution rows
are locked. Every operation that changes a membership role/status or a
relevant account's active state must itself acquire that Institution lock
before persisting; this serializes those changes against the invariant check.
If an operation discovers that it must mutate or authorize against an
additional User row after locking Institutions, it must roll back and restart
with the complete User set sorted before acquiring any Institution lock.
Never acquire a newly discovered User lock while holding Institution locks:
that reverses the order and can deadlock.

This order closes the account-deactivation/assignment race because both
operations first serialize on the same global User row for the user whose
availability is changing. If deactivation wins, assignment waits and then
sees the account disabled when it revalidates; if assignment wins, deactivation
waits, re-queries owner memberships after obtaining the User lock, discovers
the new institution dependency, and locks that institution before validating
whether deactivation can proceed. It cannot miss a committed assignment to
that user by relying on an earlier institution list.

Every relevant write path must participate in this protocol; the locking
proposal does not itself enforce that requirement. No path may lock an
Institution and then request a User lock, or acquire multi-row locks in an
unstable order. In particular, owner services, lifecycle/recovery workflows,
account administration, Django admin actions, bulk operations, management
commands, background jobs, and direct SQL must not silently use conflicting
paths. Retry only recognized transient deadlock/serialization failures, by
restarting the entire transaction with the same deterministic order and an
idempotency strategy.

An ordinary SQL `CHECK` cannot enforce a cross-row minimum owner count. Model
validation, an unlocked count, Membership-row locks alone, or a service
convention alone do not prove universal enforcement. The required database
enforcement boundary remains unresolved; options and limitations are recorded
under OWN-04 below and in the decision register. Do not claim universal
invariant enforcement until that boundary is approved, implemented, and
validated for every supported and alternate write path.

### Conflict, retry, and audit behavior

- A stale request, actor who lost owner status, or final-owner removal attempt
  is rejected as a business conflict (proposed HTTP 409 for APIs), with no
  partial role change.
- Retry only recognized transient database serialization/deadlock failures,
  with a small bounded retry count and an idempotency strategy. If retries are
  exhausted, return an explicit retriable service error; do not disguise it as
  success. The exact retry and HTTP contract remains to be approved.
- Audit committed changes in the same transaction. Record rejected attempts
  after rollback through a separate safe audit path if the security policy
  requires them; a failed transaction must not create a success-shaped event.
- Avoid logging credentials, session secrets, or unnecessary student data.

## 4. Institution lifecycle

### Existing values and compatibility

The model currently uses `draft`, `active`, `suspended`, and `closed`; the
database check constraint accepts exactly these values. Some older proposal
text refers to `onboarding`. This proposal uses `draft` for the pre-activation
state and does not add or rename a status. Treat `onboarding` as proposed
product terminology that maps to existing `draft`, not as a current status.
Adding a new status later would require a reviewed model/constraint migration,
data mapping, API/schema update, and lifecycle tests. No status migration is
proposed here.

### Proposed transition table

This is a review proposal, not an implemented workflow. “Platform approver”
means a separately authorized platform governance actor; it is not an
institution membership role and no such actor/workflow currently exists.

| From | To | Initiator | Approver / executor | Required preconditions and outcome |
|---|---|---|---|---|
| Not created | `draft` | Authenticated eligible creator or authorized provisioning service | Creation service atomically assigns the initial active owner; any separate platform review is unresolved | Valid institution data; eligible owner identity; institution and owner membership commit together. No public business access is implied. |
| `draft` | `active` | Active owner requests activation | Separate platform provisioning approver approves; no approval is implied by membership alone | At least one available active owner; identity/institution verification and required configuration complete. |
| `draft` | `suspended` | Platform security/compliance function | Authorized platform actor executes and records reason | Emergency hold with evidence/reason; ordinary tenant routes become unavailable. |
| `draft` | `closed` | Active owner requests cancellation | Platform reviewer approves; if multi-owner policy requires, another active owner also approves | No unresolved provisioning obligation; retention/legal hold and outstanding data/export obligations reviewed. |
| `active` | `suspended` | Owner may request; platform security/compliance may initiate emergency action | Authorized platform actor executes; emergency action receives timely independent review | Recorded reason, scope, actor, evidence, and remediation path. Ordinary tenant access is blocked. |
| `active` | `closed` | Active owner requests closure | Independent platform/compliance approver; second owner approval is recommended where multiple owners exist | Retention, legal hold, billing/contract, export, backup, and dependent-workflow review; active owner recorded at closure. |
| `suspended` | `active` | Active owner requests reinstatement | Platform approver verifies remediation and approves | Suspension cause resolved; current owner and institution checks pass; reinstatement event recorded. |
| `suspended` | `closed` | Active owner requests closure, or platform/legal process initiates it | Platform/compliance approver | Closure obligations and retention/legal review complete; record reason and actor. |
| `closed` | `suspended` | Authorized platform recovery process only | Independent platform approver | The transaction must lock relevant User rows then the Institution row, re-read ownership, and prove at least one available active owner exists before committing the transition. If none exists, the institution remains closed until ownership recovery and reopening can be performed atomically; audit both outcomes. |
| `closed` | `draft` or direct `active` | Not allowed as an ordinary transition | Not applicable | No direct transition. A distinct reviewed reopen operation is required; normal activation approval then governs `suspended` → `active`. |

All other transitions are denied by default. In particular, do not move an
institution back to `draft`, reopen it directly to `active`, or hard-delete it
through ordinary product workflows.

### Lifecycle and access behavior

- Existing tenant resolution permits `draft` and `active` context for an active
  member. Keep that contract; `draft` access is for explicitly scoped setup
  functions, not a blanket grant to future business APIs.
- `suspended` and `closed` remain unavailable to ordinary tenant APIs (current
  behavior: 404). Owners do not bypass this gate. A recovery or support route,
  if approved, must be separate, purpose-bound, and audited.
- The final-owner invariant applies before and after reopening: `closed` →
  `suspended` cannot commit without an available active owner. Lock ownership
  participants before the Institution row, validate and change lifecycle in
  the same transaction. If there is no available owner, keep the institution
  closed; an approved recovery must assign/restore an owner and reopen
  atomically. This prevents a non-closed institution from being created
  without an accountable owner by reopening.
- Institution lifecycle changes do not silently change Membership status or
  session state. Each request still resolves current institution and
  membership status; account deactivation and session invalidation follow
  their own approved contract.
- `closed` is terminal for ordinary workflows. Exceptional reopening is
  separate, audited, and staged through `suspended`.

## 5. Required audit events

The future audit store should be append-only and institution-scoped. Each event
must include a stable event ID, UTC timestamp, institution ID, actor identity
(user or explicitly identified system/platform actor), action, target
membership/user where applicable, previous and resulting role/status,
reason/purpose, outcome, and request/correlation ID. Approval events record
the approver separately from the initiator. Record only the minimum metadata
needed; never store credentials, session tokens, invitation secrets, or
unnecessary student payloads.

| Event | Required detail |
|---|---|
| Initial owner assignment | Creator/provisioning actor, initial owner, institution, creation status, verification basis, and transaction outcome |
| Owner addition | Initiator, approving owner/platform actor, target identity, prior/new membership state, reason, and acceptance |
| Ownership transfer | Outgoing and incoming owner IDs, initiator, approver(s), both membership changes, reason, and atomic outcome |
| Owner relinquishment/removal | Actor, affected owner, successor owner(s), resulting membership role/status, reason, and invariant check outcome |
| Owner suspension/reinstatement | Actor, affected owner, reason/evidence, approver, prior/new status, and resulting available-owner count |
| Ownership succession/recovery | Requester, unavailable owner(s), evidence, independent approver, successor identity, scope/expiry if platform-assisted, and review outcome |
| Institution activation | Initiator, verifier/approver, verification references, old/new status, owner at activation, and outcome |
| Institution suspension | Initiator/executor, reason/evidence, scope, approver or emergency-review deadline, old/new status, and outcome |
| Institution reinstatement | Requester, remediation summary/reference, approver, old/new status, and outcome |
| Institution closure | Initiator, approver(s), reason, retention/legal/export checks, active owner at closure, old/new status, and outcome |
| Institution reopening | Platform recovery actor, independent approver, justification, old/new status (`closed` → `suspended`), and outcome |

Successful state changes and their audit records commit atomically. Audit
records cannot be updated/deleted through ordinary application permissions.
Audit read/export authorization, retention, integrity verification, and
emergency access remain separate decisions.

## 6. PostgreSQL concurrency test strategy

Use PostgreSQL-backed transactional tests in the existing CI job. SQLite tests
may check service validation and response mapping but do not prove row-lock,
transaction-isolation, or concurrent final-owner safety.

Required PostgreSQL-backed cases before enabling owner workflows:

1. **Bootstrap atomicity:** concurrent institution creation/initial-owner
   assignment never commits an institution without its initial active owner.
   The distinct creator/owner User rows are locked in UUID order before the
   new Institution row is created.
2. **Account deactivation versus owner assignment:** race deactivation of a
   user with assigning that same user as owner in another institution. If
   deactivation obtains the User lock first, assignment must block, then fail
   after observing the disabled account. If assignment obtains it first,
   deactivation must block, re-query memberships after acquiring the lock,
   discover and lock the newly affected institution, then either reject
   deactivation for violating the invariant or proceed only if another
   available owner remains.
3. **Account deactivation versus ownership transfer:** race deactivation of an
   outgoing or incoming owner with a transfer involving that user. The shared
   User lock serializes the outcomes; the later transaction re-reads roles and
   account status and either safely commits or fails without partial changes.
4. **Two concurrent final-owner removals:** start with two available owners
   and concurrently remove, suspend, or demote each. One may commit; the
   second must block on the shared user/institution lock, re-read state, and
   fail if it would remove the last owner. Assert no committed zero-owner
   state.
5. **Overlapping transfers:** concurrently transfer ownership across
   overlapping users and institutions. Lock all participant User rows and
   Institution rows in UUID order. The later transaction must block, then
   revalidate and either commit a valid transition or fail/retry explicitly;
   assert no deadlock leaves partial changes or violates the invariant.
6. **Closed-institution reopening versus recovery:** race `closed` → `suspended`
   with ownership recovery. Reopening must block on shared User/Institution
   locks, then re-read. If recovery is not committed or no available owner
   exists, reopening fails and the institution remains closed. If recovery and
   reopening participate in the same transaction, both may commit atomically.
7. **Two-owner self-demotion race:** start with exactly two active owners on
   separate database connections. Synchronize both transactions attempting to
   relinquish their own role. One may commit; the other must observe one
   remaining active owner and fail with a conflict. After both finish, count
   must be at least one.
8. **Two-owner removal race:** concurrently attempt to suspend/remove distinct
   owners. Verify no committed schedule leaves zero active owners and the
   losing operation has no partial mutation.
9. **Concurrent transfers:** race transfers to different eligible successors.
   Verify serialized, auditable final ownership, no duplicate membership, and
   at least one active owner at every committed state.
10. **Role/status and account disable:** race owner demotion/removal with
   membership suspension and global user deactivation. Verify all affected
   institutions preserve an available owner or reject the operation.
11. **Institution lifecycle race:** race closure/suspension with ownership
   transfer/removal. Verify lifecycle and ownership rules serialize and the
   audit outcome matches committed state.
12. **Lock ordering/deadlock handling:** exercise multi-institution account
   deactivation with reversed input ordering. Verify deterministic ordering,
   bounded retries on recognized transient errors, and explicit failure after
   retry exhaustion.
13. **Rollback and audit:** force audit insert failure and verify ownership and
   lifecycle changes roll back. Verify rejected attempts do not have a
   success audit event.

Use PostgreSQL, `TransactionTestCase` or equivalent transaction-aware tests,
independent connections/processes, synchronization barriers, bounded timeouts,
and repeatable assertions. Do not use `TestCase` transaction wrapping or one
connection in a way that masks locking. SQLite tests are not substitutes for
real concurrent PostgreSQL transactions or evidence of row-lock safety.
Repeat concurrency cases enough to detect interleavings while keeping
deterministic barriers and diagnostics. Tests must assert database state and
audit rows, not merely HTTP status.

## 7. Database enforcement boundary (OWN-04 — Proposed)

No existing decision settles how the invariant is enforced against every
write path. Keep this decision Proposed; service-level locking is an
architectural recommendation, not universal enforcement.

| Option | Advantages | Limitations and required safeguards |
|---|---|---|
| Strict service-level transactional locking | Reuses the shared User-then-Institution lock order; business rules and audit events remain explicit and testable; simpler portability and migration burden | Only protects writes that use the protocol. Direct SQL, bulk updates, alternate services, admin actions, management commands, and jobs can bypass it unless restricted, reviewed, and tested. Database credentials/permissions and write-path inventory must support the restriction. |
| PostgreSQL-specific enforcement (for example, carefully designed triggers or other database mechanisms) | Can protect selected direct/alternate writes that bypass application services; keeps some invariant checks near persisted state | Cross-row minimums are not ordinary CHECK constraints. Trigger visibility, transaction timing, multi-row statement ordering, role/account changes, audit atomicity, and lock ordering are complex; triggers can deadlock with service locks or fail to cover privileged/bulk paths if poorly designed. Must share or deliberately coordinate the lock protocol and be proven with PostgreSQL concurrency tests. |

Approval must define which writers are permitted, how direct/bulk/admin paths
are restricted or covered, whether PostgreSQL-specific enforcement is
required, and how the strategy is tested. Until then, neither option may be
described as universally enforcing the invariant.

## 8. Decisions still requiring approval

- Whether the final-owner invariant applies to every non-closed institution as
  proposed, and how institution-wide account disablement/recovery works.
- Whether creator self-service is allowed, what identity verification is
  required, and whether platform activation approval is mandatory.
- Exact owner powers, including which ordinary administration actions are
  shared with `institution_admin`; owners are not automatically
  institution-admins or unrestricted data readers.
- Whether one active owner is sufficient or a recommended/required
  two-owner succession policy should exist.
- Owner addition, target acceptance, transfer approval, relinquishment
  semantics, emergency succession evidence, and independent approval.
- Which actor may suspend/reinstate/close/reopen institutions, required reason
  codes, review deadlines, and whether closed institutions may ever reopen.
- Closure effects on billing, exports, jobs, legal holds, data retention, and
  backups.
- Audit schema, append-only enforcement, access, retention, and failed-attempt
  recording.
- PostgreSQL-specific deferred trigger/constraint defense beyond the
  shared User-then-Institution lock protocol (OWN-04).

The project-owner-selected `owner` role representation is not an approval of
these implementation details, the final-owner invariant, lifecycle
transitions, or any role/action grant. Keep the decision-register entries
Proposed until each decision is explicitly reviewed.

## Related documentation

- [Tenant and authentication decision register](./decisions/TENANT_AND_AUTH_DECISIONS.md)
- [Institution role and permission matrix](./INSTITUTION_ROLE_PERMISSION_MATRIX.md)
- [Multi-tenancy architecture](./MULTI_TENANCY.md)
- [Tenant isolation test strategy](./TENANT_ISOLATION_TEST_STRATEGY.md)
- [Engineering backlog](../engineering/ENGINEERING_BACKLOG.md)
