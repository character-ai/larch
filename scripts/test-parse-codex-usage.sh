#!/usr/bin/env bash
# test-parse-codex-usage.sh — offline harness for Codex JSONL usage parsing.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SCRIPT="$REPO_ROOT/scripts/parse-codex-usage.sh"
CODEX_FIXTURE="$REPO_ROOT/scripts/fixtures/parse-codex-usage/codex-events-0.125.jsonl"
CODEX_MSG_FIXTURE="$REPO_ROOT/scripts/fixtures/parse-codex-usage/codex-msg-token-usage.jsonl"
PASS=0
FAIL=0

pass() { PASS=$((PASS + 1)); }
fail() { echo "FAIL: $1" >&2; FAIL=$((FAIL + 1)); }
eq() { if [[ "$2" == "$3" ]]; then pass; else fail "$1 expected '$2' got '$3'"; fi; }
contains() { case "$3" in *"$2"*) pass ;; *) fail "$1 missing '$2': $3" ;; esac; }

ROOT="${TMPDIR:-/tmp}"
TMP=$(mktemp -d "$ROOT/test-parse-codex-usage.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

run_ok() {
    local label=$1 file=$2 expected=$3 out
    out=$("$SCRIPT" "$file" 2>"$TMP/$label.err") || {
        fail "$label unexpectedly failed: $(cat "$TMP/$label.err" 2>/dev/null)"
        return
    }
    eq "$label output" "$expected" "$out"
    local input cached output total
    input=$(printf '%s\n' "$out" | awk -F= '$1=="INPUT"{print $2}')
    cached=$(printf '%s\n' "$out" | awk -F= '$1=="CACHED_INPUT"{print $2}')
    output=$(printf '%s\n' "$out" | awk -F= '$1=="OUTPUT"{print $2}')
    total=$(printf '%s\n' "$out" | awk -F= '$1=="TOTAL"{print $2}')
    eq "$label total arithmetic" "$total" "$((input + cached + output))"
}

run_fail() {
    local label=$1 expected_rc=$2 file_arg=${3:-} expected_err=${4:-}
    local out rc
    set +e
    if [[ -n "$file_arg" ]]; then
        out=$("$SCRIPT" "$file_arg" 2>"$TMP/$label.err")
    else
        out=$("$SCRIPT" 2>"$TMP/$label.err")
    fi
    rc=$?
    set -e
    eq "$label rc" "$expected_rc" "$rc"
    eq "$label stdout empty" "" "$out"
    if [[ -n "$expected_err" ]]; then
        contains "$label stderr" "$expected_err" "$(cat "$TMP/$label.err" 2>/dev/null)"
    fi
}

cat > "$TMP/sum.jsonl" <<'JSONL'
{"msg":{"usage":{"input_tokens":100,"cached_input_tokens":10,"output_tokens":5}}}
{"msg":{"usage":{"input_tokens":50,"cached_input_tokens":5,"output_tokens":7}}}
JSONL
run_ok "per-bucket-sum" "$TMP/sum.jsonl" $'INPUT=135\nCACHED_INPUT=15\nOUTPUT=12\nTOTAL=162'

cat > "$TMP/cache-math.jsonl" <<'JSONL'
{"msg":{"usage":{"input_tokens":1000,"cached_input_tokens":900,"output_tokens":50}}}
JSONL
run_ok "cache-math" "$TMP/cache-math.jsonl" $'INPUT=100\nCACHED_INPUT=900\nOUTPUT=50\nTOTAL=1050'

cat > "$TMP/mixed-shapes.jsonl" <<'JSONL'
{"usage":{"input_tokens":20,"cached_input_tokens":4,"output_tokens":6}}
{"usage":{"input_tokens":30,"input_tokens_details":{"cached_tokens":10},"output_tokens":8}}
JSONL
run_ok "mixed-shapes" "$TMP/mixed-shapes.jsonl" $'INPUT=36\nCACHED_INPUT=14\nOUTPUT=14\nTOTAL=64'

cat > "$TMP/coalesce.jsonl" <<'JSONL'
{"msg":{"usage":{"input_tokens":100,"cached_input_tokens":25,"output_tokens":10}},"usage":{"input_tokens":999,"cached_input_tokens":999,"output_tokens":999}}
JSONL
run_ok "msg-coalesce" "$TMP/coalesce.jsonl" $'INPUT=75\nCACHED_INPUT=25\nOUTPUT=10\nTOTAL=110'

run_ok "msg-direct-usage" "$CODEX_MSG_FIXTURE" $'INPUT=100\nCACHED_INPUT=20\nOUTPUT=9\nTOTAL=129'

cat > "$TMP/token-usage-rollup-precedence.jsonl" <<'JSONL'
{"msg":{"usage":{"input_tokens":100,"cached_input_tokens":10,"output_tokens":5}}}
{"type":"token_usage","input_tokens":7777,"cached_input_tokens":7000,"output_tokens":222}
{"type":"task.completed","input_tokens":999,"cached_input_tokens":500,"output_tokens":111}
JSONL
run_ok "token-usage-rollup-precedence" "$TMP/token-usage-rollup-precedence.jsonl" $'INPUT=777\nCACHED_INPUT=7000\nOUTPUT=222\nTOTAL=7999'

cat > "$TMP/empty-usage-top-level-fallback.jsonl" <<'JSONL'
{"type":"token_usage","usage":{},"input_tokens":5,"cached_input_tokens":2,"output_tokens":1}
JSONL
run_ok "empty-usage-top-level-fallback" "$TMP/empty-usage-top-level-fallback.jsonl" $'INPUT=3\nCACHED_INPUT=2\nOUTPUT=1\nTOTAL=6'

cat > "$TMP/wrong-type-top-level.jsonl" <<'JSONL'
{"type":"task.completed","input_tokens":999,"cached_input_tokens":500,"output_tokens":111}
JSONL
run_fail "wrong-type-top-level" 1 "$TMP/wrong-type-top-level.jsonl" "no usage events"

cat > "$TMP/msg-zero-fallback.jsonl" <<'JSONL'
{"msg":{"usage":{"input_tokens":0,"cached_input_tokens":0,"output_tokens":0}},"usage":{"input_tokens":5000,"cached_input_tokens":0,"output_tokens":100}}
JSONL
run_ok "msg-zero-fallback" "$TMP/msg-zero-fallback.jsonl" $'INPUT=5000\nCACHED_INPUT=0\nOUTPUT=100\nTOTAL=5100'

cat > "$TMP/noise.jsonl" <<'JSONL'
wrapper noise
{"usage":{"input_tokens":10,"input_tokens_details":{"cached_tokens":3},"output_tokens":2}}
not json
JSONL
run_ok "wrapper-noise" "$TMP/noise.jsonl" $'INPUT=7\nCACHED_INPUT=3\nOUTPUT=2\nTOTAL=12'

: > "$TMP/empty.jsonl"
run_fail "empty-file" 1 "$TMP/empty.jsonl" "events file missing"
run_fail "missing-file" 1 "$TMP/missing.jsonl" "events file missing"

cat > "$TMP/no-usage.jsonl" <<'JSONL'
{"type":"event","msg":{"kind":"started"}}
JSONL
run_fail "no-usage" 1 "$TMP/no-usage.jsonl" "no usage events"

cat > "$TMP/zero-total.jsonl" <<'JSONL'
{"usage":{"input_tokens":0,"cached_input_tokens":0,"output_tokens":0}}
JSONL
run_fail "zero-total" 1 "$TMP/zero-total.jsonl" "no usage events"

cat > "$TMP/cache-exceeds.jsonl" <<'JSONL'
{"usage":{"input_tokens":5,"cached_input_tokens":6,"output_tokens":1}}
JSONL
run_fail "cache-exceeds" 1 "$TMP/cache-exceeds.jsonl" "cached_tokens exceeds input_tokens"

cat > "$TMP/cache-exceeds-midstream.jsonl" <<'JSONL'
{"usage":{"input_tokens":5,"cached_input_tokens":2,"output_tokens":1}}
{"usage":{"input_tokens":4,"cached_input_tokens":6,"output_tokens":1}}
{"usage":{"input_tokens":9,"cached_input_tokens":1,"output_tokens":2}}
JSONL
run_fail "cache-exceeds-midstream" 1 "$TMP/cache-exceeds-midstream.jsonl" "cached_tokens exceeds input_tokens"

run_fail "argv-error" 2 "" "usage error"

set +e
out=$(PATH="/bin:/usr/bin" "$SCRIPT" "$TMP/cache-math.jsonl" 2>"$TMP/no-jq.err")
rc=$?
set -e
eq "jq-missing rc" "1" "$rc"
eq "jq-missing stdout" "" "$out"
contains "jq-missing stderr" "jq not found" "$(cat "$TMP/no-jq.err" 2>/dev/null)"

cat > "$TMP/jq-failed.jsonl" <<'JSONL'
{"usage":{"input_tokens":"abc","cached_input_tokens":0,"output_tokens":1}}
JSONL
run_fail "jq-failed" 1 "$TMP/jq-failed.jsonl" "jq failed"

cat > "$TMP/line-streaming.jsonl" <<'JSONL'
{"usage":{"input_tokens":1,"cached_input_tokens":0,"output_tokens":2}}
{"usage":{"input_tokens":3,"cached_input_tokens":1,"output_tokens":4}}
JSONL
run_ok "line-streaming" "$TMP/line-streaming.jsonl" $'INPUT=3\nCACHED_INPUT=1\nOUTPUT=6\nTOTAL=10'

run_ok "codex-cli-fixture" "$CODEX_FIXTURE" $'INPUT=777\nCACHED_INPUT=7000\nOUTPUT=222\nTOTAL=7999'

total=$((PASS + FAIL))
if (( FAIL == 0 )); then
    echo "PASS: test-parse-codex-usage.sh — $PASS/$total assertions"
else
    echo "FAIL: test-parse-codex-usage.sh — $FAIL/$total assertions failed" >&2
    exit 1
fi
