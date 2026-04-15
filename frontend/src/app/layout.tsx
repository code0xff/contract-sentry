import type { Metadata } from 'next';
import Link from 'next/link';
import { Shield } from 'lucide-react';
import { ThemeProvider } from '@/components/theme-provider';
import { ThemeToggle } from '@/components/theme-toggle';
import './globals.css';

export const metadata: Metadata = {
  title: 'Contract Sentry',
  description: 'EVM smart contract security testing platform',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          <div className="min-h-screen bg-background">
            <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
              <div className="mx-auto flex h-14 max-w-5xl items-center px-4">
                <Link href="/" className="mr-6 flex items-center gap-2 font-bold text-foreground">
                  <Shield className="h-5 w-5" />
                  Contract Sentry
                </Link>
                <nav className="flex flex-1 items-center gap-4 text-sm">
                  <Link href="/" className="text-muted-foreground transition-colors hover:text-foreground">
                    New Analysis
                  </Link>
                  <Link href="/contracts" className="text-muted-foreground transition-colors hover:text-foreground">
                    Contracts
                  </Link>
                </nav>
                <div className="flex items-center gap-2">
                  <Link href="/login" className="mr-1 text-sm text-muted-foreground transition-colors hover:text-foreground">
                    Login
                  </Link>
                  <ThemeToggle />
                </div>
              </div>
            </header>
            <main className="mx-auto max-w-5xl px-4 py-8">
              {children}
            </main>
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}
