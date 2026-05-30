# PFE Management Platform Backend
## Technical Dossier - Post Convergence Architecture

Version date: 2026-05-05

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
- creating/opening an academic year is `SUPER_ADMIN` controlled
- creating a new academic year is blocked while the latest/current year is `ACTIVE`
- academic-year status changes go through lifecycle endpoints, not normal admin update
- closed or archived years cannot be edited through normal update endpoint
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
- phases can be created/updated/archived only while the academic year is `ACTIVE`
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

## 3.8 Defenses

Sprint 8 implements the defense workflow with lightweight operational entities only. It does not add reporting, notification, archive, or grading-engine layers.

### `Defense`
- `id`
- `team`
- `status` (`REQUESTED`, `READY_TO_SCHEDULE`, `SCHEDULED`, `COMPLETED`, `CANCELLED`, `ARCHIVED`)
- `requested_by`, `requested_at`
- `scheduled_at`, `location`, `scheduled_by`
- `final_grade`
- `deliberation`
- `pv_file`
- `pv_uploaded_by`, `pv_uploaded_at`
- timestamps

Flow:
- `REQUESTED` when leader submits a defense request
- `READY_TO_SCHEDULE` after all active supervisors accept
- `SCHEDULED` after admin scheduling and jury assignment
- `COMPLETED` after PV upload by president or admin
- `CANCELLED` if any supervisor denies

### `DefenseAttachedFile`
Associates a defense with ordered `DeliverableFile` records:
- `defense`
- `deliverable_file`
- `order`
- `added_by`, `added_at`

Rules:
- a defense request must include at least one attached file
- attached files must belong to the same team as the defense
- attached files may come from existing `DeliverableFile` records or fresh PC uploads
- fresh uploads are first stored as `DeliverableFile`, then attached to the defense

### `DefenseSupervisorDecision`
Per-supervisor acceptance gate:
- `defense`
- `supervisor`
- `decision` (`PENDING`, `ACCEPTED`, `DENIED`)
- `decided_at`

Rules:
- decisions are created automatically for all active team supervisors
- all active supervisors must accept before scheduling
- one denial cancels the defense request
- cancelled teams may submit a new request later

### `DefenseJuryAssignment`
Jury membership for a defense:
- `defense`
- `user`
- `role` (`PRESIDENT`, `EXAMINER`, `GUEST`)
- `assigned_by`, `assigned_at`

Rules:
- exactly one `PRESIDENT`
- at least one `EXAMINER`
- all active supervisors are auto-added as `GUEST`
- supervisors cannot become `PRESIDENT`
- duplicate jury users are blocked

### Sprint 8 services
Business behavior is centralized in:
- `DefenseService`

Core operations:
- request defense
- supervisor accept / deny
- admin schedule / reschedule
- admin jury update
- admin attached-file update
- PV upload by president or admin

Phase enforcement:
- all operational defense actions require `DEFENSE_WINDOW`
- enforcement is in the service layer through `CampaignPhaseService`

File behavior:
- defense files are mandatory at request time
- team leader may select existing deliverable files
- team leader may upload new files from PC during request creation
- admin may adjust attached files before completion
- jury access opens once defense is scheduled

PV behavior:
- PV uses structured fields plus file storage
- required fields: `final_grade`, `deliberation`, `pv_file`
- `final_grade` must stay within `0..20`
- only the defense `PRESIDENT` or a platform admin may upload the PV
- PV upload changes the defense status to `COMPLETED`

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
- notifications/messaging/dashboard

What is still intentionally not implemented inside deliverables:
- deliverable definitions
- deadlines
- version numbering/history models
- final submission locking
- grading
- archive handoff

---

## 8) Test Status

Current local containerized test run:
- Sprint 6 isolated suite: `22 passed`
- Campaign phase enforcement suite: `18 passed`
- Sprint 7 deliverable files suite: `28 passed`
- Sprint 8 defenses suite: `31 passed`
- Full suite: run after the latest Sprint 8 pass

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

## 13) Sprint 8 Defense Workflow

Sprint 8 implements the defense request, supervisor acceptance, scheduling, jury, and PV flow.

Operational rules:
- all operational actions require `DEFENSE_WINDOW`
- only the active team leader can request a defense
- the team must be `VALIDATED` and must already have an assigned subject
- the team must have at least one active supervisor
- the request must contain at least one file
- files can be selected from existing `DeliverableFile` records, uploaded from PC during the request, or both
- all active supervisors receive `PENDING` decisions automatically
- if one supervisor denies, the defense becomes `CANCELLED`
- if all supervisors accept, the defense becomes `READY_TO_SCHEDULE`
- only admins can schedule or reschedule
- scheduling creates jury assignments with exactly one `PRESIDENT` and at least one `EXAMINER`
- all active supervisors are auto-added as `GUEST`
- supervisors cannot be `PRESIDENT`
- admins can adjust attached files before completion, but the defense must always keep at least one attached file
- jury file access opens after scheduling
- only the `PRESIDENT` or a platform admin can upload the PV
- PV upload stores `final_grade`, `deliberation`, `pv_file`, uploader metadata, and changes the defense to `COMPLETED`

API surface added:
- `POST /api/defenses/request/`
- `GET /api/defenses/me/`
- `GET /api/defenses/{defense_id}/files/`
- `GET /api/supervision/defense-requests/`
- `POST /api/defenses/{defense_id}/accept/`
- `POST /api/defenses/{defense_id}/deny/`
- `GET /api/jury/defenses/`
- `GET /api/jury/defenses/{defense_id}/`
- `GET /api/jury/defenses/{defense_id}/files/`
- `POST /api/jury/defenses/{defense_id}/pv/`
- `GET /api/admin/defenses/`
- `GET /api/admin/defenses/{defense_id}/`
- `POST /api/admin/defenses/{defense_id}/schedule/`
- `POST /api/admin/defenses/{defense_id}/reschedule/`
- `POST /api/admin/defenses/{defense_id}/jury/`
- `POST /api/admin/defenses/{defense_id}/files/`
- `POST /api/admin/defenses/{defense_id}/pv/`

## 14) Sprint 9 Academic Year Lifecycle

Sprint 9 implements academic-year closure, reopening, and archival governance.

Source of truth:
- `AcademicYear.status` is the only campaign freeze/archive source
- child objects keep their final business statuses
- closing or archiving does not cascade `ARCHIVED` to teams, subjects, defenses, appeals, or files
- files are never moved or deleted by lifecycle actions

Lifecycle:
- `ACTIVE -> CLOSED`: super-admin only
- `CLOSED -> ACTIVE`: super-admin only
- `CLOSED -> ARCHIVED`: super-admin only
- `ARCHIVED` is final and irreversible

Closing:
- requires `confirm=true` and a reason
- normal close blocks unresolved validated teams, unresolved defenses, and pending appeals
- force close may keep unresolved work as-is for later reopening
- `FORMING` and `LOCKED` abandoned teams are dissolved and active/pending participants are ended
- open campaign phases are frozen by setting `end_at` to the closure time
- user accounts remain `ACTIVE`

Reopening:
- only from `CLOSED`
- fails if another academic year is already `ACTIVE`
- does not reopen phases automatically
- does not alter child statuses

Archiving:
- only from `CLOSED`
- admin-only historical read access after archive
- students linked only to the archived year are suspended
- external supervisors linked only to the archived year are suspended
- teachers and administrative staff remain active
- users already suspended/archived are not reactivated

Lifecycle event model:
- `AcademicYearLifecycleEvent`
- event types: `CLOSED`, `FORCE_CLOSED`, `REOPENED`, `ARCHIVED`
- stores actor, timestamp, reason, and JSON metadata/readiness snapshots

Services:
- `AcademicYearLifecycleService.check_closure_readiness(...)`
- `AcademicYearLifecycleService.close_year(...)`
- `AcademicYearLifecycleService.reopen_year(...)`
- `AcademicYearLifecycleService.archive_year(...)`
- `AcademicYearLifecycleService.close_and_archive_year(...)`
- `AcademicYearLifecycleService.assert_academic_year_writable(...)`
- `AcademicYearLifecycleService.assert_archived_access_allowed(...)`

APIs:
- `GET /api/super-admin/academic-years/{id}/closure-readiness/`
- `POST /api/super-admin/academic-years/{id}/close/`
- `POST /api/super-admin/academic-years/{id}/reopen/`
- `POST /api/super-admin/academic-years/{id}/archive/`
- `POST /api/super-admin/academic-years/{id}/close-and-archive/`
- `GET /api/super-admin/academic-years/{id}/lifecycle-events/`

Changed behavior:
- academic-year creation is super-admin only
- creating a new academic year fails while a current year is `ACTIVE`
- academic-year status cannot be changed through normal admin update endpoints
- the old admin archive endpoint delegates to the lifecycle archive rules and requires super-admin confirmation
- campaign phases can be created/updated/archived only while their academic year is `ACTIVE`
- admin team overrides are blocked when the academic year is `CLOSED` or `ARCHIVED`
- non-admin user endpoints hide/deny archived-year team, deliverable, defense, and teacher-owned subject data

## 15) Sprint 10 Reporting and CSV Exports

Sprint 10 exposes official institutional outputs as read-only generated reports.

Scope:
- JSON previews and CSV downloads only
- no PDF export in this sprint
- no Excel export in this sprint
- no report persistence tables
- no asynchronous report generation
- no workflow/domain status changes
- no mutation of active, closed, or archived academic-year records

Access rules:
- all reporting endpoints are admin/super-admin only
- authorization uses active `PlatformAccessGrant`
- teachers, students, and external supervisors cannot access reports unless they also hold platform admin access
- reports can target `ACTIVE`, `CLOSED`, and `ARCHIVED` academic years
- archived academic-year history remains admin-only and is intentionally available through these admin report endpoints

Implemented service:
- `ReportService.get_defense_report(academic_year)`
- `ReportService.get_team_assignment_report(academic_year)`
- `ReportService.get_student_results_report(academic_year)`
- `ReportService.get_jury_planning_report(academic_year)`
- `ReportService.to_csv(rows, columns)`
- `ReportService.build_csv_response(rows, columns, filename)`

Implemented report endpoints:
- `GET /api/admin/reports/academic-years/{academic_year_id}/defenses/`
- `GET /api/admin/reports/academic-years/{academic_year_id}/defenses.csv`
- `GET /api/admin/reports/academic-years/{academic_year_id}/team-assignments/`
- `GET /api/admin/reports/academic-years/{academic_year_id}/team-assignments.csv`
- `GET /api/admin/reports/academic-years/{academic_year_id}/student-results/`
- `GET /api/admin/reports/academic-years/{academic_year_id}/student-results.csv`
- `GET /api/admin/reports/academic-years/{academic_year_id}/jury-planning/`
- `GET /api/admin/reports/academic-years/{academic_year_id}/jury-planning.csv`

CSV behavior:
- `Content-Type: text/csv; charset=utf-8`
- `Content-Disposition: attachment`
- header row included
- deterministic column order
- deterministic row ordering
- safe empty values for missing PV, missing schedule, missing subject, or missing team
- filenames include the academic year label, for example `defenses_2025-2026.csv`

Defense/PV report fields:
- defense id/status
- team code/name
- assigned subject title/type
- supervisors
- jury president, examiners, guests
- schedule date/location
- final grade, deliberation, PV upload metadata, PV file URL/name

Team assignment report fields:
- team code/name/status
- selection round and annual average
- students, leader, supervisors
- assigned subject title/type/status/proposer
- derived assignment status (`ASSIGNED` / `UNASSIGNED`)

Student results report fields:
- student identity and account status
- academic year
- most relevant team participation
- assigned subject
- defense status and final grade
- derived result status:
  - `COMPLETED`
  - `DEFENSE_COMPLETED_NO_GRADE`
  - `DEFENSE_PENDING`
  - `ASSIGNED_NO_DEFENSE`
  - `NO_ASSIGNMENT`
  - `ABANDONED`
  - `NO_TEAM`

Jury planning report fields:
- schedule date/location
- defense status
- team and subject
- president, examiners, guests, supervisors
- final grade and PV uploaded flag

Tests:
- `tests/test_sprint10_reports_exports.py`
- verifies admin-only access, active/closed/archived year access, JSON output, CSV headers/content-disposition, missing-value safety, deterministic ordering, archived-year admin-only access, and no domain mutation

## 16) Sprint 11 Notifications: In-App and Email

Sprint 11 adds a communication layer without changing workflow decisions.

Scope:
- in-app notifications for supported workflow events
- email delivery for `IMPORTANT` notifications only
- frontend polling support
- no WebSockets
- no push notifications
- no SMS
- no reminders or recurring jobs
- no notification preferences
- no delete endpoint
- no report notifications

Models:
- `Notification`
  - recipient
  - type
  - importance
  - title/message
  - optional link URL
  - read status and timestamp
  - metadata
- `NotificationDelivery`
  - notification
  - channel: `EMAIL`
  - status: `PENDING`, `SENT`, `FAILED`, `SKIPPED`
  - attempted/sent timestamps
  - error message

Importance behavior:
- `NORMAL`: in-app only
- `IMPORTANT`: in-app plus email delivery row and Celery email task
- email scheduling uses `transaction.on_commit(...)`
- email failure never rolls back the business action

Email task:
- `send_notification_email(notification_id)`
- sends through Django `send_mail`
- subject format: `[PFE Platform] {notification.title}`
- marks delivery `SENT`, `FAILED`, or `SKIPPED`

Archived-year rule:
- if related academic year is `ARCHIVED`, notifications to students, external supervisors, and non-admin teachers are skipped
- platform admins and super-admins may receive archive/lifecycle notifications
- archived-year historical reads do not create notifications

Implemented endpoint surface:
- `GET /api/notifications/`
- `GET /api/notifications/?unread=true`
- `GET /api/notifications/unread-count/`
- `POST /api/notifications/{notification_id}/read/`
- `POST /api/notifications/read-all/`

Frontend polling guidance:
- poll `GET /api/notifications/unread-count/`
- or poll `GET /api/notifications/?unread=true`
- recommended interval: 30 seconds

Implemented event hooks:
- team invitation received / **rejected**
- team member joined / left / removed
- leadership transferred
- team locked
- **team dissolved** (all active members notified)
- **team supervisor added / removed**
- subject submitted / resubmitted / approved / rejected
- **subject pending moderation** (notifies platform admins on teacher submit/resubmit)
- **subject archived**
- **subject assigned to team**
- assignment result available
- appeal submitted / accepted / rejected
- deliverable uploaded / reviewed / comment added
- defense requested
- supervisor accepted / denied defense request
- defense ready to schedule (**reclassified NORMAL → IMPORTANT**)
- defense scheduled / rescheduled
- **defense cancelled**
- **defense jury updated** (new jurors notified)
- **defense files updated** (supervisor-only, only once defense is SCHEDULED)
- jury assigned
- PV uploaded
- academic year closed / force closed / reopened / archived
- **academic year opened** (all active users notified)
- **campaign phase opened / closed** (audience resolved by phase type)
- **campaign phase closing soon** (24-hour advance reminder, one-shot per deadline)
- **platform grant received / revoked**
- **password changed** (reset-confirm and change-password flows)

Phase closing-soon mechanism:
- `CampaignPhase.closing_soon_notified_at` (null DateTimeField) — one-shot guard, cleared by `CampaignPhaseSerializer.update()` whenever `end_at` is rescheduled
- `apps.campaigns.tasks.send_phase_closing_soon_reminders` — Celery task, fired every 15 minutes by Celery beat
- Picks phases where `end_at ∈ (now, now + 24h]`, `closing_soon_notified_at IS NULL`, `is_archived = False`, parent year `ACTIVE`
- Uses `SELECT FOR UPDATE` to prevent double-fire under concurrent beat runs

Duplicate and actor rules:
- duplicate recipients are collapsed to one notification
- uploader is excluded from `DELIVERABLE_UPLOADED`
- comment author is excluded from `DELIVERABLE_COMMENT_ADDED`
- joining/leaving member is not notified for their own join/leave event

Tests:
- `tests/test_sprint11_notifications.py`
- verifies model creation, NORMAL vs IMPORTANT behavior, email task statuses, API list/count/read/read-all, recipient scoping, archive skip rules, duplicate prevention, actor exclusion, and representative hooks across teams, subjects, assignments, appeals, deliverables, defenses, and academic-year lifecycle

## 17) Sprint 12 Read-Only Dashboards

Sprint 12 adds lightweight dashboard read models for the three main runtime audiences.

Scope:
- read-only admin dashboard
- read-only teacher/supervisor dashboard
- read-only student dashboard
- no persistence models
- no charts
- no exports
- no WebSockets
- no async jobs
- no notification side effects
- no workflow changes

Implemented app:
- `apps.dashboard`

Implemented service:
- `DashboardService.get_admin_dashboard(user, academic_year=None)`
- `DashboardService.get_teacher_dashboard(user, academic_year=None)`
- `DashboardService.get_student_dashboard(user, academic_year=None)`
- academic-year resolution helpers for admin, teacher/supervisor, and student contexts
- archived-year guard for non-admin dashboard access

Endpoints:
- `GET /api/dashboard/admin/`
- `GET /api/dashboard/teacher/`
- `GET /api/dashboard/student/`

All endpoints accept optional:
- `academic_year_id`

Access rules:
- admin dashboard is platform admin/super-admin only through active `PlatformAccessGrant`
- admin dashboard can target `ACTIVE`, `CLOSED`, and `ARCHIVED` academic years
- teacher dashboard is available to teachers, external supervisors, and platform admins
- non-admin teachers/external supervisors cannot access `ARCHIVED` academic-year data
- student dashboard is student-only
- students cannot access `ARCHIVED` academic-year data
- `CLOSED` academic years remain readable where the user is related to the data

Admin dashboard fields:
- academic year summary
- team totals by status
- assigned/unassigned team counts
- defense counts by status
- appeal counts by status
- deliverable review counts
- subject counts by status

Teacher/supervisor dashboard fields:
- supervised team counts
- validated supervised team count
- pending deliverable review count
- latest five pending deliverable reviews
- pending defense request count
- next five upcoming scheduled defenses where the user is supervisor or jury

Student dashboard fields:
- academic year summary
- current or most relevant team
- active members and supervisors
- assigned subject
- latest defense status
- latest five deliverable files
- assignment round and assigned flag

Implementation notes:
- dashboard services query existing normalized domain data
- no dashboard tables are created
- service methods use filtered counts, `select_related`, and limited lists where appropriate
- dashboards do not mutate domain data
- archived-year visibility follows Sprint 9 admin-only historical access rule

Tests:
- `tests/test_sprint12_dashboards.py`
- verifies unauthenticated denial, role access rules, admin counts, archived-year admin access, teacher/supervisor metrics, external supervisor access, student dashboard safety, archived-year denial for students/non-admin teachers, and no data mutation

## 18) Sprint 13 Bulk User Imports and Admin Action Logging

Sprint 13 adds safe admin-driven bulk account creation and append-only traceability for sensitive admin actions.

Scope:
- CSV import preview for students
- CSV import preview for teachers
- optional XLSX parsing when `openpyxl` is installed in the runtime
- import confirmation from stored preview data
- random password generation
- first-login password reset requirement
- append-only admin action log
- no async/background imports
- no password emailing
- no generated password exposure
- no user self-registration
- no bulk updates to existing users

Import app:
- `apps.imports`

Import model:
- `UserImportBatch`
  - `import_type`: `STUDENTS`, `TEACHERS`
  - `status`: `PREVIEWED`, `COMPLETED`, `FAILED`, `EXPIRED`
  - uploader and original filename
  - total/valid/invalid row counts
  - row-level errors and warnings
  - normalized validated rows
  - created/skipped counts
  - completion timestamp

Supported templates:
- students:
  - `matricule,email,first_name,last_name,moyenne_generale,specialite,academic_year`
- teachers:
  - `matricule,email,first_name,last_name,grade,departement`

Student import behavior:
- creates `User` with `business_identity=STUDENT`
- creates/updates `StudentProfile`
- assigns explicit active `AcademicYear` by year label or current active year when omitted
- rejects missing active year, unknown year, `CLOSED` year, and `ARCHIVED` year
- creates the default solo team through existing team service

Teacher import behavior:
- creates `User` with `business_identity=TEACHER`
- creates/updates `TeacherProfile`
- does not attach teacher to an academic year

Validation rules:
- preview creates no users
- required columns are checked
- duplicate matricule/email inside the same file is invalid
- existing matricule/email in the database is invalid
- `moyenne_generale` must be between `0` and `20`
- formula-like values starting with `=`, `+`, `-`, or `@` are rejected in identity/name/template fields
- max file size: 5 MB
- max rows: 1000
- unsupported extensions are rejected
- CSV uses UTF-8 with BOM support

XLSX support status:
- `.xlsx` is supported only if `openpyxl` is installed in the runtime
- current dependency file does not declare `openpyxl`
- when unavailable, XLSX upload returns a clear validation error
- no dependency was added in this sprint to avoid changing the deployment image unexpectedly

Password behavior:
- imported users receive a secure random password internally
- generated passwords are never returned
- generated passwords are never logged
- generated passwords are never emailed
- imported users are saved with `must_reset_password=True`
- login with valid credentials is blocked while `must_reset_password=True`
- password reset confirmation clears `must_reset_password`

Import endpoints:
- `POST /api/admin/imports/users/preview/`
- `POST /api/admin/imports/users/confirm/`
- `GET /api/admin/imports/users/template/?import_type=STUDENTS`
- `GET /api/admin/imports/users/template/?import_type=TEACHERS`

Audit app:
- `apps.audit`

Audit model:
- `AdminActionLog`
  - actor
  - action type
  - target model/id/repr
  - timestamp
  - metadata
  - IP address
  - user agent

Audit rules:
- append-only in business logic
- no update endpoint
- no delete endpoint
- no password metadata
- no raw import file content metadata

Implemented audit action types include:
- `USER_IMPORT_PREVIEWED`
- `USER_IMPORT_COMPLETED`
- `USER_CREATED_BY_IMPORT`
- `ACADEMIC_YEAR_CLOSED`
- `ACADEMIC_YEAR_FORCE_CLOSED`
- `ACADEMIC_YEAR_REOPENED`
- `ACADEMIC_YEAR_ARCHIVED`
- `USER_CREATED`
- `USER_UPDATED`
- `USER_ARCHIVED`
- `PLATFORM_GRANT_CREATED`
- `PLATFORM_GRANT_REVOKED`
- placeholders for team, subject, assignment, appeal, and defense admin hooks

Implemented audit hooks:
- import preview
- import confirmation
- each imported user
- academic-year close / force close / reopen / archive
- platform grant create / revoke
- manual admin user create / update / archive

Audit endpoint:
- `GET /api/super-admin/audit/admin-actions/`

Audit access:
- super-admin only for log listing
- authorization uses active `PlatformAccessGrant`

Tests:
- `tests/test_sprint13_bulk_imports_audit.py`
- verifies preview validation, duplicate/existing-user handling, active-year rules, templates, confirm behavior, partial import, stored-row confirmation, hidden generated passwords, reset-required login block, reset completion, audit log creation, super-admin log access, and platform grant audit hooks

## 19) Recommended Next Sprints

The core PFE campaign backend is now functionally complete from identity through notifications. Remaining work should avoid changing the domain source of truth unless a real product requirement demands it.

### Sprint 14 — Security and Audit Hardening
Goal:
- tighten production safety around sensitive lifecycle and file actions

Recommended scope:
- object-level permission regression suite
- audit events for sensitive admin actions if needed
- rate limits for auth/password flows if infrastructure supports it
- file access hardening and optional signed URLs if product requires private downloads

Recommended backend shape:
- reuse `PlatformAccessGrant`
- optionally extend existing `audit` app
- no legacy role fallback

Risks/dependencies:
- define exactly which actions must be audit-grade before adding a broad audit engine

### Sprint 15 — Optional Product Enhancements
Goal:
- add quality-of-life features after core governance is stable

Possible scope:
- richer search/filtering
- admin correction tools with better previews
- notification preferences
- supervisor-owner distinction in UI/read APIs
- final archive browsing screens for admins

Out of scope unless explicitly approved:
- changing core assignment storage to assignment-run/result tables
- destructive archive cleanup
- child status cascade to `ARCHIVED`
- replacing `PlatformAccessGrant`
