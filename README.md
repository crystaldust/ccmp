# ccmp

Switch [Claude Code](https://claude.com/claude-code) between model providers from the
command line, with API keys stored in the **macOS Keychain** instead of plaintext
config files.

```console
$ ccmp add glm --template glm          # prompt for the API key (hidden)
$ ccmp use glm
$ ccmp list
$ ccmp doctor
```

## Why

Claude Code reads its provider from `~/.claude/settings.json` (`ANTHROPIC_BASE_URL`,
model names, and a credential). `ccmp` manages those keys for you, and keeps the API
key itself out of the file entirely — it is stored in the macOS Keychain and handed to
Claude Code through the `apiKeyHelper` mechanism, which reads the key on demand.

## Install

From source (dev):

```console
$ python3 -m pip install -e .
```

From PyPI (once published):

```console
$ pipx install ccmp
```

## Commands

| Command | Description |
| --- | --- |
| `ccmp add <name>` | Add a provider (interactive; key is hidden, stored in Keychain) |
| `ccmp list` | List profiles (key shown masked / present-or-missing only) |
| `ccmp use <name>` | Switch to a profile |
| `ccmp use official` | Restore the official Claude subscription / OAuth |
| `ccmp current` | Show the active profile |
| `ccmp remove <name>` | Remove a profile and its Keychain item |
| `ccmp config <name> <key> <value>` | Edit `base_url` or `models.<field>` |
| `ccmp doctor` | Check the local setup for conflicts |
| `ccmp test [name]` | Send a minimal request to verify key + endpoint |
| `ccmp key` | Print the active profile's key (internal, used by `apiKeyHelper`) |

Built-in templates: `deepseek`, `glm`, `kimi`, `ark` (Volcengine Ark), `bailian`
(Alibaba Model Studio). Use `--template` with `add`, then override any field with
`config`.

## Supported platforms

- **macOS**: full support (API keys in Keychain).
- **Windows / Linux**: on the backlog — currently `ccmp` exits with a clear error.

## Security notes

- API keys live in the macOS Keychain (service `ccmp:<profile>`), never in
  `settings.json` or `profiles.json`.
- The Keychain item is created with `-A` (any local application may read it without a
  GUI prompt). This trades a bit of strictness for a working headless flow; the key is
  still not stored in plaintext on disk.
- `ccmp` only edits the keys it owns inside `settings.json` (`apiKeyHelper` plus the
  `ANTHROPIC_*` env vars). Everything else you have there is preserved, and every
  change is backed up to `~/.config/ccmp/backups/` first.

## Scope

`ccmp` manages local configuration and static key storage. It is not a proxy and does
not change any provider's terms of service or regional eligibility rules.

## Development

```console
$ python3 -m unittest discover -s tests
```
