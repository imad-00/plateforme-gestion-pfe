import type { Metadata } from 'next'
import { LifecycleView } from './lifecycle-view'

export const metadata: Metadata = { title: 'Lifecycle — GradeX Super Admin' }

export default function AdminLifecyclePage() {
  return <LifecycleView />
}
