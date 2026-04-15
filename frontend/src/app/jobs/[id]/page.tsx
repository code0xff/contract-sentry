'use client';

import { useCallback, useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { generateAiReport, getCampaign, getFindings, getJob, getJobReport, triggerCampaign } from '@/lib/api';
import type { AttackCampaign, CampaignStatus, Finding, Job, ToolExecutionStatus } from '@/types';
import { PageError, PageLoading } from '@/components/page-state';
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

const CAMPAIGN_STATUS_BADGE: Record<CampaignStatus, string> = {
  queued:    'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
  planning:  'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  running:   'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  succeeded: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
  partial:   'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
  failed:    'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  timed_out: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400',
};

const CAMPAIGN_ACTIVE: CampaignStatus[] = ['queued', 'planning', 'running'];

const STATUS_DOT: Record<string, string> = {
  pending:   'bg-amber-500',
  running:   'bg-blue-500 animate-pulse',
  completed: 'bg-green-500',
  failed:    'bg-red-500',
  cancelled: 'bg-gray-400',
};

const TOOL_STATUS_BADGE: Record<'ok' | 'failed' | 'skipped', string> = {
  ok: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
  failed: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  skipped: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400',
};

function normalizeToolStatus(value: string | ToolExecutionStatus) {
  if (typeof value === 'string') {
    return {
      status: 'failed' as const,
      summary: value,
      detail: null,
      stage: null,
      command: null,
      returncode: null,
      timed_out: false,
      stdout_tail: null,
      stderr_tail: null,
    };
  }
  return value;
}

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
  const [baselineInput, setBaselineInput] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [aiReportLoading, setAiReportLoading] = useState(false);
  const [campaign, setCampaign] = useState<AttackCampaign | null>(null);
  const [campaignLoading, setCampaignLoading] = useState(false);

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

  // Load existing campaign when job completes
  useEffect(() => {
    if (job?.status === 'completed') {
      getCampaign(id).then(setCampaign).catch(() => {/* no campaign yet */});
    }
  }, [id, job?.status]);

  // Poll campaign while active
  useEffect(() => {
    if (!campaign || !CAMPAIGN_ACTIVE.includes(campaign.status)) return;
    const t = setInterval(() => {
      getCampaign(id).then(setCampaign).catch(() => undefined);
    }, 3000);
    return () => clearInterval(t);
  }, [campaign, id]);

  async function runCampaign() {
    setCampaignLoading(true);
    try {
      const c = await triggerCampaign(id);
      setCampaign(c);
      toast.success('Attack campaign queued');
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to start campaign');
    } finally {
      setCampaignLoading(false);
    }
  }

  async function viewReport() {
    try {
      const report = await getJobReport(id);
      router.push(`/reports/${report.id}`);
    } catch {
      toast.error('Report is not ready yet — please try again in a moment.');
    }
  }

  async function downloadAiReport() {
    setAiReportLoading(true);
    try {
      const { markdown } = await generateAiReport(id);
      const blob = new Blob([markdown], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit-report-${id}.md`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('AI report downloaded');
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to generate AI report');
    } finally {
      setAiReportLoading(false);
    }
  }

  if (loading) return <PageLoading />;
  if (error)   return <PageError error={error} onRetry={() => { setLoading(true); setError(null); loadJob(); }} />;
  if (!job)    return <PageError error="Job not found" />;

  const isActive = job.status === 'pending' || job.status === 'running';
  const toolStatuses = job.tool_errors
    ? Object.entries(job.tool_errors).map(([tool, value]) => ({ tool, status: normalizeToolStatus(value) }))
    : [];
  const failedTools = toolStatuses.filter(({ status }) => status.status === 'failed');
  const skippedTools = toolStatuses.filter(({ status }) => status.status === 'skipped');
  const hasFailedTools = failedTools.length > 0;
  const hasSkippedTools = skippedTools.length > 0;
  const allToolsFailed = toolStatuses.length > 0 && failedTools.length === toolStatuses.length;

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
            {job.entry_files && job.entry_files.length > 0 && (
              <div>
                <p className="text-xs text-muted-foreground">Analyzed Files</p>
                <ul className="mt-0.5 space-y-0.5">
                  {job.entry_files.map(f => (
                    <li key={f} className="font-mono text-xs">{f}</li>
                  ))}
                </ul>
              </div>
            )}
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
              <div className="col-span-2">
                <p className="text-xs text-muted-foreground mb-1">Error</p>
                <p className="text-sm text-destructive">{job.error}</p>
              </div>
            )}
          </div>

          {isActive && (
            <div className="mt-4 rounded-md border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-700 dark:border-blue-800 dark:bg-blue-950/30 dark:text-blue-400">
              Analysis in progress… page auto-refreshes every 3s.
            </div>
          )}

          {!isActive && hasFailedTools && (
            <div className={cn(
              "mt-4 rounded-md border px-4 py-3 text-sm",
              job.status === 'failed'
                ? 'border-red-300 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-950/30 dark:text-red-400'
                : 'border-yellow-300 bg-yellow-50 text-yellow-800 dark:border-yellow-800 dark:bg-yellow-950/30 dark:text-yellow-400'
            )}>
              {job.status === 'failed'
                ? 'All selected analysis tools failed.'
                : 'Some analysis tools failed. Findings and reports may be incomplete.'}
            </div>
          )}
        </CardContent>
      </Card>

      {toolStatuses.length > 0 && (
        <Card className="mb-6">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Tool Execution</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {toolStatuses.map(({ tool, status }) => (
              <div key={tool} className="rounded-md border p-3">
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-semibold">{tool}</span>
                    <span className={cn('rounded px-2 py-0.5 text-xs font-semibold', TOOL_STATUS_BADGE[status.status])}>
                      {status.status}
                    </span>
                  </div>
                  {status.timed_out && (
                    <span className="text-xs text-destructive">timed out</span>
                  )}
                </div>
                <p className="text-sm">{status.summary}</p>
                {status.detail && (
                  <p className="mt-1 whitespace-pre-wrap break-words font-mono text-xs text-muted-foreground">{status.detail}</p>
                )}
                <div className="mt-2 grid gap-2 text-xs text-muted-foreground md:grid-cols-2">
                  {status.stage && <div>Stage: {status.stage}</div>}
                  {status.returncode !== null && <div>Return code: {status.returncode}</div>}
                  {status.command && (
                    <div className="md:col-span-2 break-all">
                      Command: <code>{status.command}</code>
                    </div>
                  )}
                  {status.stderr_tail && (
                    <div className="md:col-span-2">
                      <p className="mb-1">stderr</p>
                      <pre className="overflow-x-auto rounded bg-muted/50 p-2 whitespace-pre-wrap">{status.stderr_tail}</pre>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {job.status === 'completed' && (
        <>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold">Findings ({findings.length})</h2>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={runCampaign}
                disabled={campaignLoading || (!!campaign && CAMPAIGN_ACTIVE.includes(campaign.status))}
              >
                {campaignLoading || (campaign && CAMPAIGN_ACTIVE.includes(campaign.status))
                  ? 'Campaign running…'
                  : campaign
                  ? 'Re-run Campaign'
                  : 'Run Attack Campaign'}
              </Button>
              <Button size="sm" variant="outline" onClick={downloadAiReport} disabled={aiReportLoading}>
                {aiReportLoading ? 'Generating…' : 'Generate AI Report'}
              </Button>
              <Button size="sm" onClick={viewReport}>
                View Report
              </Button>
            </div>
          </div>

          {findings.length === 0 && !hasFailedTools && !hasSkippedTools && (
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
                  <div className="mb-2 flex flex-wrap items-center gap-2">
                    <SeverityBadge severity={f.severity} />
                    <strong className="text-sm">{f.title}</strong>
                  </div>
                  <p className="mb-2 text-xs text-muted-foreground">
                    Tool: {f.tool} · Type: {f.vulnerability_type} · Confidence: {Math.round(f.confidence * 100)}%
                    {f.location && ` · ${f.location}`}
                  </p>
                  <p className="text-sm">{f.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>

          {campaign && (
            <Card className="mb-6">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center justify-between text-sm">
                  <span>Attack Campaign</span>
                  <span className={cn('rounded px-2 py-0.5 text-xs font-semibold', CAMPAIGN_STATUS_BADGE[campaign.status])}>
                    {campaign.status}
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {CAMPAIGN_ACTIVE.includes(campaign.status) && (
                  <p className={cn('text-sm', campaign.status === 'queued' ? 'text-muted-foreground' : 'text-blue-600 dark:text-blue-400')}>
                    {campaign.status === 'queued' && 'Queued — waiting for worker…'}
                    {campaign.status === 'planning' && 'AI is designing attack scenarios…'}
                    {campaign.status === 'running' && 'Running forge test -vvv…'}
                  </p>
                )}

                {campaign.results && Object.keys(campaign.results).length > 0 && (
                  <div>
                    <p className="mb-1.5 text-xs font-semibold">Test Results</p>
                    <div className="flex flex-col gap-1">
                      {Object.entries(campaign.results).map(([name, result]) => (
                        <div
                          key={name}
                          className={cn(
                            'flex items-center gap-2 rounded px-2 py-1 font-mono text-xs',
                            result === 'pass'
                              ? 'bg-green-50 text-green-800 dark:bg-green-900/20 dark:text-green-400'
                              : 'bg-red-50 text-red-800 dark:bg-red-900/20 dark:text-red-400',
                          )}
                        >
                          <span>{result === 'pass' ? '✓' : '✗'}</span>
                          <span>{name}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {campaign.attack_plan && (
                  <details>
                    <summary className="cursor-pointer text-xs font-semibold">Attack Plan</summary>
                    <pre className="mt-2 whitespace-pre-wrap break-words text-xs text-muted-foreground">
                      {campaign.attack_plan}
                    </pre>
                  </details>
                )}

                {campaign.test_code && (
                  <details>
                    <summary className="cursor-pointer text-xs font-semibold">Foundry Test Suite</summary>
                    <pre className="mt-2 overflow-x-auto rounded-md bg-zinc-900 p-4 text-xs text-zinc-100 dark:bg-zinc-950">
                      {campaign.test_code}
                    </pre>
                  </details>
                )}

                {campaign.trace && (
                  <details>
                    <summary className="cursor-pointer text-xs font-semibold">Raw Trace</summary>
                    <pre className="mt-2 overflow-x-auto whitespace-pre-wrap break-words text-xs text-muted-foreground">
                      {campaign.trace}
                    </pre>
                  </details>
                )}

                {campaign.error && (
                  <p className="text-xs text-destructive">{campaign.error}</p>
                )}
              </CardContent>
            </Card>
          )}

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
