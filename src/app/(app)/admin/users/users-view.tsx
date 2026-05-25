'use client'

import { useEffect, useState } from 'react'
import {
  AlertCircle,
  Loader2,
  MoreHorizontal,
  Plus,
  Search,
  Shield,
  ShieldOff,
  Users,
} from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { api, ApiClientError } from '@/lib/api-client'
import { useApi } from '@/hooks/use-api'
import type {
  AccountStatus,
  BusinessIdentity,
  PaginatedResponse,
  PlatformAccessGrant,
  User,
} from '@/lib/types'
import { DataTable, type Column } from '@/components/shared/data-table'
import { StatusBadge } from '@/components/shared/status-badge'
import { ConfirmDialog } from '@/components/shared/confirm-dialog'
import { EmptyState } from '@/components/shared/empty-state'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

// ─── Constants ────────────────────────────────────────────────────────────────

const ROLE_LABELS: Record<BusinessIdentity, string> = {
  STUDENT: 'Student',
  TEACHER: 'Teacher',
  ADMINISTRATIVE_STAFF: 'Admin Staff',
  EXTERNAL_SUPERVISOR: 'Ext. Supervisor',
}

const ROLE_CLASSES: Record<BusinessIdentity, string> = {
  STUDENT: 'bg-primary/10 text-primary border-primary/20',
  TEACHER: 'bg-violet-50 text-violet-700 border-violet-200',
  ADMINISTRATIVE_STAFF: 'bg-amber-50 text-amber-700 border-amber-200',
  EXTERNAL_SUPERVISOR: 'bg-teal-50 text-teal-700 border-teal-200',
}

// ─── Types ────────────────────────────────────────────────────────────────────

interface UserFormState {
  matricule: string
  email: string
  first_name: string
  last_name: string
  password: string
  business_identity: BusinessIdentity | ''
  account_status: AccountStatus | ''
  // Student profile
  academic_year: string
  annual_average: string
  speciality: string
  // Teacher / supervisor profile
  grade: string
  department: string
}

const EMPTY_FORM: UserFormState = {
  matricule: '',
  email: '',
  first_name: '',
  last_name: '',
  password: '',
  business_identity: '',
  account_status: 'ACTIVE',
  academic_year: '',
  annual_average: '',
  speciality: '',
  grade: '',
  department: '',
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function userToForm(u: User): UserFormState {
  const sp = u.student_profile
  const tp = u.teacher_profile
  return {
    matricule: u.matricule,
    email: u.email,
    first_name: u.first_name,
    last_name: u.last_name,
    password: '',
    business_identity: u.business_identity,
    account_status: u.account_status,
    academic_year: sp?.academic_year != null ? String(sp.academic_year) : '',
    annual_average: sp?.annual_average ?? '',
    speciality: sp?.speciality ?? sp?.specialite ?? '',
    grade: tp?.grade ?? '',
    department: tp?.department ?? tp?.departement ?? '',
  }
}

function buildUserBody(form: UserFormState, isEdit = false): Record<string, unknown> {
  const body: Record<string, unknown> = {
    matricule: form.matricule,
    email: form.email,
    first_name: form.first_name,
    last_name: form.last_name,
    business_identity: form.business_identity,
    account_status: form.account_status,
  }
  if (!isEdit || form.password) body.password = form.password
  if (form.business_identity === 'STUDENT') {
    body.student_profile = {
      academic_year: form.academic_year ? Number(form.academic_year) : null,
      annual_average: form.annual_average || null,
      speciality: form.speciality || null,
    }
  }
  if (
    form.business_identity === 'TEACHER' ||
    form.business_identity === 'EXTERNAL_SUPERVISOR'
  ) {
    body.teacher_profile = {
      grade: form.grade || null,
      department: form.department || null,
    }
  }
  return body
}

function extractMessage(err: unknown): string {
  if (err instanceof ApiClientError) {
    const d = err.data as Record<string, unknown>
    const first = Object.values(d).flat().find(v => typeof v === 'string')
    return (first as string | undefined) ?? err.message
  }
  return err instanceof Error ? err.message : 'An unexpected error occurred.'
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function RoleBadge({ identity }: { identity: BusinessIdentity }) {
  return (
    <span
      className={`inline-flex h-5 items-center rounded-full border px-2.5 text-xs font-medium whitespace-nowrap ${ROLE_CLASSES[identity]}`}
    >
      {ROLE_LABELS[identity]}
    </span>
  )
}

function InlineError({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg bg-status-error-bg p-3 text-sm text-status-error-fg">
      <AlertCircle className="mt-0.5 size-4 shrink-0" />
      <span>{message}</span>
    </div>
  )
}

// ─── Shared form fields ───────────────────────────────────────────────────────

interface UserFormFieldsProps {
  form: UserFormState
  onChange: (patch: Partial<UserFormState>) => void
  isEdit?: boolean
}

function UserFormFields({ form, onChange, isEdit = false }: UserFormFieldsProps) {
  return (
    <div className="space-y-4">
      {/* Matricule + Role */}
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="uf-matricule">Matricule</Label>
          <Input
            id="uf-matricule"
            value={form.matricule}
            onChange={e => onChange({ matricule: e.target.value })}
          />
        </div>
        <div className="space-y-1.5">
          <Label>Role</Label>
          {isEdit ? (
            <Input
              value={
                form.business_identity
                  ? (ROLE_LABELS[form.business_identity as BusinessIdentity] ?? form.business_identity)
                  : ''
              }
              disabled
            />
          ) : (
            <Select
              value={form.business_identity}
              onValueChange={v => onChange({ business_identity: v as BusinessIdentity })}
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select role…" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="STUDENT">Student</SelectItem>
                <SelectItem value="TEACHER">Teacher</SelectItem>
                <SelectItem value="ADMINISTRATIVE_STAFF">Admin Staff</SelectItem>
                <SelectItem value="EXTERNAL_SUPERVISOR">Ext. Supervisor</SelectItem>
              </SelectContent>
            </Select>
          )}
        </div>
      </div>

      {/* Name */}
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="uf-first-name">First Name</Label>
          <Input
            id="uf-first-name"
            value={form.first_name}
            onChange={e => onChange({ first_name: e.target.value })}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="uf-last-name">Last Name</Label>
          <Input
            id="uf-last-name"
            value={form.last_name}
            onChange={e => onChange({ last_name: e.target.value })}
          />
        </div>
      </div>

      {/* Email */}
      <div className="space-y-1.5">
        <Label htmlFor="uf-email">Email</Label>
        <Input
          id="uf-email"
          type="email"
          value={form.email}
          onChange={e => onChange({ email: e.target.value })}
        />
      </div>

      {/* Password */}
      <div className="space-y-1.5">
        <Label htmlFor="uf-password">
          Password{' '}
          {isEdit && (
            <span className="font-normal text-muted-foreground">(leave blank to keep current)</span>
          )}
        </Label>
        <Input
          id="uf-password"
          type="password"
          value={form.password}
          onChange={e => onChange({ password: e.target.value })}
        />
      </div>

      {/* Account status */}
      <div className="space-y-1.5">
        <Label>Account Status</Label>
        <Select
          value={form.account_status}
          onValueChange={v => onChange({ account_status: v as AccountStatus })}
        >
          <SelectTrigger className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ACTIVE">Active</SelectItem>
            <SelectItem value="SUSPENDED">Suspended</SelectItem>
            <SelectItem value="ARCHIVED">Archived</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Student profile */}
      {form.business_identity === 'STUDENT' && (
        <div className="space-y-3 rounded-lg border border-border p-3">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Student Profile
          </p>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="uf-acad-year">Academic Year ID</Label>
              <Input
                id="uf-acad-year"
                type="number"
                min={1}
                placeholder="e.g. 1"
                value={form.academic_year}
                onChange={e => onChange({ academic_year: e.target.value })}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="uf-speciality">Speciality</Label>
              <Input
                id="uf-speciality"
                value={form.speciality}
                onChange={e => onChange({ speciality: e.target.value })}
              />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="uf-avg">Annual Average</Label>
            <Input
              id="uf-avg"
              placeholder="e.g. 15.50"
              value={form.annual_average}
              onChange={e => onChange({ annual_average: e.target.value })}
            />
          </div>
        </div>
      )}

      {/* Teacher / supervisor profile */}
      {(form.business_identity === 'TEACHER' ||
        form.business_identity === 'EXTERNAL_SUPERVISOR') && (
        <div className="space-y-3 rounded-lg border border-border p-3">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {form.business_identity === 'TEACHER' ? 'Teacher Profile' : 'Supervisor Profile'}
          </p>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="uf-grade">Grade</Label>
              <Input
                id="uf-grade"
                value={form.grade}
                onChange={e => onChange({ grade: e.target.value })}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="uf-dept">Department</Label>
              <Input
                id="uf-dept"
                value={form.department}
                onChange={e => onChange({ department: e.target.value })}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Create / Edit dialog ─────────────────────────────────────────────────────

type DialogMode = 'create' | 'create-admin' | 'edit'

interface UserDialogProps {
  mode: DialogMode
  user?: User
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
}

function UserDialog({ mode, user, open, onOpenChange, onSuccess }: UserDialogProps) {
  const [form, setForm] = useState<UserFormState>(EMPTY_FORM)
  const [accessLevel, setAccessLevel] = useState<'ADMIN' | 'SUPER_ADMIN'>('ADMIN')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setError(null)
    setLoading(false)
    if (mode === 'edit' && user) {
      setForm(userToForm(user))
    } else {
      setForm({
        ...EMPTY_FORM,
        business_identity: mode === 'create-admin' ? 'ADMINISTRATIVE_STAFF' : '',
      })
      setAccessLevel('ADMIN')
    }
  }, [open, mode, user])

  function patch(update: Partial<UserFormState>) {
    setForm(prev => ({ ...prev, ...update }))
  }

  async function handleSubmit() {
    setLoading(true)
    setError(null)
    try {
      if (mode === 'edit' && user) {
        await api.patch(`/api/admin/users/${user.id}/`, buildUserBody(form, true))
      } else if (mode === 'create-admin') {
        await api.post('/api/super-admin/admins/', {
          ...buildUserBody(form),
          access_level: accessLevel,
        })
      } else {
        await api.post('/api/admin/users/', buildUserBody(form))
      }
      onSuccess()
      onOpenChange(false)
    } catch (err) {
      setError(extractMessage(err))
    } finally {
      setLoading(false)
    }
  }

  const title =
    mode === 'edit' ? 'Edit User' : mode === 'create-admin' ? 'New Admin User' : 'New User'
  const confirmLabel = mode === 'edit' ? 'Save Changes' : 'Create'

  return (
    <Dialog open={open} onOpenChange={loading ? undefined : onOpenChange}>
      <DialogContent className="max-h-[90vh] max-w-lg overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>

        <UserFormFields form={form} onChange={patch} isEdit={mode === 'edit'} />

        {/* Access level — admin creation only */}
        {mode === 'create-admin' && (
          <div className="space-y-1.5">
            <Label>Access Level</Label>
            <Select
              value={accessLevel}
              onValueChange={v => setAccessLevel(v as 'ADMIN' | 'SUPER_ADMIN')}
            >
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ADMIN">Admin</SelectItem>
                <SelectItem value="SUPER_ADMIN">Super Admin</SelectItem>
              </SelectContent>
            </Select>
          </div>
        )}

        {error && <InlineError message={error} />}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={loading}>
            {loading && <Loader2 className="size-4 animate-spin" />}
            {confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ─── Grant access dialog ──────────────────────────────────────────────────────

interface GrantDialogProps {
  user: User | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
}

function GrantDialog({ user, open, onOpenChange, onSuccess }: GrantDialogProps) {
  const [accessLevel, setAccessLevel] = useState<'ADMIN' | 'SUPER_ADMIN'>('ADMIN')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (open) { setError(null); setLoading(false); setAccessLevel('ADMIN') }
  }, [open])

  async function handleGrant() {
    if (!user) return
    setLoading(true)
    setError(null)
    try {
      await api.post('/api/super-admin/platform-access-grants/', {
        user: user.id,
        access_level: accessLevel,
      })
      onSuccess()
      onOpenChange(false)
    } catch (err) {
      setError(extractMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={loading ? undefined : onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Grant Admin Access</DialogTitle>
        </DialogHeader>

        {user && (
          <p className="text-sm text-muted-foreground">
            Grant platform admin access to{' '}
            <span className="font-medium text-foreground">
              {user.first_name} {user.last_name}
            </span>
            .
          </p>
        )}

        <div className="space-y-1.5">
          <Label>Access Level</Label>
          <Select
            value={accessLevel}
            onValueChange={v => setAccessLevel(v as 'ADMIN' | 'SUPER_ADMIN')}
          >
            <SelectTrigger className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ADMIN">Admin</SelectItem>
              <SelectItem value="SUPER_ADMIN">Super Admin</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {error && <InlineError message={error} />}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
            Cancel
          </Button>
          <Button onClick={handleGrant} disabled={loading}>
            {loading && <Loader2 className="size-4 animate-spin" />}
            Grant Access
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ─── Main view ────────────────────────────────────────────────────────────────

export function UsersView() {
  const { user: currentUser } = useAuth()
  const isSuperAdmin = currentUser?.platform_access_level === 'SUPER_ADMIN'

  // ── Filter / pagination state ──────────────────────────────────────────────
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [search, setSearch] = useState('')
  const [appliedSearch, setAppliedSearch] = useState('')
  const [biFilter, setBiFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')

  // 400 ms debounce on search input
  useEffect(() => {
    const t = setTimeout(() => { setAppliedSearch(search); setPage(1) }, 400)
    return () => clearTimeout(t)
  }, [search])

  function applyFilter(setter: (v: string) => void) {
    return (v: string) => { setter(v); setPage(1) }
  }

  // ── Dialog state ──────────────────────────────────────────────────────────
  const [createOpen, setCreateOpen] = useState(false)
  const [createAdminOpen, setCreateAdminOpen] = useState(false)
  const [editUser, setEditUser] = useState<User | null>(null)
  const [archiveUser, setArchiveUser] = useState<User | null>(null)
  const [archiveLoading, setArchiveLoading] = useState(false)
  const [archiveError, setArchiveError] = useState<string | null>(null)
  const [grantUser, setGrantUser] = useState<User | null>(null)
  const [revokeGrant, setRevokeGrant] = useState<PlatformAccessGrant | null>(null)
  const [revokeLoading, setRevokeLoading] = useState(false)
  const [revokeError, setRevokeError] = useState<string | null>(null)

  // ── Data ──────────────────────────────────────────────────────────────────
  const usersApi = useApi<PaginatedResponse<User>>(
    () => {
      const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
      if (appliedSearch) params.set('search', appliedSearch)
      if (biFilter !== 'all') params.set('business_identity', biFilter)
      if (statusFilter !== 'all') params.set('account_status', statusFilter)
      return api.get(`/api/admin/users/?${params}`)
    },
    [page, pageSize, appliedSearch, biFilter, statusFilter],
  )

  // Fetch active grants to enable per-row revoke (fetches once, refreshed after mutations)
  const grantsApi = useApi<PaginatedResponse<PlatformAccessGrant>>(
    () => api.get('/api/admin/platform-access-grants/?is_active=true&page_size=100'),
    [],
  )

  // Build a user-id → grant lookup for active (non-revoked) grants
  const grantsMap = new Map<number, PlatformAccessGrant>()
  for (const g of (grantsApi.data?.results ?? [])) {
    if (g.revoked_at === null) grantsMap.set(g.user.id, g)
  }

  // ── Actions ───────────────────────────────────────────────────────────────
  async function handleArchive() {
    if (!archiveUser) return
    setArchiveLoading(true)
    setArchiveError(null)
    try {
      await api.post(`/api/admin/users/${archiveUser.id}/archive/`, {})
      setArchiveUser(null)
      usersApi.refetch()
    } catch (err) {
      setArchiveError(extractMessage(err))
    } finally {
      setArchiveLoading(false)
    }
  }

  async function handleRevoke() {
    if (!revokeGrant) return
    setRevokeLoading(true)
    setRevokeError(null)
    try {
      await api.post(`/api/super-admin/platform-access-grants/${revokeGrant.id}/revoke/`, {})
      setRevokeGrant(null)
      usersApi.refetch()
      grantsApi.refetch()
    } catch (err) {
      setRevokeError(extractMessage(err))
    } finally {
      setRevokeLoading(false)
    }
  }

  // ── Columns ───────────────────────────────────────────────────────────────
  const columns: Column<User>[] = [
    {
      key: 'matricule',
      header: 'Matricule',
      className: 'w-32',
      render: u => <span className="font-mono text-xs">{u.matricule}</span>,
    },
    {
      key: 'name',
      header: 'Name',
      render: u => (
        <div>
          <p className="text-sm font-medium text-foreground">
            {u.first_name} {u.last_name}
          </p>
          <p className="text-xs text-muted-foreground">{u.email}</p>
        </div>
      ),
    },
    {
      key: 'business_identity',
      header: 'Role',
      render: u => <RoleBadge identity={u.business_identity} />,
    },
    {
      key: 'account_status',
      header: 'Status',
      render: u => <StatusBadge status={u.account_status} />,
    },
    {
      key: 'platform_access_level',
      header: 'Admin',
      render: u =>
        u.platform_access_level ? (
          <StatusBadge
            status={u.platform_access_level}
            label={u.platform_access_level === 'SUPER_ADMIN' ? 'Super Admin' : 'Admin'}
          />
        ) : (
          <span className="text-muted-foreground">—</span>
        ),
    },
    {
      key: 'actions',
      header: '',
      className: 'w-10 text-right',
      render: u => {
        const activeGrant = grantsMap.get(u.id)
        const canGrant =
          isSuperAdmin &&
          !u.platform_access_level &&
          (u.business_identity === 'TEACHER' ||
            u.business_identity === 'ADMINISTRATIVE_STAFF')
        const canRevoke = isSuperAdmin && !!activeGrant

        return (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon-sm" aria-label="User actions">
                <MoreHorizontal className="size-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => setEditUser(u)}>Edit</DropdownMenuItem>
              <DropdownMenuItem
                variant="destructive"
                onClick={() => { setArchiveError(null); setArchiveUser(u) }}
              >
                Archive
              </DropdownMenuItem>
              {(canGrant || canRevoke) && <DropdownMenuSeparator />}
              {canGrant && (
                <DropdownMenuItem onClick={() => setGrantUser(u)}>
                  <Shield className="size-4" />
                  Grant Admin Access
                </DropdownMenuItem>
              )}
              {canRevoke && activeGrant && (
                <DropdownMenuItem
                  variant="destructive"
                  onClick={() => { setRevokeError(null); setRevokeGrant(activeGrant) }}
                >
                  <ShieldOff className="size-4" />
                  Revoke Access
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        )
      },
    },
  ]

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <>
      <PageHeader
        title="Users"
        description="Manage platform users and access grants."
        action={
          <div className="flex items-center gap-2">
            {isSuperAdmin && (
              <Button variant="outline" size="sm" onClick={() => setCreateAdminOpen(true)}>
                <Shield className="size-4" />
                New Admin
              </Button>
            )}
            <Button size="sm" onClick={() => setCreateOpen(true)}>
              <Plus className="size-4" />
              New User
            </Button>
          </div>
        }
      />

      {/* ── Filters ── */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="relative min-w-56 flex-1">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search name, email or matricule…"
            className="pl-8"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <Select value={biFilter} onValueChange={applyFilter(setBiFilter)}>
          <SelectTrigger className="w-44">
            <SelectValue placeholder="All roles" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All roles</SelectItem>
            <SelectItem value="STUDENT">Student</SelectItem>
            <SelectItem value="TEACHER">Teacher</SelectItem>
            <SelectItem value="ADMINISTRATIVE_STAFF">Admin Staff</SelectItem>
            <SelectItem value="EXTERNAL_SUPERVISOR">Ext. Supervisor</SelectItem>
          </SelectContent>
        </Select>
        <Select value={statusFilter} onValueChange={applyFilter(setStatusFilter)}>
          <SelectTrigger className="w-36">
            <SelectValue placeholder="All statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="ACTIVE">Active</SelectItem>
            <SelectItem value="SUSPENDED">Suspended</SelectItem>
            <SelectItem value="ARCHIVED">Archived</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* ── Table ── */}
      {usersApi.error ? (
        <InlineError message={usersApi.error} />
      ) : (
        <DataTable<User>
          columns={columns}
          data={usersApi.data?.results ?? []}
          keyField="id"
          isLoading={usersApi.isLoading}
          page={page}
          pageSize={pageSize}
          total={usersApi.data?.count ?? 0}
          onPageChange={setPage}
          onPageSizeChange={size => { setPageSize(size); setPage(1) }}
          emptyState={
            <EmptyState
              icon={Users}
              title="No users found"
              description="Try adjusting your search or filters."
              className="border-0 py-10"
            />
          }
        />
      )}

      {/* ── Dialogs ── */}
      <UserDialog
        mode="create"
        open={createOpen}
        onOpenChange={setCreateOpen}
        onSuccess={usersApi.refetch}
      />

      <UserDialog
        mode="create-admin"
        open={createAdminOpen}
        onOpenChange={setCreateAdminOpen}
        onSuccess={() => { usersApi.refetch(); grantsApi.refetch() }}
      />

      <UserDialog
        mode="edit"
        user={editUser ?? undefined}
        open={editUser !== null}
        onOpenChange={open => { if (!open) setEditUser(null) }}
        onSuccess={usersApi.refetch}
      />

      <GrantDialog
        user={grantUser}
        open={grantUser !== null}
        onOpenChange={open => { if (!open) setGrantUser(null) }}
        onSuccess={() => { usersApi.refetch(); grantsApi.refetch() }}
      />

      <ConfirmDialog
        open={archiveUser !== null}
        onOpenChange={open => { if (!open) { setArchiveUser(null); setArchiveError(null) } }}
        title="Archive User"
        description={`Archive ${archiveUser?.first_name ?? ''} ${archiveUser?.last_name ?? ''}? Their account will be deactivated and they will no longer be able to log in.`}
        confirmLabel="Archive"
        destructive
        isLoading={archiveLoading}
        error={archiveError}
        onConfirm={handleArchive}
      />

      <ConfirmDialog
        open={revokeGrant !== null}
        onOpenChange={open => { if (!open) { setRevokeGrant(null); setRevokeError(null) } }}
        title="Revoke Admin Access"
        description={`Revoke ${revokeGrant?.user.first_name ?? ''} ${revokeGrant?.user.last_name ?? ''}'s ${revokeGrant?.access_level === 'SUPER_ADMIN' ? 'Super Admin' : 'Admin'} access? They will lose all administrative privileges immediately.`}
        confirmLabel="Revoke"
        destructive
        isLoading={revokeLoading}
        error={revokeError}
        onConfirm={handleRevoke}
      />
    </>
  )
}
