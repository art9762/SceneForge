"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createProject } from "@/lib/api";

export default function Home() {
  const router = useRouter();
  const [idea, setIdea] = useState("");
  const [name, setName] = useState("");
  const [provider, setProvider] = useState("claude");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await createProject({
        raw_idea: idea,
        project_name: name || undefined,
        provider,
      });
      router.push(`/project/${res.project_dir}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Ошибка");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <form onSubmit={handleSubmit} className="w-full max-w-lg space-y-6">
        <h1 className="text-3xl font-bold text-white">SceneForge</h1>
        <p className="text-zinc-400">Создайте сценарий из идеи</p>

        <textarea
          value={idea}
          onChange={(e) => setIdea(e.target.value)}
          placeholder="Опишите вашу идею для видео..."
          required
          rows={4}
          className="w-full rounded-lg bg-zinc-800 border border-zinc-700 p-3 text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />

        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Название проекта (необязательно)"
          className="w-full rounded-lg bg-zinc-800 border border-zinc-700 p-3 text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />

        <select
          value={provider}
          onChange={(e) => setProvider(e.target.value)}
          className="w-full rounded-lg bg-zinc-800 border border-zinc-700 p-3 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="claude">Claude</option>
          <option value="openai">OpenAI</option>
        </select>

        {error && <p className="text-red-400 text-sm">{error}</p>}

        <button
          type="submit"
          disabled={loading || !idea.trim()}
          className="w-full rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 p-3 text-white font-medium transition"
        >
          {loading ? "Создаём..." : "Создать проект"}
        </button>
      </form>
    </div>
  );
}
