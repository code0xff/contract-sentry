import type { Contract, Finding, FindingDiff, Job, Report, Simulation } from '@/types/index';

const BASE = process.env.NEXT_PUBLIC_API_URL ?? '';

// Auth
export const loginUser = (email: string, password: string) =>
  request<{ access_token: string }>('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });

export const registerUser = (email: string, password: string) =>
  request<void>('/api/v1/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });

function authHeader(): Record<string, string> {
  if (typeof window === 'undefined') return {};
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      headers: { 'Content-Type': 'application/json', ...authHeader(), ...init?.headers },
      ...init,
    });
  } catch (err) {
    // Network-level failure (ECONNREFUSED, DNS, etc.)
    throw new Error(`Network error — cannot reach server (${(err as Error).message})`);
  }
  if (!res.ok) {
    // Try to parse FastAPI's {"detail": "..."} error body
    const body = await res.text().catch(() => '');
    let message = `${res.status} ${res.statusText}`;
    if (body) {
      try {
        const json = JSON.parse(body);
        if (typeof json.detail === 'string') {
          message = json.detail;
        } else if (Array.isArray(json.detail)) {
          // Pydantic validation errors: [{loc, msg, type}]
          message = json.detail.map((d: { msg?: string }) => d.msg ?? String(d)).join('; ');
        } else {
          message = body;
        }
      } catch {
        message = body || message;
      }
    }
    throw new Error(message);
  }
  if (res.status === 204 || res.headers.get('content-length') === '0') {
    return undefined as T;
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
export const analyzeContract = (contractId: string, tools?: string[], entryFiles?: string[]) =>
  request<Job>(`/api/v1/contracts/${contractId}/analyze`, {
    method: 'POST',
    body: JSON.stringify(tools || entryFiles ? { ...(tools && { tools }), ...(entryFiles && { entry_files: entryFiles }) } : {}),
  });

export const generateAiReport = (jobId: string) =>
  request<{ markdown: string }>(`/api/v1/jobs/${jobId}/report/ai-markdown`, { method: 'POST' });

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
  const res = await fetch(`${BASE}/api/v1/reports/${reportId}/markdown`, { headers: authHeader() });
  if (!res.ok) throw new Error(res.statusText);
  return res.text();
};

export const getReportHtml = async (reportId: string): Promise<string> => {
  const res = await fetch(`${BASE}/api/v1/reports/${reportId}/html`, { headers: authHeader() });
  if (!res.ok) throw new Error(res.statusText);
  return res.text();
};

export const diffFindings = (jobId: string, baselineJobId: string) =>
  request<FindingDiff>(`/api/v1/jobs/${jobId}/diff?baseline=${baselineJobId}`);

export const generatePoc = (jobId: string, findingId: string) =>
  request<{ poc: string }>(`/api/v1/jobs/${jobId}/findings/${findingId}/poc`, { method: 'POST' });

// Simulations
export const getSimulation = (simId: string) => request<Simulation>(`/api/v1/simulations/${simId}`);

// Multi-file upload
export async function uploadContractFiles(payload: {
  name: string;
  language?: string;
  compiler_version?: string;
  files: File[];
}): Promise<Contract> {
  const form = new FormData();
  form.append('name', payload.name);
  form.append('language', payload.language ?? 'solidity');
  if (payload.compiler_version) {
    form.append('compiler_version', payload.compiler_version);
  }
  for (const file of payload.files) {
    // Preserve directory structure via webkitRelativePath when available
    const relativePath =
      (file as File & { webkitRelativePath?: string }).webkitRelativePath || file.name;
    form.append('files', file, relativePath);
  }
  // NOTE: Do NOT set Content-Type — browser sets multipart boundary automatically
  const res = await fetch(`${BASE}/api/v1/contracts/upload`, {
    method: 'POST',
    headers: { ...authHeader() },
    body: form,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status} ${text}`);
  }
  return res.json() as Promise<Contract>;
}

export const deleteContract = (contractId: string): Promise<void> =>
  request<void>(`/api/v1/contracts/${contractId}`, { method: 'DELETE' });

export const deleteJob = (jobId: string): Promise<void> =>
  request<void>(`/api/v1/jobs/${jobId}`, { method: 'DELETE' });

export interface CompileCheckResult {
  success: boolean;
  missing: string[];
  errors: string[];
}

export const compileCheck = (contractId: string): Promise<CompileCheckResult> =>
  request<CompileCheckResult>(`/api/v1/contracts/${contractId}/compile-check`, { method: 'POST' });

export async function addContractFiles(
  contractId: string,
  files: File[],
  pathOverrides?: Record<string, string>,  // filename → resolved import path
): Promise<Contract> {
  const form = new FormData();
  for (const file of files) {
    const defaultPath =
      (file as File & { webkitRelativePath?: string }).webkitRelativePath || file.name;
    const resolvedPath = pathOverrides?.[file.name] ?? defaultPath;
    form.append('files', file, resolvedPath);
  }
  const res = await fetch(`${BASE}/api/v1/contracts/${contractId}/files`, {
    method: 'PATCH',
    headers: { ...authHeader() },
    body: form,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status} ${text}`);
  }
  return res.json() as Promise<Contract>;
}
