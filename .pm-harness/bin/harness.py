#!/usr/bin/env python3
"""harness.py — PM Harness CLI (engine 2.1.0 / pm-pack 2.6.0).

Shim only (CORE-SPEC §E.1): configuration + pack registrations live in the
SpecPack; every contract is implemented by harness_core.
"""
import json
import os
import sys

_BIN = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BIN)
import harness_core
import private_split

PACK = json.load(open(os.path.join(_BIN, "pack-config.json")))
PACK["messages"] = json.load(open(os.path.join(_BIN, "locale.json")))


def register(core):
    private_split.register(core)


if __name__ == "__main__":
    harness_core.main(pack=sys.modules[__name__])
