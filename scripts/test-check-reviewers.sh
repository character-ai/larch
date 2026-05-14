#!/bin/bash
# Regression test for check-reviewers.sh probe acceptance logic.
# Tests the case-insensitive exact-match rule: after whitespace strip + lowercase,
# the probe reply must equal exactly "ok". Rejects substrings like "token", "broken".
#
# Wired into: make test-harnesses
# Exit codes: 0 all pass, 1 any failure

set -euo pipefail

# Tighten run-external-agent.sh's poll cadence so each probe stub does not pay
# a 3s sleep cycle. Production probes inherit the default 3s.
export RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05
# wait-for-reviewers.sh polls sentinel-files every 5s by default; drop to
# 0.05s for stub-binary tests.
export WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.05

FAIL=0

fail() {
    echo "FAIL: $1" >&2
    FAIL=1
}

# Simulate the normalization pipeline from check-reviewers.sh:
# tr -d '[:space:]' | tr '[:upper:]' '[:lower:]'
normalize_and_check() {
    local input="$1"
    local reply
    reply=$(printf '%s' "$input" | tr -d '[:space:]' | tr '[:upper:]' '[:lower:]')
    if [[ "$reply" == "ok" ]]; then
        echo "healthy"
    else
        echo "unhealthy"
    fi
}

# --- Should be healthy ---
check_healthy() {
    local label="$1" input="$2"
    local result
    result=$(normalize_and_check "$input")
    if [[ "$result" != "healthy" ]]; then
        fail "Expected healthy for '$label', got unhealthy"
    fi
}

# --- Should be unhealthy ---
check_unhealthy() {
    local label="$1" input="$2"
    local result
    result=$(normalize_and_check "$input")
    if [[ "$result" != "unhealthy" ]]; then
        fail "Expected unhealthy for '$label', got healthy"
    fi
}

# Positive cases (should pass probe)
check_healthy "exact OK"          "OK"
check_healthy "lowercase ok"      "ok"
check_healthy "mixed case Ok"     "Ok"
check_healthy "mixed case oK"     "oK"
check_healthy "with whitespace"   "  OK  "
check_healthy "with newline"      "OK
"
check_healthy "with tab"          "$(printf 'OK\t')"

# Negative cases (should fail probe)
check_unhealthy "empty"                  ""
check_unhealthy "token"                  "token"
check_unhealthy "broken"                 "broken"
check_unhealthy "NotOK"                  "NotOK"
check_unhealthy "OK with suffix"         "OK sure"
check_unhealthy "Sure OK"               "Sure OK"
check_unhealthy "error with ok substr"   "Please look at the docs"
check_unhealthy "wok"                    "wok"
check_unhealthy "okay"                   "okay"
check_unhealthy "OK."                    "OK."
check_unhealthy "auth error"             "Error: Password not found for account"
check_unhealthy "thinking prefix"        "Thinking about this... OK"

# Gemini probe integration: stub gemini JSON stdout and let check-reviewers.sh
# exercise run-external-agent.sh + jq .response extraction.
REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
TMPDIR=$(mktemp -d /tmp/larch-test-check-reviewers-XXXXXX)
trap 'rm -rf "$TMPDIR"' EXIT
STUB_BIN="$TMPDIR/bin"
mkdir -p "$STUB_BIN"

STUB_PROBE_PID_LOG="$TMPDIR/probe-pids.log"
cat > "$STUB_BIN/codex" <<STUB
#!/usr/bin/env bash
printf '%s\n' "\$\$" >> "$STUB_PROBE_PID_LOG"
sleep 30
STUB
chmod +x "$STUB_BIN/codex"

cat > "$STUB_BIN/cursor" <<STUB
#!/usr/bin/env bash
printf '%s\n' "\$\$" >> "$STUB_PROBE_PID_LOG"
sleep 30
STUB
chmod +x "$STUB_BIN/cursor"

set +e
PATH="$STUB_BIN:$PATH" LARCH_TEST_PROBE_SLEEP_SECONDS=0 WAIT_FOR_REVIEWERS_POLL_INTERVAL=00 \
  "$REPO_ROOT/scripts/check-reviewers.sh" --probe >"$TMPDIR/infra.stdout" 2>"$TMPDIR/infra.stderr"
infra_code=$?
set -e
[[ "$infra_code" -eq 0 ]] \
  || fail "Expected probe infrastructure error path to exit 0, got $infra_code"
infra_stdout=$(cat "$TMPDIR/infra.stdout")
grep -q '^WAIT_INFRA_ERROR=' <<< "$infra_stdout" \
  || fail "Expected WAIT_INFRA_ERROR on wait preflight failure"
grep -q '^CODEX_HEALTHY=false$' <<< "$infra_stdout" \
  || fail "Expected CODEX_HEALTHY=false fail-closed value on wait preflight failure"
grep -q '^CURSOR_HEALTHY=false$' <<< "$infra_stdout" \
  || fail "Expected CURSOR_HEALTHY=false fail-closed value on wait preflight failure"
grep -q 'Probe infrastructure error:' "$TMPDIR/infra.stderr" \
  || fail "Expected probe infrastructure diagnostic on stderr"
if grep -q 'Retrying failed health probes (attempt 2 of 3' "$TMPDIR/infra.stderr"; then
  fail "Expected wait preflight failure to skip retry attempts"
fi
if [[ -s "$STUB_PROBE_PID_LOG" ]]; then
  fail "Expected wait preflight failure to launch no sleeping probe wrappers"
fi

# Cursor probe argv coverage (#1358 / review-round-1 FINDING_5):
# pin `--output-format json` and the conditional `--api-key <value>`
# adjacency in the Cursor probe argv so a future edit cannot drop either
# silently while production review launches stay correct.
CURSOR_PROBE_ARGV_LOG="$TMPDIR/cursor-probe-argv.log"
cat > "$STUB_BIN/cursor" <<STUB
#!/usr/bin/env bash
{
  for _arg in "\$@"; do
    printf '%s\n' "\$_arg"
  done
  printf -- '---\n'
} >> "$CURSOR_PROBE_ARGV_LOG"
# Emit the probe's required exact "OK" reply so check-reviewers' acceptance
# rule matches and the probe completes its happy path.
printf 'OK\n'
STUB
chmod +x "$STUB_BIN/cursor"

run_cursor_probe() {
    PATH="$STUB_BIN:$PATH" LARCH_TEST_PROBE_SLEEP_SECONDS=0 \
      "$REPO_ROOT/scripts/check-reviewers.sh" --probe --skip-codex-probe
}

# Case 1: with CURSOR_API_KEY set, probe argv contains adjacent --api-key
# <value> tokens AND --output-format json.
: > "$CURSOR_PROBE_ARGV_LOG"
CURSOR_API_KEY="probe-test-key-XYZ" run_cursor_probe >/dev/null 2>&1
ofmt_line=$(grep -Fxn -- '--output-format' "$CURSOR_PROBE_ARGV_LOG" | awk -F: 'NR==1 {print $1; exit}')
json_line=$(grep -Fxn -- 'json' "$CURSOR_PROBE_ARGV_LOG" | awk -F: 'NR==1 {print $1; exit}')
api_key_line=$(grep -Fxn -- '--api-key' "$CURSOR_PROBE_ARGV_LOG" | awk -F: 'NR==1 {print $1; exit}')
api_val_line=$(grep -Fxn -- 'probe-test-key-XYZ' "$CURSOR_PROBE_ARGV_LOG" | awk -F: 'NR==1 {print $1; exit}')
if [[ -n "$ofmt_line" && -n "$json_line" && -n "$api_key_line" && -n "$api_val_line" ]] \
   && (( ofmt_line < json_line )) && (( api_val_line == api_key_line + 1 )); then
    :
else
    fail "Cursor probe argv missing --output-format json or non-adjacent --api-key with CURSOR_API_KEY set; ofmt=$ofmt_line json=$json_line api_key=$api_key_line api_val=$api_val_line"
fi

# Case 2: with CURSOR_API_KEY empty, probe argv contains --output-format json
# but no --api-key (preserves cursor login keychain fallback).
: > "$CURSOR_PROBE_ARGV_LOG"
CURSOR_API_KEY="" run_cursor_probe >/dev/null 2>&1
ofmt_line=$(grep -Fxn -- '--output-format' "$CURSOR_PROBE_ARGV_LOG" | awk -F: 'NR==1 {print $1; exit}')
if [[ -n "$ofmt_line" ]]; then
    :
else
    fail "Cursor probe argv missing --output-format with CURSOR_API_KEY empty"
fi
if grep -Fxq -- '--api-key' "$CURSOR_PROBE_ARGV_LOG"; then
    fail "Cursor probe argv must not include --api-key when CURSOR_API_KEY is empty"
fi

if [[ "$FAIL" -eq 1 ]]; then
    echo "FAIL: test-check-reviewers.sh — some probe acceptance tests failed" >&2
    exit 1
fi

echo "PASS: test-check-reviewers.sh — all probe acceptance tests passed"
exit 0
