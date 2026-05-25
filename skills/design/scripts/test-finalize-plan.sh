#!/usr/bin/env bash
# Regression harness for finalize-plan.sh.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
SUBJECT="$SCRIPT_DIR/finalize-plan.sh"

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

TMPROOT=$(mktemp -d "${TMPDIR:-/tmp}/larch-finalize-plan-test.XXXXXX")
trap 'rm -rf "$TMPROOT"' EXIT

make_tree() {
    local dir="$1"
    mkdir -p "$dir"
    printf '# Plan\n\ndiff_lines: 3\n' > "$dir/plan.txt"
    printf '3\n' > "$dir/diff-lines.txt"
    printf '# Tally\n' > "$dir/voting-tally.md"
}

DESIGN="$TMPROOT/design"
make_tree "$DESIGN"
: > "$DESIGN/rejected-findings.md"
: > "$DESIGN/accepted-plan-findings.md"
: > "$DESIGN/oos.md"
out=$("$SUBJECT" --design-tmpdir "$DESIGN")
printf '%s\n' "$out" | grep -q '^FINALIZE_PLAN_STATUS=ok$' || fail "all-present tree did not pass"

rm "$DESIGN/rejected-findings.md" "$DESIGN/accepted-plan-findings.md" "$DESIGN/oos.md"
"$SUBJECT" --design-tmpdir "$DESIGN" >/dev/null
[[ -f "$DESIGN/rejected-findings.md" ]] || fail "missing rejected-findings.md not created"
[[ -f "$DESIGN/accepted-plan-findings.md" ]] || fail "missing accepted-plan-findings.md not created"
[[ -f "$DESIGN/oos.md" ]] || fail "missing oos.md not created"

rm "$DESIGN/plan.txt"
if "$SUBJECT" --design-tmpdir "$DESIGN" >/tmp/larch-finalize-plan-missing.out 2>&1; then
    fail "missing required plan.txt accepted"
fi
grep -q '^FINALIZE_PLAN_STATUS=missing-artifact$' /tmp/larch-finalize-plan-missing.out || fail "missing-artifact status not emitted"
grep -q '^FINALIZE_PLAN_ARTIFACT=plan.txt$' /tmp/larch-finalize-plan-missing.out || fail "missing artifact name not emitted"

if "$SUBJECT" --design-tmpdir "$TMPROOT/nope" >/tmp/larch-finalize-plan-nope.out 2>&1; then
    fail "missing design tmpdir accepted"
fi
grep -q '^FINALIZE_PLAN_STATUS=missing-design-tmpdir$' /tmp/larch-finalize-plan-nope.out || fail "missing-design-tmpdir status not emitted"

DESIGN2="$TMPROOT/design2"
make_tree "$DESIGN2"
"$SUBJECT" --design-tmpdir "$DESIGN2" >/dev/null
"$SUBJECT" --design-tmpdir "$DESIGN2" >/dev/null

echo "=== missing voting-tally.md is auto-created ==="
DESIGN_MISS_TALLY="$TMPROOT/design-miss-tally"
make_tree "$DESIGN_MISS_TALLY"
rm -f "$DESIGN_MISS_TALLY/voting-tally.md"
out_miss_tally=$("$SUBJECT" --design-tmpdir "$DESIGN_MISS_TALLY")
printf '%s\n' "$out_miss_tally" | grep -q '^FINALIZE_PLAN_STATUS=ok$' || fail "missing voting-tally should yield ok"
[[ -f "$DESIGN_MISS_TALLY/voting-tally.md" ]] || fail "voting-tally.md not auto-created"
[[ ! -s "$DESIGN_MISS_TALLY/voting-tally.md" ]] || fail "voting-tally.md should be empty after auto-create"

echo "=== empty voting-tally.md passes ==="
DESIGN_EMPTY_TALLY="$TMPROOT/design-empty-tally"
make_tree "$DESIGN_EMPTY_TALLY"
: > "$DESIGN_EMPTY_TALLY/voting-tally.md"
out_empty_tally=$("$SUBJECT" --design-tmpdir "$DESIGN_EMPTY_TALLY")
printf '%s\n' "$out_empty_tally" | grep -q '^FINALIZE_PLAN_STATUS=ok$' || fail "empty voting-tally should yield ok"

echo "=== voting-tally.md as a symlink rejected ==="
DESIGN_SYM_TALLY="$TMPROOT/design-sym-tally"
make_tree "$DESIGN_SYM_TALLY"
rm -f "$DESIGN_SYM_TALLY/voting-tally.md"
printf 'x' > "$DESIGN_SYM_TALLY/voting-tally-target.txt"
ln -s voting-tally-target.txt "$DESIGN_SYM_TALLY/voting-tally.md"
if "$SUBJECT" --design-tmpdir "$DESIGN_SYM_TALLY" >/tmp/larch-finalize-plan-sym.out 2>&1; then
    fail "symlink voting-tally should be rejected"
fi
grep -q '^FINALIZE_PLAN_STATUS=invalid-artifact$' /tmp/larch-finalize-plan-sym.out || fail "invalid-artifact not emitted for symlink tally"
grep -q '^FINALIZE_PLAN_ARTIFACT=voting-tally.md$' /tmp/larch-finalize-plan-sym.out || fail "artifact name wrong for symlink tally"

echo "PASS: test-finalize-plan.sh"
