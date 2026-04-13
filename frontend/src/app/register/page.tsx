'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';

const BASE = process.env.NEXT_PUBLIC_API_URL ?? '';
const CARD = { background: '#fff', borderRadius: 8, padding: '2rem', boxShadow: '0 1px 4px rgba(0,0,0,.08)', maxWidth: 400, margin: '4rem auto' } as const;
const INPUT = { width: '100%', padding: '0.5rem', borderRadius: 4, border: '1px solid #ccc', boxSizing: 'border-box' as const, marginBottom: '1rem' };
const BTN = { width: '100%', padding: '0.6rem', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600 } as const;

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await fetch(`${BASE}/api/v1/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const msg = await res.json().catch(() => ({}));
        setError(msg.detail ?? 'Registration failed');
        return;
      }
      router.push('/login');
    } catch {
      setError('Network error');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={CARD}>
      <h2 style={{ marginTop: 0 }}>Create Account</h2>
      <form onSubmit={handleSubmit}>
        <label style={{ display: 'block', fontWeight: 600, marginBottom: 4 }}>Email</label>
        <input type="email" value={email} onChange={e => setEmail(e.target.value)} style={INPUT} required />
        <label style={{ display: 'block', fontWeight: 600, marginBottom: 4 }}>Password (min 8 chars)</label>
        <input type="password" value={password} onChange={e => setPassword(e.target.value)} style={INPUT} required minLength={8} />
        {error && <p style={{ color: '#ef4444', marginBottom: '0.75rem' }}>{error}</p>}
        <button type="submit" disabled={loading} style={BTN}>{loading ? 'Creating account\u2026' : 'Register'}</button>
      </form>
      <p style={{ textAlign: 'center', marginTop: '1rem', fontSize: '0.9rem' }}>
        Have an account? <a href="/login" style={{ color: '#2563eb' }}>Sign in</a>
      </p>
    </div>
  );
}
