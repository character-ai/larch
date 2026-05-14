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

# Voter files use "ID: VOTE" anchored format (uppercase, one vote per line).
V1="$TMPROOT/v1.txt"
V2="$TMPROOT/v2.txt"
V3="$TMPROOT/v3.txt"
cat > "$V1" <<'EOF'
FINDING_1: YES
FINDING_2: NO
OOS_1: YES
OOS_2: YES
EOF
cat > "$V2" <<'EOF'
FINDING_1: YES
FINDING_2: YES
OOS_1: NO
OOS_2: YES
EOF
cat > "$V3" <<'EOF'
FINDING_1: YES
FINDING_2: NO
OOS_1: YES
OOS_2: YES
EOF

DESIGN="$TMPROOT/design"
mkdir -p "$DESIGN"
out=$("$SUBJECT" --ballot-file "$BALLOT" --voter-files "$V1" "$V2" "$V3" --design-tmpdir "$DESIGN")
printf '%s\n' "$out" | grep -q '^TALLY_PLAN_REVIEW_STATUS=ok$' || fail "status ok not emitted"
# FINDING_1: 3 YES >= 2 threshold -> accepted.
grep -q 'FINDING_1' "$DESIGN/accepted-plan-findings.md" || fail "accepted finding missing"
# FINDING_2: 1 YES, 2 NO -> rejected.
grep -q 'FINDING_2' "$DESIGN/rejected-findings.md" || fail "rejected finding missing"
grep -q 'OOS_1' "$DESIGN/oos.md" || fail "accepted OOS missing from visibility file"
grep -q 'OOS_1' "$DESIGN/oos-accepted-design.md" || fail "accepted OOS missing from accepted-only file"
# OOS_2 has focus-area = security (unfenced) -> excluded from public outputs.
if grep -q 'OOS_2' "$DESIGN/oos.md" || grep -q 'OOS_2' "$DESIGN/oos-accepted-design.md"; then
    fail "security-tagged accepted OOS was not excluded"
fi
grep -q '| Reviewer | Proposed | Accepted | Neutral/Exon | Rejected | OOS-Proposed | OOS-Accepted | Score |' "$DESIGN/voting-tally.md" || fail "scoreboard header missing"
# Cursor-Arch: 1 accepted finding (+1), 1 accepted OOS (+1) = score 2.
grep -q '| Cursor-Arch | 1 | 1 | 0 | 0 | 1 | 1 | 2 |' "$DESIGN/voting-tally.md" || fail "scoreboard counts wrong for Cursor-Arch"

# Tie test: 2 voters, 1 YES 1 NO -> below unanimous-2 threshold -> not accepted.
V4="$TMPROOT/v4.txt"
V5="$TMPROOT/v5.txt"
cat > "$V4" <<'EOF'
FINDING_1: YES
EOF
cat > "$V5" <<'EOF'
FINDING_1: NO
EOF
DESIGN_TIE="$TMPROOT/design-tie"
mkdir -p "$DESIGN_TIE"
"$SUBJECT" --ballot-file "$BALLOT" --voter-files "$V4" "$V5" --design-tmpdir "$DESIGN_TIE" >/dev/null
# With 2 eligible voters: 1 YES is not unanimous -> not accepted.
if grep -q 'FINDING_1' "$DESIGN_TIE/accepted-plan-findings.md"; then
    fail "tie (1Y/1N) with 2 voters should not be accepted"
fi

# Security OOS in fenced code: should NOT be suppressed (only unfenced triggers exclusion).
BALLOT2="$TMPROOT/ballot2.md"
cat > "$BALLOT2" <<'EOF'
### OOS_3: Fenced security mention
- **Reviewer**: Cursor-Arch
- focus-area = documentation
- Concern: example shows `focus-area = security` in code.

### OOS_4: Unfenced security tag
- **Reviewer**: Codex-Edge
- focus-area = security
- Concern: real security finding.
EOF
V6="$TMPROOT/v6.txt"
cat > "$V6" <<'EOF'
OOS_3: YES
OOS_4: YES
EOF
DESIGN2="$TMPROOT/design2"
mkdir -p "$DESIGN2"
"$SUBJECT" --ballot-file "$BALLOT2" --voter-files "$V6" "$V6" --design-tmpdir "$DESIGN2" >/dev/null
# OOS_3 has focus-area=security only in a code span (fenced) -> public output allowed.
grep -q 'OOS_3' "$DESIGN2/oos.md" || fail "fenced security mention should not be suppressed from oos.md"
# OOS_4 has unfenced focus-area=security -> excluded from public outputs.
if grep -q 'OOS_4' "$DESIGN2/oos.md" || grep -q 'OOS_4' "$DESIGN2/oos-accepted-design.md"; then
    fail "unfenced security-tagged accepted OOS was not excluded"
fi

# SESSION_ENV_PATH handoff: accepted OOS written to parent tmpdir.
PARENT="$TMPROOT/parent-session"
mkdir -p "$PARENT"
SESSION_ENV="$PARENT/session-env.sh"
touch "$SESSION_ENV"
DESIGN3="$TMPROOT/design3"
mkdir -p "$DESIGN3"
V7="$TMPROOT/v7.txt"
cat > "$V7" <<'EOF'
OOS_1: YES
OOS_1: YES
EOF
"$SUBJECT" --ballot-file "$BALLOT" --voter-files "$V7" "$V7" --design-tmpdir "$DESIGN3" --session-env-path "$SESSION_ENV" >/dev/null
[[ -f "$PARENT/oos-accepted-design.md" ]] || fail "nested run did not write oos-accepted-design.md to parent tmpdir"

if "$SUBJECT" --ballot-file "$BALLOT" --voter-files "$TMPROOT/missing.txt" --design-tmpdir "$TMPROOT/nope" >/tmp/larch-tally-plan-review-fail.out 2>&1; then
    fail "missing voter file accepted"
fi
grep -q 'voter file is missing' /tmp/larch-tally-plan-review-fail.out || fail "missing voter diagnostic absent"

echo "PASS: test-tally-plan-review.sh"
