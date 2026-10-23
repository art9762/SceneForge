"use client";

import { useEffect, useReducer, useState } from "react";
import { usePathname } from "next/navigation";
import { getFinalFile, getProjectState, resumeProject, selectConcept, type FinalFilename, type ProjectResponse } from "@/lib/api";

export default function ProjectPage() {
  // Read the encoded URL once: catch-all params may retain escaped slashes
  // during client navigation, while filesystem paths can contain literal %.
  const projectDir = decodeURIComponent(usePathname().slice("/project/".length));
  const [snapshot, setSnapshot] = useState<{ projectDir: string; data: ProjectResponse } | null>(null);
  const [loadError, setLoadError] = useState("");
  const [actionFailure, setActionFailure] = useState<{ projectDir: string; message: string } | null>(null);
  const actionError = actionFailure?.projectDir === projectDir ? actionFailure.message : "";
  const [selectingProject, setSelectingProject] = useState("");
  const selecting = selectingProject === projectDir;
  const [submittedRuns, setSubmittedRuns] = useState<Set<string>>(new Set());
  const [resumingProject, setResumingProject] = useState("");
  const [downloading, setDownloading] = useState<FinalFilename | null>(null);
  const [refreshVersion, refresh] = useReducer((version: number) => version + 1, 0);
  const data = snapshot?.projectDir === projectDir ? snapshot.data : null;

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    const controller = new AbortController();

    async function poll() {
      try {
        const next = await getProjectState(projectDir, controller.signal);
        if (!active) return;
        setSnapshot({ projectDir, data: next });
        setLoadError("");
      } catch (error: unknown) {
        if (active) setLoadError(error instanceof Error ? error.message : "Ошибка загрузки");
      } finally {
        if (active) timer = setTimeout(poll, 3000);
      }
    }

    timer = setTimeout(poll, 0);
    return () => {
      active = false;
      clearTimeout(timer);
      controller.abort();
    };
  }, [projectDir, refreshVersion]);

  async function handleSelect(index: number) {
    if (!data || selecting || submittedRuns.has(data.state.run?.id || data.state.id)) return;
    const target = projectDir;
    setSelectingProject(target);
    setActionFailure(null);
    try {
      await selectConcept(data.state.id, index, data.state.run?.id);
      setSubmittedRuns((previous) => new Set(previous).add(data.state.run?.id || data.state.id));
      refresh();
    } catch (error: unknown) {
      setActionFailure({ projectDir: target, message: error instanceof Error ? error.message : "Не удалось выбрать концепцию" });
      refresh();
    } finally {
      setSelectingProject((previous) => previous === target ? "" : previous);
    }
  }

  async function handleResume() {
    if (!data || resumingProject === projectDir) return;
    const target = projectDir;
    setResumingProject(target);
    setActionFailure(null);
    try {
      await resumeProject(target);
      refresh();
    } catch (error: unknown) {
      setActionFailure({ projectDir: target, message: error instanceof Error ? error.message : "Не удалось продолжить проект" });
      refresh(); // A conflicting start can already be running in another tab.
    } finally {
      setResumingProject((previous) => previous === target ? "" : previous);
    }
  }

  async function download(filename: FinalFilename) {
    const target = projectDir;
    setDownloading(filename);
    setActionFailure(null);
    try {
      const { content } = await getFinalFile(projectDir, filename);
      const url = URL.createObjectURL(new Blob([content], { type: "text/markdown;charset=utf-8" }));
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.append(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error: unknown) {
      setActionFailure({ projectDir: target, message: error instanceof Error ? error.message : "Не удалось скачать файл" });
    } finally {
      setDownloading(null);
    }
  }

  if (!data) return <div className="p-8 text-zinc-400" role={loadError ? "alert" : "status"}>{loadError || "Загрузка..."}</div>;

  const { state, steps, total_steps } = data;
  const currentStep = Math.max(0, Math.min(state.current_step, total_steps));
  const progress = total_steps > 0 ? (currentStep / total_steps) * 100 : 0;
  const isDone = total_steps > 0 && state.current_step >= total_steps;
  const activeRun = state.run?.status === "running" || state.run?.status === "waiting_input";
  const canResume = !isDone && !activeRun;
  const concepts = state.concepts?.concepts ?? [];
  const needsSelection = steps[state.current_step] === "select_concept"
    && concepts.length > 0 && state.selected_concept_index === null && state.run?.status === "waiting_input";
  const selectedConcept = state.selected_concept_index === null
    ? null : concepts[state.selected_concept_index];

  return (
    <main className="flex-1 p-8 max-w-3xl w-full mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-white break-words">Проект: {projectDir.split("/").pop()}</h1>
      {(loadError || actionError) && <p role="alert" className="text-red-400">{actionError || loadError}</p>}

      <div>
        <div className="flex justify-between text-sm text-zinc-400 mb-1">
          <span>Прогресс</span><span>{currentStep}/{total_steps}</span>
        </div>
        <div role="progressbar" aria-label="Прогресс проекта" aria-valuemin={0} aria-valuemax={total_steps} aria-valuenow={currentStep} className="w-full h-3 bg-zinc-800 rounded-full overflow-hidden">
          <div className="h-full bg-blue-600 transition-all duration-500" style={{ width: `${progress}%` }} />
        </div>
        <p role="status" className="text-sm text-zinc-300 mt-2">
          {isDone ? "Пайплайн завершён" : state.run?.status === "running" ? `Выполняется: ${steps[currentStep]}`
            : state.run?.status === "waiting_input" ? "Ожидается выбор концепции"
            : state.run?.status === "failed" ? "Выполнение завершилось ошибкой"
            : state.run?.status === "interrupted" ? "Выполнение прервано"
            : state.run?.status === "paused" ? "Отдельный шаг выполнен. Можно продолжить пайплайн."
            : "Проект сохранён. Можно продолжить выполнение."}
        </p>
        {state.run?.error && <p role="alert" className="mt-2 text-red-400">{state.run.error}{state.run.error_type ? ` (${state.run.error_type})` : ""}</p>}
        {canResume && (
          <div className="mt-3 space-y-2">
            <p className="text-sm text-zinc-400">Продолжим с шага «{steps[currentStep]}». Сохранённые шаги останутся; незавершённый запрос к модели может повториться.</p>
            <button onClick={handleResume} disabled={resumingProject === projectDir} className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded text-white">
              {resumingProject === projectDir ? "Запускаем…" : state.run?.status === "failed" ? "Повторить с сохранённого шага" : "Продолжить с сохранённого шага"}
            </button>
          </div>
        )}
      </div>

      <ol className="space-y-1" aria-label="Шаги проекта">
        {steps.map((name, index) => (
          <li key={name} aria-current={index === currentStep ? "step" : undefined} className="flex items-center gap-2 text-sm">
            <span aria-hidden="true">{index < currentStep ? "✅" : index === currentStep ? "→" : "⬜"}</span>
            <span className={index <= currentStep ? "text-zinc-300" : "text-zinc-500"}>{name}</span>
          </li>
        ))}
      </ol>

      {state.brief !== null && (
        <section className="bg-zinc-800 rounded-lg p-4 space-y-2">
          <h2 className="text-sm font-medium text-zinc-400 mb-1">Бриф</h2>
          <h3 className="text-white font-medium">{state.brief.title}</h3>
          <p className="text-zinc-300 text-sm">{[state.brief.format, state.brief.duration_minutes > 0 ? `${state.brief.duration_minutes} мин` : "", state.brief.platform].filter(Boolean).join(" · ")}</p>
          <dl className="text-zinc-200 text-sm space-y-1">
            {Object.entries({ "Аудитория": state.brief.target_audience, "Тон": state.brief.tone, "Стиль": state.brief.style, "Цель": state.brief.goal }).filter(([, value]) => value).map(([label, value]) => (
              <div key={label}><dt className="inline text-zinc-400">{label}: </dt><dd className="inline">{value}</dd></div>
            ))}
          </dl>
          {state.brief.constraints.length > 0 && <ul className="text-zinc-300 text-sm list-disc pl-5">{state.brief.constraints.map((text, index) => <li key={index}>{text}</li>)}</ul>}
          {state.brief.keywords.length > 0 && <p className="text-zinc-400 text-sm">{state.brief.keywords.join(", ")}</p>}
        </section>
      )}

      {needsSelection && (
        <section className="space-y-3">
          <h2 className="text-lg font-medium text-white">Выберите концепцию</h2>
          {submittedRuns.has(state.run?.id || state.id) ? <p role="status" className="text-zinc-300">Выбор отправлен. Ждём следующий шаг…</p> : (
            <div className="grid gap-3">
              {concepts.map((concept, index) => (
                <div key={index} className="bg-zinc-800 rounded-lg p-4 border border-zinc-700">
                  <h3 className="font-medium text-white">{concept.name}</h3>
                  <p className="text-zinc-400 text-sm mt-1">{concept.logline}</p>
                  <p className="text-zinc-400 text-sm mt-1">{concept.synopsis}</p>
                  <button onClick={() => handleSelect(index)} disabled={selecting} className="mt-2 px-4 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded text-sm text-white transition">
                    {selecting ? "Отправляем…" : "Выбрать"}
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {selectedConcept && (
        <section className="bg-zinc-800 rounded-lg p-4">
          <h2 className="text-sm font-medium text-zinc-400 mb-1">Выбранная концепция</h2>
          <h3 className="text-white">{selectedConcept.name}</h3>
          <p className="text-zinc-200 text-sm">{selectedConcept.logline}</p>
        </section>
      )}

      {state.critique !== null && (
        <section className="bg-zinc-800 rounded-lg p-4 space-y-2">
          <h2 className="text-sm font-medium text-zinc-400">Критика — оценка: {state.critique.overall_score}/10</h2>
          <ul className="text-zinc-200 text-sm list-disc pl-5">{state.critique.strengths.map((text, index) => <li key={index}>{text}</li>)}</ul>
          {state.critique.weaknesses.map((item, index) => (
            <p key={index} className="text-zinc-200 text-sm"><strong>{item.area}:</strong> {item.issue} — {item.suggestion}</p>
          ))}
          <ul className="text-zinc-200 text-sm list-disc pl-5">{state.critique.suggestions.map((text, index) => <li key={index}>{text}</li>)}</ul>
        </section>
      )}

      {isDone && (
        <section className="space-y-2">
          <h2 className="text-lg font-medium text-white">Готовые файлы</h2>
          <div className="flex flex-wrap gap-3">
            {(["script.md", "teleprompter.md"] as const).map((filename) => (
              <button key={filename} onClick={() => download(filename)} disabled={downloading !== null} className="px-4 py-2 bg-green-700 hover:bg-green-600 disabled:opacity-50 rounded text-white text-sm transition">
                {downloading === filename ? "Скачиваем…" : filename}
              </button>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
