"use client";

import { useState } from "react";

import { createSimulation } from "@/lib/api";
import type { Simulation } from "@/types";

export function SimulationPanel({ jobId }: { jobId: string }) {
  const [sim, setSim] = useState<Simulation | null>(null);
  const [template, setTemplate] = useState("reentrancy");
  const [fork, setFork] = useState("");

  async function run() {
    const s = await createSimulation(jobId, {
      template,
      fork_rpc_url: fork || undefined,
    });
    setSim(s);
  }

  return (
    <div>
      <label>
        Template
        <select value={template} onChange={(e) => setTemplate(e.target.value)}>
          <option value="reentrancy">reentrancy</option>
          <option value="integer_overflow">integer_overflow</option>
          <option value="access_control">access_control</option>
        </select>
      </label>
      <label>
        Fork RPC URL (optional)
        <input value={fork} onChange={(e) => setFork(e.target.value)} />
      </label>
      <button onClick={run}>Run simulation</button>
      {sim && (
        <pre>{JSON.stringify(sim, null, 2)}</pre>
      )}
    </div>
  );
}
