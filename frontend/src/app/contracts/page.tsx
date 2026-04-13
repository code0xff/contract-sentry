'use client';

import { useEffect, useState } from 'react';
import { listContracts } from '@/lib/api';
import type { Contract } from '@/types';

const LANG_COLOR: Record<string, string> = {
  solidity: '#3b82f6',
  vyper: '#8b5cf6',
  bytecode: '#6b7280',
};

export default function ContractListPage() {
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listContracts()
      .then(setContracts)
      .catch(e => setError(e instanceof Error ? e.message : 'Failed to load'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1 style={{ margin: 0 }}>Contracts</h1>
        <a
          href="/"
          style={{ padding: '0.5rem 1.2rem', background: '#2563eb', color: '#fff', borderRadius: 6, textDecoration: 'none', fontWeight: 600, fontSize: '0.9rem' }}
        >
          + New Analysis
        </a>
      </div>

      {loading && <p style={{ color: '#6b7280' }}>Loading…</p>}
      {error && <p style={{ color: '#ef4444', background: '#fef2f2', padding: '0.75rem', borderRadius: 6 }}>Error: {error}</p>}

      {!loading && !error && contracts.length === 0 && (
        <div style={{ background: '#fff', borderRadius: 8, padding: '3rem', textAlign: 'center', boxShadow: '0 1px 4px rgba(0,0,0,.08)' }}>
          <p style={{ margin: 0, color: '#6b7280' }}>No contracts yet. <a href="/" style={{ color: '#2563eb' }}>Upload your first contract</a>.</p>
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {contracts.map(c => (
          <a
            key={c.id}
            href={`/contracts/${c.id}`}
            style={{ display: 'block', background: '#fff', borderRadius: 8, padding: '1.25rem 1.5rem', boxShadow: '0 1px 4px rgba(0,0,0,.08)', textDecoration: 'none', color: 'inherit' }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
              <div>
                <span style={{ fontWeight: 600, fontSize: '1rem' }}>{c.name}</span>
                {c.compiler_version && (
                  <span style={{ marginLeft: 8, fontSize: '0.8rem', color: '#6b7280' }}>{c.compiler_version}</span>
                )}
              </div>
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <span style={{
                  padding: '2px 8px', borderRadius: 4, fontSize: '0.75rem', fontWeight: 600,
                  background: `${LANG_COLOR[c.language] ?? '#6b7280'}22`,
                  color: LANG_COLOR[c.language] ?? '#6b7280',
                }}>
                  {c.language}
                </span>
                <span style={{ fontSize: '0.8rem', color: '#9ca3af' }}>
                  {new Date(c.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}
