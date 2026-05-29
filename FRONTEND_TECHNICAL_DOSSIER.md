# PFE Management Platform Frontend
## Technical Dossier — Next.js 16 App Router

Version date: 2026-05-29
Sister document: `PROJECT_TECHNICAL_DOSSIER.md` (backend, authoritative for API surface and domain rules).

This file is the **guide and blocknote** for frontend work. Whenever something is built, planned, or changed, it is recorded here so the dossier stays the single source of truth. The update log (§0) is the chronological view; §11 is the structural sprint plan.

---

## 0) Update Log

Newest entries on top.

### 2026-05-29 — Sprint Frontend-4 (Notifications) shipped
- **Notification bell in the Topbar** (`components/layout/notification-bell.tsx`) with unread-count badge (caps at `99+`). Clicking opens a Popover panel showing the latest 10 items with title, message, relative time, and a primary-coloured dot for unread. Clicking an item marks it read (optimistic), and if its `link_url` is non-empty, navigates there and closes the panel. "Mark all read" button in the header; "View all notifications →" link in the footer.
- **Polling hook** `hooks/use-unread-notifications.ts` — calls `GET /api/notifications/unread-count/` every 30s. Uses the **Page Visibility API**: stops polling when the tab is hidden, fetches immediately on visibility restore. Exposes `refresh()` (manual re-fetch) and `setUnreadCount(n)` (optimistic delta for mutation callers). Single-flight guard prevents overlapping requests if a poll fires during a manual refresh.
- **Full `/notifications` page** at `(app)/notifications/notifications-view.tsx`. Filter dropdown (`all` / `unread only`), `limit/offset` paged with a "Load more" button, mark-all-read in the page header (only when there are unread visible). Per-card `IMPORTANT` badge, inline "Mark read" button when the card has no `link_url` (otherwise the card click does it), `whitespace-pre-line` on the message so multi-line messages render.
- **Cross-role route allowance**: `(app)/layout.tsx`'s `isAllowed()` got a `SHARED_ROUTES = ['/notifications']` list checked before role-based gating. `middleware.ts` matcher extended with `/notifications` and `/notifications/:path*`.
- **New shadcn primitive**: `components/ui/popover.tsx` (~45 lines), following the existing dropdown-menu pattern. Reusable for future filter panels / info bubbles.
- **New types** in `lib/types.ts`: `Notification`, `NotificationType` (28-member union mirroring `apps/notifications/models.py`), `NotificationImportance`, `UnreadCountResponse`, `MarkAllReadResponse`.
- **Sprint 11 backend gotcha recorded**: `GET /api/notifications/` returns a **flat array**, NOT a paginated envelope. Uses `?limit=N&offset=N`. The dossier had this right in §7.13; logging it here so future-me doesn't trip.
- Backend untouched. TypeScript clean. Smoke test: `/notifications` returns 307 (middleware), all four notification endpoints return 401 — wiring confirmed.

### 2026-05-29 — Sprint Frontend-3 (Dashboards) shipped
- **Three new role-specific dashboard landing pages** wired to the existing backend `GET /api/dashboard/{admin|teacher|student}/` endpoints:
  - **`/admin`** — `admin-dashboard-view.tsx`. 6 status-breakdown stat cards (Teams, Assignments, Subjects, Appeals, Deliverables, Defenses), each with colour-tiered breakdown chips and drill-down links to the relevant admin page. Quick-actions bar at the bottom.
  - **`/teacher`** — `teacher-dashboard-view.tsx`. 4 big counter cards (supervised teams, pending reviews, defense requests, upcoming defenses) + two lists ("Latest pending reviews", "Upcoming defenses"). Each upcoming-defense item shows the user's role context (`Supervisor` / `Jury` / `Supervisor · Jury`). Same shell renders for `EXTERNAL_SUPERVISOR`.
  - **`/student`** — `student-dashboard-view.tsx`. Side-by-side team + subject cards (empty-state aware), conditional defense card with status + scheduled time + final grade + PV indicator, latest-5 deliverables list with review-status badges. Empty states route the user to the next logical action.
- **Default landing route changed** for every role: `app/page.tsx`, `(auth)/login/login-view.tsx`, and `(app)/layout.tsx` now redirect to `/admin`, `/teacher`, or `/student` instead of the first feature page (e.g. previously `/admin/users`).
- **Sidebar updated**: each role's nav has a new top "Dashboard" entry pointing at the role root. Added `exact?: boolean` to the `NavItem` type and used exact matching for dashboard entries so they don't stay highlighted when the user navigates into child pages like `/admin/users`.
- **New types in `lib/types.ts`**: `AdminDashboard`, `TeacherDashboard`, `StudentDashboard` plus 8 sub-types matching the backend response shapes from `apps/dashboard/services.py`.
- Backend untouched — Sprint 12 dashboard endpoints were already complete.
- TypeScript: `npx tsc --noEmit` clean.
- Smoke test: all three routes return 307 (auth middleware), backend endpoints return 401 — wiring confirmed.

### 2026-05-29 — Sprint Frontend-2 closed out
- **Backend addition** (driven by frontend need): `GET /api/admin/appeals/` list endpoint added in `apps/assignments/views.py` (`AdminAppealListView`) + URL registered in `admin_urls.py`. Supports `?status=PENDING|ACCEPTED|REJECTED&team_code=X` filters and the standard `page` / `page_size` pagination. Re-uses the existing `AppealSerializer`.
- **`/admin/teams`** — `ManageMembersDialog` added. Surfaces all active members; non-leaders get **Make Leader** (calls `POST /api/admin/teams/<code>/transfer-leadership/`) and **Remove** (calls `POST /api/admin/teams/<code>/remove-member/` via `ConfirmDialog`). To remove the leader, admin must first promote someone else — keeps the destructive flow explicit.
- **`/admin/assignments`** — placeholder "Appeals note" replaced with a real Appeals section: paginated list using new backend endpoint, status filter (defaults to PENDING), per-row **Accept** (ConfirmDialog) and **Reject** (Dialog with optional `admin_comment` textarea). `RejectAppealDialog` is a new local component.
- Sprint Frontend-2 is now ✅ DONE. All 13 MVP pages have view files and full action coverage.
- TypeScript: `npx tsc --noEmit` clean.

### 2026-05-29 — Sprint 1 auth verified end-to-end
- Granted `PlatformAccessGrant(SUPER_ADMIN)` to `imad@imad.com` (id=1) — fixed the underlying authorization gap behind the earlier "super admin login bounce" (the timing fix and the missing grant were two separate bugs).
- Verified: login + redirect, session restore on hard refresh, role-based route guards (admin bounced from `/student/*` and `/teacher/*`), logout (refresh token blacklisted, localStorage + cookie cleared).
- CORS confirmed live in the running container; `django-cors-headers 4.9.0` installed.

### 2026-05-26 — Initial dossier
- Merged from former `CLAUDE.md` and `ONBOARDING.md`, mirrors the backend dossier structure.
- Documented 10 fully-built pages + 3 placeholders + 6 missing-domain sprints.
- Recorded integration fixes (CORS, post-login race), known issues (MinIO public URLs, frontend not in docker-compose).

---

## 1) Architecture Decision

The frontend mirrors the backend's **hard-cut converged mode**. The runtime treats the same two orthogonal axes as authoritative:

1. **Business identity** (`User.business_identity`): `STUDENT`, `TEACHER`, `ADMINISTRATIVE_STAFF`, `EXTERNAL_SUPERVISOR`
2. **Platform privilege** (`PlatformAccessGrant.access_level`, surfaced as `User.platform_access_level`): `ADMIN`, `SUPER_ADMIN`

No legacy `global_role` fallback. Route gating, sidebar rendering, and inline action visibility all derive from these two fields plus `account_status`.

Implementation principles:
- **Server-shell + Client-view per page** — tokens live in browser memory, so every authenticated page is a Client Component.
- **No global state library** — React Context for auth + custom `useApi` hook for data fetching. No Redux/Zustand/SWR/React Query.
- **Phase-gating is server-side truth** — the frontend only renders intent. Every gated action consults `GET /api/campaign/current/` and surfaces a friendly notice when the relevant phase is closed; the final authority is the 400/403 from the backend.
- **JWT in two places** — access token in React memory only, refresh token in `localStorage`, plus a marker cookie `gradex_session=1` for middleware route protection.

---

## 2) Preserved Technical Backbone

- Next.js 16.2.3 (App Router, React Server Components, React Compiler enabled)
- React 19.2.4
- TypeScript 5 (strict mode)
- Tailwind CSS 4 (`@tailwindcss/postcss`)
- shadcn/ui + Radix UI primitives
- `lucide-react` for icons
- `react-hook-form` for form state
- `sonner` for toasts (provider mounted, light usage)
- `next-themes` (configured, light-only for now)
- Native `fetch` API — no Axios

`reactCompiler: true` is set in `next.config.ts`, so `useMemo`/`useCallback` are usually unnecessary for performance.

---

## 3) Repository Layout

```
plateform-gestion-pfe-esi/                  (repo root)
├── PROJECT_TECHNICAL_DOSSIER.md            backend dossier (authoritative)
├── FRONTEND_TECHNICAL_DOSSIER.md           this file
├── docker-compose.yml                      backend stack only — frontend not yet containerised
├── backend/                                Django backend
└── plateform-frontend/                     Next.js frontend (this dossier's subject)
    ├── src/
    │   ├── app/
    │   │   ├── layout.tsx                  Root layout — mounts AuthProvider
    │   │   ├── page.tsx                    Root: role-based redirect
    │   │   ├── globals.css                 All design tokens (colors, status, shadows, radius)
    │   │   ├── (auth)/                     Public pages: centred card, no sidebar
    │   │   │   ├── layout.tsx
    │   │   │   ├── login/
    │   │   │   └── forgot-password/        3-step: request OTP → verify → confirm
    │   │   └── (app)/                      Authenticated shell: sidebar + topbar
    │   │       ├── layout.tsx              Client-side auth guard + role-to-section enforcement
    │   │       ├── student/                team, subjects, results, deliverables
    │   │       ├── teacher/                subjects, supervision
    │   │       └── admin/                  users, academic-years, subjects, teams, assignments
    │   ├── components/
    │   │   ├── ui/                         shadcn primitives
    │   │   ├── layout/                     sidebar, topbar, page-header
    │   │   └── shared/                     data-table, status-badge, confirm-dialog, empty-state
    │   ├── lib/
    │   │   ├── api-client.ts               fetch wrapper: JWT attach + silent refresh
    │   │   ├── auth-context.tsx            AuthProvider + useAuth hook
    │   │   ├── types.ts                    TypeScript types matching backend response shapes
    │   │   └── utils.ts                    cn() helper
    │   ├── hooks/
    │   │   └── use-api.ts                  { data, isLoading, error, refetch }
    │   └── middleware.ts                   gradex_session cookie route protection
    ├── next.config.ts                      reactCompiler: true
    ├── package.json
    └── tsconfig.json
```

---

## 4) Routing & Permission Model

### Route groups

- **`(auth)/`** — public pages, centred-card layout, no auth check.
- **`(app)/`** — all authenticated pages. `(app)/layout.tsx` calls `useAuth()`, redirects unauthenticated users to `/login`, and bounces users away from sections they don't own.

### Role → section mapping

| User signal | Default landing | Allowed sections |
|---|---|---|
| `platform_access_level` set (`ADMIN` or `SUPER_ADMIN`) | `/admin/users` | `/admin/*` |
| `business_identity == STUDENT` | `/student/team` | `/student/*` |
| `business_identity == TEACHER` | `/teacher/subjects` | `/teacher/*` |
| `business_identity == EXTERNAL_SUPERVISOR` | `/teacher/supervision` | `/teacher/*` |
| `ADMINISTRATIVE_STAFF` without grant | `/admin/users` (then bounce) | none — see Convergence §9 |

### Two-tier route protection

1. **`src/middleware.ts`** — coarse cookie check. If `gradex_session` is missing on `/student/*`, `/teacher/*`, `/admin/*`, redirect to `/login?next=<path>`.
2. **`(app)/layout.tsx`** — fine-grained client-side check. Calls `isAllowed(user, pathname)`. If a refresh token exists in localStorage but `user` hasn't loaded yet, hold on `<LoadingShell />` instead of redirecting (avoids the post-login race).

### Token storage

| Token | Where | Why |
|---|---|---|
| Access JWT | React memory (`tokenRef.current` + state) | Never persisted; loss on reload triggers refresh |
| Refresh JWT | `localStorage["gradex_refresh"]` | Survives reload, used by `restoreSession()` |
| `gradex_session=1` cookie | Document cookie, `SameSite=Lax` | Marker only — middleware reads this to gate routes |

### SimpleJWT lifetimes (backend defaults)

| Token | Lifetime |
|---|---|
| Access | 15 minutes (`SIMPLE_JWT_ACCESS_MINUTES=15`) |
| Refresh | 7 days (`SIMPLE_JWT_REFRESH_DAYS=7`) |

### Silent refresh

`api-client.ts` attaches `Authorization: Bearer <access>` to every request. On a 401 it calls `POST /api/auth/refresh/`, updates the access token, retries the original request once. If refresh fails, `logout()` is called automatically and the user is redirected to `/login`. The frontend never prompts re-login on access expiry.

A **single-flight refresh promise** ensures concurrent 401s only fire one refresh call.

---

## 5) Architecture Conventions

### Server-shell + Client-view pattern (no exceptions)

```
src/app/(app)/admin/users/
├── page.tsx          → Server Component: exports metadata + wraps view in <Suspense>
└── users-view.tsx    → Client Component ('use client'): owns all data fetching and UI
```

`page.tsx` is always ~10 lines:
```tsx
import type { Metadata } from 'next'
import { Suspense } from 'react'
import { UsersView } from './users-view'

export const metadata: Metadata = { title: 'Users — GradeX' }

export default function AdminUsersPage() {
  return <Suspense><UsersView /></Suspense>
}
```

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

**Circular-import note**: `api-client.ts` does not import from `auth-context.tsx`. `AuthProvider` calls `registerAuth(callbacks)` on mount to wire token read/write. Don't change this.

### Auth context (`src/lib/auth-context.tsx`)

```typescript
const { user, isLoading, login, logout } = useAuth()

// user.business_identity: 'STUDENT' | 'TEACHER' | 'ADMINISTRATIVE_STAFF' | 'EXTERNAL_SUPERVISOR'
// user.platform_access_level: 'ADMIN' | 'SUPER_ADMIN' | null
// user.student_profile / user.teacher_profile: nested profile (nullable)
```

`useAuth()` throws if called outside `AuthProvider`. No need to redirect from views — `(app)/layout.tsx` does it.

### `useApi` hook (`src/hooks/use-api.ts`)

```typescript
const { data, isLoading, error, refetch } = useApi<PaginatedResponse<User>>(
  () => api.get('/api/admin/users/'),
  [],  // dependency array — re-fetches when these change
)
```

- `data` starts `null`, becomes the resolved value
- `error` is a string (extracted message) or `null`
- `refetch()` re-runs the fetcher without changing deps
- The fetcher is stored in a ref so it always uses the latest closure — safe to close over state in deps

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
  [page, search],
)
```

### Shared components

| Component | Path | Purpose |
|---|---|---|
| `DataTable<T>` | `components/shared/data-table.tsx` | Generic paginated table with page-size selector |
| `StatusBadge` | `components/shared/status-badge.tsx` | Maps backend status strings to four colour tiers |
| `ConfirmDialog` | `components/shared/confirm-dialog.tsx` | Destructive-action modal with inline `error` prop |
| `EmptyState` | `components/shared/empty-state.tsx` | Icon + title + description placeholder |
| `PageHeader` | `components/layout/page-header.tsx` | Title + description + optional action slot |
| `Sidebar` | `components/layout/sidebar.tsx` | Role-aware nav, reads user from AuthContext |
| `Topbar` | `components/layout/topbar.tsx` | User chip + logout button |

shadcn primitives installed in `components/ui/`: `avatar`, `badge`, `button`, `card`, `dialog`, `dropdown-menu`, `input`, `label`, `select`, `separator`, `skeleton`, `sonner`, `table`, `tabs`, `textarea`.

### Recurring per-page helpers

Every view file defines these locally (copy the pattern, don't share to avoid tight coupling):

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

// Loading skeleton
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

```typescript
const campaignApi = useApi<CampaignStatus>(() => api.get('/api/campaign/current/'), [])

const canUpload = campaignApi.data?.open_phases.includes('WORK_AND_SUPERVISION') ?? false
const canSubmitWishlist = campaignApi.data?.actions.can_submit_first_wishlist ?? false
```

Show a notice (not an error) when gating is the reason an action is unavailable. See `student/deliverables/deliverables-view.tsx` for the `UploadNotice` / `uploadBlockReason` pattern.

### Reference example

`src/app/(app)/admin/users/users-view.tsx` is the most complete example — paginated `DataTable`, debounced search + `Select` filter dropdowns, `DropdownMenu` per-row actions, create/edit `Dialog`, `ConfirmDialog` with inline error, super-admin conditional UI, grants map lookup. Read it before building any new admin page.

---

## 6) Style Guide — Institutional Blue (light mode only)

All tokens are CSS variables defined in `src/app/globals.css`.

### Colour palette

| Token | CSS variable | Hex | Usage |
|---|---|---|---|
| Primary | `--primary` | `#185FA5` | Buttons, links, active nav |
| Primary hover | — | `#0C447C` | Use `hover:brightness-90` on primary |
| Primary tint | `--secondary` / `--accent` | `#E6F1FB` | Ghost button bg, active nav item bg |
| Secondary blue | `--ring` | `#378ADD` | Focus rings |
| Text primary | `--foreground` | `#1E293B` | Body text, headings |
| Text muted | `--muted-foreground` | `#64748B` | Labels, captions, helper |
| Surface 1 | `--background` | `#F8FAFC` | Page background |
| Surface 2 | `--card` | `#FFFFFF` | Cards, modals, popovers |
| Border | `--border` | `#E2E8F0` | Dividers, input borders |

### Status colours (four tiers)

Each status has three tokens: `bg`, `fg`, `border`.

| Tier | bg / fg / border | Maps to backend values |
|---|---|---|
| Success | `--status-success-{bg\|fg\|border}` | `APPROVED`, `ACCEPTED`, `ACTIVE`, `VALIDATED` |
| Warning | `--status-warning-{bg\|fg\|border}` | `SUBMITTED`, `PENDING`, `LOCKED`, `FORMING` |
| Error | `--status-error-{bg\|fg\|border}` | `REJECTED`, `DISSOLVED`, `SUSPENDED`, `ARCHIVED` |
| Neutral | `--status-neutral-{bg\|fg\|border}` | `DRAFT`, `CLOSED`, `ENDED` |

Tailwind utilities: `bg-status-success-bg`, `text-status-success-fg`, `border-status-success-border`, etc.

### Typography

Font: **Inter** via `next/font/google`, variable `--font-sans`. No custom heading font.

| Element | Classes |
|---|---|
| h1 | `text-3xl font-bold tracking-tight` |
| h2 | `text-2xl font-semibold tracking-tight` |
| h3 | `text-xl font-semibold tracking-tight` |
| h4 | `text-lg font-semibold` |
| Body | `text-sm` (default) or `text-base` |
| Muted | `text-sm text-muted-foreground` |

### Other tokens

| Token | Value | Usage |
|---|---|---|
| `--radius` | `0.5rem` (8px) | Base border radius |
| `--shadow-card` | subtle 2-layer | Cards, list items |
| `--shadow-dropdown` | medium 2-layer | Dropdowns, tooltips |
| `--shadow-modal` | strong 2-layer | Dialogs, modals |

Tailwind shadow utilities: `shadow-card`, `shadow-dropdown`, `shadow-modal`.

---

## 7) API Integration Surface

Base path: `http://localhost:8000` (override with `NEXT_PUBLIC_API_URL`).
All list endpoints return `PaginatedResponse<T>` → `{ count, next, previous, results }`. Page params: `?page=2&page_size=25` (default 10, max 100).

Error shapes:

| Status | Shape |
|---|---|
| 400 | `{ "field_name": ["message"] }` |
| 401 | `{ "detail": "..." }` |
| 403 | `{ "detail": "You do not have permission to perform this action." }` |
| 404 | `{ "detail": "Not found." }` |

### 7.1 Auth — `/api/auth/`

| Method | Path | Auth |
|---|---|---|
| POST | `/api/auth/login/` | public |
| POST | `/api/auth/refresh/` | public |
| POST | `/api/auth/logout/` | authenticated |
| GET | `/api/auth/me/` | authenticated |
| POST | `/api/auth/change-password/` | authenticated |
| POST | `/api/auth/password-reset/request-otp/` | public |
| POST | `/api/auth/password-reset/resend-otp/` | public |
| POST | `/api/auth/password-reset/verify-otp/` | public |
| POST | `/api/auth/password-reset/confirm/` | public |
| POST | `/api/auth/identity-availability/` | ADMIN+ |

Login response:
```json
{
  "access": "<JWT>",
  "refresh": "<JWT>",
  "user": {
    "id": 1, "matricule": "...", "email": "...",
    "first_name": "...", "last_name": "...",
    "business_identity": "STUDENT|TEACHER|ADMINISTRATIVE_STAFF|EXTERNAL_SUPERVISOR",
    "account_status": "ACTIVE|SUSPENDED|ARCHIVED",
    "platform_access_level": "ADMIN|SUPER_ADMIN|null",
    "student_profile": { ... } | null,
    "teacher_profile": { ... } | null
  }
}
```

Password-reset flow in `DEBUG=1`: `request-otp` returns `"otp_debug": "123456"` in the response — no SMTP needed locally.

### 7.2 Academic Years — `/api/admin/academic-years/`

| Method | Path | Auth |
|---|---|---|
| GET | `/api/admin/academic-years/` (`?include_archived=true`) | ADMIN+ |
| POST | `/api/admin/academic-years/` | ADMIN+ |
| GET | `/api/admin/academic-years/<id>/` | ADMIN+ |
| PATCH | `/api/admin/academic-years/<id>/` (archived blocks) | ADMIN+ |
| POST | `/api/admin/academic-years/<id>/archive/` | ADMIN+ |

Fields: `id`, `year` (`"2024-2025"`), `year_label`, `start_date`, `end_date`, `status` (`ACTIVE|CLOSED|ARCHIVED`), `wishlist_size` (≥1), `created_at`, `updated_at`. Only one `ACTIVE` year at a time (DB constraint).

### 7.3 Campaign Phases — `/api/admin/campaign-phases/` + `/api/campaign/current/`

| Method | Path | Auth |
|---|---|---|
| GET | `/api/admin/campaign-phases/` (`?academic_year=1&phase_type=X`) | ADMIN+ |
| POST | `/api/admin/campaign-phases/` | ADMIN+ |
| GET | `/api/admin/campaign-phases/<id>/` | ADMIN+ |
| PATCH | `/api/admin/campaign-phases/<id>/` | ADMIN+ |
| POST | `/api/admin/campaign-phases/<id>/archive/` | ADMIN+ |
| GET | `/api/campaign/current/` | authenticated |

Phase enum: `CAMPAIGN_SETUP`, `SUBJECT_MANAGEMENT`, `TEAM_FORMATION`, `WISHLIST_1`, `ASSIGNMENT_REVIEW_1`, `RESULTS_AND_APPEALS`, `WISHLIST_2`, `ASSIGNMENT_REVIEW_2`, `WORK_AND_SUPERVISION`, `DEFENSE_WINDOW`, `ARCHIVE`.

`/api/campaign/current/` response:
```json
{
  "academic_year": { "id": 1, "label": "2024-2025", "status": "ACTIVE" } | null,
  "open_phases": ["WISHLIST_1"],
  "actions": {
    "can_manage_team": true, "can_submit_first_wishlist": true,
    "can_view_subject_catalog": true, "can_run_first_assignment": false,
    "can_view_assignment_result": false, "can_submit_appeal": false,
    "can_submit_second_wishlist": false
  }
}
```

### 7.4 Users — `/api/admin/users/`

| Method | Path | Auth |
|---|---|---|
| GET | `/api/admin/users/` (`?business_identity=X&account_status=Y`) | ADMIN+ |
| POST | `/api/admin/users/` | ADMIN+ |
| GET | `/api/admin/users/<id>/` | ADMIN+ |
| PATCH | `/api/admin/users/<id>/` | ADMIN+ |
| POST | `/api/admin/users/<id>/archive/` | ADMIN+ |

POST body: `matricule`, `email`, `first_name`, `last_name`, `business_identity`, `account_status`, `password`, optional nested `student_profile` or `teacher_profile`.

### 7.5 Platform Access Grants — `/api/admin/platform-access-grants/`

| Method | Path | Auth |
|---|---|---|
| GET | `/api/admin/platform-access-grants/` (`?is_active=true`) | ADMIN+ |
| GET / POST | `/api/super-admin/admins/` | SUPER_ADMIN |
| POST | `/api/super-admin/platform-access-grants/` | SUPER_ADMIN |
| POST | `/api/super-admin/platform-access-grants/<id>/revoke/` | SUPER_ADMIN |

Grant body: `{ "user": 2, "access_level": "ADMIN|SUPER_ADMIN" }`.

### 7.6 Subjects / Topics

**Teacher endpoints** (`TEACHER` or ADMIN+):

| Method | Path |
|---|---|
| GET / POST | `/api/teacher/subjects/` |
| GET / PATCH | `/api/teacher/subjects/<id>/` (only DRAFT or REJECTED) |
| POST | `/api/teacher/subjects/<id>/submit/` (DRAFT → SUBMITTED) |
| POST | `/api/teacher/subjects/<id>/resubmit/` (REJECTED → SUBMITTED) |

**Admin moderation** (ADMIN+):

| Method | Path |
|---|---|
| GET | `/api/admin/subjects/` (`?status=SUBMITTED&academic_year=1`) |
| GET | `/api/admin/subjects/<id>/` |
| POST | `/api/admin/subjects/<id>/approve/` |
| POST | `/api/admin/subjects/<id>/reject/` (`{ "reason": "..." }`) |
| POST | `/api/admin/subjects/<id>/archive/` |

**Public catalog** (authenticated):

| Method | Path |
|---|---|
| GET | `/api/subjects/` or `/api/subjects/catalog/` (phase-gated, team-size filtered) |
| GET | `/api/subjects/<id>/` |

Subject compatibility rule: team size ≤ 2 → any approved subject; team size > 2 → `STARTUP_PROJECT` only.

### 7.7 Teams

**Student-facing** (authenticated):

| Method | Path |
|---|---|
| GET | `/api/teams/me/` (auto-creates solo team) |
| POST | `/api/teams/<team_code>/invite/` (`{ student_id\|matricule\|email }`) |
| POST | `/api/team-invitations/<participation_id>/accept/` |
| POST | `/api/team-invitations/<participation_id>/reject/` |
| POST | `/api/teams/leave/` (leader must transfer first) |
| POST | `/api/teams/<team_code>/remove-member/` (leader only) |
| POST | `/api/teams/<team_code>/transfer-leadership/` |
| POST | `/api/teams/<team_code>/lock/` (FORMING → LOCKED) |

**Admin-facing** (ADMIN+):

| Method | Path |
|---|---|
| GET | `/api/admin/teams/` (`?academic_year=1&status=FORMING&search=name`) |
| GET | `/api/admin/teams/<team_code>/` |
| POST | `/api/admin/teams/<team_code>/remove-member/` |
| POST | `/api/admin/teams/<team_code>/transfer-leadership/` |
| POST | `/api/admin/teams/<team_code>/supervisors/` |
| POST | `/api/admin/teams/<team_code>/supervisors/remove/` |
| POST | `/api/admin/teams/<team_code>/dissolve/` |

Team status enum: `FORMING|LOCKED|VALIDATED|DISSOLVED|ARCHIVED`. Participation role: `LEADER|MEMBER|SUPERVISOR`. Participation status: `PENDING|ACTIVE|ENDED|REJECTED`.

### 7.8 Wishlists, Appeals, Assignments

| Method | Path | Auth |
|---|---|---|
| POST | `/api/wishlists/` | authenticated (leader) |
| GET | `/api/wishlists/me/` | authenticated |
| GET | `/api/admin/wishlists/` (`?selection_round=FIRST&status=SUBMITTED`) | ADMIN+ |
| GET | `/api/admin/wishlists/<wishlist_id>/` | ADMIN+ |
| POST | `/api/appeals/` (`{ "reason": "..." }`) | authenticated (leader) |
| GET | `/api/appeals/me/` (returns `{}` if none) | authenticated |
| GET | `/api/admin/appeals/` (`?status=PENDING&team_code=X`) — **added 2026-05-29** | ADMIN+ |
| POST | `/api/admin/appeals/<appeal_id>/accept/` | ADMIN+ |
| POST | `/api/admin/appeals/<appeal_id>/reject/` (`{ "admin_comment": "..." }`) | ADMIN+ |
| GET | `/api/assignments/me/` | authenticated (RESULTS_AND_APPEALS) |
| POST | `/api/admin/assignments/merit/` (`{ "selection_round": "FIRST" }`) | ADMIN+ |
| POST | `/api/admin/assignments/random/` (`{ "selection_round", "seed?": 123 }`) | ADMIN+ |
| POST | `/api/admin/assignments/manual/` (`{ "team_code", "subject_id" }`) | ADMIN+ |
| POST | `/api/admin/assignments/<team_code>/validate/` | ADMIN+ |

Wishlist POST: `{ "selection_round": "FIRST|SECOND", "items": [{ "subject_id": 1, "rank": 1 }, ...] }`.
Bulk assignment response: `{ "selection_round", "total_teams", "assigned_count", "unassigned_teams": [] }`.

### 7.9 Deliverable Files & Supervision

| Method | Path | Auth |
|---|---|---|
| GET | `/api/deliverable-files/me/` | authenticated (team member) |
| POST | `/api/deliverable-files/upload/` (multipart: `file`, `comment?`) | authenticated (LEADER/MEMBER) |
| GET | `/api/deliverable-files/<file_id>/` | authenticated |
| POST | `/api/deliverable-files/<file_id>/comments/` (`{ "text": "..." }`) | authenticated |
| POST | `/api/deliverable-files/<file_id>/review/` | authenticated (supervisor) |
| GET | `/api/supervision/teams/` | authenticated (supervisor) |
| GET | `/api/supervision/teams/<team_code>/files/` | authenticated (supervisor) |

Review body: `{ "review_status": "ACCEPTED|NEEDS_REVISION|REJECTED", "review_comment": "optional" }`.
Upload constraint: LEADER/MEMBER of a VALIDATED team with assigned subject during `WORK_AND_SUPERVISION`.

### 7.10 Defenses (Sprint 8 — not yet integrated in frontend)

**Student/team leader:**

| Method | Path |
|---|---|
| POST | `/api/defenses/request/` |
| GET | `/api/defenses/me/` |
| GET | `/api/defenses/<defense_id>/files/` |

**Supervisor:**

| Method | Path |
|---|---|
| GET | `/api/supervision/defense-requests/` |
| POST | `/api/defenses/<defense_id>/accept/` |
| POST | `/api/defenses/<defense_id>/deny/` |

**Jury:**

| Method | Path |
|---|---|
| GET | `/api/jury/defenses/` |
| GET | `/api/jury/defenses/<defense_id>/` |
| GET | `/api/jury/defenses/<defense_id>/files/` |
| POST | `/api/jury/defenses/<defense_id>/pv/` |

**Admin:**

| Method | Path |
|---|---|
| GET | `/api/admin/defenses/` |
| GET | `/api/admin/defenses/<defense_id>/` |
| POST | `/api/admin/defenses/<defense_id>/schedule/` |
| POST | `/api/admin/defenses/<defense_id>/reschedule/` |
| POST | `/api/admin/defenses/<defense_id>/jury/` |
| POST | `/api/admin/defenses/<defense_id>/files/` |
| POST | `/api/admin/defenses/<defense_id>/pv/` |

Status flow: `REQUESTED → READY_TO_SCHEDULE → SCHEDULED → COMPLETED` (or `CANCELLED` on any supervisor denial).
Jury roles: exactly one `PRESIDENT`, ≥1 `EXAMINER`, active supervisors auto-added as `GUEST`. Supervisors cannot be `PRESIDENT`.
PV: only `PRESIDENT` or platform admin can upload; required fields `final_grade` (0..20), `deliberation`, `pv_file`.

### 7.11 Academic Year Lifecycle (Sprint 9 — not yet integrated)

| Method | Path | Auth |
|---|---|---|
| GET | `/api/super-admin/academic-years/<id>/closure-readiness/` | SUPER_ADMIN |
| POST | `/api/super-admin/academic-years/<id>/close/` (`{ "confirm": true, "reason": "...", "force": false }`) | SUPER_ADMIN |
| POST | `/api/super-admin/academic-years/<id>/reopen/` | SUPER_ADMIN |
| POST | `/api/super-admin/academic-years/<id>/archive/` | SUPER_ADMIN |
| POST | `/api/super-admin/academic-years/<id>/close-and-archive/` | SUPER_ADMIN |
| GET | `/api/super-admin/academic-years/<id>/lifecycle-events/` | SUPER_ADMIN |

Transitions: `ACTIVE → CLOSED → ARCHIVED` (linear, with optional `CLOSED → ACTIVE` reopen). `ARCHIVED` is irreversible. Normal close blocks unresolved validated teams, defenses, and pending appeals; force close bypasses.

### 7.12 Reports & CSV Exports (Sprint 10 — not yet integrated)

| Method | Path | Format |
|---|---|---|
| GET | `/api/admin/reports/academic-years/<year_id>/defenses/` | JSON |
| GET | `/api/admin/reports/academic-years/<year_id>/defenses.csv` | CSV |
| GET | `/api/admin/reports/academic-years/<year_id>/team-assignments/` | JSON |
| GET | `/api/admin/reports/academic-years/<year_id>/team-assignments.csv` | CSV |
| GET | `/api/admin/reports/academic-years/<year_id>/student-results/` | JSON |
| GET | `/api/admin/reports/academic-years/<year_id>/student-results.csv` | CSV |
| GET | `/api/admin/reports/academic-years/<year_id>/jury-planning/` | JSON |
| GET | `/api/admin/reports/academic-years/<year_id>/jury-planning.csv` | CSV |

ADMIN+ only. Targets `ACTIVE`, `CLOSED`, and `ARCHIVED` years. CSV: `Content-Type: text/csv; charset=utf-8`, `Content-Disposition: attachment`, deterministic ordering, filename like `defenses_2025-2026.csv`.

### 7.13 Notifications (Sprint 11 — integrated 2026-05-29)

| Method | Path | Notes |
|---|---|---|
| GET | `/api/notifications/` (`?unread=true&limit=N&offset=N`) | **Flat array — NOT a paginated envelope.** Uses limit/offset, not page/page_size. |
| GET | `/api/notifications/unread-count/` | `{ "unread_count": N }` |
| POST | `/api/notifications/<notification_id>/read/` | Returns updated notification |
| POST | `/api/notifications/read-all/` | `{ "updated": N }` |

Notification importance: `NORMAL` (in-app only) or `IMPORTANT` (in-app + email via Celery — handled server-side, no frontend concern).
Notification types: **28** values covering team / subject / assignment / appeal / deliverable / defense / academic-year-lifecycle events. Full enum in `lib/types.ts` → `NotificationType`.

**Frontend integration**:
- Bell icon + Popover in the Topbar, visible on every authenticated page
- Polling 30s interval, paused while the tab is hidden (Page Visibility API)
- Full page at `/notifications` (cross-role — listed in `SHARED_ROUTES`)
- Optimistic UI for both single-mark-read and mark-all-read; bell count syncs via shared hook

### 7.14 Dashboards (Sprint 12 — integrated 2026-05-29)

| Method | Path | Auth |
|---|---|---|
| GET | `/api/dashboard/admin/` (`?academic_year_id=X`) | ADMIN+ |
| GET | `/api/dashboard/teacher/` | TEACHER, EXTERNAL_SUPERVISOR, ADMIN+ |
| GET | `/api/dashboard/student/` | STUDENT |

**Frontend routes:** `/admin`, `/teacher`, `/student` are the role landing pages. Sidebar puts "Dashboard" at the top of every nav.

**Response shapes** (exact, from `apps/dashboard/services.py` — types in `lib/types.ts`):

Admin: `{ academic_year, teams{total,forming,locked,validated,dissolved}, assignments{assigned,unassigned}, defenses{total,requested,ready_to_schedule,scheduled,completed,cancelled}, appeals{total,pending_or_submitted,accepted,rejected}, deliverables{total_files,pending_review,accepted,needs_revision,rejected}, subjects{total,draft,submitted,approved,assigned,rejected} }`

Teacher: `{ academic_year, supervision{supervised_teams_count,validated_supervised_teams_count}, deliverables{pending_review_count,latest_pending_review[]}, defenses{upcoming_count,pending_requests_count,upcoming[]} }`. Each upcoming defense includes `role_context: "SUPERVISOR" | "JURY" | "SUPERVISOR,JURY"`.

Student: `{ academic_year, team|null, subject|null, defense|null, deliverables{total_files,latest[]}, assignment{selection_round,assigned} }`. All major fields can be null pre-team-formation or pre-assignment — UI surfaces empty states routing the user to the next logical action.

### 7.15 Bulk Imports & Audit (Sprint 13 — not yet integrated)

| Method | Path | Auth |
|---|---|---|
| POST | `/api/admin/imports/users/preview/` (multipart) | ADMIN+ |
| POST | `/api/admin/imports/users/confirm/` (`{ "batch_id": N }`) | ADMIN+ |
| GET | `/api/admin/imports/users/template/?import_type=STUDENTS\|TEACHERS` | ADMIN+ |
| GET | `/api/super-admin/audit/admin-actions/` | SUPER_ADMIN |

CSV templates:
- Students: `matricule,email,first_name,last_name,moyenne_generale,specialite,academic_year`
- Teachers: `matricule,email,first_name,last_name,grade,departement`

Constraints: max 5 MB, max 1000 rows, UTF-8 with BOM, formula injection (`=`, `+`, `-`, `@`) rejected. XLSX supported only if `openpyxl` installed.
Imported users get a generated password + `must_reset_password=true` — login blocked until they reset via forgot-password.

### 7.16 Technical

| Method | Path | Auth |
|---|---|---|
| GET | `/api/health/` | public |
| GET | `/api/schema/` | public (OpenAPI JSON) |
| GET | `/api/docs/` | public (Swagger UI) |
| GET | `/admin/` | Django staff |

---

## 8) Integration Convergence Applied

Integration fixes applied during frontend ↔ backend wire-up:

### CORS configuration (applied)
- Added `django-cors-headers` to `backend/requirements.txt`
- Registered `corsheaders` in `INSTALLED_APPS`
- Inserted `corsheaders.middleware.CorsMiddleware` immediately after `SecurityMiddleware`
- Set `CORS_ALLOWED_ORIGINS=http://localhost:3000` (env-driven, comma-separated list)
- Set `CORS_ALLOW_CREDENTIALS = True`

### Post-login redirect race fix (applied)
- Symptom: super-admin logs in, sees 200 from `/api/auth/login/`, gets bounced back to `/login`
- Root cause: `(app)/layout.tsx` ran its auth-guard `useEffect` with stale `user = null` before React committed the `setUser()` update from `auth-context.tsx`
- Fix:
  - `auth-context.tsx`: write refresh token to localStorage **before** calling `setUser` (creates a synchronous signal independent of React's commit cycle)
  - `(app)/layout.tsx`: when `user === null && isLoading === false`, check `localStorage.getItem('gradex_refresh')` — if present, hold on `<LoadingShell />` instead of redirecting

### Known issues (not yet fixed)
1. **MinIO public URLs are unreachable from the browser**. `AWS_S3_ENDPOINT_URL` uses the Docker-internal hostname `minio:9000`, which the browser can't resolve. Files returned by the API as `http://minio:9000/pfe-media/...` break in `<img>` / `<a>` tags. Fix candidates: serve files through a Django proxy view, or split internal vs. public MinIO URLs in settings.
2. **Frontend not in `docker-compose.yml`**. `docker compose up -d` starts only the backend stack. Frontend has no `Dockerfile` and must be run with `npm run dev` separately.
3. **`API_BASE` declared in 5 files** (`api-client.ts`, `auth-context.tsx`, `forgot-password-view.tsx`, `deliverables-view.tsx`, `supervision-view.tsx`). Only the `api-client.ts` / `auth-context.tsx` instances are justified (circular-dep avoidance); the three view files can be cleaned up.
4. **No `.env.example` in frontend** — silent fallback to `http://localhost:8000` works for local dev but is undocumented.

---

## 9) Gotchas & Lessons Learned

### 1. All list endpoints return a paginated envelope
Always unwrap `.results`:
```typescript
const files = filesApi.data?.results ?? []     // correct
const files = filesApi.data ?? []              // wrong — crashes on .map()
```
The OpenAPI schema sometimes declares list endpoints as `type: array` while runtime returns the paginated envelope. **Trust the runtime.**

### 2. `GET /api/campaign/current/` shape is not flat
It's `{ academic_year, open_phases, actions }` — see §7.3. Use the `CampaignStatus` type from `types.ts`.

### 3. DRF serialises some numbers as strings
- `Subject.attachment_size_bytes`, `SupervisionTeam.files_count`, `SupervisionTeam.selected_subject_id`, `Wishlist.item_count`, `Team.annual_average` / `TeamSummary.annual_average` — all strings
- Use `Number(x)` when you need arithmetic; the types reflect this already.

### 4. Some FK fields are integer IDs, not nested objects
- `Team.assignment_validated_by` → `number | null`
- `Team.academic_year` → `number`
- `Wishlist.submitted_by`, `Appeal.submitted_by`, `Appeal.reviewed_by` → `number | null`
- `Subject.reviewed_by` in teacher view → `number | null` (admin view nests the object)

Don't render `.first_name` on these. Use `MemberSummary` (which has `first_name`, `last_name`) where the API does nest user data.

### 5. The live API is the truth
This dossier's API tables were derived from the backend dossier and integration testing. When in doubt, hit the actual endpoint or check `/api/schema/`. Fix this file after confirming.

### 6. Phase-gating depends on the open phase, not the user's role
Actions like "Upload Deliverable" or "Submit Wishlist" return 400/403 even for valid users if the wrong phase is open. The backend seed command's `--phase <PHASE>` flag controls this for local testing. Always check `/api/campaign/current/` first when something unexpectedly fails.

### 7. `GET /api/appeals/me/` returns `{}` when no appeal exists
Not `null`, not a 404 — an empty object. Guard with:
```typescript
const rawAppeal = appealsApi.data
const appeal = rawAppeal && 'appeal_id' in rawAppeal ? rawAppeal as Appeal : null
```

### 8. File URLs need prefixing in local dev
When `USE_S3=0` (Django filesystem), `file_url` is a relative path (`/media/...`). When `USE_S3=1` (MinIO), it's absolute but uses the Docker-internal hostname (see Known Issue §8). Helper:
```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
const fullUrl = path.startsWith('http') ? path : `${API_BASE}${path}`
```

---

## 10) Where We Are Arriving — Current Snapshot

**Backend completeness:** 100% of dossier scope (Sprints 1–13 merged and tested) + one new admin endpoint added by the frontend (see Update Log 2026-05-29).
**Frontend completeness:** Sprints 1–7 + Sprint 11 notifications + Sprint 12 dashboards integrated. **17 pages live** (13 MVP + 3 dashboards + 1 notifications page) + bell in the topbar everywhere. Sprints 8, 9, 10, 13 not yet integrated.

### Pages built — fully implemented (17)

| Route | Backend domain | Status |
|---|---|---|
| `/login` | Sprint 1 — Accounts | ✅ Verified end-to-end (auth audit 2026-05-29) |
| `/forgot-password` | Sprint 1 — OTP flow | ✅ Tested |
| `/notifications` | Sprint 11 — Notifications | ✅ Built 2026-05-29 — filter, load-more, mark-read, mark-all-read |
| `/admin` | Sprint 12 — Admin dashboard | ✅ Built 2026-05-29 — stat cards + quick actions |
| `/admin/users` | Sprint 1 + super-admin grants | ✅ Tested |
| `/admin/academic-years` | Sprints 2 + 3 — Years + Phases | ✅ Tested |
| `/admin/subjects` | Sprint 4 — Moderation | ✅ list/filter, approve, reject with reason, archive |
| `/admin/teams` | Sprint 5 — Admin team mgmt | ✅ list, detail, manage members (promote + remove), manage supervisors, dissolve |
| `/admin/assignments` | Sprint 6 — Assign + Appeals | ✅ run merit/random/manual, validate, wishlists list, appeals list + accept/reject |
| `/teacher` | Sprint 12 — Teacher dashboard | ✅ Built 2026-05-29 — counters + pending reviews + upcoming defenses |
| `/teacher/subjects` | Sprint 4 — Topic proposals | ✅ Tested |
| `/teacher/supervision` | Sprint 7 — Supervision | 🟡 Smoke-tested (full E2E unblocked) |
| `/student` | Sprint 12 — Student dashboard | ✅ Built 2026-05-29 — team + subject + defense + deliverables |
| `/student/team` | Sprint 5 — Teams | ✅ Tested |
| `/student/subjects` | Sprint 4 catalogue + Sprint 6 wishlist | ✅ Tested |
| `/student/results` | Sprint 6 — Assignment + Appeal | 🟡 Smoke-tested (full E2E unblocked) |
| `/student/deliverables` | Sprint 7 — Deliverables | 🟡 Smoke-tested (full E2E unblocked) |

Plus the **notification bell** in the Topbar on every authenticated page — polls unread count every 30s. Default landing page per role is the dashboard. E2E build-up test sequence is documented in §13.

### Backend domains with zero frontend coverage

| Backend Sprint | Domain | Endpoints | Frontend gap |
|---|---|---|---|
| Sprint 8 | Defenses | 17 | Student request, supervisor accept/deny, admin schedule + jury + PV, jury view |
| Sprint 9 | Year Lifecycle | 6 | Super-admin close / reopen / archive UI + lifecycle event timeline |
| Sprint 10 | Reports & CSV | 8 | Admin report dashboards + CSV download buttons |
| Sprint 11 | Notifications | 5 | Bell icon, polling, list/read/mark-all UI |
| Sprint 12 | Dashboards | 3 | Role-specific dashboard landing pages |
| Sprint 13 | Bulk Imports + Audit | 5 | CSV/XLSX upload preview + confirm, audit log viewer |

### Integration health

- ✅ CORS configured
- ✅ Auth + silent JWT refresh working
- ✅ Post-login race fixed
- ❌ MinIO public URL still broken — blocks file display anywhere `USE_S3=1`
- ❌ Frontend not containerised — must be run separately from `docker compose up -d`

---

## 11) Sprint Frontend Plan

Frontend sprints are numbered separately from backend sprints. Each one corresponds to a coherent chunk of backend domain the frontend doesn't yet expose.

### Sprint Frontend-1 — Foundation & MVP Pages ✅ DONE

Scope delivered:
- `lib/types.ts`, `lib/api-client.ts` (silent refresh + circular-dep workaround), `lib/auth-context.tsx` (with localStorage guard against post-login race)
- `middleware.ts` cookie protection + `(app)/layout.tsx` role guard
- `hooks/use-api.ts`
- All design tokens in `globals.css` (Institutional Blue palette)
- Auth pages (login, 3-step forgot-password)
- App shell (sidebar, topbar, page-header)
- Shared components (DataTable, StatusBadge, ConfirmDialog, EmptyState)
- 10 of 13 MVP pages (see snapshot in §10)

### Sprint Frontend-2 — Finish MVP Admin Pages ✅ DONE (2026-05-29)

All three previously-placeholder admin views are now fully implemented.

**`/admin/subjects` — Subject Moderation** ✅
- List + filters (status, academic year, proposer)
- Approve, reject (with reason dialog), archive
- Respects `SUBJECT_MANAGEMENT` phase gating

**`/admin/teams` — Teams Management** ✅
- List with filters (status, academic year, search) + detail dialog (leader + members + supervisors + invitations)
- `ManageMembersDialog`: per-row **Make Leader** (`transfer-leadership`) and **Remove** (`remove-member` via ConfirmDialog). Leader cannot be removed directly — must promote someone else first
- `ManageSupervisorsDialog`: add (from active TEACHER/EXTERNAL_SUPERVISOR users) and remove
- Dissolve team (destructive ConfirmDialog)

**`/admin/assignments` — Assignment Running + Appeals** ✅
- Run merit / random / manual assignments with `BulkResultCard` / `ManualResultCard` result displays
- Per-team validate by team code
- Wishlists list with status + round filters, drill-down planned for later
- Appeals list (paginated, status filter, defaults to PENDING) — per-row **Accept** (ConfirmDialog) and **Reject** (`RejectAppealDialog` with optional `admin_comment` textarea)

**Backend side-effect:** `GET /api/admin/appeals/` was missing. Added `AdminAppealListView` in `apps/assignments/views.py` + URL in `admin_urls.py`. Uses existing `AppealSerializer`. Supports `?status=` and `?team_code=` filters.

### Sprint Frontend-3 — Dashboards ✅ DONE (2026-05-29)

Three role-specific dashboard landing pages wired to `GET /api/dashboard/{admin|teacher|student}/`. Default landing route per role now points at the dashboard. Sidebar "Dashboard" entry at the top of every nav.

Shipped:
- **`/admin`** — 6 status-breakdown stat cards (Teams, Assignments, Subjects, Appeals, Deliverables, Defenses) with colour-tiered breakdown chips + quick-action buttons to drill into the relevant admin page
- **`/teacher`** — 4 counter cards + "Latest pending reviews" list + "Upcoming defenses" list with role-context badges (Supervisor / Jury / Supervisor · Jury). Reused for `EXTERNAL_SUPERVISOR`.
- **`/student`** — Team + Subject side-by-side cards (empty-state aware), conditional defense card, latest-5 deliverables list with review-status badges

Deferred to a polish pass:
- Academic year selector on the admin dashboard (backend already accepts `?academic_year_id=`)
- A "Refresh" action and last-fetched timestamp
- Subtle micro-animations on stat counters

### Sprint Frontend-4 — Notifications ✅ DONE (2026-05-29)

Shipped:
- **Bell + Popover in Topbar** — unread-count badge (caps at `99+`), latest 10 items, click to mark read + navigate (when `link_url` is set), "Mark all read" header button, "View all →" footer link.
- **Polling hook** `useUnreadNotifications` — 30s interval, paused while tab is hidden (Page Visibility API), single-flight guard, exposes `refresh()` and `setUnreadCount()` for optimistic updates.
- **Full page** at `/notifications` — filter (all / unread), `Load more` with limit/offset pagination (`PAGE_SIZE=20`), `IMPORTANT` badge per item, multi-line message rendering, inline mark-read button when no `link_url`.
- **Cross-role gating** — `SHARED_ROUTES` allowlist in `(app)/layout.tsx`, middleware matcher extended.
- **Reusable popover primitive** — `components/ui/popover.tsx`.

Deferred to a polish pass:
- Type-aware icons per notification type (currently uses the generic Bell)
- Browser notification API integration for important events
- "X new since last visit" indicator when re-opening the panel

### Sprint Frontend-5 — Defenses Workflow (Sprint 8 backend)

The biggest single chunk. Touches four roles:

- **Student** (`/student/defense`): request defense (select files from existing deliverables or upload new), view my defense status, view attached files
- **Supervisor** (`/teacher/defense-requests`): list pending requests for teams I supervise, accept or deny each
- **Admin** (`/admin/defenses`): list all defenses by status, schedule + reschedule + assign jury (1 PRESIDENT, ≥1 EXAMINER), edit attached files, upload PV
- **Jury** (`/jury/defenses`): list defenses I'm assigned to, view files, upload PV (if PRESIDENT)

Status transitions visualised inline. PV upload form: `final_grade` (0..20), `deliberation` (textarea), `pv_file` (PDF upload). Phase gating: all actions require `DEFENSE_WINDOW`.

### Sprint Frontend-6 — Lifecycle, Reports, Imports, Audit

Batched because all four share the same admin/super-admin patterns — sidebar entries under a single "Administration" or "Operations" section.

- **Year Lifecycle** (`/admin/lifecycle`, SUPER_ADMIN only): closure readiness check → close (normal/force) → reopen → archive. Lifecycle event timeline per year.
- **Reports** (`/admin/reports`): four report previews (JSON in `DataTable`) with "Download CSV" buttons.
- **Bulk Imports** (`/admin/imports`): file upload → preview table with row-level errors → "Confirm" button. Template download links.
- **Audit Log** (`/admin/audit`, SUPER_ADMIN only): paginated `DataTable` with filter by action type + actor + date range.

### Sprint Frontend-7 — Hardening & Polish

Buffer sprint:
- Fix MinIO public URL (settings or proxy view)
- Containerise frontend, add to `docker-compose.yml`
- Consolidate the 5 `API_BASE` declarations
- Add `.env.example` for the frontend
- UI consistency pass: every page matches Style Guide
- `npm run build` produces zero warnings/errors
- Demo / soutenance scenario walkthrough

---

## 12) Out-of-Scope (Frontend)

Mirrors the backend dossier's out-of-scope list:
- **Push notifications / WebSockets** — polling only for notifications
- **Notification preferences** — backend doesn't expose them
- **PDF/Excel exports** — backend ships CSV only
- **Persistent dashboards / saved filters** — backend computes on demand
- **Frontend feature flags** — no LaunchDarkly / GrowthBook integration

What's intentionally not implemented inside frontend (independent of backend):
- Dark mode (`next-themes` configured but unused)
- i18n / multi-language
- Offline support / service workers
- Storybook for shared components

---

## 13) Test Status

The frontend has no automated test suite at this time. Quality gates are:

1. **TypeScript:** `npx tsc --noEmit` must be zero errors.
2. **Lint:** `npm run lint` (Next.js ESLint config).
3. **Manual phase-based E2E:** re-seed the backend with `python manage.py seed --phase <PHASE>` for the relevant feature, log in as the matching demo account, exercise the happy path + at least one error path.
4. **Production build:** `npm run build` must produce zero errors before demo.

All MVP pages are testable end-to-end as of 2026-05-29:

| Page | Status |
|---|---|
| `/student/results` (view + submit appeal) | ✅ Fully testable — admin can produce assignments and review appeals |
| `/student/deliverables` upload | ✅ Testable — needs `WORK_AND_SUPERVISION` phase open |
| `/teacher/supervision` | ✅ Testable — subject's proposer is auto-added as supervisor on assignment |

Recommended end-to-end happy-path sequence (run after seeding fresh data):
1. Admin creates `AcademicYear` (ACTIVE, wishlist_size=5)
2. Admin creates phases: `SUBJECT_MANAGEMENT`, `TEAM_FORMATION`, `WISHLIST_1`, `ASSIGNMENT_REVIEW_1`, `RESULTS_AND_APPEALS`, `WORK_AND_SUPERVISION`
3. Admin creates 1 teacher + 3-4 students (link to the academic year)
4. Teacher proposes 2-3 subjects → submits
5. Admin approves the subjects on `/admin/subjects`
6. Students log in → form a team → submit wishlist
7. Admin runs merit assignment → validates → student sees result
8. Student submits an appeal → admin reviews on `/admin/assignments` Appeals section
9. Student uploads a deliverable → teacher reviews on `/teacher/supervision`

Future testing additions (Sprint Frontend-7 candidate): Playwright smoke flow covering login → student team formation → wishlist → admin assignment → results visibility.

---

## 14) Working Style — How To Continue This Project

This section is the **operating manual for the next collaborator** (human or agent). It records how the recent work was actually done so the rhythm stays consistent. The conventions in §5 say *what* the code looks like; this section says *how to arrive at it*.

If you only read one section before contributing, read this one.

### 14.1 The "read the truth" loop

**Never guess at API shapes. Read the backend.**

The dossier is correct but a snapshot — when a discrepancy turns up, the backend code wins, then you fix the dossier. The sequence that has worked repeatedly:

1. **Open the backend `urls.py`** for the relevant app (`backend/apps/<app>/urls.py` or `admin_urls.py` or `super_admin_urls.py`). It tells you what paths exist and which view class handles each.
2. **Open the view class.** It tells you the request body, the permission class, the response serializer, the query params it honours.
3. **Open the serializer.** It tells you the exact field names, the read-only fields, the source mappings (some fields like `moyenne_generale` are aliases for `annual_average`).
4. **Open the model when types are ambiguous.** Numeric fields serialized by DRF often come back as strings (`Subject.attachment_size_bytes`, `Wishlist.item_count`, `Team.annual_average`). FK fields embedded via `serializers.IntegerField` come back as plain numbers, not nested objects. Both quirks live in `types.ts`; replicate them when you add new endpoints.
5. **Verify with curl** before assuming anything. `curl -s -H "Origin: http://localhost:3000" http://localhost:8000/api/<endpoint>/ | python3 -m json.tool` works without auth for unauthenticated endpoints; for authenticated ones, do it once with a real bearer token and copy the shape into types.ts.

**Anti-pattern**: copying API shapes from this dossier without verifying. The dossier drifts when new endpoints land. Treat it as documentation, not as a contract.

### 14.2 Definition of done for a sprint

A frontend sprint is **done** when:

- The feature is wired end-to-end in code (views + types + redirects + sidebar/topbar entries)
- `npx tsc --noEmit` is **zero errors** (not a warning either)
- HTTP smoke test passes: unauthenticated routes return 307 (middleware), backend endpoints return 401 (auth required). The wiring is then known-good even before fixtures exist.
- The dossier §0 Update Log has a new entry, the relevant §7.x is marked "integrated", and §10/§11 are updated.

A sprint is **not** done when:
- "It compiles" but no smoke test was run
- The user has to manually find the test path
- A backend dependency was assumed (like "the appeal list endpoint exists") without grepping `urls.py`

**Full E2E testing is deferred** until the build-up data exists (see §13). Don't block sprint completion on it — the user has explicitly chosen to ship implementation first, test after. If you discover a real bug in the smoke test (not a missing-data 400), fix it before claiming done.

### 14.3 When to touch the backend

The user owns both sides of the repo (branch `imad-backend`). Backend changes are fair game **only when the frontend genuinely cannot ship the feature otherwise**.

Threshold: the backend is missing an endpoint or response field that no workaround can replace. Example precedent — `GET /api/admin/appeals/` (2026-05-29). The frontend needed a list of pending appeals; the only existing endpoints were per-appeal accept/reject. The fix was a new `AdminAppealListView` mirroring the existing wishlists pattern. Eight lines of Python.

**Not a backend job:**
- Cosmetic response shape changes ("I wish this field was a number not a string") — the frontend converts.
- New filter params when the existing endpoint can be filtered client-side.
- "Convenience" composite endpoints that the frontend can assemble from existing ones.
- Anything that touches business rules — those belong on the backend independently.

When you do touch the backend:
- Match the existing patterns exactly (`AdminAppealListView` mirrors `AdminWishListListView`; same `select_related`, same pagination class, same `?status=` / `?team_code=` filters).
- Reuse the existing serializer when its shape fits — don't add a new `AppealListItem` next to `AppealSerializer` if the existing one already serves.
- Record the addition in the dossier §0 update log with the date marker `**added 2026-05-29**` so the next reader knows it's frontend-driven.

### 14.4 The sprint workflow that worked

For each sprint chunk (e.g. Sprint Frontend-3 Dashboards, Sprint Frontend-4 Notifications), the pattern was:

1. **TodoWrite first.** Lay out the discrete steps before any code. One `in_progress` at a time. Mark `completed` immediately after each step — don't batch.
2. **Read the backend.** Open `urls.py`, `views.py`, `services.py`, `serializers.py`, `models.py` for the relevant app. Note exact response shapes.
3. **Add types.** New types go into `lib/types.ts` in their dedicated `// ─── X ───` section, near the related backend domain. Include a comment when a type has a non-obvious quirk (e.g. "GET /api/notifications/ returns a flat array, NOT a paginated envelope").
4. **Add primitives if needed.** A new shadcn primitive (like the Popover added for the notification bell) follows the existing dropdown-menu pattern: ~30-50 lines, Radix umbrella import, data-slot attributes.
5. **Build the view files.** Server-shell + Client-view per page, no exceptions. Copy the recurring helpers (`extractMessage`, `InlineError`, `LoadingSkeleton`) into each new view; don't centralize them.
6. **Wire it in.** Sidebar nav entry, default route, layout guard, middleware matcher — every cross-cutting change in the same chunk so the feature is whole.
7. **Type-check.** `cd plateform-frontend && npx tsc --noEmit`. Zero is the bar.
8. **Smoke test.** `curl` the new route on `:3000` (expect 307) and the backend endpoint on `:8000` (expect 401). Both confirm wiring without needing fixtures.
9. **Update the dossier.** §0 update log entry, §7.x marked integrated, §10/§11 updated. The dossier is the blocknote — every shipped chunk gets a line.
10. **Mark all todos completed.** Then give the user a tight recap: files touched, design highlights, quality gate, what's next.

### 14.5 Code conventions to keep

The dossier §5 says what these are; here is how to apply them under pressure:

- **Reference implementations** — when in doubt about a pattern, copy from a known-good page:
  - Admin CRUD with filters → `admin/users/users-view.tsx`
  - Multi-section page with internal navigation → `admin/assignments/assignments-view.tsx`
  - Dialog-driven mutations with inline errors → any of the manage-* dialogs in `admin/teams/teams-view.tsx`
  - Read-only dashboard with stat cards → `admin/admin-dashboard-view.tsx`
  - Polling + page visibility → `hooks/use-unread-notifications.ts`
- **Three lines is better than premature abstraction.** `extractMessage` is duplicated in every view file on purpose. Centralising it would create a tight coupling between unrelated pages — when one page's error story diverges, you'd have to either add config or fork the helper anyway. Three lines, six files, zero coupling.
- **Don't add backwards-compatibility shims.** If you rename a field or restructure types, update every call site in the same edit. No `// removed for X` comments. No deprecated aliases.
- **Don't add defensive validation past the boundary.** Trust `useApi` to return either `data` or `error` — don't null-check `data` after `error` is null. Trust `useAuth()` to never return null inside `(app)/*` — the layout guard already enforces it.
- **No comments that re-describe the code.** A comment is for the *why*, not the *what*. The codebase has a handful of multi-line comments — each one names a constraint that wouldn't be obvious from the code (race condition, circular-import workaround, etc.). Follow that template, don't expand on it.

### 14.6 Things you should NOT do

These are the anti-patterns. Each has a specific reason behind it.

- **Don't add features the user didn't ask for.** If they say "build the appeals UI", build the appeals UI — not the appeals UI plus a new academic-year picker plus a tooltip system. Scope creep silently extends every sprint and makes diffs un-reviewable.
- **Don't run full E2E tests unprompted.** The user has explicitly opted to ship implementation first and test in batch. Smoke tests at HTTP level are part of "done"; full happy-path walkthroughs are not.
- **Don't run destructive shell commands without confirmation.** No `rm -rf` on data, no `git reset --hard`, no `git push --force`, no `docker compose down -v`. Read-only `docker compose exec … python manage.py shell -c "…"` queries are fine.
- **Don't ask "should I proceed?" on each small step.** If the work is in scope, just do it. Reserve confirmation for true decisions: backend changes, scope expansions, anything destructive.
- **Don't write summary or planning markdown files** unless asked. The dossier is the single source of truth; everything else clutters.
- **Don't use emojis in code or in committed text.** The dossier uses ✅ / ⚠️ / ⏳ / 🟡 as state markers in the snapshot table and update log — that's the only place. Not in new file content, not in code comments, not in commit messages.
- **Don't fix one problem by introducing another.** The post-login bounce was *two* bugs (React commit race + missing PlatformAccessGrant). The right fix was to address both, not to add a `setTimeout` to mask the race. Root cause every time.

### 14.7 The dossier is a blocknote — keep it current

This file is the project's working memory. Every meaningful change leaves a trace.

Format for §0 entries:

```
### YYYY-MM-DD — Brief title of what landed
- Bullet with what was shipped, including specific file paths and class/function names
- Bullet for the *why* if it's non-obvious (e.g. "Backend addition because the frontend cannot otherwise…")
- Bullet for deferred polish — items the next sprint can pick up
- Closing line: TypeScript status + smoke test results
```

When the entry describes a backend addition driven by frontend need, mark it inside the §7.x table too with `**added YYYY-MM-DD**` so the next reader sees the provenance without scrolling.

When a sprint completes, also:
- Move its status in §11 from ⏳/🟡 to ✅ DONE with a date
- Update the page count in §10 ("13 of 13 MVP pages" → "17 pages live", etc.)
- Move any unfinished sub-items to a "Deferred to a polish pass" bullet so they're tracked without bloating the active sprint

When a backend section is no longer "not yet integrated", change its header marker accordingly:

```
### 7.14 Dashboards (Sprint 12 — not yet integrated)
                                       ↓
### 7.14 Dashboards (Sprint 12 — integrated 2026-05-29)
```

### 14.8 Reading the user's signals

The user is leading; you are executing. Pay attention to what they ask for *between the lines*.

- **"Analyse deep, implement, then test"** — they want the full sequence in one go, not pause-to-confirm at every step.
- **"Leave tests for later"** — full E2E is out of scope for this sprint, smoke testing only.
- **"Make it a guide and bloknote"** — the dossier is for them to read between sessions; structure it for skim-reading (clear headings, tables, code fences).
- **"Sprint X is done, move to Y"** — accept their definition of done; don't relitigate.
- **A screenshot of a 400 error** — they want to know *why*, not necessarily a fix yet. Diagnose first, propose options, let them pick.
- **A specific bug report** ("super admin redirects to login") — root cause it across both halves of the stack (frontend race + backend grant gap) before patching anything.

When uncertain about scope between two reasonable interpretations, pick the smaller one and proceed. If you got it wrong, the user will redirect; if you got it right, you've saved a round trip.

### 14.9 Communication after work

At the end of each meaningful piece of work, send a tight recap. The shape that has worked:

1. **What Was Built** — file table (path / lines / purpose), one row per file touched
2. **Design highlights** — 3-5 bullets on the non-obvious choices (e.g. "polling pauses while tab hidden", "leader has no remove button — admin must promote first")
3. **Wiring fixes** — anything cross-cutting (sidebar, layout guard, middleware, redirects)
4. **Documentation updates** — dossier sections touched
5. **Quality Gate** — TS errors, smoke test results, anything else verified
6. **Next move** — one sentence proposing the next sprint per the plan, with a single-question check-in

Not a narrative. Not a step-by-step replay. The user already saw the tool calls. Tell them what *changed* and what *happens next*.

### 14.10 Quick reminders

- The repo root is `plateform-gestion-pfe-esi/`. The frontend lives in `plateform-frontend/` (note the spelling — there is no second `e` in "plateform"). The backend lives in `backend/`. The dossier this section appears in lives at `plateform-frontend/FRONTEND_TECHNICAL_DOSSIER.md`; its sister is `PROJECT_TECHNICAL_DOSSIER.md` at the repo root.
- Current working branch is `imad-backend`. The user owns both sides of the stack.
- The dev server runs on `:3000`. The backend Django dev server runs on `:8000` inside `docker compose` (services: `web`, `worker`, `db`, `redis`, `minio`, `minio-init`). CORS is configured for `http://localhost:3000` only.
- When the user asks you to "test", default to **HTTP smoke** unless they explicitly say "full end-to-end" or "click through the UI". The smoke is fast and catches wiring bugs; the full walkthrough requires fixture data.
- When you finish a sprint, the next sprint is named in §11. Propose it as a single question rather than jumping in — the user may have a different priority that day.
