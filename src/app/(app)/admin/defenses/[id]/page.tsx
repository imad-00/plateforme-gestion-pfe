import type { Metadata } from 'next'
import { DefenseDetailView } from './defense-detail-view'

export const metadata: Metadata = { title: 'Defense — GradeX Admin' }

interface PageProps {
  params: Promise<{ id: string }>
}

export default async function AdminDefenseDetailPage({ params }: PageProps) {
  const { id } = await params
  return <DefenseDetailView defenseId={id} />
}
