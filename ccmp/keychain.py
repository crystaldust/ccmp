"""macOS Keychain access through the `security` CLI.

Only macOS is supported today; Windows and Linux are on the backlog. Tests point at a
throwaway keychain file via the CCMP_KEYCHAIN environment variable so they never touch
the user's login keychain.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


class KeychainError(Exception):
    pass


class KeychainUnavailable(KeychainError):
    pass


def _security_bin() -> str:
    path = shutil.which("security")
    if path is None:
        raise KeychainUnavailable(
            "`security` not found — only macOS Keychain is supported. "
            "Windows/Linux support is on the backlog."
        )
    return path


def _resolve_keychain(keychain: Path | str | None) -> Path | None:
    if keychain is not None:
        return Path(keychain)
    env = os.environ.get("CCMP_KEYCHAIN")
    return Path(env) if env else None


def _run(args: list[str], keychain: Path | str | None) -> subprocess.CompletedProcess:
    full = [_security_bin(), *args]
    kc = _resolve_keychain(keychain)
    if kc is not None:
        full.append(str(kc))
    return subprocess.run(full, capture_output=True, text=True)


def add(
    service: str, account: str, secret: str, keychain: Path | str | None = None
) -> None:
    """Store a secret. ``-A`` allows any local app to read it without a GUI prompt."""
    r = _run(
        ["add-generic-password", "-a", account, "-s", service, "-w", secret, "-U", "-A"],
        keychain,
    )
    if r.returncode != 0:
        raise KeychainError(f"failed to store key in Keychain: {r.stderr.strip()}")


def get(service: str, account: str, keychain: Path | str | None = None) -> str:
    r = _run(["find-generic-password", "-a", account, "-s", service, "-w"], keychain)
    if r.returncode != 0:
        raise KeychainError(f"no Keychain item '{service}/{account}': {r.stderr.strip()}")
    return r.stdout.strip()


def delete(service: str, account: str, keychain: Path | str | None = None) -> bool:
    r = _run(["delete-generic-password", "-a", account, "-s", service], keychain)
    return r.returncode == 0


def exists(service: str, account: str, keychain: Path | str | None = None) -> bool:
    try:
        get(service, account, keychain)
        return True
    except KeychainError:
        return False
