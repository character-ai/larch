#!/usr/bin/env bash
# Regression harness for tally-plan-review.sh.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
CLAUDE_PLUGIN_ROOT=$(cd "$SCRIPT_DIR/../../.." && pwd -P)
export CLAUDE_PLUGIN_ROOT
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
grep -q '| Reviewer | Proposed | Accepted | Neutral/Exon | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral/Exon | OOS-Rejected | Score |' "$DESIGN/voting-tally.md" || fail "scoreboard header missing"
# Cursor-Arch: 1 accepted finding (+1), 1 accepted OOS (+1) = score 2.
grep -q '| Cursor-Arch | 1 | 1 | 0 | 0 | 1 | 1 | 0 | 0 | 2 |' "$DESIGN/voting-tally.md" || fail "scoreboard counts wrong for Cursor-Arch"

# Rejected OOS subtracts one point.
BALLOT_OOS_REJECTED="$TMPROOT/ballot-oos-rejected.md"
cat > "$BALLOT_OOS_REJECTED" <<'EOF'
### OOS_1: Rejected follow-up
- **Reviewer**: Codex-Security
- focus-area = code-quality
- Concern: speculative follow-up.
EOF
V_OOS_REJECTED="$TMPROOT/v-oos-rejected.txt"
cat > "$V_OOS_REJECTED" <<'EOF'
OOS_1: NO
EOF
DESIGN_OOS_REJECTED="$TMPROOT/design-oos-rejected"
mkdir -p "$DESIGN_OOS_REJECTED"
"$SUBJECT" --ballot-file "$BALLOT_OOS_REJECTED" --voter-files "$V_OOS_REJECTED" "$V_OOS_REJECTED" "$V_OOS_REJECTED" --design-tmpdir "$DESIGN_OOS_REJECTED" >/dev/null
grep -q '| Codex-Security | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 1 | -1 |' "$DESIGN_OOS_REJECTED/voting-tally.md" || fail "rejected OOS did not subtract from score"

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

# Single-judge decisions are binding for YES, rejected for NO, and exonerated
# for EXONERATE.
DESIGN_ONE_YES="$TMPROOT/design-one-yes"
mkdir -p "$DESIGN_ONE_YES"
"$SUBJECT" --ballot-file "$BALLOT" --voter-files "$V4" --design-tmpdir "$DESIGN_ONE_YES" >/dev/null
grep -q 'FINDING_1' "$DESIGN_ONE_YES/accepted-plan-findings.md" || fail "single YES should accept FINDING_1"

DESIGN_ONE_NO="$TMPROOT/design-one-no"
mkdir -p "$DESIGN_ONE_NO"
"$SUBJECT" --ballot-file "$BALLOT" --voter-files "$V5" --design-tmpdir "$DESIGN_ONE_NO" >/dev/null
if grep -q 'FINDING_1' "$DESIGN_ONE_NO/accepted-plan-findings.md"; then
    fail "single NO should not accept FINDING_1"
fi
grep -q 'FINDING_1' "$DESIGN_ONE_NO/rejected-findings.md" || fail "single NO rejected finding missing"

V_EXON="$TMPROOT/v-exon.txt"
cat > "$V_EXON" <<'EOF'
FINDING_1: EXONERATE
EOF
DESIGN_ONE_EXON="$TMPROOT/design-one-exon"
mkdir -p "$DESIGN_ONE_EXON"
"$SUBJECT" --ballot-file "$BALLOT" --voter-files "$V_EXON" --design-tmpdir "$DESIGN_ONE_EXON" >/dev/null
grep -q '| FINDING_1 | 0 | 0 | 1 | 0 | exonerated |' "$DESIGN_ONE_EXON/voting-tally.md" || fail "single EXONERATE should be exonerated"
if grep -q 'FINDING_1' "$DESIGN_ONE_EXON/accepted-plan-findings.md"; then
    fail "single EXONERATE should not accept FINDING_1"
fi

DESIGN_ZERO="$TMPROOT/design-zero"
mkdir -p "$DESIGN_ZERO"
out_zero=$("$SUBJECT" --ballot-file "$BALLOT" --design-tmpdir "$DESIGN_ZERO")
printf '%s\n' "$out_zero" | grep -q '^TALLY_PLAN_REVIEW_STATUS=main-agent-vote-required$' || fail "zero voter status missing"
[[ ! -s "$DESIGN_ZERO/accepted-plan-findings.md" ]] || fail "zero voter accepted file should be empty"

V_NEUTRAL="$TMPROOT/v-neutral.txt"
: > "$V_NEUTRAL"
DESIGN_NEUTRAL="$TMPROOT/design-neutral"
mkdir -p "$DESIGN_NEUTRAL"
"$SUBJECT" --ballot-file "$BALLOT" --voter-files "$V4" "$V_NEUTRAL" "$V_NEUTRAL" --design-tmpdir "$DESIGN_NEUTRAL" >/dev/null
if grep -q 'FINDING_1' "$DESIGN_NEUTRAL/accepted-plan-findings.md"; then
    fail "3-voter panel with 1 YES and 2 JUDGE_ERROR should not accept"
fi
grep -q '| FINDING_1 | 1 | 0 | 0 | 2 | rejected |' "$DESIGN_NEUTRAL/voting-tally.md" || fail "JUDGE_ERROR quorum result row missing"

BALLOT_OOS_ONE="$TMPROOT/ballot-oos-one.md"
cat > "$BALLOT_OOS_ONE" <<'EOF'
### OOS_1: Single judge follow-up
- **Reviewer**: Cursor-Arch
- focus-area = documentation
- Concern: docs follow-up.
EOF
V_OOS_ONE="$TMPROOT/v-oos-one.txt"
cat > "$V_OOS_ONE" <<'EOF'
OOS_1: YES
EOF
DESIGN_OOS_ONE="$TMPROOT/design-oos-one"
mkdir -p "$DESIGN_OOS_ONE"
"$SUBJECT" --ballot-file "$BALLOT_OOS_ONE" --voter-files "$V_OOS_ONE" --design-tmpdir "$DESIGN_OOS_ONE" >/dev/null
grep -q 'OOS_1' "$DESIGN_OOS_ONE/oos-accepted-design.md" || fail "single YES OOS should be accepted"

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

# SESSION_ENV_PATH HARD handoff: write plan-review-tally to parent /implement run logs.
IMPLEMENT_PARENT="$TMPROOT/implement-parent"
mkdir -p "$IMPLEMENT_PARENT"
printf 'plan-review-run\n' > "$IMPLEMENT_PARENT/session-id"
SESSION_ENV_TALLY="$TMPROOT/design-session-env.sh"
{
    printf 'PREV_IMPLEMENT_TMPDIR=%s\n' "$IMPLEMENT_PARENT"
    printf 'POST_PLAN_WORKFLOW_PATH=HARD\n'
} > "$SESSION_ENV_TALLY"
DESIGN_TALLY="$TMPROOT/design-tally"
mkdir -p "$DESIGN_TALLY"
"$SUBJECT" --ballot-file "$BALLOT" --voter-files "$V1" "$V2" "$V3" --design-tmpdir "$DESIGN_TALLY" --session-env-path "$SESSION_ENV_TALLY" >/dev/null
TALLY_BATCH="$IMPLEMENT_PARENT/larch-logs/implement/plan-review-run/plan-review-tally.json"
[[ -f "$TALLY_BATCH" ]] || fail "nested HARD run did not write plan-review-tally batch"
jq -e '.batch == "plan-review-tally" and .mode == "hard" and .rounds == 1 and .accepted_count == 1 and .rejected_count == 1 and (.body | contains("## Rejected Plan Review Findings"))' \
    "$TALLY_BATCH" >/dev/null || fail "plan-review-tally batch content/counts wrong"

SESSION_ENV_NO_MODE="$TMPROOT/design-session-env-no-mode.sh"
printf 'PREV_IMPLEMENT_TMPDIR=%s\n' "$IMPLEMENT_PARENT" > "$SESSION_ENV_NO_MODE"
rm -f "$TALLY_BATCH"
"$SUBJECT" --ballot-file "$BALLOT" --voter-files "$V1" "$V2" "$V3" --design-tmpdir "$DESIGN_TALLY" --session-env-path "$SESSION_ENV_NO_MODE" >/dev/null
[[ ! -f "$TALLY_BATCH" ]] || fail "missing workflow path should skip plan-review-tally flush"

if "$SUBJECT" --ballot-file "$BALLOT" --voter-files "$TMPROOT/missing.txt" --design-tmpdir "$TMPROOT/nope" >/tmp/larch-tally-plan-review-fail.out 2>&1; then
    fail "missing voter file accepted"
fi
grep -q 'voter file is missing' /tmp/larch-tally-plan-review-fail.out || fail "missing voter diagnostic absent"

echo "PASS: test-tally-plan-review.sh"
