#!/usr/bin/env bash
# Offline harness for persist-retally-step3-env.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd -P)"
SUBJECT="$ROOT/skills/design/scripts/persist-retally-step3-env.sh"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; }
export CLAUDE_PLUGIN_ROOT="$ROOT"

TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-persist-retally-step3-env.XXXXXX")
trap 'rm -rf "$TMP"' EXIT
DESIGN_CANON="$(cd "$TMP" && pwd -P)"
printf 'anchor body\n' >"$TMP/plan-review-scope-anchor.txt"
printf 'stale anchor\n' >"$TMP/stale-scope-anchor.txt"

cat >"$TMP/.step3-plan-review-result.env" <<EOF
LOOP_STATUS=main-agent-vote-required
TALLY_PLAN_REVIEW_STATUS=main-agent-vote-required
SCOPE_ANCHOR_FILE=/tmp/stale-scope-anchor.txt
ACCEPTED_COUNT=3
IMPORTANT_ACCEPTED_COUNT=2
NIT_ACCEPTED_COUNT=0
NON_NIT_ACCEPTED_COUNT=3
EOF
cp "$TMP/.step3-plan-review-result.env" "$TMP/.step3-review-result.env"
cat >"$TMP/accepted-plan-findings.md" <<'EOF'
### FINDING_99: Partial failed re-tally accepted
- **Concern**: should be cleared
EOF

printf 'TALLY_PLAN_REVIEW_STATUS=tally-error\nVOTING_TALLY_FILE=%s/voting-tally.md\n' "$TMP" >"$TMP/retally-stdout.txt"

"$SUBJECT" \
    --design-tmpdir "$TMP" \
    --retally-stdout-file "$TMP/retally-stdout.txt" \
    --retally-input-anchor "$TMP/stale-scope-anchor.txt" \
    --tally-plan-review-status tally-error \
    --loop-status complete

grep -q '^SCOPE_ANCHOR_FILE=' "$TMP/.step3-plan-review-result.env" && fail 'tally-error must omit scope anchor from plan-review result env'
grep -q '^SCOPE_ANCHOR_FILE=' "$TMP/.step3-review-result.env" && fail 'tally-error must omit scope anchor from review result env'
grep -Fqx 'TALLY_PLAN_REVIEW_STATUS=tally-error' "$TMP/.step3-plan-review-result.env" || fail 'plan-review env must carry tally-error'
grep -Fqx 'LOOP_STATUS=complete' "$TMP/.step3-review-result.env" || fail 'review env must carry loop complete'
[[ ! -s "$TMP/accepted-plan-findings.md" ]] || fail 'tally-error should clear partial accepted-plan-findings.md'
grep -Fqx 'ACCEPTED_COUNT=0' "$TMP/.step3-plan-review-result.env" || fail 'tally-error should zero ACCEPTED_COUNT in plan-review env'
grep -Fqx 'IMPORTANT_ACCEPTED_COUNT=0' "$TMP/.step3-review-result.env" || fail 'tally-error should zero IMPORTANT_ACCEPTED_COUNT in review env'

printf 'TALLY_PLAN_REVIEW_STATUS=ok\nSCOPE_ANCHOR_FILE=%s/plan-review-scope-anchor.txt\n' "$TMP" >"$TMP/retally-ok.txt"
cat >"$TMP/.step3-plan-review-result.env" <<EOF
LOOP_STATUS=main-agent-vote-required
TALLY_PLAN_REVIEW_STATUS=main-agent-vote-required
ACCEPTED_COUNT=0
EOF
cp "$TMP/.step3-plan-review-result.env" "$TMP/.step3-review-result.env"

"$SUBJECT" \
    --design-tmpdir "$TMP" \
    --retally-stdout-file "$TMP/retally-ok.txt" \
    --retally-input-anchor "$TMP/stale-scope-anchor.txt" \
    --tally-plan-review-status ok \
    --loop-status complete

grep -Fqx "SCOPE_ANCHOR_FILE=$DESIGN_CANON/plan-review-scope-anchor.txt" "$TMP/.step3-plan-review-result.env" \
    || fail 'ok re-tally should persist parsed scope anchor'
grep -Fqx "SCOPE_ANCHOR_FILE=$DESIGN_CANON/plan-review-scope-anchor.txt" "$TMP/.step3-review-result.env" \
    || fail 'ok re-tally should persist parsed scope anchor to review env'

cat >"$TMP/accepted-plan-findings-all.md" <<'EOF'
### FINDING_1: Prior accepted
- **Concern**: prior
EOF
cat >"$TMP/accepted-plan-findings.md" <<'EOF'
### FINDING_2: MainAgent accepted
- **Concern**: current
EOF

"$SUBJECT" \
    --design-tmpdir "$TMP" \
    --retally-stdout-file "$TMP/retally-ok.txt" \
    --retally-input-anchor "$TMP/stale-scope-anchor.txt" \
    --tally-plan-review-status ok \
    --loop-status complete

grep -Fq '### FINDING_1: Prior accepted' "$TMP/accepted-plan-findings-all.md" \
    || fail 'ok re-tally should preserve prior cumulative accepted findings'
grep -Fq '### FINDING_2: MainAgent accepted' "$TMP/accepted-plan-findings-all.md" \
    || fail 'ok re-tally should append current MainAgent accepted findings'

cat >"$TMP/.oos-accepted-design.prev.md" <<'EOF'
### OOS_1: Prior accepted OOS
- **Description**: Preserve the prior round OOS item.
- **Focus area**: correctness
EOF
cat >"$TMP/oos-accepted-design.md" <<'EOF'
### OOS_1: MainAgent accepted OOS
- **Description**: Preserve the current MainAgent OOS item.
- **Focus area**: correctness
EOF

"$SUBJECT" \
    --design-tmpdir "$TMP" \
    --retally-stdout-file "$TMP/retally-ok.txt" \
    --retally-input-anchor "$TMP/stale-scope-anchor.txt" \
    --tally-plan-review-status ok \
    --loop-status complete
[[ "$(grep -c '^### FINDING_2:' "$TMP/accepted-plan-findings-all.md")" -eq 1 ]] \
    || fail 'ok re-tally cumulative merge should be idempotent'
grep -Fq 'Prior accepted OOS' "$TMP/oos-accepted-design.md" \
    || fail 'ok re-tally should preserve prior cumulative accepted OOS'
grep -Fq 'MainAgent accepted OOS' "$TMP/oos-accepted-design.md" \
    || fail 'ok re-tally should append current MainAgent accepted OOS'
[[ "$(grep -c 'Preserve the current MainAgent OOS item' "$TMP/oos-accepted-design.md")" -eq 1 ]] \
    || fail 'ok re-tally OOS cumulative merge should be idempotent'

cat >"$TMP/accepted-plan-findings-all.md" <<'EOF'
### FINDING_1: Prior accepted
- **Concern**: prior
EOF
cat >"$TMP/accepted-plan-findings.md" <<'EOF'
### FINDING_3: Tally-error accepted should not merge
- **Concern**: current
EOF

"$SUBJECT" \
    --design-tmpdir "$TMP" \
    --retally-stdout-file "$TMP/retally-stdout.txt" \
    --retally-input-anchor "$TMP/stale-scope-anchor.txt" \
    --tally-plan-review-status tally-error \
    --loop-status complete

grep -Fq '### FINDING_3:' "$TMP/accepted-plan-findings-all.md" \
    && fail 'tally-error re-tally must not merge current accepted findings'

cat >"$TMP/.step3-review-result.env" <<'EOF'
LOOP_STATUS=main-agent-vote-required
STEP3_REVIEW_LOOP_STATUS=main-agent-vote-required
POSTPLAN_RC=12
DEDUP_RC=2
FINAL_ROUND_NUM=2
PLAN_REVIEW_CONTINUE_REASON=stale
TALLY_PLAN_REVIEW_STATUS=main-agent-vote-required
EOF
cp "$TMP/.step3-review-result.env" "$TMP/.step3-plan-review-result.env"
printf 'TALLY_PLAN_REVIEW_STATUS=ok\nSCOPE_ANCHOR_FILE=%s/plan-review-scope-anchor.txt\n' "$DESIGN_CANON" >"$TMP/retally-ok.txt"

"$SUBJECT" \
    --design-tmpdir "$TMP" \
    --retally-stdout-file "$TMP/retally-ok.txt" \
    --retally-input-anchor "$TMP/stale-scope-anchor.txt" \
    --tally-plan-review-status ok \
    --loop-status complete

grep -q '^STEP3_REVIEW_LOOP_STATUS=' "$TMP/.step3-review-result.env" && fail 'ok re-tally must drop stale STEP3_REVIEW_LOOP_STATUS'
grep -q '^POSTPLAN_RC=' "$TMP/.step3-review-result.env" && fail 'ok re-tally must drop stale POSTPLAN_RC'
grep -q '^DEDUP_RC=' "$TMP/.step3-review-result.env" && fail 'ok re-tally must drop stale DEDUP_RC'
grep -q '^FINAL_ROUND_NUM=' "$TMP/.step3-review-result.env" && fail 'ok re-tally must drop stale FINAL_ROUND_NUM'
grep -Fqx 'LOOP_STATUS=complete' "$TMP/.step3-review-result.env" || fail 'ok re-tally must refresh LOOP_STATUS'

RT="$TMP/retally-round-refresh"
mkdir -p "$RT/plan-review/round-3"
cat >"$RT/.step3-plan-review-result.env" <<'EOF'
LOOP_STATUS=main-agent-vote-required
TALLY_PLAN_REVIEW_STATUS=main-agent-vote-required
ROUNDS_COMPLETED=3
ACCEPTED_COUNT=0
EOF
cp "$RT/.step3-plan-review-result.env" "$RT/.step3-review-result.env"
printf '9\n' >"$RT/review-round-count.txt"
cat >"$RT/voting-tally.md" <<'EOF'
## Findings
| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 3 | 0 | 0 | accepted |
| OOS_1 | 0 | 3 | 0 | rejected |
EOF
cat >"$RT/findings-classification.tsv" <<'EOF'
finding_id	finding_reviewers	voting_result
FINDING_99	Stale	accepted
EOF
cat >"$RT/plan-review/round-3/findings-classification.tsv" <<'EOF'
finding_id	finding_reviewers	voting_result
FINDING_3	RoundLocal	rejected
EOF
cat >"$RT/plan-review/round-3/plan-review-slots.ndjson" <<EOF
{"slot":"cursor-plan-arch","tool":"cursor","output":"$RT/cursor-plan-arch-output.txt"}
EOF
printf 'TALLY_PLAN_REVIEW_STATUS=ok\n' >"$RT/retally-ok.txt"
printf 'anchor\n' >"$RT/anchor.txt"
printf 'timing\trow\n' >"$RT/timing-ledger.tsv"

"$SUBJECT" \
    --design-tmpdir "$RT" \
    --retally-stdout-file "$RT/retally-ok.txt" \
    --retally-input-anchor "$RT/anchor.txt" \
    --tally-plan-review-status ok \
    --loop-status complete

cmp -s "$RT/voting-tally.md" "$RT/plan-review/round-3/voting-tally.md" \
    || fail 'ok re-tally should refresh resolved round voting-tally.md'
jq -e '.tally.ACCEPTED_COUNT == "1" and .tally.OOS_REJECTED_COUNT == "1" and .summary.panel.total_slot_count == 1' \
    "$RT/plan-review/round-3/round-meta.json" >/dev/null || fail 'ok re-tally should write non-zero round-meta for resolved round'
grep -Fq 'RoundLocal' "$RT/plan-review/round-3/findings-classification.tsv" \
    || fail 'ok re-tally must preserve existing round-local findings-classification.tsv'
grep -Fq 'Stale' "$RT/plan-review/round-3/findings-classification.tsv" \
    && fail 'ok re-tally must not copy stale session-root findings-classification.tsv'
[[ "$(cat "$RT/timing-ledger.tsv")" == $'timing\trow' ]] \
    || fail 'persist-retally-step3-env must not append timing rows'
[[ ! -e "$RT/plan-review/round-9/round-meta.json" ]] \
    || fail 'retally refresh must ignore misleading review-round-count.txt'

RTP="$TMP/retally-round-num-preferred"
mkdir -p "$RTP/plan-review/round-2" "$RTP/plan-review/round-4"
cat >"$RTP/.step3-plan-review-result.env" <<'EOF'
LOOP_STATUS=main-agent-vote-required
TALLY_PLAN_REVIEW_STATUS=main-agent-vote-required
ROUND_NUM=4
ROUNDS_COMPLETED=2
EOF
cp "$RTP/.step3-plan-review-result.env" "$RTP/.step3-review-result.env"
cat >"$RTP/voting-tally.md" <<'EOF'
## Findings
| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_4 | 3 | 0 | 0 | accepted |
EOF
printf '{"slot":"codex-plan-arch","tool":"codex","output":"%s/codex-primary-plan-arch-output.txt"}\n' "$RTP" >"$RTP/plan-review/round-4/plan-review-slots.ndjson"
printf 'anchor\n' >"$RTP/anchor.txt"
printf 'TALLY_PLAN_REVIEW_STATUS=ok\n' >"$RTP/retally-ok.txt"
"$SUBJECT" \
    --design-tmpdir "$RTP" \
    --retally-stdout-file "$RTP/retally-ok.txt" \
    --retally-input-anchor "$RTP/anchor.txt" \
    --tally-plan-review-status ok \
    --loop-status complete
[[ -s "$RTP/plan-review/round-4/round-meta.json" ]] || fail 'ROUND_NUM should select round 4 for metadata refresh'
[[ ! -e "$RTP/plan-review/round-2/round-meta.json" ]] || fail 'ROUND_NUM should take precedence over ROUNDS_COMPLETED'

RTE="$TMP/retally-tally-error-clears-meta"
mkdir -p "$RTE/plan-review/round-5"
cat >"$RTE/.step3-plan-review-result.env" <<'EOF'
LOOP_STATUS=main-agent-vote-required
TALLY_PLAN_REVIEW_STATUS=main-agent-vote-required
ROUND_NUM=5
ACCEPTED_COUNT=7
EOF
cp "$RTE/.step3-plan-review-result.env" "$RTE/.step3-review-result.env"
printf '{"tally":{"ACCEPTED_COUNT":"7"}}\n' >"$RTE/plan-review/round-5/round-meta.json"
printf '{"slot":"stale","tool":"cursor","output":"stale-output.txt"}\n' >"$RTE/plan-review/round-5/panel-manifest.ndjson"
printf 'old tally\n' >"$RTE/plan-review/round-5/voting-tally.md"
printf 'new tally must not copy\n' >"$RTE/voting-tally.md"
cat >"$RTE/accepted-plan-findings.md" <<'EOF'
### FINDING_5: partial
EOF
printf 'anchor\n' >"$RTE/anchor.txt"
printf 'TALLY_PLAN_REVIEW_STATUS=tally-error\n' >"$RTE/retally-error.txt"
"$SUBJECT" \
    --design-tmpdir "$RTE" \
    --retally-stdout-file "$RTE/retally-error.txt" \
    --retally-input-anchor "$RTE/anchor.txt" \
    --tally-plan-review-status tally-error \
    --loop-status complete
[[ ! -e "$RTE/plan-review/round-5/round-meta.json" ]] || fail 'tally-error should remove stale round-meta.json'
[[ ! -e "$RTE/plan-review/round-5/panel-manifest.ndjson" ]] || fail 'tally-error should remove stale panel-manifest.ndjson'
grep -Fqx 'old tally' "$RTE/plan-review/round-5/voting-tally.md" \
    || fail 'tally-error must not refresh voting-tally.md'
[[ ! -s "$RTE/accepted-plan-findings.md" ]] || fail 'tally-error should clear partial accepted-plan-findings.md in refresh coverage'

pass 'persist-retally-step3-env harness'
