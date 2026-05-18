#!/usr/bin/env bash
# test-write-rejected-findings.sh — offline harness for write-rejected-findings.sh.

set -euo pipefail
export LARCH_QUIET_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
HELPER="$SCRIPT_DIR/write-rejected-findings.sh"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-write-rejected-findings.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT
PASS=0; FAIL=0
pass(){ PASS=$((PASS+1)); printf 'PASS: %s\n' "$1"; }
fail(){ FAIL=$((FAIL+1)); printf 'FAIL: %s\n' "$1" >&2; }
assert_contains(){ case "$2" in *"$1"*) pass "$3" ;; *) fail "$3 (missing $1)" ;; esac; }
finish(){ [ "$FAIL" -eq 0 ] || exit 1; printf 'PASS=%s\n' "$PASS"; }

empty="$TMP_ROOT/empty"; mkdir -p "$empty"
out=$("$HELPER" --implement-tmpdir "$empty")
assert_contains 'STATUS=empty' "$out" 'empty status emitted'
assert_contains 'REJECTED_COUNT=0' "$out" 'empty count emitted'

case_dir="$TMP_ROOT/nonempty"; mkdir -p "$case_dir"
printf '[Code Review] one\n\n- two\n' > "$case_dir/rejected-findings.md"
out=$("$HELPER" --implement-tmpdir "$case_dir" --run-id run-3 --log-root "$case_dir/logs")
assert_contains 'STATUS=ok' "$out" 'nonempty status emitted'
assert_contains 'REJECTED_COUNT=2' "$out" 'nonempty count emitted'
if [ -s "$case_dir/logs/implement/run-3/rejected-findings.md" ]; then pass 'optional copy written'; else fail 'optional copy written'; fi

set +e
bad=$("$HELPER" 2>/dev/null)
rc=$?
set -e
if [ "$rc" -ne 0 ]; then pass 'missing tmpdir exits non-zero'; else fail 'missing tmpdir exits non-zero'; fi
assert_contains 'STATUS=failed' "$bad" 'missing args emits envelope'

finish
