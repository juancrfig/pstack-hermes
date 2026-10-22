#!/usr/bin/env python3
"""Build the Hermes copy of pstack from the upstream repo, the way upstream builds its Claude Code tree.

The copy is byte for byte, except for two things upstream does as well:
  1. one adapter line after the H1 of every skill that uses Cursor names;
  2. a relative link to a file the copy leaves out becomes a GitHub link.

  sync.py --update   fetch cursor/plugins into .upstream, rebuild pstack/, record the commit in UPSTREAM
  sync.py            rebuild pstack/ from the commit already in .upstream
  sync.py --check    fail if pstack/ differs from what the rebuild would write (no writes)
"""

import os
import posixpath
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UPSTREAM_DIR = ROOT / ".upstream"
UPSTREAM_URL = "https://github.com/cursor/plugins.git"
OUT = ROOT / "pstack"
GITHUB = "https://github.com/cursor/plugins"
ADAPTER_SRC = ROOT / "adapter" / "hermes-adapter" / "SKILL.md"
LINE = (
    'In Hermes, load the **hermes-adapter** skill with `skill_view(name="pstack:hermes-adapter")` once per '
    "session before you follow this skill. It maps the Cursor names in pstack skills to Hermes."
)
LINK = re.compile(r"\]\(([^)\s]+)\)")
SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# (key the adapter must mention, regex that detects the Cursor name). Same list as upstream's generator.
TERMS = [
    ("`Task`", r"`Task`|\bTask (tool|subagent|call)"),
    ("`AskQuestion`", r"AskQuestion"),
    ("todolist", r"(?i)\btodo ?list\b"),
    ("generalPurpose", r"generalPurpose"),
    ("poteto-agent", r"poteto-agent"),
    ("comment-sicko", r"comment-sicko"),
    ("`readonly: true`", r"readonly: (true|false)|readonly/Ask"),
    ('`environment: "cloud"`', r'environment: "(cloud|local)"'),
    ("cloud_base_branch", r"cloud_base_branch"),
    ("`run_in_background: true`", r"run_in_background"),
    ("`resume`", r"`resume`"),
    ("`file_attachments`", r"file_attachments"),
    ("claude-", r"\bclaude-[a-z]+-\d"),
    ("grok-", r"\bgrok-\d"),
    ("gpt-", r"\bgpt-\d"),
    ("inherit-parent", r"inherit-parent"),
    ("pstack-models.mdc", r"pstack-models\.mdc"),
    (".cursor/skills/", r"\.cursor/skills"),
    ("~/.cursor/plugins/", r"\.cursor/plugins|\.cursor-plugin"),
    (".cursor/rules/", r"\.cursor/rules|always-applied rule"),
    ("agent-transcripts", r"agent-transcripts|\.cursor/projects"),
    ("Cursor-only features", r"Bugbot|Cursor [Aa]utomation|cursor\.(sh|com)/automations|[Cc]loud [Aa]gent|built-in PR tool"),
]
ROUTE_KEY = "Run another pstack skill"


def walk(d: Path):
    for p in sorted(d.rglob("*")):
        if p.is_file() and p.name != ".DS_Store" and "node_modules" not in p.parts:
            yield p


def git(*args, cwd=None):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def fetch_upstream():
    if not (UPSTREAM_DIR / ".git").exists():
        subprocess.run(["git", "clone", "-q", UPSTREAM_URL, str(UPSTREAM_DIR)], check=True)
    else:
        git("fetch", "-q", "origin", "main", cwd=UPSTREAM_DIR)
        git("checkout", "-q", "--detach", "origin/main", cwd=UPSTREAM_DIR)
    return git("rev-parse", "HEAD", cwd=UPSTREAM_DIR)


def build(src: Path) -> dict[str, tuple[bytes, bool]]:
    """Return {relative path in pstack/: (bytes, executable)} for the Hermes copy."""
    ps = src / "pstack"
    skills_dir = ps / "skills"
    skills = sorted(p.name for p in skills_dir.iterdir() if (p / "SKILL.md").is_file())
    adapter = ADAPTER_SRC.read_text(encoding="utf-8")

    problems, users, wrap = [], {}, {}
    for skill in skills:
        d = skills_dir / skill
        others = "|".join(re.escape(s) for s in skills if s != skill)
        route = re.compile(rf"the \*\*(?P<bold>{others})\*\* skill|`/(?P<command>{others})`")
        uses = set()
        for p in (p for p in walk(d) if p.suffix == ".md"):
            text = p.read_text(encoding="utf-8")
            for key, rx in TERMS:
                if re.search(rx, text):
                    uses.add(key)
            for line in text.split("\n"):
                if any(f"(../{(m.group('bold') or m.group('command'))}/" not in line for m in route.finditer(line)):
                    uses.add(ROUTE_KEY)
        text = (d / "SKILL.md").read_text(encoding="utf-8")
        wrap[skill] = bool(uses) and bool(re.search(r"^# ", text, re.M))
        if uses and not wrap[skill]:
            problems.append(f"skills/{skill}/SKILL.md uses Cursor names but has no H1")
        for k in uses:
            users.setdefault(k, []).append(skill)
        fm = re.match(r"^---\n(.*?)\n---", text, re.S)
        name = re.search(r"^name:(.*)$", fm.group(1), re.M).group(1).strip().strip("\"'") if fm else None
        if name != skill:
            problems.append(f"skills/{skill}/SKILL.md has name {name!r}, not its folder name")
        if not SKILL_NAME.match(skill) or len(skill) > 64:
            problems.append(f"skills/{skill} is not a valid skill name")
    for key, using in users.items():
        if key != ROUTE_KEY and key not in adapter:
            problems.append(f"adapter has no row for {key}, used by {', '.join(using)}")
    if ROUTE_KEY not in adapter:
        problems.append(f"adapter has no row for {ROUTE_KEY}")
    if problems:
        sys.exit("\n".join(f"FAIL {p}" for p in problems))

    sources = [*walk(skills_dir), *walk(ps / "agents"), *walk(ps / "docs" / "guide"), ps / "README.md", ps / "LICENSE", ps / "plugin.json"]
    files = {str(p.relative_to(ps)): [p.read_bytes(), bool(p.stat().st_mode & 0o111)] for p in sources}
    for skill, w in wrap.items():
        if w:
            path = f"skills/{skill}/SKILL.md"
            text = files[path][0].decode()
            files[path][0] = re.sub(r"^(# .*)\n+", lambda m: f"{m.group(1)}\n\n{LINE}\n\n", text, count=1, flags=re.M).encode()

    def resolve(frm, href):
        target = re.sub(r"[#?].*", "", href)
        if not target or re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I):
            return None
        path = posixpath.normpath(posixpath.join(posixpath.dirname(frm), target))
        return path if (ps / path).exists() else None

    def has(path):
        return path in files or any(k.startswith(path + "/") for k in files)

    for path, entry in files.items():
        if not path.endswith(".md"):
            continue

        def fix(m):
            href = m.group(1)
            target = resolve(path, href)
            if not target or target.split("/")[0] == ".." or has(target):
                return m.group(0)
            kind = "tree" if (ps / target).is_dir() else "blob"
            tail = re.search(r"[#?].*", href)
            return f"]({GITHUB}/{kind}/main/pstack/{target}{tail.group(0) if tail else ''})"

        entry[0] = LINK.sub(fix, entry[0].decode()).encode()
    for path, entry in files.items():
        if path.endswith(".md"):
            for m in LINK.finditer(entry[0].decode()):
                t = resolve(path, m.group(1))
                if t and not has(t):
                    sys.exit(f"FAIL {path} links to {m.group(1)}, which is not in the copy")
    return {k: (v[0], v[1]) for k, v in files.items()}


def on_disk():
    return {str(p.relative_to(OUT)): (p.read_bytes(), bool(p.stat().st_mode & 0o111)) for p in walk(OUT)} if OUT.exists() else {}


def main():
    args = set(sys.argv[1:])
    sha = fetch_upstream() if "--update" in args else git("rev-parse", "HEAD", cwd=UPSTREAM_DIR)
    want = build(UPSTREAM_DIR)
    if "--check" in args:
        have = on_disk()
        drift = sorted(k for k in set(want) | set(have) if want.get(k) != have.get(k))
        for k in drift[:20]:
            print(f"pstack/{k}")
        if drift:
            sys.exit(f"pstack/ differs from upstream {sha[:10]} in {len(drift)} files. Run scripts/sync.py.")
        print(f"pstack/ matches upstream {sha[:10]}: {len(want)} files.")
        return
    shutil.rmtree(OUT, ignore_errors=True)
    for k, (data, exe) in want.items():
        p = OUT / k
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        os.chmod(p, 0o755 if exe else 0o644)
    (ROOT / "UPSTREAM").write_text(f"{UPSTREAM_URL} {sha}\n")
    version = re.search(r'"version":\s*"([^"]+)"', (OUT / "plugin.json").read_text()).group(1)
    manifest = (ROOT / "plugin.yaml").read_text()
    (ROOT / "plugin.yaml").write_text(re.sub(r'^version:.*$', f'version: "{version}"', manifest, flags=re.M))
    print(f"{len(want)} files from upstream {sha[:10]}, pstack {version}")


if __name__ == "__main__":
    main()
