import type { Metadata } from 'next'
import { JuryDefensesView } from './jury-defenses-view'

export const metadata: Metadata = { title: 'Jury — GradeX' }

export default function JuryDefensesPage() {
  return <JuryDefensesView />
}
