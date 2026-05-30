'use client'

import { useRef, useState } from 'react'
import {
  AlertCircle,
  CheckCircle2,
  FileText,
  Lock,
  Plus,
  Trash2,
  Upload,
  User as UserIcon,
  X,
} from 'lucide-react'
import { api } from '@/lib/api-client'
import { ApiClientError } from '@/lib/api-client'
import { useAuth } from '@/lib/auth-context'
import { buildFileUrl } from '@/lib/config'
import type { User } from '@/lib/types'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { PageHeader } from '@/components/layout/page-header'

function extractMessage(err: unknown): string {
  if (err instanceof ApiClientError) {
    const d = err.data as Record<string, unknown>
    const first = Object.values(d).flat().find(v => typeof v === 'string')
    return (first as string | undefined) ?? err.message
  }
  return err instanceof Error ? err.message : 'An unexpected error occurred.'
}

function InlineError({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg bg-status-error-bg p-3 text-sm text-status-error-fg">
      <AlertCircle className="mt-0.5 size-4 shrink-0" />
      <span>{message}</span>
    </div>
  )
}

function InlineSuccess({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg bg-status-success-bg p-3 text-sm text-status-success-fg">
      <CheckCircle2 className="mt-0.5 size-4 shrink-0" />
      <span>{message}</span>
    </div>
  )
}

export function ProfileView() {
  const { user, refreshUser } = useAuth()

  if (!user) return null

  return (
    <div className="space-y-6">
      <PageHeader
        title="My profile"
        description="Update your personal information, CV and password."
      />

      <ReadOnlyIdentity user={user} />
      <PersonalInfoCard user={user} onSaved={refreshUser} />
      {user.business_identity === 'TEACHER' && (
        <TeacherProfileCard user={user} onSaved={refreshUser} />
      )}
      {user.business_identity === 'STUDENT' && (
        <StudentProfileCard user={user} onSaved={refreshUser} />
      )}
      {user.business_identity === 'EXTERNAL_SUPERVISOR' && (
        <ExternalSupervisorCard user={user} onSaved={refreshUser} />
      )}
      <CVUploadCard user={user} onChanged={refreshUser} />
      <ChangePasswordCard />
    </div>
  )
}

// ─── Read-only identity ───────────────────────────────────────────────────────

function ReadOnlyIdentity({ user }: { user: User }) {
  const role =
    user.platform_access_level === 'SUPER_ADMIN'
      ? 'Super Admin'
      : user.platform_access_level === 'ADMIN'
        ? 'Admin'
        : user.business_identity.replace('_', ' ').toLowerCase()

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <UserIcon className="size-4 text-muted-foreground" />
          Account identity
        </CardTitle>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-1 gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-xs text-muted-foreground">Matricule</dt>
            <dd className="font-medium">{user.matricule}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Email</dt>
            <dd className="font-medium">{user.email}</dd>
            <dd className="mt-0.5 text-xs text-muted-foreground">
              Email is managed by your administrator and cannot be changed here.
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Role</dt>
            <dd className="font-medium capitalize">{role}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Account status</dt>
            <dd className="font-medium">
              <Badge variant="outline">{user.account_status}</Badge>
            </dd>
          </div>
        </dl>
      </CardContent>
    </Card>
  )
}

// ─── Personal info (name + bio + interests) ───────────────────────────────────

function PersonalInfoCard({ user, onSaved }: { user: User; onSaved: () => void }) {
  const [firstName, setFirstName] = useState(user.first_name)
  const [lastName, setLastName] = useState(user.last_name)
  const [bio, setBio] = useState(user.bio ?? '')
  const [interests, setInterests] = useState<string[]>(user.interests ?? [])
  const [interestDraft, setInterestDraft] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  function addInterest() {
    const t = interestDraft.trim()
    if (!t) return
    if (interests.includes(t)) {
      setInterestDraft('')
      return
    }
    setInterests([...interests, t].slice(0, 20))
    setInterestDraft('')
  }

  function removeInterest(value: string) {
    setInterests(interests.filter(i => i !== value))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setSuccess(null)
    setSaving(true)
    try {
      await api.patch<User>('/api/auth/me/', {
        first_name: firstName,
        last_name: lastName,
        bio,
        interests,
      })
      setSuccess('Personal information updated.')
      onSaved()
    } catch (err) {
      setError(extractMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Personal information</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="first_name">First name</Label>
              <Input
                id="first_name"
                value={firstName}
                onChange={e => setFirstName(e.target.value)}
                maxLength={150}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="last_name">Last name</Label>
              <Input
                id="last_name"
                value={lastName}
                onChange={e => setLastName(e.target.value)}
                maxLength={150}
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="bio">Bio</Label>
            <Textarea
              id="bio"
              value={bio}
              onChange={e => setBio(e.target.value)}
              placeholder="A short bio that other users can see."
              rows={4}
              maxLength={2000}
            />
            <p className="text-xs text-muted-foreground">{bio.length}/2000</p>
          </div>

          <div className="space-y-1.5">
            <Label>Interests</Label>
            <div className="flex gap-2">
              <Input
                value={interestDraft}
                onChange={e => setInterestDraft(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    addInterest()
                  }
                }}
                placeholder="Add an interest and press Enter"
                maxLength={64}
              />
              <Button type="button" variant="outline" onClick={addInterest}>
                <Plus className="size-4" />
                Add
              </Button>
            </div>
            {interests.length > 0 && (
              <div className="flex flex-wrap gap-1.5 pt-2">
                {interests.map(i => (
                  <Badge key={i} variant="secondary" className="gap-1 pr-1">
                    {i}
                    <button
                      type="button"
                      onClick={() => removeInterest(i)}
                      className="rounded-full p-0.5 hover:bg-muted-foreground/20"
                      aria-label={`Remove ${i}`}
                    >
                      <X className="size-3" />
                    </button>
                  </Badge>
                ))}
              </div>
            )}
            <p className="text-xs text-muted-foreground">
              Up to 20 interests. Helps supervisors and teammates find you.
            </p>
          </div>

          {error && <InlineError message={error} />}
          {success && <InlineSuccess message={success} />}

          <div className="flex justify-end">
            <Button type="submit" disabled={saving}>
              {saving ? 'Saving…' : 'Save changes'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}

// ─── Teacher / student / external profile cards ───────────────────────────────

function TeacherProfileCard({ user, onSaved }: { user: User; onSaved: () => void }) {
  const initial = user.teacher_profile
  const [grade, setGrade] = useState(initial?.grade ?? '')
  const [department, setDepartment] = useState(initial?.department ?? '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setSuccess(null)
    setSaving(true)
    try {
      await api.patch<User>('/api/auth/me/', {
        teacher_profile: { grade, department },
      })
      setSuccess('Teaching profile updated.')
      onSaved()
    } catch (err) {
      setError(extractMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Teaching profile</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="grade">Grade</Label>
              <Input id="grade" value={grade} onChange={e => setGrade(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="department">Department</Label>
              <Input id="department" value={department} onChange={e => setDepartment(e.target.value)} />
            </div>
          </div>
          {error && <InlineError message={error} />}
          {success && <InlineSuccess message={success} />}
          <div className="flex justify-end">
            <Button type="submit" disabled={saving}>
              {saving ? 'Saving…' : 'Save changes'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}

function StudentProfileCard({ user, onSaved }: { user: User; onSaved: () => void }) {
  const initial = user.student_profile
  const [skillsSummary, setSkillsSummary] = useState(initial?.skills_summary ?? '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setSuccess(null)
    setSaving(true)
    try {
      await api.patch<User>('/api/auth/me/', {
        student_profile: { skills_summary: skillsSummary },
      })
      setSuccess('Student profile updated.')
      onSaved()
    } catch (err) {
      setError(extractMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Student profile</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <dl className="grid grid-cols-1 gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-xs text-muted-foreground">Speciality</dt>
              <dd className="font-medium">{initial?.speciality ?? '—'}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Annual average</dt>
              <dd className="font-medium">{initial?.annual_average ?? '—'}</dd>
            </div>
          </dl>
          <div className="space-y-1.5">
            <Label htmlFor="skills_summary">Skills summary</Label>
            <Textarea
              id="skills_summary"
              value={skillsSummary}
              onChange={e => setSkillsSummary(e.target.value)}
              placeholder="A short summary of your technical and soft skills."
              rows={4}
            />
          </div>
          {error && <InlineError message={error} />}
          {success && <InlineSuccess message={success} />}
          <div className="flex justify-end">
            <Button type="submit" disabled={saving}>
              {saving ? 'Saving…' : 'Save changes'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}

function ExternalSupervisorCard({ user, onSaved }: { user: User; onSaved: () => void }) {
  const initial = user.external_supervisor_profile
  const [organization, setOrganization] = useState(initial?.organization ?? '')
  const [jobTitle, setJobTitle] = useState(initial?.job_title ?? '')
  const [expertiseArea, setExpertiseArea] = useState(initial?.expertise_area ?? '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setSuccess(null)
    setSaving(true)
    try {
      await api.patch<User>('/api/auth/me/', {
        external_supervisor_profile: {
          organization,
          job_title: jobTitle,
          expertise_area: expertiseArea,
        },
      })
      setSuccess('External supervisor profile updated.')
      onSaved()
    } catch (err) {
      setError(extractMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">External supervisor profile</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="organization">Organization</Label>
              <Input id="organization" value={organization} onChange={e => setOrganization(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="job_title">Job title</Label>
              <Input id="job_title" value={jobTitle} onChange={e => setJobTitle(e.target.value)} />
            </div>
            <div className="space-y-1.5 sm:col-span-2">
              <Label htmlFor="expertise_area">Expertise area</Label>
              <Input
                id="expertise_area"
                value={expertiseArea}
                onChange={e => setExpertiseArea(e.target.value)}
                placeholder="e.g. Web security, distributed systems, DevOps"
              />
            </div>
          </div>
          {error && <InlineError message={error} />}
          {success && <InlineSuccess message={success} />}
          <div className="flex justify-end">
            <Button type="submit" disabled={saving}>
              {saving ? 'Saving…' : 'Save changes'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}

// ─── CV upload ────────────────────────────────────────────────────────────────

function CVUploadCard({ user, onChanged }: { user: User; onChanged: () => void }) {
  const fileInput = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const cvUrl = user.cv_file_url ? buildFileUrl(user.cv_file_url) : null

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setError(null)
    setUploading(true)
    try {
      const fd = new FormData()
      fd.append('cv_file', file)
      await api.post<User>('/api/auth/me/cv/', fd)
      onChanged()
    } catch (err) {
      setError(extractMessage(err))
    } finally {
      setUploading(false)
      if (fileInput.current) fileInput.current.value = ''
    }
  }

  async function handleRemove() {
    setError(null)
    setUploading(true)
    try {
      await api.delete<User>('/api/auth/me/cv/')
      onChanged()
    } catch (err) {
      setError(extractMessage(err))
    } finally {
      setUploading(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <FileText className="size-4 text-muted-foreground" />
          CV / Resume
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {cvUrl ? (
          <div className="flex items-center justify-between rounded-lg border border-border bg-muted/40 px-3 py-2 text-sm">
            <a
              href={cvUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-primary hover:underline"
            >
              <FileText className="size-4" />
              View current CV
            </a>
            <Button variant="ghost" size="sm" onClick={handleRemove} disabled={uploading}>
              <Trash2 className="size-3.5" />
              Remove
            </Button>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No CV uploaded yet.</p>
        )}
        <input
          ref={fileInput}
          type="file"
          accept=".pdf,.doc,.docx"
          className="hidden"
          onChange={handleFile}
        />
        <Button
          type="button"
          variant="outline"
          onClick={() => fileInput.current?.click()}
          disabled={uploading}
        >
          <Upload className="size-4" />
          {uploading ? 'Uploading…' : cvUrl ? 'Replace CV' : 'Upload CV'}
        </Button>
        <p className="text-xs text-muted-foreground">
          PDF, DOC or DOCX up to 10 MB.
        </p>
        {error && <InlineError message={error} />}
      </CardContent>
    </Card>
  )
}

// ─── Change password ──────────────────────────────────────────────────────────

function ChangePasswordCard() {
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setSuccess(null)
    if (newPassword !== confirmPassword) {
      setError('New password and confirmation do not match.')
      return
    }
    setSaving(true)
    try {
      await api.post('/api/auth/change-password/', {
        old_password: oldPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      })
      setSuccess('Password updated. You will stay signed in on this device.')
      setOldPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (err) {
      setError(extractMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Lock className="size-4 text-muted-foreground" />
          Change password
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="old_password">Current password</Label>
            <Input
              id="old_password"
              type="password"
              value={oldPassword}
              onChange={e => setOldPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="new_password">New password</Label>
            <Input
              id="new_password"
              type="password"
              value={newPassword}
              onChange={e => setNewPassword(e.target.value)}
              autoComplete="new-password"
              required
              minLength={8}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="confirm_password">Confirm new password</Label>
            <Input
              id="confirm_password"
              type="password"
              value={confirmPassword}
              onChange={e => setConfirmPassword(e.target.value)}
              autoComplete="new-password"
              required
              minLength={8}
            />
          </div>
          {error && <InlineError message={error} />}
          {success && <InlineSuccess message={success} />}
          <div className="flex justify-end">
            <Button type="submit" disabled={saving}>
              {saving ? 'Updating…' : 'Update password'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
