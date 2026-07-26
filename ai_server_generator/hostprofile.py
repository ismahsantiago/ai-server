"""Assembly and deterministic serialization of host profiles."""

from __future__ import annotations

import json
import platform
from datetime import datetime, timezone
from typing import Any

from .hostprobe import Fact
from .readiness import evaluate
from .tiering import derive_tier, recommend


def _safe_text(value: object) -> object:
    if isinstance(value, str) and (
        value.startswith("/") or value.startswith("~") or "/Users/" in value or "/home/" in value
    ):
        return "[redacted]"
    return value


def assemble(
    facts: dict[str, Fact],
    *,
    supported: bool = True,
    generated_at: str | None = None,
    platform_info: dict[str, object] | None = None,
) -> dict[str, Any]:
    safe_facts = {
        key: {field: _safe_text(item) for field, item in value.json().items()}
        for key, value in facts.items()
    }
    details = platform_info or {
        "system": platform.system(),
        "machine": platform.machine(),
        "python_version": platform.python_version(),
    }
    document: dict[str, Any] = {
        "host_profile_version": 1,
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "platform": {**details, "supported": supported},
        "infrastructure": {"facts": safe_facts, "execution_context": {}},
        "software_readiness": {
            "gaps": [],
            "summary": {"blocking": 0, "degraded": 0, "advisory": 0},
        },
        "recommendations": {"runnable_presets": [], "excluded_presets": []},
        "notes": [],
    }
    if supported:
        document["recommendations"]["tier"] = derive_tier(document)
        run, excluded = recommend(document)
        document["recommendations"]["runnable_presets"] = run
        document["recommendations"]["excluded_presets"] = excluded
    gaps = evaluate(document)
    document["software_readiness"]["gaps"] = [gap.json() for gap in gaps]
    for gap in gaps:
        document["software_readiness"]["summary"][gap.severity] += 1
    document["notes"] = [
        f"{key}: {_safe_text(value.source)}"
        for key, value in facts.items()
        if value.status == "unknown"
    ]
    return document


def serialize(profile: dict[str, Any]) -> str:
    return json.dumps(profile, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
