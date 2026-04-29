"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { getProjectState, selectConcept } from "@/lib/api";

type StepInfo = { name: string; status: string };
type ProjectData = Awaited<ReturnType<typeof getProjectState>>;

export default function ProjectPage() {
  const params = useParams();
  const projectDir = Array.isArray(params.path) ? params.path.join("/") : (params.path as string);

  const [data, setData] = useState<ProjectData | null>(null);
  const [error, setError] = useState("");

  const poll = useCallback(async () => {
    try {
      const d = await getProjectState(projectDir);
      setData(d);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Ошибка загрузки");
    }
  }, [projectDir]);

  useEffect(() => {
    poll();
    const id = setInterval(poll, 3000);
    return () => clearInterval(id);
  }, [poll]);

  async function handleSelect(index: number) {
    // project_id is typically the last segment of projectDir
    const projectId = projectDir.split("/").pop() || projectDir;
    await selectConcept(projectId, index);
    poll();
  }

  if (error) return <div className="p-8 text-red-400">{error}</div>;
  if (!data) return <div className="p-8 text-zinc-400">Загрузка...</div>;

  const { state, steps, total_steps, current_step } = data;
  const progress = total_steps > 0 ? (current_step / total_steps) * 100 : 0;
  const isDone = steps.every((s: StepInfo) => s.status === "done");
  const needsSelection = steps.some(
    (s: StepInfo) => s.name === "select_concept" && s.status === "waiting"
  ) && state.concepts && !state.selected_concept;

  return (
    <div className="flex-1 p-8 max-w-3xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-white">Проект: {projectDir.split("/").pop()}</h1>

      {/* Progress */}
      <div>
        <div className="flex justify-between text-sm text-zinc-400 mb-1">
          <span>Прогресс</span>
          <span>{current_step}/{total_steps}</span>
        </div>
        <div className="w-full h-3 bg-zinc-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-600 transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Steps */}
      <ul className="space-y-1">
        {steps.map((s: StepInfo) => (
          <li key={s.name} className="flex items-center gap-2 text-sm">
            <span>
              {s.status === "done" ? "✅" : s.status === "running" ? "⏳" : "⬜"}
            </span>
            <span className={s.status === "done" ? "text-zinc-300" : "text-zinc-500"}>
              {s.name}
            </span>
          </li>
        ))}
      </ul>

      {/* Brief */}
      {state.brief != null && (
        <div className="bg-zinc-800 rounded-lg p-4">
          <h3 className="text-sm font-medium text-zinc-400 mb-1">Бриф</h3>
          <p className="text-zinc-200 text-sm whitespace-pre-wrap">
            {String(typeof state.brief === "string" ? state.brief : JSON.stringify(state.brief, null, 2))}
          </p>
        </div>
      )}

      {/* Concept Selection */}
      {needsSelection && state.concepts != null && (
        <div className="space-y-3">
          <h3 className="text-lg font-medium text-white">Выберите концепцию</h3>
          <div className="grid gap-3">
            {(state.concepts as { title: string; logline: string }[]).map((c, i) => (
              <div key={i} className="bg-zinc-800 rounded-lg p-4 border border-zinc-700">
                <h4 className="font-medium text-white">{c.title}</h4>
                <p className="text-zinc-400 text-sm mt-1">{c.logline}</p>
                <button
                  onClick={() => handleSelect(i)}
                  className="mt-2 px-4 py-1.5 bg-blue-600 hover:bg-blue-700 rounded text-sm text-white transition"
                >
                  Выбрать
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Selected concept */}
      {state.selected_concept != null && (
        <div className="bg-zinc-800 rounded-lg p-4">
          <h3 className="text-sm font-medium text-zinc-400 mb-1">Выбранная концепция</h3>
          <p className="text-zinc-200 text-sm whitespace-pre-wrap">
            {String(typeof state.selected_concept === "string"
              ? state.selected_concept
              : JSON.stringify(state.selected_concept, null, 2))}
          </p>
        </div>
      )}

      {/* Critique */}
      {state.critique != null && (
        <div className="bg-zinc-800 rounded-lg p-4">
          <h3 className="text-sm font-medium text-zinc-400 mb-1">
            Критика — оценка: {(state.critique as { score: number }).score}/10
          </h3>
          <p className="text-zinc-200 text-sm">{(state.critique as { notes: string }).notes}</p>
        </div>
      )}

      {/* Final files */}
      {isDone && (
        <div className="space-y-2">
          <h3 className="text-lg font-medium text-white">Готовые файлы</h3>
          <div className="flex gap-3">
            <a
              href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/projects/${encodeURIComponent(projectDir)}/final/script.md`}
              target="_blank"
              className="px-4 py-2 bg-green-700 hover:bg-green-600 rounded text-white text-sm transition"
            >
              📄 script.md
            </a>
            <a
              href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/projects/${encodeURIComponent(projectDir)}/final/teleprompter.md`}
              target="_blank"
              className="px-4 py-2 bg-green-700 hover:bg-green-600 rounded text-white text-sm transition"
            >
              📄 teleprompter.md
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
