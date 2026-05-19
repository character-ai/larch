#!/usr/bin/env bash
# measure-realized-cost.sh - Estimate realized SKILL.md load cost from run logs.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
OUT_DIR="$REPO_ROOT/larch-logs/measure-realized-cost"
STAMP="${LARCH_MEASURE_DATE:-$(date +%Y-%m-%d)}"
OUT_FILE="$OUT_DIR/$STAMP.tsv"

mkdir -p "$OUT_DIR"

python3 - "$REPO_ROOT" "$OUT_FILE" <<'PY'
import collections
import json
import os
import pathlib
import sys
import tempfile

try:
    import tiktoken
except Exception as exc:  # pragma: no cover - environment diagnostic
    raise SystemExit(f"measure-realized-cost.sh: tiktoken is required: {exc}")

repo = pathlib.Path(sys.argv[1])
out_path = pathlib.Path(sys.argv[2])
enc = tiktoken.get_encoding("cl100k_base")
invocations = collections.Counter()
issues_by_skill = collections.defaultdict(set)

def normalize_skill(raw):
    if not raw:
        return ""
    skill = str(raw)
    if skill.startswith("larch:"):
        skill = skill.split(":", 1)[1]
    if skill.startswith("inferred:"):
        return ""
    return skill

def manifest_issue(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    issue = data.get("issue_number")
    return str(issue) if isinstance(issue, int) or (isinstance(issue, str) and issue) else None

for run_dir in sorted((repo / "larch-logs").glob("*/*")):
    if not run_dir.is_dir():
        continue
    issue = manifest_issue(run_dir / "manifest.json")
    skills_in_run = set()
    timing_json = run_dir / "timing-report.json"
    if timing_json.exists():
        try:
            data = json.loads(timing_json.read_text(encoding="utf-8"))
            for row in data.get("per_step", []):
                skill = normalize_skill(row.get("skill"))
                if skill:
                    skills_in_run.add(skill)
        except Exception:
            pass
    if not skills_in_run:
        manifest_path = run_dir / "manifest.json"
        if manifest_path.exists():
            try:
                skill = normalize_skill(json.loads(manifest_path.read_text(encoding="utf-8")).get("skill"))
                if skill:
                    skills_in_run.add(skill)
            except Exception:
                pass
    for skill in skills_in_run:
        invocations[skill] += 1
        if issue:
            issues_by_skill[skill].add(issue)

def skill_path(skill):
    candidates = [
        repo / "skills" / skill / "SKILL.md",
        repo / ".claude" / "skills" / skill / "SKILL.md",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None

rows = []
for skill, count in invocations.items():
    path = skill_path(skill)
    if path is None:
        continue
    text = path.read_text(encoding="utf-8", errors="replace")
    tokens = len(enc.encode(text))
    rows.append((skill, count, len(issues_by_skill[skill]), tokens, count * tokens))

rows.sort(key=lambda row: (-row[4], row[0]))
out_path.parent.mkdir(parents=True, exist_ok=True)
fd, tmp_name = tempfile.mkstemp(prefix=".tmp.measure-realized-cost.", dir=str(out_path.parent), text=True)
with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
    fh.write("skill\tinvocations\tissues_observed\ttokens_per_invocation\trealized_tokens\n")
    for row in rows:
        fh.write("%s\t%d\t%d\t%d\t%d\n" % row)
os.replace(tmp_name, out_path)
PY

printf 'WROTE\t%s\n' "${OUT_FILE#"$REPO_ROOT"/}"
