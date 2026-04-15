'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { listCampaigns } from '@/lib/api';
import type { AttackCampaignListItem, CampaignStatus } from '@/types';
import { PageError, PageLoading } from '@/components/page-state';
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

function passCount(results: Record<string, 'pass' | 'fail'> | null) {
  if (!results) return null;
  const vals = Object.values(results);
  return { pass: vals.filter(v => v === 'pass').length, total: vals.length };
}

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<AttackCampaignListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function load() {
    setLoading(true);
    setError(null);
    listCampaigns()
      .then(setCampaigns)
      .catch(e => setError(e instanceof Error ? e.message : 'Failed to load'))
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, []);

  if (loading) return <PageLoading message="Loading campaigns…" />;
  if (error) return <PageError error={error} onRetry={load} />;

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold">Attack Campaigns</h1>

      {campaigns.length === 0 ? (
        <p className="text-sm text-muted-foreground">No campaigns yet. Run one from a completed analysis job.</p>
      ) : (
        <div className="space-y-3">
          {campaigns.map(c => {
            const pc = passCount(c.results);
            return (
              <Link key={c.id} href={`/campaigns/${c.id}`}>
                <Card className="cursor-pointer transition-colors hover:bg-accent/40">
                  <CardHeader className="pb-2 pt-4">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base font-semibold">
                        {c.contract_name ?? 'Unknown Contract'}
                      </CardTitle>
                      <span className={cn('rounded px-2 py-0.5 text-xs font-semibold', CAMPAIGN_STATUS_BADGE[c.status])}>
                        {c.status}
                      </span>
                    </div>
                  </CardHeader>
                  <CardContent className="pb-4 text-xs text-muted-foreground space-y-0.5">
                    <div>Job: <code>{c.job_id}</code></div>
                    {c.tools && <div>Tools: {c.tools.join(', ')}</div>}
                    {pc && (
                      <div>
                        Tests:{' '}
                        <span className="text-green-600 dark:text-green-400 font-medium">{pc.pass} pass</span>
                        {' / '}
                        <span className="text-red-600 dark:text-red-400 font-medium">{pc.total - pc.pass} fail</span>
                        {' '}of {pc.total}
                      </div>
                    )}
                    {c.error && <div className="text-red-500">Error: {c.error.slice(0, 80)}</div>}
                    <div>Started: {new Date(c.created_at).toLocaleString()}</div>
                    {c.finished_at && <div>Finished: {new Date(c.finished_at).toLocaleString()}</div>}
                  </CardContent>
                </Card>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
