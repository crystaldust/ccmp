"""Read/modify/write ~/.claude/settings.json without clobbering user content."""

from __future__ import annotations

import json
import os
import shutil
import time
from copy import deepcopy
from pathlib import Path

import json5

# env vars ccmp owns inside the settings `env` block
OWNED_ENV_KEYS = [
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "CLAUDE_CODE_SUBAGENT_MODEL",
]

# profile `models` field -> env var
MODEL_ENV_MAP = {
    "default": "ANTHROPIC_MODEL",
    "sonnet": "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "opus": "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "haiku": "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "subagent": "CLAUDE_CODE_SUBAGENT_MODEL",
}


def settings_path(claude_config_dir: Path | str | None = None) -> Path:
    if claude_config_dir is not None:
        return Path(claude_config_dir).expanduser() / "settings.json"
    env = os.environ.get("CLAUDE_CONFIG_DIR")
    if env:
        return Path(env).expanduser() / "settings.json"
    return Path.home() / ".claude" / "settings.json"


def load(path: Path | str) -> dict:
    """Load settings.json, tolerating JSON5 comments / trailing commas."""
    p = Path(path)
    if not p.exists():
        return {}
    text = p.read_text(encoding="utf-8")
    try:
        return json5.loads(text)
    except Exception:
        return json.loads(text)  # last-resort strict JSON


def apply_profile(settings: dict, helper_cmd: str, profile: dict) -> dict:
    """Return a copy of `settings` with ccmp-owned keys pointing at `profile`."""
    new = deepcopy(settings)
    new["apiKeyHelper"] = helper_cmd
    env = dict(new.get("env", {}))
    for key in OWNED_ENV_KEYS:
        env.pop(key, None)
    env["ANTHROPIC_BASE_URL"] = profile["base_url"]
    for field, envvar in MODEL_ENV_MAP.items():
        value = (profile.get("models") or {}).get(field)
        if value:
            env[envvar] = value
    for key, value in (profile.get("extra_env") or {}).items():
        env[key] = value
    new["env"] = env
    return new


def clear_provider(settings: dict) -> dict:
    """Return a copy of `settings` with ccmp-owned keys removed (back to official)."""
    new = deepcopy(settings)
    new.pop("apiKeyHelper", None)
    env = dict(new.get("env", {}))
    for key in OWNED_ENV_KEYS:
        env.pop(key, None)
    if env:
        new["env"] = env
    else:
        new.pop("env", None)
    return new


def save(path: Path | str, settings: dict, backups_dir: Path | str) -> None:
    """Back up the existing file, then atomically write the new one."""
    p = Path(path)
    if p.exists():
        bdir = Path(backups_dir)
        bdir.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d-%H%M%S")
        shutil.copy2(p, bdir / f"settings-{ts}.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    os.replace(tmp, p)
