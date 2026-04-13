import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Contract-Centry',
  description: 'EVM smart contract security testing platform',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, fontFamily: 'system-ui, sans-serif', background: '#f5f7fa', color: '#222' }}>
        <nav style={{ background: '#1a1a2e', color: '#fff', padding: '0.75rem 1.5rem', display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
          <a href="/" style={{ color: '#7eb8f7', textDecoration: 'none', fontWeight: 700, fontSize: '1.1rem' }}>
            Contract-Centry
          </a>
          <a href="/" style={{ color: '#ccc', textDecoration: 'none', fontSize: '0.9rem' }}>New Analysis</a>
          <a href="/contracts" style={{ color: '#ccc', textDecoration: 'none', fontSize: '0.9rem' }}>Contracts</a>
        </nav>
        <main style={{ maxWidth: 960, margin: '0 auto', padding: '2rem 1rem' }}>
          {children}
        </main>
      </body>
    </html>
  );
}
