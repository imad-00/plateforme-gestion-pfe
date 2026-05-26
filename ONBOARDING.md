# GradeX Frontend — Onboarding Guide

> **Read this alongside `CLAUDE.md` (repo root `gradex/CLAUDE.md`).** That file is the authoritative reference for the API endpoint catalogue, request/response shapes, auth flow, user roles, and the Style Guide (colors, typography, spacing). This document covers the frontend architecture, conventions, and what remains to be built.

---

## 1. Project Overview

GradeX is a PFE (Final Year Project) management platform used by students, teachers, external supervisors, and administrative staff to manage team formation, subject selection, assignments, and deliverable review.

**Stack (read from `package.json` and `next.config.ts`):**
- Next.js 16.2.3 · React 19.2.4 · TypeScript 5 · Tailwind v4
- shadcn component library (Radix UI primitives, `radix-ui` package)
- `lucide-react` for icons · `react-hook-form` (available but not yet used)
- React Compiler enabled (`reactCompiler: true` in `next.config.ts`) — no need to manually `useMemo`/`useCallback` for perf

**Repo layout:**
```
gradex/
├── CLAUDE.md                        ← API reference, auth, roles, Style Guide — READ THIS
├── backend/                         ← Django backend (separate repo, never touch)
│   └── backend/
│       ├── manage.py
│       └── apps/                    ← accounts, academics, campaigns, topics, teams, …
└── plateforme-gestion-pfe/          ← Next.js frontend (your working directory)
    ├── src/
    │   ├── app/
    │   │   ├── layout.tsx           ← root layout, mounts AuthProvider
    │   │   ├── (auth)/              ← public pages (login, forgot-password)
    │   │   └── (app)/               ← authenticated pages (sidebar + topbar shell)
    │   ├── components/
    │   │   ├── ui/                  ← shadcn primitives (button, card, dialog, …)
    │   │   ├── layout/              ← sidebar, topbar, page-header
    │   │   └── shared/              ← data-table, status-badge, confirm-dialog, empty-state
    │   ├── lib/
    │   │   ├── api-client.ts        ← fetch wrapper with JWT + silent refresh
    │   │   ├── auth-context.tsx     ← AuthProvider + useAuth hook
    │   │   └── types.ts             ← TypeScript types matching backend response shapes
    │   ├── hooks/
    │   │   └── use-api.ts           ← { data, isLoading, error, refetch } hook
    │   └── middleware.ts            ← session-cookie route protection
    └── CLAUDE.md                    ← NOT present; the API reference lives at gradex/CLAUDE.md
```

---

## 2. Environment

### Shell — Windows + PowerShell

The dev machine runs **Windows 11 with PowerShell**. The `&&` operator **does not work** in PowerShell 5.1 (it throws a parser error). Run commands on separate lines or chain with `;` when failure of the first doesn't matter:

```powershell
# ✗ wrong
cd plateforme-gestion-pfe && npm run dev

# ✓ correct
cd plateforme-gestion-pfe
npm run dev
```

### Running the frontend

```powershell
cd c:\Users\ibrah\Documents\gradex\plateforme-gestion-pfe
npm run dev          # starts on http://localhost:3000
```

TypeScript check (run after every change):
```powershell
npx tsc --noEmit
```

### Backend

The Django backend lives in `gradex/backend/` and is run via Docker Compose on a **teammate's branch** — do not modify backend files. Typical start:

```powershell
cd c:\Users\ibrah\Documents\gradex\backend
docker-compose up
# API available at http://localhost:8000
```

Set `NEXT_PUBLIC_API_URL=http://localhost:8000` in `.env.local` if not already present (the api-client defaults to that value when the env var is absent).

### Seeding demo data

The backend has a management command that seeds accounts, an academic year, campaign phases, and approved subjects:

```bash
# inside the backend container or with the venv activated:
python manage.py seed

# To seed with a specific campaign phase open (controls phase-gating):
python manage.py seed --phase TEAM_FORMATION
python manage.py seed --phase WISHLIST_1
python manage.py seed --phase WORK_AND_SUPERVISION
```

**`--phase` choices** (from the seed command source):
`CAMPAIGN_SETUP`, `SUBJECT_MANAGEMENT`, `TEAM_FORMATION`, `WISHLIST_1`, `ASSIGNMENT_REVIEW_1`, `RESULTS_AND_APPEALS`, `WISHLIST_2`, `ASSIGNMENT_REVIEW_2`, `WORK_AND_SUPERVISION`, `DEFENSE_WINDOW`, `ARCHIVE`

The seed command is **idempotent** — safe to run multiple times.

### Demo accounts (from `seed.py`)

All accounts share the password: **`Testpass123!`**

| Matricule | Email | Role | Notes |
|---|---|---|---|
| `STU001` | student@example.com | Student | Primary student |
| `STU002` | student2@example.com | Student | Alice Martin |
| `STU003` | student3@example.com | Student | Yacine Boudiaf |
| `STU004` | student4@example.com | Student | Sara Hamdi |
| `TEA001` | teacher@example.com | Teacher | Owns seeded subjects |
| `ADM001` | admin@example.com | Admin staff | `ADMIN` platform grant |
| `SADM001` | superadmin@example.com | Admin staff | `SUPER_ADMIN` grant |

---

## 3. Architecture & Conventions

### Route groups

The App Router uses two route groups:

- **`(auth)/`** — public pages (login, forgot-password). Layout: centered card, no sidebar. No auth check.
- **`(app)/`** — all authenticated pages. Layout defined in `src/app/(app)/layout.tsx`: checks `useAuth()`, redirects unauthenticated users to `/login`, redirects users to their correct section if they navigate to the wrong role's routes.

Role-to-section mapping (from `(app)/layout.tsx`):
```
platform_access_level set       → /admin/*
business_identity STUDENT       → /student/*
business_identity TEACHER       → /teacher/*
business_identity EXTERNAL_SUPERVISOR → /teacher/*
```

The middleware (`src/middleware.ts`) only checks for the `gradex_session` cookie and redirects to `/login` if absent. Fine-grained role enforcement happens client-side in the layout.

### The Server-shell + Client-view pattern

**Every page** follows this exact split — no exceptions:

```
src/app/(app)/admin/users/
├── page.tsx          ← Server Component: exports metadata + wraps view in <Suspense>
└── users-view.tsx    ← Client Component ('use client'): owns all data fetching and UI
```

`page.tsx` is always ~10 lines:
```tsx
import type { Metadata } from 'next'
import { Suspense } from 'react'
import { UsersView } from './users-view'

export const metadata: Metadata = { title: 'Users — GradeX' }

export default function AdminUsersPage() {
  return (
    <Suspense>
      <UsersView />
    </Suspense>
  )
}
```

All data fetching is in the `*-view.tsx` file. Tokens live in browser memory/localStorage and are unavailable to Server Components, which is why everything authenticated is a Client Component.

### API client (`src/lib/api-client.ts`)

```typescript
import { api, ApiClientError } from '@/lib/api-client'

// GET
const data = await api.get<PaginatedResponse<User>>('/api/admin/users/')

// POST (JSON)
await api.post('/api/admin/users/', { matricule: '...', ... })

// POST (file upload — FormData path: browser sets Content-Type with boundary)
const form = new FormData()
form.append('file', file)
await api.post('/api/deliverable-files/upload/', form)

// PATCH
await api.patch('/api/admin/users/1/', { account_status: 'SUSPENDED' })

// Error handling
try {
  await api.post(...)
} catch (err) {
  if (err instanceof ApiClientError) {
    // err.status  → HTTP status code
    // err.data    → { detail?: string, [field]: string[] }
  }
}
```

**Silent refresh:** on a 401 response the client automatically calls `POST /api/auth/refresh/`, updates the access token, and retries the original request once. If refresh also fails, `logout()` is called automatically and the user is redirected to `/login`. You never handle token refresh manually.

**Circular-import note:** `api-client.ts` does not import from `auth-context.tsx`. Instead, `AuthProvider` calls `registerAuth(callbacks)` on mount to wire up token read/write. This is already done — don't change it.

### Auth context (`src/lib/auth-context.tsx`)

```typescript
const { user, isLoading, login, logout } = useAuth()

// user: User | null
// user.business_identity: 'STUDENT' | 'TEACHER' | 'ADMINISTRATIVE_STAFF' | 'EXTERNAL_SUPERVISOR'
// user.platform_access_level: 'ADMIN' | 'SUPER_ADMIN' | null
// user.student_profile / user.teacher_profile: nested profile objects (nullable)
```

Call `useAuth()` at the top of every view component. It throws if called outside `AuthProvider`, which serves as a safety net. No need to redirect manually in views — the layout handles that.

### `useApi` hook (`src/hooks/use-api.ts`)

```typescript
const { data, isLoading, error, refetch } = useApi<PaginatedResponse<User>>(
  () => api.get('/api/admin/users/'),
  [],  // dependency array — re-fetches when these values change
)
```

- `data` starts as `null`, then becomes the resolved value
- `error` is a string (the extracted message) or `null`
- `refetch()` re-runs the fetcher without changing deps
- The fetcher is stored in a ref (`fetcherRef.current = fetcher`) so it always uses the latest closure — safe to close over state variables in deps

For paginated endpoints with filter state:
```typescript
const [page, setPage] = useState(1)
const [search, setSearch] = useState('')

const usersApi = useApi<PaginatedResponse<User>>(
  () => {
    const params = new URLSearchParams({ page: String(page) })
    if (search) params.set('search', search)
    return api.get(`/api/admin/users/?${params}`)
  },
  [page, search],  // re-fetch when either changes
)
```

### Shared components

**`DataTable<T>`** (`src/components/shared/data-table.tsx`):
```typescript
import { DataTable, type Column } from '@/components/shared/data-table'

const columns: Column<User>[] = [
  { key: 'matricule', header: 'Matricule', render: u => <span>{u.matricule}</span> },
  { key: 'account_status', header: 'Status', render: u => <StatusBadge status={u.account_status} /> },
  { key: 'actions', header: '', render: u => <Button onClick={() => setEdit(u)}>Edit</Button> },
]

<DataTable<User>
  columns={columns}
  data={usersApi.data?.results ?? []}
  keyField="id"               // must be a keyof T
  isLoading={usersApi.isLoading}
  page={page}
  pageSize={pageSize}
  total={usersApi.data?.count ?? 0}
  onPageChange={setPage}
  onPageSizeChange={size => { setPageSize(size); setPage(1) }}
  emptyState={<EmptyState icon={Users} title="No users" />}
/>
```

**`StatusBadge`** (`src/components/shared/status-badge.tsx`):
```tsx
<StatusBadge status="APPROVED" />          // auto-formats label
<StatusBadge status="SUPER_ADMIN" label="Super Admin" />  // override label
```
Maps backend status strings to the four color tiers defined in the Style Guide. Unknown values fall back to neutral.

**`ConfirmDialog`** (`src/components/shared/confirm-dialog.tsx`):
```tsx
<ConfirmDialog
  open={archiveUser !== null}
  onOpenChange={open => { if (!open) { setArchiveUser(null); setError(null) } }}
  title="Archive User"
  description="This cannot be undone."
  confirmLabel="Archive"
  destructive          // red confirm button
  isLoading={loading}
  error={error}        // shown inline inside the dialog on failure
  onConfirm={handleArchive}
/>
```
The `error` prop was added to the shared component — always pass it so failures display without closing the dialog.

**`EmptyState`** (`src/components/shared/empty-state.tsx`):
```tsx
<EmptyState icon={Users} title="No users found" description="Try adjusting filters." />
```

**`PageHeader`** (`src/components/layout/page-header.tsx`):
```tsx
<PageHeader
  title="Users"
  description="Manage platform users."
  action={<Button onClick={...}>New User</Button>}
/>
```

### Recurring per-page helpers

Every view file defines these locally (copy the pattern, don't share them to avoid tight coupling):

```typescript
// Error message extraction from ApiClientError or plain Error
function extractMessage(err: unknown): string {
  if (err instanceof ApiClientError) {
    const d = err.data as Record<string, unknown>
    const first = Object.values(d).flat().find(v => typeof v === 'string')
    return (first as string | undefined) ?? err.message
  }
  return err instanceof Error ? err.message : 'An unexpected error occurred.'
}

// Inline error banner
function InlineError({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg bg-status-error-bg p-3 text-sm text-status-error-fg">
      <AlertCircle className="mt-0.5 size-4 shrink-0" />
      <span>{message}</span>
    </div>
  )
}

// Loading skeleton (3 placeholder cards)
function LoadingSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-[120px] w-full rounded-xl" />
      <Skeleton className="h-[120px] w-full rounded-xl" />
    </div>
  )
}
```

### Phase-gating pattern

Many actions are only available when a specific campaign phase is open. Fetch `GET /api/campaign/current/` and check `open_phases` or `actions`:

```typescript
const campaignApi = useApi<CampaignStatus>(() => api.get('/api/campaign/current/'), [])

// Using open_phases directly:
const canUpload = campaignApi.data?.open_phases.includes('WORK_AND_SUPERVISION') ?? false

// Using per-action flags:
const canSubmitWishlist = campaignApi.data?.actions.can_submit_first_wishlist ?? false
```

Show a notice (not an error) when gating is the reason an action is unavailable. See `student/deliverables/deliverables-view.tsx` for the `UploadNotice` / `uploadBlockReason` pattern.

### Reference example

**`src/app/(app)/admin/users/users-view.tsx`** is the most complete example — it demonstrates: paginated `DataTable`, filter bar with debounced search + `Select` dropdowns, `DropdownMenu` per-row actions, create/edit `Dialog` with shared form fields, `ConfirmDialog` for archive + revoke, super-admin conditional UI, and the full grants map lookup. Read it before building any new admin page.

---

## 4. Gotchas & Lessons Learned

### 1. All list endpoints return a paginated envelope

**Always** unwrap `.results`:
```typescript
// ✗ wrong
const files = filesApi.data ?? []

// ✓ correct
const files = filesApi.data?.results ?? []
```

And use `PaginatedResponse<T>` as the generic:
```typescript
const filesApi = useApi<PaginatedResponse<DeliverableFile>>(...)
```

The OpenAPI schema (`gradex/schema.json`) sometimes declares list endpoints as `type: array` when the actual runtime response is the paginated envelope. **Trust the runtime, not the schema.** This caused a `files.map is not a function` crash in early development — it's the most common trap.

### 2. `GET /api/campaign/current/` shape

The response is always:
```json
{
  "academic_year": { "id": 1, "label": "2024-2025", "status": "ACTIVE" } | null,
  "open_phases": ["WISHLIST_1"],
  "actions": {
    "can_manage_team": true,
    "can_submit_first_wishlist": true,
    "can_view_subject_catalog": true,
    "can_run_first_assignment": false,
    "can_view_assignment_result": false,
    "can_submit_appeal": false,
    "can_submit_second_wishlist": false
  }
}
```
It is **not** a flat object of flags. It was initially built against wrong assumptions — any view that reads this endpoint must use the `CampaignStatus` type from `types.ts`.

### 3. DRF serializes some numbers as strings

These fields come back as strings, not numbers, even though they are numeric:
- `Subject.attachment_size_bytes` → `string | null`
- `SupervisionTeam.files_count` → `string`
- `SupervisionTeam.selected_subject_id` → `string | null`
- `Wishlist.item_count` → `string`
- `Team.annual_average` / `TeamSummary.annual_average` → `string | null`

Use `Number(team.files_count)` when you need arithmetic. The `types.ts` file already reflects these as `string`.

### 4. Some FK fields are integer IDs, not nested objects

These come back as plain numbers:
- `Team.assignment_validated_by` → `number | null` (not a `User`)
- `Team.academic_year` → `number` (not an `AcademicYear`)
- `Wishlist.submitted_by` → `number | null`
- `Appeal.submitted_by` / `Appeal.reviewed_by` → `number | null`
- `Subject.reviewed_by` in teacher view → `number | null` (admin view nests the object)

Do not try to render `.first_name` on these — they are IDs only. Use `MemberSummary` (which has `first_name`, `last_name`) for fields that do carry nested user data (e.g. `DeliverableFile.uploaded_by`, `DeliverableFileComment.author`).

### 5. CLAUDE.md is a spec, the live API is the truth

The CLAUDE.md API reference was written during backend development and has been corrected multiple times. When in doubt, hit the actual endpoint with the live backend (or check `gradex/schema.json`, which is the raw OpenAPI output). The live API is always authoritative. Discrepancies between CLAUDE.md and the actual response should be fixed in CLAUDE.md after confirming.

### 6. Phase-gating depends on the currently-open phase, not the user's role

Actions like "Upload Deliverable" or "Submit Wishlist" fail even for valid users if the wrong campaign phase is open. The `seed --phase <PHASE>` command controls this for local testing. If something unexpectedly returns 403 or 400, check `GET /api/campaign/current/` first.

### 7. `GET /api/appeals/me/` returns `{}` when no appeal exists

Not `null`, not a 404 — an empty object. Guard with:
```typescript
const rawAppeal = appealsApi.data
const appeal = rawAppeal && 'appeal_id' in rawAppeal ? rawAppeal as Appeal : null
```

### 8. File URLs need prefixing in local dev

When the backend runs with `USE_S3=0`, `file_url` fields are relative paths (`/media/...`). Build the full URL with:
```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
const fullUrl = path.startsWith('http') ? path : `${API_BASE}${path}`
```
When `USE_S3=1` (MinIO), `file_url` is already an absolute URL — the conditional handles both cases.

---

## 5. Work Remaining

### ALREADY BUILT — Do not rebuild; reuse these

Read this before starting any new page. Everything listed here exists in the repo, compiles, and passes `npx tsc --noEmit`. Do not re-implement any of it — import and extend instead.

#### Sprint 1 Foundation (complete and tested)

| File | What it does |
|---|---|
| `src/lib/types.ts` | All TypeScript types matching backend response shapes |
| `src/lib/api-client.ts` | Fetch wrapper: JWT attach, silent refresh on 401, `api.get/post/patch`, `ApiClientError` |
| `src/lib/auth-context.tsx` | `AuthProvider`, `useAuth()` hook, `login()`, `logout()`, `restoreSession()` |
| `src/middleware.ts` | Checks `gradex_session` cookie; redirects unauthenticated requests to `/login` |
| `src/hooks/use-api.ts` | `useApi<T>(fetcher, deps)` → `{ data, isLoading, error, refetch }` |
| `src/app/globals.css` | All CSS design tokens (colors, status colors, radius, shadows) — the full Style Guide |
| `src/app/(auth)/login/` | Login page — `POST /api/auth/login/`, stores tokens, sets session cookie, redirects by role |
| `src/app/(auth)/forgot-password/` | 3-step flow — request OTP → verify → confirm new password |
| `src/app/(app)/layout.tsx` | Authenticated shell: restores session on mount, enforces role-to-section routing |
| `src/components/layout/sidebar.tsx` | Role-aware navigation sidebar |
| `src/components/layout/topbar.tsx` | User info chip + logout button |
| `src/components/layout/page-header.tsx` | `<PageHeader title description action? />` |
| `src/components/shared/data-table.tsx` | Generic paginated table — `<DataTable columns data keyField isLoading page pageSize total onPageChange />` |
| `src/components/shared/status-badge.tsx` | `<StatusBadge status />` — maps backend status strings to colored badges |
| `src/components/shared/confirm-dialog.tsx` | `<ConfirmDialog open onConfirm destructive? error? />` — has inline error display via `error` prop |
| `src/components/shared/empty-state.tsx` | `<EmptyState icon title description? />` |

shadcn UI primitives installed in `src/components/ui/`: `avatar`, `badge`, `button`, `card`, `dialog`, `dropdown-menu`, `input`, `label`, `select`, `separator`, `skeleton`, `sonner`, `table`, `tabs`, `textarea`.

#### Sprint 2 pages (9 of 11 built)

Every route below has both a `page.tsx` (Server Component shell) and a `*-view.tsx` (Client Component). Do not create new files in these directories.

| Route | View file | Test status |
|---|---|---|
| `/login` | `(auth)/login/login-view.tsx` | Fully tested |
| `/forgot-password` | `(auth)/forgot-password/forgot-password-view.tsx` | Fully tested |
| `/student/team` | `student/team/team-view.tsx` | Fully tested |
| `/student/subjects` | `student/subjects/subjects-view.tsx` | Fully tested |
| `/student/results` | `student/results/results-view.tsx` | Smoke-tested — needs `/admin/assignments` to produce data |
| `/student/deliverables` | `student/deliverables/deliverables-view.tsx` | Smoke-tested — needs `/admin/assignments` to produce data |
| `/teacher/subjects` | `teacher/subjects/subjects-view.tsx` | Fully tested |
| `/teacher/supervision` | `teacher/supervision/supervision-view.tsx` | Smoke-tested — needs assignment data for supervised teams |
| `/admin/users` | `admin/users/users-view.tsx` | Fully tested |
| `/admin/academic-years` | `admin/academic-years/academic-years-view.tsx` | Fully tested |
| `/admin/subjects` | `admin/subjects/subjects-view.tsx` | Fully tested |

**Smoke-tested pages** render correctly and handle empty/error states, but their core data paths (results display, file upload, file review) require a team to be VALIDATED with an assigned subject — which only `/admin/assignments` can produce. Full end-to-end testing of these three pages is deferred to Sprint 3.

**Remaining (placeholders — `page.tsx` only, no view file yet):**

| Route | File | Status |
|---|---|---|
| `/admin/teams` | `admin/teams/page.tsx` | ⏳ Placeholder |
| `/admin/assignments` | `admin/assignments/page.tsx` | ⏳ Placeholder |

---

### Sprint 2 — 2 admin pages remaining (build in this order)

#### `/admin/teams` — Teams Management

```
Build the Admin "Teams" page — route /admin/teams. Use the admin team endpoints in CLAUDE.md.

List: GET /api/admin/teams/ (paginated) — use the DataTable shared component.
Filters: ?status=FORMING, ?academic_year=<id>, ?search=<name>. Show team code, name,
status badge, member count (active_student_count), annual average, assigned subject ID if any.

Per-team expandable detail (or a Detail Dialog) showing:
- Active members with their names and roles
- Active supervisors
- Pending invitations

Actions (all guarded with ConfirmDialog where destructive):
- Remove member: POST /api/admin/teams/<team_code>/remove-member/ — body: { student_id, dissolve_if_needed: false }
- Transfer leadership: POST /api/admin/teams/<team_code>/transfer-leadership/ — body: { new_leader_id }
- Add supervisor: POST /api/admin/teams/<team_code>/supervisors/ — body: { user_id }
  (requires a user selector — either an Input for the user's ID or a search-based Select)
- Remove supervisor: POST /api/admin/teams/<team_code>/supervisors/remove/ — body: { user_id }
- Dissolve team: POST /api/admin/teams/<team_code>/dissolve/ — destructive, ConfirmDialog.

Match the Style Guide, use the API client, use-api hook, data-table, status-badge, confirm-dialog.
Handle loading/error/empty states. Follow the Server-shell + Client-view pattern.
Show me the diff.
```

#### `/admin/assignments` — Assignment Running & Appeals

```
Build the Admin "Assignments" page — route /admin/assignments. Use the admin assignment,
wishlist, and appeal endpoints in CLAUDE.md. This is the most complex admin page — use tabs
to organize it.

Tab 1 — Run Assignments:
  Three assignment algorithms. Each has a "Run" button that calls its endpoint and shows
  the result ({ selection_round, total_teams, assigned_count, unassigned_teams }).

  - Merit assignment: POST /api/admin/assignments/merit/ — body: { selection_round: "FIRST"|"SECOND" }
  - Random assignment: POST /api/admin/assignments/random/ — body: { selection_round, seed? }
  - Manual assignment: POST /api/admin/assignments/manual/ — body: { team_code, subject_id }
    (requires two inputs: team code and subject ID)

  Validate an individual team's assignment:
  POST /api/admin/assignments/<team_code>/validate/ — body: {}
  Show a table of teams with their current assignment status. A "Validate" button per row.

Tab 2 — Wishlists:
  List all submitted wishlists: GET /api/admin/wishlists/ (paginated).
  Filters: ?selection_round=FIRST&status=SUBMITTED&team_code=X.
  Show team code, round, status, item count, submitted-at.
  Expandable row or dialog showing the ranked subject list.

Tab 3 — Appeals:
  List all appeals: not directly available but can be inferred from assignment data.
  Actually use GET /api/admin/wishlists/ with filters, and for appeals fetch them from
  the assignments overview.
  
  For each appeal: show team, reason, status badge, submitted-at.
  Actions:
  - Accept: POST /api/admin/appeals/<appeal_id>/accept/ — ConfirmDialog. Note: accepting
    releases the team's subject and enters them in the second round.
  - Reject: POST /api/admin/appeals/<appeal_id>/reject/ — body: { admin_comment: "optional" }.
    Open a small Dialog with an optional Textarea for the comment.

  NOTE: There is no GET /api/admin/appeals/ list endpoint documented. Check GET /api/admin/wishlists/
  or look at the live API for how to list all appeals. Confirm with the backend before building.

Use shadcn Tabs. Match the Style Guide, use the API client, use-api hook, data-table,
status-badge, confirm-dialog. Handle loading/error/empty states.
Follow the Server-shell + Client-view pattern. Show me the diff.
```

---

### Sprint 3 — Integration & polish (after Sprint 2)

Once `/admin/assignments` exists and can produce real assignment data:

1. **End-to-end workflow testing** — run the full student flow: team formation → wishlist → assignment → result + appeal → deliverable upload → teacher review. This requires seeding through multiple phases using `seed --phase`.
2. **Integration bug fixes** — fix any issues discovered during full-flow testing. Expect API shape mismatches, phase-gating edge cases, and cross-page state staleness.
3. **UI consistency pass** — verify every page matches the Style Guide: colors, spacing, badge usage, loading/empty/error states, dialog patterns.
4. **Full test of `/student/results`, `/student/deliverables`, `/teacher/supervision`** — these pages were built but couldn't be tested end-to-end without assignment data (which `/admin/assignments` now produces). Test the review flow, comment posting, and file download.

---

### Sprint 4 — QA, demo prep, buffer

- Bug-fix buffer for anything uncovered in Sprint 3
- Demo / soutenance scenario walkthrough (June 3 deadline)
- Verify `npm run build` produces zero errors

---

## 6. Workflow

### How a page gets built

1. **Write one focused prompt** (use the templates in Section 5).
2. **Review the diff** — check that the new files match conventions: correct imports, `useApi` with the right generic, `PaginatedResponse<T>` unwrapped, `extractMessage` pattern, no hardcoded data.
3. **Type-check:** `npx tsc --noEmit` — must be zero errors.
4. **Test against the live backend** — seed the right phase, log in as the relevant demo account, exercise every action including error states.
5. **Commit** the two files (`page.tsx` + `*-view.tsx`).

### Standard per-page prompt pattern

```
Build the Admin "[Name]" page — route /admin/[route]. Use the [relevant] endpoints in CLAUDE.md.

List: GET /api/admin/[endpoint]/ (paginated) — use the DataTable shared component. Show [columns].
[Filters if any.]

[Action 1]: [description] via [endpoint] — [guard if needed].
[Action 2]: ...

Match the Style Guide, use the API client, use-api hook, data-table, status-badge, confirm-dialog.
Handle loading/error/empty states. Follow the Server-shell + Client-view pattern.
Show me the diff.
```

Always ask for **the diff**, not the full file — it's easier to review incremental changes.

---

## 7. Collaboration & Git

**Frontend branch:** `feat/khalil-frontend`

### Rules

| Rule | Why |
|---|---|
| Only commit inside `plateforme-gestion-pfe/` | The parent `gradex/` folder and `backend/` are out of scope |
| Never touch backend files | Backend is on a teammate's branch; any change creates merge conflicts |
| Divide work **by page** | Each page is its own folder — two devs on different pages never touch the same files |
| `git pull` before starting a page | Avoids re-doing work a teammate already merged |
| `git push` after each page | Makes progress visible and reduces merge conflict risk |

### Typical workflow

```powershell
cd c:\Users\ibrah\Documents\gradex\plateforme-gestion-pfe
git pull origin feat/khalil-frontend

# … build the page …
npx tsc --noEmit    # must be zero errors

git add src/app/(app)/admin/subjects/page.tsx
git add src/app/(app)/admin/subjects/subjects-view.tsx
git commit -m "feat(admin): subjects moderation page"
git push origin feat/khalil-frontend
```

Do **not** use `git add .` or `git add -A` — risk of accidentally staging `.env.local` or other local files.

---

## 8. Testing

### Phase-based testing with `seed --phase`

Every interactive feature on the platform is phase-gated. To test a feature:

1. Re-seed with the appropriate phase:
   ```bash
   python manage.py seed --phase TEAM_FORMATION
   ```
2. Log in as the relevant demo account.
3. Test the feature — the campaign status will reflect the correct open phase.

### Demo accounts

See Section 2. All share password `Testpass123!`.

### Multi-user flows

For flows that require two simultaneous users (e.g., student inviting another student to a team, teacher reviewing a student's file):
- Open one browser window in normal mode (Student A)
- Open a second window in **private/incognito mode** (Student B or Teacher)
- Both sessions remain independent

### Pages that require `/admin/assignments` to exist first

These pages were built but **cannot be fully tested** until the Assignments admin page can produce real assignment results:

| Page | Blocked on |
|---|---|
| `/student/results` | Needs a completed assignment to show `GET /api/assignments/me/` data |
| `/student/results` appeal flow | Needs a completed assignment + RESULTS_AND_APPEALS phase |
| `/student/deliverables` upload | Needs team to be VALIDATED with an assigned subject + WORK_AND_SUPERVISION phase |
| `/teacher/supervision` | Needs teams to be assigned to the teacher as supervisor |

Build `/admin/assignments` first, then run the full end-to-end workflow test described in Sprint 3.
