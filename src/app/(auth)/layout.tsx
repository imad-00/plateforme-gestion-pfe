import Link from 'next/link'
import { GraduationCap } from 'lucide-react'

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center gap-8 p-4">
      <Link
        href="/"
        className="flex flex-col items-center gap-2 text-center transition-opacity hover:opacity-90"
        aria-label="GradeX home"
      >
        <div className="flex size-11 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-card">
          <GraduationCap className="size-5" />
        </div>
        <span className="text-xl font-bold tracking-tight">GradeX</span>
        <span className="text-sm text-muted-foreground">
          PFE Management · École Supérieure en Informatique — Sidi Bel Abbès
        </span>
      </Link>
      {children}
      <footer className="text-center">
        <p className="text-xs text-muted-foreground">
          ESI-SBA ·{' '}
          <a
            href="https://www.esi-sba.dz"
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium text-foreground hover:underline"
          >
            esi-sba.dz
          </a>
        </p>
      </footer>
    </div>
  )
}
