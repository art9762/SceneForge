const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
  const res = await fetch(`${API_BASE}/api/projects/${encodeURIComponent(projectDir)}/state`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<{
    state: {
      brief?: unknown;
      concepts?: { title: string; logline: string }[];
      selected_concept?: unknown;
      critique?: { score: number; notes: string };
      [key: string]: unknown;
    };
    steps: { name: string; status: string }[];
    total_steps: number;
    current_step: number;
  }>;
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

export async function getFinalFile(projectDir: string, filename: string) {
  const res = await fetch(`${API_BASE}/api/projects/${encodeURIComponent(projectDir)}/final/${filename}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<{ content: string }>;
}
