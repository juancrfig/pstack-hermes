"""pstack for Hermes: registers the upstream skills untouched and injects the role-to-model rule."""

import logging
from pathlib import Path

ROOT = Path(__file__).parent
TREE = ROOT / "pstack"
ADAPTER = ROOT / "adapter" / "hermes-adapter" / "SKILL.md"
logger = logging.getLogger(__name__)


def _model_rule_path() -> Path:
    from hermes_constants import get_hermes_home
    return Path(get_hermes_home()) / "rules" / "pstack-models.md"


def _inject_model_rule(is_first_turn=False, **_):
    """The Hermes counterpart of Cursor's always-applied pstack-models rule: show it once per session."""
    if not is_first_turn:
        return None
    path = _model_rule_path()
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return f"pstack model rule ({path}):\n{text}" if text else None


def register(ctx):
    for skill_dir in sorted(p for p in (TREE / "skills").iterdir() if (p / "SKILL.md").is_file()):
        ctx.register_skill(skill_dir.name, skill_dir / "SKILL.md")
    ctx.register_skill("hermes-adapter", ADAPTER)
    ctx.register_hook("pre_llm_call", _inject_model_rule)
