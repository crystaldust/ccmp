import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from ccmp import keychain


@unittest.skipUnless(shutil.which("security"), "macOS `security` CLI required")
class KeychainTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.kc = Path(self.tmp.name) / "t.keychain-db"
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

    def test_add_get_delete_roundtrip(self):
        keychain.add("ccmp:t", "default", "secret-123", keychain=self.kc)
        self.assertEqual(keychain.get("ccmp:t", "default", keychain=self.kc), "secret-123")
        self.assertTrue(keychain.exists("ccmp:t", "default", keychain=self.kc))
        self.assertTrue(keychain.delete("ccmp:t", "default", keychain=self.kc))
        self.assertFalse(keychain.exists("ccmp:t", "default", keychain=self.kc))

    def test_get_missing_raises(self):
        with self.assertRaises(keychain.KeychainError):
            keychain.get("ccmp:nope", "default", keychain=self.kc)
