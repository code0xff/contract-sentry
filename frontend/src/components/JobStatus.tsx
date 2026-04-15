"use client";

import { useEffect, useState } from "react";
import { getJob } from "@/lib/api";
import type { Job } from "@/types";

export function JobStatus({ jobId, pollMs = 3000 }: { jobId: string; pollMs?: number }) {
  const [job, setJob] = useState<Job | null>(null);
  const [errorCount, setErrorCount] = useState(0);

  useEffect(() => {
    let cancelled = false;
    async function tick() {
      try {
        const j = await getJob(jobId);
        if (!cancelled) { setJob(j); setErrorCount(0); }
      } catch {
        if (!cancelled) setErrorCount(n => n + 1);
      }
    }
    tick();
    const id = setInterval(tick, pollMs);
    return () => { cancelled = true; clearInterval(id); };
  }, [jobId, pollMs]);

  if (errorCount >= 3) {
    return <p className="text-sm text-destructive">Unable to reach server — please check your connection.</p>;
  }
  if (!job) return <p className="text-muted-foreground text-sm">Loading…</p>;
  return (
    <div className="text-sm">
      <p>Status: {job.status}</p>
      <p>Progress: {job.progress}%</p>
    </div>
  );
}
