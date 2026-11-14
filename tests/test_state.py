import tempfile
import unittest
from pathlib import Path

from ccmp import state


class StateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "profiles.json"

    def test_load_default_when_missing(self):
        self.assertEqual(state.load_state(self.path), state.DEFAULT_STATE)

    def test_roundtrip(self):
        st = state.load_state(self.path)
        state.add_profile(st, "glm", {"base_url": "https://x"})
        state.set_current(st, "glm")
        state.save_state(st, self.path)
        got = state.load_state(self.path)
        self.assertEqual(got["current"], "glm")
        self.assertIn("glm", got["profiles"])

    def test_add_duplicate_raises(self):
        st = state.load_state(self.path)
        state.add_profile(st, "a", {})
        with self.assertRaises(ValueError):
            state.add_profile(st, "a", {})

    def test_set_current_unknown_raises(self):
        st = state.load_state(self.path)
        with self.assertRaises(ValueError):
            state.set_current(st, "nope")

    def test_remove_clears_current(self):
        st = state.load_state(self.path)
        state.add_profile(st, "a", {})
        state.set_current(st, "a")
        state.remove_profile(st, "a")
        self.assertIsNone(st["current"])
