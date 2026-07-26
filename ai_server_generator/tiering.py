"""Product-approved, data-derived memory tiers and recommendations."""

from __future__ import annotations

from typing import Any

from .data import load_profiles
from .presets import ordered_presets


def _fact(profile: dict[str, Any], key: str) -> dict[str, Any]:
    return profile.get("infrastructure", {}).get("facts", {}).get(key, {})


def _measured(profile: dict[str, Any], key: str) -> bool:
    return _fact(profile, key).get("status") == "measured"


def _value(profile: dict[str, Any], key: str) -> Any:
    return _fact(profile, key).get("value")


def footprint(preset: Any) -> float:
    return (
        preset.estimated_model_gb + preset.kv_cache_gb_at_default_context + preset.runtime_buffer_gb
    )


def boundaries() -> list[float]:
    return sorted({footprint(preset) for preset in ordered_presets()})


def usable_budget(profile: dict[str, Any]) -> tuple[float | None, list[str]]:
    if not _measured(profile, "memory.total_gb"):
        return None, ["memory.total_gb"]
    available = _value(profile, "memory.available_gb")
    if not _measured(profile, "memory.available_gb"):
        return None, ["memory.available_gb"]
    values = [float(available)]
    cgroup = _fact(profile, "memory.cgroup_limit_gb")
    if cgroup.get("status") == "measured":
        values.append(float(cgroup["value"]))
    return min(values), []


def derive_tier(profile: dict[str, Any]) -> dict[str, Any]:
    budget, undetermined = usable_budget(profile)
    starts = boundaries()
    if budget is None:
        tier_id, label = "needs-smaller-model", "Needs a smaller model"
    else:
        identifiers = [
            ("start-small", "Start small"),
            ("code-starter", "Code starter"),
            ("everyday-code", "Everyday code"),
            ("deeper-work", "Deeper work"),
            ("full-catalog", "Full catalog"),
        ]
        matched = [index for index, start in enumerate(starts) if budget >= start]
        tier_id, label = (
            identifiers[matched[-1]]
            if matched
            else ("needs-smaller-model", "Needs a smaller model")
        )
    basis = {
        "usable_budget_gb": budget,
        "memory.available_gb": _value(profile, "memory.available_gb"),
        "memory.cgroup_limit_gb": _value(profile, "memory.cgroup_limit_gb"),
        "boundaries_gb": starts,
    }
    if _measured(profile, "cpu.performance_cores"):
        basis["cpu.performance_cores"] = _value(profile, "cpu.performance_cores")
    return {
        "tier_id": tier_id,
        "tier_label": label,
        "tier_model_version": 1,
        "tier_model_status": "provisional-pending-product-signoff",
        "confidence": "high" if not undetermined else "reduced",
        "undetermined_inputs": undetermined,
        "basis": basis,
    }


def recommend(profile: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    budget, undetermined = usable_budget(profile)
    if budget is None:
        return [], [
            {
                "verdict": "NO-FIT",
                "reason": "usable-memory-unknown",
                "basis": {"undetermined_inputs": undetermined},
            }
        ]
    profiles = load_profiles()
    disk = _fact(profile, "disk.free_gb")
    disk_free = float(disk["value"]) if disk.get("status") == "measured" else None
    runnable: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for preset in ordered_presets():
        selected = profiles[preset.default_profile]
        envelope = float(str(selected["mem_limit"]).rstrip("gG"))
        required = footprint(preset)
        item = {
            "alias": preset.alias,
            "selected_profile": preset.default_profile,
            "context": preset.default_context,
            "mem_limit": selected["mem_limit"],
            "cpus": selected["cpu_limit"],
            "pids_limit": 256,
            "basis": {
                "estimated_model_gb": preset.estimated_model_gb,
                "kv_cache_gb_at_default_context": preset.kv_cache_gb_at_default_context,
                "runtime_buffer_gb": preset.runtime_buffer_gb,
                "footprint_gb": required,
                "usable_budget_gb": budget,
                "disk_free_gb": disk_free,
                "disk_required_gb": round(preset.estimated_model_gb * 1.1, 3),
            },
        }
        if budget < required:
            item.update(verdict="NO-FIT", reason="memory-fit")
            excluded.append(item)
        elif envelope < required:
            item.update(
                verdict="NO-FIT",
                reason="profile-envelope",
                next_action="Choose a profile/runtime envelope that covers the planning footprint before serving this preset.",
            )
            excluded.append(item)
        elif disk_free is None:
            item.update(verdict="NO-FIT", reason="disk-unknown")
            excluded.append(item)
        elif disk_free < preset.estimated_model_gb * 1.1:
            item.update(verdict="NO-FIT", reason="disk-insufficient")
            excluded.append(item)
        else:
            item["verdict"] = "FIT"
            runnable.append(item)
    return runnable, excluded
