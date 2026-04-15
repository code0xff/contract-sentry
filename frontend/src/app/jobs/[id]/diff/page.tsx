'use client';

import { Suspense, useEffect, useState } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { diffFindings } from '@/lib/api';
import type { Finding, FindingDiff } from '@/types/index';
import { PageError, PageLoading } from '@/components/page-state';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';

const SEVERITY_BADGE: Record<string, string> = {
  critical: 'bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-400',
  high:     'bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-900/30 dark:text-orange-400',
  medium:   'bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-400',
  low:      'bg-green-100 text-green-700 border-green-200 dark:bg-green-900/30 dark:text-green-400',
  info:     'bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-400',
};

const SEVERITY_BORDER_L: Record<string, string> = {
  critical: 'border-l-red-500',
  high:     'border-l-orange-500',
  medium:   'border-l-yellow-500',
  low:      'border-l-green-500',
  info:     'border-l-blue-500',
};

function FindingCard({ finding }: { finding: Finding }) {
  return (
    <Card className={cn('border-l-4', SEVERITY_BORDER_L[finding.severity] ?? 'border-l-border')}>
      <CardContent className="px-4 py-3">
        <div className="mb-1 flex items-center gap-2">
          <span className={cn(
            'inline-flex items-center rounded border px-2 py-0.5 text-xs font-bold',
            SEVERITY_BADGE[finding.severity] ?? 'bg-secondary text-secondary-foreground border-border',
          )}>
            {finding.severity.toUpperCase()}
          </span>
          <strong className="text-sm">{finding.title}</strong>
        </div>
        <p className="text-xs text-muted-foreground">
          Type: {finding.vulnerability_type}
          {finding.location && ` · ${finding.location}`}
        </p>
      </CardContent>
    </Card>
  );
}

function Section({ title, findings, accentClass }: { title: string; findings: Finding[]; accentClass: string }) {
  return (
    <div className="mb-8">
      <h2 className={cn('mb-3 text-base font-semibold', accentClass)}>
        {title} <span className="font-normal text-muted-foreground">({findings.length})</span>
      </h2>
      {findings.length === 0 ? (
        <p className="text-sm text-muted-foreground italic">None</p>
      ) : (
        <div className="flex flex-col gap-2">
          {findings.map(f => <FindingCard key={f.id} finding={f} />)}
        </div>
      )}
    </div>
  );
}

function DiffContent() {
  const { id } = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const baseline = searchParams.get('baseline') ?? '';
  const router = useRouter();

  const [diff, setDiff] = useState<FindingDiff | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!baseline) {
      setError('Missing baseline job ID — please go back and enter a valid job ID to compare against.');
      setLoading(false);
      return;
    }
    diffFindings(id, baseline)
      .then(setDiff)
      .catch(err => setError(err instanceof Error ? err.message : 'Failed to load diff'))
      .finally(() => setLoading(false));
  }, [id, baseline]);

  if (loading) return <PageLoading message="Loading diff…" />;
  if (error)   return <PageError error={error} onRetry={baseline ? () => { setLoading(true); setError(null); diffFindings(id, baseline).then(setDiff).catch(e => setError(e instanceof Error ? e.message : 'Failed to load diff')).finally(() => setLoading(false)); } : undefined} />;
  if (!diff)   return null;

  return (
    <div>
      <Button variant="ghost" size="sm" className="-ml-2 mb-4" onClick={() => router.push(`/jobs/${id}`)}>
        ← Back to Job
      </Button>

      <h1 className="mb-1 text-2xl font-bold">Vulnerability Diff</h1>
      <p className="mb-6 text-sm text-muted-foreground">
        Comparing job <code className="text-xs">{id}</code> against baseline{' '}
        <code className="text-xs">{baseline}</code>
      </p>

      <div className="mb-8 flex flex-wrap gap-4 rounded-lg border bg-muted/40 p-4">
        <div className="text-center min-w-[80px]">
          <div className="text-3xl font-bold text-destructive">{diff.summary.new}</div>
          <div className="mt-1 text-xs text-muted-foreground uppercase">New</div>
        </div>
        <div className="text-center min-w-[80px]">
          <div className="text-3xl font-bold text-green-600 dark:text-green-400">{diff.summary.fixed}</div>
          <div className="mt-1 text-xs text-muted-foreground uppercase">Fixed</div>
        </div>
        <div className="text-center min-w-[80px]">
          <div className="text-3xl font-bold text-muted-foreground">{diff.summary.persisting}</div>
          <div className="mt-1 text-xs text-muted-foreground uppercase">Persisting</div>
        </div>
      </div>

      <Section title="New Findings"       findings={diff.new}        accentClass="text-destructive" />
      <Section title="Fixed Findings"     findings={diff.fixed}      accentClass="text-green-600 dark:text-green-400" />
      <Section title="Persisting Findings" findings={diff.persisting} accentClass="text-muted-foreground" />
    </div>
  );
}

export default function DiffPage() {
  return (
    <Suspense fallback={<PageLoading message="Loading diff…" />}>
      <DiffContent />
    </Suspense>
  );
}
