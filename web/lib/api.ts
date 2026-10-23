const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type Concept = {
  name: string;
  logline: string;
  synopsis: string;
  direction: string;
  tone_description: string;
  why_it_works: string;
};

export type ProjectData = {
  state: {
    id: string;
    current_step: number;
    brief: Record<string, unknown> | null;
    concepts: { concepts: Concept[] } | null;
    selected_concept_index: number | null;
    critique: {
      overall_score: number;
      strengths: string[];
      weaknesses: { area: string; issue: string; suggestion: string }[];
      suggestions: string[];
    } | null;
  };
  steps: string[];
  total_steps: number;
};

export function encodeProjectPath(projectDir: string) {
  return projectDir.split("/").map(encodeURIComponent).join("/");
}

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

export async function getProjectState(projectDir: string) {
  const res = await fetch(`${API_BASE}/api/projects/${encodeProjectPath(projectDir)}/state`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<ProjectData>;
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

export type FinalFilename = "script.md" | "teleprompter.md";

export async function getFinalFile(projectDir: string, filename: FinalFilename) {
  const res = await fetch(`${API_BASE}/api/projects/${encodeProjectPath(projectDir)}/final/${filename}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<{ content: string }>;
}
