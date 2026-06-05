#!/usr/bin/env bash
# check-scope-reduction-marker.sh — detect leading [SCOPE-REDUCTION] plan-review findings.

set -euo pipefail

usage() {
    printf '%s\n' 'Usage: check-scope-reduction-marker.sh [--file <path>]' >&2
}

IN_PATH=""
while [ $# -gt 0 ]; do
    case "$1" in
        --file) IN_PATH="${2:?}"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) printf 'check-scope-reduction-marker.sh: unknown option: %s\n' "$1" >&2; usage; exit 2 ;;
    esac
done

if [ -n "$IN_PATH" ]; then
    python3 - "$IN_PATH" <<'PY'
import re
import sys

text = open(sys.argv[1], encoding="utf-8", errors="replace").read()


def strip_code(s):
    s = re.sub(r"```.*?```", "", s, flags=re.S)
    s = re.sub(r"`[^`\n]*`", "", s)
    return s


def norm(s):
    s = " ".join(strip_code(s).strip().split())
    s = re.sub(r"^\[(?:important|nit|latent)\]\s*", "", s, flags=re.I)
    return s


def candidates(body):
    body = strip_code(body)
    for line in body.splitlines():
        stripped = line.strip()
        m = re.match(r"^###\s+FINDING_[0-9]+:\s*(.*)$", stripped, re.I)
        if m:
            yield m.group(1)
        m = re.match(r"^-?\s*(?:\*\*)?Concern(?:\*\*)?:\s*(.*)$", stripped, re.I)
        if m:
            yield m.group(1)
        m = re.match(r"^\s*what:\s*(.*)$", stripped, re.I)
        if m:
            yield m.group(1)

for cand in candidates(text):
    if norm(cand).startswith("[SCOPE-REDUCTION]"):
        raise SystemExit(0)
raise SystemExit(1)
PY
else
    python3 - <<'PY'
import re
import sys

text = sys.stdin.read()


def strip_code(s):
    s = re.sub(r"```.*?```", "", s, flags=re.S)
    s = re.sub(r"`[^`\n]*`", "", s)
    return s


def norm(s):
    s = " ".join(strip_code(s).strip().split())
    s = re.sub(r"^\[(?:important|nit|latent)\]\s*", "", s, flags=re.I)
    return s


def candidates(body):
    body = strip_code(body)
    for line in body.splitlines():
        stripped = line.strip()
        m = re.match(r"^###\s+FINDING_[0-9]+:\s*(.*)$", stripped, re.I)
        if m:
            yield m.group(1)
        m = re.match(r"^-?\s*(?:\*\*)?Concern(?:\*\*)?:\s*(.*)$", stripped, re.I)
        if m:
            yield m.group(1)
        m = re.match(r"^\s*what:\s*(.*)$", stripped, re.I)
        if m:
            yield m.group(1)

for cand in candidates(text):
    if norm(cand).startswith("[SCOPE-REDUCTION]"):
        raise SystemExit(0)
raise SystemExit(1)
PY
fi
