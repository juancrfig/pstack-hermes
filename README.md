# pstack for Hermes

[pstack](https://github.com/cursor/plugins/tree/main/pstack) by Lauren Tan (MIT), packaged as a Hermes plugin.

The skills are a byte-for-byte copy of upstream. Two changes, both the same ones upstream makes for its Claude Code tree:

1. One line after the H1 of each skill that uses Cursor names. It tells the agent to load `pstack:hermes-adapter` once per session.
2. A relative link to a file the copy leaves out becomes a GitHub link.

`adapter/hermes-adapter/SKILL.md` is the only hand-written file. It maps Cursor tool, subagent, model and path names to Hermes.

## Install

    hermes plugins install juancrfig/pstack-hermes
    hermes plugins enable pstack

Skills are `pstack:<name>`, for example `pstack:poteto-mode`.

## Keep it current

    python3 scripts/sync.py --update    # fetch upstream, rebuild pstack/, record the commit in UPSTREAM
    python3 scripts/sync.py --check     # fail if pstack/ drifted from upstream
    python3 -m unittest discover -s tests

`sync.py` fails when a skill uses a Cursor name the adapter has no row for, so a new upstream name cannot slip through unmapped.

## Hermes features pstack assumes

`delegate_task` needs per-task `model`, `reasoning_effort` and `readonly` for pstack's model-per-role and read-only subagents. Stock Hermes lacks them. The adapter says what to do without them (use the configured model, ask the child not to edit, check `git status`).
