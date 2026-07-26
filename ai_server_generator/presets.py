from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPreset:
    alias: str
    name: str
    summary: str
    capability_tags: tuple[str, ...]
    memory_guidance: str
    architecture: str
    parameter_billions: float
    quantization_assumption: str
    estimated_model_gb: float
    kv_cache_gb_at_default_context: float
    runtime_buffer_gb: float
    minimum_host_ram_gb: float
    recommended_host_ram_gb: float
    default_context: int
    artifact_repository: str | None = None
    artifact_revision: str | None = None
    artifact_filename: str | None = None
    artifact_size_bytes: int | None = None
    artifact_sha256: str | None = None
    chat_template: str | None = None
    metadata_status: str = "planning-assumption-only"
    contract_version: int = 2
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
        architecture="unknown-9b-family",
        parameter_billions=9.0,
        quantization_assumption="Q4-class planning assumption; operator artifact not pinned",
        estimated_model_gb=5.5,
        kv_cache_gb_at_default_context=1.0,
        runtime_buffer_gb=1.0,
        minimum_host_ram_gb=10.0,
        recommended_host_ram_gb=12.0,
        default_context=4096,
    ),
    "devstral-small-v25.07": ModelPreset(
        alias="devstral-small-v25.07",
        name="Devstral Small (v25.07)",
        summary="rapid development and multimodal",
        capability_tags=("development", "multimodal", "latency"),
        memory_guidance="Recommended: 6-8 GB RAM budget for responsive local workflows.",
        architecture="mistral-24b-family",
        parameter_billions=24.0,
        quantization_assumption="Q4-class planning assumption; operator artifact not pinned",
        estimated_model_gb=14.5,
        kv_cache_gb_at_default_context=1.5,
        runtime_buffer_gb=1.5,
        minimum_host_ram_gb=20.0,
        recommended_host_ram_gb=24.0,
        default_context=4096,
    ),
    "qwen3-coder-7b": ModelPreset(
        alias="qwen3-coder-7b",
        name="Qwen 3 Coder (7B)",
        summary="coding efficiency",
        capability_tags=("code", "completion", "throughput"),
        memory_guidance="Recommended: 6-8 GB RAM budget for coding-focused workloads.",
        architecture="qwen-7b-family",
        parameter_billions=7.0,
        quantization_assumption="Q4-class planning assumption; operator artifact not pinned",
        estimated_model_gb=4.8,
        kv_cache_gb_at_default_context=1.0,
        runtime_buffer_gb=1.0,
        minimum_host_ram_gb=9.5,
        recommended_host_ram_gb=12.0,
        default_context=4096,
    ),
    "smollm3-3b": ModelPreset(
        alias="smollm3-3b",
        name="SmolLM 3 (3B)",
        summary="ultralight multitask",
        capability_tags=("lightweight", "multitask", "low-memory"),
        memory_guidance="Recommended: 4-6 GB RAM budget for ultralight serving.",
        architecture="smollm-3b-family",
        parameter_billions=3.0,
        quantization_assumption="Q4-class planning assumption; operator artifact not pinned",
        estimated_model_gb=2.0,
        kv_cache_gb_at_default_context=0.5,
        runtime_buffer_gb=0.75,
        minimum_host_ram_gb=6.0,
        recommended_host_ram_gb=8.0,
        default_context=2048,
        default_profile="medium-fast",
    ),
    "phi-4-14b": ModelPreset(
        alias="phi-4-14b",
        name="Phi-4 (14B)",
        summary="general reasoning max limit",
        capability_tags=("reasoning", "general", "max-limit"),
        memory_guidance="Recommended: 10-12 GB RAM budget; watch headroom on 12 GB hosts.",
        architecture="phi-4-14b-family",
        parameter_billions=14.0,
        quantization_assumption="Q4-class planning assumption; operator artifact not pinned",
        estimated_model_gb=9.0,
        kv_cache_gb_at_default_context=1.5,
        runtime_buffer_gb=1.25,
        minimum_host_ram_gb=14.0,
        recommended_host_ram_gb=16.0,
        default_context=6144,
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
