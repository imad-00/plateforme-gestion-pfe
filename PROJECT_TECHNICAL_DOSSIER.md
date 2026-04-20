# PFE Management Platform Backend
## Technical Dossier (Sprint 0 to Sprint 4)

Version date: 2026-04-19

---

## 1) Project Context and Sprint 4 Intent

This backend serves a PFE (Final Engineering Project) institutional workflow platform.

Sprint 0-3 already delivered a working technical base and a first domain slice (auth, academic year governance, subject lifecycle).

Sprint 4 is a **domain realignment sprint**, not a feature-expansion sprint.

Its purpose is to refactor the architecture toward the updated domain model while preserving validated foundations.

---

## 2) Technology Stack (Preserved)

- Django 5
- Django REST Framework
- SimpleJWT
- PostgreSQL
- Redis + Celery
- MinIO (S3 compatible)
- drf-spectacular
- pytest + pytest-django
- Docker Compose

Why unchanged:

- stack remains technically sound
- no infrastructure redesign was required for domain realignment
- focus stayed on domain and access model evolution

---

## 3) Architecture Baseline (Still Valid)

Main apps:

- `accounts`: identity, auth, profiles, platform access grants, account admin APIs
- `academics`: academic year governance
- `campaigns`: campaign phase domain (new in Sprint 4)
- `topics`: subject lifecycle and catalog
- placeholders kept for future: teams, assignments, deliverables, defenses, archives, audit, projects

Global API prefix remains `/api/`.

---

## 4) Sprint 4 Realignment Summary

## 4.1 Why refactor was needed

Before Sprint 4, the model depended mostly on:

- `global_role`
- `is_active`/`is_archived` booleans
- teacher/student profile assumptions

Updated requirements introduced a clearer domain split:

1. business identity (who the actor is)
2. platform privilege (who can administrate platform-level operations)
3. contextual roles (future sprint scope)

Sprint 4 therefore introduced foundational entities for this split while keeping backward compatibility.

## 4.2 What changed concretely

- `User` now includes:
  - `business_identity`
  - `account_status`
- new `PlatformAccessGrant` model for platform admin privileges
- new `CampaignPhase` model linked to `AcademicYear`
- `Subject` evolved with:
  - `ASSIGNED` state
  - optional attachment metadata fields

## 4.3 What stayed intentionally unchanged

- login by matricule/email
- existing auth endpoints
- existing academic year endpoints
- existing subject workflow endpoints
- archive-not-delete philosophy

## 4.4 Sprint 4 execution plan (implemented)

The Sprint 4 refactor was executed in controlled steps:

1. Domain model realignment:
   - `User` extended with `business_identity` and `account_status`
   - `PlatformAccessGrant` introduced for platform-level privileges
   - `CampaignPhase` introduced for campaign governance windows
   - `Subject` extended with `ASSIGNED` and attachment metadata
2. Validation and permission alignment:
   - account-access checks now support `account_status`
   - permissions prefer active platform grants
   - legacy fallback kept but restricted to avoid over-granting
3. API and migrations:
   - admin/super-admin APIs added for grants and campaign phases
   - non-destructive migrations and data backfill delivered
4. Testing and documentation:
   - integration tests extended on grants, phases, subject transitions
   - technical dossier updated to reflect implemented vs prepared scope

---

## 5) Complete Domain Model Inventory (Post Sprint 4)

## 5.1 Implemented core models

### App `accounts`

#### `User`

Core auth anchor remains the same table.

Key fields now:

- identity/auth: `matricule`, `email`, password, names
- legacy privilege: `global_role` (kept for compatibility)
- new identity axis: `business_identity`
  - `STUDENT`
  - `TEACHER`
  - `ADMINISTRATIVE_STAFF`
  - `EXTERNAL_SUPERVISOR`
- new lifecycle axis: `account_status`
  - `ACTIVE`
  - `SUSPENDED`
  - `ARCHIVED`
- compatibility flags: `is_active`, `is_archived`, `is_staff`, `is_superuser`

Compatibility strategy:

- `account_status` is now explicit domain status
- legacy booleans are still present and synchronized for safe transition

#### `StudentProfile`

- still present
- still linked to `AcademicYear`
- used by current implemented flows

#### `TeacherProfile`

- still present
- used by current implemented flows

#### `AdministrativeStaffProfile` (new)

- foundational profile model for staff-type users

#### `ExternalSupervisorProfile` (new)

- foundational profile model for external supervisors

#### `PlatformAccessGrant` (new)

Separates platform privilege from business identity.

Key fields:

- `user`
- `access_level`: `ADMIN`, `SUPER_ADMIN`
- `granted_by`
- `granted_at`
- `revoked_at`

Rules:

- only `TEACHER` and `ADMINISTRATIVE_STAFF` identities may receive grants
- one active grant per user at a time
- grants are revocable (not hard deleted)

### App `academics`

#### `AcademicYear`

Still the institutional source of truth.

Current rules kept:

- one active year at a time
- archived year cannot be active
- activating a year archives/deactivates previous years

Sprint 4 note:

- computed calendar helper remains utility only
- business decisions rely on DB active year

### App `campaigns`

#### `CampaignPhase` (new)

Introduced to prepare campaign-driven workflow.

Fields:

- `academic_year`
- `phase_type`
- `start_at`
- `end_at` (nullable)
- `display_order`
- `is_archived`

Supported phase types:

- `ACCOUNT_SETUP`
- `SUBJECT_SUBMISSION_AND_REVIEW`
- `FIRST_WISH_SELECTION`
- `RESULTS_AND_APPEALS`
- `SECOND_WISH_SELECTION`
- `FINAL_RESULTS_AND_ASSIGNMENT`
- `WORK_PERIOD`
- `DEFENSE_PERIOD`

### App `topics`

#### `Subject`

Sprint 3 lifecycle preserved and extended.

Now includes:

- new status: `ASSIGNED`
- optional attachment metadata:
  - `attachment_key`
  - `attachment_original_name`
  - `attachment_mime_type`
  - `attachment_size_bytes`

Status set:

- `DRAFT`
- `SUBMITTED`
- `APPROVED`
- `REJECTED`
- `ASSIGNED`
- `ARCHIVED`

---

## 6) Identity and Access Strategy (Revised)

## 6.1 Business identity

Who the person is in the institution:

- Student
- Teacher
- Administrative Staff
- External Supervisor

## 6.2 Platform privilege

Who can administrate platform-level operations:

- modeled by `PlatformAccessGrant`
- independent from business identity

## 6.3 Transitional compatibility

- old `global_role` is still present
- permission layer now prefers platform grants
- fallback to legacy role is kept for records without grant history
- if a user has grant history and no active grant, fallback is not used (revocation remains effective)

## 6.4 Contextual roles

Not implemented yet (future sprint).

Prepared by architecture only.

---

## 7) Permissions Refactor (Sprint 4)

Current permission model distinguishes:

- authenticated + active account
- platform admin privileges
- super admin privileges
- teacher-or-above access for teacher domain endpoints

Important change:

- permissions no longer depend only on `global_role`
- platform access grants are now first-class

---

## 8) API Surface (Post Sprint 4)

## 8.1 Preserved endpoints

- `/api/auth/login/`
- `/api/auth/refresh/`
- `/api/auth/me/`
- `/api/admin/academic-years/...`
- `/api/admin/users/...`
- `/api/super-admin/admins/`
- `/api/teacher/subjects/...`
- `/api/admin/subjects/...`
- `/api/subjects/...`

## 8.2 New Sprint 4 endpoints

### Platform access

- `GET /api/admin/platform-access-grants/`
- `POST /api/super-admin/platform-access-grants/`
- `POST /api/super-admin/platform-access-grants/{id}/revoke/`

### Campaign phases

- `GET /api/admin/campaign-phases/`
- `POST /api/admin/campaign-phases/`
- `GET /api/admin/campaign-phases/{id}/`
- `PATCH /api/admin/campaign-phases/{id}/`
- `POST /api/admin/campaign-phases/{id}/archive/`

---

## 9) AcademicYear and Campaign Binding Rules

The institutional rule is enforced:

- campaign operations are expected to bind to active DB academic year
- no active year -> creation operations fail with readable validation errors
- public subject catalog returns empty list cleanly when no active year exists

---

## 10) Subject Workflow Compatibility After Refactor

Sprint 3 behavior retained:

- teacher creates draft
- submits/resubmits
- admin approves/rejects
- archive removes from catalog visibility

Sprint 4 extension:

- `ASSIGNED` status is now part of lifecycle model for future assignment sprint
- attachment metadata fields added for richer subject description

---

## 11) Status Normalization Strategy

Full replacement of all legacy booleans was intentionally avoided to reduce migration risk.

Applied incremental strategy:

- introduced `User.account_status` enum
- kept legacy booleans for compatibility and synchronized behavior
- kept `AcademicYear` booleans with explicit governance rules
- expanded `Subject` status as primary lifecycle direction

This balances correctness and stability for an academic project with ongoing sprint evolution.

---

## 12) Implemented vs Prepared vs Not Yet Implemented

## Implemented now

- auth + JWT
- academic year governance
- admin user management
- subject lifecycle
- platform access grant model and APIs
- campaign phase model and admin APIs

## Prepared (foundation ready, full workflow not yet implemented)

- contextual-role-driven team logic
- campaign-phase-driven hard enforcement across all future modules
- subject assignment workflow automation

## Not implemented yet

- teams and participations
- wishlists
- appeals
- deliverables
- defense workflow
- audit trail system
- notification system

---

## 13) Tests and Quality Gate

Test status after Sprint 4 realignment:

- full suite passing
- coverage now includes:
  - platform access grant constraints and permissions
  - campaign phase lifecycle constraints
  - subject status extension compatibility
  - backward compatibility of Sprint 1-3 core behavior

---

## 14) Migration Impact

Sprint 4 introduces new migrations for:

- accounts: identity/status fields + new profile/grant models + data backfill
- campaigns: initial campaign phase model
- topics: subject status extension + attachment metadata fields

Migration strategy was non-destructive and incremental.

---

## 15) Backward Compatibility Notes

- existing login flow preserved
- existing core endpoints preserved
- legacy `global_role` remains functional during transition
- platform grants introduced without immediate hard break of old records
- archived/inactive access protections remain enforced

---

## 16) Next Sprint Direction (Prepared by Sprint 4)

Sprint 5 can now implement domain features with less rewrite risk:

- campaign phases enforcement in business actions
- team entities and participation states
- subject assignment and team locking
- first/second wish workflow

Sprint 4 goal achieved: foundational realignment without destabilizing validated existing functionality.
