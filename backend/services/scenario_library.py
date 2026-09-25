"""Structured scenario library backed by backend/data/scenarios.json.

Provides fast lookup by id, category, or keyword so the frontend
and demo tooling can drive test flows from structured data rather
than hard-coded strings.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "scenarios.json"

_scenarios: list[dict[str, Any]] = []


def _load() -> list[dict[str, Any]]:
    try:
        return json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def all_scenarios() -> list[dict[str, Any]]:
    global _scenarios
    if not _scenarios:
        _scenarios = _load()
    return _scenarios


def get_scenario(scenario_id: str) -> dict[str, Any] | None:
    return next((s for s in all_scenarios() if s["id"] == scenario_id), None)


def scenarios_by_category(category: str) -> list[dict[str, Any]]:
    return [s for s in all_scenarios() if s["category"] == category]


def categories() -> list[str]:
    seen: list[str] = []
    for s in all_scenarios():
        if s["category"] not in seen:
            seen.append(s["category"])
    return seen
