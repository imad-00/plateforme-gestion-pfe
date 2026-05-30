'use client'

import Link from 'next/link'
import { ArrowLeft, BookOpen, Link as LinkIcon, Paperclip, Sparkles, Target, User } from 'lucide-react'
import { api, ApiClientError } from '@/lib/api-client'
import { useApi } from '@/hooks/use-api'
import type { PublicSubject } from '@/lib/types'
import { PageHeader } from '@/components/layout/page-header'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

function extractMessage(err: unknown): string {
  if (err instanceof ApiClientError) {
    const d = err.data as Record<string, unknown>
    const first = Object.values(d).flat().find(v => typeof v === 'string')
    return (first as string | undefined) ?? err.message
  }
  return err instanceof Error ? err.message : 'An unexpected error occurred.'
}

const TYPE_LABEL: Record<string, string> = {
  RESEARCH_PROJECT: 'Research project',
  APPLIED_PROJECT: 'Applied project',
  STARTUP_PROJECT: 'Startup project',
}

function splitLines(text: string | undefined | null): string[] {
  if (!text) return []
  return text
    .split(/\r?\n/)
    .map(l => l.trim())
    .filter(Boolean)
}

function isLikelyUrl(s: string): boolean {
  return /^https?:\/\//i.test(s)
}

export function SubjectDetailView({ id }: { id: string }) {
  const { data, isLoading, error } = useApi<PublicSubject>(
    () => api.get(`/api/subjects/${id}/`),
    [id],
  )

  return (
    <div className="space-y-6">
      <div>
        <Link
          href="/student/subjects"
          className="mb-3 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-3.5" />
          Back to subjects
        </Link>
        <PageHeader
          title={data?.title ?? 'Subject details'}
          description={data ? TYPE_LABEL[data.subject_type] ?? data.subject_type : 'Full subject description and requirements.'}
        />
      </div>

      {isLoading && (
        <div className="space-y-4">
          <Skeleton className="h-32 w-full rounded-xl" />
          <Skeleton className="h-32 w-full rounded-xl" />
        </div>
      )}

      {error && <p className="text-sm text-status-error-fg">{extractMessage(error)}</p>}

      {data && (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <BookOpen className="size-4 text-muted-foreground" />
                Description
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="whitespace-pre-line text-sm text-foreground">{data.description}</p>
              {data.subject_code && (
                <p className="mt-3 font-mono text-xs text-muted-foreground">{data.subject_code}</p>
              )}
            </CardContent>
          </Card>

          {data.requirements && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Target className="size-4 text-muted-foreground" />
                  Requirements & prerequisites
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="whitespace-pre-line text-sm text-foreground">{data.requirements}</p>
              </CardContent>
            </Card>
          )}

          {data.required_skills && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Sparkles className="size-4 text-muted-foreground" />
                  Required skills
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-1.5">
                  {data.required_skills
                    .split(/[,;\n]/)
                    .map(s => s.trim())
                    .filter(Boolean)
                    .map((skill, i) => (
                      <span
                        key={`${skill}-${i}`}
                        className="rounded-full border border-border bg-muted/60 px-2.5 py-1 text-xs"
                      >
                        {skill}
                      </span>
                    ))}
                </div>
              </CardContent>
            </Card>
          )}

          {splitLines(data.helpful_links).length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <LinkIcon className="size-4 text-muted-foreground" />
                  Helpful links & resources
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm">
                  {splitLines(data.helpful_links).map((line, i) =>
                    isLikelyUrl(line) ? (
                      <li key={i}>
                        <a
                          href={line}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="break-all text-primary hover:underline"
                        >
                          {line}
                        </a>
                      </li>
                    ) : (
                      <li key={i} className="text-muted-foreground">{line}</li>
                    ),
                  )}
                </ul>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <User className="size-4 text-muted-foreground" />
                Proposed by
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm">
                <span className="font-medium">
                  {data.proposed_by.first_name} {data.proposed_by.last_name}
                </span>{' '}
                <span className="text-muted-foreground">({data.proposed_by.matricule})</span>
              </p>
              <p className="text-xs text-muted-foreground">{data.proposed_by.email}</p>
              {data.attachment_url && (
                <a
                  href={data.attachment_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-3 inline-flex items-center gap-1 text-sm text-primary hover:underline"
                >
                  <Paperclip className="size-3.5" />
                  Download attachment
                </a>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
