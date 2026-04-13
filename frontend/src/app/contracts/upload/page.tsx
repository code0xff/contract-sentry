"use client";

import { useState } from "react";

import { analyzeContract, createContract } from "@/lib/api";

export default function UploadPage() {
  const [name, setName] = useState("Sample.sol");
  const [source, setSource] = useState("// SPDX-License-Identifier: MIT\npragma solidity ^0.8.20;\ncontract Sample {}");
  const [status, setStatus] = useState<string>("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("uploading…");
    try {
      const c = await createContract({ name, language: "solidity", source });
      const j = await analyzeContract(c.id);
      setStatus(`Job created: ${j.id}`);
    } catch (err) {
      setStatus(`error: ${(err as Error).message}`);
    }
  }

  return (
    <section>
      <h2>Upload contract</h2>
      <form onSubmit={submit}>
        <label>
          Name
          <input value={name} onChange={(e) => setName(e.target.value)} style={{ display: "block" }} />
        </label>
        <label>
          Source
          <textarea
            value={source}
            onChange={(e) => setSource(e.target.value)}
            rows={15}
            style={{ display: "block", width: "100%", fontFamily: "monospace" }}
          />
        </label>
        <button type="submit">Upload and analyze</button>
      </form>
      <p>{status}</p>
    </section>
  );
}
