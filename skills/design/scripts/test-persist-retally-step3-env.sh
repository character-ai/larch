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

"$SUBJECT" \
    --design-tmpdir "$TMP" \
    --retally-stdout-file "$TMP/retally-ok.txt" \
    --retally-input-anchor "$TMP/stale-scope-anchor.txt" \
    --tally-plan-review-status ok \
    --loop-status complete
[[ "$(grep -c '^### FINDING_2:' "$TMP/accepted-plan-findings-all.md")" -eq 1 ]] \
    || fail 'ok re-tally cumulative merge should be idempotent'

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

pass 'persist-retally-step3-env harness'
