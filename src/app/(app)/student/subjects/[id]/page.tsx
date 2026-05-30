import { SubjectDetailView } from './subject-detail-view'

export default async function StudentSubjectDetailPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  return <SubjectDetailView id={id} />
}
