// ─── Status enums ─────────────────────────────────────────────────────────────

export type BusinessIdentity =
  | 'STUDENT'
  | 'TEACHER'
  | 'ADMINISTRATIVE_STAFF'
  | 'EXTERNAL_SUPERVISOR'

export type AccountStatus = 'ACTIVE' | 'SUSPENDED' | 'ARCHIVED'

export type PlatformAccessLevel = 'ADMIN' | 'SUPER_ADMIN'

export type AcademicYearStatus = 'ACTIVE' | 'CLOSED' | 'ARCHIVED'

export type PhaseType =
  | 'CAMPAIGN_SETUP'
  | 'SUBJECT_MANAGEMENT'
  | 'TEAM_FORMATION'
  | 'WISHLIST_1'
  | 'ASSIGNMENT_REVIEW_1'
  | 'RESULTS_AND_APPEALS'
  | 'WISHLIST_2'
  | 'ASSIGNMENT_REVIEW_2'
  | 'WORK_AND_SUPERVISION'
  | 'DEFENSE_WINDOW'
  | 'ARCHIVE'

export type SubjectType =
  | 'RESEARCH_PROJECT'
  | 'APPLIED_PROJECT'
  | 'STARTUP_PROJECT'

export type SubjectStatus =
  | 'DRAFT'
  | 'SUBMITTED'
  | 'APPROVED'
  | 'REJECTED'
  | 'ASSIGNED'
  | 'ARCHIVED'

export type TeamStatus =
  | 'FORMING'
  | 'LOCKED'
  | 'VALIDATED'
  | 'DISSOLVED'
  | 'ARCHIVED'

export type SelectionRound = 'FIRST' | 'SECOND'

export type ParticipationRole = 'LEADER' | 'MEMBER' | 'SUPERVISOR'

export type ParticipationStatus = 'PENDING' | 'ACTIVE' | 'ENDED' | 'REJECTED'

export type WishlistStatus = 'DRAFT' | 'SUBMITTED' | 'LOCKED' | 'ARCHIVED'

export type AppealStatus = 'PENDING' | 'ACCEPTED' | 'REJECTED'

export type ReviewStatus = 'PENDING' | 'ACCEPTED' | 'NEEDS_REVISION' | 'REJECTED'

// ─── User ─────────────────────────────────────────────────────────────────────

export interface StudentProfile {
  academic_year: number | null
  annual_average: string | null // DRF DecimalField serialises as string
  moyenne_generale: string | null
  speciality: string | null
  specialite: string | null
  cv_file_url: string | null
  skills_summary: string | null
}

export interface TeacherProfile {
  grade: string | null
  department: string | null
  departement: string | null
}

export interface User {
  id: number
  matricule: string
  email: string
  first_name: string
  last_name: string
  business_identity: BusinessIdentity
  account_status: AccountStatus
  platform_access_level: PlatformAccessLevel | null
  student_profile: StudentProfile | null
  teacher_profile: TeacherProfile | null
  // absent from login response, present on admin user detail
  created_at?: string
  updated_at?: string
}

// ─── Academic Years ───────────────────────────────────────────────────────────

export interface AcademicYear {
  id: number
  year: string
  year_label: string
  start_date: string | null
  end_date: string | null
  status: AcademicYearStatus
  wishlist_size: number
  created_at: string
  updated_at: string
}

// ─── Campaign Phases ──────────────────────────────────────────────────────────

export interface CampaignPhase {
  id: number
  academic_year: number // id only, not nested
  phase_type: PhaseType
  start_at: string
  end_at: string | null
  display_order: number
  is_archived: boolean
  created_at: string
  updated_at: string
}

export interface CampaignStatus {
  academic_year: { id: number; label: string; status: AcademicYearStatus } | null
  open_phases: PhaseType[]
  actions: {
    can_manage_team: boolean
    can_submit_first_wishlist: boolean
    can_view_subject_catalog: boolean
    can_run_first_assignment: boolean
    can_view_assignment_result: boolean
    can_submit_appeal: boolean
    can_submit_second_wishlist: boolean
  }
}

// ─── Platform Access Grants ───────────────────────────────────────────────────

export interface PlatformAccessGrant {
  id: number
  user: User
  access_level: PlatformAccessLevel
  granted_by: User
  granted_at: string
  revoked_at: string | null
  created_at: string
  updated_at: string
}

// ─── Subjects ─────────────────────────────────────────────────────────────────

// Slim summary types nested inside Subject responses
export interface SubjectAcademicYearSummary {
  id: number
  year: string
  status: AcademicYearStatus
}

export interface SubjectTeacherSummary {
  id: number
  matricule: string
  first_name: string
  last_name: string
  email: string
}

// Returned by GET /api/subjects/ (public catalog) and embedded in wishlist items
export interface PublicSubject {
  id: number
  subject_code: string | null
  title: string
  description: string
  subject_type: SubjectType
  attachment_url: string | null
  attachment_key: string | null
  proposed_by: SubjectTeacherSummary
  academic_year: SubjectAcademicYearSummary
  created_at: string
  updated_at: string
}

// Returned by GET /api/admin/subjects/ and GET /api/teacher/subjects/
export interface Subject {
  id: number
  subject_code: string | null
  title: string
  description: string
  subject_type: SubjectType
  attachment_url: string | null
  attachment_key: string | null
  attachment_original_name: string | null
  attachment_mime_type: string | null
  attachment_size_bytes: string | null // DRF serialises as string
  status: SubjectStatus
  academic_year: SubjectAcademicYearSummary
  proposed_by: SubjectTeacherSummary
  rejection_reason: string | null
  submitted_at: string | null
  reviewed_at: string | null
  reviewed_by: SubjectTeacherSummary | number | null // nested in admin view, integer in teacher view
  assigned_at: string | null
  assigned_to_team: string | null // team_code string
  created_at: string
  updated_at: string
}

// ─── Teams ────────────────────────────────────────────────────────────────────

export interface TeamListItem {
  team_code: string
  name: string
  academic_year: number
  status: TeamStatus
  selection_round: SelectionRound
  annual_average: string | null
  assignment_validated_at: string | null
  assignment_validated_by: number | null
  created_at: string
  updated_at: string
  dissolved_at: string | null
}

export interface Participation {
  participation_id: string // uuid
  user: User
  role: ParticipationRole
  status: ParticipationStatus
  joined_at: string | null
  ended_at: string | null
  created_at: string
  updated_at: string
}

export interface Team {
  team_code: string
  name: string
  academic_year: number // id only, not nested
  status: TeamStatus
  selection_round: SelectionRound
  annual_average: string | null // DRF DecimalField serialises as string
  selected_subject_id: number | null
  active_student_count: number
  assignment_validated_at: string | null
  assignment_validated_by: number | null // integer user ID
  active_leader: Participation | null
  active_members: Participation[]
  active_supervisors: Participation[]
  pending_invitations: Participation[]
  created_at: string
  updated_at: string
  dissolved_at: string | null
}

// Base Team shape embedded inside Wishlist and Appeal responses
// (does NOT include selected_subject_id, active_leader, active_members, etc.)
export interface TeamSummary {
  team_code: string
  name: string
  academic_year: number
  status: TeamStatus
  selection_round: SelectionRound
  annual_average: string | null
  assignment_validated_at: string | null
  assignment_validated_by: number | null // integer user ID
  created_at: string
  updated_at: string
  dissolved_at: string | null
}

export interface MemberSummary {
  id: number
  matricule: string
  email: string
  first_name: string
  last_name: string
  business_identity: BusinessIdentity
}

export interface SupervisionTeam {
  team_code: string
  name: string
  academic_year: number
  status: TeamStatus
  selected_subject_id: string | null // serialized as string by DRF
  files_count: string // serialized as string by DRF
  members_summary: MemberSummary[]
}

export interface ReceivedInvitation {
  participation_id: string // uuid
  team: {
    team_code: string
    name: string
    status: TeamStatus
    active_student_count: number
  }
  created_at: string
}

// ─── Wishlists ────────────────────────────────────────────────────────────────

export interface WishlistItem {
  wishitem_id: string // uuid
  subject: PublicSubject
  rank: number
}

// Slim shape returned by GET /api/admin/wishlists/ list endpoint — no items array.
export interface WishlistListItem {
  wishlist_id: string // uuid
  team: TeamSummary
  selection_round: SelectionRound
  status: WishlistStatus
  submitted_by: number | null // integer user ID
  submitted_at: string | null
  item_count: string // DRF serialises as string
  created_at: string
  updated_at: string
}

// Full shape returned by GET /api/admin/wishlists/<id>/ and GET /api/wishlists/me/.
export interface Wishlist {
  wishlist_id: string // uuid
  team: TeamSummary
  selection_round: SelectionRound
  status: WishlistStatus
  submitted_by: number | null // integer user ID
  submitted_at: string | null
  item_count: string // DRF serialises as string
  items: WishlistItem[]
  created_at: string
  updated_at: string
}

// ─── Appeals ──────────────────────────────────────────────────────────────────

export interface Appeal {
  appeal_id: string // uuid
  team: TeamSummary
  reason: string
  status: AppealStatus
  submitted_by: number | null // integer user ID
  reviewed_by: number | null // integer user ID
  submitted_at: string
  resolved_at: string | null
  admin_comment: string | null
  created_at: string
  updated_at: string
}

// ─── Assignments ──────────────────────────────────────────────────────────────

export interface Assignment {
  team_code: string
  team_status: TeamStatus
  selection_round: SelectionRound
  subject_id: number | null
  subject_title: string | null
}

// Actual response from POST /api/admin/assignments/merit/ and /random/.
export interface BulkAssignmentResult {
  mode: string
  selection_round: string
  assigned_teams: Array<{ team_code: string; subject_id: number; annual_average?: string }>
  unassigned_teams: Array<{ team_code: string; reason: string }>
  skipped_teams: Array<{ team_code: string; reason: string }>
}

// Response from POST /api/admin/assignments/manual/.
export interface ManualAssignmentResult {
  team_code: string
  subject_id: number
}

// ─── Deliverables ─────────────────────────────────────────────────────────────

export interface DeliverableFileComment {
  id: string // uuid
  author: MemberSummary
  text: string
  created_at: string
  updated_at: string
}

export interface DeliverableFile {
  id: string // uuid
  team: TeamSummary
  file_url: string
  original_filename: string
  file_size: number
  content_type: string
  uploaded_by: MemberSummary
  uploaded_at: string
  comment: string | null
  review_status: ReviewStatus
  reviewed_by: MemberSummary | null
  reviewed_at: string | null
  review_comment: string | null
  comments: DeliverableFileComment[]
  created_at: string
  updated_at: string
}

// ─── Notifications (Sprint 11 backend) ───────────────────────────────────────

export type NotificationType =
  | 'TEAM_INVITATION_RECEIVED'
  | 'TEAM_MEMBER_JOINED'
  | 'TEAM_MEMBER_LEFT'
  | 'TEAM_MEMBER_REMOVED'
  | 'LEADERSHIP_TRANSFERRED'
  | 'TEAM_LOCKED'
  | 'SUBJECT_SUBMITTED'
  | 'SUBJECT_APPROVED'
  | 'SUBJECT_REJECTED'
  | 'SUBJECT_RESUBMITTED'
  | 'ASSIGNMENT_RESULT_AVAILABLE'
  | 'APPEAL_SUBMITTED'
  | 'APPEAL_ACCEPTED'
  | 'APPEAL_REJECTED'
  | 'DELIVERABLE_UPLOADED'
  | 'DELIVERABLE_REVIEWED'
  | 'DELIVERABLE_COMMENT_ADDED'
  | 'DEFENSE_REQUESTED'
  | 'DEFENSE_SUPERVISOR_ACCEPTED'
  | 'DEFENSE_SUPERVISOR_DENIED'
  | 'DEFENSE_READY_TO_SCHEDULE'
  | 'DEFENSE_SCHEDULED'
  | 'DEFENSE_RESCHEDULED'
  | 'JURY_ASSIGNED'
  | 'PV_UPLOADED'
  | 'ACADEMIC_YEAR_CLOSED'
  | 'ACADEMIC_YEAR_FORCE_CLOSED'
  | 'ACADEMIC_YEAR_REOPENED'
  | 'ACADEMIC_YEAR_ARCHIVED'

export type NotificationImportance = 'NORMAL' | 'IMPORTANT'

// GET /api/notifications/ returns a flat array (NOT a paginated envelope).
// Supports ?unread=true&limit=N&offset=N for limit/offset paging.
export interface Notification {
  id: number
  type: NotificationType
  importance: NotificationImportance
  title: string
  message: string
  link_url: string // empty string when no link
  is_read: boolean
  read_at: string | null
  metadata: Record<string, unknown>
  created_at: string
}

export interface UnreadCountResponse {
  unread_count: number
}

export interface MarkAllReadResponse {
  updated: number
}

// ─── Dashboards (Sprint 12 backend) ───────────────────────────────────────────

export interface DashboardAcademicYearSummary {
  id: number
  year: string
  status: AcademicYearStatus
}

// Admin dashboard — GET /api/dashboard/admin/
export interface AdminDashboard {
  academic_year: DashboardAcademicYearSummary
  teams: {
    total: number
    forming: number
    locked: number
    validated: number
    dissolved: number
  }
  assignments: {
    assigned: number
    unassigned: number
  }
  defenses: {
    total: number
    requested: number
    ready_to_schedule: number
    scheduled: number
    completed: number
    cancelled: number
  }
  appeals: {
    total: number
    pending_or_submitted: number
    accepted: number
    rejected: number
  }
  deliverables: {
    total_files: number
    pending_review: number
    accepted: number
    needs_revision: number
    rejected: number
  }
  subjects: {
    total: number
    draft: number
    submitted: number
    approved: number
    assigned: number
    rejected: number
  }
}

// Teacher dashboard — GET /api/dashboard/teacher/
export interface TeacherDashboardPendingDeliverable {
  file_id: string
  original_filename: string
  team_code: string
  uploaded_at: string
  uploaded_by: string
}

export interface TeacherDashboardUpcomingDefense {
  defense_id: string
  team_code: string
  team_name: string
  scheduled_at: string
  location: string
  role_context: 'SUPERVISOR' | 'JURY' | 'SUPERVISOR,JURY'
}

export interface TeacherDashboard {
  academic_year: DashboardAcademicYearSummary
  supervision: {
    supervised_teams_count: number
    validated_supervised_teams_count: number
  }
  deliverables: {
    pending_review_count: number
    latest_pending_review: TeacherDashboardPendingDeliverable[]
  }
  defenses: {
    upcoming_count: number
    pending_requests_count: number
    upcoming: TeacherDashboardUpcomingDefense[]
  }
}

// Student dashboard — GET /api/dashboard/student/
export interface StudentDashboardMember {
  id: number
  name: string
  role: ParticipationRole
}

export interface StudentDashboardTeam {
  team_code: string
  name: string
  status: TeamStatus
  role: ParticipationRole
  members: StudentDashboardMember[]
  supervisors: StudentDashboardMember[]
}

export interface StudentDashboardSubject {
  id: number
  title: string
  type: SubjectType
  status: SubjectStatus
}

export interface StudentDashboardDefense {
  id: string
  status: string // backend uses its Defense.Status enum — keep loose to avoid coupling
  scheduled_at: string
  location: string
  final_grade: string
  pv_uploaded: boolean
}

export interface StudentDashboardDeliverable {
  file_id: string
  original_filename: string
  uploaded_at: string
  uploaded_by: string
  review_status: ReviewStatus
}

export interface StudentDashboard {
  academic_year: DashboardAcademicYearSummary
  team: StudentDashboardTeam | null
  subject: StudentDashboardSubject | null
  defense: StudentDashboardDefense | null
  deliverables: {
    total_files: number
    latest: StudentDashboardDeliverable[]
  }
  assignment: {
    selection_round: SelectionRound | ''
    assigned: boolean
  }
}

// ─── Defenses (Sprint 8 backend) ─────────────────────────────────────────────

export type DefenseStatus =
  | 'REQUESTED'
  | 'READY_TO_SCHEDULE'
  | 'SCHEDULED'
  | 'COMPLETED'
  | 'CANCELLED'
  | 'ARCHIVED'

export type DefenseSupervisorDecisionStatus = 'PENDING' | 'ACCEPTED' | 'DENIED'

export type DefenseJuryRole = 'PRESIDENT' | 'EXAMINER' | 'GUEST'

export interface DefenseAttachedFile {
  id: string // uuid
  deliverable_file: DeliverableFile
  order: number
  added_by: MemberSummary
  added_at: string
}

export interface DefenseSupervisorDecision {
  id: string // uuid
  supervisor: MemberSummary
  decision: DefenseSupervisorDecisionStatus
  decided_at: string | null
}

export interface DefenseJuryAssignment {
  id: string // uuid
  user: MemberSummary
  role: DefenseJuryRole
  assigned_by: MemberSummary
  assigned_at: string
}

// Slim shape returned by list endpoints (admin / jury / supervisor list).
export interface DefenseListItem {
  id: string // uuid
  team: Team
  status: DefenseStatus
  requested_by: number | null // integer user ID
  requested_at: string
  scheduled_at: string | null
  location: string
  scheduled_by: number | null
  final_grade: string | null
  deliberation: string
  pv_file: string | null
  pv_uploaded_by: number | null
  pv_uploaded_at: string | null
  created_at: string
  updated_at: string
}

// Full shape returned by detail endpoints and request/accept/deny/schedule responses.
// GET /api/defenses/me/ returns `{}` when the student has no defense — callers
// must guard with an `'id' in response` check before treating as a Defense.
export interface DefenseDetail extends Omit<DefenseListItem, 'requested_by' | 'scheduled_by' | 'pv_uploaded_by'> {
  requested_by: MemberSummary
  scheduled_by: MemberSummary | null
  pv_uploaded_by: MemberSummary | null
  pv_file_url: string
  attached_files: DefenseAttachedFile[]
  supervisor_decisions: DefenseSupervisorDecision[]
  jury_assignments: DefenseJuryAssignment[]
}

// ─── Auth responses ───────────────────────────────────────────────────────────

export interface LoginResponse {
  access: string
  refresh: string
  user: User
}

// ─── Pagination ───────────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

// ─── API errors ───────────────────────────────────────────────────────────────

export interface ApiError {
  detail?: string
  [field: string]: string | string[] | undefined
}
