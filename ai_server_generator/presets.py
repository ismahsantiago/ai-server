from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPreset:
    alias: str
    name: str
    summary: str
    capability_tags: tuple[str, ...]
    memory_guidance: str
    default_setup: str = "chat"
    default_profile: str = "medium"
    default_access: str = "localhost"

    @property
    def default_model_path(self) -> str:
        return f"./models/{self.alias}.gguf"


MODEL_PRESETS: dict[str, ModelPreset] = {
    "ornith-9b": ModelPreset(
        alias="ornith-9b",
        name="Ornith 1.0 (9B)",
        summary="agentic code specialist",
        capability_tags=("code", "agentic", "tool-use"),
        memory_guidance="Recommended: 7-9 GB RAM budget for stable local serving.",
    ),
    "devstral-small-v25.07": ModelPreset(
        alias="devstral-small-v25.07",
        name="Devstral Small (v25.07)",
        summary="rapid development and multimodal",
        capability_tags=("development", "multimodal", "latency"),
        memory_guidance="Recommended: 6-8 GB RAM budget for responsive local workflows.",
    ),
    "qwen3-coder-7b": ModelPreset(
        alias="qwen3-coder-7b",
        name="Qwen 3 Coder (7B)",
        summary="coding efficiency",
        capability_tags=("code", "completion", "throughput"),
        memory_guidance="Recommended: 6-8 GB RAM budget for coding-focused workloads.",
    ),
    "smollm3-3b": ModelPreset(
        alias="smollm3-3b",
        name="SmolLM 3 (3B)",
        summary="ultralight multitask",
        capability_tags=("lightweight", "multitask", "low-memory"),
        memory_guidance="Recommended: 4-6 GB RAM budget for ultralight serving.",
        default_profile="medium-fast",
    ),
    "phi-4-14b": ModelPreset(
        alias="phi-4-14b",
        name="Phi-4 (14B)",
        summary="general reasoning max limit",
        capability_tags=("reasoning", "general", "max-limit"),
        memory_guidance="Recommended: 10-12 GB RAM budget; watch headroom on 12 GB hosts.",
        default_profile="good",
    ),
}


PRESET_ORDER = [
    "ornith-9b",
    "devstral-small-v25.07",
    "qwen3-coder-7b",
    "smollm3-3b",
    "phi-4-14b",
]


def ordered_presets() -> list[ModelPreset]:
    return [MODEL_PRESETS[alias] for alias in PRESET_ORDER]


def resolve_preset(alias: str) -> ModelPreset:
    if alias not in MODEL_PRESETS:
        raise ValueError(f"unknown preset: {alias}")
    return MODEL_PRESETS[alias]
