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
  academic_year: number
  annual_average: string | null // DRF DecimalField serialises as string
  speciality: string
}

export interface TeacherProfile {
  grade: string
  department: string
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
  start_date: string
  end_date: string
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
  teacher_can_propose_subjects: boolean
  student_can_form_teams: boolean
  student_can_submit_wishlist: boolean
  student_can_see_results: boolean
  student_can_appeal: boolean
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

export interface Subject {
  id: number
  subject_code: string
  title: string
  description: string
  subject_type: SubjectType
  attachment_url: string | null
  attachment_key: string | null
  attachment_original_name: string | null
  attachment_mime_type: string | null
  attachment_size_bytes: number | null
  status: SubjectStatus
  academic_year: AcademicYear // nested object
  proposed_by: User
  rejection_reason: string | null
  submitted_at: string | null
  reviewed_at: string | null
  reviewed_by: User | null
  assigned_at: string | null
  assigned_to_team: string | null // team_code string
  created_at: string
  updated_at: string
}

// ─── Teams ────────────────────────────────────────────────────────────────────

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
  assignment_validated_by: User | null
  active_leader: Participation | null
  active_members: Participation[]
  active_supervisors: Participation[]
  pending_invitations: Participation[]
  created_at: string
  updated_at: string
  dissolved_at: string | null
}

// Slim Team shape used when Team is nested inside other responses
export interface TeamSummary {
  team_code: string
  name: string
  academic_year: number
  status: TeamStatus
  selected_subject_id: number | null
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
  selected_subject_id: number | null
  files_count: number
  members_summary: MemberSummary[]
}

// ─── Wishlists ────────────────────────────────────────────────────────────────

export interface WishlistItem {
  wishitem_id: string // uuid
  subject: Subject
  rank: number
}

export interface Wishlist {
  wishlist_id: string // uuid
  team: TeamSummary
  selection_round: SelectionRound
  status: WishlistStatus
  submitted_by: User
  submitted_at: string
  item_count: number
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
  submitted_by: User
  reviewed_by: User | null
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

export interface BulkAssignmentResult {
  selection_round: SelectionRound
  total_teams: number
  assigned_count: number
  unassigned_teams: string[] // array of team_codes
}

// ─── Deliverables ─────────────────────────────────────────────────────────────

export interface DeliverableFileComment {
  id: string // uuid
  author: User
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
  uploaded_by: User
  uploaded_at: string
  comment: string | null
  review_status: ReviewStatus
  reviewed_by: User | null
  reviewed_at: string | null
  review_comment: string | null
  comments: DeliverableFileComment[]
  created_at: string
  updated_at: string
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
