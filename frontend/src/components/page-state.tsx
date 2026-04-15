'use client';

import { X } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';

/** Full-page loading text */
export function PageLoading({ message = 'Loading…' }: { message?: string }) {
  return <p className="text-muted-foreground">{message}</p>;
}

/** Full-page error with optional retry */
export function PageError({
  error,
  onRetry,
}: {
  error: string;
  onRetry?: () => void;
}) {
  return (
    <div className="space-y-3">
      <Alert variant="destructive">
        <AlertDescription>{error}</AlertDescription>
      </Alert>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}

/** Inline dismissable alert for action feedback (replaces browser alert()) */
export function ActionAlert({
  message,
  type = 'error',
  onClose,
}: {
  message: string;
  type?: 'error' | 'success';
  onClose: () => void;
}) {
  return (
    <Alert
      variant={type === 'error' ? 'destructive' : 'default'}
      className={
        type === 'success'
          ? 'border-green-500/50 bg-green-50 text-green-800 dark:bg-green-950/20 dark:text-green-400'
          : undefined
      }
    >
      <div className="flex items-start justify-between gap-2">
        <AlertDescription className="flex-1">{message}</AlertDescription>
        <button onClick={onClose} className="shrink-0 opacity-60 hover:opacity-100">
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
    </Alert>
  );
}
