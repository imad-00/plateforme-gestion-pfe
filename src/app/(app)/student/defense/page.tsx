import type { Metadata } from 'next'
import { DefenseView } from './defense-view'

export const metadata: Metadata = { title: 'Defense — GradeX' }

export default function StudentDefensePage() {
  return <DefenseView />
}
