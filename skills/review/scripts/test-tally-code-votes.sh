#!/usr/bin/env bash
# test-tally-code-votes.sh — regression harness for tally-code-votes.sh.

set -euo pipefail

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
printf 'FINDING_1: YES\nFINDING_2: YES\nFINDING_3: YES\n' > "$TMP/cursor-vote-output.txt"
printf 'FINDING_1: YES\nFINDING_2: NO -- low priority\nFINDING_3: YES\n' > "$TMP/codex-vote-output.txt"
printf 'FINDING_1: NO -- already handled elsewhere\nFINDING_2: NO -- not actionable\nFINDING_3: NO -- not worth filing\n' > "$TMP/claude-vote-output.txt"
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
got=$(awk -F= '$1=="REJECTED_COUNT"{print $2}' "$out"); assert_eq "FINDING_2 1Y/1N → neutral (tied), not counted in rejected" "$got" "0"
got=$(awk -F= '$1=="NEUTRAL_COUNT"{print $2}' "$out"); assert_eq "FINDING_2 1Y/1N → neutral_count=1" "$got" "1"
got=$(awk -F= '$1=="FINDING_2_OUTCOME"{print $2}' "$TMP/review-tally.env"); assert_eq "review-tally.env records neutral outcome explicitly" "$got" "neutral"
got=$(awk -F= '$1=="OOS_ACCEPTED_COUNT"{print $2}' "$out"); assert_eq "FINDING_3 unanimous YES → OOS accepted" "$got" "1"

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
got=$(awk -F= '$1=="REJECTED_COUNT"{print $2}' "$out"); assert_eq "1 voter EXONERATE → rejected_count=0 (exonerated, not rejected)" "$got" "0"
got=$(awk -F= '$1=="EXONERATED_COUNT"{print $2}' "$out"); assert_eq "1 voter EXONERATE → exonerated_count=2" "$got" "2"
got=$(awk -F= '$1=="FINDING_1_OUTCOME"{print $2}' "$TMP/review-tally.env"); assert_eq "review-tally.env records exonerated outcome explicitly" "$got" "exonerated"
grep -Fq '| FINDING_1 | 0 | 0 | 1 | 0 | exonerated |' "$TMP/voting-tally.md" || { FAIL=1; printf '  FAIL single EXONERATE not labeled exonerated\n'; }

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

echo "# Case: 3 voters, 1 YES 2 NEUTRAL → rejected (no quorum reduction)"
TMP="$WORKDIR/case4f"
mkdir -p "$TMP"
mk_ballot "$TMP/ballot.md"
printf 'FINDING_1: YES\n' > "$TMP/cursor-vote-output.txt"
: > "$TMP/codex-vote-output.txt"
: > "$TMP/claude-vote-output.txt"
out="$TMP/out.env"
"$SCRIPT" --ballot-file "$TMP/ballot.md" \
    --voter-files "$TMP/cursor-vote-output.txt" "$TMP/codex-vote-output.txt" "$TMP/claude-vote-output.txt" \
    --review-tmpdir "$TMP" > "$out"
got=$(awk -F= '$1=="ACCEPTED_COUNT"{print $2}' "$out"); assert_eq "3 voters, 1 YES 2 NEUTRAL → no accepted" "$got" "0"
grep -Fq '| FINDING_1 | 1 | 0 | 0 | 2 | rejected |' "$TMP/voting-tally.md" || { FAIL=1; printf '  FAIL neutral quorum row missing\n'; }

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

echo "# Case: manifest-file yield TSV ignores OOS and neutral/exonerated rows"
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
grep -Fq $'dyn-yield\tcorrectness\t4\t1\t1\t0\t1.000000' "$yield_file" || { FAIL=1; printf '  FAIL yield TSV should count only accepted/rejected in-scope findings\n'; }

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

if [[ "$FAIL" -eq 0 ]]; then
    printf 'PASS: test-tally-code-votes.sh\n'
    exit 0
else
    printf 'FAIL: test-tally-code-votes.sh\n'
    exit 1
fi
