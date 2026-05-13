#!/usr/bin/env bash
# Regression harness for log-phase.sh.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)
SCRIPT="$REPO_ROOT/skills/review/scripts/log-phase.sh"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-log-phase.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

printf 'payload\n' > "$TMP/payload.md"
out=$(cd "$REPO_ROOT" && "$SCRIPT" --log-root "$TMP/logs" --run-id run1 --batch review-context --action write --payload-file "$TMP/payload.md")
grep -Fq 'LOG_WRITTEN=true' <<< "$out"
[[ -f "$TMP/logs/review/run1/review-context.md" ]]

if "$SCRIPT" --log-root "$TMP/logs" --run-id run1 --batch bad/batch --action write --payload-file "$TMP/payload.md" >/dev/null 2>"$TMP/err"; then
    echo "FAIL: invalid batch accepted" >&2
    exit 1
fi
grep -Fq 'unregistered review batch' "$TMP/err"

echo "All assertions passed."
