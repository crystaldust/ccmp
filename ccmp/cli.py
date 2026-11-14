"""ccmp command-line interface."""

from __future__ import annotations

import argparse
import getpass
import json as _json
import shlex
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from . import __version__, doctor, keychain, models, settings, state


class CCMPError(Exception):
    pass


def _ccmp_executable() -> str:
    exe = shutil.which("ccmp")
    if exe:
        return shlex.quote(exe)
    # Running from a source checkout: use the dev launcher, which sets PYTHONPATH.
    launcher = Path(__file__).resolve().parent.parent / "bin" / "ccmp"
    if launcher.exists():
        return shlex.quote(str(launcher))
    return f"{shlex.quote(sys.executable)} -m ccmp"


def _helper_command() -> str:
    return f"{_ccmp_executable()} key"


def _keychain_ref(profile_name: str, profile: dict[str, Any]) -> tuple[str, str]:
    kc = profile.get("keychain", {})
    return kc.get("service", f"ccmp:{profile_name}"), kc.get("account", "default")


def _require_profile(st: dict[str, Any], name: str) -> dict[str, Any]:
    profile = state.get_profile(st, name)
    if profile is None:
        raise CCMPError(f"profile '{name}' does not exist")
    return profile


def cmd_add(args: argparse.Namespace) -> int:
    st = state.load_state()
    if args.name in state.profile_names(st):
        raise CCMPError(f"profile '{args.name}' already exists")

    template = None
    if args.template:
        template = models.TEMPLATES.get(args.template)
        if template is None:
            raise CCMPError(
                f"unknown template '{args.template}' (available: {', '.join(models.TEMPLATES)})"
            )

    base_url = args.base_url or (template or {}).get("base_url") or input("Base URL: ").strip()
    if not base_url:
        raise CCMPError("base_url is required")

    profile: dict[str, Any] = {
        "base_url": base_url,
        "keychain": {"service": f"ccmp:{args.name}", "account": "default"},
        "models": dict((template or {}).get("models", {})),
        "extra_env": dict((template or {}).get("extra_env", {})),
    }
    if not profile["models"].get("default"):
        model = args.model
        if model is None and sys.stdin.isatty():
            model = input("Default model (e.g. glm-5.3): ").strip() or None
        if model:
            profile["models"]["default"] = model
            profile["models"].setdefault("sonnet", model)
            profile["models"].setdefault("opus", model)
        else:
            raise CCMPError("provide --template or --model (or edit later with `ccmp config`)")

    secret = args.key
    if secret is None and args.key_stdin:
        secret = sys.stdin.read().strip()
    if secret is None:
        secret = getpass.getpass("API key (hidden): ").strip()
    if not secret:
        raise CCMPError("API key is required")

    keychain.add(f"ccmp:{args.name}", "default", secret)
    state.add_profile(st, args.name, profile)
    state.save_state(st)
    print(f"added profile '{args.name}' (key stored in Keychain)")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    st = state.load_state()
    if not st["profiles"]:
        print("no profiles yet — run `ccmp add <name>`")
        return 0
    width = max(len(n) for n in st["profiles"])
    for name in sorted(st["profiles"]):
        mark = "*" if st["current"] == name else " "
        prof = st["profiles"][name]
        svc, acct = _keychain_ref(name, prof)
        ready = "key ok" if keychain.exists(svc, acct) else "key MISSING"
        default_model = prof.get("models", {}).get("default", "-")
        print(f"{mark} {name:<{width}}  {prof.get('base_url','')!s:<52}  {default_model}  {ready}")
    return 0


def cmd_use(args: argparse.Namespace) -> int:
    st = state.load_state()
    spath = settings.settings_path()
    if args.name == "official":
        state.set_current(st, None)
        state.save_state(st)
        data = settings.load(spath)
        settings.save(spath, settings.clear_provider(data), state.backups_dir())
        print("switched to official Claude Code (subscription / OAuth)")
        print("note: settings are read at startup — restart `claude`")
        return 0

    profile = _require_profile(st, args.name)
    svc, acct = _keychain_ref(args.name, profile)
    if not keychain.exists(svc, acct):
        raise CCMPError(
            f"no API key in Keychain for '{args.name}' — run `ccmp add {args.name}` again"
        )
    state.set_current(st, args.name)
    state.save_state(st)
    data = settings.load(spath)
    settings.save(
        spath, settings.apply_profile(data, _helper_command(), profile), state.backups_dir()
    )
    print(f"switched to '{args.name}' ({profile.get('base_url')})")
    print("note: settings are read at startup — restart `claude`")
    return 0


def cmd_current(args: argparse.Namespace) -> int:
    st = state.load_state()
    if not st["current"]:
        print("no active profile (using official Claude Code)")
        return 0
    name = st["current"]
    prof = st["profiles"][name]
    print(f"current: {name}")
    print(f"  base_url: {prof.get('base_url')}")
    for field, envvar in settings.MODEL_ENV_MAP.items():
        value = prof.get("models", {}).get(field)
        if value:
            print(f"  {field:<8} ({envvar}) -> {value}")
    return 0


def cmd_remove(args: argparse.Namespace) -> int:
    st = state.load_state()
    if args.name not in state.profile_names(st):
        raise CCMPError(f"profile '{args.name}' does not exist")
    prof = st["profiles"][args.name]
    svc, acct = _keychain_ref(args.name, prof)
    keychain.delete(svc, acct)
    state.remove_profile(st, args.name)
    state.save_state(st)
    print(f"removed profile '{args.name}'")
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    st = state.load_state()
    profile = _require_profile(st, args.name)
    if args.key == "base_url":
        profile["base_url"] = args.value
    elif args.key.startswith("models."):
        profile.setdefault("models", {})[args.key.split(".", 1)[1]] = args.value
    else:
        raise CCMPError(f"unknown config key '{args.key}' (try base_url or models.<field>)")
    state.save_state(st)
    print(f"updated {args.name}.{args.key} = {args.value}")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    checks = doctor.run()
    print(doctor.render(checks))
    return 0 if all(c["ok"] for c in checks) else 1


def cmd_test(args: argparse.Namespace) -> int:
    st = state.load_state()
    name = args.name or st["current"]
    if not name:
        raise CCMPError("no active profile")
    profile = _require_profile(st, name)
    svc, acct = _keychain_ref(name, profile)
    secret = keychain.get(svc, acct)
    base = profile["base_url"].rstrip("/")
    body = _json.dumps(
        {
            "model": profile.get("models", {}).get("default", ""),
            "max_tokens": 16,
            "messages": [{"role": "user", "content": "ping"}],
        }
    ).encode()
    req = urllib.request.Request(
        base + "/v1/messages",
        data=body,
        headers={
            "content-type": "application/json",
            "x-api-key": secret,
            "authorization": f"Bearer {secret}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"OK ({resp.status}) — endpoint reachable, auth accepted")
            return 0
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode()[:200]}")
        return 1
    except Exception as e:  # noqa: BLE001 - report any transport error
        print(f"error: {e}")
        return 1


def cmd_key(args: argparse.Namespace) -> int:
    """Internal: print the active profile's key to stdout only (for apiKeyHelper)."""
    st = state.load_state()
    name = args.name or st["current"]
    if not name:
        sys.stderr.write("ccmp: no active profile\n")
        return 1
    profile = _require_profile(st, name)
    svc, acct = _keychain_ref(name, profile)
    try:
        sys.stdout.write(keychain.get(svc, acct) + "\n")
        return 0
    except keychain.KeychainError as e:
        sys.stderr.write(f"ccmp: {e}\n")
        return 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ccmp",
        description="Switch Claude Code model providers; API keys in the macOS Keychain.",
    )
    p.add_argument("--version", action="version", version=f"ccmp {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="add a provider profile")
    a.add_argument("name")
    a.add_argument("--template", choices=list(models.TEMPLATES), help="use a built-in template")
    a.add_argument("--base-url", help="Anthropic-compatible base URL")
    a.add_argument("--model", help="default model (also used for sonnet/opus when unset)")
    a.add_argument("--key", help="API key (prefer --key-stdin to avoid shell history)")
    a.add_argument("--key-stdin", action="store_true", help="read API key from stdin")
    a.set_defaults(func=cmd_add)

    sub.add_parser("list", help="list profiles").set_defaults(func=cmd_list)

    u = sub.add_parser("use", help="switch to a profile (or 'official')")
    u.add_argument("name")
    u.set_defaults(func=cmd_use)

    sub.add_parser("current", help="show the active profile").set_defaults(func=cmd_current)

    r = sub.add_parser("remove", help="remove a profile")
    r.add_argument("name")
    r.set_defaults(func=cmd_remove)

    c = sub.add_parser("config", help="edit a profile field")
    c.add_argument("name")
    c.add_argument("key")
    c.add_argument("value")
    c.set_defaults(func=cmd_config)

    sub.add_parser("doctor", help="check the local setup").set_defaults(func=cmd_doctor)

    t = sub.add_parser("test", help="send a minimal request to the active profile")
    t.add_argument("name", nargs="?")
    t.set_defaults(func=cmd_test)

    k = sub.add_parser("key", help="print the active profile's key (internal)")
    k.add_argument("name", nargs="?")
    k.set_defaults(func=cmd_key)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except CCMPError as e:
        print(f"ccmp: error: {e}", file=sys.stderr)
        return 1
    except keychain.KeychainUnavailable as e:
        print(f"ccmp: {e}", file=sys.stderr)
        return 1
