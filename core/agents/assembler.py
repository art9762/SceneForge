"""Final assembler — combines all pipeline outputs into final deliverables."""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel

from .base import BaseAgent
from ..schemas.project import ProjectState


class AssemblerInput(BaseModel):
    project: ProjectState


class AssemblerOutput(BaseModel):
    script_markdown: str = ""
    teleprompter_text: str = ""


class FinalAssembler(BaseAgent):
    name: ClassVar[str] = "assembler"
    description: ClassVar[str] = "Собирает все данные проекта в финальный markdown и текст для телесуфлёра"
    system_prompt: ClassVar[str] = ""
    input_schema: ClassVar[type[BaseModel]] = AssemblerInput
    output_schema: ClassVar[type[BaseModel]] = AssemblerOutput
    default_provider: ClassVar[str] = "claude"
    default_model: ClassVar[str] = ""

    async def run(self, input_data: BaseModel, provider=None, model=None) -> AssemblerOutput:
        """Assemble final output without calling LLM."""
        data: AssemblerInput = input_data  # type: ignore[assignment]
        project = data.project

        # Build script markdown
        lines: list[str] = []
        lines.append(f"# {project.brief.title if project.brief else 'Без названия'}\n")

        if project.brief:
            lines.append("## Бриф\n")
            lines.append(f"- **Формат:** {project.brief.format}")
            lines.append(f"- **Хронометраж:** {project.brief.duration_minutes} мин")
            lines.append(f"- **Аудитория:** {project.brief.target_audience}")
            lines.append(f"- **Тон:** {project.brief.tone}")
            lines.append(f"- **Платформа:** {project.brief.platform}")
            lines.append(f"- **Цель:** {project.brief.goal}")
            lines.append("")

        # Use v2 draft if available, otherwise v1
        draft = project.draft_v2 or project.draft_v1
        if draft:
            lines.append("## Сценарий\n")
            for scene in draft.scenes:
                lines.append(f"### Сцена {scene.scene_number}: {scene.title}\n")
                if scene.video:
                    lines.append(f"**[VIDEO]** {scene.video}\n")
                if scene.voiceover:
                    lines.append(f"**[VOICEOVER]** {scene.voiceover}\n")
                if scene.sound:
                    lines.append(f"**[SOUND]** {scene.sound}\n")
                if scene.edit_notes:
                    lines.append(f"**[EDIT]** {scene.edit_notes}\n")
                if scene.duration_hint:
                    lines.append(f"*Хронометраж: {scene.duration_hint}*\n")
                lines.append("")

        if project.production_notes:
            pn = project.production_notes
            lines.append("## Продакшн\n")
            if pn.locations:
                lines.append("### Локации")
                for loc in pn.locations:
                    lines.append(f"- {loc}")
                lines.append("")
            if pn.props:
                lines.append("### Реквизит")
                for prop in pn.props:
                    lines.append(f"- {prop}")
                lines.append("")
            if pn.archive_footage:
                lines.append("### Архивные кадры")
                for af in pn.archive_footage:
                    lines.append(f"- {af}")
                lines.append("")
            if pn.graphics:
                lines.append("### Графика")
                for g in pn.graphics:
                    lines.append(f"- {g}")
                lines.append("")

        if project.edit_notes:
            en = project.edit_notes
            lines.append("## Монтажные заметки\n")
            if en.music_notes:
                lines.append(f"**Музыка:** {en.music_notes}\n")
            if en.sound_design:
                lines.append("### Звуковой дизайн")
                for s in en.sound_design:
                    lines.append(f"- {s}")
                lines.append("")
            if en.transitions:
                lines.append("### Переходы")
                for t in en.transitions:
                    lines.append(f"- {t}")
                lines.append("")

        script_markdown = "\n".join(lines)

        # Build teleprompter text (voiceover only, clean)
        teleprompter_lines: list[str] = []
        if draft:
            for scene in draft.scenes:
                if scene.voiceover:
                    teleprompter_lines.append(scene.voiceover)
                    teleprompter_lines.append("")

        teleprompter_text = "\n".join(teleprompter_lines).strip()

        return AssemblerOutput(
            script_markdown=script_markdown,
            teleprompter_text=teleprompter_text,
        )
