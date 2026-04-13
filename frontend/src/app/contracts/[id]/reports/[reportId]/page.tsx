import { getReport } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ReportPage({
  params,
}: {
  params: { id: string; reportId: string };
}) {
  const report = await getReport(params.reportId);
  return (
    <section>
      <h2>Report {report.id}</h2>
      <p>Status: {report.status}</p>
      <p>
        Composite severity: <strong>{report.summary.composite_severity}</strong>
      </p>
      <p>Total findings: {report.summary.total}</p>
      <pre>{JSON.stringify(report.summary.by_severity, null, 2)}</pre>
    </section>
  );
}
