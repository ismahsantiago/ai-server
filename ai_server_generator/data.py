from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILE_ORDER = ["medium-fast", "medium", "good"]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def profiles_dir() -> Path:
    return PROJECT_ROOT / "profiles"


def manifests_dir() -> Path:
    return PROJECT_ROOT / "manifests"


def templates_dir() -> Path:
    return PROJECT_ROOT / "templates"


def load_profiles() -> dict[str, dict[str, Any]]:
    profiles: dict[str, dict[str, Any]] = {}
    for path in profiles_dir().glob("*.json"):
        data = load_json(path)
        profiles[data["name"]] = data
    return profiles


def ordered_profile_names() -> list[str]:
    profiles = load_profiles()
    preferred = [name for name in PROFILE_ORDER if name in profiles]
    remaining = sorted(name for name in profiles if name not in PROFILE_ORDER)
    return preferred + remaining


def load_setups() -> dict[str, dict[str, Any]]:
    setups: dict[str, dict[str, Any]] = {}
    for path in manifests_dir().glob("*.json"):
        data = load_json(path)
        setups[data["name"]] = data
    return setups


def setup_listing_names() -> list[str]:
    names: list[str] = []
    for setup_name, setup in sorted(load_setups().items()):
        default_profile = setup.get("default_profile", "medium")
        if "localhost" in setup.get("supported_access", []):
            names.append(f"{setup_name}-localhost-{default_profile}")
        names.append(setup_name)
    return names
