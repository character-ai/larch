#!/usr/bin/env bash
# Regression harness for finalize-plan.sh.

set -euo pipefail

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

echo "PASS: test-finalize-plan.sh"
