'use client';

import { useCallback, useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { createSimulation, getFindings, getJob } from '@/lib/api';
import type { Finding, Job } from '@/types';

const SEVERITY_COLOR: Record<string, string> = {
  critical: '#7f1d1d', high: '#92400e', medium: '#78350f', low: '#14532d', info: '#1e3a5f',
};
const SEVERITY_BG: Record<string, string> = {
  critical: '#fee2e2', high: '#fef3c7', medium: '#fef9c3', low: '#dcfce7', info: '#dbeafe',
};

function Badge({ severity }: { severity: string }) {
  return (
    <span style={{
      display: 'inline-block', padding: '2px 8px', borderRadius: 4, fontSize: '0.75rem',
      fontWeight: 700, background: SEVERITY_BG[severity] ?? '#eee', color: SEVERITY_COLOR[severity] ?? '#333',
    }}>
      {severity.toUpperCase()}
    </span>
  );
}

function StatusDot({ status }: { status: string }) {
  const color = { pending: '#f59e0b', running: '#3b82f6', completed: '#22c55e', failed: '#ef4444', cancelled: '#6b7280' }[status] ?? '#ccc';
  return <span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: '50%', background: color, marginRight: 6 }} />;
}

export default function JobPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [job, setJob] = useState<Job | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(true);
  const [simLoading, setSimLoading] = useState<string | null>(null);
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

  useEffect(() => {
    loadJob();
  }, [loadJob]);

  // Poll while pending/running
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

  if (loading) return <p>Loading…</p>;
  if (error) return <p style={{ color: 'red' }}>Error: {error}</p>;
  if (!job) return <p>Job not found</p>;

  const CARD = { background: '#fff', borderRadius: 8, padding: '1.5rem', boxShadow: '0 1px 4px rgba(0,0,0,.08)', marginBottom: '1.5rem' } as const;

  return (
    <div>
      <button onClick={() => router.push('/')} style={{ border: 'none', background: 'none', cursor: 'pointer', color: '#2563eb', fontSize: '0.9rem', padding: 0, marginBottom: '1rem' }}>
        ← Back
      </button>
      <h1 style={{ marginTop: 0 }}>Job Status</h1>

      <div style={CARD}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', fontSize: '0.9rem' }}>
          <div><strong>Job ID:</strong> <code style={{ fontSize: '0.8rem' }}>{job.id}</code></div>
          <div><strong>Status:</strong> <StatusDot status={job.status} />{job.status}</div>
          <div><strong>Tools:</strong> {job.tools.join(', ')}</div>
          <div><strong>Progress:</strong> {job.progress}%</div>
          {job.started_at && <div><strong>Started:</strong> {new Date(job.started_at).toLocaleString()}</div>}
          {job.finished_at && <div><strong>Finished:</strong> {new Date(job.finished_at).toLocaleString()}</div>}
          {job.error && <div style={{ gridColumn: '1/-1', color: '#ef4444' }}><strong>Error:</strong> {job.error}</div>}
        </div>

        {(job.status === 'pending' || job.status === 'running') && (
          <div style={{ marginTop: '1rem', background: '#f0f9ff', padding: '0.75rem', borderRadius: 4, color: '#1d4ed8' }}>
            Analysis in progress… page auto-refreshes every 3s.
          </div>
        )}
      </div>

      {job.status === 'completed' && (
        <>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h2 style={{ margin: 0 }}>Findings ({findings.length})</h2>
            <button
              onClick={() => router.push(`/reports/${id}`)}
              style={{ padding: '0.5rem 1.2rem', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600 }}
            >
              View Report
            </button>
          </div>

          {findings.length === 0 && (
            <div style={CARD}><p style={{ margin: 0, color: '#22c55e' }}>✓ No findings — contract looks clean!</p></div>
          )}

          {findings.map(f => (
            <div key={f.id} style={{ ...CARD, borderLeft: `4px solid ${SEVERITY_COLOR[f.severity] ?? '#ccc'}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.5rem' }}>
                <div>
                  <Badge severity={f.severity} />
                  {' '}
                  <strong style={{ fontSize: '1rem' }}>{f.title}</strong>
                </div>
                <button
                  onClick={() => runSimulation(f)}
                  disabled={simLoading === f.id}
                  style={{ padding: '0.35rem 0.9rem', background: simLoading === f.id ? '#aaa' : '#7c3aed', color: '#fff', border: 'none', borderRadius: 5, cursor: 'pointer', fontSize: '0.8rem' }}
                >
                  {simLoading === f.id ? 'Queuing…' : 'Simulate Exploit'}
                </button>
              </div>
              <div style={{ fontSize: '0.8rem', color: '#555', marginTop: 4 }}>
                Tool: {f.tool} | Type: {f.vulnerability_type} | Confidence: {Math.round(f.confidence * 100)}%
                {f.location && ` | ${f.location}`}
              </div>
              <p style={{ margin: '0.5rem 0 0', fontSize: '0.9rem' }}>{f.description}</p>
            </div>
          ))}
        </>
      )}
    </div>
  );
}
