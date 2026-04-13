"use client";

import { useEffect, useState } from "react";

import { getJob } from "@/lib/api";
import type { Job } from "@/types";

export function JobStatus({ jobId, pollMs = 3000 }: { jobId: string; pollMs?: number }) {
  const [job, setJob] = useState<Job | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function tick() {
      try {
        const j = await getJob(jobId);
        if (!cancelled) setJob(j);
      } catch {
        // ignore
      }
    }
    tick();
    const id = setInterval(tick, pollMs);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [jobId, pollMs]);

  if (!job) return <p>Loading…</p>;
  return (
    <div>
      <p>Status: {job.status}</p>
      <p>Progress: {job.progress}%</p>
    </div>
  );
}
