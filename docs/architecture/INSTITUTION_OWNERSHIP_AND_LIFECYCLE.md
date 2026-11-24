# Institution Ownership and Lifecycle Architecture

**Status:** Recommended architecture pending explicit project-owner approval.
The project owner selected a dedicated `owner` membership role distinct from
`institution_admin`; the role and workflows are not implemented. Decision
statuses remain Proposed until approved. Do not treat these recommendations
as deployed controls.

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

## 2. Institution provisioning and initial owner assignment

### Current implementation boundary

The current custom User has a unique email and Django's active-account flag;
login rejects inactive accounts. There is no email-verification state,
institution request/verification/approval workflow, platform-provisioning
authority, owner-acceptance flow, or provisioning audit trail. The
recommendations below require new functionality and must not be interpreted
as current checks or permissions. Do not enable self-service provisioning
until verified-email and the authorized review/audit boundaries exist.

### Recommended workflow

Treat these as separate, attributable milestones, not synonyms:

1. **Request:** An authenticated, active account submits a provisioning
   request. Require control of a verified email address and enough evidence to
   establish the creator's identity and authority to represent the named
   institution. The creator need not be the eventual owner and receives no
   membership or tenant authority merely by filing the request.
2. **Verification:** A designated platform verifier checks that the
   institution exists and that the creator is authorized to request it.
   Recommended evidence is one authoritative source establishing institutional
   identity plus a separately sourced official contact or authority record
   confirming the representative. Email-domain control alone is insufficient
   proof of authority. Record evidence references and findings, not copies of
   sensitive documents in the audit trail. Conflicting or inadequate evidence
   pauses the request for manual review; it is not treated as verified.
3. **Initial-owner acceptance:** Identify one proposed owner by account,
   verify that person's email/control and authority, and obtain an explicit,
   one-time acceptance of the `owner` role for this institution before
   provisioning. Acceptance must state the institution and role, use a
   short-lived single-use challenge stored only as a digest, and be made by
   the authenticated eligible owner account. If creator and proposed owner are
   the same person, require a distinct affirmative owner-acceptance action;
   request submission alone is not acceptance. Do not create an owner from an
   unverified email or assign a role supplied by the client.
4. **Approval:** A separately authorized platform provisioning approver
   reviews the verification record, duplicate/conflict search, owner
   acceptance, and request outcome, then explicitly approves or rejects
   provisioning. The approver must differ from the creator and proposed owner.
   Record verification and approval as distinct decisions; use a second
   independent platform approver for exceptions, conflicting claims, or
   overrides. No platform role, staff permission, support interface, or
   approval capability currently exists. A future least-privilege
   platform-only authority must be designed separately from institution
   membership and Django `is_staff`/`is_superuser`.
5. **Provisioning:** Only after successful verification, owner acceptance,
   and approval, create the Institution with status `draft` and its initial
   active owner Membership in one transaction. Derive the owner from the
   accepted request; reject client-selected roles. Insert the successful
   provisioning and initial-assignment audit events and mark the request
   provisioned in the same transaction. If any write, including audit
   insertion, fails, roll back both rows and record the failed attempt/request
   outcome separately after rollback; never leave an institution without its
   initial available owner or a success-shaped audit event.
6. **Activation:** Provisioning approval does not activate the institution.
   After required setup is complete, the active owner separately requests
   activation and an independent platform approver approves it under the
   lifecycle rules in section 5. Keep the existing status vocabulary:
   verification/request states belong to the separate provisioning workflow,
   not a new Institution status. A `draft` context remains governed by the
   existing resolver but does not authorize business APIs.

The provisioning request should be a separate future workflow record, not an
extra meaning for `Institution.status` and not a partially created tenant.
Recommended states are `pending_verification`, `pending_owner_acceptance`,
`pending_approval`, `rejected`, `expired`, `cancelled`, and `provisioned`;
only permitted forward transitions are allowed, with actor, timestamp, and
reason recorded. Set request/challenge expiry, evidence-retention periods,
and resubmission limits through explicit product/legal policy before launch.
Before an Institution exists, provisioning audit entries are request-scoped
and keyed by an immutable request ID; successful creation links that history
to the new institution. Keep provisioning evidence in a restricted evidence
store and place only non-sensitive references and decisions in audit records.

### Failed, abandoned, duplicate, and conflicting requests

- Make request submission idempotent: a retry with the same idempotency key
  returns the existing request, not a second institution. Apply rate limits
  and abuse monitoring. A genuinely new attempt after a terminal outcome gets
  a new request ID and repeats verification.
- Expire unaccepted owner challenges and abandoned requests; revoke the
  challenge on rejection, cancellation, replacement, or expiry. Do not retain
  raw challenge tokens. Keep a minimal outcome/audit record under the approved
  retention policy.
- Search for an existing institution using authoritative identity evidence
  and the canonical slug before approval. A name or slug match alone is not
  proof that the requester controls that institution. A suspected duplicate
  or competing ownership claim is placed on hold and independently reviewed;
  never auto-merge institutions, reassign their owner, or disclose private
  tenant information to the requester. A slug collision after verified
  identity requires a reviewed alternate slug, not a second tenant.
- A database uniqueness conflict or failed final transaction creates no
  partial Institution/Membership. Return an explicit outcome, preserve the
  request for an authorized retry where appropriate, and record the conflict
  without disclosing another institution's private details.
- A creator may cancel before provisioning. After provisioning, abandonment
  follows the existing institution lifecycle and owner succession rules; it
  does not delete the institution or waive the available-owner invariant.

### Existing institution owner assignment

Before enabling owner-dependent workflows, perform a reviewed, institution-
by-institution assignment; never infer an owner by promoting all or any
`institution_admin` memberships. Recommended migration sequence:

1. Inventory every institution and its status, current memberships, account
   availability, duplicate/conflicting identity claims, and pending legal or
   operational holds. Closed institutions are exempt from the non-closed
   invariant but must receive an owner through the recovery process before
   reopening.
2. Collect an explicit proposed owner for each `draft`, `active`, and
   `suspended` institution. Verify the person's identity and authority using
   the same evidence standard as provisioning; obtain their explicit
   acceptance and independent platform approval. Do not accept an inactive or
   unverified account.
3. Produce a reviewed assignment manifest mapping institution ID to accepted
   owner user ID, evidence reference, verifier, approver, and decision. Use
   two-person review for ambiguous or contested assignments. Resolve
   conflicts before applying changes; do not choose the most privileged or
   most senior-looking current member by default.
4. After the owner-role schema migration, apply each institution's assignment
   in an atomic, idempotent transaction under the approved lock protocol.
   Promote an existing membership only with explicit approval and record its
   previous/new role; because membership has one role, the former role is
   replaced, not retained implicitly. If the person has no membership, create
   the active owner membership in the same transaction. Preserve suspended
   or removed membership history; reactivate only through an explicitly
   approved assignment.
5. While backfill is incomplete, keep owner-dependent APIs and writes disabled
   and prevent uncoordinated owner-affecting changes, using a defined
   maintenance/write-freeze window for the backfill. Validate that every
   non-closed institution has at least one available owner before enabling
   the invariant guard or owner workflows. If any institution is unresolved,
   do not declare the invariant established or enable workflows that rely on
   it; resolve it through the recovery path first.

Each assignment must have an auditable actor, independent approver, target,
institution, prior/new membership state, evidence reference, reason, and
outcome. The current model has no `owner` value or audit record; this is a
future migration and controlled backfill, not a description of existing data.

### Alternatives and trade-offs

- **Immediate self-service creation/activation:** lowest friction, but exposes
  the service to impersonation, institution squatting, duplicate tenants, and
  fraudulent owner claims. Do not recommend activation without independent
  verification and approval.
- **Provision a `draft` Institution as soon as a request arrives:** simplifies
  the request UI but leaves abandoned/unverified tenant rows and complicates
  slug conflicts, cleanup, and the owner invariant. Prefer a separate request
  record and create the Institution only after all gates pass.
- **Platform-only request intake:** offers stronger control but adds
  operational delay and excludes self-service. Recommend authenticated
  self-service requests subject to the same evidence and approval gates;
  allow a future authorized provisioning service to submit the same
  attributable request on an institution's behalf.
- **Automatically assign the creator or highest-privilege existing member:**
  convenient but does not establish authority or consent. Require explicit
  owner selection, acceptance, and approval instead.
- **Single reviewer versus separation of duties:** one reviewer is faster;
  separate verification and approval, and a distinct creator/owner, reduce
  collusion and error but increase staffing cost. Recommend independent
  approval and a second approver for exceptions; the project owner must decide
  whether all standard verifications also require a distinct verifier.

## 3. Ownership representation

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
5. **Bootstrap assignment.** Recommended default: create an institution in
   `draft` and assign its initial active owner membership in the same database
   transaction. The owner is the authenticated creator or a person selected
   by an explicitly authorized provisioning actor; if the selected owner is
   not the creator, require that person's explicit acceptance. Ignore/reject
   a client-provided role. Creator eligibility, verification, self-service
   abuse controls, and platform provisioning authority remain product-owner
   decisions. Email verification is not currently implemented.
6. **Ordinary administration.** Recommend permitting owners to perform a
   reviewed set of routine institution-administration operations, but not
   treating `owner` as a synonym for `institution_admin`. Each operation must
   list both roles explicitly where appropriate. Sensitive administrator
   grants remain denied unless separately approved.
7. **Multiple owners and transfer.** Support more than one active owner to
   allow continuity. A transfer promotes an eligible active member to owner
   before demoting/removing the outgoing owner, in one transaction. Require
   the incoming owner's explicit acceptance and approval by an existing
   authorized owner or the separately approved recovery authority. Audit the
   old/new owner, reason, initiator, approver, and outcome. The outgoing owner
   may remain an active `institution_admin` only if that is the explicitly
   selected new role.
8. **Relinquishment.** An owner may demote or leave only if another available
   active owner remains after the transaction. Otherwise require an atomic
   transfer/add-owner operation first.
9. **Suspension, removal, and disabled accounts.** An owner membership with
   `suspended` or `removed` status does not count toward the invariant. An
   inactive global user (`User.is_active=False`) is unavailable and does not
   count either. Preserve removed membership history. Before global account
   deactivation, examine every non-closed institution where the user has an
   owner membership. Reject the entire deactivation if any such institution
   would have no other available owner; otherwise deactivate the account
   without changing membership states. Do not accept a client-supplied subset
   of affected institutions or automatically promote another member. Account
   reactivation does not change memberships; an unchanged active owner
   membership becomes available again when the account is active.
10. **Succession and recovery.** One available owner is the invariant; a
    second active owner is recommended for continuity but is not mandatory.
    If no available owner remains because of legacy data, compromise, or an
    exceptional operational failure, freeze ordinary ownership/lifecycle
    changes and use a separate platform recovery path. Require identity and
    authority evidence, an eligible successor's explicit acceptance, two
    distinct platform actors (requester/executor and independent approver),
    a reason, and a recorded review. The recovery transaction restores or
    assigns an owner and records its audit event atomically. For a closed
    institution, recovery and `closed` → `suspended` reopening are one
    transaction; absent an eligible accepted successor or independent
    approval, leave it closed. Do not silently elevate an administrator.
    No recovery role or workflow exists today.

## 4. Final active-owner invariant

### Recommended invariant

After the owner-role migration and before owner-dependent workflows are
enabled, establish this target invariant: at every committed database state,
each institution whose status is `draft`,
`active`, or `suspended` must have at least one Membership for that institution
with `role = owner`, `status = active`, and an associated User with
`is_active = true`. These are the only qualifying values; an
`institution_admin`, suspended/removed membership, or inactive account does
not count. The institution and initial owner membership must be created in
one transaction. Preserve an available owner through `draft`, `active`, and
`suspended` so reinstatement retains an accountable owner.

Immediately before an authorized closure commits, an available owner must
request closure and be identified in the closure event. Once status is
`closed`, the minimum-owner invariant no longer applies; subsequent owner
membership/account cleanup is governed by the approved retention policy.
Reopening is a distinct recovery operation and must not commit a non-closed
institution without an available owner.

This invariant does not grant tenant API access while an institution is
suspended or closed. The existing resolver continues to govern ordinary
tenant access.

### Global account deactivation

Deactivation is a change to the user's availability in every institution, not
a per-institution membership operation. In one transaction, lock the target
User, then re-query all institutions in which that user currently has an
owner membership, and lock every affected non-closed Institution in UUID
order. Re-read all memberships and owner account states after the institution
locks. Permit deactivation only if each affected institution retains at least
one other available owner; otherwise reject the whole operation with no
account or membership change. Closed institutions do not block deactivation.
Do not silently suspend memberships, promote another member, or partially
disable an account based on only some institutions. Reactivation restores
availability for unchanged active owner memberships but does not restore
suspended or removed memberships.

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

When both operations follow this protocol, it closes the
account-deactivation/assignment race because they serialize on the same
global User row for the user whose availability is changing. If deactivation
wins, assignment waits and then sees the account disabled when it revalidates;
if assignment wins, deactivation waits, re-queries owner memberships after
obtaining the User lock, discovers the new institution dependency, and locks
that institution before validating whether deactivation can proceed. It
cannot miss a committed assignment to that user by relying on an earlier
institution list. This is a property of the proposed protocol, not a guarantee
of current code or uncoordinated writers.

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
convention alone do not prove universal enforcement. OWN-04 recommends a
service protocol plus a PostgreSQL deferred invariant guard; the guard's
design, approval, and coverage remain unresolved. Do not claim universal
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

## 5. Institution lifecycle

### Existing values and compatibility

The model currently uses `draft`, `active`, `suspended`, and `closed`; the
database check constraint accepts exactly these values. Some older proposal
text refers to `onboarding`. This proposal uses `draft` for the pre-activation
state and does not add or rename a status. Treat `onboarding` as proposed
product terminology that maps to existing `draft`, not as a current status.
Adding a new status later would require a reviewed model/constraint migration,
data mapping, API/schema update, and lifecycle tests. No status migration is
proposed here.

### Recommended transition table

This is the recommended contract, not an implemented or approved workflow.
“Platform approver” means a separately authorized platform governance actor;
it is not an institution membership role, `is_staff`, or `is_superuser`, and no
such actor/workflow currently exists. A transition that requires platform
approval must be approved by a different human actor from its requester and
executor. An emergency suspension may execute before review only to contain an
immediate risk; a different platform approver must review it within the
product-owner-approved deadline.

| From | To | Initiator | Approver / executor | Required preconditions and outcome |
|---|---|---|---|---|
| Not created | `draft` | Authenticated eligible creator requests creation, or authorized provisioning service provisions | Creation service atomically creates the institution and initial owner membership | Eligible creator/provisioner; owner is the creator or has explicitly accepted; no public business access is implied. |
| `draft` | `active` | Active owner requests activation | Independent platform provisioning approver verifies and approves | Available active owner; identity/institution checks and required configuration complete. |
| `draft` | `suspended` | Platform security/compliance initiates | Authorized platform actor executes; separate approver reviews | Immediate, evidenced security/compliance hold; ordinary tenant routes become unavailable. |
| `draft` | `closed` | Active owner requests cancellation | Independent platform approver approves | Provisioning obligations and retention/legal/export obligations reviewed; active owner recorded. |
| `active` | `suspended` | Owner may request; platform security/compliance may initiate emergency action | Authorized platform actor executes; independent approver reviews an emergency action | Recorded reason, scope, actor, evidence, and remediation path. Ordinary tenant access is blocked. |
| `active` | `closed` | Active owner requests closure | Independent platform/compliance approver approves | Retention, legal hold, billing/contract, export, backup, and dependent-workflow review; available owner and all approvals recorded. |
| `suspended` | `active` | Active owner requests reinstatement | Independent platform approver verifies remediation and approves | Suspension cause resolved; available owner and institution checks pass; reinstatement event recorded. |
| `suspended` | `closed` | Active owner requests closure, or platform/legal process initiates it | Independent platform/compliance approver approves | Closure obligations and retention/legal review complete; available owner recorded for an owner-requested closure. |
| `closed` | `suspended` | Authorized platform recovery process only | Different platform approver independently approves the recovery/reopen request | Restore or assign an eligible, accepting available owner and transition in the same transaction; record evidence, reason, actors, and outcome. If preconditions fail, leave closed. |
| `closed` | `draft` or direct `active` | Not allowed | Not applicable | No direct transition. A distinct recovery may only reopen to `suspended`; ordinary approval then governs `suspended` → `active`. |

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
  the same transaction. If no owner is available, a separately approved
  recovery must verify and assign/restore an eligible person's accepted owner
  membership and reopen atomically. Otherwise, keep the institution closed.
  There is no direct `closed` → `active` path.
- Institution lifecycle changes do not silently change Membership status or
  session state. Each request still resolves current institution and
  membership status; account deactivation and session invalidation follow
  their own approved contract.
- `closed` is terminal for ordinary workflows. Only the independent,
  evidence-based platform recovery process may reopen it, staged through
  `suspended`; an existing owner cannot bypass the platform approval.

## 6. Required audit events

The future audit store should be append-only. Pre-provisioning events are
request-scoped and linked to institution-scoped events at creation; each event
must include a stable event ID, UTC timestamp, institution ID when one exists,
actor identity
(user or explicitly identified system/platform actor), action, target
membership/user where applicable, previous and resulting role/status,
reason/purpose, outcome, and request/correlation ID. Record the initiator,
executor, and approver as distinct attributed principals where their roles
differ; one person must not satisfy a required independent approval. A global
account deactivation affecting multiple institutions must be traceable from
each affected institution, with one correlation ID linking the atomic
operation. Record only the minimum metadata needed; never store credentials,
session tokens, invitation secrets, or unnecessary student payloads.

| Event | Required detail |
|---|---|
| Provisioning request | Request ID, creator, submitted institution identifiers, idempotency outcome, timestamps, and request status; before institution creation this is request-scoped, not tenant-scoped |
| Institution verification | Verifier, evidence references/source, identity and representative-authority findings, conflicts, decision, and timestamp |
| Provisioning approval/rejection | Approver distinct from creator and proposed owner, verification/owner-acceptance references, decision, reason, and timestamp |
| Initial owner acceptance | Authenticated target owner, institution/request, accepted role, challenge outcome and timestamp; never the raw token |
| Institution provisioning and initial owner assignment | Creator/provisioning actor, verifier, approver, initial owner, institution, creation status, evidence/acceptance references, and atomic transaction outcome |
| Provisioning failure, cancellation, or expiry | Request actor or system reason, request ID, terminal state, conflict category, and timestamp without exposing another institution |
| Owner addition | Initiator, approving owner/platform actor, target identity, prior/new membership state, reason, and acceptance |
| Ownership transfer | Outgoing and incoming owner IDs, initiator, approver(s), both membership changes, reason, and atomic outcome |
| Owner relinquishment/removal | Actor, affected owner, successor owner(s), resulting membership role/status, reason, and invariant check outcome |
| Owner suspension/reinstatement | Actor, affected owner, reason/evidence, approver, prior/new status, and resulting available-owner count |
| Global account deactivation | Account actor/approver, target user, every affected institution, owner-state validation, reason, and atomic outcome |
| Ownership succession/recovery | Requester, unavailable owner(s), evidence, independent approver, successor identity, scope/expiry if platform-assisted, and review outcome |
| Institution activation | Owner initiator, independent approver, setup/verification references, old/new status, owner at activation, and outcome |
| Institution suspension | Initiator/executor, reason/evidence, scope, approver or emergency-review deadline, old/new status, and outcome |
| Institution reinstatement | Requester, remediation summary/reference, approver, old/new status, and outcome |
| Institution closure | Initiator, approver(s), reason, retention/legal/export checks, active owner at closure, old/new status, and outcome |
| Institution reopening | Platform recovery actor, independent approver, justification, old/new status (`closed` → `suspended`), and outcome |

Successful state changes and their success audit records commit in the same
database transaction; failure to insert the event rolls back the state change.
After a rejected transaction, any separately recorded security event must be
explicitly marked as a failed attempt and must never represent a committed
change. Ordinary application database roles may insert/read audit events as
authorized but must not update/delete them. Use database privileges and an
immutable-write guard, separate table ownership from the application role, and
restrict privileged maintenance. A database owner/superuser can bypass these
controls, so privileged access must be tightly limited and independently
reviewed. Audit reader/export authorization, retention, external tamper
evidence, and emergency access require separate policy decisions.

## 7. PostgreSQL concurrency test strategy

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

## 8. Database enforcement boundary (OWN-04 — Proposed)

Recommended target: require both service-level transactional authorization and
audit, and a PostgreSQL-specific deferred invariant guard. Neither exists in
the application today. OWN-04 remains Proposed until the project owner
approves permitted writers and PostgreSQL tests prove the chosen database
mechanism.

| Option | Advantages | Limitations and required safeguards |
|---|---|---|
| Strict service-level transactional locking | Reuses the shared User-then-Institution lock order; business authorization and audit attribution remain explicit and testable; simpler portability and migration burden | Guarantees the invariant only for writes that use the protocol. Direct SQL, bulk updates, alternate services, admin actions, commands, and jobs can bypass it unless prohibited or routed through the service. |
| PostgreSQL-specific deferred invariant guard | Can reject covered transactions whose final state violates the invariant, including selected direct/bulk DML that bypasses application services | Does not authorize actors or supply trustworthy initiator/approver audit. Coverage requires checks for Membership writes, `User.is_active`, and Institution creation/status changes, including every affected institution. Cross-row checks are not ordinary `CHECK` constraints. Trigger timing, concurrent visibility, multi-row ordering, deadlocks, transaction-role bypasses, and restore/replication behavior require explicit PostgreSQL design and tests. |
| Hybrid (recommended) | Service provides authorization, validation, deterministic User-then-Institution locks, and atomic audit; database guard provides an independent final-state check for covered writes | Does not cover privileged database-owner/superuser bypass, disabled triggers, or untested maintenance/restore paths. Database roles must restrict ordinary DML bypasses, and all permitted writers must be inventoried and verified. |

The service guarantee applies only when every supported application path uses
the protocol. A database guard can extend the invariant check to ordinary
covered SQL writes but cannot make a bypassing writer authorized or correctly
audited. The guard must validate the transaction's final state, allow valid
intermediate states within bootstrap/transfer/recovery transactions, and
serialize checks consistently with service locks. It must include global
account deactivation across all affected non-closed institutions. A plain
Membership constraint/trigger alone cannot account for changes to
`User.is_active`; a plain account trigger cannot prove membership/lifecycle
consistency. No enforcement guarantee may be claimed until concurrent tests
prove the complete set of permitted paths, including bulk statements and
failures.

## 9. Recommendations and remaining approval

The recommendations in OWN-01 through OWN-04 and INS-01/02 are individually
specified in the decision register; none is marked Accepted. The implementation
contract recommended here is: dedicated `owner` distinct from
`institution_admin`; one accepted, available owner for each non-closed
institution; global deactivation rejected if it would orphan any such
institution; no automatic promotion; exceptional recovery by an independently
approved platform process; ordinary lifecycle transitions initiated by an
owner and approved/executed by a separate platform actor; closure terminal
except for audited recovery to `suspended`; service transactions plus a
PostgreSQL final-state guard; and atomic, protected audit records.

The project owner must still decide:

- Creator eligibility, verification/evidence, abuse controls, and whether
  self-service creation is allowed.
- Which platform governance actors can independently approve activation,
  suspension review, closure, reinstatement, and break-glass recovery; the
  emergency-review deadline and evidence standard.
- How each existing institution receives its initial owner. Do not infer this
  from `institution_admin`; resolve every institution explicitly before
  migration.
- Which ordinary administration actions, if any, are shared with
  `institution_admin`; the owner role itself confers no implicit grants.
- Permitted database writers, database-role restrictions, guard feasibility,
  controlled bypass/restore procedure, and required PostgreSQL proof.
- Closure effects, legal holds, billing, export, backup, personal-data and
  audit retention, audit readers, and external tamper evidence.

Decision status is not implementation status: these recommendations do not
change the current models, session authentication, tenant resolver, or
authorization behavior.

## Related documentation

- [Tenant and authentication decision register](./decisions/TENANT_AND_AUTH_DECISIONS.md)
- [Institution role and permission matrix](./INSTITUTION_ROLE_PERMISSION_MATRIX.md)
- [Multi-tenancy architecture](./MULTI_TENANCY.md)
- [Tenant isolation test strategy](./TENANT_ISOLATION_TEST_STRATEGY.md)
- [Engineering backlog](../engineering/ENGINEERING_BACKLOG.md)
