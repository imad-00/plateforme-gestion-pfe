import type { Metadata } from 'next'
import { DefenseRequestsView } from './defense-requests-view'

export const metadata: Metadata = { title: 'Defense requests — GradeX' }

export default function TeacherDefenseRequestsPage() {
  return <DefenseRequestsView />
}
