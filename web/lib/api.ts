const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function responseError(response: Response): Promise<Error> {
  try {
    const body: { detail?: unknown } = await response.json();
    if (typeof body.detail === "string") return new Error(body.detail);
  } catch { /* Fall back to the HTTP code for non-JSON or validation responses. */ }
  return new Error(`Ошибка API (HTTP ${response.status})`);
}

export interface Concept {
  name: string;
  direction: string;
  logline: string;
  synopsis: string;
  tone_description: string;
  why_it_works: string;
}

export interface Brief {
  title: string;
  format: string;
  duration_minutes: number;
  target_audience: string;
  tone: string;
  style: string;
  platform: string;
  goal: string;
  constraints: string[];
  keywords: string[];
}

export interface ProjectState {
  id: string;
  raw_idea: string;
  current_step: number;
  run: {
    id: string;
    status: "running" | "waiting_input" | "failed" | "interrupted" | "paused" | "completed";
    provider: string;
    model: string | null;
    step_name: string | null;
    error: string | null;
    error_type: string | null;
    started_at: string;
    finished_at: string | null;
  } | null;
  brief: Brief | null;
  concepts: { concepts: Concept[] } | null;
  selected_concept_index: number | null;
  critique: {
    overall_score: number;
    strengths: string[];
    weaknesses: { area: string; issue: string; suggestion: string }[];
    suggestions: string[];
  } | null;
}

export interface ProjectResponse {
  state: ProjectState;
  steps: string[];
  total_steps: number;
}

export type FinalFilename = "script.md" | "teleprompter.md";

export async function createProject(data: {
  raw_idea: string;
  project_name?: string;
  provider?: string;
  model?: string;
}) {
  const res = await fetch(`${API_BASE}/api/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw await responseError(res);
  return res.json() as Promise<{ project_id: string; project_dir: string }>;
}

export async function getProjectState(projectDir: string, signal?: AbortSignal) {
  const res = await fetch(`${API_BASE}/api/projects/${encodeURIComponent(projectDir)}/state`, {
    signal,
    cache: "no-store",
  });
  if (!res.ok) throw await responseError(res);
  return res.json() as Promise<ProjectResponse>;
}

export async function selectConcept(projectId: string, conceptIndex: number, runId?: string) {
  const res = await fetch(`${API_BASE}/api/projects/${projectId}/select-concept`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ concept_index: conceptIndex, run_id: runId }),
  });
  if (!res.ok) throw await responseError(res);
  return res.json();
}

export async function resumeProject(projectDir: string) {
  const res = await fetch(`${API_BASE}/api/projects/${encodeURIComponent(projectDir)}/resume`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
  if (!res.ok) throw await responseError(res);
  return res.json() as Promise<{ project_id: string; project_dir: string; run_id: string }>;
}

export async function getFinalFile(projectDir: string, filename: FinalFilename) {
  const res = await fetch(`${API_BASE}/api/projects/${encodeURIComponent(projectDir)}/final/${filename}`);
  if (!res.ok) throw await responseError(res);
  return res.json() as Promise<{ content: string }>;
}
