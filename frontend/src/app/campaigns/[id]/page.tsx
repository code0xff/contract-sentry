'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getCampaignById } from '@/lib/api';
import type { AttackCampaignListItem, CampaignStatus } from '@/types';
import { PageError, PageLoading } from '@/components/page-state';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

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

export default function CampaignDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [campaign, setCampaign] = useState<AttackCampaignListItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function load() {
    setLoading(true);
    setError(null);
    getCampaignById(id)
      .then(setCampaign)
      .catch(e => setError(e instanceof Error ? e.message : 'Failed to load'))
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, [id]);

  // Poll while active
  useEffect(() => {
    if (!campaign || !CAMPAIGN_ACTIVE.includes(campaign.status)) return;
    const timer = setInterval(() => {
      getCampaignById(id).then(setCampaign).catch(() => {});
    }, 3000);
    return () => clearInterval(timer);
  }, [campaign?.status, id]);

  if (loading) return <PageLoading message="Loading campaign…" />;
  if (error) return <PageError error={error} onRetry={load} />;
  if (!campaign) return <PageError error="Campaign not found" />;

  return (
    <div>
      <Button variant="ghost" size="sm" className="-ml-2 mb-4" onClick={() => router.back()}>
        ← Back
      </Button>

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{campaign.contract_name ?? 'Attack Campaign'}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Job: <code className="text-xs">{campaign.job_id}</code>
            {campaign.tools && <> · Tools: {campaign.tools.join(', ')}</>}
            {' · '}Started: {new Date(campaign.created_at).toLocaleString()}
            {campaign.finished_at && <> · Finished: {new Date(campaign.finished_at).toLocaleString()}</>}
          </p>
        </div>
        <span className={cn('rounded px-3 py-1 text-sm font-semibold', CAMPAIGN_STATUS_BADGE[campaign.status])}>
          {campaign.status}
        </span>
      </div>

      {CAMPAIGN_ACTIVE.includes(campaign.status) && (
        <p className={cn('mb-4 text-sm', campaign.status === 'queued' ? 'text-muted-foreground' : 'text-blue-600 dark:text-blue-400')}>
          {campaign.status === 'queued' && 'Queued — waiting for worker…'}
          {campaign.status === 'planning' && 'AI is designing attack scenarios…'}
          {campaign.status === 'running' && 'Running forge test -vvv…'}
        </p>
      )}

      {campaign.error && (
        <p className="mb-4 text-sm text-destructive">{campaign.error}</p>
      )}

      {campaign.results && Object.keys(campaign.results).length > 0 && (
        <Card className="mb-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Test Results</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col gap-1.5">
              {Object.entries(campaign.results).map(([name, result]) => (
                <div
                  key={name}
                  className={cn(
                    'flex items-center gap-2 rounded px-3 py-1.5 font-mono text-xs',
                    result === 'pass'
                      ? 'bg-green-50 text-green-800 dark:bg-green-900/20 dark:text-green-400'
                      : 'bg-red-50 text-red-800 dark:bg-red-900/20 dark:text-red-400',
                  )}
                >
                  <span className="font-bold">{result === 'pass' ? '✓' : '✗'}</span>
                  <span>{name}</span>
                  <span className="ml-auto uppercase opacity-60">{result}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {campaign.attack_plan && (
        <Card className="mb-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Attack Plan</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="whitespace-pre-wrap break-words text-xs text-muted-foreground leading-relaxed">
              {campaign.attack_plan}
            </pre>
          </CardContent>
        </Card>
      )}

      {campaign.test_code && (
        <Card className="mb-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Foundry Test Suite</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <pre className="overflow-x-auto rounded-b-lg bg-zinc-900 p-4 text-xs text-zinc-100 dark:bg-zinc-950 leading-relaxed">
              {campaign.test_code}
            </pre>
          </CardContent>
        </Card>
      )}

      {campaign.trace && (
        <Card className="mb-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Raw Forge Trace</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="overflow-x-auto whitespace-pre-wrap break-words text-xs text-muted-foreground leading-relaxed">
              {campaign.trace}
            </pre>
          </CardContent>
        </Card>
      )}

      <div className="mt-4 text-right">
        <Button variant="outline" size="sm" asChild>
          <a href={`/jobs/${campaign.job_id}`}>View Analysis Job →</a>
        </Button>
      </div>
    </div>
  );
}
