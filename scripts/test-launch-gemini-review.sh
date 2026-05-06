#!/bin/bash
# Regression test for launch-gemini-review.sh lifecycle and JSON normalization.
#
# Wired into: make test-harnesses
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
TMPDIR=$(mktemp -d /tmp/larch-test-launch-gemini-XXXXXX)
trap 'rm -rf "$TMPDIR"' EXIT

# Tighten run-external-agent.sh's poll cadence so each stub invocation does
# not pay a 10s sleep cycle. Production callers inherit the default 10s.
# See scripts/run-external-agent.md.
export RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05

FAIL=0
fail() {
  echo "FAIL: $1" >&2
  FAIL=1
}

assert_no_launcher_artifacts() {
  local label="$1"
  local output="$2"
  local raw="${output}.raw"
  local suffix
  for suffix in "" ".done" ".meta" ".diag"; do
    [[ ! -e "${output}${suffix}" ]] \
      || fail "$label: unexpected artifact ${output}${suffix}"
    [[ ! -e "${raw}${suffix}" ]] \
      || fail "$label: unexpected raw artifact ${raw}${suffix}"
  done
}

assert_rejected_output() {
  local label="$1"
  local output="$2"
  local stdout="$TMPDIR/${label}.stdout"
  local stderr="$TMPDIR/${label}.stderr"
  local code
  set +e
  "$REPO_ROOT/scripts/launch-gemini-review.sh" --output "$output" --timeout 60 --prompt "hi" >"$stdout" 2>"$stderr"
  code=$?
  set -e
  [[ "$code" -eq 2 ]] \
    || fail "$label: expected exit 2, got $code"
  grep -q 'ERROR: --output contains bytes outside' "$stderr" \
    || fail "$label: expected output validation error"
  assert_no_launcher_artifacts "$label" "$output"
}

STUB_BIN="$TMPDIR/bin"
mkdir -p "$STUB_BIN"
ARGV_LOG="$TMPDIR/gemini-argv.log"
cat > "$STUB_BIN/gemini" <<STUB
#!/usr/bin/env bash
# Record each argv element on its own line to \$ARGV_LOG so the harness can
# pin reviewer Gemini flags. Sentinel line --- separates invocations.
{
  for _arg in "\$@"; do
    printf '%s\n' "\$_arg"
  done
  printf -- '---\n'
} >> "$ARGV_LOG"
case "\${GEMINI_STUB_MODE:-ok}" in
  ok) printf '{"response":"Plain review text"}\n' ;;
  error) printf '{"error":"auth failed"}\n' ;;
  empty) printf '{"response":""}\n' ;;
esac
printf 'diagnostic noise\n' >&2
STUB
chmod +x "$STUB_BIN/gemini"

OUTPUT="$TMPDIR/gemini-review.txt"
PATH="$STUB_BIN:$PATH" "$REPO_ROOT/scripts/launch-gemini-review.sh" --output "$OUTPUT" --timeout 1800 --prompt "test"

[[ "$(cat "$OUTPUT")" == "Plain review text" ]] \
  || fail "Expected normalized plain text output"
grep -q '^TIMEOUT=600$' "${OUTPUT}.raw.meta" \
  || fail "Expected run-external-agent timeout clamp to 600"
grep -q '^CMD_JSON=' "${OUTPUT}.meta" \
  || fail "Expected launcher meta to include CMD_JSON"
if grep -q '^CMD=' "${OUTPUT}.meta"; then
  fail "Launcher meta should not include legacy CMD"
fi
# Pin reviewer approval-mode to yolo so a regression to plan (which would
# block git/shell access and silently break the live-repo review contract)
# is caught at harness time. The launcher passes the inner `gemini` argv
# through run-external-agent.sh; the stub records each arg on its own line.
APPROVAL_MODE_VALUE=$(awk 'prev=="--approval-mode"{print; exit} {prev=$0}' "$ARGV_LOG")
[[ "$APPROVAL_MODE_VALUE" == "yolo" ]] \
  || fail "Expected gemini argv to include --approval-mode yolo, got '$APPROVAL_MODE_VALUE'"
# Pin --admin-policy <path-ending-in-gemini-reviewer-policy.toml> so a
# regression that drops the policy file from the gemini argv (re-opening
# the bug from #1234 -- reviewer can write files despite "Do NOT modify
# files" prompt) is caught at harness time. The policy file lives beside
# the launcher; the absolute path varies by checkout, so we pin the
# basename. Also assert the path exists on disk and is non-empty so a
# stale path that points outside the install is caught.
ADMIN_POLICY_PATH=$(awk 'prev=="--admin-policy"{print; exit} {prev=$0}' "$ARGV_LOG")
[[ "$ADMIN_POLICY_PATH" == *"/gemini-reviewer-policy.toml" ]] \
  || fail "Expected gemini argv to include --admin-policy <path>/gemini-reviewer-policy.toml, got '$ADMIN_POLICY_PATH'"
[[ -s "$ADMIN_POLICY_PATH" ]] \
  || fail "Expected --admin-policy path '$ADMIN_POLICY_PATH' to exist and be non-empty"
grep -q '^0$' "${OUTPUT}.done" \
  || fail "Expected success .done exit code 0"
if grep -q '[{}]' "$OUTPUT"; then
  fail "Output should not contain raw JSON braces"
fi

ERROR_OUTPUT="$TMPDIR/gemini-error.txt"
PATH="$STUB_BIN:$PATH" GEMINI_STUB_MODE=error \
  "$REPO_ROOT/scripts/launch-gemini-review.sh" --output "$ERROR_OUTPUT" --timeout 1800 --prompt "test"
[[ ! -s "$ERROR_OUTPUT" ]] \
  || fail "Expected empty output on Gemini .error"
grep -q '^1$' "${ERROR_OUTPUT}.done" \
  || fail "Expected non-zero .done on Gemini .error"
[[ -s "${ERROR_OUTPUT}.diag" ]] \
  || fail "Expected diagnostic on Gemini .error"

EMPTY_OUTPUT="$TMPDIR/gemini-empty.txt"
PATH="$STUB_BIN:$PATH" GEMINI_STUB_MODE=empty \
  "$REPO_ROOT/scripts/launch-gemini-review.sh" --output "$EMPTY_OUTPUT" --timeout 1800 --prompt "test"
[[ ! -s "$EMPTY_OUTPUT" ]] \
  || fail "Expected empty main output when Gemini .response is empty"
grep -q '^1$' "${EMPTY_OUTPUT}.done" \
  || fail "Expected non-zero .done when .response is empty"
[[ -s "${EMPTY_OUTPUT}.diag" ]] \
  || fail "Expected diagnostic on empty .response"
grep -q -i 'empty' "${EMPTY_OUTPUT}.diag" \
  || fail "Expected diag to mention empty response"

MISSING_JQ_OUTPUT="$TMPDIR/gemini-missing-jq.txt"
PATH="$STUB_BIN:$PATH" LARCH_TEST_FORCE_MISSING_JQ=true \
  "$REPO_ROOT/scripts/launch-gemini-review.sh" --output "$MISSING_JQ_OUTPUT" --timeout 1800 --prompt "test"
[[ ! -s "$MISSING_JQ_OUTPUT" ]] \
  || fail "Expected empty output when jq is missing"
grep -q '^127$' "${MISSING_JQ_OUTPUT}.done" \
  || fail "Expected 127 .done when jq is missing"
grep -q 'MISSING_JQ' "${MISSING_JQ_OUTPUT}.diag" \
  || fail "Expected MISSING_JQ diagnostic"
if grep -q '^CMD_JSON=' "${MISSING_JQ_OUTPUT}.meta"; then
  fail "Missing-jq launcher meta should omit CMD_JSON"
fi

BAD_EQUALS_OUTPUT="$TMPDIR/bad=output.txt"
assert_rejected_output "reject-equals" "$BAD_EQUALS_OUTPUT"

BAD_LF_OUTPUT="$TMPDIR/bad"$'\n'"output.txt"
assert_rejected_output "reject-lf" "$BAD_LF_OUTPUT"

# Reject --timeout 0 at launcher (parallel to run-external-agent.sh + #1115).
TIMEOUT_ZERO_OUTPUT="$TMPDIR/timeout-zero.txt"
TZ_STDOUT="$TMPDIR/timeout-zero.stdout"
TZ_STDERR="$TMPDIR/timeout-zero.stderr"
set +e
"$REPO_ROOT/scripts/launch-gemini-review.sh" --output "$TIMEOUT_ZERO_OUTPUT" --timeout 0 --prompt "hi" >"$TZ_STDOUT" 2>"$TZ_STDERR"
TZ_CODE=$?
set -e
[[ "$TZ_CODE" -eq 2 ]] \
  || fail "reject-timeout-zero: expected exit 2, got $TZ_CODE"
grep -q '\-\-timeout must be a positive integer' "$TZ_STDERR" \
  || fail "reject-timeout-zero: expected positive-integer error"
assert_no_launcher_artifacts "reject-timeout-zero" "$TIMEOUT_ZERO_OUTPUT"

# Reject zero-valued multi-digit timeout strings (#1167) — parallel to
# launch-*-implement.sh and run-external-agent.sh. The single-digit `0` is
# caught by the case-statement; `00`/`000` slip past the case but are
# rejected by the (( 10#$TIMEOUT < 1 )) guard with the same exit 2 contract.
for ZERO_VAL in 00 000; do
  TZ_OUTPUT="$TMPDIR/timeout-${ZERO_VAL}.txt"
  TZ_OUT="$TMPDIR/timeout-${ZERO_VAL}.stdout"
  TZ_ERR="$TMPDIR/timeout-${ZERO_VAL}.stderr"
  set +e
  "$REPO_ROOT/scripts/launch-gemini-review.sh" --output "$TZ_OUTPUT" --timeout "$ZERO_VAL" --prompt "hi" >"$TZ_OUT" 2>"$TZ_ERR"
  TZ_CODE=$?
  set -e
  [[ "$TZ_CODE" -eq 2 ]] \
    || fail "reject-timeout-${ZERO_VAL}: expected exit 2, got $TZ_CODE"
  grep -q '\-\-timeout must be a positive integer' "$TZ_ERR" \
    || fail "reject-timeout-${ZERO_VAL}: expected positive-integer error"
  assert_no_launcher_artifacts "reject-timeout-${ZERO_VAL}" "$TZ_OUTPUT"
done

if [[ "$FAIL" -eq 1 ]]; then
  exit 1
fi

echo "PASS: test-launch-gemini-review.sh — launcher lifecycle tests passed"
