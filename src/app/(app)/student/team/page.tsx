import type { Metadata } from 'next'
import { Suspense } from 'react'
import { TeamView } from './team-view'

export const metadata: Metadata = { title: 'My Team — GradeX' }

export default function TeamPage() {
  return (
    <Suspense>
      <TeamView />
    </Suspense>
  )
}
