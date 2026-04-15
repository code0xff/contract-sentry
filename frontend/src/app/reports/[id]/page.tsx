'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getReport, getReportMarkdown } from '@/lib/api';
import type { Report } from '@/types';
import { PageError, PageLoading } from '@/components/page-state';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { cn } from '@/lib/utils';

const SEVERITY_TEXT: Record<string, string> = {
  critical: 'text-red-600 dark:text-red-400',
  high:     'text-orange-600 dark:text-orange-400',
  medium:   'text-yellow-600 dark:text-yellow-500',
  low:      'text-green-600 dark:text-green-400',
  info:     'text-blue-600 dark:text-blue-400',
};

const SEVERITY_BORDER_T: Record<string, string> = {
  critical: 'border-t-red-500',
  high:     'border-t-orange-500',
  medium:   'border-t-yellow-500',
  low:      'border-t-green-500',
  info:     'border-t-blue-500',
};

const SEVERITIES = ['critical', 'high', 'medium', 'low', 'info'] as const;

export default function ReportPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [report, setReport] = useState<Report | null>(null);
  const [markdown, setMarkdown] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getReport(id), getReportMarkdown(id)])
      .then(([r, md]) => { setReport(r); setMarkdown(md); })
      .catch(err => setError(err instanceof Error ? err.message : 'Failed to load'))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <PageLoading message="Loading report…" />;
  if (error)   return <PageError error={error} onRetry={() => { setLoading(true); setError(null); Promise.all([getReport(id), getReportMarkdown(id)]).then(([r, md]) => { setReport(r); setMarkdown(md); }).catch(err => setError(err instanceof Error ? err.message : 'Failed to load')).finally(() => setLoading(false)); }} />;
  if (!report) return <PageError error="Report not found" />;

  const { summary } = report;

  return (
    <div>
      <Button variant="ghost" size="sm" className="-ml-2 mb-4" onClick={() => router.back()}>
        ← Back
      </Button>

      <h1 className="mb-1 text-2xl font-bold">Security Report</h1>
      <p className="mb-6 text-sm text-muted-foreground">
        Job: <code className="text-xs">{id}</code> · Generated: {new Date(report.created_at).toLocaleString()}
      </p>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-base">Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="mb-4 grid grid-cols-5 gap-3">
            {SEVERITIES.map(sev => (
              <div key={sev} className={cn(
                "rounded-md border-t-2 bg-muted p-3 text-center",
                SEVERITY_BORDER_T[sev]
              )}>
                <div className={cn("text-2xl font-bold", SEVERITY_TEXT[sev])}>
                  {summary.by_severity?.[sev] ?? 0}
                </div>
                <div className="mt-1 text-xs uppercase text-muted-foreground">{sev}</div>
              </div>
            ))}
          </div>
          <p className="text-sm">
            <strong>Total findings:</strong> {summary.total}
            {summary.composite_severity && (
              <>
                {' · '}
                <strong>Composite severity:</strong>{' '}
                <span className={SEVERITY_TEXT[summary.composite_severity] ?? ''}>
                  {summary.composite_severity.toUpperCase()}
                </span>
              </>
            )}
          </p>
        </CardContent>
      </Card>

      <Tabs defaultValue="summary">
        <div className="mb-3 flex items-center justify-between">
          <TabsList>
            <TabsTrigger value="summary">Overview</TabsTrigger>
            <TabsTrigger value="markdown">Full Report</TabsTrigger>
          </TabsList>
          <a
            href={`/api/v1/reports/${id}/html`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-muted-foreground underline underline-offset-4 hover:text-foreground"
          >
            HTML ↗
          </a>
        </div>

        <Card>
          <CardContent className="pt-5">
            <TabsContent value="summary">
              <p className="mb-3 text-sm text-muted-foreground">
                This report summarises all findings from static analysis, dynamic fuzzing, and exploit simulation.
                Switch to <strong>Full Report</strong> for remediation guidance.
              </p>
              {report.status !== 'ready' && (
                <p className="text-sm text-amber-600 dark:text-amber-400">
                  ⚠ Report is still being generated. Refresh shortly.
                </p>
              )}
            </TabsContent>
            <TabsContent value="markdown">
              <pre className="overflow-x-auto whitespace-pre-wrap font-mono text-xs leading-relaxed">
                {markdown || 'No content yet.'}
              </pre>
            </TabsContent>
          </CardContent>
        </Card>
      </Tabs>
    </div>
  );
}
