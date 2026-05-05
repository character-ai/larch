#!/bin/bash
# Regression test for launch-gemini-review.sh lifecycle and JSON normalization.
#
# Wired into: make test-harnesses
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
TMPDIR=$(mktemp -d /tmp/larch-test-launch-gemini-XXXXXX)
trap 'rm -rf "$TMPDIR"' EXIT

FAIL=0
fail() {
  echo "FAIL: $1" >&2
  FAIL=1
}

STUB_BIN="$TMPDIR/bin"
mkdir -p "$STUB_BIN"
cat > "$STUB_BIN/gemini" <<'STUB'
#!/usr/bin/env bash
case "${GEMINI_STUB_MODE:-ok}" in
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

MISSING_JQ_OUTPUT="$TMPDIR/gemini-missing-jq.txt"
PATH="$STUB_BIN:$PATH" LARCH_TEST_FORCE_MISSING_JQ=true \
  "$REPO_ROOT/scripts/launch-gemini-review.sh" --output "$MISSING_JQ_OUTPUT" --timeout 1800 --prompt "test"
[[ ! -s "$MISSING_JQ_OUTPUT" ]] \
  || fail "Expected empty output when jq is missing"
grep -q '^127$' "${MISSING_JQ_OUTPUT}.done" \
  || fail "Expected 127 .done when jq is missing"
grep -q 'MISSING_JQ' "${MISSING_JQ_OUTPUT}.diag" \
  || fail "Expected MISSING_JQ diagnostic"

if [[ "$FAIL" -eq 1 ]]; then
  exit 1
fi

echo "PASS: test-launch-gemini-review.sh — launcher lifecycle tests passed"
