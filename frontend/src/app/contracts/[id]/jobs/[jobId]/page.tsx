import { getFindings, getJob } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function JobDetail({ params }: { params: { id: string; jobId: string } }) {
  const job = await getJob(params.jobId);
  const findings = await getFindings(params.jobId).catch(() => []);
  return (
    <section>
      <h2>Job {job.id}</h2>
      <p>Status: {job.status}</p>
      <p>Progress: {job.progress}%</p>
      <h3>Findings</h3>
      <ul>
        {findings.map((f) => (
          <li key={f.id}>
            <strong>[{f.severity}]</strong> {f.title} — {f.vulnerability_type} ({f.tool})
          </li>
        ))}
      </ul>
    </section>
  );
}
