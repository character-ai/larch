#!/bin/bash
# Regression test for check-reviewers.sh probe acceptance logic.
# Tests the case-insensitive exact-match rule: after whitespace strip + lowercase,
# the probe reply must equal exactly "ok". Rejects substrings like "token", "broken".
#
# Wired into: make test-harnesses
# Exit codes: 0 all pass, 1 any failure

set -euo pipefail

# Tighten run-external-agent.sh's poll cadence so each Gemini-probe stub does
# not pay a 10s sleep cycle. Production probes (real Gemini) inherit the
# default 10s. See scripts/run-external-agent.md.
export RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05
# wait-for-reviewers.sh polls sentinel-files every 5s by default; that becomes
# the floor when the run-external-agent.sh polling above is already sub-second.
# Drop it to 0.05s for stub-binary tests.
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

cat > "$STUB_BIN/gemini" <<'STUB'
#!/usr/bin/env bash
case "${GEMINI_STUB_MODE:-ok}" in
  ok) printf '{"response":"OK"}\n' ;;
  error) printf '{"error":"auth failed"}\n' ;;
  verbose) printf '{"response":"Thinking... OK"}\n' ;;
esac
STUB
chmod +x "$STUB_BIN/gemini"

run_gemini_probe() {
    PATH="$STUB_BIN:$PATH" LARCH_TEST_PROBE_SLEEP_SECONDS=0 \
      "$REPO_ROOT/scripts/check-reviewers.sh" --probe --include-gemini --skip-codex-probe --skip-cursor-probe
}

probe_output=$(GEMINI_STUB_MODE=ok run_gemini_probe)
grep -q '^GEMINI_AVAILABLE=true$' <<< "$probe_output" \
  || fail "Expected GEMINI_AVAILABLE=true with stub gemini"
grep -q '^GEMINI_HEALTHY=true$' <<< "$probe_output" \
  || fail "Expected GEMINI_HEALTHY=true for JSON .response OK"

probe_output=$(GEMINI_STUB_MODE=error run_gemini_probe)
grep -q '^GEMINI_HEALTHY=false$' <<< "$probe_output" \
  || fail "Expected GEMINI_HEALTHY=false for JSON .error"
grep -q '^GEMINI_PROBE_ERROR=.*Gemini error' <<< "$probe_output" \
  || fail "Expected GEMINI_PROBE_ERROR for JSON .error"

probe_output=$(LARCH_TEST_FORCE_MISSING_JQ=true GEMINI_STUB_MODE=ok run_gemini_probe)
grep -q '^GEMINI_HEALTHY=false$' <<< "$probe_output" \
  || fail "Expected GEMINI_HEALTHY=false when jq is missing"
grep -q '^GEMINI_PROBE_ERROR=MISSING_JQ' <<< "$probe_output" \
  || fail "Expected MISSING_JQ diagnostic when jq is missing"

if [[ "$FAIL" -eq 1 ]]; then
    echo "FAIL: test-check-reviewers.sh — some probe acceptance tests failed" >&2
    exit 1
fi

echo "PASS: test-check-reviewers.sh — all probe acceptance tests passed"
exit 0
