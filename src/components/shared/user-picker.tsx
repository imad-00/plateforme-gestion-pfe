'use client'

import { useEffect, useRef, useState } from 'react'
import { Check, Loader2, Search, X } from 'lucide-react'
import { api } from '@/lib/api-client'
import type { BusinessIdentity, PaginatedResponse, User } from '@/lib/types'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

// ─── Shape ───────────────────────────────────────────────────────────────────
// A small denormalised user record the picker emits and consumes. Avoids forcing
// callers to keep full User objects around — id + display name is enough for
// rendering chips and submitting forms.

export interface PickerUser {
  id: number
  first_name: string
  last_name: string
  matricule: string
}

function initials(first: string, last: string): string {
  return `${first[0] ?? ''}${last[0] ?? ''}`.toUpperCase()
}

function toPicker(u: User): PickerUser {
  return { id: u.id, first_name: u.first_name, last_name: u.last_name, matricule: u.matricule }
}

// ─── Picker ──────────────────────────────────────────────────────────────────

interface UserPickerProps {
  value: PickerUser[]
  onChange: (next: PickerUser[]) => void
  /** When false (default), only one user can be selected at a time. */
  multi?: boolean
  /** Backend identity filter passed to /api/admin/users/. Default TEACHER. */
  identity?: BusinessIdentity
  /** IDs the user is not allowed to pick (e.g. team supervisors for jury form). */
  excludeIds?: number[]
  placeholder?: string
  disabled?: boolean
}

export function UserPicker({
  value,
  onChange,
  multi = false,
  identity = 'TEACHER',
  excludeIds = [],
  placeholder = 'Search by name or matricule…',
  disabled = false,
}: UserPickerProps) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [results, setResults] = useState<User[]>([])
  const [loading, setLoading] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  // Click-outside to close the dropdown.
  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (!containerRef.current?.contains(e.target as Node)) setOpen(false)
    }
    if (open) document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [open])

  // Debounced search. Empty query still triggers a search so the user sees the
  // first page of options as soon as they focus the input — common UX with no
  // typing required.
  useEffect(() => {
    if (!open) return
    const handle = setTimeout(async () => {
      setLoading(true)
      try {
        const params = new URLSearchParams({
          page_size: '15',
          business_identity: identity,
          account_status: 'ACTIVE',
        })
        if (query.trim()) params.set('search', query.trim())
        const res = await api.get<PaginatedResponse<User>>(`/api/admin/users/?${params}`)
        setResults(res.results)
      } catch {
        setResults([])
      } finally {
        setLoading(false)
      }
    }, 200)
    return () => clearTimeout(handle)
  }, [query, open, identity])

  const selectedIds = new Set(value.map(u => u.id))
  const excluded = new Set(excludeIds)

  function toggle(u: User) {
    const picker = toPicker(u)
    if (multi) {
      if (selectedIds.has(u.id)) {
        onChange(value.filter(v => v.id !== u.id))
      } else {
        onChange([...value, picker])
      }
    } else {
      onChange([picker])
      setOpen(false)
      setQuery('')
    }
  }

  function remove(id: number) {
    onChange(value.filter(v => v.id !== id))
  }

  return (
    <div ref={containerRef} className="space-y-2">
      {/* Selected chips */}
      {value.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {value.map(u => (
            <span
              key={u.id}
              className="inline-flex items-center gap-1.5 rounded-full border border-border bg-muted/60 py-1 pl-2 pr-1 text-xs"
            >
              <Avatar size="sm" className="size-5">
                <AvatarFallback className="bg-primary/10 text-[10px] font-medium text-primary">
                  {initials(u.first_name, u.last_name)}
                </AvatarFallback>
              </Avatar>
              <span className="text-foreground">
                {u.first_name} {u.last_name}
              </span>
              <button
                type="button"
                disabled={disabled}
                onClick={() => remove(u.id)}
                className="rounded-full p-0.5 text-muted-foreground hover:bg-background hover:text-foreground"
                aria-label={`Remove ${u.first_name} ${u.last_name}`}
              >
                <X className="size-3" />
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Search input */}
      <div className="relative">
        <Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={query}
          onChange={e => setQuery(e.target.value)}
          onFocus={() => setOpen(true)}
          placeholder={placeholder}
          disabled={disabled || (!multi && value.length > 0)}
          className="pl-8"
        />

        {/* Dropdown */}
        {open && (
          <div className="absolute left-0 right-0 top-[calc(100%+2px)] z-50 max-h-56 overflow-y-auto rounded-lg border border-border bg-popover p-1 shadow-md">
            {loading ? (
              <div className="flex items-center justify-center gap-2 p-3 text-sm text-muted-foreground">
                <Loader2 className="size-3.5 animate-spin" />
                Searching…
              </div>
            ) : results.length === 0 ? (
              <p className="p-3 text-center text-sm text-muted-foreground">No matches.</p>
            ) : (
              results.map(u => {
                const isExcluded = excluded.has(u.id)
                const isSelected = selectedIds.has(u.id)
                return (
                  <button
                    key={u.id}
                    type="button"
                    disabled={isExcluded}
                    onClick={() => toggle(u)}
                    className={[
                      'flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left text-sm transition-colors',
                      isExcluded
                        ? 'cursor-not-allowed opacity-50'
                        : 'hover:bg-muted focus:bg-muted focus:outline-none',
                      isSelected ? 'bg-primary/5' : '',
                    ].join(' ')}
                  >
                    <Avatar size="sm">
                      <AvatarFallback className="bg-primary/10 text-[10px] font-medium text-primary">
                        {initials(u.first_name, u.last_name)}
                      </AvatarFallback>
                    </Avatar>
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium text-foreground">
                        {u.first_name} {u.last_name}
                      </p>
                      <p className="truncate text-xs text-muted-foreground">
                        {u.matricule}{isExcluded ? ' · Already a supervisor' : ''}
                      </p>
                    </div>
                    {isSelected && <Check className="size-3.5 text-primary" />}
                  </button>
                )
              })
            )}
          </div>
        )}
      </div>

      {!multi && value.length > 0 && (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-auto p-0 text-xs text-muted-foreground"
          onClick={() => onChange([])}
          disabled={disabled}
        >
          Clear selection
        </Button>
      )}
    </div>
  )
}
