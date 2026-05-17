#!/usr/bin/env bash
# test-tally-code-votes.sh — regression harness for tally-code-votes.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
SCRIPT="$SCRIPT_DIR/tally-code-votes.sh"

FAIL=0
WORKDIR=$(mktemp -d "${TMPDIR:-/tmp}/test-tally-code-votes.XXXXXX")
trap 'rm -rf "$WORKDIR"' EXIT

assert_eq() {
    local name="$1" got="$2" want="$3"
    if [[ "$got" == "$want" ]]; then
        printf '  ok   %s\n' "$name"
    else
        printf '  FAIL %s — got %q want %q\n' "$name" "$got" "$want"
        FAIL=1
    fi
}

mk_ballot() {
    local file="$1"
    cat > "$file" <<'EOF'
### FINDING_1: First in-scope finding
- **Reviewer**: Codex-Structure
- **Concern**: Concern 1.
- **Suggested revision**: Revision 1.

### FINDING_2: Second in-scope finding
- **Reviewer**: Cursor-Security
- **Concern**: Concern 2.
- **Suggested revision**: Revision 2.

### FINDING_3: [OUT_OF_SCOPE] OOS observation
- **Reviewer**: Codex-Plan-fidelity
- **Concern**: Pre-existing thing.
- **Suggested revision**: Revision 3.
EOF
}

echo "# Case: 3 voters, 2 YES on FINDING_1, 1 YES on FINDING_2, 2 YES on FINDING_3 (OOS)"
TMP="$WORKDIR/case1"
mkdir -p "$TMP"
mk_ballot "$TMP/ballot.md"
printf 'FINDING_1: YES\nFINDING_2: YES\nFINDING_3: YES\n' > "$TMP/cursor-vote-output.txt"
printf 'FINDING_1: YES\nFINDING_2: NO -- low priority\nFINDING_3: YES\n' > "$TMP/codex-vote-output.txt"
printf 'FINDING_1: NO -- already handled elsewhere\nFINDING_2: NO -- not actionable\nFINDING_3: NO -- not worth filing\n' > "$TMP/claude-vote-output.txt"
out="$TMP/out.env"
"$SCRIPT" --ballot-file "$TMP/ballot.md" \
    --voter-files "$TMP/cursor-vote-output.txt" "$TMP/codex-vote-output.txt" "$TMP/claude-vote-output.txt" \
    --review-tmpdir "$TMP" > "$out"
got=$(awk -F= '$1=="ACCEPTED_COUNT"{print $2}' "$out"); assert_eq "ACCEPTED_COUNT=1 (FINDING_1 has 2 YES)" "$got" "1"
got=$(awk -F= '$1=="REJECTED_COUNT"{print $2}' "$out"); assert_eq "REJECTED_COUNT=1 (FINDING_2 has 1 YES)" "$got" "1"
got=$(awk -F= '$1=="OOS_ACCEPTED_COUNT"{print $2}' "$out"); assert_eq "OOS_ACCEPTED_COUNT=1 (FINDING_3 has 2 YES, accepted)" "$got" "1"
got=$(awk -F= '$1=="OOS_REJECTED_COUNT"{print $2}' "$out"); assert_eq "OOS_REJECTED_COUNT=0" "$got" "0"
# Spot-check the artifacts.
grep -Fq 'FINDING_1: First in-scope finding' "$TMP/accepted-findings.md" || { FAIL=1; printf '  FAIL accepted-findings missing FINDING_1\n'; }
grep -Fq 'FINDING_2' "$TMP/rejected-findings.md" || { FAIL=1; printf '  FAIL rejected-findings missing FINDING_2\n'; }
grep -Fq 'OOS observation' "$TMP/oos-accepted-review.md" || { FAIL=1; printf '  FAIL oos-accepted missing FINDING_3\n'; }
grep -Fq '| Reviewer | Proposed | Accepted | Neutral/Exon | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral/Exon | OOS-Rejected | Score |' "$TMP/voting-tally.md" || { FAIL=1; printf '  FAIL scoreboard header missing OOS outcome columns\n'; }

echo "# Case: OOS rejected subtracts 1 from reviewer score"
TMP="$WORKDIR/case1b"
mkdir -p "$TMP"
cat > "$TMP/ballot.md" <<'EOF'
### FINDING_1: [OUT_OF_SCOPE] Rejected OOS observation
- **Reviewer**: Codex-Security
- **Concern**: Pre-existing concern that should not be tracked.
- **Suggested revision**: No change.
EOF
printf 'FINDING_1: NO -- not worth filing\n' > "$TMP/cursor-vote-output.txt"
printf 'FINDING_1: NO -- not actionable\n' > "$TMP/codex-vote-output.txt"
printf 'FINDING_1: NO -- too speculative\n' > "$TMP/claude-vote-output.txt"
out="$TMP/out.env"
"$SCRIPT" --ballot-file "$TMP/ballot.md" \
    --voter-files "$TMP/cursor-vote-output.txt" "$TMP/codex-vote-output.txt" "$TMP/claude-vote-output.txt" \
    --review-tmpdir "$TMP" > "$out"
got=$(awk -F= '$1=="OOS_REJECTED_COUNT"{print $2}' "$out"); assert_eq "OOS_REJECTED_COUNT=1" "$got" "1"
grep -Fq '| Codex-Security | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 1 | -1 |' "$TMP/voting-tally.md" || { FAIL=1; printf '  FAIL rejected OOS did not subtract from score\n'; }

echo "# Case: 2 voters, unanimous YES (3-voter threshold falls back to 2-voter unanimous)"
TMP="$WORKDIR/case2"
mkdir -p "$TMP"
mk_ballot "$TMP/ballot.md"
printf 'FINDING_1: YES\nFINDING_2: YES\nFINDING_3: YES\n' > "$TMP/cursor-vote-output.txt"
printf 'FINDING_1: YES\nFINDING_2: NO -- nope\nFINDING_3: YES\n' > "$TMP/codex-vote-output.txt"
out="$TMP/out.env"
"$SCRIPT" --ballot-file "$TMP/ballot.md" \
    --voter-files "$TMP/cursor-vote-output.txt" "$TMP/codex-vote-output.txt" \
    --review-tmpdir "$TMP" > "$out"
got=$(awk -F= '$1=="ACCEPTED_COUNT"{print $2}' "$out"); assert_eq "FINDING_1 unanimous YES → accepted" "$got" "1"
got=$(awk -F= '$1=="REJECTED_COUNT"{print $2}' "$out"); assert_eq "FINDING_2 1Y/1N → rejected (not unanimous)" "$got" "1"
got=$(awk -F= '$1=="OOS_ACCEPTED_COUNT"{print $2}' "$out"); assert_eq "FINDING_3 unanimous YES → OOS accepted" "$got" "1"

echo "# Case: 1 voter → skip with warning, all accepted"
TMP="$WORKDIR/case3"
mkdir -p "$TMP"
mk_ballot "$TMP/ballot.md"
printf 'FINDING_1: NO\nFINDING_2: NO\nFINDING_3: NO\n' > "$TMP/cursor-vote-output.txt"
out="$TMP/out.env"
"$SCRIPT" --ballot-file "$TMP/ballot.md" \
    --voter-files "$TMP/cursor-vote-output.txt" \
    --review-tmpdir "$TMP" > "$out"
got=$(awk -F= '$1=="ACCEPTED_COUNT"{print $2}' "$out"); assert_eq "1 voter → 2 in-scope all accepted" "$got" "2"
got=$(awk -F= '$1=="OOS_ACCEPTED_COUNT"{print $2}' "$out"); assert_eq "1 voter → OOS all accepted" "$got" "1"
got=$(awk -F= '$1=="VOTING_SKIPPED_WARNING"{print $2}' "$out")
case "$got" in *"Voting skipped"*) printf '  ok   warning emitted\n' ;; *) FAIL=1; printf '  FAIL warning missing (got %q)\n' "$got" ;; esac

echo "# Case: --both-down true → bypass voting"
TMP="$WORKDIR/case4"
mkdir -p "$TMP"
mk_ballot "$TMP/ballot.md"
out="$TMP/out.env"
"$SCRIPT" --ballot-file "$TMP/ballot.md" \
    --review-tmpdir "$TMP" --both-down true > "$out"
got=$(awk -F= '$1=="ACCEPTED_COUNT"{print $2}' "$out"); assert_eq "both-down → 2 in-scope accepted" "$got" "2"
got=$(awk -F= '$1=="OOS_ACCEPTED_COUNT"{print $2}' "$out"); assert_eq "both-down → OOS accepted" "$got" "1"

echo "# Case: security-tagged accepted OOS is NOT written to public file"
TMP="$WORKDIR/case5"
mkdir -p "$TMP"
cat > "$TMP/ballot.md" <<'EOF'
### FINDING_1: [OUT_OF_SCOPE] Privilege escalation in setup
- **Reviewer**: Codex-Security
- **Concern**: focus-area = security, this is sensitive.
- **Suggested revision**: redacted.
EOF
printf 'FINDING_1: YES\n' > "$TMP/cursor-vote-output.txt"
printf 'FINDING_1: YES\n' > "$TMP/codex-vote-output.txt"
printf 'FINDING_1: YES\n' > "$TMP/claude-vote-output.txt"
out="$TMP/out.env"
"$SCRIPT" --ballot-file "$TMP/ballot.md" \
    --voter-files "$TMP/cursor-vote-output.txt" "$TMP/codex-vote-output.txt" "$TMP/claude-vote-output.txt" \
    --review-tmpdir "$TMP" > "$out"
got=$(awk -F= '$1=="OOS_ACCEPTED_COUNT"{print $2}' "$out"); assert_eq "security OOS counted as accepted" "$got" "1"
if [[ -s "$TMP/oos-accepted-review.md" ]]; then
    FAIL=1; printf '  FAIL oos-accepted-review.md should be empty for security-tagged item\n'
else
    printf '  ok   security OOS held locally (oos-accepted-review.md empty)\n'
fi

if [[ "$FAIL" -eq 0 ]]; then
    printf 'PASS: test-tally-code-votes.sh\n'
    exit 0
else
    printf 'FAIL: test-tally-code-votes.sh\n'
    exit 1
fi
