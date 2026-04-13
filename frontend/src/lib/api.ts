import type { Contract, Finding, FindingDiff, Job, Report, Simulation } from '@/types/index';

const BASE = process.env.NEXT_PUBLIC_API_URL ?? '';

function authHeader(): Record<string, string> {
  if (typeof window === 'undefined') return {};
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...authHeader(), ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status} ${text}`);
  }
  return res.json() as Promise<T>;
}

// Contracts
export const createContract = (payload: {
  name: string;
  language: string;
  source?: string;
  bytecode?: string;
  compiler_version?: string;
}) => request<Contract>('/api/v1/contracts', { method: 'POST', body: JSON.stringify(payload) });

export const listContracts = () => request<Contract[]>('/api/v1/contracts');

export const getContract = (id: string) => request<Contract>(`/api/v1/contracts/${id}`);

export const listContractJobs = (contractId: string) =>
  request<Job[]>(`/api/v1/contracts/${contractId}/jobs`);

// Jobs
export const analyzeContract = (contractId: string, tools?: string[]) =>
  request<Job>(`/api/v1/contracts/${contractId}/analyze`, {
    method: 'POST',
    body: JSON.stringify(tools ? { tools } : {}),
  });

export const getJob = (jobId: string) => request<Job>(`/api/v1/jobs/${jobId}`);

export const getFindings = (jobId: string) => request<Finding[]>(`/api/v1/jobs/${jobId}/findings`);

export const createSimulation = (
  jobId: string,
  payload: { template: string; fork_rpc_url?: string; fork_block?: number; finding_id?: string }
) =>
  request<Simulation>(`/api/v1/jobs/${jobId}/simulate`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });

// Reports
export const getJobReport = (jobId: string) => request<Report>(`/api/v1/jobs/${jobId}/report`);

export const getReport = (reportId: string) => request<Report>(`/api/v1/reports/${reportId}`);

export const getReportMarkdown = async (reportId: string): Promise<string> => {
  const res = await fetch(`${BASE}/api/v1/reports/${reportId}/markdown`);
  if (!res.ok) throw new Error(res.statusText);
  return res.text();
};

export const getReportHtml = async (reportId: string): Promise<string> => {
  const res = await fetch(`${BASE}/api/v1/reports/${reportId}/html`);
  if (!res.ok) throw new Error(res.statusText);
  return res.text();
};

export const diffFindings = (jobId: string, baselineJobId: string) =>
  request<FindingDiff>(`/api/v1/jobs/${jobId}/diff?baseline=${baselineJobId}`);

export const generatePoc = (jobId: string, findingId: string) =>
  request<{ poc: string }>(`/api/v1/jobs/${jobId}/findings/${findingId}/poc`, { method: 'POST' });

// Simulations
export const getSimulation = (simId: string) => request<Simulation>(`/api/v1/simulations/${simId}`);
