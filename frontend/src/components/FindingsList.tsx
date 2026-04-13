import type { Finding } from "@/types";

export function FindingsList({ findings }: { findings: Finding[] }) {
  if (!findings.length) return <p>No findings.</p>;
  return (
    <ul>
      {findings.map((f) => (
        <li key={f.id}>
          <strong>[{f.severity}]</strong> {f.title} — {f.vulnerability_type} ({f.tool})
          {f.location && <em> @ {f.location}</em>}
        </li>
      ))}
    </ul>
  );
}
