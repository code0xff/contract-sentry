'use client';

import { useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { CheckCircle, Upload, XCircle } from 'lucide-react';
import { addContractFiles, analyzeContract, compileCheck, createContract, uploadContractFiles } from '@/lib/api';
import type { CompileCheckResult } from '@/lib/api';
import type { ContractLanguage } from '@/types';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';

const TOOLS = ['slither', 'mythril', 'echidna'] as const;

function getPath(f: File) {
  return (f as File & { webkitRelativePath?: string }).webkitRelativePath || f.name;
}

function FileSelector({
  files,
  selected,
  onToggle,
  onSelectAll,
  onDeselectAll,
}: {
  files: File[];
  selected: Set<string>;
  onToggle: (path: string) => void;
  onSelectAll: () => void;
  onDeselectAll: () => void;
}) {
  const allSelected = files.every(f => selected.has(getPath(f)));
  const noneSelected = files.every(f => !selected.has(getPath(f)));

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">
          {files.length} file{files.length > 1 ? 's' : ''} found
          {selected.size > 0 && ` · ${selected.size} selected`}
        </span>
        <div className="flex gap-3 text-xs">
          <button
            type="button"
            disabled={allSelected}
            onClick={onSelectAll}
            className="text-muted-foreground underline underline-offset-2 hover:text-foreground disabled:opacity-40 disabled:no-underline"
          >
            Select All
          </button>
          <button
            type="button"
            disabled={noneSelected}
            onClick={onDeselectAll}
            className="text-muted-foreground underline underline-offset-2 hover:text-foreground disabled:opacity-40 disabled:no-underline"
          >
            Deselect All
          </button>
        </div>
      </div>

      <div className="max-h-52 overflow-y-auto rounded-md border bg-muted/40 p-2 font-mono text-xs">
        {files.map(f => {
          const path = getPath(f);
          const isChecked = selected.has(path);
          return (
            <label
              key={path}
              className={cn(
                'flex cursor-pointer items-center gap-2 rounded px-2 py-1 hover:bg-muted',
                isChecked ? 'text-foreground' : 'text-muted-foreground',
              )}
            >
              <input
                type="checkbox"
                checked={isChecked}
                onChange={() => onToggle(path)}
                className="shrink-0"
              />
              <span className="flex-1 truncate">{path}</span>
              <span className="shrink-0 text-muted-foreground">
                {(f.size / 1024).toFixed(1)} KB
              </span>
            </label>
          );
        })}
      </div>
    </div>
  );
}

export default function HomePage() {
  const router = useRouter();

  // Shared
  const [name, setName] = useState('');
  const [tools, setTools] = useState<string[]>(['slither', 'mythril']);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Paste tab
  const [language, setLanguage] = useState<ContractLanguage>('solidity');
  const [source, setSource] = useState('');
  const [bytecode, setBytecode] = useState('');

  // Upload tab
  const [allFiles, setAllFiles] = useState<File[]>([]);
  const [selectedPaths, setSelectedPaths] = useState<Set<string>>(new Set());
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const extraFileInputRef = useRef<HTMLInputElement>(null);

  // Compile-check state
  const [uploadedContractId, setUploadedContractId] = useState<string | null>(null);
  const [checkResult, setCheckResult] = useState<CompileCheckResult | null>(null);
  const [checkLoading, setCheckLoading] = useState(false);

  const toggleTool = (t: string) =>
    setTools(prev => prev.includes(t) ? prev.filter(x => x !== t) : [...prev, t]);

  function loadFiles(files: File[]) {
    const sol = files.filter(f => f.name.endsWith('.sol'));
    if (!sol.length) return;
    setAllFiles(sol);
    setSelectedPaths(new Set(sol.map(getPath)));
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragActive(false);
    loadFiles(Array.from(e.dataTransfer.files));
  }

  function togglePath(path: string) {
    setSelectedPaths(prev => {
      const next = new Set(prev);
      next.has(path) ? next.delete(path) : next.add(path);
      return next;
    });
  }

  async function handlePasteSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (language !== 'bytecode' && !source.trim()) { setError('Source code is required'); return; }
    if (language === 'bytecode' && !bytecode.trim()) { setError('Bytecode is required'); return; }
    setLoading(true);
    const autoName = name.trim() || (language === 'bytecode' ? 'Contract' : (source.match(/contract\s+(\w+)/)?.[1] ?? 'Contract'));
    try {
      const contract = await createContract({
        name: autoName,
        language,
        source: source.trim() || undefined,
        bytecode: bytecode.trim() || undefined,
      });
      const job = await analyzeContract(contract.id, tools);
      router.push(`/jobs/${job.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Submission failed');
    } finally {
      setLoading(false);
    }
  }

  function resetUpload() {
    setAllFiles([]);
    setSelectedPaths(new Set());
    setUploadedContractId(null);
    setCheckResult(null);
  }

  async function handleFolderUpload(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (selectedPaths.size === 0) { setError('Select at least one .sol file'); return; }
    setLoading(true);
    const filesToUpload = allFiles.filter(f => selectedPaths.has(getPath(f)));
    const autoName = name.trim() || filesToUpload[0]?.name.replace(/\.sol$/, '') || 'Contract';
    try {
      const contract = await uploadContractFiles({ name: autoName, language: 'solidity', files: filesToUpload });
      setUploadedContractId(contract.id);
      setCheckLoading(true);
      const result = await compileCheck(contract.id);
      setCheckResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setLoading(false);
      setCheckLoading(false);
    }
  }

  async function handleAddFiles(files: File[]) {
    if (!uploadedContractId || !files.length) return;
    setCheckLoading(true);
    setError(null);
    try {
      await addContractFiles(uploadedContractId, files);
      const result = await compileCheck(uploadedContractId);
      setCheckResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add files');
    } finally {
      setCheckLoading(false);
    }
  }

  async function handleStartAnalysis() {
    if (!uploadedContractId) return;
    setLoading(true);
    setError(null);
    try {
      const job = await analyzeContract(uploadedContractId, tools);
      router.push(`/jobs/${job.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
      setLoading(false);
    }
  }

  const toolSection = (
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
  );

  return (
    <div className="max-w-2xl">
      <h1 className="mb-6 text-2xl font-bold">Submit Contract for Analysis</h1>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Contract Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="name">Contract Name</Label>
            <Input
              id="name"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="MyContract.sol"
            />
          </div>

          <Tabs defaultValue="paste">
            <TabsList className="w-full">
              <TabsTrigger value="paste" className="flex-1">Paste Source</TabsTrigger>
              <TabsTrigger value="folder" className="flex-1">Upload Files</TabsTrigger>
            </TabsList>

            {/* ── Paste tab ── */}
            <TabsContent value="paste">
              <form onSubmit={handlePasteSubmit} className="mt-4 space-y-4">
                <div className="space-y-1.5">
                  <Label htmlFor="language">Language</Label>
                  <select
                    id="language"
                    value={language}
                    onChange={e => setLanguage(e.target.value as ContractLanguage)}
                    className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  >
                    <option value="solidity">Solidity</option>
                    <option value="bytecode">Bytecode only</option>
                  </select>
                </div>

                {language !== 'bytecode' ? (
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
                ) : (
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

                {toolSection}

                {error && (
                  <Alert variant="destructive">
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}
                <Button type="submit" disabled={loading}>
                  {loading ? 'Submitting…' : 'Analyze Contract'}
                </Button>
              </form>
            </TabsContent>

            {/* ── Upload tab ── */}
            <TabsContent value="folder">
              <div className="mt-4 space-y-4">
                {/* ── Step 1: pick & upload files (hidden once uploaded) ── */}
                {!uploadedContractId && (
                  <form onSubmit={handleFolderUpload} className="space-y-4">
                    <div
                      className={cn(
                        'flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 text-center transition-colors cursor-pointer',
                        dragActive ? 'border-primary bg-primary/5' : 'border-border hover:border-muted-foreground/50',
                      )}
                      onDragOver={e => { e.preventDefault(); setDragActive(true); }}
                      onDragLeave={() => setDragActive(false)}
                      onDrop={handleDrop}
                      onClick={() => fileInputRef.current?.click()}
                    >
                      <Upload className="mb-2 h-8 w-8 text-muted-foreground" />
                      <p className="text-sm font-medium">
                        Drop .sol files here or{' '}
                        <span className="text-foreground underline underline-offset-2">browse</span>
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Select individual files or an entire project folder
                      </p>
                      <input ref={fileInputRef} type="file" multiple accept=".sol" className="hidden"
                        onChange={e => { loadFiles(Array.from(e.target.files ?? [])); e.target.value = ''; }} />
                    </div>

                    <div className="flex items-center justify-between">
                      <label className="cursor-pointer text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground">
                        Select folder instead
                        <input type="file" multiple accept=".sol"
                          // @ts-expect-error webkitdirectory is non-standard
                          webkitdirectory="" className="hidden"
                          onChange={e => { loadFiles(Array.from(e.target.files ?? [])); e.target.value = ''; }} />
                      </label>
                      {allFiles.length > 0 && (
                        <button type="button" onClick={() => { setAllFiles([]); setSelectedPaths(new Set()); }}
                          className="text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground">
                          Clear
                        </button>
                      )}
                    </div>

                    {allFiles.length > 0 && (
                      <FileSelector files={allFiles} selected={selectedPaths} onToggle={togglePath}
                        onSelectAll={() => setSelectedPaths(new Set(allFiles.map(getPath)))}
                        onDeselectAll={() => setSelectedPaths(new Set())} />
                    )}

                    {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

                    <Button type="submit" disabled={loading || selectedPaths.size === 0}>
                      {loading ? 'Uploading & checking…' : `Upload${selectedPaths.size > 0 ? ` (${selectedPaths.size} files)` : ''}`}
                    </Button>
                  </form>
                )}

                {/* ── Step 2: compile check result ── */}
                {uploadedContractId && (
                  <div className="space-y-4">
                    {checkLoading && (
                      <div className="rounded-md border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-700 dark:border-blue-800 dark:bg-blue-950/30 dark:text-blue-400">
                        Checking compilation…
                      </div>
                    )}

                    {!checkLoading && checkResult?.success && (
                      <div className="flex items-center gap-2 rounded-md border border-green-300 bg-green-50 px-4 py-3 text-sm font-medium text-green-700 dark:border-green-800 dark:bg-green-950/30 dark:text-green-400">
                        <CheckCircle className="h-4 w-4 shrink-0" />
                        Compilation OK — ready to analyze
                      </div>
                    )}

                    {!checkLoading && checkResult && !checkResult.success && (
                      <div className="rounded-md border border-yellow-300 bg-yellow-50 px-4 py-3 dark:border-yellow-800 dark:bg-yellow-950/30">
                        <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-yellow-800 dark:text-yellow-400">
                          <XCircle className="h-4 w-4 shrink-0" />
                          Compilation failed
                        </div>

                        {checkResult.missing.length > 0 && (
                          <>
                            <p className="mb-1 text-xs font-medium text-yellow-800 dark:text-yellow-400">
                              Missing imports ({checkResult.missing.length}):
                            </p>
                            <ul className="mb-3 space-y-1">
                              {checkResult.missing.map(m => (
                                <li key={m} className="font-mono text-xs text-yellow-700 dark:text-yellow-500">{m}</li>
                              ))}
                            </ul>
                            <p className="mb-2 text-xs text-yellow-700 dark:text-yellow-500">
                              Upload the .sol files that define these imports:
                            </p>
                            <input ref={extraFileInputRef} type="file" multiple accept=".sol" className="hidden"
                              onChange={async e => {
                                const files = Array.from(e.target.files ?? []);
                                e.target.value = '';
                                if (files.length) await handleAddFiles(files);
                              }} />
                            <Button size="sm" variant="outline" onClick={() => extraFileInputRef.current?.click()} disabled={checkLoading}>
                              Add Missing Files
                            </Button>
                          </>
                        )}

                        {checkResult.errors.length > 0 && (
                          <>
                            <p className="mb-1 text-xs font-medium text-yellow-800 dark:text-yellow-400">
                              Compiler errors:
                            </p>
                            <ul className="space-y-1">
                              {checkResult.errors.map((e, i) => (
                                <li key={i} className="font-mono text-xs text-yellow-700 dark:text-yellow-500">{e}</li>
                              ))}
                            </ul>
                          </>
                        )}

                        {checkResult.missing.length === 0 && checkResult.errors.length === 0 && (
                          <p className="text-xs text-yellow-700 dark:text-yellow-500">
                            Compilation did not succeed. You can still proceed with analysis — tools may find partial results.
                          </p>
                        )}
                      </div>
                    )}

                    {toolSection}

                    {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

                    <div className="flex gap-2">
                      <Button
                        disabled={loading || checkLoading || !checkResult}
                        onClick={handleStartAnalysis}
                      >
                        {loading ? 'Starting…' : 'Start Analysis'}
                      </Button>
                      <Button variant="ghost" size="sm" onClick={resetUpload}>
                        Start over
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      <p className="mt-4 text-sm text-muted-foreground">
        Results are processed asynchronously. You will be redirected to the job status page.
      </p>
    </div>
  );
}
