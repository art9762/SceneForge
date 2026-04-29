"""SceneForge CLI — interactive pipeline runner."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import IntPrompt

from core.pipeline import Pipeline
from core.schemas.project import ProjectState
from core.config import get_settings

app = typer.Typer(
    name="sceneforge",
    help="🎬 SceneForge — AI writers' room for video scripts",
    no_args_is_help=True,
)
console = Console()


async def _select_concept(state: ProjectState) -> int:
    """Interactive concept selection in CLI."""
    console.print("\n[bold yellow]Выберите концепцию:[/bold yellow]\n")
    for i, c in enumerate(state.concepts.concepts):
        console.print(Panel(
            f"[bold]{c.name}[/bold]\n\n"
            f"[italic]{c.logline}[/italic]\n\n"
            f"{c.synopsis}\n\n"
            f"[dim]Направление: {c.direction} | Тон: {c.tone_description}[/dim]\n"
            f"[dim]Почему работает: {c.why_it_works}[/dim]",
            title=f"Концепция {i + 1}",
            border_style="cyan",
        ))

    choice = IntPrompt.ask(
        "\nВведите номер концепции",
        choices=[str(i + 1) for i in range(len(state.concepts.concepts))],
    )
    return choice - 1


@app.command()
def run(
    idea: str = typer.Argument(..., help="Сырая идея для сценария"),
    project_name: str = typer.Option(None, "--name", "-n", help="Название проекта (папки)"),
    provider: str = typer.Option("claude", "--provider", "-p", help="LLM провайдер: claude или openai"),
    model: str = typer.Option(None, "--model", "-m", help="Модель (по умолчанию из конфига)"),
):
    """Запустить полный пайплайн генерации сценария."""
    settings = get_settings()
    name = project_name or idea[:40].replace(" ", "-").lower()
    project_dir = Path(settings.projects_dir) / name

    console.print(Panel(
        f"[bold]{idea}[/bold]",
        title="🎬 SceneForge — Новый проект",
        border_style="green",
    ))

    pipeline = Pipeline(
        project_dir=project_dir,
        provider_name=provider,
        model=model,
        on_select_concept=_select_concept,
    )

    state = asyncio.run(pipeline.run(raw_idea=idea))

    console.print(f"\n[bold green]Результат сохранён в: {project_dir}/final/[/bold green]")
    console.print(f"  • script.md — полный сценарий")
    console.print(f"  • teleprompter.md — текст для озвучки")


@app.command()
def resume(
    project_path: str = typer.Argument(..., help="Путь к папке проекта"),
    provider: str = typer.Option("claude", "--provider", "-p"),
    model: str = typer.Option(None, "--model", "-m"),
):
    """Продолжить незавершённый проект."""
    project_dir = Path(project_path)
    if not (project_dir / "project.json").exists():
        console.print("[red]project.json не найден в указанной папке[/red]")
        raise typer.Exit(1)

    pipeline = Pipeline(
        project_dir=project_dir,
        provider_name=provider,
        model=model,
        on_select_concept=_select_concept,
    )

    asyncio.run(pipeline.run())
    console.print(f"\n[bold green]Готово! Результат в: {project_dir}/final/[/bold green]")


@app.command()
def status(
    project_path: str = typer.Argument(..., help="Путь к папке проекта"),
):
    """Показать статус проекта."""
    project_dir = Path(project_path)
    state_file = project_dir / "project.json"
    if not state_file.exists():
        console.print("[red]Проект не найден[/red]")
        raise typer.Exit(1)

    state = ProjectState.load(state_file)
    steps = [
        "Бриф", "Концепции", "Выбор концепции", "Структура",
        "Черновик v1", "Критика", "Черновик v2", "Продакшн",
        "Монтажные заметки", "Финальная сборка",
    ]

    console.print(Panel(
        f"ID: {state.id}\n"
        f"Идея: {state.raw_idea[:80]}...\n"
        f"Шаг: {state.current_step}/{len(steps)}\n"
        f"Создан: {state.created_at}\n"
        f"Обновлён: {state.updated_at}",
        title="📋 Статус проекта",
        border_style="blue",
    ))

    for i, name in enumerate(steps):
        if i < state.current_step:
            console.print(f"  [green]✓[/green] {name}")
        elif i == state.current_step:
            console.print(f"  [yellow]→[/yellow] {name}")
        else:
            console.print(f"  [dim]○[/dim] {name}")


if __name__ == "__main__":
    app()
