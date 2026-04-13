'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getReport, getReportMarkdown } from '@/lib/api';
import type { Report } from '@/types';

const SEVERITY_COLOR: Record<string, string> = {
  critical: '#ef4444', high: '#f97316', medium: '#eab308', low: '#22c55e', info: '#3b82f6',
};

export default function ReportPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [report, setReport] = useState<Report | null>(null);
  const [markdown, setMarkdown] = useState<string>('');
  const [tab, setTab] = useState<'summary' | 'markdown'>('summary');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getReport(id), getReportMarkdown(id)])
      .then(([r, md]) => { setReport(r); setMarkdown(md); })
      .catch(err => setError(err instanceof Error ? err.message : 'Failed to load'))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <p>Loading report…</p>;
  if (error) return <p style={{ color: 'red' }}>Error: {error}</p>;
  if (!report) return <p>Report not found</p>;

  const { summary } = report;
  const CARD = { background: '#fff', borderRadius: 8, padding: '1.5rem', boxShadow: '0 1px 4px rgba(0,0,0,.08)', marginBottom: '1.5rem' } as const;
  const TAB = (active: boolean) => ({
    padding: '0.5rem 1.2rem', border: 'none', cursor: 'pointer', borderRadius: '6px 6px 0 0',
    background: active ? '#fff' : '#e5e7eb', fontWeight: active ? 700 : 400, borderBottom: active ? '2px solid #2563eb' : 'none',
  } as const);

  return (
    <div>
      <button onClick={() => router.back()} style={{ border: 'none', background: 'none', cursor: 'pointer', color: '#2563eb', fontSize: '0.9rem', padding: 0, marginBottom: '1rem' }}>
        ← Back
      </button>
      <h1 style={{ marginTop: 0 }}>Security Report</h1>
      <p style={{ color: '#555', fontSize: '0.85rem' }}>Job: <code>{id}</code> · Generated: {new Date(report.created_at).toLocaleString()}</p>

      <div style={CARD}>
        <h2 style={{ marginTop: 0 }}>Summary</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '0.75rem', marginBottom: '1rem' }}>
          {['critical', 'high', 'medium', 'low', 'info'].map(sev => (
            <div key={sev} style={{ background: '#f9fafb', borderRadius: 6, padding: '0.75rem', textAlign: 'center', borderTop: `3px solid ${SEVERITY_COLOR[sev]}` }}>
              <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{summary.by_severity?.[sev] ?? 0}</div>
              <div style={{ fontSize: '0.75rem', color: '#555', textTransform: 'uppercase' }}>{sev}</div>
            </div>
          ))}
        </div>
        <p style={{ margin: 0 }}>
          <strong>Total findings:</strong> {summary.total}
          {summary.composite_severity && <> · <strong>Composite severity:</strong> <span style={{ color: SEVERITY_COLOR[summary.composite_severity] ?? '#333' }}>{summary.composite_severity.toUpperCase()}</span></>}
        </p>
      </div>

      <div style={{ display: 'flex', gap: 4, marginBottom: 0 }}>
        <button style={TAB(tab === 'summary')} onClick={() => setTab('summary')}>Overview</button>
        <button style={TAB(tab === 'markdown')} onClick={() => setTab('markdown')}>Full Report</button>
        <a
          href={`/api/v1/reports/${id}/html`}
          target="_blank"
          rel="noopener noreferrer"
          style={{ ...TAB(false), textDecoration: 'none', display: 'inline-flex', alignItems: 'center' }}
        >
          HTML ↗
        </a>
      </div>

      <div style={{ ...CARD, borderRadius: '0 8px 8px 8px' }}>
        {tab === 'summary' && (
          <div>
            <p style={{ margin: '0 0 1rem', color: '#555' }}>
              This report summarises all findings from static analysis, dynamic fuzzing, and exploit simulation.
              Switch to <strong>Full Report</strong> for remediation guidance.
            </p>
            {report.status !== 'ready' && (
              <p style={{ color: '#f59e0b' }}>⚠ Report is still being generated. Refresh shortly.</p>
            )}
          </div>
        )}
        {tab === 'markdown' && (
          <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.85rem', overflowX: 'auto' }}>
            {markdown || 'No content yet.'}
          </pre>
        )}
      </div>
    </div>
  );
}
