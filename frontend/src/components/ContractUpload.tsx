"use client";

import { useState } from "react";

import { analyzeContract, createContract } from "@/lib/api";
import type { Contract, Job } from "@/types";

export function ContractUpload({ onUploaded }: { onUploaded?: (c: Contract, j: Job) => void }) {
  const [name, setName] = useState("Sample.sol");
  const [source, setSource] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const c = await createContract({ name, language: "solidity", source });
      const j = await analyzeContract(c.id);
      onUploaded?.(c, j);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit}>
      <input value={name} onChange={(e) => setName(e.target.value)} />
      <textarea value={source} onChange={(e) => setSource(e.target.value)} rows={10} />
      <button type="submit" disabled={busy}>
        {busy ? "Uploading…" : "Upload"}
      </button>
    </form>
  );
}
