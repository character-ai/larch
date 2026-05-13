#!/usr/bin/env bash
# Regression harness for gather-context.sh.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)
SCRIPT="$REPO_ROOT/skills/review/scripts/gather-context.sh"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-gather-context.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

out=$(cd "$REPO_ROOT" && "$SCRIPT" --mode description --description-text "review skill" --output-dir "$TMP")
grep -Fq 'MODE=description' <<< "$out"
scope=$(printf '%s\n' "$out" | awk -F= '$1=="FILE_LIST_FILE"{print $2}')
scope=$(printf '%b' "${scope//\\x/\\x}")
[[ -s "$scope" ]] || { echo "FAIL: description produced empty scope" >&2; exit 1; }
grep -Fq 'skills/review/SKILL.md' "$scope" || { echo "FAIL: expected review skill in scope" >&2; exit 1; }

echo "All assertions passed."
