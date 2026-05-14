#!/usr/bin/env bash
# Regression harness for design-driver.sh.

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
SUBJECT="$SCRIPT_DIR/design-driver.sh"

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

TMPROOT=$(mktemp -d "${TMPDIR:-/tmp}/larch-design-driver-test.XXXXXX")
trap 'rm -rf "$TMPROOT"' EXIT

DESIGN="$TMPROOT/design"
mkdir -p "$DESIGN"
printf '# Plan\n\ndiff_lines: 5\n' > "$DESIGN/plan.txt"
printf '# Tally\n' > "$DESIGN/voting-tally.md"

actions="$TMPROOT/actions.txt"
cat > "$actions" <<EOF
ACTION=EMIT_PLAN
ACTION=FINALIZE
EOF

out=$("$SUBJECT" --design-tmpdir "$DESIGN" --action-file "$actions")
printf '%s\n' "$out" | grep -q '^STEP_STARTED=EMIT_PLAN$' || fail "EMIT_PLAN did not start"
printf '%s\n' "$out" | grep -q '^STEP_COMPLETED=FINALIZE$' || fail "FINALIZE did not complete"
[[ -f "$DESIGN/.completed/emit_plan" || -f "$DESIGN/.completed/emit-plan" ]] || fail "completion sentinel not written"

out=$("$SUBJECT" --design-tmpdir "$DESIGN" --action-file "$actions")
printf '%s\n' "$out" | grep -q '^STEP_SKIPPED=EMIT_PLAN REASON=already-completed$' || fail "completed EMIT_PLAN not skipped"

DESIGN2="$TMPROOT/design2"
mkdir -p "$DESIGN2/.completed"
printf '# Plan\n\ndiff_lines: 6\n' > "$DESIGN2/plan.txt"
printf '6\n' > "$DESIGN2/diff-lines.txt"
printf '# Tally\n' > "$DESIGN2/voting-tally.md"
: > "$DESIGN2/.completed/emit_plan"
out=$("$SUBJECT" --design-tmpdir "$DESIGN2" --action-file "$actions" --resume-from FINALIZE)
printf '%s\n' "$out" | grep -q '^STEP_SKIPPED=EMIT_PLAN REASON=completed-before-resume$' || fail "resume did not skip prior completed step"
printf '%s\n' "$out" | grep -q '^STEP_COMPLETED=FINALIZE$' || fail "resume did not run target step"

bad="$TMPROOT/bad-actions.txt"
cat > "$bad" <<EOF
ACTION=EMIT_PLAN
EOF
DESIGN3="$TMPROOT/design3"
mkdir -p "$DESIGN3"
printf '# Plan without estimate\n' > "$DESIGN3/plan.txt"
if "$SUBJECT" --design-tmpdir "$DESIGN3" --action-file "$bad" >/tmp/larch-design-driver-fail.out 2>&1; then
    fail "failing action was accepted"
fi
grep -q '^STEP_FAILED=EMIT_PLAN REASON=exit-1$' /tmp/larch-design-driver-fail.out || fail "failure status not emitted"

unknown="$TMPROOT/unknown-actions.txt"
cat > "$unknown" <<'EOF'
hello
ACTION=UNKNOWN ARGS=--flag value
EOF
out=$("$SUBJECT" --design-tmpdir "$DESIGN" --action-file "$unknown")
printf '%s\n' "$out" | grep -q '^ACTION_PASSTHROUGH=hello$' || fail "non-action passthrough missing"
printf '%s\n' "$out" | grep -q '^ACTION_PASSTHROUGH=ACTION=UNKNOWN ARGS=--flag value$' || fail "unknown action passthrough missing"

echo "PASS: test-design-driver.sh"
