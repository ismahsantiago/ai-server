"""Shared assertions for the optional real-kernel doctor container check."""
from __future__ import annotations

import json
import sys
from typing import Any

SKIPPED = "SKIPPED: no reachable Docker daemon"


def validate_output(payload: str) -> str:
    """Validate a doctor JSON document, or preserve the explicit skip outcome."""
    if payload.strip() == SKIPPED:
        return SKIPPED
    profile: dict[str, Any] = json.loads(payload)
    facts = profile["infrastructure"]["facts"]
    assert facts["execution.in_container"]["value"] is True
    assert facts["memory.cgroup_limit_gb"]["status"] == "measured"
    assert abs(float(facts["memory.cgroup_limit_gb"]["value"]) - 2.0) < 0.1
    source = str(facts["execution.in_container"]["source"])
    assert "dockerenv" in source or "cgroup-v2-cap" in source
    assert "cgroup-name" not in source
    assert facts["execution.observation_scope"]["value"] == "container-on-virtualized-host"
    assert facts["memory.total_gb"]["status"] == "unknown"
    assert facts["memory.vm_total_gb"]["status"] == "measured"
    assert facts["memory.total_gb"]["value"] != facts["memory.cgroup_limit_gb"]["value"]
    return f"doctor container check: cgroup memory limit {facts['memory.cgroup_limit_gb']['value']} scope {facts['execution.observation_scope']['value']}"


def main() -> int:
    print(validate_output(sys.stdin.read()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
