#!/bin/bash
# Regression test for wait-for-reviewers.sh argv validation + stdout grammar,
# and collector-side wait error passthrough (closes #1186 + #1188 / #1200).
#
# Wired into: make test-harnesses (test-harnesses-5 shard).
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
TMPDIR=$(mktemp -d "${TMPDIR:-/tmp}/larch-test-wait-XXXXXX")
trap 'rm -rf "$TMPDIR"' EXIT

# Fast poll so the DONE case finishes quickly. The TIMEOUT case still spends
# about 1s wall-clock because wait's loop is gated on $SECONDS vs $TIMEOUT.
export WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.05

FAIL=0
fail() {
  echo "FAIL: $1" >&2
  FAIL=1
}

assert_reject() {
  local label="$1"
  shift
  local stderr_pattern="$1"
  shift
  local stdout="$TMPDIR/${label}.stdout"
  local stderr="$TMPDIR/${label}.stderr"
  local code

  set +e
  "$REPO_ROOT/scripts/wait-for-reviewers.sh" "$@" >"$stdout" 2>"$stderr"
  code=$?
  set -e

  [[ "$code" -eq 1 ]] \
    || fail "$label: expected exit 1, got $code"
  grep -q "$stderr_pattern" "$stderr" \
    || fail "$label: expected stderr to match '$stderr_pattern'"
}

# R1/R2: case-statement rejections (literal 0, non-numeric).
assert_reject "reject-timeout-zero" 'must be a positive integer' --timeout 0 "$TMPDIR/dummy.done"
assert_reject "reject-timeout-abc" 'must be a positive integer' --timeout abc "$TMPDIR/dummy.done"

# R3: line-26 ${2:?} requires-value rejection, not the case-statement.
assert_reject "reject-timeout-missing" '\-\-timeout requires a value' --timeout

# R4: happy-path DONE grammar.
SENTINEL="$TMPDIR/done-ok.done"
printf '0\n' > "$SENTINEL"
set +e
"$REPO_ROOT/scripts/wait-for-reviewers.sh" --timeout 5 "$SENTINEL" >"$TMPDIR/r4.stdout" 2>"$TMPDIR/r4.stderr"
R4_CODE=$?
set -e
[[ "$R4_CODE" -eq 0 ]] \
  || fail "R4: expected exit 0 on existing sentinel, got $R4_CODE"
grep -q '^DONE done-ok: exit=0$' "$TMPDIR/r4.stdout" \
  || fail "R4: expected DONE stdout grammar"

# R5: TIMEOUT grammar on missing sentinel under --timeout 1 (~1s wall-clock).
set +e
"$REPO_ROOT/scripts/wait-for-reviewers.sh" --timeout 1 "$TMPDIR/never.done" >"$TMPDIR/r5.stdout" 2>"$TMPDIR/r5.stderr"
R5_CODE=$?
set -e
[[ "$R5_CODE" -eq 0 ]] \
  || fail "R5: expected exit 0 on normal timeout, got $R5_CODE"
grep -q '^TIMEOUT never$' "$TMPDIR/r5.stdout" \
  || fail "R5: expected TIMEOUT stdout grammar"

# C1: collector swallows nothing on --timeout 0.
set +e
"$REPO_ROOT/scripts/collect-agent-results.sh" --timeout 0 "$TMPDIR/never.txt" >"$TMPDIR/c1.stdout" 2>"$TMPDIR/c1.stderr"
C1_CODE=$?
set -e
[[ "$C1_CODE" -eq 1 ]] \
  || fail "C1: expected collector exit 1 on --timeout 0, got $C1_CODE"
grep -q 'must be a positive integer' "$TMPDIR/c1.stderr" \
  || fail "C1: expected wait positive-integer message on collector stderr"
grep -q 'collect-agent-results.sh: wait-for-reviewers.sh exited' "$TMPDIR/c1.stderr" \
  || fail "C1: expected collector trailer line 'collect-agent-results.sh: wait-for-reviewers.sh exited <N>' on stderr"
if grep -qE '^(REVIEWER_FILE|STATUS)=' "$TMPDIR/c1.stdout"; then
  fail "C1: collector emitted reviewer records on stdout despite usage error"
fi

# C2: collector swallows nothing on --timeout abc.
set +e
"$REPO_ROOT/scripts/collect-agent-results.sh" --timeout abc "$TMPDIR/never.txt" >"$TMPDIR/c2.stdout" 2>"$TMPDIR/c2.stderr"
C2_CODE=$?
set -e
[[ "$C2_CODE" -eq 1 ]] \
  || fail "C2: expected collector exit 1 on --timeout abc, got $C2_CODE"
grep -q 'must be a positive integer' "$TMPDIR/c2.stderr" \
  || fail "C2: expected wait positive-integer message on collector stderr"
grep -q 'collect-agent-results.sh: wait-for-reviewers.sh exited' "$TMPDIR/c2.stderr" \
  || fail "C2: expected collector trailer line 'collect-agent-results.sh: wait-for-reviewers.sh exited <N>' on stderr"
if grep -qE '^(REVIEWER_FILE|STATUS)=' "$TMPDIR/c2.stdout"; then
  fail "C2: collector emitted reviewer records on stdout despite usage error"
fi

if [[ "$FAIL" -eq 1 ]]; then
  exit 1
fi

echo "PASS: test-wait-for-reviewers.sh - wait+collector contract pinned"
