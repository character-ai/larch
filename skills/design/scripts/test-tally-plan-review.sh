#!/usr/bin/env bash
# Regression harness for tally-plan-review.sh.

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
SUBJECT="$SCRIPT_DIR/tally-plan-review.sh"

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

TMPROOT=$(mktemp -d "${TMPDIR:-/tmp}/larch-tally-plan-review-test.XXXXXX")
trap 'rm -rf "$TMPROOT"' EXIT

BALLOT="$TMPROOT/ballot.md"
cat > "$BALLOT" <<'EOF'
### FINDING_1: Fix parser
- **Reviewer**: Cursor-Arch
- focus-area = correctness
- Concern: parser misses bad input.

### FINDING_2: Optional cleanup
- **Reviewer**: Codex-Pragmatic
- focus-area = code-quality
- Concern: cleanup could be smaller.

### OOS_1: Follow-up docs
- **Reviewer**: Cursor-Arch
- focus-area = documentation
- Concern: docs follow-up.

### OOS_2: Token leak audit
- **Reviewer**: Codex-Security
- focus-area = security
- Concern: security-sensitive follow-up.
EOF

V1="$TMPROOT/v1.txt"
V2="$TMPROOT/v2.txt"
V3="$TMPROOT/v3.txt"
cat > "$V1" <<'EOF'
FINDING_1 YES
FINDING_2 NO
OOS_1 YES
OOS_2 YES
EOF
cat > "$V2" <<'EOF'
FINDING_1 YES
FINDING_2 YES
OOS_1 NO
OOS_2 YES
EOF
cat > "$V3" <<'EOF'
FINDING_1 YES
FINDING_2 NO
OOS_1 YES
OOS_2 YES
EOF

DESIGN="$TMPROOT/design"
mkdir -p "$DESIGN"
out=$("$SUBJECT" --ballot-file "$BALLOT" --voter-files "$V1" "$V2" "$V3" --design-tmpdir "$DESIGN")
printf '%s\n' "$out" | grep -q '^TALLY_PLAN_REVIEW_STATUS=ok$' || fail "status ok not emitted"
grep -q 'FINDING_1' "$DESIGN/accepted-plan-findings.md" || fail "accepted finding missing"
grep -q 'FINDING_2' "$DESIGN/rejected-findings.md" || fail "rejected finding missing"
grep -q 'OOS_1' "$DESIGN/oos.md" || fail "accepted OOS missing from visibility file"
grep -q 'OOS_1' "$DESIGN/oos-accepted-design.md" || fail "accepted OOS missing from accepted-only file"
if grep -q 'OOS_2' "$DESIGN/oos.md" || grep -q 'OOS_2' "$DESIGN/oos-accepted-design.md"; then
    fail "security-tagged accepted OOS was not excluded"
fi
grep -q '| Reviewer | Proposed | Accepted | Neutral/Exon | Rejected | OOS-Proposed | OOS-Accepted | Score |' "$DESIGN/voting-tally.md" || fail "scoreboard header missing"
grep -q '| Cursor-Arch | 1 | 1 | 0 | 0 | 1 | 1 | 3 |' "$DESIGN/voting-tally.md" || fail "scoreboard counts wrong for Cursor-Arch"

V4="$TMPROOT/v4.txt"
V5="$TMPROOT/v5.txt"
cat > "$V4" <<'EOF'
FINDING_1 YES
EOF
cat > "$V5" <<'EOF'
FINDING_1 NO
EOF
DESIGN_TIE="$TMPROOT/design-tie"
mkdir -p "$DESIGN_TIE"
"$SUBJECT" --ballot-file "$BALLOT" --voter-files "$V4" "$V5" --design-tmpdir "$DESIGN_TIE" >/dev/null
grep -q '| FINDING_1 | 1 | 1 | 0 | neutral |' "$DESIGN_TIE/voting-tally.md" || fail "tie did not render neutral"

if "$SUBJECT" --ballot-file "$BALLOT" --voter-files "$TMPROOT/missing.txt" --design-tmpdir "$TMPROOT/nope" >/tmp/larch-tally-plan-review-fail.out 2>&1; then
    fail "missing voter file accepted"
fi
grep -q 'voter file is missing' /tmp/larch-tally-plan-review-fail.out || fail "missing voter diagnostic absent"

echo "PASS: test-tally-plan-review.sh"
