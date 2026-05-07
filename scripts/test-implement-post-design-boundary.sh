#!/bin/bash
# Regression test for issue #1014: post-/design boundary checkpoint reminder
# in skills/implement/SKILL.md Step 1 (normal mode), the post-design wrapper,
# and the matching --emit-load-breadcrumb flag handler in
# skills/design/scripts/read-design-manifest.sh.
#
# Exit 0 on pass, exit 1 on any assertion failure.

set -euo pipefail

# Symlink-safe: use BASH_SOURCE[0] for repo-root resolution to match sibling
# harnesses (e.g., test-implement-anti-polling-rule.sh).
REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
SKILL_MD="$REPO_ROOT/skills/implement/SKILL.md"
READER="$REPO_ROOT/skills/design/scripts/read-design-manifest.sh"
WRAPPER="$REPO_ROOT/skills/implement/scripts/post-design-boundary.sh"
WRAPPER_MD="$REPO_ROOT/skills/implement/scripts/post-design-boundary.md"

fail() { echo "FAIL: $1" >&2; exit 1; }

[[ -f "$SKILL_MD" ]] || fail "skills/implement/SKILL.md missing"
[[ -f "$READER" ]] || fail "skills/design/scripts/read-design-manifest.sh missing"

# Extract the Post-/design boundary checkpoint blockquote slice — the awk
# state machine starts at the line containing the header literal and runs to
# the FIRST blank line that follows the blockquote. Anti-pattern strings (B)
# and the breadcrumb literal (E) must live INSIDE this slice, not just
# anywhere in SKILL.md.
SLICE=$(awk '
    /Post-\/design boundary checkpoint/ { in_slice=1 }
    in_slice && /^[[:space:]]*$/ { exit }
    in_slice { print }
' "$SKILL_MD")
[[ -n "$SLICE" ]] || fail "(A) Post-/design boundary checkpoint slice not found in SKILL.md"

# (A) Header literal present in SKILL.md.
grep -q "Post-/design boundary checkpoint" "$SKILL_MD" \
    || fail "(A) missing 'Post-/design boundary checkpoint' header in SKILL.md"

# (B) Anti-pattern strings present INSIDE the boundary-checkpoint slice
#     (case-insensitive). Asserts the strings stay where they are
#     load-bearing — drifting them out of the warning text silently weakens
#     the reminder.
for s in "returning control" "design phase complete" "handing off"; do
    printf '%s\n' "$SLICE" | grep -qi -- "$s" \
        || fail "(B) anti-pattern string missing from boundary-checkpoint slice: $s"
done

# (C) Both breadcrumb forms present in SKILL.md.
grep -q '🔃 1.r: design plan | rebase' "$SKILL_MD" \
    || fail "(C) missing 1.r rebase breadcrumb literal"
grep -q '🔶 2: implementation' "$SKILL_MD" \
    || fail "(C) missing Step 2 breadcrumb literal"

# (D) NEVER #7 reference present.
grep -q 'NEVER #7' "$SKILL_MD" \
    || fail "(D) missing 'NEVER #7' reference in SKILL.md"

# (E) Manifest-loaded breadcrumb literal present in SKILL.md (uses plan=<basename>
#     not PLAN_FILE=<basename> per #1014 review FINDING_2 — KV-namespace collision).
grep -q '📥 1: design plan — manifest loaded (plan=' "$SKILL_MD" \
    || fail "(E) missing manifest-loaded breadcrumb literal (plan=...) in SKILL.md"

# (F') SKILL.md invokes the wrapper, and the wrapper owns the reader call with
#      --emit-load-breadcrumb so the breadcrumb path is preserved end-to-end.
# shellcheck disable=SC2016 # literal ${CLAUDE_PLUGIN_ROOT} is intentional.
grep -q '\${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/post-design-boundary.sh' "$SKILL_MD" \
    || fail "(F') SKILL.md missing post-design-boundary.sh invocation"
[[ -f "$WRAPPER" ]] || fail "(F') post-design-boundary.sh missing"
grep -q 'read-design-manifest.sh.*--emit-load-breadcrumb' "$WRAPPER" \
    || fail "(F') wrapper missing read-design-manifest.sh --emit-load-breadcrumb invocation"

# (K) Wrapper exists, is executable, and has a sibling contract.
[[ -x "$WRAPPER" ]] || fail "(K) post-design-boundary.sh missing or not executable"
[[ -f "$WRAPPER_MD" ]] || fail "(K) post-design-boundary.md missing"

# (L) SKILL.md Step 1 normal mode invokes the wrapper with the three required
#     flags. Quoting may vary; this assertion pins the logical Bash block.
WRAPPER_BLOCK=$(awk '
    /post-design-boundary\.sh/ { in_block=1 }
    in_block { print }
    in_block && /--design-only/ { exit }
' "$SKILL_MD")
[[ -n "$WRAPPER_BLOCK" ]] || fail "(L) wrapper invocation block missing"
for flag in "--implement-tmpdir" "--session-env" "--design-only"; do
    printf '%s\n' "$WRAPPER_BLOCK" | grep -q -- "$flag" \
        || fail "(L) wrapper invocation missing flag: $flag"
done

# (M) The post-/design slice no longer calls read-design-manifest.sh with
#     --emit-load-breadcrumb directly; the wrapper owns that call.
# shellcheck disable=SC2016 # literal "$IMPLEMENT_TMPDIR" is intentional.
grep -q 'read-design-manifest.sh --implement-tmpdir "\$IMPLEMENT_TMPDIR" --emit-load-breadcrumb' "$SKILL_MD" \
    && fail "(M) SKILL.md still calls read-design-manifest.sh --emit-load-breadcrumb directly"

# (N) Step 1 carries the post-/design legal next-actions matrix.
for sentinel in \
    "post-/design legal next-actions matrix" \
    "Wrapper output" \
    "If a downstream paragraph appears to disagree, the matrix wins."; do
    grep -q "$sentinel" "$SKILL_MD" \
        || fail "(N) missing post-/design matrix sentinel: $sentinel"
done

# (G) read-design-manifest.sh defines the --emit-load-breadcrumb flag handler.
grep -q -- '--emit-load-breadcrumb' "$READER" \
    || fail "(G) read-design-manifest.sh missing --emit-load-breadcrumb flag handler"

# (H) Reader emits the breadcrumb literal on the success path with plan= (not PLAN_FILE=).
grep -q '📥 1: design plan — manifest loaded (plan=' "$READER" \
    || fail "(H) read-design-manifest.sh missing breadcrumb emission (plan=...)"

# (I) Reader does NOT emit the breadcrumb with the old PLAN_FILE= form anywhere
#     (guards against partial revert).
grep -q '📥 1: design plan — manifest loaded (PLAN_FILE=' "$READER" \
    && fail "(I) read-design-manifest.sh still emits the legacy PLAN_FILE= form — would collide with KV envelope key"
grep -q '📥 1: design plan — manifest loaded (PLAN_FILE=' "$SKILL_MD" \
    && fail "(I) SKILL.md still references the legacy PLAN_FILE= breadcrumb form"

# (J) Stdout-shape integration test (#1014 review FINDING_3, Cursor-Testing +
#     Cursor-Edge): synthesize a minimal valid manifest, run the reader with
#     --emit-load-breadcrumb, and assert (a) the breadcrumb appears AFTER the
#     MANIFEST_OK=true line, (b) the breadcrumb is the LAST line of stdout,
#     and (c) the breadcrumb is SUPPRESSED on the missing-manifest failure
#     path.
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/design-export"
cat > "$TMP/design-export/plan.txt" <<'EOF_PLAN'
test plan body
EOF_PLAN
: > "$TMP/design-export/voting-tally.md"
echo "tally" > "$TMP/design-export/voting-tally.md"
: > "$TMP/design-export/contested-decisions.md"
: > "$TMP/design-export/oos.md"
: > "$TMP/design-export/rejected-findings.md"
: > "$TMP/design-export/accepted-plan-findings.md"
cat > "$TMP/design-export/manifest.env" <<EOF_MANIFEST
MANIFEST_VERSION=1
PLAN_FILE=$TMP/design-export/plan.txt
PLAN_REVIEW_TALLY_FILE=$TMP/design-export/voting-tally.md
CONTESTED_CRITERIA_FILE=$TMP/design-export/contested-decisions.md
OOS_FILE=$TMP/design-export/oos.md
REJECTED_FINDINGS_FILE=$TMP/design-export/rejected-findings.md
ACCEPTED_PLAN_FINDINGS_FILE=$TMP/design-export/accepted-plan-findings.md
TIMESTAMP=2026-01-01T00:00:00Z
SESSION_ID=test-session
EOF_MANIFEST

OUT=$(bash "$READER" --implement-tmpdir "$TMP" --emit-load-breadcrumb)
printf '%s\n' "$OUT" | grep -q '^MANIFEST_OK=true$' \
    || fail "(J) reader did not emit MANIFEST_OK=true on the synthesized valid manifest"
LAST_LINE=$(printf '%s\n' "$OUT" | tail -n 1)
case "$LAST_LINE" in
    "📥 1: design plan — manifest loaded (plan=plan.txt)") ;;
    *) fail "(J) breadcrumb is not the last line of stdout (got: $LAST_LINE)" ;;
esac

# Failure-path: missing manifest. Reader exits 0 with MANIFEST_FAILED envelope
# and MUST NOT emit the breadcrumb.
TMP2=$(mktemp -d)
OUT_FAIL=$(bash "$READER" --implement-tmpdir "$TMP2" --emit-load-breadcrumb)
rm -rf "$TMP2"
printf '%s\n' "$OUT_FAIL" | grep -q '^MANIFEST_FAILED=true$' \
    || fail "(J) reader did not emit MANIFEST_FAILED=true on missing manifest"
printf '%s\n' "$OUT_FAIL" | grep -q '📥 1: design plan — manifest loaded' \
    && fail "(J) reader emitted the breadcrumb on a failure path — must be success-only"

echo "PASS: post-/design boundary checkpoint regression test"
