import type { ProjectData } from "./api";

export function projectView(data: ProjectData) {
  const { state, total_steps } = data;
  const currentStep = Math.max(0, Math.min(state.current_step, total_steps));
  const concepts = state.concepts?.concepts ?? [];
  const needsSelection = data.steps[currentStep] === "select_concept"
    && state.selected_concept_index === null && concepts.length > 0;

  return {
    currentStep,
    progress: total_steps > 0 ? (currentStep / total_steps) * 100 : 0,
    isDone: total_steps > 0 && currentStep >= total_steps,
    concepts,
    needsSelection,
    selectedConcept: state.selected_concept_index === null
      ? null : concepts[state.selected_concept_index] ?? null,
    steps: data.steps.map((name, index) => ({
      name,
      status: index < currentStep ? "done" : index > currentStep ? "pending"
        : needsSelection ? "waiting" : "running",
    })),
  };
}
