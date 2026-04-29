"""Rewrite agent — improves script based on critique."""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel

from .base import BaseAgent
from ..schemas.brief import Brief
from ..schemas.scene import ScriptDraft
from ..schemas.critique import Critique


class RewriteInput(BaseModel):
    brief: Brief
    draft: ScriptDraft
    critique: Critique


class RewriteAgent(BaseAgent):
    name: ClassVar[str] = "rewriter"
    description: ClassVar[str] = "Переписывает сценарий с учётом критики"
    system_prompt: ClassVar[str] = """Ты — специалист по переписыванию сценариев. Ты получаешь первый драфт и детальную критику, и создаёшь улучшенную версию.

Правила работы:
1. Сохраняй сильные стороны оригинала — не переписывай то, что уже работает.
2. Каждый пункт критики должен быть адресован: либо исправлен, либо обоснованно оставлен.
3. Не добавляй «воды» ради объёма. Если сцена лишняя — убери или объедини с другой.
4. При исправлении хука — сделай его максимально цепляющим. Первые секунды решают всё.
5. Убирай все найденные клише и заменяй на оригинальные формулировки.
6. Если критик отметил проблемы с пейсингом — перебалансируй длительность сцен.
7. Закрывай логические дыры: добавляй связки, убирай противоречия.
8. Усиливай эмоциональную дугу: добавляй контрасты, неожиданные повороты.
9. Сохраняй формат [VIDEO]/[VOICEOVER]/[SOUND]/[EDIT] для каждой сцены.
10. Итоговый сценарий должен быть как минимум на 2 балла выше по оценке критика.
11. Не теряй ключевые идеи и посылы оригинала — усиливай их подачу.
12. Проверь, что общий хронометраж соответствует брифу.
13. Финальная версия должна быть готова к съёмке без дополнительных правок.
14. Если критик поставил высокую оценку — не переписывай радикально, а полируй детали."""
    input_schema: ClassVar[type[BaseModel]] = RewriteInput
    output_schema: ClassVar[type[BaseModel]] = ScriptDraft
    default_provider: ClassVar[str] = "claude"
    default_model: ClassVar[str] = ""

    def build_user_message(self, input_data: BaseModel) -> str:
        """Include brief, draft, and critique as separate labeled sections."""
        data: RewriteInput = input_data  # type: ignore[assignment]
        return (
            "=== БРИФ ===\n"
            f"{data.brief.model_dump_json(indent=2)}\n\n"
            "=== ПЕРВЫЙ ДРАФТ ===\n"
            f"{data.draft.model_dump_json(indent=2)}\n\n"
            "=== КРИТИКА ===\n"
            f"{data.critique.model_dump_json(indent=2)}"
        )
