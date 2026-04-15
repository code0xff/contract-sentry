export type ContractLanguage = "solidity" | "vyper" | "bytecode";

export type Severity = "critical" | "high" | "medium" | "low" | "info";

export type JobStatus = "pending" | "running" | "completed" | "failed" | "cancelled";

export type SimulationStatus =
  | "queued"
  | "running"
  | "succeeded"
  | "failed"
  | "timed_out";

export type VulnerabilityType =
  | "reentrancy"
  | "integer_overflow"
  | "access_control"
  | "unchecked_return"
  | "timestamp_dependency"
  | "delegatecall"
  | "self_destruct"
  | "front_running"
  | "denial_of_service"
  | "flash_loan"
  | "other";

export interface Contract {
  id: string;
  name: string;
  language: ContractLanguage;
  compiler_version: string | null;
  created_at: string;
}

export interface Job {
  id: string;
  contract_id: string;
  status: JobStatus;
  tools: string[];
  progress: number;
  error: string | null;
  tool_errors: Record<string, string> | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface Finding {
  id: string;
  job_id: string;
  tool: string;
  vulnerability_type: VulnerabilityType;
  severity: Severity;
  title: string;
  description: string;
  location: string | null;
  confidence: number;
  created_at: string;
  evidences: { id: string; kind: string; payload: Record<string, unknown> }[];
}

export interface Report {
  id: string;
  job_id: string;
  status: "draft" | "ready";
  summary: {
    total: number;
    by_severity: Record<string, number>;
    composite_severity: Severity;
  };
  created_at: string;
}

export interface Simulation {
  id: string;
  job_id: string;
  finding_id: string | null;
  status: SimulationStatus;
  template: string;
  fork_rpc_url: string | null;
  fork_block: number | null;
  output: string | null;
  trace: string | null;
  created_at: string;
  finished_at: string | null;
}
