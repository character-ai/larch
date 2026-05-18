#!/usr/bin/env bash
# measure-md-cost.sh - Measure markdown file size and token cost by load tier.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
OUT_DIR="$REPO_ROOT/larch-logs/measure-md-cost"
STAMP="${LARCH_MEASURE_DATE:-$(date +%Y-%m-%d)}"
OUT_FILE="$OUT_DIR/$STAMP.tsv"

mkdir -p "$OUT_DIR"

python3 - "$REPO_ROOT" "$OUT_FILE" <<'PY'
import os
import pathlib
import subprocess
import sys
import tempfile

try:
    import tiktoken
except Exception as exc:  # pragma: no cover - environment diagnostic
    raise SystemExit(f"measure-md-cost.sh: tiktoken is required: {exc}")

repo = pathlib.Path(sys.argv[1])
out_path = pathlib.Path(sys.argv[2])
enc = tiktoken.get_encoding("cl100k_base")

def git_files(pattern):
    data = subprocess.check_output(
        ["git", "-C", str(repo), "ls-files", "-z", pattern],
        stderr=subprocess.DEVNULL,
    )
    return [p.decode("utf-8") for p in data.split(b"\0") if p]

def claude_imports():
    imports = set()
    claude = repo / "CLAUDE.md"
    if not claude.exists():
        return imports
    for line in claude.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped.startswith("@"):
            target = stripped[1:].split()[0]
            if target.endswith(".md") and not target.startswith("/"):
                imports.add(target)
    return imports

tier1_imports = claude_imports()

def classify(path):
    if path == "CLAUDE.md":
        return "tier-1a-claude-root"
    if path in tier1_imports:
        return "tier-1a-claude-import"
    if path.startswith("skills/") and path.endswith("/SKILL.md"):
        return "tier-1b-runtime-skill"
    if path.startswith(".claude/skills/") and path.endswith("/SKILL.md"):
        return "tier-1b-dev-skill"
    if path.startswith(".claude/rules/") and path.endswith(".md"):
        return "tier-1c-claude-rule"
    if path.startswith("skills/shared/"):
        return "tier-2-shared-reference"
    if "/references/" in path:
        return "tier-2-skill-reference"
    if path.startswith("scripts/"):
        return "tier-2-script-doc"
    if path.startswith("docs/"):
        return "tier-3-doc"
    if path.startswith("larch-logs/"):
        return "tier-4-run-log"
    return "tier-3-other"

rows = []
for rel in git_files("*.md"):
    file_path = repo / rel
    if not file_path.is_file():
        continue
    raw = file_path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    rows.append((
        rel,
        classify(rel),
        len(raw),
        len(enc.encode(text)),
        0 if text == "" else text.count("\n") + (0 if text.endswith("\n") else 1),
        sum(1 for line in text.splitlines() if line.startswith("## ")),
    ))

rows.sort(key=lambda row: (row[1], row[0]))
out_path.parent.mkdir(parents=True, exist_ok=True)
fd, tmp_name = tempfile.mkstemp(prefix=".tmp.measure-md-cost.", dir=str(out_path.parent), text=True)
with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
    fh.write("path\ttier\tbytes\ttokens\tlines\th2_count\n")
    for row in rows:
        fh.write("%s\t%s\t%d\t%d\t%d\t%d\n" % row)
os.replace(tmp_name, out_path)
PY

printf 'WROTE\t%s\n' "${OUT_FILE#"$REPO_ROOT"/}"
