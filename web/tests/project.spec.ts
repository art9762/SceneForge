import { expect, test, type Page } from "@playwright/test";
import { readFile } from "node:fs/promises";
import snapshots from "./fixtures/project-states.json";
import type { ProjectResponse } from "../lib/api";

const projectDir = "/tmp/sceneforge%20-test/Обсерватория";
const projectURL = `/project/${encodeURIComponent(projectDir)}`;
const stateURL = "http://localhost:8000/api/projects/**/state";
const headers = { "Access-Control-Allow-Origin": "*" };

async function showState(page: Page, name: keyof typeof snapshots) {
  let requestedDir: string | undefined;
  await page.route(stateURL, (route) => {
    requestedDir = decodeURIComponent(new URL(route.request().url()).pathname.slice("/api/projects/".length, -"/state".length));
    return route.fulfill({ json: snapshots[name], headers });
  });
  await page.goto(projectURL);
  await expect(page.getByRole("heading", { name: "Проект: Обсерватория" })).toBeVisible();
  expect(requestedDir).toBe(projectDir);
}

test("renders real string steps and nested progress without showing final files early", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await showState(page, "initial");
  await expect(page.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "0");
  await expect(page.getByRole("list", { name: "Шаги проекта" }).getByRole("listitem")).toHaveCount(10);
  await expect(page.locator('[aria-current="step"]')).toContainText("brief");
  await expect(page.getByRole("heading", { name: "Готовые файлы" })).toHaveCount(0);
  expect(errors).toEqual([]);
});

test("selects the first nested concept using state.id and blocks repeat submissions", async ({ page }) => {
  let selected: unknown;
  await page.route(`http://localhost:8000/api/projects/${snapshots.waiting.state.id}/select-concept`, async (route) => {
    if (route.request().method() === "OPTIONS") {
      return route.fulfill({ status: 204, headers: { ...headers, "Access-Control-Allow-Methods": "POST", "Access-Control-Allow-Headers": "content-type" } });
    }
    selected = route.request().postDataJSON();
    await route.fulfill({ json: { status: "ok" }, headers });
  });
  await showState(page, "waiting");
  await expect(page.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "2");
  await expect(page.getByRole("heading", { name: "Концепция 1", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Выбрать", exact: true }).first().click();
  await expect(page.getByRole("status").filter({ hasText: "Выбор отправлен" })).toBeVisible();
  expect(selected).toEqual({ concept_index: 0, run_id: snapshots.waiting.state.run.id });
  await expect(page.getByRole("button", { name: "Выбрать", exact: true })).toHaveCount(0);
});

test("renders selected index zero and real critique, downloads Markdown rather than JSON", async ({ page }, testInfo) => {
  await page.route("http://localhost:8000/api/projects/**/final/*", (route) => route.fulfill({ json: { content: "# Готовый сценарий\nТестовый текст\n" }, headers }));
  await showState(page, "complete");
  await expect(page.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "10");
  await expect(page.getByRole("heading", { name: "Выбранная концепция" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Концепция 1", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Критика — оценка: 8/10" })).toBeVisible();
  await expect(page.getByText("Длинная сцена", { exact: false })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("project-complete.png"), fullPage: true });
  for (const filename of ["script.md", "teleprompter.md"]) {
    const pending = page.waitForEvent("download");
    await page.getByRole("button", { name: filename, exact: true }).click();
    const download = await pending;
    expect(download.suggestedFilename()).toBe(filename);
    expect(await readFile((await download.path())!, "utf8")).toBe("# Готовый сценарий\nТестовый текст\n");
  }
});

test("polling recovers after a network failure", async ({ page }) => {
  let calls = 0;
  await page.route(stateURL, (route) => {
    calls++;
    return calls === 1
      ? route.fulfill({ status: 503, json: { detail: "Временно недоступно" }, headers })
      : route.fulfill({ json: snapshots.waiting, headers });
  });
  await page.goto(projectURL);
  await expect(page.getByRole("alert").filter({ hasText: "Временно недоступно" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Выберите концепцию" })).toBeVisible({ timeout: 10000 });
  await expect(page.getByRole("alert").filter({ hasText: "Временно недоступно" })).toHaveCount(0);
});

test("shows failure and resumes once with the saved project path", async ({ page }) => {
  let resumed = false;
  let calls = 0;
  let requestedPath = "";
  await page.route(stateURL, (route) => route.fulfill({ json: resumed ? snapshots.waiting : snapshots.failed, headers }));
  await page.route("http://localhost:8000/api/projects/**/resume", async (route) => {
    if (route.request().method() === "OPTIONS") return route.fulfill({ status: 204, headers: { ...headers, "Access-Control-Allow-Methods": "POST", "Access-Control-Allow-Headers": "content-type" } });
    calls++;
    requestedPath = decodeURIComponent(new URL(route.request().url()).pathname.slice("/api/projects/".length, -"/resume".length));
    expect(route.request().postDataJSON()).toEqual({});
    await new Promise((resolve) => setTimeout(resolve, 150));
    resumed = true;
    await route.fulfill({ json: { project_id: snapshots.failed.state.id, project_dir: projectDir, run_id: snapshots.waiting.state.run.id }, headers });
  });
  await page.goto(projectURL);
  await expect(page.getByRole("status")).toContainText("завершилось ошибкой");
  await expect(page.getByRole("alert").filter({ hasText: "RuntimeError" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Выбрать", exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: "Повторить с сохранённого шага" }).click();
  await expect(page.getByRole("button", { name: "Запускаем…" })).toBeDisabled();
  await expect(page.getByRole("heading", { name: "Выберите концепцию" })).toBeVisible();
  expect(requestedPath).toBe(projectDir);
  expect(calls).toBe(1);
});

test("a persisted interruption and legacy state require explicit resume", async ({ page }) => {
  for (const name of ["interrupted", "legacy"] as const) {
    await page.unroute(stateURL);
    await page.route(stateURL, (route) => route.fulfill({ json: snapshots[name], headers }));
    await page.goto(projectURL);
    await expect(page.getByRole("button", { name: "Продолжить с сохранённого шага" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Выбрать", exact: true })).toHaveCount(0);
    if (name === "interrupted") await expect(page.getByRole("status")).toContainText("прервано");
  }
});

test("concept submission is scoped to the run and can be made again after a restart", async ({ page }) => {
  let current = structuredClone(snapshots.waiting) as ProjectResponse;
  const selectedRuns: string[] = [];
  await page.route(stateURL, (route) => route.fulfill({ json: current, headers }));
  await page.route("http://localhost:8000/api/projects/*/select-concept", async (route) => {
    if (route.request().method() === "OPTIONS") return route.fulfill({ status: 204, headers: { ...headers, "Access-Control-Allow-Methods": "POST", "Access-Control-Allow-Headers": "content-type" } });
    selectedRuns.push(route.request().postDataJSON().run_id);
    current = { ...current, state: { ...current.state, run: { ...current.state.run!, status: "interrupted", error: "Процесс остановился" } } };
    await route.fulfill({ json: { status: "ok" }, headers });
  });
  await page.route("http://localhost:8000/api/projects/**/resume", async (route) => {
    if (route.request().method() === "OPTIONS") return route.fulfill({ status: 204, headers: { ...headers, "Access-Control-Allow-Methods": "POST", "Access-Control-Allow-Headers": "content-type" } });
    current = structuredClone(snapshots.waiting) as ProjectResponse;
    current.state.run!.id = "new-run-after-restart";
    await route.fulfill({ json: { project_id: current.state.id, project_dir: projectDir, run_id: current.state.run!.id }, headers });
  });
  await page.goto(projectURL);
  await page.getByRole("button", { name: "Выбрать", exact: true }).first().click();
  await page.getByRole("button", { name: "Продолжить с сохранённого шага" }).click();
  await page.getByRole("button", { name: "Выбрать", exact: true }).first().click();
  expect(selectedRuns).toEqual([snapshots.waiting.state.run.id, "new-run-after-restart"]);
});

test("conflicting resume refreshes the active run and never starts another automatically", async ({ page }) => {
  let conflict = false;
  let calls = 0;
  await page.route(stateURL, (route) => route.fulfill({ json: conflict ? snapshots.initial : snapshots.interrupted, headers }));
  await page.route("http://localhost:8000/api/projects/**/resume", async (route) => {
    if (route.request().method() === "OPTIONS") return route.fulfill({ status: 204, headers: { ...headers, "Access-Control-Allow-Methods": "POST", "Access-Control-Allow-Headers": "content-type" } });
    calls++;
    conflict = true;
    await route.fulfill({ status: 409, json: { detail: "Проект уже выполняется" }, headers });
  });
  await page.goto(projectURL);
  await page.getByRole("button", { name: "Продолжить с сохранённого шага" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Проект уже выполняется" })).toBeVisible();
  await expect(page.getByRole("status")).toContainText("Выполняется: brief");
  await expect(page.getByRole("button", { name: "Продолжить с сохранённого шага" })).toHaveCount(0);
  expect(calls).toBe(1);
});

test("creation preserves the absolute returned project path", async ({ page }) => {
  await page.route("http://localhost:8000/api/projects", (route) => route.fulfill({ json: { project_id: snapshots.initial.state.id, project_dir: projectDir }, headers: { ...headers, "Access-Control-Allow-Headers": "content-type" } }));
  let requestedDir: string | undefined;
  await page.route(stateURL, (route) => {
    requestedDir = decodeURIComponent(new URL(route.request().url()).pathname.slice("/api/projects/".length, -"/state".length));
    return route.fulfill({ json: snapshots.initial, headers });
  });
  await page.goto("/");
  await page.getByRole("textbox").first().fill("Тестовая идея");
  await page.getByRole("button", { name: "Создать проект" }).click();
  await expect(page.getByRole("heading", { name: "Проект: Обсерватория" })).toBeVisible();
  expect(requestedDir).toBe(projectDir);
});
