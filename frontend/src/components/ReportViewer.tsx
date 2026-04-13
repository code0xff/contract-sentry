import type { Report } from "@/types";

export function ReportViewer({ report }: { report: Report }) {
  return (
    <div>
      <h3>Composite severity: {report.summary.composite_severity}</h3>
      <p>Total findings: {report.summary.total}</p>
      <table>
        <thead>
          <tr>
            <th>severity</th>
            <th>count</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(report.summary.by_severity).map(([k, v]) => (
            <tr key={k}>
              <td>{k}</td>
              <td>{v}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
