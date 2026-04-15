'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { Trash2 } from 'lucide-react';
import { useParams, useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { analyzeContract, deleteContract, deleteJob, getContract, listContractJobs } from '@/lib/api';
import type { Contract, Job } from '@/types';
import { PageError, PageLoading } from '@/components/page-state';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';

const STATUS_CLASSES: Record<string, string> = {
  pending:   'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  running:   'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  completed: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  failed:    'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  cancelled: 'bg-secondary text-secondary-foreground',
};

const STATUS_DOT: Record<string, string> = {
  pending:   'bg-amber-500',
  running:   'bg-blue-500 animate-pulse',
  completed: 'bg-green-500',
  failed:    'bg-red-500',
  cancelled: 'bg-gray-400',
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={cn(
      "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium",
      STATUS_CLASSES[status] ?? 'bg-secondary text-secondary-foreground'
    )}>
      <span className={cn("h-1.5 w-1.5 rounded-full", STATUS_DOT[status] ?? 'bg-gray-400')} />
      {status}
    </span>
  );
}

const TOOLS = ['slither', 'mythril', 'echidna'];

export default function ContractDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [contract, setContract] = useState<Contract | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [selectedTools, setSelectedTools] = useState<string[]>(['slither', 'mythril']);
  const [deletingJob, setDeletingJob] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [c, js] = await Promise.all([getContract(id), listContractJobs(id)]);
      setContract(c); setJobs(js);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load contract');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const hasActive = jobs.some(j => j.status === 'pending' || j.status === 'running');
    if (!hasActive) return;
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, [jobs, load]);

  const toggleTool = (t: string) =>
    setSelectedTools(prev => prev.includes(t) ? prev.filter(x => x !== t) : [...prev, t]);

  async function handleDeleteContract() {
    if (!contract) return;
    if (!confirm(`Delete "${contract.name}" and all its analyses? This cannot be undone.`)) return;
    try {
      await deleteContract(contract.id);
      toast.success(`"${contract.name}" deleted`);
      router.push('/contracts');
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Delete failed');
    }
  }

  async function handleDeleteJob(e: React.MouseEvent, jobId: string) {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm('Delete this analysis job and all its findings? This cannot be undone.')) return;
    setDeletingJob(jobId);
    try {
      await deleteJob(jobId);
      setJobs(prev => prev.filter(j => j.id !== jobId));
      toast.success('Job deleted');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Delete failed');
    } finally {
      setDeletingJob(null);
    }
  }

  async function startAnalysis() {
    if (!contract || selectedTools.length === 0) return;
    setAnalyzing(true);
    try {
      const job = await analyzeContract(contract.id, selectedTools);
      router.push(`/jobs/${job.id}`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to start analysis');
      setAnalyzing(false);
    }
  }

  if (loading) return <PageLoading />;
  if (error)   return <PageError error={error} onRetry={() => { setLoading(true); setError(null); load(); }} />;
  if (!contract) return <PageError error="Contract not found" />;

  const activeJob = jobs.find(j => j.status === 'pending' || j.status === 'running');

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <Button variant="ghost" size="sm" className="-ml-2" onClick={() => router.push('/contracts')}>
          ← Contracts
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className="text-muted-foreground hover:text-destructive"
          onClick={handleDeleteContract}
          title="Delete contract"
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>

      <Card className="mb-6">
        <CardContent className="pt-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h1 className="mb-1 text-xl font-bold">{contract.name}</h1>
              <p className="text-sm text-muted-foreground">
                {contract.language}
                {contract.compiler_version ? ` · ${contract.compiler_version}` : ''}
                {' · Added '}{new Date(contract.created_at).toLocaleDateString()}
              </p>
            </div>
            <div className="flex flex-col items-end gap-2">
              <div className="flex flex-wrap gap-3">
                {TOOLS.map(t => (
                  <label key={t} className="flex cursor-pointer items-center gap-1.5 text-sm">
                    <input
                      type="checkbox"
                      checked={selectedTools.includes(t)}
                      onChange={() => toggleTool(t)}
                      disabled={!!activeJob}
                      className="rounded"
                    />
                    <span className="capitalize">{t}</span>
                  </label>
                ))}
              </div>
              <Button
                onClick={startAnalysis}
                disabled={analyzing || !!activeJob || selectedTools.length === 0}
                size="sm"
              >
                {activeJob ? 'Analysis running…' : analyzing ? 'Starting…' : 'Run Analysis'}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <h2 className="mb-3 text-lg font-semibold">Analysis History ({jobs.length})</h2>

      {jobs.length === 0 && (
        <Card>
          <CardContent className="py-8 text-center text-sm text-muted-foreground">
            No analyses yet. Run your first analysis above.
          </CardContent>
        </Card>
      )}

      <div className="flex flex-col gap-2">
        {jobs.map(job => (
          <Link key={job.id} href={`/jobs/${job.id}`} className="group block no-underline">
            <Card className="cursor-pointer transition-colors hover:bg-accent/50">
              <CardContent className="px-5 py-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <StatusBadge status={job.status} />
                    <span className="text-sm text-muted-foreground">{job.tools.join(', ')}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="text-right text-xs text-muted-foreground">
                      {job.status === 'running' && (
                        <span className="mr-3 font-medium text-blue-500">{job.progress}%</span>
                      )}
                      {new Date(job.created_at).toLocaleString()}
                    </div>
                    <button
                      onClick={e => handleDeleteJob(e, job.id)}
                      disabled={deletingJob === job.id}
                      className="rounded p-1 text-muted-foreground opacity-0 transition-opacity hover:bg-destructive/10 hover:text-destructive group-hover:opacity-100 disabled:opacity-40"
                      title="Delete job"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
                {job.error && (
                  <p className="mt-2 text-sm text-destructive">
                    Analysis failed: {job.error}
                  </p>
                )}
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
