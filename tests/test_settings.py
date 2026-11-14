import json
import tempfile
import unittest
from pathlib import Path

from ccmp import settings


class SettingsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def test_apply_profile_sets_helper_and_env(self):
        prof = {"base_url": "https://x", "models": {"default": "m", "haiku": "h"}}
        out = settings.apply_profile({}, "ccmp key", prof)
        self.assertEqual(out["apiKeyHelper"], "ccmp key")
        self.assertEqual(out["env"]["ANTHROPIC_BASE_URL"], "https://x")
        self.assertEqual(out["env"]["ANTHROPIC_MODEL"], "m")
        self.assertEqual(out["env"]["ANTHROPIC_DEFAULT_HAIKU_MODEL"], "h")
        self.assertNotIn("ANTHROPIC_DEFAULT_OPUS_MODEL", out["env"])

    def test_apply_profile_preserves_unknown_keys(self):
        src = {"model": "x", "env": {"FOO": "bar"}, "permissions": {"allow": ["a"]}}
        out = settings.apply_profile(src, "ccmp key", {"base_url": "https://x", "models": {}})
        self.assertEqual(out["model"], "x")
        self.assertEqual(out["env"]["FOO"], "bar")
        self.assertEqual(out["permissions"]["allow"], ["a"])

    def test_apply_profile_removes_old_owned_env(self):
        src = {"env": {"ANTHROPIC_MODEL": "old", "KEEP": "1"}}
        out = settings.apply_profile(src, "ccmp key", {"base_url": "https://x", "models": {}})
        self.assertNotIn("ANTHROPIC_MODEL", out["env"])
        self.assertEqual(out["env"]["KEEP"], "1")

    def test_clear_provider(self):
        src = {"apiKeyHelper": "x", "env": {"ANTHROPIC_BASE_URL": "u", "KEEP": "1"}}
        out = settings.clear_provider(src)
        self.assertNotIn("apiKeyHelper", out)
        self.assertNotIn("ANTHROPIC_BASE_URL", out["env"])
        self.assertEqual(out["env"]["KEEP"], "1")

    def test_load_json5_with_comments(self):
        p = self.dir / "s.json"
        p.write_text('{"env": { // note\n "ANTHROPIC_BASE_URL": "https://x", } }')
        self.assertEqual(settings.load(p)["env"]["ANTHROPIC_BASE_URL"], "https://x")

    def test_save_backs_up_and_writes(self):
        p = self.dir / "settings.json"
        p.write_text('{"a":1}')
        bdir = self.dir / "bak"
        settings.save(p, {"b": 2}, bdir)
        self.assertEqual(json.loads(p.read_text()), {"b": 2})
        self.assertEqual(len(list(bdir.glob("settings-*.json"))), 1)
