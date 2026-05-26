#!/usr/bin/env bash
# test-tally-code-votes.sh — regression harness for tally-code-votes.sh.

set -euo pipefail
export LARCH_QUIET_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
CLAUDE_PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
export CLAUDE_PLUGIN_ROOT
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
printf 'FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\nFINDING_2: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false\nFINDING_3: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false\n' > "$TMP/cursor-vote-output.txt"
printf 'FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\nFINDING_2: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false -- low priority\nFINDING_3: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false\n' > "$TMP/codex-vote-output.txt"
printf 'FINDING_1: NO CORRECTNESS=partially-true SEVERITY=minor QUALITY=weak UNCERTAIN=false -- already handled elsewhere\nFINDING_2: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false -- not actionable\nFINDING_3: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false -- not worth filing\n' > "$TMP/claude-vote-output.txt"
out="$TMP/out.env"
"$SCRIPT" --ballot-file "$TMP/ballot.md" \
    --voter-files "$TMP/cursor-vote-output.txt" "$TMP/codex-vote-output.txt" "$TMP/claude-vote-output.txt" \
    --review-tmpdir "$TMP" > "$out"
got=$(awk -F= '$1=="ACCEPTED_COUNT"{print $2}' "$out"); assert_eq "ACCEPTED_COUNT=1 (FINDING_1 has 2 YES)" "$got" "1"
got=$(awk -F= '$1=="REJECTED_COUNT"{print $2}' "$out"); assert_eq "REJECTED_COUNT=1 (FINDING_2 has 1 YES)" "$got" "1"
got=$(awk -F= '$1=="EXONERATED_COUNT"{print $2}' "$out"); assert_eq "EXONERATED_COUNT=0 (no exonerated findings)" "$got" "0"
got=$(awk -F= '$1=="NEUTRAL_COUNT"{print $2}' "$out"); assert_eq "NEUTRAL_COUNT=0 (no neutral findings)" "$got" "0"
got=$(awk -F= '$1=="FINDING_2_OUTCOME"{print $2}' "$TMP/review-tally.env"); assert_eq "review-tally.env records rejected outcome explicitly" "$got" "rejected"
got=$(awk -F= '$1=="ACCEPTED_COUNT"{print $2}' "$TMP/review-tally.env"); assert_eq "review-tally.env stores accepted count summary" "$got" "1"
got=$(awk -F= '$1=="OOS_ACCEPTED_COUNT"{print $2}' "$out"); assert_eq "OOS_ACCEPTED_COUNT=1 (FINDING_3 has 2 YES, accepted)" "$got" "1"
got=$(awk -F= '$1=="OOS_REJECTED_COUNT"{print $2}' "$out"); assert_eq "OOS_REJECTED_COUNT=0" "$got" "0"
classification_file=$(awk -F= '$1=="FINDINGS_CLASSIFICATION_TSV_FILE"{print $2}' "$out")
[[ -f "$classification_file" ]] || { FAIL=1; printf '  FAIL classification TSV not emitted\n'; }
read -r classification_header < "$classification_file"
assert_eq "classification TSV header" "$classification_header" $'finding_id\treviewer_slots\tvoting_result\tv1_vote\tv1_correctness\tv1_severity\tv1_quality\tv1_uncertain\tv2_vote\tv2_correctness\tv2_severity\tv2_quality\tv2_uncertain\tv3_vote\tv3_correctness\tv3_severity\tv3_quality\tv3_uncertain'
grep -Fq $'FINDING_1\tCodex-Structure\taccepted\tYES\ttrue\tmajor\tgood\tfalse\tYES\ttrue\tmajor\tgood\tfalse\tNO\tpartially-true\tminor\tweak\tfalse' "$classification_file" \
    || { FAIL=1; printf '  FAIL classification TSV missing rated FINDING_1 row\n'; }
# Spot-check the artifacts.
grep -Fq 'FINDING_1: First in-scope finding' "$TMP/accepted-findings.md" || { FAIL=1; printf '  FAIL accepted-findings missing FINDING_1\n'; }
grep -Fq 'FINDING_2' "$TMP/rejected-findings.md" || { FAIL=1; printf '  FAIL rejected-findings missing FINDING_2\n'; }
grep -Fq 'OOS observation' "$TMP/oos-accepted-review.md" || { FAIL=1; printf '  FAIL oos-accepted missing FINDING_3\n'; }
grep -Fq '| Reviewer | Proposed | Accepted | Exonerated | Rejected | OOS-Proposed | OOS-Accepted | OOS-Exonerated | OOS-Rejected | Score | Status |' "$TMP/voting-tally.md" || { FAIL=1; printf '  FAIL scoreboard header missing OOS outcome columns\n'; }
if grep -Fq 'Degraded code-review panel' "$TMP/voting-tally.md"; then
    FAIL=1; printf '  FAIL clean 3-voter fixture should not emit degraded panel banner\n'
else
    printf '  ok   clean 3-voter fixture emits no degraded panel banner\n'
fi
grep -Fq 'STATUS=OK' "$TMP/voting-tally.md" || { FAIL=1; printf '  FAIL clean 3-voter fixture should populate live row Status=OK\n'; }

echo "# Case: merged ballot — comma-separated **Reviewer(s)** fans out scoreboard rows"
TMP="$WORKDIR/case_comma_reviewers"
mkdir -p "$TMP"
cat > "$TMP/ballot.md" <<'EOF'
### FINDING_1: merged finding
- **Reviewer(s)**: cursor-a-output.txt, cursor-b-output.txt, cursor-c-output.txt
- **Concern**: one concern.
- **Suggested revision**: fix it
EOF
printf 'FINDING_1: YES\n' > "$TMP/cursor-vote-output.txt"
printf 'FINDING_1: YES\n' > "$TMP/codex-vote-output.txt"
printf 'FINDING_1: YES\n' > "$TMP/claude-vote-output.txt"
out="$TMP/out.env"
"$SCRIPT" --ballot-file "$TMP/ballot.md" \
    --voter-files "$TMP/cursor-vote-output.txt" "$TMP/codex-vote-output.txt" "$TMP/claude-vote-output.txt" \
    --review-tmpdir "$TMP" > "$out"
grep -Fq '| cursor-a |' "$TMP/voting-tally.md" || { FAIL=1; printf '  FAIL scoreboard missing cursor-a row for comma-split Reviewer(s)\n'; }
grep -Fq '| cursor-b |' "$TMP/voting-tally.md" || { FAIL=1; printf '  FAIL scoreboard missing cursor-b row\n'; }
grep -Fq '| cursor-c |' "$TMP/voting-tally.md" || { FAIL=1; printf '  FAIL scoreboard missing cursor-c row\n'; }

echo "# Case: direct OOS_N ballot IDs tally and classify without legacy FINDING_N aliases"
TMP="$WORKDIR/case_oos_n_ids"
mkdir -p "$TMP"
cat > "$TMP/ballot.md" <<'EOF'
### OOS_1: Future cleanup
- **Reviewer**: Cursor-Testing
- **Concern**: Pre-existing issue.
- **Suggested revision**: Track later.
EOF
printf 'OOS_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false\n' > "$TMP/cursor-vote-output.txt"
printf 'OOS_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=good UNCERTAIN=false\n' > "$TMP/codex-vote-output.txt"
printf 'OOS_1: NO CORRECTNESS=partially-true SEVERITY=nit QUALITY=weak UNCERTAIN=false\n' > "$TMP/claude-vote-output.txt"
out="$TMP/out.env"
"$SCRIPT" --ballot-file "$TMP/ballot.md" \
    --voter-files "$TMP/cursor-vote-output.txt" "$TMP/codex-vote-output.txt" "$TMP/claude-vote-output.txt" \
    --review-tmpdir "$TMP" > "$out"
got=$(awk -F= '$1=="OOS_ACCEPTED_COUNT"{print $2}' "$out"); assert_eq "direct OOS_N accepted count" "$got" "1"
got=$(awk -F= '$1=="OOS_1_OUTCOME"{print $2}' "$TMP/review-tally.env"); assert_eq "review-tally.env records direct OOS_N outcome" "$got" "accepted"
classification_file=$(awk -F= '$1=="FINDINGS_CLASSIFICATION_TSV_FILE"{print $2}' "$out")
grep -Fq $'OOS_1\tCursor-Testing\taccepted\tYES\ttrue\tminor\tadequate\tfalse\tYES\ttrue\tminor\tgood\tfalse\tNO\tpartially-true\tnit\tweak\tfalse' "$classification_file" \
    || { FAIL=1; printf '  FAIL classification TSV missing direct OOS_N row\n'; }

echo "# Case: parser failure emits WARN breadcrumb and records JUDGE_ERROR in TSV"
TMP="$WORKDIR/case_parser_failure_warn"
mkdir -p "$TMP"
cat > "$TMP/ballot.md" <<'EOF'
### FINDING_1: parser failure fixture
- **Reviewer**: Cursor-Testing
- **Concern**: Parser can fail.
- **Suggested revision**: Preserve WARN breadcrumb.
EOF
printf 'FINDING_1: YES\n' > "$TMP/good-vote-output.txt"
out="$TMP/out.env"
env -u LARCH_QUIET_DISABLE LARCH_BREADCRUMBS_SURFACED_FILE="$TMP/surfaced" "$SCRIPT" --ballot-file "$TMP/ballot.md" \
    --voter-files "$TMP/good-vote-output.txt" "$TMP/missing-vote-output.txt" \
    --review-tmpdir "$TMP" > "$out"
grep -Fq 'WARN=judge vote/rating parser failed' "$out" \
    || { FAIL=1; printf '  FAIL parser failure WARN breadcrumb missing\n'; }
classification_file=$(awk -F= '$1=="FINDINGS_CLASSIFICATION_TSV_FILE"{print $2}' "$out")
grep -Fq $'FINDING_1\tCursor-Testing\trejected\tYES\t\t\t\ttrue\tJUDGE_ERROR\t\t\t\ttrue\t\t\t\t\t' "$classification_file" \
    || { FAIL=1; printf '  FAIL parser failure should record JUDGE_ERROR in TSV\n'; }

echo "# Case: voter parse-rate diag emits degraded voter banner"
TMP="$WORKDIR/case_voter_parse_banner"
mkdir -p "$TMP"
mk_ballot "$TMP/ballot.md"
printf 'FINDING_1: YES\nFINDING_2: YES\nFINDING_3: YES\n' > "$TMP/cursor-vote-output.txt"
printf 'FINDING_1: YES\nFINDING_2: NO\nFINDING_3: YES\n' > "$TMP/codex-vote-output.txt"
printf 'FINDING_1: NO\nFINDING_2: NO\nFINDING_3: NO\n' > "$TMP/claude-vote-output.txt"
printf 'voter_tool=cursor\njudge_error_count=3\ntotal_findings=3\nvoter_file=%s/cursor-vote-output.txt\nvoter_sha256=%s\n' "$TMP" "$(shasum -a 256 "$TMP/cursor-vote-output.txt" | awk '{print $1}')" > "$TMP/cursor-vote-output-parse-rate-diag.txt"
out="$TMP/out.env"
"$SCRIPT" --ballot-file "$TMP/ballot.md" \
    --voter-files "$TMP/cursor-vote-output.txt" "$TMP/codex-vote-output.txt" "$TMP/claude-vote-output.txt" \
    --review-tmpdir "$TMP" > "$out"
grep -Fq '1 voter slot(s) emitted narrative-only output' "$TMP/voting-tally.md" \
    || { FAIL=1; printf '  FAIL voter parse-rate degraded banner missing\n'; }
grep -Fq '2 judge(s) available. Panel tier: unanimous-2.' "$TMP/voting-tally.md" \
    || { FAIL=1; printf '  FAIL voter parse-rate should reduce effective judges in banner\n'; }

echo "# Case: voter parse-rate and reviewer NOT_SUBSTANTIVE banners can coexist"
TMP="$WORKDIR/case_voter_parse_combined_banner"
mkdir -p "$TMP"
mk_ballot "$TMP/ballot.md"
printf 'FINDING_1: YES\nFINDING_2: YES\nFINDING_3: YES\n' > "$TMP/cursor-vote-output.txt"
printf 'FINDING_1: YES\nFINDING_2: NO\nFINDING_3: YES\n' > "$TMP/codex-vote-output.txt"
printf 'FINDING_1: NO\nFINDING_2: NO\nFINDING_3: NO\n' > "$TMP/claude-vote-output.txt"
printf 'voter_tool=cursor\njudge_error_count=3\ntotal_findings=3\nvoter_file=%s/cursor-vote-output.txt\nvoter_sha256=%s\n' "$TMP" "$(shasum -a 256 "$TMP/cursor-vote-output.txt" | awk '{print $1}')" > "$TMP/cursor-vote-output-parse-rate-diag.txt"
out="$TMP/out.env"
"$SCRIPT" --ballot-file "$TMP/ballot.md" \
    --voter-files "$TMP/cursor-vote-output.txt" "$TMP/codex-vote-output.txt" "$TMP/claude-vote-output.txt" \
    --not-substantive-count 1 \
    --review-tmpdir "$TMP" > "$out"
grep -Fq '1 reviewer slot(s) emitted narrative-only output (NOT_SUBSTANTIVE)' "$TMP/voting-tally.md" \
    || { FAIL=1; printf '  FAIL combined banner case missing reviewer NOT_SUBSTANTIVE banner\n'; }
grep -Fq '1 voter slot(s) emitted narrative-only output' "$TMP/voting-tally.md" \
    || { FAIL=1; printf '  FAIL combined banner case missing voter parse-rate banner\n'; }

echo "# Case: per-output parse-rate diags reduce effective quorum and ignore stale unrelated diags"
TMP="$WORKDIR/case_voter_parse_effective_quorum"
mkdir -p "$TMP"
mk_ballot "$TMP/ballot.md"
printf 'FINDING_1: YES\nFINDING_2: YES\nFINDING_3: YES\n' > "$TMP/cursor-vote-output.txt"
printf 'FINDING_1: NO\nFINDING_2: NO\nFINDING_3: NO\n' > "$TMP/codex-vote-output.txt"
printf 'FINDING_1: narrative only\nFINDING_2: narrative only\nFINDING_3: narrative only\n' > "$TMP/claude-vote-output.txt"
printf 'voter_tool=claude\njudge_error_count=3\ntotal_findings=3\nvoter_file=%s/claude-vote-output.txt\nvoter_sha256=%s\n' "$TMP" "$(shasum -a 256 "$TMP/claude-vote-output.txt" | awk '{print $1}')" > "$TMP/claude-vote-output-parse-rate-diag.txt"
printf 'stale\n' > "$TMP/cursor-vote-output-parse-rate-diag.txt"
out="$TMP/out.env"
"$SCRIPT" --ballot-file "$TMP/ballot.md" \
    --voter-files "$TMP/cursor-vote-output.txt" "$TMP/codex-vote-output.txt" "$TMP/claude-vote-output.txt" \
    --review-tmpdir "$TMP" > "$out"
grep -Fq '1 voter slot(s) emitted narrative-only output' "$TMP/voting-tally.md" \
    || { FAIL=1; printf '  FAIL effective quorum case missing voter parse-rate banner\n'; }
grep -Fq '| FINDING_1 | 1 | 1 | 0 | 0 | neutral |' "$TMP/voting-tally.md" \
    || { FAIL=1; printf '  FAIL effective quorum case should classify 1 YES / 1 NO as neutral after removing the dead slot from tallying\n'; }
got=$(awk -F= '$1=="VOTER_COUNT"{print $2}' "$out"); assert_eq "VOTER_COUNT reflects effective judges when parse-rate degrades a slot" "$got" "2"
got=$(awk -F= '$1=="ELIGIBLE_VOTER_COUNT"{print $2}' "$out"); assert_eq "ELIGIBLE_VOTER_COUNT preserves raw voter file count" "$got" "3"

echo "# Case: all voter files parse-rate fail → main-agent-vote-required uses effective quorum"
TMP="$WORKDIR/case_voter_parse_all_failed"
mkdir -p "$TMP"
mk_ballot "$TMP/ballot.md"
printf 'FINDING_1: narrative only\nFINDING_2: narrative only\nFINDING_3: narrative only\n' > "$TMP/cursor-vote-output.txt"
printf 'FINDING_1: narrative only\nFINDING_2: narrative only\nFINDING_3: narrative only\n' > "$TMP/codex-vote-output.txt"
printf 'FINDING_1: narrative only\nFINDING_2: narrative only\nFINDING_3: narrative only\n' > "$TMP/claude-vote-output.txt"
printf 'voter_tool=cursor\njudge_error_count=3\ntotal_findings=3\nvoter_file=%s/cursor-vote-output.txt\nvoter_sha256=%s\n' "$TMP" "$(shasum -a 256 "$TMP/cursor-vote-output.txt" | awk '{print $1}')" > "$TMP/cursor-vote-output-parse-rate-diag.txt"
printf 'voter_tool=codex\njudge_error_count=3\ntotal_findings=3\nvoter_file=%s/codex-vote-output.txt\nvoter_sha256=%s\n' "$TMP" "$(shasum -a 256 "$TMP/codex-vote-output.txt" | awk '{print $1}')" > "$TMP/codex-vote-output-parse-rate-diag.txt"
printf 'voter_tool=claude\njudge_error_count=3\ntotal_findings=3\nvoter_file=%s/claude-vote-output.txt\nvoter_sha256=%s\n' "$TMP" "$(shasum -a 256 "$TMP/claude-vote-output.txt" | awk '{print $1}')" > "$TMP/claude-vote-output-parse-rate-diag.txt"
out="$TMP/out.env"
"$SCRIPT" --ballot-file "$TMP/ballot.md" \
    --voter-files "$TMP/cursor-vote-output.txt" "$TMP/codex-vote-output.txt" "$TMP/claude-vote-output.txt" \
    --review-tmpdir "$TMP" > "$out"
got=$(awk -F= '$1=="TALLY_STATUS"{print $2}' "$out"); assert_eq "all parse-rate failures trigger main-agent-vote-required" "$got" "main-agent-vote-required"
got=$(awk -F= '$1=="ELIGIBLE_VOTER_COUNT"{print $2}' "$out"); assert_eq "all parse-rate failures preserve eligible count" "$got" "3"
got=$(awk -F= '$1=="VOTER_COUNT"{print $2}' "$out"); assert_eq "all parse-rate failures drop effective count to zero" "$got" "0"
grep -Fq '3 voter slot(s) emitted narrative-only output' "$TMP/voting-tally.md" \
    || { FAIL=1; printf '  FAIL all parse-rate failures should still emit voter parse-rate banner on early exit\n'; }

echo "# Case: stale parse-rate diag for replaced voter output is ignored"
TMP="$WORKDIR/case_voter_parse_stale_diag_replaced_output"
mkdir -p "$TMP"
mk_ballot "$TMP/ballot.md"
printf 'FINDING_1: narrative only\nFINDING_2: narrative only\nFINDING_3: narrative only\n' > "$TMP/claude-vote-output.txt"
printf 'voter_tool=claude\njudge_error_count=3\ntotal_findings=3\nvoter_file=%s/claude-vote-output.txt\nvoter_sha256=%s\n' "$TMP" "$(shasum -a 256 "$TMP/claude-vote-output.txt" | awk '{print $1}')" > "$TMP/claude-vote-output-parse-rate-diag.txt"
printf 'FINDING_1: YES\nFINDING_2: YES\nFINDING_3: YES\n' > "$TMP/claude-vote-output.txt"
printf 'FINDING_1: YES\nFINDING_2: NO\nFINDING_3: YES\n' > "$TMP/codex-vote-output.txt"
printf 'FINDING_1: YES\nFINDING_2: NO\nFINDING_3: YES\n' > "$TMP/cursor-vote-output.txt"
out="$TMP/out.env"
"$SCRIPT" --ballot-file "$TMP/ballot.md" \
    --voter-files "$TMP/cursor-vote-output.txt" "$TMP/codex-vote-output.txt" "$TMP/claude-vote-output.txt" \
    --review-tmpdir "$TMP" > "$out"
got=$(awk -F= '$1=="VOTER_COUNT"{print $2}' "$out"); assert_eq "stale replaced-output diag should not reduce effective voters" "$got" "3"
if grep -Fq 'voter slot(s) emitted narrative-only output' "$TMP/voting-tally.md"; then
    FAIL=1; printf '  FAIL stale replaced-output diag should not emit parse-rate banner\n'
else
    printf '  ok   stale replaced-output diag ignored by checksum binding\n'
fi

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
grep -Fq '| Codex-Security | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 1 | -1 | STATUS=OK |' "$TMP/voting-tally.md" || { FAIL=1; printf '  FAIL rejected OOS did not subtract from score\n'; }

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
got=$(awk -F= '$1=="REJECTED_COUNT"{print $2}' "$out"); assert_eq "FINDING_2 1Y/1N → rejected (split-panel subtype)" "$got" "1"
got=$(awk -F= '$1=="NEUTRAL_COUNT"{print $2}' "$out"); assert_eq "NEUTRAL_COUNT=1 (internal split-panel accounting)" "$got" "1"
got=$(awk -F= '$1=="FINDING_2_OUTCOME"{print $2}' "$TMP/review-tally.env"); assert_eq "review-tally.env records rejected outcome" "$got" "rejected"
got=$(awk -F= '$1=="FINDING_2_REJECTED_SUBTYPE"{print $2}' "$TMP/review-tally.env"); assert_eq "review-tally.env records split-panel subtype" "$got" "neutral"
got=$(awk -F= '$1=="OOS_ACCEPTED_COUNT"{print $2}' "$out"); assert_eq "FINDING_3 unanimous YES → OOS accepted" "$got" "1"
classification_file=$(awk -F= '$1=="FINDINGS_CLASSIFICATION_TSV_FILE"{print $2}' "$out")
grep -Fq $'FINDING_2\tCursor-Security\tneutral\tYES\t\t\t\ttrue\tNO\t\t\t\ttrue\t\t\t\t\t' "$classification_file" \
    || { FAIL=1; printf '  FAIL classification TSV missing neutral voting_result row\n'; }

echo "# Case: round 2 expected 3-voter panel does not emit degraded banner when all three judges arrive"
TMP="$WORKDIR/case2_round2_clean"
mkdir -p "$TMP"
mk_ballot "$TMP/ballot.md"
printf 'FINDING_1: YES\nFINDING_2: YES\nFINDING_3: YES\n' > "$TMP/cursor-vote-output.txt"
printf 'FINDING_1: YES\nFINDING_2: YES\nFINDING_3: YES\n' > "$TMP/codex-vote-output.txt"
printf 'FINDING_1: YES\nFINDING_2: NO -- nope\nFINDING_3: YES\n' > "$TMP/claude-vote-output.txt"
out="$TMP/out.env"
"$SCRIPT" --ballot-file "$TMP/ballot.md" \
    --voter-files "$TMP/cursor-vote-output.txt" "$TMP/codex-vote-output.txt" "$TMP/claude-vote-output.txt" \
    --round-num 2 \
    --review-tmpdir "$TMP" > "$out"
if grep -Fq 'Degraded code-review panel' "$TMP/voting-tally.md"; then
    FAIL=1; printf '  FAIL round-2 clean 3-voter fixture should not emit degraded panel banner\n'
else
    printf '  ok   round-2 clean 3-voter fixture emits no degraded panel banner\n'
fi

echo "# Case: 2 voters, sparse per-finding ballots leave 1 YES and 1 missing vote → rejected"
TMP="$WORKDIR/case3"
mkdir -p "$TMP"
mk_ballot "$TMP/ballot.md"
printf 'FINDING_1: YES\n' > "$TMP/cursor-vote-output.txt"
printf 'FINDING_2: NO\n' > "$TMP/codex-vote-output.txt"
out="$TMP/out.env"
"$SCRIPT" --ballot-file "$TMP/ballot.md" \
    --voter-files "$TMP/cursor-vote-output.txt" "$TMP/codex-vote-output.txt" \
    --review-tmpdir "$TMP" > "$out"
got=$(awk -F= '$1=="ACCEPTED_COUNT"{print $2}' "$out"); assert_eq "2 voters, only 1 YES → no in-scope accepted" "$got" "0"
got=$(awk -F= '$1=="REJECTED_COUNT"{print $2}' "$out"); assert_eq "2 voters, partial votes → 2 in-scope rejected" "$got" "2"

echo "# Case: 1 voter YES → accepted, including OOS"
TMP="$WORKDIR/case4"
mkdir -p "$TMP"
mk_ballot "$TMP/ballot.md"
printf 'FINDING_1: YES\nFINDING_2: YES\nFINDING_3: YES\n' > "$TMP/cursor-vote-output.txt"
out="$TMP/out.env"
"$SCRIPT" --ballot-file "$TMP/ballot.md" \
    --voter-files "$TMP/cursor-vote-output.txt" \
    --review-tmpdir "$TMP" > "$out"
got=$(awk -F= '$1=="ACCEPTED_COUNT"{print $2}' "$out"); assert_eq "1 voter YES → 2 in-scope accepted" "$got" "2"
got=$(awk -F= '$1=="OOS_ACCEPTED_COUNT"{print $2}' "$out"); assert_eq "1 voter YES → OOS accepted" "$got" "1"

echo "# Case: 1 voter NO → rejected"
TMP="$WORKDIR/case4b"
mkdir -p "$TMP"
mk_ballot "$TMP/ballot.md"
printf 'FINDING_1: NO\nFINDING_2: NO\nFINDING_3: NO\n' > "$TMP/cursor-vote-output.txt"
out="$TMP/out.env"
"$SCRIPT" --ballot-file "$TMP/ballot.md" \
    --voter-files "$TMP/cursor-vote-output.txt" \
    --review-tmpdir "$TMP" > "$out"
got=$(awk -F= '$1=="ACCEPTED_COUNT"{print $2}' "$out"); assert_eq "1 voter NO → no in-scope accepted" "$got" "0"
got=$(awk -F= '$1=="REJECTED_COUNT"{print $2}' "$out"); assert_eq "1 voter NO → 2 in-scope rejected" "$got" "2"
got=$(awk -F= '$1=="OOS_REJECTED_COUNT"{print $2}' "$out"); assert_eq "1 voter NO → OOS rejected" "$got" "1"

echo "# Case: 1 voter EXONERATE → exonerated, not accepted"
TMP="$WORKDIR/case4c"
mkdir -p "$TMP"
mk_ballot "$TMP/ballot.md"
printf 'FINDING_1: EXONERATE\nFINDING_2: EXONERATE\nFINDING_3: EXONERATE\n' > "$TMP/cursor-vote-output.txt"
out="$TMP/out.env"
"$SCRIPT" --ballot-file "$TMP/ballot.md" \
    --voter-files "$TMP/cursor-vote-output.txt" \
    --review-tmpdir "$TMP" > "$out"
got=$(awk -F= '$1=="ACCEPTED_COUNT"{print $2}' "$out"); assert_eq "1 voter EXONERATE → no in-scope accepted" "$got" "0"
got=$(awk -F= '$1=="REJECTED_COUNT"{print $2}' "$out"); assert_eq "1 voter EXONERATE → rejected_count includes exonerated patterns" "$got" "2"
got=$(awk -F= '$1=="EXONERATED_COUNT"{print $2}' "$out"); assert_eq "1 voter EXONERATE → exonerated_count=2" "$got" "2"
got=$(awk -F= '$1=="FINDING_1_OUTCOME"{print $2}' "$TMP/review-tally.env"); assert_eq "review-tally.env records rejected outcome" "$got" "rejected"
got=$(awk -F= '$1=="FINDING_1_REJECTED_SUBTYPE"{print $2}' "$TMP/review-tally.env"); assert_eq "review-tally.env records exonerated subtype" "$got" "exonerated"
grep -Fq '| FINDING_1 | 0 | 0 | 1 | 0 | exonerated |' "$TMP/voting-tally.md" || { FAIL=1; printf '  FAIL single EXONERATE not labeled exonerated\n'; }
classification_file=$(awk -F= '$1=="FINDINGS_CLASSIFICATION_TSV_FILE"{print $2}' "$out")
grep -Fq $'FINDING_1\tCodex-Structure\texonerated\tEXONERATE\t\t\t\ttrue\t\t\t\t\t\t\t\t\t\t' "$classification_file" \
    || { FAIL=1; printf '  FAIL classification TSV missing exonerated voting_result row\n'; }

echo "# Case: 0 voters → main-agent-vote-required"
TMP="$WORKDIR/case4d"
mkdir -p "$TMP"
mk_ballot "$TMP/ballot.md"
out="$TMP/out.env"
"$SCRIPT" --ballot-file "$TMP/ballot.md" --review-tmpdir "$TMP" > "$out"
got=$(awk -F= '$1=="TALLY_STATUS"{print $2}' "$out"); assert_eq "0 voters status" "$got" "main-agent-vote-required"
got=$(awk -F= '$1=="ACCEPTED_COUNT"{print $2}' "$out"); assert_eq "0 voters accepted count" "$got" "0"

echo "# Case: --both-down true → main-agent-vote-required"
TMP="$WORKDIR/case4e"
mkdir -p "$TMP"
mk_ballot "$TMP/ballot.md"
out="$TMP/out.env"
"$SCRIPT" --ballot-file "$TMP/ballot.md" \
    --review-tmpdir "$TMP" --both-down true > "$out"
got=$(awk -F= '$1=="TALLY_STATUS"{print $2}' "$out"); assert_eq "both-down status" "$got" "main-agent-vote-required"
got=$(awk -F= '$1=="ACCEPTED_COUNT"{print $2}' "$out"); assert_eq "both-down accepted count" "$got" "0"

echo "# Case: 3 voters, 1 YES 2 JUDGE_ERROR → rejected (no quorum reduction)"
TMP="$WORKDIR/case4f"
mkdir -p "$TMP"
mk_ballot "$TMP/ballot.md"
printf 'FINDING_1: YES\n' > "$TMP/cursor-vote-output.txt"
out="$TMP/out.env"
"$SCRIPT" --ballot-file "$TMP/ballot.md" \
    --voter-files "$TMP/cursor-vote-output.txt" "$TMP/codex-vote-missing.txt" "$TMP/claude-vote-missing.txt" \
    --review-tmpdir "$TMP" > "$out"
got=$(awk -F= '$1=="ACCEPTED_COUNT"{print $2}' "$out"); assert_eq "3 voters, 1 YES 2 JUDGE_ERROR → no accepted" "$got" "0"
grep -Fq '| FINDING_1 | 1 | 0 | 0 | 2 | rejected |' "$TMP/voting-tally.md" || { FAIL=1; printf '  FAIL rejected row with 2 JERR votes missing\n'; }
classification_file=$(awk -F= '$1=="FINDINGS_CLASSIFICATION_TSV_FILE"{print $2}' "$out")
[[ "$classification_file" == "$TMP/findings-classification-round-1.tsv" ]] || { FAIL=1; printf '  FAIL JUDGE_ERROR case did not emit standalone classification TSV path\n'; }
grep -Fq $'FINDING_1\tCodex-Structure\trejected\tYES\t\t\t\ttrue\tJUDGE_ERROR\t\t\t\ttrue\tJUDGE_ERROR\t\t\t\ttrue' "$classification_file" \
    || { FAIL=1; printf '  FAIL classification TSV missing JUDGE_ERROR columns for rejected row\n'; }

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

echo "# Case: scope-fit gate — finding about file NOT in diff is reclassified to OOS"
TMP="$WORKDIR/case6a"
mkdir -p "$TMP"
cat > "$TMP/ballot.md" <<'EOF'
### FINDING_1: **Important** — `code-quality` — `docs/linting.md:22`
- **Reviewer**: Cursor-Correctness
- **Concern**: Usage CI bullet still documents harnesses-1 through harnesses-10 after eleven-way sharding.
- **Suggested revision**: Update to reflect 11 shards.

### FINDING_2: **Important** — `correctness` — `scripts/dispatch-code-voters.sh:42`
- **Reviewer**: Codex-Structure
- **Concern**: Null check missing on return path.
- **Suggested revision**: Add nil guard.
EOF
printf 'scripts/dispatch-code-voters.sh\n' > "$TMP/scope-files.txt"
printf 'FINDING_1: YES\nFINDING_2: YES\n' > "$TMP/cursor-vote-output.txt"
printf 'FINDING_1: YES\nFINDING_2: YES\n' > "$TMP/codex-vote-output.txt"
printf 'FINDING_1: YES\nFINDING_2: YES\n' > "$TMP/claude-vote-output.txt"
out="$TMP/out.env"
"$SCRIPT" --ballot-file "$TMP/ballot.md" \
    --voter-files "$TMP/cursor-vote-output.txt" "$TMP/codex-vote-output.txt" "$TMP/claude-vote-output.txt" \
    --scope-files "$TMP/scope-files.txt" \
    --review-tmpdir "$TMP" > "$out"
got=$(awk -F= '$1=="OUT_OF_SCOPE_DRIFT_COUNT"{print $2}' "$out"); assert_eq "scope gate: docs/linting.md drifted → count=1" "$got" "1"
got=$(awk -F= '$1=="ACCEPTED_COUNT"{print $2}' "$out"); assert_eq "scope gate: only in-diff finding accepted (FINDING_2)" "$got" "1"
if grep -Fq 'docs/linting.md' "$TMP/accepted-findings.md" 2>/dev/null; then
    FAIL=1; printf '  FAIL docs/linting.md finding must not be in accepted-findings.md\n'
else
    printf '  ok   docs/linting.md finding absent from accepted-findings.md\n'
fi
grep -Fq 'docs/linting.md' "$TMP/oos.md" || { FAIL=1; printf '  FAIL docs/linting.md finding missing from oos.md\n'; }

echo "# Case: scope-fit gate — finding about file IN diff is NOT reclassified"
TMP="$WORKDIR/case6b"
mkdir -p "$TMP"
cat > "$TMP/ballot.md" <<'EOF'
### FINDING_1: **Important** — `correctness` — `scripts/dispatch-code-voters.sh:42`
- **Reviewer**: Codex-Structure
- **Concern**: Null check missing on return path.
- **Suggested revision**: Add nil guard.
EOF
printf 'scripts/dispatch-code-voters.sh\n' > "$TMP/scope-files.txt"
printf 'FINDING_1: YES\n' > "$TMP/cursor-vote-output.txt"
printf 'FINDING_1: YES\n' > "$TMP/codex-vote-output.txt"
printf 'FINDING_1: YES\n' > "$TMP/claude-vote-output.txt"
out="$TMP/out.env"
"$SCRIPT" --ballot-file "$TMP/ballot.md" \
    --voter-files "$TMP/cursor-vote-output.txt" "$TMP/codex-vote-output.txt" "$TMP/claude-vote-output.txt" \
    --scope-files "$TMP/scope-files.txt" \
    --review-tmpdir "$TMP" > "$out"
got=$(awk -F= '$1=="OUT_OF_SCOPE_DRIFT_COUNT"{print $2}' "$out"); assert_eq "scope gate: file in diff → no drift" "$got" "0"
got=$(awk -F= '$1=="ACCEPTED_COUNT"{print $2}' "$out"); assert_eq "scope gate: in-diff finding accepted normally" "$got" "1"

echo "# Case: scope-fit gate — plan-file mentions path → no drift"
TMP="$WORKDIR/case6d"
mkdir -p "$TMP"
cat > "$TMP/ballot.md" <<'EOF'
### FINDING_1: **Important** — `code-quality` — `docs/linting.md:22`
- **Reviewer**: Cursor-Correctness
- **Concern**: Stale shard reference.
- **Suggested revision**: Update.
EOF
printf 'scripts/dispatch-code-voters.sh\n' > "$TMP/scope-files.txt"
printf 'Touch docs/linting.md per plan section 3.\n' > "$TMP/plan.txt"
printf 'FINDING_1: YES\n' > "$TMP/cursor-vote-output.txt"
printf 'FINDING_1: YES\n' > "$TMP/codex-vote-output.txt"
printf 'FINDING_1: YES\n' > "$TMP/claude-vote-output.txt"
out="$TMP/out.env"
"$SCRIPT" --ballot-file "$TMP/ballot.md" \
    --voter-files "$TMP/cursor-vote-output.txt" "$TMP/codex-vote-output.txt" "$TMP/claude-vote-output.txt" \
    --scope-files "$TMP/scope-files.txt" \
    --plan-file "$TMP/plan.txt" \
    --review-tmpdir "$TMP" > "$out"
got=$(awk -F= '$1=="OUT_OF_SCOPE_DRIFT_COUNT"{print $2}' "$out"); assert_eq "scope gate: plan names docs/linting.md → drift=0" "$got" "0"
got=$(awk -F= '$1=="ACCEPTED_COUNT"{print $2}' "$out"); assert_eq "scope gate: plan exemption keeps finding in accepted" "$got" "1"
grep -Fq 'docs/linting.md' "$TMP/accepted-findings.md" || { FAIL=1; printf '  FAIL plan-exempt path should stay in accepted-findings.md\n'; }

echo "# Case: scope-fit gate — no --scope-files → gate is no-op"
TMP="$WORKDIR/case6c"
mkdir -p "$TMP"
cat > "$TMP/ballot.md" <<'EOF'
### FINDING_1: **Important** — `code-quality` — `docs/linting.md:22`
- **Reviewer**: Cursor-Correctness
- **Concern**: Stale shard reference.
- **Suggested revision**: Update.
EOF
printf 'FINDING_1: YES\n' > "$TMP/cursor-vote-output.txt"
printf 'FINDING_1: YES\n' > "$TMP/codex-vote-output.txt"
printf 'FINDING_1: YES\n' > "$TMP/claude-vote-output.txt"
out="$TMP/out.env"
"$SCRIPT" --ballot-file "$TMP/ballot.md" \
    --voter-files "$TMP/cursor-vote-output.txt" "$TMP/codex-vote-output.txt" "$TMP/claude-vote-output.txt" \
    --review-tmpdir "$TMP" > "$out"
got=$(awk -F= '$1=="OUT_OF_SCOPE_DRIFT_COUNT"{print $2}' "$out"); assert_eq "no scope-files → gate no-op, drift=0" "$got" "0"
got=$(awk -F= '$1=="ACCEPTED_COUNT"{print $2}' "$out"); assert_eq "no scope-files → finding accepted normally" "$got" "1"

echo "# Case: manifest-file writes per-archetype yield TSV with fallback basename normalization"
TMP="$WORKDIR/case7"
mkdir -p "$TMP"
cat > "$TMP/ballot.md" <<'EOF'
### FINDING_1: Static structure finding
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: Static concern.
- **Suggested revision**: Static revision.

### FINDING_2: Dynamic fallback finding
- **Reviewer**: dyn-foo-output-phase2.txt
- **Concern**: Dynamic concern.
- **Suggested revision**: Dynamic revision.

### FINDING_3: Generalist finding
- **Reviewer**: codex-generalist-output.txt
- **Concern**: Generalist concern.
- **Suggested revision**: Generalist revision.
EOF
cat > "$TMP/panel-manifest.ndjson" <<EOF
{"slot":"structure","tool":"cursor","output":"$TMP/cursor-specialist-structure-output.txt","agent":"agents/reviewer-structure.md"}
{"slot":"dyn-foo","tool":"cursor","output":"$TMP/dyn-foo-output.txt","prompt_file":"$TMP/dyn-foo-prompt.md","weight":6,"focus_area":"architecture"}
{"slot":"generic","tool":"codex","output":"$TMP/codex-generalist-output.txt","agent":"agents/code-reviewer.md"}
EOF
printf 'FINDING_1: YES\nFINDING_2: NO\nFINDING_3: YES\n' > "$TMP/cursor-vote-output.txt"
printf 'FINDING_1: YES\nFINDING_2: NO\nFINDING_3: YES\n' > "$TMP/codex-vote-output.txt"
printf 'FINDING_1: NO\nFINDING_2: YES\nFINDING_3: YES\n' > "$TMP/claude-vote-output.txt"
out="$TMP/out.env"
"$SCRIPT" --ballot-file "$TMP/ballot.md" \
    --voter-files "$TMP/cursor-vote-output.txt" "$TMP/codex-vote-output.txt" "$TMP/claude-vote-output.txt" \
    --manifest-file "$TMP/panel-manifest.ndjson" \
    --review-tmpdir "$TMP" > "$out"
yield_file=$(awk -F= '$1=="YIELD_TSV_FILE"{print $2}' "$out")
[[ -s "$yield_file" ]] || { FAIL=1; printf '  FAIL yield TSV not emitted\n'; }
grep -Fq $'structure\tcode-quality\t1\t1\t1\t0\t1.000000' "$yield_file" || { FAIL=1; printf '  FAIL static structure yield row missing\n'; }
grep -Fq $'dyn-foo\tarchitecture\t6\t1\t0\t1\t0.000000' "$yield_file" || { FAIL=1; printf '  FAIL dynamic fallback-normalized yield row missing\n'; }
grep -Fq $'generic\tcode-quality\t1\t1\t1\t0\t1.000000' "$yield_file" || { FAIL=1; printf '  FAIL generalist yield row missing\n'; }
if grep -Fq '| dyn-foo | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |' "$TMP/voting-tally.md"; then
    FAIL=1; printf '  FAIL dynamic fallback-normalized reviewer should not also emit dead-slot STATUS=OK row\n'
else
    printf '  ok   dynamic fallback-normalized reviewer does not emit extra dead-slot row\n'
fi

echo "# Case: manifest-file yield TSV counts all in-scope outcomes and ignores OOS rows"
TMP="$WORKDIR/case7a"
mkdir -p "$TMP"
cat > "$TMP/ballot.md" <<'EOF'
### FINDING_1: Accepted in-scope finding
- **Reviewer**: dyn-yield-output.txt
- **Concern**: Accepted concern.
- **Suggested revision**: Accepted revision.

### FINDING_2: Neutral in-scope finding
- **Reviewer**: dyn-yield-output.txt
- **Concern**: Neutral concern.
- **Suggested revision**: Neutral revision.

### FINDING_3: [OUT_OF_SCOPE] OOS accepted finding
- **Reviewer**: dyn-yield-output.txt
- **Concern**: OOS concern.
- **Suggested revision**: OOS revision.
EOF
cat > "$TMP/panel-manifest.ndjson" <<EOF
{"slot":"dyn-yield","tool":"cursor","output":"$TMP/dyn-yield-output.txt","prompt_file":"$TMP/dyn-yield-prompt.md","weight":4,"focus_area":"correctness"}
EOF
printf 'FINDING_1: YES\nFINDING_2: YES\nFINDING_3: YES\n' > "$TMP/cursor-vote-output.txt"
printf 'FINDING_1: YES\nFINDING_2: NO\nFINDING_3: YES\n' > "$TMP/codex-vote-output.txt"
out="$TMP/out.env"
"$SCRIPT" --ballot-file "$TMP/ballot.md" \
    --voter-files "$TMP/cursor-vote-output.txt" "$TMP/codex-vote-output.txt" \
    --manifest-file "$TMP/panel-manifest.ndjson" \
    --review-tmpdir "$TMP" > "$out"
yield_file=$(awk -F= '$1=="YIELD_TSV_FILE"{print $2}' "$out")
grep -Fq $'dyn-yield\tcorrectness\t4\t2\t1\t0\t0.500000' "$yield_file" || { FAIL=1; printf '  FAIL yield TSV should count all in-scope findings in the denominator\n'; }

echo "# Case: manifest-file warns when reviewer totals lack a manifest entry"
TMP="$WORKDIR/case7b"
mkdir -p "$TMP"
cat > "$TMP/ballot.md" <<'EOF'
### FINDING_1: Orphan reviewer finding
- **Reviewer**: cursor-specialist-unknown-output.txt
- **Concern**: Orphan concern.
- **Suggested revision**: Orphan revision.
EOF
cat > "$TMP/panel-manifest.ndjson" <<EOF
{"slot":"structure","tool":"cursor","output":"$TMP/cursor-specialist-structure-output.txt","agent":"agents/reviewer-structure.md"}
EOF
printf 'FINDING_1: YES\n' > "$TMP/cursor-vote-output.txt"
printf 'FINDING_1: YES\n' > "$TMP/codex-vote-output.txt"
printf 'FINDING_1: NO\n' > "$TMP/claude-vote-output.txt"
out="$TMP/out.env"
"$SCRIPT" --ballot-file "$TMP/ballot.md" \
    --voter-files "$TMP/cursor-vote-output.txt" "$TMP/codex-vote-output.txt" "$TMP/claude-vote-output.txt" \
    --manifest-file "$TMP/panel-manifest.ndjson" \
    --review-tmpdir "$TMP" > "$out"
grep -Fq 'WARN=yield TSV missing manifest entry for reviewer basename: cursor-specialist-unknown-output.txt' "$out" || { FAIL=1; printf '  FAIL orphan reviewer warning missing\n'; }

echo "# Case: panel-manifest with 8 slots, only 5 produce findings — scoreboard shows 8 rows"
TMP="$WORKDIR/case_dead_slots"
mkdir -p "$TMP"
# 5-slot ballot (structure + correctness + testing + security + edge-cases)
cat > "$TMP/ballot.md" <<'EOF'
### FINDING_1: Structure concern
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: Structure issue.
- **Suggested revision**: Fix it.

### FINDING_2: Correctness concern
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: Correctness issue.
- **Suggested revision**: Fix it.

### FINDING_3: Testing concern
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: Testing issue.
- **Suggested revision**: Fix it.

### FINDING_4: Security concern
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: Security issue.
- **Suggested revision**: Fix it.

### FINDING_5: Edge cases concern
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: Edge case issue.
- **Suggested revision**: Fix it.
EOF
# 8-slot panel manifest (structure+correctness+testing+security+edge-cases+plan-fidelity+codex-generalist+dyn-zero)
cat > "$TMP/panel-manifest.ndjson" <<EOF
{"slot":"structure","tool":"cursor","output":"$TMP/cursor-specialist-structure-output.txt","agent":"agents/reviewer-structure.md"}
{"slot":"correctness","tool":"cursor","output":"$TMP/cursor-specialist-correctness-output.txt","agent":"agents/reviewer-correctness.md"}
{"slot":"testing","tool":"cursor","output":"$TMP/cursor-specialist-testing-output.txt","agent":"agents/reviewer-testing.md"}
{"slot":"security","tool":"cursor","output":"$TMP/cursor-specialist-security-output.txt","agent":"agents/reviewer-security.md"}
{"slot":"edge-cases","tool":"cursor","output":"$TMP/cursor-specialist-edge-cases-output.txt","agent":"agents/reviewer-edge-cases.md"}
{"slot":"plan-fidelity","tool":"cursor","output":"$TMP/cursor-specialist-plan-fidelity-output.txt","agent":"agents/reviewer-plan-fidelity.md"}
{"slot":"generic","tool":"codex","output":"$TMP/codex-generalist-output.txt","agent":"agents/codex-generalist.md"}
{"slot":"dyn-zero","tool":"cursor","output":"$TMP/dyn-zero-output.txt","prompt_file":"$TMP/dyn-zero-prompt.md","weight":3,"focus_area":"correctness"}
EOF
# Collector results: plan-fidelity and codex-generalist are NOT_SUBSTANTIVE (dead slots),
# dyn-zero is OK but produced no findings.
cat > "$TMP/collector-results.env" <<EOF
REVIEWER_FILE=$TMP/cursor-specialist-structure-output.txt
TOOL=cursor
STATUS=OK
EXIT_CODE=0

REVIEWER_FILE=$TMP/cursor-specialist-correctness-output.txt
TOOL=cursor
STATUS=OK
EXIT_CODE=0

REVIEWER_FILE=$TMP/cursor-specialist-testing-output.txt
TOOL=cursor
STATUS=OK
EXIT_CODE=0

REVIEWER_FILE=$TMP/cursor-specialist-security-output.txt
TOOL=cursor
STATUS=OK
EXIT_CODE=0

REVIEWER_FILE=$TMP/cursor-specialist-edge-cases-output.txt
TOOL=cursor
STATUS=OK
EXIT_CODE=0

REVIEWER_FILE=$TMP/cursor-specialist-plan-fidelity-output.txt
TOOL=cursor
STATUS=NOT_SUBSTANTIVE
EXIT_CODE=0

REVIEWER_FILE=$TMP/codex-generalist-output.txt
TOOL=codex
STATUS=NOT_SUBSTANTIVE
EXIT_CODE=0

REVIEWER_FILE=$TMP/dyn-zero-output.txt
TOOL=cursor
STATUS=OK
EXIT_CODE=0
EOF
printf 'FINDING_1: YES\nFINDING_2: YES\nFINDING_3: NO\nFINDING_4: YES\nFINDING_5: YES\n' > "$TMP/cursor-vote-output.txt"
printf 'FINDING_1: YES\nFINDING_2: NO\nFINDING_3: YES\nFINDING_4: YES\nFINDING_5: NO\n'  > "$TMP/codex-vote-output.txt"
printf 'FINDING_1: YES\nFINDING_2: YES\nFINDING_3: YES\nFINDING_4: YES\nFINDING_5: YES\n' > "$TMP/claude-vote-output.txt"
out="$TMP/out.env"
"$SCRIPT" --ballot-file "$TMP/ballot.md" \
    --voter-files "$TMP/cursor-vote-output.txt" "$TMP/codex-vote-output.txt" "$TMP/claude-vote-output.txt" \
    --manifest-file "$TMP/panel-manifest.ndjson" \
    --collector-results-file "$TMP/collector-results.env" \
    --not-substantive-count 2 \
    --review-tmpdir "$TMP" > "$out"
tally_content=$(cat "$TMP/voting-tally.md" 2>/dev/null || true)
# Scoreboard must include rows for live slots using the same short label as dead slots.
for _slot in cursor-specialist-structure cursor-specialist-correctness \
             cursor-specialist-testing cursor-specialist-security \
             cursor-specialist-edge-cases; do
    if printf '%s\n' "$tally_content" | grep -Fq "| $_slot " \
       && printf '%s\n' "$tally_content" | grep -F "| $_slot " | grep -Fq '| STATUS=OK |'; then
        printf '  ok   dead_slots: live slot %s row present\n' "$_slot"
    else
        FAIL=1; printf '  FAIL dead_slots: live slot %s row missing short label or STATUS=OK\n' "$_slot"
    fi
done
# Dead slots use short label (no -output.txt suffix)
for _slot in cursor-specialist-plan-fidelity codex-generalist dyn-zero; do
    if printf '%s\n' "$tally_content" | grep -Fq "| $_slot "; then
        printf '  ok   dead_slots: dead slot %s row present in scoreboard\n' "$_slot"
    else
        FAIL=1; printf '  FAIL dead_slots: dead slot %s row missing from scoreboard\n' "$_slot"
    fi
done
# Dead slots should carry STATUS=NOT_SUBSTANTIVE annotation
if printf '%s\n' "$tally_content" | grep -q 'STATUS=NOT_SUBSTANTIVE'; then
    printf '  ok   dead_slots: NOT_SUBSTANTIVE annotation present\n'
else
    FAIL=1; printf '  FAIL dead_slots: NOT_SUBSTANTIVE annotation missing\n'
fi
# OK dynamic slots with zero findings should appear in the scoreboard.
if printf '%s\n' "$tally_content" | grep -Fq '| dyn-zero | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |'; then
    printf '  ok   dead_slots: dynamic zero-finding slot shows STATUS=OK\n'
else
    FAIL=1; printf '  FAIL dead_slots: dynamic zero-finding slot missing STATUS=OK row\n'
fi
# Manifest rows missing collector entries should fall back to STATUS=OK.
TMP="$WORKDIR/case8"
mkdir -p "$TMP"
cat > "$TMP/ballot.md" <<'EOF'
### FINDING_1: Structure concern
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: Structure issue.
- **Suggested revision**: Fix it.
EOF
cat > "$TMP/panel-manifest.ndjson" <<EOF
{"slot":"structure","tool":"cursor","output":"$TMP/cursor-specialist-structure-output.txt","agent":"agents/reviewer-structure.md"}
{"slot":"generic","tool":"codex","output":"$TMP/codex-generalist-output.txt","agent":"agents/codex-generalist.md"}
EOF
cat > "$TMP/collector-results.env" <<EOF
REVIEWER_FILE=$TMP/cursor-specialist-structure-output.txt
TOOL=cursor
STATUS=OK
EXIT_CODE=0
EOF
printf 'FINDING_1: YES\n' > "$TMP/cursor-vote-output.txt"
out="$TMP/out.env"
"$SCRIPT" --ballot-file "$TMP/ballot.md" \
    --voter-files "$TMP/cursor-vote-output.txt" \
    --manifest-file "$TMP/panel-manifest.ndjson" \
    --collector-results-file "$TMP/collector-results.env" \
    --review-tmpdir "$TMP" > "$out"
if grep -Fq '| codex-generalist | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |' "$TMP/voting-tally.md"; then
    printf '  ok   dead_slots: missing collector row falls back to OK\n'
else
    FAIL=1; printf '  FAIL dead_slots: missing collector row did not fall back to OK\n'
fi
# Degraded banner must appear (NOT_SUBSTANTIVE_COUNT=2 passed via --not-substantive-count)
if printf '%s\n' "$tally_content" | grep -q '2 reviewer slot(s) emitted narrative-only output'; then
    printf '  ok   dead_slots: degraded panel banner present\n'
else
    FAIL=1; printf '  FAIL dead_slots: degraded panel banner missing\n'
fi

if [[ "$FAIL" -eq 0 ]]; then
    printf 'PASS: test-tally-code-votes.sh\n'
    exit 0
else
    printf 'FAIL: test-tally-code-votes.sh\n'
    exit 1
fi
