import os
import shutil
import subprocess
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest import mock

from ccmp import cli, settings


@unittest.skipUnless(shutil.which("security"), "macOS `security` CLI required")
class CliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.home = root / "ccmp-home"
        self.ccdir = root / "claude-config"
        self.kc = root / "t.keychain-db"
        subprocess.run(
            ["security", "create-keychain", "-p", "test", str(self.kc)],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["security", "unlock-keychain", "-p", "test", str(self.kc)],
            check=True,
            capture_output=True,
        )
        self.addCleanup(
            lambda: subprocess.run(
                ["security", "delete-keychain", str(self.kc)], capture_output=True
            )
        )
        self._old_env = {
            k: os.environ.get(k) for k in ("CCMP_HOME", "CLAUDE_CONFIG_DIR", "CCMP_KEYCHAIN")
        }
        os.environ["CCMP_HOME"] = str(self.home)
        os.environ["CLAUDE_CONFIG_DIR"] = str(self.ccdir)
        os.environ["CCMP_KEYCHAIN"] = str(self.kc)
        self.addCleanup(self._restore_env)

    def _restore_env(self):
        for k, v in self._old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_add_use_current_key_roundtrip(self):
        self.assertEqual(
            cli.main(
                ["add", "glm", "--base-url", "https://open.bigmodel.cn/api/anthropic", "--model", "glm-5.3", "--key", "sk-test"]
            ),
            0,
        )
        self.assertEqual(cli.main(["use", "glm"]), 0)
        self.assertEqual(cli.main(["current"]), 0)

        data = settings.load(settings.settings_path())
        self.assertIn("apiKeyHelper", data)
        self.assertEqual(data["env"]["ANTHROPIC_BASE_URL"], "https://open.bigmodel.cn/api/anthropic")

        buf = StringIO()
        with mock.patch("sys.stdout", buf):
            self.assertEqual(cli.main(["key"]), 0)
        self.assertEqual(buf.getvalue().strip(), "sk-test")

    def test_use_unknown_profile_errors(self):
        self.assertEqual(cli.main(["use", "nope"]), 1)

    def test_use_official_clears_provider(self):
        cli.main(["add", "glm", "--base-url", "https://x", "--model", "m", "--key", "sk"])
        cli.main(["use", "glm"])
        self.assertEqual(cli.main(["use", "official"]), 0)
        data = settings.load(settings.settings_path())
        self.assertNotIn("apiKeyHelper", data)
        self.assertNotIn("ANTHROPIC_BASE_URL", data.get("env", {}))

    def test_add_duplicate_errors(self):
        cli.main(["add", "glm", "--base-url", "https://x", "--model", "m", "--key", "sk"])
        self.assertEqual(cli.main(["add", "glm", "--base-url", "https://x", "--model", "m", "--key", "sk"]), 1)

    def test_helper_uses_dev_launcher_when_not_installed(self):
        with mock.patch("ccmp.cli.shutil.which", return_value=None):
            self.assertIn("bin/ccmp", cli._helper_command())

    def test_helper_prefers_installed_ccmp(self):
        with mock.patch("ccmp.cli.shutil.which", return_value="/opt/bin/ccmp"):
            self.assertEqual(cli._helper_command(), "/opt/bin/ccmp key")
