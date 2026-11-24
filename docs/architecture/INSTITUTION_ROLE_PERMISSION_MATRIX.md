# Institution Role and Permission Matrix

**Status:** Proposed; project-owner review and explicit approval required.
**Scope:** Function-level institution role defaults for future APIs and
services. This document does not implement permissions or approve a role/action
policy.

## Current implementation boundary

The implemented `Membership.Role` choices are:

- `institution_admin`
- `academic_staff`
- `finance_staff`
- `student`
- `guardian`

The project owner has selected a dedicated `owner` Membership role, distinct
from `institution_admin`, as the ownership representation for a future
implementation. `owner` is not yet a model choice or permission. The operation
tables below cover the five implemented roles; the proposed owner-specific
overlay below documents the additional ownership boundary without pretending
the role or its grants exist.

Only active memberships pass tenant resolution. The implemented
`InstitutionRolePermission` can enforce a view's explicit, non-empty
`allowed_membership_roles` declaration against the current membership for the
resolved institution. No production business endpoint currently uses that
permission. The tenant context endpoint establishes membership and institution
context; it does not apply role/action restrictions.

The role names and model choices are implementation facts, not evidence that
their grants have been approved. The matrix below is a proposed starting point,
not an accepted action matrix. The selected owner-role representation is
documented as a future direction, not an implemented role or approved
permission grant. No role hierarchy, API, or capability is introduced here.

## Matrix semantics

| Value | Meaning |
|---|---|
| **ALLOW** | Proposed default function-level grant, subject to active membership, resolved institution context, input validation, and any mandatory object-level scope below. |
| **DENY** | No default grant. A future exception needs an explicit reviewed policy; a client request cannot create one. |
| **CONDITIONAL** | Allow only when every condition identified for that cell is satisfied and enforced server-side. It is not a grant until the relevant capability and controls exist. |
| **DEFERRED** | No policy is proposed yet because a product, lifecycle, relationship, or platform-access decision is unresolved. Treat as denied until reviewed. |

This is a function-level baseline, never a substitute for object authorization.
Every tenant operation must use the resolved institution, revalidate current
membership and role on each request, and scope the target object and related
records to that institution. Client-supplied role, institution ID, membership
ID, or object ID never establishes authority. A read grant does not imply
create, update, delete, approval, publication, or export authority.

Codes in cells refer to the mandatory conditions below. A conditional cell is
denied unless all its listed conditions are implemented. An unlisted operation
has no implicit grant.

## Proposed owner-role overlay

The following is supplemental to the five-role operation tables, not a sixth
implemented role or a blanket addition to every matrix cell. The selected
representation is dedicated `owner`, not `institution_admin` with a different
label. One membership continues to hold one role; owners do not also hold
`institution_admin` simultaneously. If an operation is to be shared, a future
view must explicitly list both roles after policy approval.

| Operation area | Proposed `owner` treatment |
|---|---|
| Initial owner assignment, adding owners, transfer, relinquishment | CONDITIONAL (C29) |
| Routine institution settings and narrowly scoped institution administration | CONDITIONAL (C30) |
| Membership administration and owner-role changes | CONDITIONAL (C31) |
| Admissions and individual student records | DENY by owner role alone |
| Academic, enrolment, attendance, assessment, and results operations | DENY by owner role alone; separate explicit matrix grant and object-level scope required |
| Institutional ledger, transactions, approvals, and student fees | DENY by owner role alone |
| Reports and exports containing tenant/member/student/financial data | DENY by owner role alone; export is separately authorized |
| Audit-log reads or exports | DEFERRED pending an approved auditor/access policy |
| Platform support or cross-institution access | DENY |
| Institution activation, suspension, closure, and reopening | CONDITIONAL (C32) |

These are recommended defaults, not accepted owner permissions. Owner status
does not imply `is_staff`, `is_superuser`, platform authority, or unrestricted
access to sensitive records. Ownership transitions and institution lifecycle
changes must follow the recommended shared User-then-Institution PostgreSQL
lock protocol and atomic audit rules. OWN-04 recommends a PostgreSQL deferred
invariant guard in addition to the service; neither layer exists today, and
neither claims universal enforcement before approval, writer inventory, and
PostgreSQL validation.

## Proposed matrix

### 1. Institution administration and settings

| Operation | `institution_admin` | `academic_staff` | `finance_staff` | `student` | `guardian` |
|---|---|---|---|---|---|
| Read general settings | CONDITIONAL (C1) | DENY | DENY | DENY | DENY |
| Read academic configuration | CONDITIONAL (C1) | CONDITIONAL (C2) | DENY | CONDITIONAL (C3) | CONDITIONAL (C4) |
| Read finance configuration | CONDITIONAL (C1) | DENY | CONDITIONAL (C5) | DENY | DENY |
| Create/update settings | CONDITIONAL (C1) | CONDITIONAL (C2) | CONDITIONAL (C5) | DENY | DENY |
| Delete settings | DENY | DENY | DENY | DENY | DENY |
| Approve lifecycle changes, suspend, close, or reopen institution | DEFERRED | DEFERRED | DEFERRED | DEFERRED | DEFERRED |
| Export settings | DENY | DENY | DENY | DENY | DENY |

### 2. User and membership management

| Operation | `institution_admin` | `academic_staff` | `finance_staff` | `student` | `guardian` |
|---|---|---|---|---|---|
| Read membership directory | CONDITIONAL (C6) | CONDITIONAL (C7) | CONDITIONAL (C7) | DENY | DENY |
| Create/invite membership | CONDITIONAL (C8) | DENY | DENY | DENY | DENY |
| Update role or membership status | CONDITIONAL (C8, C9) | DENY | DENY | DENY | DENY |
| Remove membership | CONDITIONAL (C8, C9) | DENY | DENY | DENY | DENY |
| Approve role grant or owner transfer | DEFERRED | DEFERRED | DEFERRED | DEFERRED | DEFERRED |
| Export membership directory | CONDITIONAL (C6, C10) | DENY | DENY | DENY | DENY |

### 3. Admissions and applications

| Operation | `institution_admin` | `academic_staff` | `finance_staff` | `student` | `guardian` |
|---|---|---|---|---|---|
| Read application | CONDITIONAL (C11) | CONDITIONAL (C11) | DENY | CONDITIONAL (C12) | CONDITIONAL (C4, C12) |
| Create application | CONDITIONAL (C11) | CONDITIONAL (C11) | DENY | CONDITIONAL (C12) | DEFERRED |
| Update application | CONDITIONAL (C11) | CONDITIONAL (C11) | DENY | CONDITIONAL (C12) | DEFERRED |
| Delete/withdraw application | CONDITIONAL (C11) | DENY | DENY | CONDITIONAL (C12) | DEFERRED |
| Approve/reject application | CONDITIONAL (C11) | CONDITIONAL (C11) | DENY | DENY | DENY |
| Publish/export application data | CONDITIONAL (C10, C11) | CONDITIONAL (C10, C11) | DENY | DENY | DENY |

### 4. Student records and profiles

| Operation | `institution_admin` | `academic_staff` | `finance_staff` | `student` | `guardian` |
|---|---|---|---|---|---|
| Read student profile | CONDITIONAL (C13) | CONDITIONAL (C14) | CONDITIONAL (C15) | CONDITIONAL (C16) | CONDITIONAL (C4, C17) |
| Create student record | CONDITIONAL (C13) | CONDITIONAL (C14) | DENY | DENY | DENY |
| Update student record | CONDITIONAL (C13) | CONDITIONAL (C14) | CONDITIONAL (C15) | CONDITIONAL (C16) | DENY |
| Delete student record | DENY | DENY | DENY | DENY | DENY |
| Approve sensitive change/merge | DEFERRED | DEFERRED | DENY | DENY | DENY |
| Export student records | CONDITIONAL (C10, C13) | CONDITIONAL (C10, C14) | CONDITIONAL (C10, C15) | CONDITIONAL (C16) | CONDITIONAL (C4, C10, C17) |

### 5. Academic structure: departments, programmes, classes, and courses

| Operation | `institution_admin` | `academic_staff` | `finance_staff` | `student` | `guardian` |
|---|---|---|---|---|---|
| Read structure | CONDITIONAL (C1) | ALLOW | CONDITIONAL (C5) | CONDITIONAL (C3) | CONDITIONAL (C4) |
| Create structure | CONDITIONAL (C1) | CONDITIONAL (C18) | DENY | DENY | DENY |
| Update structure | CONDITIONAL (C1) | CONDITIONAL (C18) | DENY | DENY | DENY |
| Delete structure | DENY | CONDITIONAL (C18) | DENY | DENY | DENY |
| Approve/publish structure or catalogue | CONDITIONAL (C1, C18) | CONDITIONAL (C18) | DENY | DENY | DENY |
| Export structure | CONDITIONAL (C10) | CONDITIONAL (C10, C18) | CONDITIONAL (C10, C5) | DENY | DENY |

### 6. Enrolment and registration

| Operation | `institution_admin` | `academic_staff` | `finance_staff` | `student` | `guardian` |
|---|---|---|---|---|---|
| Read enrolment | CONDITIONAL (C13) | CONDITIONAL (C14) | CONDITIONAL (C15) | CONDITIONAL (C16) | CONDITIONAL (C4, C17) |
| Create registration | CONDITIONAL (C19) | CONDITIONAL (C19) | DENY | CONDITIONAL (C16, C19) | DEFERRED |
| Update registration | CONDITIONAL (C19) | CONDITIONAL (C19) | DENY | CONDITIONAL (C16, C19) | DEFERRED |
| Delete/withdraw registration | CONDITIONAL (C19) | DENY | DENY | CONDITIONAL (C16, C19) | DEFERRED |
| Approve enrolment | CONDITIONAL (C19) | CONDITIONAL (C19) | DENY | DENY | DENY |
| Export enrolment | CONDITIONAL (C10, C19) | CONDITIONAL (C10, C19) | CONDITIONAL (C10, C15, C19) | CONDITIONAL (C16, C19) | CONDITIONAL (C4, C10, C17, C19) |

### 7. Attendance

| Operation | `institution_admin` | `academic_staff` | `finance_staff` | `student` | `guardian` |
|---|---|---|---|---|---|
| Read attendance | CONDITIONAL (C13) | CONDITIONAL (C14) | DENY | CONDITIONAL (C16) | CONDITIONAL (C4, C17) |
| Create attendance entry | DENY | CONDITIONAL (C14, C20) | DENY | DENY | DENY |
| Update attendance entry | DENY | CONDITIONAL (C14, C20) | DENY | DENY | DENY |
| Delete attendance entry | DENY | DENY | DENY | DENY | DENY |
| Approve correction | CONDITIONAL (C20) | CONDITIONAL (C20) | DENY | DENY | DENY |
| Export attendance | CONDITIONAL (C10, C13) | CONDITIONAL (C10, C14) | DENY | CONDITIONAL (C16) | CONDITIONAL (C4, C10, C17) |

### 8. Examinations and assessment

| Operation | `institution_admin` | `academic_staff` | `finance_staff` | `student` | `guardian` |
|---|---|---|---|---|---|
| Read assessment configuration | CONDITIONAL (C1) | CONDITIONAL (C14) | DENY | CONDITIONAL (C3) | CONDITIONAL (C4) |
| Read individual pre-publication assessment data | DENY | CONDITIONAL (C14, C21) | DENY | DENY | DENY |
| Create/update assessment | DENY | CONDITIONAL (C14, C21) | DENY | DENY | DENY |
| Delete assessment | DENY | DENY | DENY | DENY | DENY |
| Approve/publish assessment or marks | DEFERRED | CONDITIONAL (C21, C22) | DENY | DENY | DENY |
| Export assessment and marks | DENY | CONDITIONAL (C10, C14, C21, C22) | DENY | DENY | DENY |

### 9. Results and transcripts

| Operation | `institution_admin` | `academic_staff` | `finance_staff` | `student` | `guardian` |
|---|---|---|---|---|---|
| Read unpublished result/transcript | DENY | CONDITIONAL (C14, C21) | DENY | DENY | DENY |
| Read published result/transcript | DENY | CONDITIONAL (C14, C21) | DENY | CONDITIONAL (C16, C22) | CONDITIONAL (C4, C17, C22) |
| Create/update result | DENY | CONDITIONAL (C14, C21) | DENY | DENY | DENY |
| Delete result/transcript | DENY | DENY | DENY | DENY | DENY |
| Approve/publish result/transcript | DEFERRED | CONDITIONAL (C21, C22) | DENY | DENY | DENY |
| Export result/transcript | DENY | CONDITIONAL (C10, C14, C21, C22) | DENY | CONDITIONAL (C10, C16, C22) | CONDITIONAL (C4, C10, C17, C22) |

### 10. Institutional finance and student fees

| Operation | `institution_admin` | `academic_staff` | `finance_staff` | `student` | `guardian` |
|---|---|---|---|---|---|
| Read finance configuration | CONDITIONAL (C1, C5) | DENY | CONDITIONAL (C5) | DENY | DENY |
| Read institution ledger/transactions | DENY | DENY | CONDITIONAL (C23) | DENY | DENY |
| Read own fee/statement | DENY | DENY | CONDITIONAL (C23) | CONDITIONAL (C16, C24) | CONDITIONAL (C4, C17, C24) |
| Create fee/transaction | DENY | DENY | CONDITIONAL (C23) | DENY | DENY |
| Update fee/transaction | DENY | DENY | CONDITIONAL (C23) | DENY | DENY |
| Delete/void transaction | DENY | DENY | DENY | DENY | DENY |
| Approve/refund/reconcile | DEFERRED | DENY | CONDITIONAL (C23, C25) | DENY | DENY |
| Export finance data | DENY | DENY | CONDITIONAL (C10, C23, C25) | CONDITIONAL (C10, C16, C24) | CONDITIONAL (C4, C10, C17, C24) |

### 11. Reports and exports

| Operation | `institution_admin` | `academic_staff` | `finance_staff` | `student` | `guardian` |
|---|---|---|---|---|---|
| Read operational/aggregate report | CONDITIONAL (C26) | CONDITIONAL (C14, C26) | CONDITIONAL (C23, C26) | DENY | DENY |
| Create report definition | CONDITIONAL (C26) | CONDITIONAL (C14, C26) | CONDITIONAL (C23, C26) | DENY | DENY |
| Update report definition | CONDITIONAL (C26) | CONDITIONAL (C14, C26) | CONDITIONAL (C23, C26) | DENY | DENY |
| Delete report definition | DENY | DENY | DENY | DENY | DENY |
| Approve sensitive/report release | DEFERRED | DEFERRED | DEFERRED | DENY | DENY |
| Export report/data | CONDITIONAL (C10, C26) | CONDITIONAL (C10, C14, C26) | CONDITIONAL (C10, C23, C26) | CONDITIONAL (C10, C16, C26) | CONDITIONAL (C4, C10, C17, C26) |

### 12. Notifications and communication

| Operation | `institution_admin` | `academic_staff` | `finance_staff` | `student` | `guardian` |
|---|---|---|---|---|---|
| Read own notification | CONDITIONAL (C27) | CONDITIONAL (C27) | CONDITIONAL (C27) | CONDITIONAL (C27) | CONDITIONAL (C4, C27) |
| Create/send communication | CONDITIONAL (C27) | CONDITIONAL (C14, C27) | CONDITIONAL (C23, C27) | DENY | DEFERRED |
| Update/cancel own or scheduled communication | CONDITIONAL (C27) | CONDITIONAL (C14, C27) | CONDITIONAL (C23, C27) | DENY | DENY |
| Delete communication/history | DENY | DENY | DENY | DENY | DENY |
| Approve broad/urgent communication | DEFERRED | DEFERRED | DEFERRED | DENY | DENY |
| Export communication history | CONDITIONAL (C10, C27) | CONDITIONAL (C10, C14, C27) | CONDITIONAL (C10, C23, C27) | CONDITIONAL (C10, C27) | CONDITIONAL (C4, C10, C27) |

### 13. Audit logs and sensitive administration

| Operation | `institution_admin` | `academic_staff` | `finance_staff` | `student` | `guardian` |
|---|---|---|---|---|---|
| Read audit events | CONDITIONAL (C28) | DENY | DENY | DENY | DENY |
| Directly create an audit event | DENY | DENY | DENY | DENY | DENY |
| Update/delete an audit event | DENY | DENY | DENY | DENY | DENY |
| Approve sensitive administrative operation | DEFERRED | DEFERRED | DEFERRED | DENY | DENY |
| Export audit events | CONDITIONAL (C10, C28) | DENY | DENY | DENY | DENY |

## Conditions required for CONDITIONAL cells

- **C1 — Settings boundary:** explicitly classify settings as general,
  academic, or finance configuration; limit reads and changes to the caller's
  assigned institutional responsibility. Lifecycle status changes remain
  separately approved, audited operations.
- **C2 — Academic configuration:** read or change only academic configuration
  the institution has delegated to the member; no platform or financial
  settings.
- **C3 — Published catalogue:** expose only intentionally published,
  non-sensitive academic information, never internal configuration.
- **C4 — Guardian relationship:** require a verified, current, revocable
  guardian-to-student relationship and the learner's approved consent/age
  policy. No such relationship model or policy currently exists; until then
  deny.
- **C5 — Finance configuration:** limit to finance-owned configuration and
  least-privilege institution-level data; no student case records or
  institution settings beyond this responsibility.
- **C6 — Membership privacy:** reveal only directory fields required for
  administration; exclude credentials, private contact data, learner records,
  and audit details unless separately authorized.
- **C7 — Work-scoped directory:** disclose only the minimum colleagues or
  contacts needed for an assigned academic or finance workflow.
- **C8 — Membership workflow:** require a separately authorized membership
  management workflow, verified target identity, allowed role assignment,
  atomic state transition, and an audit event. Invitation functionality does
  not currently exist.
- **C9 — Privilege/owner safeguards:** prohibit self-elevation and role grants
  beyond the actor's approved authority. There is no `owner` role in the model;
  apply the recommended OWN-01 invariant, succession, and transfer safeguards
  only after explicit approval and implementation.
- **C10 — Export controls:** treat export as a separate permission; scope and
  minimize fields/rows, authorize the requested format and audience, apply
  retention/download controls, audit requester and purpose, and prevent
  cross-tenant cache/file leakage.
- **C11 — Admissions workflow:** require an implemented admissions service,
  assigned duties, field-level privacy, conflict-of-interest controls, and an
  auditable decision workflow. No admissions capability currently exists.
- **C12 — Applicant's own case:** allow only authenticated self-access to the
  caller's own application after applicant identity is verified. Public
  application submission and guardian submission are unresolved and not
  authorized by membership alone.
- **C13 — Administrative need-to-know:** limit access to the minimum identity
  fields necessary for a documented administrative workflow; prohibit routine
  broad browsing of sensitive academic, health, safeguarding, or finance data.
- **C14 — Assignment and purpose:** require a current institution-scoped
  class, course, case, or staff assignment; restrict fields and actions to
  documented duties; enforce object-level scope on every query and write.
- **C15 — Finance minimum data:** expose only identity and enrollment facts
  strictly necessary for finance work; do not disclose academic, health, or
  safeguarding details.
- **C16 — Self record:** resolve the record through the authenticated user's
  own validated student relationship, not a supplied user/student ID; apply
  field-level privacy and workflow state. No student profile/relationship
  model currently exists, so all C16 cells remain denied until that relation
  and its policy are implemented and reviewed.
- **C17 — Linked learner:** require C4 plus explicit per-domain authorization
  for the linked learner's data and minimum necessary fields. Institution
  membership alone is insufficient.
- **C18 — Academic governance:** require an institution-approved academic
  governance workflow, limited assignments, uniqueness/integrity validation,
  and audit for changes to published structure. Destructive edits should be
  avoided in favor of retirement/versioning.
- **C19 — Registration lifecycle:** check eligibility, capacity, prerequisites,
  effective dates, and same-institution references; student self-service is
  limited to the caller's own permitted registration, while staff decisions
  require assigned authority and audit.
- **C20 — Attendance correction:** academic staff may record only assigned
  learners/sessions during an allowed window; later correction requires
  reason, actor audit, and independent approval where policy requires it.
- **C21 — Assessment assignment and integrity:** restrict authoring and
  individual pre-publication data to assigned academic staff; use immutable
  or versioned marks, retain change history, and prohibit student/guardian
  access before approved publication.
- **C22 — Publication workflow:** define an authorized reviewer, release
  timing, appeal/correction process, and atomic publication. No role is
  automatically a publisher solely because it is a member or administrator.
- **C23 — Finance segregation:** require finance assignment and auditable
  accounting controls; separate transaction initiation from approval or
  reconciliation, and prohibit administrators from unrestricted ledger access.
- **C24 — Personal fee information:** disclose only the authenticated
  student's own fee/statement or an explicitly authorized guardian-responsible
  account; finance privacy, balances, and payment data require separate
  product/legal policy.
- **C25 — Financial approval:** require amount/risk thresholds, separation of
  duties, independent approver, immutable transaction history, and audited
  reconciliation/refund rules. Role semantics and thresholds are unresolved.
- **C26 — Report scope:** scope queries before aggregation and export; suppress
  small-group disclosure where needed; apply the same role, assignment,
  object, and tenant boundaries as source records.
- **C27 — Communication safety:** limit recipients to authorized institution
  contacts, assigned learners, or the user's own notifications; protect
  sensitive content, consent/preferences, delivery logs, and abuse controls.
- **C28 — Audit confidentiality:** grant only a separately approved,
  institution-scoped auditor function (not currently modeled); log audit-log
  reads/exports, redact secrets and sensitive payloads, and keep audit records
  append-only.
- **C29 — Ownership transition:** require an existing authorized owner or
  separately approved recovery path, eligible target, target acceptance,
  OWN-01 available-owner invariant, shared User-then-Institution transaction
  protocol, and append-only audit. Initial bootstrap requires a verified and
  approved provisioning request plus explicit owner acceptance before the
  Institution and Membership are atomically created; do not automatically
  assign the requester as owner or infer ownership from an existing
  `institution_admin`. No client-selected role or unaudited self-elevation.
- **C30 — Owner administration:** permit only the specific routine settings
  and administration operations explicitly approved for owners. `owner` does
  not inherit all `institution_admin` grants; the operation's permission must
  list owner explicitly.
- **C31 — Owner membership authority:** require the approved owner/member
  governance policy, prevent self-elevation, preserve the OWN-01 final-owner
  invariant (including global account deactivation across all institutions),
  require explicit target acceptance for owner assignment, and audit
  initiator, approver, target, reason, and outcome. This does not create an
  invitation or membership-management workflow.
- **C32 — Owner lifecycle authority:** require the approved lifecycle
  transition table, independent approval where specified, required
  verification/remediation, final-owner protection (including atomic owner
  restoration/assignment with an independently approved `closed` → `suspended`
  recovery), the shared lock protocol, and an append-only audit record. No
  lifecycle endpoint currently exists.

## Cross-cutting boundaries and unresolved questions

1. **Sensitive student information:** an institutional role is not a blanket
   entitlement. Apply purpose limitation, field minimization, assignment and
   object-level checks; keep health, safeguarding, identity documents, and
   other specially protected data separately classified with explicit policy.
2. **Student self-access:** self-service must derive identity from the
   authenticated principal and a server-verified student relationship.
   Supplying another student's identifier must never broaden access.
3. **Guardian access:** `guardian` exists as a membership role, but the
   repository has no guardian-to-student relationship, consent, verification,
   or revocation mechanism. All proposed linked-learner permissions are
   conditional and must remain denied until those decisions and controls exist.
4. **Results:** deny student/guardian access before publication. After
   publication, consider only self or verified linked learner records. Define
   who may publish, correction/appeal behavior, and whether publication is
   institution-wide or cohort-specific.
5. **Financial visibility:** finance staff may need ledger access; teaching
   roles and institution administrators do not thereby gain transaction
   access. Students and guardians need separately defined statement and
   payment visibility, responsibility, and disclosure rules.
6. **Membership administration:** the existing `institution_admin` role is
   not equivalent to the selected future `owner` role. Approve who may invite,
   change roles, suspend, remove, or reinstate members, and forbid
   self-elevation. The current schema does not yet model an owner or
   final-owner protection.
7. **Audit logs:** audit read/export is sensitive and should be a separately
   authorized, audited capability. The repository has no audit model or
   auditor role. The matrix denies direct role-based writes and changes to
   audit records; trusted application services should generate append-only
   audit events as side effects of authorized operations, not through a user
   permission grant.
8. **Cross-institution access:** deny by default, including for a user with
   memberships in multiple institutions. Each request resolves one tenant;
   roles and object references in another institution grant no authority.
9. **Platform support:** no platform-support role or just-in-time grant exists
   in `Membership.Role`. Institution administration never confers
   cross-tenant support access. Define a separate, time-bounded, purpose-bound,
   audited platform access mechanism before support tooling.
10. **Unimplemented domains:** the matrix is prospective. Admissions, academic,
    enrolment, attendance, assessment, results, finance, reports, and
    communication APIs are not implemented; no matrix row should be described
    as a shipped permission.

## Approval checklist

Before using this matrix to authorize a business endpoint, the project owner
must review and explicitly decide:

- Which conditional grants and conditions are acceptable for each operation.
- Whether student/guardian relationships and any consent/age rules will exist.
- Whether the selected dedicated `owner` role's proposed powers and
  final-owner transfer safeguards are acceptable.
- Who may make, review, and publish academic, attendance, assessment, results,
  and finance changes; including segregation-of-duties thresholds.
- Which student data categories require additional restrictions and retention.
- Whether reports/exports require separate approval, audit, and recipient
  controls.
- The institution-level audit reader, retention, redaction, and export policy.
- Whether and how platform support access is authorized separately from
  institution roles.

Until approved, use default deny: `CONDITIONAL` and `DEFERRED` cells do not
grant access, and no role is inherited across institutions or operations.

## Related documentation

- [Tenant and authentication decision register](./decisions/TENANT_AND_AUTH_DECISIONS.md)
- [Multi-tenancy architecture](./MULTI_TENANCY.md)
- [Tenant isolation test strategy](./TENANT_ISOLATION_TEST_STRATEGY.md)
- [Engineering backlog](../engineering/ENGINEERING_BACKLOG.md)
