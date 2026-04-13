'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { diffFindings } from '@/lib/api';
import type { Finding, FindingDiff } from '@/types/index';

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

function FindingCard({ finding }: { finding: Finding }) {
  return (
    <div style={{
      background: '#fff', borderRadius: 6, padding: '1rem', marginBottom: '0.75rem',
      boxShadow: '0 1px 3px rgba(0,0,0,.07)',
      borderLeft: `4px solid ${SEVERITY_COLOR[finding.severity] ?? '#ccc'}`,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: 4 }}>
        <Badge severity={finding.severity} />
        <strong style={{ fontSize: '0.95rem' }}>{finding.title}</strong>
      </div>
      <div style={{ fontSize: '0.78rem', color: '#666' }}>
        Type: {finding.vulnerability_type}
        {finding.location && ` | ${finding.location}`}
      </div>
    </div>
  );
}

function Section({
  title,
  findings,
  accentColor,
}: {
  title: string;
  findings: Finding[];
  accentColor: string;
}) {
  return (
    <div style={{ marginBottom: '2rem' }}>
      <h2 style={{ color: accentColor, marginBottom: '0.75rem' }}>
        {title} ({findings.length})
      </h2>
      {findings.length === 0 ? (
        <p style={{ color: '#888', fontStyle: 'italic' }}>None</p>
      ) : (
        findings.map(f => <FindingCard key={f.id} finding={f} />)
      )}
    </div>
  );
}

export default function DiffPage() {
  const { id } = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const baseline = searchParams.get('baseline') ?? '';
  const router = useRouter();

  const [diff, setDiff] = useState<FindingDiff | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!baseline) {
      setError('Missing baseline job ID');
      setLoading(false);
      return;
    }
    diffFindings(id, baseline)
      .then(setDiff)
      .catch(err => setError(err instanceof Error ? err.message : 'Failed to load diff'))
      .finally(() => setLoading(false));
  }, [id, baseline]);

  if (loading) return <p>Loading diff…</p>;
  if (error) return <p style={{ color: 'red' }}>Error: {error}</p>;
  if (!diff) return null;

  return (
    <div>
      <button
        onClick={() => router.push(`/jobs/${id}`)}
        style={{ border: 'none', background: 'none', cursor: 'pointer', color: '#2563eb', fontSize: '0.9rem', padding: 0, marginBottom: '1rem' }}
      >
        ← Back to Job
      </button>

      <h1 style={{ marginTop: 0 }}>Vulnerability Diff</h1>
      <p style={{ color: '#555', marginBottom: '2rem', fontSize: '0.9rem' }}>
        Comparing job <code>{id}</code> against baseline <code>{baseline}</code>
      </p>

      <div style={{
        display: 'flex', gap: '1rem', marginBottom: '2rem', padding: '1rem',
        background: '#f8fafc', borderRadius: 8, flexWrap: 'wrap',
      }}>
        <div style={{ textAlign: 'center', minWidth: 80 }}>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#dc2626' }}>{diff.summary.new}</div>
          <div style={{ fontSize: '0.8rem', color: '#555' }}>New</div>
        </div>
        <div style={{ textAlign: 'center', minWidth: 80 }}>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#16a34a' }}>{diff.summary.fixed}</div>
          <div style={{ fontSize: '0.8rem', color: '#555' }}>Fixed</div>
        </div>
        <div style={{ textAlign: 'center', minWidth: 80 }}>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#6b7280' }}>{diff.summary.persisting}</div>
          <div style={{ fontSize: '0.8rem', color: '#555' }}>Persisting</div>
        </div>
      </div>

      <Section title="New Findings" findings={diff.new} accentColor="#dc2626" />
      <Section title="Fixed Findings" findings={diff.fixed} accentColor="#16a34a" />
      <Section title="Persisting Findings" findings={diff.persisting} accentColor="#6b7280" />
    </div>
  );
}
