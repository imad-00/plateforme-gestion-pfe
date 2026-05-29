import type { Metadata } from 'next'
import { JuryDefenseDetailView } from './jury-defense-detail-view'

export const metadata: Metadata = { title: 'Defense — Jury' }

interface PageProps {
  params: Promise<{ id: string }>
}

export default async function JuryDefenseDetailPage({ params }: PageProps) {
  const { id } = await params
  return <JuryDefenseDetailView defenseId={id} />
}
