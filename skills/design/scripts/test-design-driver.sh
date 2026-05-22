#!/usr/bin/env bash
# Regression harness for design-driver.sh.
# Note: this harness exercises `design-driver.sh` action stepping only; it does
# not pin removed `/implement` argv surfaces.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
SUBJECT="$SCRIPT_DIR/design-driver.sh"
DESIGN_SKILL="$SCRIPT_DIR/../SKILL.md"

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

# EMIT_PLAN must be re-runnable: running the same action file a second time
# should re-execute EMIT_PLAN (not skip it) because plan.txt may have changed.
printf '# Revised Plan\n\ndiff_lines: 8\n' > "$DESIGN/plan.txt"
out2=$("$SUBJECT" --design-tmpdir "$DESIGN" --action-file "$actions")
printf '%s\n' "$out2" | grep -q '^STEP_STARTED=EMIT_PLAN$' || fail "EMIT_PLAN re-run was skipped (should be re-runnable)"
[[ "$(cat "$DESIGN/diff-lines.txt")" == "8" ]] || fail "diff-lines.txt not updated on EMIT_PLAN re-run"
# FINALIZE: non-EMIT_PLAN actions are still sentinel-guarded on replay.
printf '%s\n' "$out2" | grep -q '^STEP_SKIPPED=FINALIZE REASON=already-completed$' || fail "completed FINALIZE was not skipped on replay"

DESIGN2="$TMPROOT/design2"
mkdir -p "$DESIGN2/.completed"
printf '# Plan\n\ndiff_lines: 6\n' > "$DESIGN2/plan.txt"
printf '6\n' > "$DESIGN2/diff-lines.txt"
printf '# Tally\n' > "$DESIGN2/voting-tally.md"
: > "$DESIGN2/.completed/emit_plan"
out=$("$SUBJECT" --design-tmpdir "$DESIGN2" --action-file "$actions" --resume-from FINALIZE)
# EMIT_PLAN before resume point: skip (before-resume, not completed-before-resume when no sentinel guards it).
# Since EMIT_PLAN skips sentinels, the before-resume path applies when it appears before the resume step.
printf '%s\n' "$out" | grep -q '^STEP_SKIPPED=EMIT_PLAN REASON=before-resume$' || fail "resume did not skip EMIT_PLAN before resume point"
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

[[ -f "$DESIGN_SKILL" ]] || fail "missing skills/design/SKILL.md"

trivial_row=$'| `--trivial` |'
simple_row=$'| `--simple` |'
hard_row=$'| `--hard` |'
grep -Fq "$trivial_row" "$DESIGN_SKILL" || fail "design SKILL missing trivial tier row"
grep -Fq "$simple_row" "$DESIGN_SKILL" || fail "design SKILL missing simple tier row"
grep -Fq "$hard_row" "$DESIGN_SKILL" || fail "design SKILL missing hard tier row"
grep -Fq 'sketch_budget=0' "$DESIGN_SKILL" || fail "design SKILL missing sketch_budget=0 mapping pin"
grep -Fq 'review_budget=quick' "$DESIGN_SKILL" || fail "design SKILL missing review_budget=quick mapping pin"
grep -Fq 'workflow_path=HARD' "$DESIGN_SKILL" || fail "design SKILL missing workflow_path=HARD tier mapping pin"

echo "PASS: test-design-driver.sh"
