"""End-to-end test: the settings shape ccmp produces actually drives Claude Code.

Skips automatically when the `claude` CLI is not installed.
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from ccmp import settings
from mock_provider import MockProvider


@unittest.skipUnless(shutil.which("claude"), "claude CLI not installed")
class IntegrationTest(unittest.TestCase):
    def test_claude_sends_helper_key(self):
        mp = MockProvider().start()
        self.addCleanup(mp.stop)

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        ccdir = Path(tmp.name) / "cfg"
        ccdir.mkdir()

        helper = Path(tmp.name) / "getkey.sh"
        helper.write_text('#!/bin/sh\necho "sk-integration"\n')
        helper.chmod(0o755)

        prof = {"base_url": f"http://127.0.0.1:{mp.port}", "models": {"default": "m"}}
        data = settings.apply_profile({}, str(helper), prof)
        settings.save(ccdir / "settings.json", data, Path(tmp.name) / "bak")

        env = dict(os.environ, CLAUDE_CONFIG_DIR=str(ccdir))
        r = subprocess.run(
            ["claude", "-p", "hi"],
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        self.assertTrue(mp.requests, "claude never hit the mock provider")
        self.assertEqual(mp.requests[0]["authorization"], "Bearer sk-integration")
        self.assertEqual(mp.requests[0]["x_api_key"], "sk-integration")
