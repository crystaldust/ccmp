"""Persistent ccmp state: profiles.json and the active-profile marker."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

DEFAULT_STATE: dict[str, Any] = {"version": 1, "current": None, "profiles": {}}


def ccmp_home() -> Path:
    """Directory holding ccmp state; overridable via CCMP_HOME (used by tests)."""
    env = os.environ.get("CCMP_HOME")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".config" / "ccmp"


def profiles_path() -> Path:
    return ccmp_home() / "profiles.json"


def backups_dir() -> Path:
    return ccmp_home() / "backups"


def load_state(path: Path | str | None = None) -> dict[str, Any]:
    p = Path(path) if path is not None else profiles_path()
    if not p.exists():
        return deepcopy(DEFAULT_STATE)
    data = json.loads(p.read_text(encoding="utf-8"))
    for key, value in DEFAULT_STATE.items():
        data.setdefault(key, value)
    return data


def save_state(state: dict[str, Any], path: Path | str | None = None) -> None:
    """Atomically write profiles.json (temp file + os.replace)."""
    p = Path(path) if path is not None else profiles_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    os.replace(tmp, p)


def profile_names(state: dict[str, Any]) -> list[str]:
    return list(state["profiles"].keys())


def get_profile(state: dict[str, Any], name: str) -> dict[str, Any] | None:
    return state["profiles"].get(name)


def add_profile(state: dict[str, Any], name: str, profile: dict[str, Any]) -> None:
    if name in state["profiles"]:
        raise ValueError(f"profile '{name}' already exists")
    state["profiles"][name] = profile


def remove_profile(state: dict[str, Any], name: str) -> None:
    if name not in state["profiles"]:
        raise ValueError(f"profile '{name}' does not exist")
    del state["profiles"][name]
    if state["current"] == name:
        state["current"] = None


def set_current(state: dict[str, Any], name: str | None) -> None:
    if name is not None and name not in state["profiles"]:
        raise ValueError(f"profile '{name}' does not exist")
    state["current"] = name
