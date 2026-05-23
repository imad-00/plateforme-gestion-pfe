import { GraduationCap } from 'lucide-react'

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center gap-8 p-4">
      <header className="flex flex-col items-center gap-2 text-center">
        <div className="flex size-11 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-card">
          <GraduationCap className="size-5" />
        </div>
        <span className="text-xl font-bold tracking-tight">GradeX</span>
        <span className="text-sm text-muted-foreground">PFE Management Platform</span>
      </header>
      {children}
    </div>
  )
}
