'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { analyzeContract, createContract } from '@/lib/api';
import type { ContractLanguage } from '@/types';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription } from '@/components/ui/alert';

const TOOLS = ['slither', 'mythril', 'echidna'] as const;

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
    <div className="max-w-2xl">
      <h1 className="mb-6 text-2xl font-bold">Submit Contract for Analysis</h1>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Contract Details</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="name">Contract Name</Label>
              <Input
                id="name"
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="MyContract.sol"
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="language">Language</Label>
              <select
                id="language"
                value={language}
                onChange={e => setLanguage(e.target.value as ContractLanguage)}
                className="flex h-9 rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              >
                <option value="solidity">Solidity</option>
                <option value="bytecode">Bytecode only</option>
              </select>
            </div>

            {language !== 'bytecode' && (
              <div className="space-y-1.5">
                <Label htmlFor="source">Source Code</Label>
                <Textarea
                  id="source"
                  value={source}
                  onChange={e => setSource(e.target.value)}
                  placeholder={'// SPDX-License-Identifier: MIT\npragma solidity ^0.8.20;\ncontract MyContract { ... }'}
                  rows={12}
                  className="font-mono text-xs"
                />
              </div>
            )}

            {language === 'bytecode' && (
              <div className="space-y-1.5">
                <Label htmlFor="bytecode">Bytecode (0x...)</Label>
                <Input
                  id="bytecode"
                  value={bytecode}
                  onChange={e => setBytecode(e.target.value)}
                  placeholder="0x608060..."
                  className="font-mono"
                />
              </div>
            )}

            <div className="space-y-2">
              <Label>Analysis Tools</Label>
              <div className="flex flex-wrap gap-4">
                {TOOLS.map(t => (
                  <label key={t} className="flex cursor-pointer items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={tools.includes(t)}
                      onChange={() => toggleTool(t)}
                      className="rounded border-border"
                    />
                    <span className="capitalize">{t}</span>
                  </label>
                ))}
              </div>
            </div>

            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <Button type="submit" disabled={loading}>
              {loading ? 'Submitting…' : 'Analyze Contract'}
            </Button>
          </form>
        </CardContent>
      </Card>

      <p className="mt-4 text-sm text-muted-foreground">
        Results are processed asynchronously. You will be redirected to the job status page.
      </p>
    </div>
  );
}
