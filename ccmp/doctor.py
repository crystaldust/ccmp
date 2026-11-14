"""`ccmp doctor`: validate the local setup and report problems."""

from __future__ import annotations

import os
import platform
import shutil
from typing import Any

from . import keychain, settings, state


def _check(ok: bool, label: str, detail: str = "") -> dict[str, Any]:
    return {"ok": ok, "label": label, "detail": detail}


def run() -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    checks.append(_check(platform.system() == "Darwin", "running on macOS"))
    checks.append(
        _check(shutil.which("security") is not None, "`security` CLI is present")
    )

    st = state.load_state()
    current = st.get("current")
    checks.append(
        _check(bool(current), "an active profile is set", current or "no profile selected")
    )

    if current:
        profile = state.get_profile(st, current)
        if profile:
            svc, acct = _keychain_ref(current, profile)
            try:
                value = keychain.get(svc, acct)
                checks.append(_check(bool(value), "Keychain item is readable", f"{svc}/{acct}"))
            except keychain.KeychainError as e:
                checks.append(_check(False, "Keychain item is readable", str(e)))

    for var in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL", "ANTHROPIC_MODEL"):
        if var in os.environ:
            checks.append(_check(False, f"shell env `{var}` is set", "it overrides settings.json"))

    spath = settings.settings_path()
    if spath.exists():
        data = settings.load(spath)
        env = data.get("env", {})
        has_helper = "apiKeyHelper" in data
        has_key = "ANTHROPIC_API_KEY" in env or "ANTHROPIC_AUTH_TOKEN" in env
        if has_helper and has_key:
            checks.append(
                _check(
                    False,
                    "settings.json has BOTH apiKeyHelper and a key env var",
                    "the two credential headers would disagree",
                )
            )
        else:
            checks.append(_check(True, "settings.json credential source is unambiguous"))
        checks.append(_check(has_helper, "apiKeyHelper is configured", data.get("apiKeyHelper", "")))
    else:
        checks.append(_check(False, "settings.json exists", str(spath)))

    return checks


def render(checks: list[dict[str, Any]]) -> str:
    lines = []
    for c in checks:
        mark = "ok " if c["ok"] else "FAIL"
        line = f"[{mark}] {c['label']}"
        if c["detail"]:
            line += f"  ({c['detail']})"
        lines.append(line)
    return "\n".join(lines)


def _keychain_ref(profile_name: str, profile: dict[str, Any]) -> tuple[str, str]:
    kc = profile.get("keychain", {})
    return kc.get("service", f"ccmp:{profile_name}"), kc.get("account", "default")
