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
grep -q '| Reviewer | Proposed | Accepted | Exonerated | Rejected | OOS-Proposed | OOS-Accepted | OOS-Exonerated | OOS-Rejected | Score |' "$DESIGN/voting-tally.md" || fail "scoreboard header missing"
# Cursor-Arch: 1 accepted finding (+1), 1 accepted OOS (+1) = score 2.
grep -q '| Cursor-Arch | 1 | 1 | 0 | 0 | 1 | 1 | 0 | 0 | 2 |' "$DESIGN/voting-tally.md" || fail "scoreboard counts wrong for Cursor-Arch"
[[ -s "$DESIGN/plan-review/round-1/findings-classification.tsv" ]] || fail "default findings-classification.tsv missing"
head -n 1 "$DESIGN/plan-review/round-1/findings-classification.tsv" | grep -q $'finding_id\tfinding_reviewers\tvoting_result' || fail "findings-classification.tsv header missing finding_reviewers"
grep -q $'FINDING_1\tCursor-Arch\taccepted' "$DESIGN/plan-review/round-1/findings-classification.tsv" || fail "classification row missing accepted FINDING_1"

DESIGN_SLOTS="$TMPROOT/design-slots"
mkdir -p "$DESIGN_SLOTS"
CUSTOM_TSV="$TMPROOT/custom/findings-classification.tsv"
"$SUBJECT" --ballot-file "$BALLOT" --voter "Claude:$V1" --voter "Codex:$V2" --voter "Cursor:$V3" --design-tmpdir "$DESIGN_SLOTS" --findings-classification-out "$CUSTOM_TSV" >/dev/null
[[ -s "$CUSTOM_TSV" ]] || fail "custom findings-classification out missing"
grep -q $'FINDING_1\tCursor-Arch\taccepted\tYES' "$CUSTOM_TSV" || fail "--voter slot metadata did not populate v1"

DESIGN_LEGACY_WARN="$TMPROOT/design-legacy-warn"
mkdir -p "$DESIGN_LEGACY_WARN"
"$SUBJECT" --ballot-file "$BALLOT" --voter-files "$V1" "$V2" "$V3" --design-tmpdir "$DESIGN_LEGACY_WARN" >/dev/null 2>"$TMPROOT/legacy-warning.err"
grep -q -- '--voter-files is deprecated' "$TMPROOT/legacy-warning.err" || fail "legacy --voter-files deprecation warning missing"

echo "=== duplicate --voter slot is rejected ==="
DESIGN_DUP_SLOT="$TMPROOT/design-dup-slot"
mkdir -p "$DESIGN_DUP_SLOT"
set +e
"$SUBJECT" --ballot-file "$BALLOT" --voter "Claude:$V1" --voter "Claude:$V2" --design-tmpdir "$DESIGN_DUP_SLOT" >/tmp/larch-tally-plan-review-dup-slot.out 2>&1
rc_dup_slot=$?
set -e
[[ "$rc_dup_slot" -eq 2 ]] || fail "duplicate --voter slot should exit 2"
grep -q 'duplicate --voter slot' /tmp/larch-tally-plan-review-dup-slot.out || fail "duplicate slot diagnostic missing"

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
grep -q $'FINDING_1\tCursor-Arch\tmain-agent-vote-required\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t' "$DESIGN_ZERO/plan-review/round-1/findings-classification.tsv" || fail "zero voter classification row should remain pending with empty voter cells"

echo "=== MainAgent cannot be combined with panel slots ==="
DESIGN_MAIN_AGENT_MIX="$TMPROOT/design-main-agent-mix"
mkdir -p "$DESIGN_MAIN_AGENT_MIX"
set +e
"$SUBJECT" --ballot-file "$BALLOT" --voter "Claude:$V1" --voter "MainAgent:$V2" --design-tmpdir "$DESIGN_MAIN_AGENT_MIX" >/tmp/larch-tally-plan-review-main-agent.out 2>&1
rc_main_agent_mix=$?
set -e
[[ "$rc_main_agent_mix" -eq 2 ]] || fail "MainAgent+panel mix should exit 2"
grep -q 'MainAgent cannot be combined with panel voter slots' /tmp/larch-tally-plan-review-main-agent.out || fail "MainAgent mix diagnostic missing"

echo "=== symlinked voter file is rejected ==="
DESIGN_VOTER_SYMLINK="$TMPROOT/design-voter-symlink"
mkdir -p "$DESIGN_VOTER_SYMLINK"
ln -sf "$V1" "$TMPROOT/v1-link.txt"
set +e
"$SUBJECT" --ballot-file "$BALLOT" --voter-files "$TMPROOT/v1-link.txt" --design-tmpdir "$DESIGN_VOTER_SYMLINK" >/tmp/larch-tally-plan-review-symlink.out 2>&1
rc_voter_symlink=$?
set -e
[[ "$rc_voter_symlink" -eq 2 ]] || fail "symlinked voter file should exit 2"
grep -q 'voter file is missing or unreadable' /tmp/larch-tally-plan-review-symlink.out || fail "symlinked voter diagnostic missing"

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

if "$SUBJECT" --ballot-file "$BALLOT" --voter-files "$TMPROOT/missing.txt" --design-tmpdir "$TMPROOT/nope" >/tmp/larch-tally-plan-review-fail.out 2>&1; then
    fail "missing voter file accepted"
fi
grep -q 'voter file is missing' /tmp/larch-tally-plan-review-fail.out || fail "missing voter diagnostic absent"

echo "=== malformed-ballot abort still writes voting-tally.md ==="
MALFORMED_BALLOT="$TMPROOT/malformed-ballot.md"
cat > "$MALFORMED_BALLOT" <<'EOF'
### FINDING_1: First
- **Reviewer**: Cursor-Arch
- focus-area = correctness
- Concern: first block.

### FINDING_1: Duplicate heading
- **Reviewer**: Codex-Pragmatic
- focus-area = code-quality
- Concern: duplicate breaks split.
EOF
DESIGN_MALFORMED="$TMPROOT/design-malformed"
mkdir -p "$DESIGN_MALFORMED"
set +e
"$SUBJECT" --ballot-file "$MALFORMED_BALLOT" --voter-files "$V1" --design-tmpdir "$DESIGN_MALFORMED" >/tmp/larch-tally-plan-review-malformed.out 2>&1
rc_malformed=$?
set -e
[[ "$rc_malformed" -eq 2 ]] || fail "malformed ballot should exit 2"
[[ -s "$DESIGN_MALFORMED/voting-tally.md" ]] || fail "voting-tally.md missing or empty on malformed ballot"
grep -q '# Plan Review Voting Tally' "$DESIGN_MALFORMED/voting-tally.md" || fail "degraded header missing"
grep -q '\*\*⚠ Tally aborted:' "$DESIGN_MALFORMED/voting-tally.md" || fail "abort prefix missing"
[[ "$(wc -l < "$DESIGN_MALFORMED/plan-review/round-1/findings-classification.tsv" | tr -d ' ')" == "1" ]] || fail "malformed ballot should rewrite classification TSV header only"

echo "=== ballot-file unreadable abort still writes voting-tally.md ==="
NONEXIST="$TMPROOT/no-such-ballot-2720.md"
DESIGN_NOBALLOT="$TMPROOT/design-noballot"
mkdir -p "$DESIGN_NOBALLOT"
set +e
"$SUBJECT" --ballot-file "$NONEXIST" --voter-files "$V1" --design-tmpdir "$DESIGN_NOBALLOT" >/dev/null 2>&1
rc_noballot=$?
set -e
[[ "$rc_noballot" -eq 2 ]] || fail "missing ballot should exit 2"
[[ -s "$DESIGN_NOBALLOT/voting-tally.md" ]] || fail "voting-tally.md missing or empty on unreadable ballot"
[[ "$(wc -l < "$DESIGN_NOBALLOT/plan-review/round-1/findings-classification.tsv" | tr -d ' ')" == "1" ]] || fail "missing ballot should rewrite classification TSV header only"

echo "PASS: test-tally-plan-review.sh"
