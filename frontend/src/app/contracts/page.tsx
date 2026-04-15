'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { deleteContract, listContracts } from '@/lib/api';
import type { Contract } from '@/types';
import { PageError, PageLoading } from '@/components/page-state';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';

const LANG_CLASSES: Record<string, string> = {
  solidity: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  vyper: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  bytecode: 'bg-secondary text-secondary-foreground',
};

export default function ContractListPage() {
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  function load() {
    setLoading(true);
    listContracts()
      .then(setContracts)
      .catch(e => setError(e instanceof Error ? e.message : 'Failed to load'))
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, []);

  async function handleDelete(e: React.MouseEvent, id: string) {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm('Delete this contract and all its analyses? This cannot be undone.')) return;
    setDeleting(id);
    try {
      await deleteContract(id);
      setContracts(prev => prev.filter(c => c.id !== id));
      toast.success('Contract deleted');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Delete failed');
    } finally {
      setDeleting(null);
    }
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Contracts</h1>
        <Button asChild size="sm">
          <Link href="/">+ New Analysis</Link>
        </Button>
      </div>

      {loading && <PageLoading />}
      {error && <PageError error={error} onRetry={() => { setLoading(true); setError(null); listContracts().then(setContracts).catch(e => setError(e instanceof Error ? e.message : 'Failed to load')).finally(() => setLoading(false)); }} />}

      {!loading && !error && contracts.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">
              No contracts yet.{' '}
              <Link href="/" className="text-foreground underline underline-offset-4">
                Upload your first contract
              </Link>
              .
            </p>
          </CardContent>
        </Card>
      )}

      <div className="flex flex-col gap-2">
        {contracts.map(c => (
          <Link key={c.id} href={`/contracts/${c.id}`} className="group block no-underline">
            <Card className="cursor-pointer transition-colors hover:bg-accent/50">
              <CardContent className="px-5 py-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{c.name}</span>
                    {c.compiler_version && (
                      <span className="text-xs text-muted-foreground">{c.compiler_version}</span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={cn(
                      "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium",
                      LANG_CLASSES[c.language] ?? 'bg-secondary text-secondary-foreground'
                    )}>
                      {c.language}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {new Date(c.created_at).toLocaleDateString()}
                    </span>
                    <button
                      onClick={e => handleDelete(e, c.id)}
                      disabled={deleting === c.id}
                      className="ml-1 rounded p-1 text-muted-foreground opacity-0 transition-opacity hover:bg-destructive/10 hover:text-destructive group-hover:opacity-100 disabled:opacity-40"
                      title="Delete contract"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
