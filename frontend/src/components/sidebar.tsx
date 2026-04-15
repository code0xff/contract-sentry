'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { FileText, LogIn, LogOut, PlusCircle, Shield, Swords } from 'lucide-react';
import { useAuth } from '@/context/auth-context';
import { Button } from '@/components/ui/button';
import { ThemeToggle } from '@/components/theme-toggle';
import { cn } from '@/lib/utils';

const PUBLIC_PATHS = ['/login', '/register'];

const NAV_ITEMS = [
  { href: '/', label: 'New Analysis', icon: PlusCircle, exact: true },
  { href: '/contracts', label: 'Contracts', icon: FileText, exact: false },
  { href: '/campaigns', label: 'Attack Campaigns', icon: Swords, exact: false },
];

export function Sidebar() {
  const pathname = usePathname();
  const { isAuthenticated, logout } = useAuth();

  if (PUBLIC_PATHS.includes(pathname)) return null;

  function isActive(href: string, exact: boolean) {
    return exact ? pathname === href : pathname.startsWith(href);
  }

  return (
    <aside className="flex h-screen w-[220px] shrink-0 flex-col border-r bg-background">
      {/* Logo */}
      <Link href="/" className="flex h-14 items-center gap-2 border-b px-4">
        <Shield className="h-5 w-5 text-foreground" />
        <span className="font-bold tracking-tight">Contract Sentry</span>
      </Link>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-0.5">
        {NAV_ITEMS.map(({ href, label, icon: Icon, exact }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
              isActive(href, exact)
                ? 'bg-accent text-accent-foreground'
                : 'text-muted-foreground hover:bg-accent/60 hover:text-foreground',
            )}
          >
            <Icon className="h-4 w-4 shrink-0" />
            {label}
          </Link>
        ))}
      </nav>

      {/* Bottom: theme + auth */}
      <div className="border-t p-3 space-y-1">
        <div className="flex items-center justify-between px-1 pb-1">
          <span className="text-xs text-muted-foreground">Theme</span>
          <ThemeToggle />
        </div>
        {isAuthenticated ? (
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start gap-2 text-muted-foreground hover:text-foreground"
            onClick={logout}
          >
            <LogOut className="h-4 w-4" />
            Sign Out
          </Button>
        ) : (
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start gap-2 text-muted-foreground hover:text-foreground"
            asChild
          >
            <Link href="/login">
              <LogIn className="h-4 w-4" />
              Sign In
            </Link>
          </Button>
        )}
      </div>
    </aside>
  );
}
