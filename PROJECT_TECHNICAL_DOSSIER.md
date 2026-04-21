# PFE Management Platform Backend
## Technical Dossier - Post Convergence Architecture

Version date: 2026-04-20

---

## 1) Architecture Decision

This codebase is now in **hard-cut converged mode**.

The runtime no longer depends on legacy role logic (`global_role`) or duplicated account/academic/subject boolean lifecycle flags.

Authoritative architectural axes are now:

1. **Business identity** (`User.business_identity`)
   - `STUDENT`
   - `TEACHER`
   - `ADMINISTRATIVE_STAFF`
   - `EXTERNAL_SUPERVISOR`
2. **Platform privilege** (`PlatformAccessGrant`)
   - `ADMIN`
   - `SUPER_ADMIN`
3. **Lifecycle enums as source of truth**
   - `User.account_status`
   - `AcademicYear.status`
   - `Subject.status`

---

## 2) Preserved Technical Backbone

- Django 5
- Django REST Framework
- SimpleJWT
- PostgreSQL
- Redis + Celery
- MinIO (S3-compatible foundation)
- drf-spectacular
- pytest + pytest-django
- Docker Compose

---

## 3) Domain Model (Implemented)

## 3.1 Accounts

### `User`
Auth anchor with:
- `matricule` (login identifier)
- `email`
- `first_name`, `last_name`
- `business_identity`
- `account_status` (`ACTIVE`, `SUSPENDED`, `ARCHIVED`)
- `is_staff`, `is_superuser` (Django platform flags)
- timestamps

Removed from runtime model:
- `global_role`
- account booleans `is_active`/`is_archived`

### Identity profiles
- `StudentProfile` (academic_year, moyenne_generale, specialite)
- `TeacherProfile` (grade, departement)
- `AdministrativeStaffProfile`
- `ExternalSupervisorProfile`

### `PlatformAccessGrant`
Platform privilege source:
- `user`
- `access_level` (`ADMIN` / `SUPER_ADMIN`)
- `granted_by`, `granted_at`, `revoked_at`

Rules:
- only `TEACHER` and `ADMINISTRATIVE_STAFF` can receive grants
- one active grant per user
- only `ACTIVE` users can hold active grants

## 3.2 Academics

### `AcademicYear`
- `year`
- `status` (`ACTIVE`, `CLOSED`, `ARCHIVED`)
- timestamps

Rules:
- one `ACTIVE` academic year at a time (DB constraint)
- activating a year archives all others (service/serializer logic)
- archived year cannot be edited through normal update endpoint

## 3.3 Campaigns

### `CampaignPhase`
- `academic_year`
- `phase_type`
- `start_at`
- `end_at` (nullable)
- `display_order`
- `is_archived`
- timestamps

Rules:
- no phase on archived academic year
- `end_at >= start_at`
- uniqueness per year:
  - `(academic_year, phase_type)`
  - `(academic_year, display_order)`

## 3.4 Topics

### `Subject`
- title/description/type
- attachment metadata
- status (`DRAFT`, `SUBMITTED`, `APPROVED`, `REJECTED`, `ASSIGNED`, `ARCHIVED`)
- `proposed_by`
- `academic_year`
- moderation metadata (`reviewed_by`, `reviewed_at`, `rejection_reason`, `submitted_at`)
- timestamps

Rules:
- subject proposer must be `TEACHER` identity
- subject linked to non-archived academic year
- workflow transitions validated explicitly
- `ARCHIVED` is represented by status only

---

## 4) Permission Model

Core permission strategy:

- authenticated + active account (`account_status == ACTIVE`)
- admin/super-admin access resolved from active `PlatformAccessGrant` only
- teacher area access based on `business_identity == TEACHER` (or admin/super-admin grant)

No runtime fallback to old role architecture.

---

## 5) API Surface (Current)

## Auth
- `POST /api/auth/login/`
- `POST /api/auth/refresh/`
- `GET /api/auth/me/`

## Academics
- `GET/POST /api/admin/academic-years/`
- `GET/PATCH /api/admin/academic-years/{id}/`
- `POST /api/admin/academic-years/{id}/archive/`

## Campaign phases
- `GET/POST /api/admin/campaign-phases/`
- `GET/PATCH /api/admin/campaign-phases/{id}/`
- `POST /api/admin/campaign-phases/{id}/archive/`

## Users (admin management)
- `GET/POST /api/admin/users/`
- `GET/PATCH /api/admin/users/{id}/`
- `POST /api/admin/users/{id}/archive/`

## Platform access grants
- `GET /api/admin/platform-access-grants/`
- `POST /api/super-admin/platform-access-grants/`
- `POST /api/super-admin/platform-access-grants/{id}/revoke/`

## Super-admin admin provisioning
- `GET/POST /api/super-admin/admins/`

## Subjects
- Teacher personal:
  - `GET/POST /api/teacher/subjects/`
  - `GET/PATCH /api/teacher/subjects/{id}/`
  - `POST /api/teacher/subjects/{id}/submit/`
  - `POST /api/teacher/subjects/{id}/resubmit/`
- Admin moderation:
  - `GET /api/admin/subjects/`
  - `GET /api/admin/subjects/{id}/`
  - `POST /api/admin/subjects/{id}/approve/`
  - `POST /api/admin/subjects/{id}/reject/`
  - `POST /api/admin/subjects/{id}/archive/`
- Public authenticated catalog:
  - `GET /api/subjects/`
  - `GET /api/subjects/{id}/`

## Technical
- `GET /api/health/`
- `GET /api/schema/`
- `GET /api/docs/`
- `GET /admin/`

---

## 6) Convergence Changes Applied

Hard cut-over completed on:

1. Access control
- removed runtime dependency on `global_role`
- removed legacy permission fallbacks
- PlatformAccessGrant is the only platform privilege source

2. Lifecycle normalization
- User lifecycle based on `account_status`
- Academic year lifecycle based on `status`
- Subject lifecycle based on `status`

3. Data migration
- academic year status backfilled from old booleans before field removal
- subject archived status backfilled before archived boolean removal

---

## 7) Out-of-Scope Domains (Still Not Implemented)

These modules remain intentionally unimplemented as full workflows:
- teams
- wishes
- appeals
- deliverables and version history flow
- defense flow and jury assignment flow
- assignments engine
- notifications/messaging/dashboard

The architecture is now aligned so Sprint 5 can implement them without another foundational redesign.

---

## 8) Test Status

Current local containerized test run:
- `72 passed`

Command:
- `docker compose run --rm web pytest -q`

---

## 9) Sprint 5 Technical Direction

Recommended next implementation order:
1. Team + TeamParticipation constraints
2. WishList + WishItem with campaign-phase gating
3. Assignment + appeal round model
4. Deliverable + DeliverableVersion
5. Defense + DefenseJuryAssignment with conflict constraints

