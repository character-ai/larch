#!/usr/bin/env bash
# Regression harness for log-phase.sh.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)
SCRIPT="$REPO_ROOT/skills/review/scripts/log-phase.sh"
export CLAUDE_PLUGIN_ROOT="$REPO_ROOT"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-log-phase.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

assert_stdout_cap() {
    local text="$1" cap="${2:-2048}" bytes
    bytes=${#text}
    [[ "$bytes" -le "$cap" ]] || { echo "FAIL: stdout ${bytes}B > ${cap}B cap" >&2; exit 1; }
}

printf 'payload\n' > "$TMP/payload.md"
out=$(cd "$REPO_ROOT" && "$SCRIPT" --log-root "$TMP/logs" --run-id run1 --batch review-context --action write --payload-file "$TMP/payload.md")
assert_stdout_cap "$out"
grep -Fq 'LOG_WRITTEN=true' <<< "$out"
[[ -f "$TMP/logs/review/run1/review-context.md" ]]

printf '{"status":"ok","dynamic_slots":1,"manifest_path":"/tmp/scout.json","yield_tsv_path":"/tmp/yield.tsv"}\n' > "$TMP/scout.json"
out=$(cd "$REPO_ROOT" && "$SCRIPT" --log-root "$TMP/logs" --run-id run1 --batch review-scout-manifest --action write --payload-file "$TMP/scout.json")
assert_stdout_cap "$out"
grep -Fq 'LOG_WRITTEN=true' <<< "$out"
[[ -f "$TMP/logs/review/run1/review-scout-manifest.json" ]]

if LARCH_QUIET_LOG_FILE="$TMP/log-phase-quiet.log" "$SCRIPT" --log-root "$TMP/logs" --run-id run1 --batch bad/batch --action write --payload-file "$TMP/payload.md" >/dev/null 2>"$TMP/err"; then
    echo "FAIL: invalid batch accepted" >&2
    exit 1
fi
grep -Fq 'unregistered review batch' "$TMP/err"

echo "All assertions passed."
