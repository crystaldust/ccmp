import unittest

from ccmp import models


class ModelsTest(unittest.TestCase):
    def test_glm_template_uses_1m_context(self):
        glm = models.TEMPLATES["glm"]
        for field in ("default", "sonnet", "opus", "haiku", "subagent"):
            self.assertTrue(glm["models"][field].endswith("[1m]"), f"{field}: {glm['models'][field]}")
        self.assertEqual(glm["extra_env"]["CLAUDE_CODE_AUTO_COMPACT_WINDOW"], "1000000")

    def test_every_template_has_base_url_and_default_model(self):
        for name, tpl in models.TEMPLATES.items():
            self.assertTrue(tpl["base_url"], name)
            self.assertTrue(tpl["models"].get("default"), name)
