# PFE Management Platform Backend
## Technical Dossier (Sprint 0 to Sprint 3)

Version date: 2026-04-14

---

## 1) Project Context and Product Intention

This backend powers a PFE (Final Engineering Project) management platform for an engineering school.

The product vision for V1 is institutional workflow management, not internal agile team collaboration.

### V1 scope focus

- academic year governance
- identity and role management
- subject (topic) proposal and moderation workflow
- progressive setup for later phases (campaigns, teams, assignment, deliverables, defense)

### Explicitly excluded so far

- member-by-member task tracking
- kanban boards
- chat/messaging systems
- recommendation engines
- assignment algorithm (future sprint)
- defense planning workflow (future sprint)

---

## 2) Why this Technology Stack

### Django 5

Used as the core framework because it gives:

- strong ORM with relational integrity
- mature auth system extensibility (custom user, custom backend)
- clean app modularization
- robust admin interface for academic demos and manual operations

### Django REST Framework (DRF)

Used for API layer because it provides:

- serializers with explicit validation
- authentication/permission integration
- predictable request/response patterns
- pagination/filter readiness

### djangorestframework-simplejwt

Used for stateless API authentication:

- access tokens for short-lived API access
- refresh tokens for session continuity
- clean integration with DRF authentication classes

### PostgreSQL

Chosen as primary transactional database because:

- strong ACID guarantees
- relational modeling fits school workflows
- proper constraints/indexing support

### Redis + Celery

Prepared for asynchronous workloads:

- Redis as broker/result backend and caching layer
- Celery worker already wired for future long tasks (imports, notifications, batch jobs)

### MinIO (S3-compatible) + django-storages

Prepared for file storage at scale:

- object storage semantics, S3-compatible
- local dev parity with cloud-compatible model
- ready for deliverables in later sprints

### drf-spectacular

Used for OpenAPI schema generation and Swagger UI:

- explicit API contract visibility
- easier teacher/reviewer demos
- frontend-backend contract clarity

### pytest + pytest-django

Chosen for integration-style testing:

- concise test style
- database transaction support
- endpoint-level behavior validation

### Docker + Docker Compose

Used for reproducible local environment:

- consistent setup across developer machines
- easy bootstrapping (web, db, redis, minio, worker)

---

## 3) High-Level Architecture

## 3.1 Project structure

- `backend/config`: settings, URL routing, celery bootstrap, health API
- `backend/apps/accounts`: identity, auth, roles, profiles, account admin APIs
- `backend/apps/academics`: academic year domain and admin APIs
- `backend/apps/topics`: subject proposal lifecycle and catalog APIs
- placeholder apps prepared for later sprints: campaigns, teams, assignments, projects, deliverables, defenses, archives, audit

## 3.2 Settings strategy

- split settings files exist (`base.py`, `local.py`, `production.py`)
- runtime values loaded from environment (`backend/.env`)
- sensitive values are not hardcoded

## 3.3 API prefix policy

All functional API routes are under `/api/` and do not use `/api/v1/`.

## 3.4 Current global URL map

- `/admin/` Django admin UI
- `/api/health/`
- `/api/auth/login/`, `/api/auth/refresh/`, `/api/auth/me/`
- `/api/admin/academic-years/...`
- `/api/admin/users/...`
- `/api/super-admin/admins/`
- `/api/teacher/subjects/...`
- `/api/admin/subjects/...`
- `/api/subjects/...` (public catalog for authenticated non-archived users)
- `/api/schema/`, `/api/docs/`

---

## 4) Environment and Runtime Configuration

Variables documented in `backend/.env.example`.

## 4.1 Core

- `DJANGO_SETTINGS_MODULE`
- `SECRET_KEY`
- `DEBUG`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`

## 4.2 Database

- `DATABASE_URL`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`

## 4.3 Cache and async

- `REDIS_URL`

## 4.4 JWT and API behavior

- `SIMPLE_JWT_ACCESS_MINUTES` (default 15)
- `SIMPLE_JWT_REFRESH_DAYS` (default 7)
- `API_PAGE_SIZE`
- `API_MAX_PAGE_SIZE`

## 4.5 MinIO / S3-compatible storage

- `USE_S3`
- `MINIO_ENDPOINT`
- `MINIO_ACCESS_KEY`
- `MINIO_SECRET_KEY`
- `MINIO_BUCKET_NAME`
- `MINIO_REGION`
- `MINIO_USE_SSL`
- `MINIO_ROOT_USER`
- `MINIO_ROOT_PASSWORD`

---

## 5) Complete Data Model Inventory (All Apps)

This section explicitly lists **all model files in the repository** and clarifies which models are implemented now vs placeholders for future sprints.

## 5.1 Implemented models (real DB tables today)

### App: `accounts`

#### Model: `User` (`accounts_user`)

Purpose: core identity and authentication record for every actor.

Fields:

- `id` (BigAutoField, PK)
- `matricule` (unique, business identifier, login-compatible)
- `email` (unique)
- `first_name`
- `last_name`
- `global_role` (`STUDENT`, `TEACHER`, `ADMIN`, `SUPER_ADMIN`)
- `is_active`
- `is_archived`
- `is_staff`
- `is_superuser` (from `PermissionsMixin`)
- `created_at`
- `updated_at`

Indexes:

- by `global_role`
- by `is_archived`

Design choices:

- `USERNAME_FIELD = "matricule"` (primary authentication identifier)
- custom backend supports login by either matricule or email
- archived users are blocked at auth and permission levels

#### Model: `StudentProfile` (`accounts_student_profile`)

Purpose: student-specific attributes separated from core identity.

Fields:

- `user` (OneToOne -> `accounts.User`)
- `academic_year` (FK -> `academics.AcademicYear`, nullable for migration/transition flexibility)
- `moyenne_generale` (nullable)
- `specialite` (nullable)
- `created_at`
- `updated_at`

Business/validation note:

- admin serializers now enforce linking student profile to active academic year when provided.

#### Model: `TeacherProfile` (`accounts_teacher_profile`)

Purpose: teacher-specific attributes separated from core identity.

Fields:

- `user` (OneToOne -> `accounts.User`)
- `grade` (nullable)
- `departement` (nullable)
- `created_at`
- `updated_at`

---

### App: `academics`

#### Model: `AcademicYear` (`academics_academic_year`)

Purpose: institutional academic cycle anchor for all year-bound operations.

Fields:

- `id` (BigAutoField, PK)
- `year` (string label like `2025/2026`, unique)
- `is_active`
- `is_archived`
- `created_at`
- `updated_at`

Indexes:

- by `is_active`
- by `is_archived`

DB constraint:

- partial unique constraint on active rows to guarantee only one active year.

Application rules:

- archived year cannot be active
- only current computed year label can be activated
- activating one year deactivates+archives all others in transaction
- helper used: `get_current_academic_year_label(start_month=9)`

---

### App: `topics`

#### Model: `Subject` (`topics_subject`)

Purpose: Sprint 3 core entity for PFE topic proposal lifecycle.

Fields:

- `id` (BigAutoField, PK)
- `title`
- `description`
- `subject_type`:
  - `RESEARCH_PROJECT`
  - `APPLIED_PROJECT`
  - `STARTUP_PROJECT`
- `technologies`
- `keywords`
- `status`:
  - `DRAFT`
  - `SUBMITTED`
  - `APPROVED`
  - `REJECTED`
  - `ARCHIVED`
- `proposed_by` (FK -> `accounts.User`)
- `academic_year` (FK -> `academics.AcademicYear`)
- `rejection_reason`
- `submitted_at`
- `reviewed_at`
- `reviewed_by` (FK -> `accounts.User`, nullable)
- `is_archived`
- `created_at`
- `updated_at`

Indexes:

- by `status`
- by `is_archived`
- by `academic_year`
- by `proposed_by`

Model-level consistency:

- cannot link subject to archived academic year
- archived subject must have status `ARCHIVED`

Workflow-level consistency (serializer/service layer):

- teacher edit only for `DRAFT` and `REJECTED`
- submit/resubmit/approve/reject transitions validated explicitly
- transition actions enforce that subject belongs to current active academic year

## 5.2 Placeholder model files (intentionally empty for now)

The following apps already exist structurally, but their `models.py` currently contains only placeholder comments by design:

- `apps.campaigns.models`
- `apps.teams.models`
- `apps.assignments.models`
- `apps.projects.models`
- `apps.deliverables.models`
- `apps.defenses.models`
- `apps.archives.models`
- `apps.audit.models`

Reason:

- these domains are planned for future sprints
- keeping placeholders now avoids architecture reshuffling later
- no fake/temporary business models were introduced prematurely

## 5.3 Current relationship map (implemented entities only)

- `User` 1 <-> 1 `StudentProfile` (optional depending on role)
- `User` 1 <-> 1 `TeacherProfile` (optional depending on role)
- `AcademicYear` 1 -> N `StudentProfile`
- `AcademicYear` 1 -> N `Subject`
- `User` (teacher) 1 -> N `Subject` via `proposed_by`
- `User` (admin/super-admin) 1 -> N `Subject` via `reviewed_by`

## 5.4 Why profiles are separate from `User`

- prevents polluting core auth identity with role-specific attributes
- keeps login/session/auth concerns isolated from student/teacher metadata
- allows controlled role changes with profile synchronization rules
- keeps API payloads explicit and future-ready for richer role data

---

## 6) Security and Access Model

## 6.1 Authentication

JWT-based auth with SimpleJWT.

- login endpoint issues `access` + `refresh`
- refresh endpoint provides renewed access
- default DRF auth class is JWT

## 6.2 Custom login flow

`POST /api/auth/login/` accepts:

- `identifier` (matricule or email)
- `password`

Validation sequence:

1. resolve user by identifier
2. reject if archived
3. reject if inactive
4. authenticate via custom backend
5. issue JWT tokens

## 6.3 Permissions classes

- `IsAuthenticatedAndNotArchived`
- `IsAdminOrSuperAdmin`
- `IsSuperAdmin`
- `IsTeacherOrAbove`

## 6.4 Role governance

- ADMIN/SUPER_ADMIN can access admin endpoints
- SUPER_ADMIN-only endpoint for admin account provisioning
- ADMIN cannot escalate users to ADMIN/SUPER_ADMIN through admin user API

---

## 7) Sprint-by-Sprint Technical Delivery

## Sprint 0 (Foundation)

Delivered:

- modular Django project scaffold
- required apps prepared
- environment-based settings
- Docker Compose stack (web, worker, postgres, redis, minio)
- DRF + drf-spectacular wiring
- custom user model baseline
- Celery + Redis base config
- MinIO integration foundation
- healthcheck endpoint
- pytest baseline and smoke tests

Primary objective achieved: solid base with low structural debt.

## Sprint 1 (Identity and Auth)

Delivered:

- custom auth backend for matricule/email login
- JWT auth endpoints
- profile-aware user serialization
- StudentProfile and TeacherProfile models
- archived/inactive login protections
- auth integration tests

Endpoints:

- `POST /api/auth/login/`
- `POST /api/auth/refresh/`
- `GET /api/auth/me/`

## Sprint 2 (Academic base + account administration)

Delivered:

- AcademicYear model and admin management APIs
- account management APIs for admin/super-admin
- profile-aware create/update for STUDENT/TEACHER
- logical archive endpoints (users, academic years)
- pagination for admin list endpoints
- role-scope restrictions (no admin escalation by ADMIN)
- integration tests for admin workflows

Endpoints (key):

- `GET/POST /api/admin/academic-years/`
- `GET/PATCH /api/admin/academic-years/{id}/`
- `POST /api/admin/academic-years/{id}/archive/`
- `GET/POST /api/admin/users/`
- `GET/PATCH /api/admin/users/{id}/`
- `POST /api/admin/users/{id}/archive/`
- `GET/POST /api/super-admin/admins/`

## Sprint 3 (Subject lifecycle)

Delivered:

- Subject model and workflow statuses
- teacher personal subject management APIs
- admin moderation APIs
- authenticated public approved-subject catalog
- workflow transition safeguards
- integration tests for end-to-end lifecycle

Teacher endpoints:

- `GET/POST /api/teacher/subjects/`
- `GET/PATCH /api/teacher/subjects/{id}/`
- `POST /api/teacher/subjects/{id}/submit/`
- `POST /api/teacher/subjects/{id}/resubmit/`

Admin moderation endpoints:

- `GET /api/admin/subjects/`
- `GET /api/admin/subjects/{id}/`
- `POST /api/admin/subjects/{id}/approve/`
- `POST /api/admin/subjects/{id}/reject/`
- `POST /api/admin/subjects/{id}/archive/`

Public catalog endpoints:

- `GET /api/subjects/`
- `GET /api/subjects/{id}/`

---

## 8) Core Business Rules Implemented in Code

## 8.1 No hard delete

Implemented strategy:

- use `is_archived` flags
- archive endpoints instead of DELETE for critical entities

## 8.2 Academic year governance

- only one active year allowed (DB + application flow)
- active year must match computed current label
- activating year archives all other years

## 8.3 User lifecycle constraints

- archived users cannot authenticate
- inactive users cannot authenticate
- all protected API access blocks archived users

## 8.4 Subject workflow constraints

- create starts at `DRAFT`
- teacher edits only `DRAFT` or `REJECTED`
- submit: `DRAFT -> SUBMITTED`
- resubmit: `REJECTED -> SUBMITTED`
- approve/reject only from `SUBMITTED`
- reject requires non-empty reason
- archive marks `is_archived=True` and `status=ARCHIVED`

## 8.5 Academic year binding for subject actions

- subjects must use active, non-archived academic year
- teacher create/update aligns to current active year
- moderation transitions validate that subject belongs to active year
- public catalog only shows approved + non-archived subjects in active year

---

## 9) API Flow Walkthroughs

## 9.1 Login flow

1. client sends identifier/password
2. backend resolves user by matricule/email
3. backend checks archived/inactive flags
4. backend authenticates credentials
5. backend returns JWT tokens + user payload

## 9.2 Admin account provisioning flow

1. super admin logs in
2. calls `/api/super-admin/admins/` POST
3. creates ADMIN (or SUPER_ADMIN if allowed by payload)
4. new admin gets staff-level access to admin APIs

## 9.3 Student/teacher account management flow

1. admin creates user via `/api/admin/users/`
2. sets role STUDENT/TEACHER
3. optional nested profile payload accepted per role
4. serializer enforces profile consistency by role

## 9.4 Subject proposal flow

1. teacher creates draft in personal area
2. teacher updates while draft/rejected
3. teacher submits for moderation
4. admin approves or rejects with reason
5. rejected can be revised and resubmitted
6. approved subject appears in public catalog

## 9.5 Academic year transition flow

1. admin posts/patches year with `is_active=true`
2. validation enforces current-year label
3. transaction archives/deactivates all other years
4. active year becomes single source for new actions

---

## 10) Transaction and Consistency Strategy

- critical state transitions wrapped with `transaction.atomic`
- serializer validation used for request-level business invariants
- model `clean()` used for local model consistency
- DB constraint used for single active academic year guarantee

Why this split:

- serializer layer handles multi-record orchestration and role-aware logic
- model layer protects intrinsic record consistency
- database layer enforces hard invariant against race conditions

---

## 11) Documentation and Developer Experience

## 11.1 Swagger/OpenAPI

- schema: `/api/schema/`
- UI: `/api/docs/`

Tags currently used:

- `Auth`
- `Academic Years`
- `Admin Users`
- `Super Admin`
- `Teacher Subjects`
- `Admin Subjects`
- `Subjects Catalog`

## 11.2 Django admin UI

Available at `/admin/` with humanized registration for:

- User
- StudentProfile
- TeacherProfile
- AcademicYear

Purpose:

- demonstration
- manual verification
- quick inspection without building custom frontend screens

---

## 12) Testing Strategy and Current Status

Test tooling:

- pytest + pytest-django
- DRF APIClient
- JWT-authenticated integration test style

Coverage focus:

- auth flows
- role access protections
- admin user management constraints
- academic year behavior
- subject lifecycle transitions
- catalog visibility filtering

Current result in local containerized run:

- all tests passing (`49 passed`)

Note:

- warning about short JWT secret in local env is expected with placeholder secret
- production must use long random secret keys

---

## 13) Operational Runbook (Local)

1. copy env template

- `cp backend/.env.example backend/.env`

2. start stack

- `docker compose up --build`

3. run migrations

- `docker compose run --rm web python manage.py migrate`

4. run checks/tests

- `docker compose run --rm web python manage.py check`
- `docker compose run --rm web pytest -q`

5. access interfaces

- API docs: `http://localhost:8000/api/docs/`
- health: `http://localhost:8000/api/health/`
- admin: `http://localhost:8000/admin/`

---

## 14) Current Constraints and Intentional Trade-offs

Intentional constraints:

- no DELETE endpoints for domain entities
- no contextual roles yet (only global role on User)
- no campaign window logic yet
- no groups/wishes/assignment algorithm yet
- no deliverables/defense workflows yet

Trade-off rationale:

- prioritized correctness and clarity over early complexity
- avoided building speculative abstractions before concrete workflows
- kept code easy to explain in academic evaluation context

---

## 15) How the Project Will Evolve (Planned Direction)

The current backend is intentionally prepared for progressive sprint expansion.

Likely future directions:

- campaign windows and institutional calendars
- team formation workflows
- wishes/preferences submission
- assignment logic and validation loops
- deliverable lifecycle and storage enforcement
- defense planning, minutes, and archival process
- audit trails and richer observability

The architecture is already modularized to support these additions without rewriting the identity and governance core.

---

## 16) Summary for Teacher Review

This backend currently demonstrates:

- a production-style technical foundation
- clear identity and role model with custom auth
- controlled academic-year governance with strict invariants
- complete subject proposal lifecycle with moderation
- logically archived data strategy
- documented and test-backed API behavior
- clear separation of concerns between apps, serializers, views, permissions, and settings

In short, Sprint 0 to Sprint 3 delivers a stable institutional core that is ready for domain expansion while staying pedagogical and maintainable.
