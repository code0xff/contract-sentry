'use client';

import { useCallback, useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { analyzeContract, getContract, listContractJobs } from '@/lib/api';
import type { Contract, Job } from '@/types';

const STATUS_COLOR: Record<string, string> = {
  pending: '#f59e0b', running: '#3b82f6', completed: '#22c55e', failed: '#ef4444', cancelled: '#6b7280',
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5, padding: '3px 10px',
      borderRadius: 12, fontSize: '0.78rem', fontWeight: 600,
      background: `${STATUS_COLOR[status] ?? '#6b7280'}18`,
      color: STATUS_COLOR[status] ?? '#6b7280',
    }}>
      <span style={{ width: 7, height: 7, borderRadius: '50%', background: STATUS_COLOR[status] ?? '#6b7280', display: 'inline-block' }} />
      {status}
    </span>
  );
}

const CARD = { background: '#fff', borderRadius: 8, padding: '1.5rem', boxShadow: '0 1px 4px rgba(0,0,0,.08)', marginBottom: '1.25rem' } as const;

export default function ContractDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [contract, setContract] = useState<Contract | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [selectedTools, setSelectedTools] = useState<string[]>(['slither', 'mythril']);

  const load = useCallback(async () => {
    try {
      const [c, js] = await Promise.all([getContract(id), listContractJobs(id)]);
      setContract(c);
      setJobs(js);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  // Poll while any job is active
  useEffect(() => {
    const hasActive = jobs.some(j => j.status === 'pending' || j.status === 'running');
    if (!hasActive) return;
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, [jobs, load]);

  const toggleTool = (t: string) =>
    setSelectedTools(prev => prev.includes(t) ? prev.filter(x => x !== t) : [...prev, t]);

  async function startAnalysis() {
    if (!contract || selectedTools.length === 0) return;
    setAnalyzing(true);
    try {
      const job = await analyzeContract(contract.id, selectedTools);
      router.push(`/jobs/${job.id}`);
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Failed to start analysis');
      setAnalyzing(false);
    }
  }

  if (loading) return <p style={{ color: '#6b7280' }}>Loading…</p>;
  if (error) return <p style={{ color: '#ef4444' }}>Error: {error}</p>;
  if (!contract) return <p>Contract not found</p>;

  const activeJob = jobs.find(j => j.status === 'pending' || j.status === 'running');

  return (
    <div>
      <button
        onClick={() => router.push('/contracts')}
        style={{ border: 'none', background: 'none', cursor: 'pointer', color: '#2563eb', fontSize: '0.9rem', padding: 0, marginBottom: '1rem' }}
      >
        ← Contracts
      </button>

      <div style={CARD}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h1 style={{ margin: '0 0 0.25rem' }}>{contract.name}</h1>
            <span style={{ fontSize: '0.85rem', color: '#6b7280' }}>
              {contract.language}{contract.compiler_version ? ` · ${contract.compiler_version}` : ''} · Added {new Date(contract.created_at).toLocaleDateString()}
            </span>
          </div>
          <div>
            <div style={{ marginBottom: '0.5rem', display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
              {['slither', 'mythril', 'echidna'].map(t => (
                <label key={t} style={{ display: 'flex', alignItems: 'center', gap: 5, cursor: 'pointer', fontSize: '0.9rem' }}>
                  <input type="checkbox" checked={selectedTools.includes(t)} onChange={() => toggleTool(t)} disabled={!!activeJob} />
                  {t.charAt(0).toUpperCase() + t.slice(1)}
                </label>
              ))}
            </div>
            <button
              onClick={startAnalysis}
              disabled={analyzing || !!activeJob || selectedTools.length === 0}
              style={{
                padding: '0.5rem 1.2rem', border: 'none', borderRadius: 6, cursor: 'pointer',
                fontWeight: 600, fontSize: '0.9rem', width: '100%',
                background: analyzing || !!activeJob ? '#d1d5db' : '#2563eb',
                color: analyzing || !!activeJob ? '#6b7280' : '#fff',
              }}
            >
              {activeJob ? 'Analysis running…' : analyzing ? 'Starting…' : 'Run Analysis'}
            </button>
          </div>
        </div>
      </div>

      <h2 style={{ margin: '0 0 1rem' }}>Analysis History ({jobs.length})</h2>

      {jobs.length === 0 && (
        <div style={{ ...CARD, textAlign: 'center', color: '#6b7280' }}>
          No analyses yet. Run your first analysis above.
        </div>
      )}

      {jobs.map(job => (
        <a
          key={job.id}
          href={`/jobs/${job.id}`}
          style={{ ...CARD, display: 'block', textDecoration: 'none', color: 'inherit', marginBottom: '0.75rem' }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
            <div>
              <StatusBadge status={job.status} />
              <span style={{ marginLeft: 10, fontSize: '0.85rem', color: '#6b7280' }}>{job.tools.join(', ')}</span>
            </div>
            <div style={{ fontSize: '0.82rem', color: '#9ca3af', textAlign: 'right' }}>
              {job.status === 'running' && <span style={{ marginRight: 10, color: '#3b82f6' }}>{job.progress}%</span>}
              {new Date(job.created_at).toLocaleString()}
            </div>
          </div>
          {job.error && <p style={{ margin: '0.5rem 0 0', fontSize: '0.85rem', color: '#ef4444' }}>{job.error}</p>}
        </a>
      ))}
    </div>
  );
}
