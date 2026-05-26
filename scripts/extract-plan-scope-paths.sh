#!/usr/bin/env bash
# extract-plan-scope-paths.sh — Extract plan scope paths from Files to modify/create.

set -euo pipefail

usage() {
    echo "Usage: extract-plan-scope-paths.sh [--plan-file PATH] [-z]" >&2
}

PLAN_FILE=""
NUL_OUTPUT=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --plan-file) PLAN_FILE="${2:?--plan-file requires a value}"; shift 2 ;;
        -z|--null) NUL_OUTPUT=true; shift ;;
        --help) usage; exit 0 ;;
        *) echo "extract-plan-scope-paths.sh: unknown option: $1" >&2; usage; exit 2 ;;
    esac
done

if [[ -z "$PLAN_FILE" ]]; then
    echo "extract-plan-scope-paths.sh: --plan-file is required" >&2
    exit 2
fi
if [[ ! -f "$PLAN_FILE" ]]; then
    echo "extract-plan-scope-paths.sh: plan file not found: $PLAN_FILE" >&2
    exit 2
fi

python3 - "$PLAN_FILE" "$NUL_OUTPUT" <<'PY'
import re
import sys

path = sys.argv[1]
nul_output = sys.argv[2] == "true"

lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
has_scope_section = any(re.match(r"^##\s+Files to modify(?:/create)?\s*$", line) for line in lines)
in_section = not has_scope_section
seen = []

for line in lines:
    if re.match(r"^##\s+Files to modify(?:/create)?\s*$", line):
        in_section = True
        continue
    if has_scope_section and in_section and re.match(r"^##\s+", line):
        break
    if not in_section:
        continue

    m = re.match(r"^###\s+(NEW|UPDATED|REWRITTEN)\s*:\s*(.+)$", line)
    if not m:
        continue
    tail = m.group(2)
    matched_backtick = False
    for pm in re.finditer(r"`([^`]+)`", tail):
        matched_backtick = True
        p = pm.group(1).strip()
        if p and p not in seen:
            seen.append(p)
    if not matched_backtick:
        parts = tail.split()
        if not parts:
            continue
        tok = re.sub(r"\(.*$", "", parts[0]).strip()
        if tok and not tok.startswith("+") and "/" in tok and tok not in seen:
            seen.append(tok)

if not seen:
    seen.append("skills/design/SKILL.md")

sep = "\0" if nul_output else "\n"
sys.stdout.write(sep.join(seen))
if seen:
    sys.stdout.write(sep)
PY
