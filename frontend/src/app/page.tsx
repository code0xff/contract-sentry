'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { analyzeContract, createContract } from '@/lib/api';
import type { ContractLanguage } from '@/types';

const CARD = { background: '#fff', borderRadius: 8, padding: '1.5rem', boxShadow: '0 1px 4px rgba(0,0,0,.08)', marginBottom: '1.5rem' } as const;
const BTN = { padding: '0.6rem 1.4rem', borderRadius: 6, border: 'none', cursor: 'pointer', fontWeight: 600, fontSize: '0.95rem' } as const;

export default function HomePage() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [language, setLanguage] = useState<ContractLanguage>('solidity');
  const [source, setSource] = useState('');
  const [bytecode, setBytecode] = useState('');
  const [tools, setTools] = useState<string[]>(['slither', 'mythril']);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleTool = (t: string) =>
    setTools(prev => prev.includes(t) ? prev.filter(x => x !== t) : [...prev, t]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!name.trim()) { setError('Contract name is required'); return; }
    if (language !== 'bytecode' && !source.trim()) { setError('Source code is required'); return; }
    if (language === 'bytecode' && !bytecode.trim()) { setError('Bytecode is required'); return; }

    setLoading(true);
    try {
      const contract = await createContract({
        name: name.trim(),
        language,
        source: source.trim() || undefined,
        bytecode: bytecode.trim() || undefined,
      });
      const job = await analyzeContract(contract.id, tools);
      router.push(`/jobs/${job.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Submission failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Submit Contract for Analysis</h1>

      <div style={CARD}>
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', fontWeight: 600, marginBottom: 4 }}>Contract Name</label>
            <input
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="MyContract.sol"
              style={{ width: '100%', padding: '0.5rem', borderRadius: 4, border: '1px solid #ccc', boxSizing: 'border-box' }}
            />
          </div>

          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', fontWeight: 600, marginBottom: 4 }}>Language</label>
            <select
              value={language}
              onChange={e => setLanguage(e.target.value as ContractLanguage)}
              style={{ padding: '0.5rem', borderRadius: 4, border: '1px solid #ccc' }}
            >
              <option value="solidity">Solidity</option>
              <option value="bytecode">Bytecode only</option>
            </select>
          </div>

          {language !== 'bytecode' && (
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', fontWeight: 600, marginBottom: 4 }}>Source Code</label>
              <textarea
                value={source}
                onChange={e => setSource(e.target.value)}
                placeholder={'// SPDX-License-Identifier: MIT\npragma solidity ^0.8.20;\ncontract MyContract { ... }'}
                rows={12}
                style={{ width: '100%', padding: '0.5rem', borderRadius: 4, border: '1px solid #ccc', fontFamily: 'monospace', fontSize: '0.85rem', boxSizing: 'border-box' }}
              />
            </div>
          )}

          {language === 'bytecode' && (
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', fontWeight: 600, marginBottom: 4 }}>Bytecode (0x...)</label>
              <input
                value={bytecode}
                onChange={e => setBytecode(e.target.value)}
                placeholder="0x608060..."
                style={{ width: '100%', padding: '0.5rem', borderRadius: 4, border: '1px solid #ccc', fontFamily: 'monospace', boxSizing: 'border-box' }}
              />
            </div>
          )}

          <div style={{ marginBottom: '1.2rem' }}>
            <label style={{ display: 'block', fontWeight: 600, marginBottom: 6 }}>Analysis Tools</label>
            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
              {['slither', 'mythril', 'echidna'].map(t => (
                <label key={t} style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
                  <input type="checkbox" checked={tools.includes(t)} onChange={() => toggleTool(t)} />
                  {t.charAt(0).toUpperCase() + t.slice(1)}
                </label>
              ))}
            </div>
          </div>

          {error && <p style={{ color: '#c0392b', background: '#fdecea', padding: '0.5rem 0.75rem', borderRadius: 4 }}>{error}</p>}

          <button type="submit" disabled={loading} style={{ ...BTN, background: loading ? '#aaa' : '#2563eb', color: '#fff' }}>
            {loading ? 'Submitting…' : 'Analyze Contract'}
          </button>
        </form>
      </div>

      <p style={{ color: '#666', fontSize: '0.85rem' }}>
        Results are processed asynchronously. You will be redirected to the job status page.
      </p>
    </div>
  );
}
