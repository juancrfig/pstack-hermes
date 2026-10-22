import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_plugin():
    spec = importlib.util.spec_from_file_location("pstack_plugin", ROOT / "__init__.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Ctx:
    def __init__(self):
        self.skills, self.hooks = {}, {}

    def register_skill(self, name, path, **_):
        assert Path(path).is_file()
        self.skills[name] = path

    def register_hook(self, name, fn):
        self.hooks[name] = fn


class PluginTest(unittest.TestCase):
    def test_copy_matches_upstream(self):
        if not (ROOT / ".upstream" / ".git").exists():
            self.skipTest("run scripts/sync.py --update first")
        out = subprocess.run([sys.executable, str(ROOT / "scripts" / "sync.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)

    def test_every_upstream_skill_is_registered(self):
        ctx = Ctx()
        load_plugin().register(ctx)
        on_disk = {p.name for p in (ROOT / "pstack" / "skills").iterdir() if (p / "SKILL.md").is_file()}
        self.assertEqual(set(ctx.skills) - {"hermes-adapter"}, on_disk)
        self.assertIn("hermes-adapter", ctx.skills)
        self.assertGreaterEqual(len(on_disk), 50)

    def test_model_rule_is_injected_on_first_turn_only(self):
        mod = load_plugin()
        with tempfile.TemporaryDirectory() as home:
            rule = Path(home) / "rules" / "pstack-models.md"
            rule.parent.mkdir()
            rule.write_text("# budget: large\nhow: opus xhigh\n")
            mod._model_rule_path = lambda: rule
            self.assertIn("how: opus xhigh", mod._inject_model_rule(is_first_turn=True))
            self.assertIsNone(mod._inject_model_rule(is_first_turn=False))
            rule.unlink()
            self.assertIsNone(mod._inject_model_rule(is_first_turn=True))


if __name__ == "__main__":
    unittest.main()
