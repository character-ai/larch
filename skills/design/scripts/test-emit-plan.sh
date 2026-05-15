#!/usr/bin/env bash
# Regression harness for emit-plan.sh.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
SUBJECT="$SCRIPT_DIR/emit-plan.sh"

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

TMPROOT=$(mktemp -d "${TMPDIR:-/tmp}/larch-emit-plan-test.XXXXXX")
trap 'rm -rf "$TMPROOT"' EXIT

case_dir="$TMPROOT/case"
mkdir -p "$case_dir"

printf '# Plan\n\nDo it.\n\ndiff_lines: 12\n' > "$case_dir/plan.txt"
out=$("$SUBJECT" --design-tmpdir "$case_dir")
printf '%s\n' "$out" | grep -q '^EMIT_PLAN_STATUS=ok$' || fail "valid plan did not emit ok"
printf '%s\n' "$out" | grep -q '^DIFF_LINES=12$' || fail "valid plan did not emit DIFF_LINES"
[[ "$(cat "$case_dir/diff-lines.txt")" == "12" ]] || fail "diff-lines.txt not written"

printf '# Plan\n\nDo it.\n' > "$case_dir/plan.txt"
if "$SUBJECT" --design-tmpdir "$case_dir" >/tmp/larch-emit-plan-missing.out 2>&1; then
    fail "missing diff_lines was accepted"
fi
grep -q '^EMIT_PLAN_STATUS=missing-diff-lines$' /tmp/larch-emit-plan-missing.out || fail "missing diff_lines status not emitted"

printf '# Plan\n\ndiff_lines: many\n' > "$case_dir/plan.txt"
if "$SUBJECT" --design-tmpdir "$case_dir" >/tmp/larch-emit-plan-nonint.out 2>&1; then
    fail "non-integer diff_lines was accepted"
fi
grep -q '^EMIT_PLAN_STATUS=missing-diff-lines$' /tmp/larch-emit-plan-nonint.out || fail "non-integer status not emitted"

: > "$case_dir/plan.txt"
if "$SUBJECT" --design-tmpdir "$case_dir" >/tmp/larch-emit-plan-empty.out 2>&1; then
    fail "empty plan was accepted"
fi
grep -q '^EMIT_PLAN_STATUS=missing-diff-lines$' /tmp/larch-emit-plan-empty.out || fail "empty plan status not emitted"

printf '# Plan\n\ndiff_lines: 7\n' > "$case_dir/plan.txt"
"$SUBJECT" --design-tmpdir "$case_dir" >/dev/null
printf '# Revised Plan\n\ndiff_lines: 9\n' > "$case_dir/plan.txt"
"$SUBJECT" --design-tmpdir "$case_dir" >/dev/null
[[ "$(cat "$case_dir/diff-lines.txt")" == "9" ]] || fail "idempotent re-run did not update diff-lines.txt"

echo "PASS: test-emit-plan.sh"
