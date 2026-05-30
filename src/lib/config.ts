// Centralised runtime config. Anything that used to read
// `process.env.NEXT_PUBLIC_*` from N different files now flows through here so
// the fallback string lives in exactly one place.
//
// `NEXT_PUBLIC_API_URL` is baked into the browser bundle at build time, so this
// module is safe to import from either client or server components.

export const API_BASE: string =
  process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

// Resolve a possibly-relative file URL into a full one. Used for deliverable
// files, defense attached files, and PV downloads — DRF's `FileField.url`
// returns either an absolute S3/MinIO URL or a `/media/...` relative path
// depending on the storage backend.
export function buildFileUrl(path: string): string {
  if (!path) return ''
  return path.startsWith('http') ? path : `${API_BASE}${path}`
}
