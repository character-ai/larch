#!/usr/bin/env bash
# Regression harness for parse-drafter-output.py sentinel edge cases.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
PARSER="$REPO_ROOT/scripts/parse-drafter-output.py"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-parse-drafter-output.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

run_case() {
    local label="$1" expected_rc="$2" raw="$3"
    local dir="$TMP/$label"
    mkdir -p "$dir"
    printf '%s\n' "$raw" > "$dir/raw.txt"
    set +e
    python3 "$PARSER" "$dir/raw.txt" "$dir/plan.txt" "$dir/summary.txt" "$dir/scout.json" >"$dir/stdout.env" 2>"$dir/stderr.txt"
    rc=$?
    set -e
    [[ "$rc" == "$expected_rc" ]] || fail "$label expected rc=$expected_rc got rc=$rc stderr=$(cat "$dir/stderr.txt")"
}

run_case inline-scout-json 0 $'LARCH_PLAN_BEGIN\n## Plan\nThis prose mentions {"archetypes":[]} as an inline example.\ndiff_lines: 1\nLARCH_PLAN_END'
grep -Fq 'SCOUT_CANDIDATE_WRITTEN=false' "$TMP/inline-scout-json/stdout.env" || fail "inline scout JSON should not write scout candidate"

run_case fenced-scout-json 0 $'LARCH_PLAN_BEGIN\n## Plan\n```json\n{"archetypes":[]}\n```\ndiff_lines: 1\nLARCH_PLAN_END'
grep -Fq 'SCOUT_CANDIDATE_WRITTEN=false' "$TMP/fenced-scout-json/stdout.env" || fail "fenced scout JSON should not write scout candidate"

run_case unclosed-fence-scout-json 1 $'LARCH_PLAN_BEGIN\n## Plan\n```json\n{"archetypes":[]}\ndiff_lines: 1\nLARCH_PLAN_END'
grep -Fq 'standalone scout manifest JSON' "$TMP/unclosed-fence-scout-json/stderr.txt" || fail "unclosed fence scout JSON should fail closed"

run_case scout-sentinel-in-plan 1 $'LARCH_PLAN_BEGIN\n## Plan\nLARCH_SCOUT_BEGIN\n{"archetypes":[]}\nLARCH_SCOUT_END\ndiff_lines: 1\nLARCH_PLAN_END'
grep -Fq 'scout block may appear only after LARCH_PLAN_END' "$TMP/scout-sentinel-in-plan/stderr.txt" || fail "scout sentinel inside plan should fail"

run_case malformed-post-plan-scout 0 $'LARCH_PLAN_BEGIN\n## Plan\nBody\ndiff_lines: 1\nLARCH_PLAN_END\nLARCH_SCOUT_BEGIN\n{not json\nLARCH_SCOUT_END'
grep -Fq 'SCOUT_CANDIDATE_WRITTEN=false' "$TMP/malformed-post-plan-scout/stdout.env" || fail "malformed post-plan scout should be non-fatal"
grep -Fq 'SCOUT_FAIL_REASON=json_parse' "$TMP/malformed-post-plan-scout/stdout.env" || fail "malformed post-plan scout reason missing"

echo "PASS: test-parse-drafter-output.sh"
