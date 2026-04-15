'use client';

import { useCallback, useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { createSimulation, generatePoc, getFindings, getJob, getJobReport } from '@/lib/api';
import type { Finding, Job } from '@/types';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';

const SEVERITY_BADGE: Record<string, string> = {
  critical: 'bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800',
  high:     'bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-900/30 dark:text-orange-400 dark:border-orange-800',
  medium:   'bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-400 dark:border-yellow-800',
  low:      'bg-green-100 text-green-700 border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-800',
  info:     'bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800',
};

const SEVERITY_BORDER_L: Record<string, string> = {
  critical: 'border-l-red-500',
  high:     'border-l-orange-500',
  medium:   'border-l-yellow-500',
  low:      'border-l-green-500',
  info:     'border-l-blue-500',
};

const STATUS_DOT: Record<string, string> = {
  pending:   'bg-amber-500',
  running:   'bg-blue-500 animate-pulse',
  completed: 'bg-green-500',
  failed:    'bg-red-500',
  cancelled: 'bg-gray-400',
};

function SeverityBadge({ severity }: { severity: string }) {
  return (
    <span className={cn(
      "inline-flex items-center rounded border px-2 py-0.5 text-xs font-bold",
      SEVERITY_BADGE[severity] ?? 'bg-secondary text-secondary-foreground border-border'
    )}>
      {severity.toUpperCase()}
    </span>
  );
}

export default function JobPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [job, setJob] = useState<Job | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(true);
  const [simLoading, setSimLoading] = useState<string | null>(null);
  const [pocLoading, setPocLoading] = useState<string | null>(null);
  const [pocCode, setPocCode] = useState<Record<string, string>>({});
  const [baselineInput, setBaselineInput] = useState('');
  const [error, setError] = useState<string | null>(null);

  const loadJob = useCallback(async () => {
    try {
      const j = await getJob(id);
      setJob(j);
      if (j.status === 'completed' || j.status === 'failed') {
        const f = await getFindings(id);
        setFindings(f);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load job');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { loadJob(); }, [loadJob]);

  useEffect(() => {
    if (!job || job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') return;
    const t = setInterval(loadJob, 3000);
    return () => clearInterval(t);
  }, [job, loadJob]);

  async function runSimulation(finding: Finding) {
    setSimLoading(finding.id);
    try {
      const sim = await createSimulation(id, { template: finding.vulnerability_type, finding_id: finding.id });
      alert(`Simulation queued — ID: ${sim.id}\nStatus: ${sim.status}`);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Simulation failed');
    } finally {
      setSimLoading(null);
    }
  }

  async function runGeneratePoc(finding: Finding) {
    setPocLoading(finding.id);
    try {
      const result = await generatePoc(id, finding.id);
      setPocCode(prev => ({ ...prev, [finding.id]: result.poc }));
    } catch (err: unknown) {
      setPocCode(prev => ({ ...prev, [finding.id]: `// Error: ${err instanceof Error ? err.message : 'Unknown error'}` }));
    } finally {
      setPocLoading(null);
    }
  }

  if (loading) return <p className="text-muted-foreground">Loading…</p>;
  if (error)   return <p className="text-destructive">Error: {error}</p>;
  if (!job)    return <p>Job not found</p>;

  const isActive = job.status === 'pending' || job.status === 'running';

  return (
    <div>
      <Button variant="ghost" size="sm" className="-ml-2 mb-4" onClick={() => router.push('/')}>
        ← Back
      </Button>

      <h1 className="mb-4 text-2xl font-bold">Job Status</h1>

      <Card className="mb-6">
        <CardContent className="pt-6">
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-xs text-muted-foreground">Job ID</p>
              <code className="text-xs">{job.id}</code>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Status</p>
              <span className="inline-flex items-center gap-1.5">
                <span className={cn("h-2 w-2 rounded-full", STATUS_DOT[job.status] ?? 'bg-gray-400')} />
                {job.status}
              </span>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Tools</p>
              {job.tools.join(', ')}
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Progress</p>
              {job.progress}%
            </div>
            {job.started_at && (
              <div>
                <p className="text-xs text-muted-foreground">Started</p>
                {new Date(job.started_at).toLocaleString()}
              </div>
            )}
            {job.finished_at && (
              <div>
                <p className="text-xs text-muted-foreground">Finished</p>
                {new Date(job.finished_at).toLocaleString()}
              </div>
            )}
            {job.error && (
              <div className="col-span-2 text-sm text-destructive">{job.error}</div>
            )}
          </div>

          {isActive && (
            <div className="mt-4 rounded-md border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-700 dark:border-blue-800 dark:bg-blue-950/30 dark:text-blue-400">
              Analysis in progress… page auto-refreshes every 3s.
            </div>
          )}
        </CardContent>
      </Card>

      {job.status === 'completed' && (
        <>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold">Findings ({findings.length})</h2>
            <Button
              size="sm"
              onClick={async () => {
                try {
                  const report = await getJobReport(id);
                  router.push(`/reports/${report.id}`);
                } catch {
                  alert('Report not ready yet. Please try again shortly.');
                }
              }}
            >
              View Report
            </Button>
          </div>

          {findings.length === 0 && (
            <Card className="mb-4">
              <CardContent className="py-8 text-center">
                <p className="font-medium text-green-600 dark:text-green-400">
                  ✓ No findings — contract looks clean!
                </p>
              </CardContent>
            </Card>
          )}

          <div className="mb-6 flex flex-col gap-3">
            {findings.map(f => (
              <Card key={f.id} className={cn("border-l-4", SEVERITY_BORDER_L[f.severity] ?? 'border-l-border')}>
                <CardContent className="pt-4">
                  <div className="mb-2 flex flex-wrap items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <SeverityBadge severity={f.severity} />
                      <strong className="text-sm">{f.title}</strong>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={pocLoading === f.id}
                        onClick={() => runGeneratePoc(f)}
                        className="h-7 text-xs"
                      >
                        {pocLoading === f.id ? 'Generating…' : 'Generate PoC'}
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={simLoading === f.id}
                        onClick={() => runSimulation(f)}
                        className="h-7 text-xs"
                      >
                        {simLoading === f.id ? 'Queuing…' : 'Simulate Exploit'}
                      </Button>
                    </div>
                  </div>
                  <p className="mb-2 text-xs text-muted-foreground">
                    Tool: {f.tool} · Type: {f.vulnerability_type} · Confidence: {Math.round(f.confidence * 100)}%
                    {f.location && ` · ${f.location}`}
                  </p>
                  <p className="text-sm">{f.description}</p>
                  {pocCode[f.id] && (
                    <pre className="mt-3 overflow-x-auto whitespace-pre-wrap break-words rounded-md bg-zinc-900 p-4 text-xs text-zinc-100 dark:bg-zinc-950">
                      {pocCode[f.id]}
                    </pre>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Compare with baseline</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                <Input
                  placeholder="Baseline job ID"
                  value={baselineInput}
                  onChange={e => setBaselineInput(e.target.value)}
                  className="min-w-[200px] flex-1"
                />
                <Button
                  size="sm"
                  disabled={!baselineInput.trim()}
                  onClick={() => {
                    if (baselineInput.trim())
                      router.push(`/jobs/${id}/diff?baseline=${encodeURIComponent(baselineInput.trim())}`);
                  }}
                >
                  Compare
                </Button>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
