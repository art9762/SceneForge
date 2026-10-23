const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<{ project_id: string; project_dir: string }>;
}

export async function getProjectState(projectDir: string, signal?: AbortSignal) {
  const res = await fetch(`${API_BASE}/api/projects/${encodeURIComponent(projectDir)}/state`, {
    signal,
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<ProjectResponse>;
}

export async function selectConcept(projectId: string, conceptIndex: number) {
  const res = await fetch(`${API_BASE}/api/projects/${projectId}/select-concept`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ concept_index: conceptIndex }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getFinalFile(projectDir: string, filename: FinalFilename) {
  const res = await fetch(`${API_BASE}/api/projects/${encodeURIComponent(projectDir)}/final/${filename}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<{ content: string }>;
}
