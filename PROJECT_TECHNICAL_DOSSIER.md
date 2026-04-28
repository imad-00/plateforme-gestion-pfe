# PFE Management Platform Backend
## Technical Dossier - Post Convergence Architecture

Version date: 2026-04-28

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
   - `Team.status`
   - `TeamParticipant.status`
   - `WishList.status`
   - `Appeal.status`

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
- `wishlist_size` (default `5`)
- timestamps

Rules:
- one `ACTIVE` academic year at a time (DB constraint)
- activating a year archives all others (service/serializer logic)
- archived year cannot be edited through normal update endpoint
- wishlist length is configured per academic year and must be at least 1

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

Important active phase family:
- `TEAM_FORMATION`
- `WISHLIST_1`
- `ASSIGNMENT_REVIEW_1`
- `RESULTS_AND_APPEALS`
- `WISHLIST_2`
- `ASSIGNMENT_REVIEW_2`
- `WORK_AND_SUPERVISION`
- `DEFENSE_WINDOW`

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

## 3.5 Teams

### `Team`
Campaign team aggregate:
- `team_code`
- `academic_year`
- `name`
- `status` (`FORMING`, `LOCKED`, `VALIDATED`, `DISSOLVED`, `ARCHIVED`)
- `selection_round` (`FIRST`, `SECOND`)
- `annual_average`
- `created_at`, `updated_at`, `dissolved_at`

Rules:
- a team belongs to one academic year
- teams are not deleted for business workflows
- student-managed composition is allowed only while `FORMING`
- `LOCKED` and `VALIDATED` teams require admin intervention for composition changes

### `TeamParticipant`
Contextual participation in a team:
- `user`
- `team`
- `role` (`LEADER`, `MEMBER`, `SUPERVISOR`)
- `status` (`PENDING`, `ACTIVE`, `ENDED`, `REJECTED`)
- `joined_at`, `ended_at`, timestamps

Rules:
- one active leader per team
- student membership uses `LEADER` / `MEMBER`
- supervisors use `SUPERVISOR`
- supervisors do not count toward student team size
- duplicate active/pending participations are blocked where relevant

### Sprint 5 services
Business behavior is centralized in:
- `TeamService`
- `InvitationService`
- `ParticipationService`

These services handle:
- solo team creation
- invitations
- invitation accept/reject
- leave team
- member removal
- leadership transfer
- team locking
- admin supervisor management
- future subject-owner supervisor helper

## 3.6 Wishes, Appeals, and Assignment

Sprint 6 adds the subject choice and assignment workflow without adding assignment run/result tables. Assignment results are stored directly on `Team` and `Subject`.

### `WishList`
Team wishlist for a selection round:
- `wishlist_id`
- `team`
- `academic_year`
- `selection_round` (`FIRST`, `SECOND`)
- `status` (`DRAFT`, `SUBMITTED`, `LOCKED`, `ARCHIVED`)
- `submitted_by`
- `submitted_at`
- timestamps

Rules:
- one wishlist per team per selection round
- wishlist size is not stored on the wishlist
- required size comes from `AcademicYear.wishlist_size`
- submitted wishlists are historical records, not deleted

### `WishItem`
Ranked subject choice:
- `wishitem_id`
- `wishlist`
- `subject`
- `rank`

Rules:
- one subject appears only once per wishlist
- one rank appears only once per wishlist
- service validation enforces continuous ranks from `1..N`

### `Appeal`
Team appeal after first-round assignment:
- `appeal_id`
- `team`
- `reason`
- `status` (`PENDING`, `ACCEPTED`, `REJECTED`)
- `submitted_by`
- `reviewed_by`
- `submitted_at`, `resolved_at`
- `admin_comment`
- timestamps

Rules:
- one appeal per team
- only the active leader can submit an appeal
- appeal is allowed only after a first-round assignment
- accepting an appeal releases the previous subject, sets the team back to `LOCKED`, and moves the team to `SECOND` round
- rejecting an appeal keeps the assignment unchanged

### Sprint 6 services
Business behavior is centralized in:
- `WishListService`
- `AssignmentService`
- `AppealService`

Assignment modes:
- `MERIT_AVERAGE`
- `RANDOM`
- `MANUAL`

Assignment result transitions:
- `Team.status: LOCKED -> VALIDATED`
- `Subject.status: APPROVED -> ASSIGNED`
- `Subject.assigned_to_team` stores the selected team
- subject owner is added as contextual `SUPERVISOR` through the Sprint 5 helper

Team average rule:
- computed from active student participants only
- uses `StudentProfile.annual_average`
- missing averages default to `10.00`
- if a team has no active student members, `Team.annual_average = null` and the team is skipped in merit assignment

Subject compatibility rule:
- team size `<= 2`: all approved unassigned subjects are eligible
- team size `> 2`: only approved unassigned `STARTUP_PROJECT` subjects are eligible
- enforced in catalog, wishlist validation, merit assignment, random assignment, and manual assignment

## 3.7 Deliverables

Sprint 7 intentionally keeps deliverables simple.

### `DeliverableFile`
Internal work file uploaded by a validated team during `WORK_AND_SUPERVISION`:
- `id`
- `team`
- `file`
- `original_filename`
- `file_size`
- `content_type`
- `uploaded_by`
- `uploaded_at`
- `comment`
- `review_status` (`PENDING`, `ACCEPTED`, `NEEDS_REVISION`, `REJECTED`)
- `reviewed_by`
- `reviewed_at`
- `review_comment`
- timestamps

### `DeliverableFileComment`
Flat coordination note attached to a file:
- `id`
- `deliverable_file`
- `author`
- `text`
- `created_at`
- `updated_at`

Rules:
- no `DeliverableDefinition`
- no `DeliverableVersion`
- no version numbering
- no deadlines
- no max upload count
- no final submission lock
- every upload creates a new record
- old files are not overwritten or hard-deleted
- `ACCEPTED` means supervisor feedback only, not administrative finalization
- students can continue uploading after `ACCEPTED`, `REJECTED`, or `NEEDS_REVISION`
- internal and external supervisors can review the same file multiple times, with the latest review overwriting the previous one
- flat comments are visible to the same team workspace and supervisors
- comments are not threaded discussions
- comments are append-only coordination/history notes in this sprint

Sprint 7 services:
- `DeliverableFileService`

Service responsibilities:
- list current team files for active student members
- upload file for active leader/member of a `VALIDATED` team
- list supervised teams for contextual supervisors
- list files for a supervised team
- add flat comment to a file for active team members or active supervisors
- review file during `WORK_AND_SUPERVISION`

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
  - `GET /api/subjects/catalog/`
  - `GET /api/subjects/`
  - `GET /api/subjects/{id}/`

## Teams
- Student/team leader:
  - `GET /api/teams/me/`
  - `POST /api/teams/{team_code}/invite/`
  - `POST /api/team-invitations/{participation_id}/accept/`
  - `POST /api/team-invitations/{participation_id}/reject/`
  - `POST /api/teams/leave/`
  - `POST /api/teams/{team_code}/remove-member/`
  - `POST /api/teams/{team_code}/transfer-leadership/`
  - `POST /api/teams/{team_code}/lock/`
- Admin:
  - `GET /api/admin/teams/`
  - `GET /api/admin/teams/{team_code}/`
  - `POST /api/admin/teams/{team_code}/remove-member/`
  - `POST /api/admin/teams/{team_code}/transfer-leadership/`
  - `POST /api/admin/teams/{team_code}/supervisors/`
  - `POST /api/admin/teams/{team_code}/supervisors/remove/`
  - `POST /api/admin/teams/{team_code}/dissolve/`

## Wishes, appeals, assignment
- Team-facing:
  - `POST /api/wishlists/`
  - `GET /api/wishlists/me/`
  - `POST /api/appeals/`
  - `GET /api/appeals/me/`
  - `GET /api/assignments/me/`
- Admin:
  - `GET /api/admin/wishlists/`
  - `GET /api/admin/wishlists/{wishlist_id}/`
  - `POST /api/admin/assignments/merit/`
  - `POST /api/admin/assignments/random/`
  - `POST /api/admin/assignments/manual/`
  - `POST /api/admin/assignments/{team_code}/validate/`
  - `POST /api/admin/appeals/{appeal_id}/accept/`
  - `POST /api/admin/appeals/{appeal_id}/reject/`

## Deliverable files and supervision
- Team-facing:
  - `GET /api/deliverable-files/me/`
  - `POST /api/deliverable-files/upload/`
  - `GET /api/deliverable-files/{file_id}/`
  - `POST /api/deliverable-files/{file_id}/comments/`
- Supervisor-facing:
  - `GET /api/supervision/teams/`
  - `GET /api/supervision/teams/{team_code}/files/`
  - `POST /api/deliverable-files/{file_id}/review/`

## Technical
- `GET /api/health/`
- `GET /api/campaign/current/`
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
- defense flow and jury assignment flow
- notifications/messaging/dashboard

What is still intentionally not implemented inside deliverables:
- deliverable definitions
- deadlines
- version numbering/history models
- final submission locking
- grading
- jury/PV/defense attachments

---

## 8) Test Status

Current local containerized test run:
- Sprint 6 isolated suite: `22 passed`
- Campaign phase enforcement suite: `18 passed`
- Sprint 7 deliverable files suite: `28 passed`
- Full suite: run after the latest Sprint 7 pass

Command:
- `docker compose run --rm web pytest -q`

---

## 9) Sprint 5 Technical Direction

Sprint 5 delivered Team + TeamParticipant lifecycle governance.

Implemented rules:
- every managed student can receive a default solo team
- active leaders can invite students while team is `FORMING`
- invited students can accept/reject invitations
- members can leave `FORMING` teams and receive a new solo team
- leaders must transfer leadership before leaving
- leaders can transfer leadership while `FORMING`
- leaders can lock a valid `FORMING` team
- pre-assignment student team size is capped at 7
- only admins can manage supervisors
- only admins can modify locked/validated teams
- subject owner supervisor helper exists for future assignment integration

## 10) Sprint 6 Technical Direction

Sprint 6 delivered WishList + WishItem + Appeal and direct assignment services.

Implemented rules:
- teams submit ranked wishlists while `LOCKED`, or while `FORMING` with automatic lock after successful validation
- only active leaders can submit wishlists and appeals
- wishlist length uses `AcademicYear.wishlist_size`
- if fewer compatible subjects exist than configured size, teams submit all compatible subjects
- no empty wishlist is accepted
- duplicate subjects, duplicate ranks, and non-continuous ranks are rejected
- catalog excludes assigned subjects
- catalog applies team-size compatibility
- merit assignment sorts teams by computed annual average
- missing student annual averages count as `10.00`
- teams are skipped from merit assignment only if they have no active student members
- random assignment respects wishlist rank and supports deterministic seed for tests
- manual assignment validates team status, subject availability, and compatibility
- assignment reserves the subject and keeps the team `LOCKED`
- manual validation changes the team to `VALIDATED` and records validation metadata
- accepted appeals release the previous subject and open the second round
- rejected appeals keep assignment unchanged

## 11) Campaign Phase Enforcement Pass

This corrective pass adds centralized campaign-window enforcement without creating a single "current phase".

Optimized phase list:
- `CAMPAIGN_SETUP`
- `SUBJECT_MANAGEMENT`
- `TEAM_FORMATION`
- `WISHLIST_1`
- `ASSIGNMENT_REVIEW_1`
- `RESULTS_AND_APPEALS`
- `WISHLIST_2`
- `ASSIGNMENT_REVIEW_2`
- `WORK_AND_SUPERVISION`
- `DEFENSE_WINDOW`
- `ARCHIVE`

Several phases may be open at the same time. A phase is open when it belongs to the relevant active academic year, is not archived, has started, and has not ended unless its end date is intentionally null.

Central service:
- `CampaignPhaseService.is_open(...)`
- `CampaignPhaseService.require_open(...)`
- `CampaignPhaseService.get_open_phases(...)`
- `CampaignPhaseService.get_user_action_availability(...)`

Phase-to-action mapping:
- `TEAM_FORMATION`: student invitations, accept/reject, leave, member removal by leader, leadership transfer by leader, manual lock
- `SUBJECT_MANAGEMENT`: teacher subject create/edit/submit/resubmit and admin approve/reject
- `WISHLIST_1`: first wishlist submission and student subject catalog visibility
- `ASSIGNMENT_REVIEW_1`: first round merit/random/manual assignment and assignment validation
- `RESULTS_AND_APPEALS`: student assignment result visibility, appeal submission, appeal review
- `WISHLIST_2`: second wishlist submission and catalog visibility only for accepted-appeal teams
- `ASSIGNMENT_REVIEW_2`: second round assignment and validation
- `WORK_AND_SUPERVISION`: reserved for Sprint 7 deliverables
- `DEFENSE_WINDOW`: reserved for Sprint 8 defense/jury/PV

Academic-year consistency:
- student creation assigns the active academic year when omitted
- student creation fails cleanly if no active academic year exists
- solo teams use the student's active campaign year
- subject creation uses the active academic year
- wishlist items must belong to the team's academic year
- assignment rejects team/subject year mismatches
- student catalog uses the student's active team academic year

Visibility rules:
- student subject catalog is hidden unless the relevant wishlist phase is open
- second wishlist catalog is available only to teams with an accepted appeal
- student assignment result endpoint is hidden until `RESULTS_AND_APPEALS`
- admin internal assignment operations remain controlled by assignment review phases

## 12) Sprint 7 Deliverable Files

Sprint 7 implements a lightweight supervision workspace, not a formal deliverable-governance module.

Operational rules:
- upload requires `WORK_AND_SUPERVISION`
- only active `LEADER` or `MEMBER` of the current team can upload
- team must be `VALIDATED`
- team must already have an assigned subject
- internal `TEACHER` supervisors and `EXTERNAL_SUPERVISOR` users can review
- active team members and active supervisors can add flat comments to a file
- reviews are mutable and overwrite previous review fields
- read-only listing is available to team members and supervisors according to their scope
- platform admins do not receive deliverable monitoring endpoints in this sprint

Storage:
- uses the existing default Django storage, which is MinIO/S3-compatible when `USE_S3=true`
- upload path follows `deliverables/<academic_year_id>/<team_code>/<filename>`

What Sprint 7 does not mean:
- `ACCEPTED` is not a final submission state
- `ACCEPTED` does not block future uploads
- uploaded files are internal team-supervisor work artifacts
- comments are simple visible notes, not a threaded discussion system
- Sprint 8 is still responsible for defense/jury/PV workflows

Recommended next implementation order:
1. Deliverable submission and review workflow under `WORK_AND_SUPERVISION`
2. Defense authorization and scheduling under `DEFENSE_WINDOW`
3. Jury assignment and PV workflow
