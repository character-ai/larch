#!/usr/bin/env bash
# Offline harness for tally-plan-assessor.sh
set -euo pipefail
export LARCH_QUIET_DISABLE=1
unset LARCH_BREADCRUMB_STREAM LARCH_DONE_SENTINEL LARCH_STATUS_FILE \
  LARCH_QUIET_LOG_FILE LARCH_BREADCRUMBS_SURFACED_FILE LARCH_PAIRED_PID_FILE || true

ROOT="$(cd "$(dirname "$0")/../../.." && pwd -P)"
SUBJECT="$ROOT/skills/design/scripts/tally-plan-assessor.sh"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; }

# shellcheck disable=SC2016 # Literal grep pin for Bash 3.2-safe array expansion.
grep -Fq 'for existing in ${qual_worse_list[@]+"${qual_worse_list[@]}"}; do' "$SUBJECT" \
  || fail 'bash32-safe empty-array idiom missing from add_distinct_qualification'

TMP=$(mktemp -d "${TMPDIR:-/tmp}/ttpa.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

write_assessor() {
  local path="$1" verdict="$2"
  cat >"$path" <<EOF
ASSESSMENT: $verdict
REASONING: test reason for $verdict
QUALIFICATIONS: qual-$verdict
EOF
}

run_tally() {
  local out="$TMP/v.txt"
  LARCH_QUIET_DISABLE=1 "$SUBJECT" \
    --design-tmpdir "$TMP" \
    --round-num 2 \
    --claude-output "$TMP/claude.txt" \
    --cursor-output "$TMP/cursor.txt" \
    --codex-output "$TMP/codex.txt" \
    --output "$out" >/dev/null 2>&1
  cat "$out"
}

assert_verdict() {
  local label="$1" expect_majority="$2" c="$3" x="$4" d="$5"
  write_assessor "$TMP/claude.txt" "$c"
  write_assessor "$TMP/cursor.txt" "$x"
  write_assessor "$TMP/codex.txt" "$d"
  body=$(run_tally)
  if [[ "$expect_majority" == WORSE ]]; then
    printf '%s\n' "$body" | grep -Fq 'WORSE:' || fail "$label expected WORSE"
  else
    printf '%s\n' "$body" | grep -Fxq 'NOT_WORSE' || fail "$label expected NOT_WORSE got: $body"
  fi
}

assert_verdict '(0,0,3)' WORSE WORSE WORSE WORSE
assert_verdict '(0,1,2)' WORSE WORSE TIE WORSE
assert_verdict '(1,0,2)' WORSE BETTER WORSE WORSE
assert_verdict '(2,1,0)' NOT_WORSE BETTER BETTER TIE
assert_verdict '(0,2,1)' NOT_WORSE TIE TIE WORSE
assert_verdict '(1,1,1)' NOT_WORSE BETTER TIE WORSE
: >"$TMP/cursor.txt"
write_assessor "$TMP/claude.txt" WORSE
write_assessor "$TMP/codex.txt" WORSE
body=$(run_tally)
printf '%s\n' "$body" | grep -Fq 'WORSE:' || fail '(0,0,2) expected WORSE'
write_assessor "$TMP/claude.txt" TIE
write_assessor "$TMP/cursor.txt" WORSE
: >"$TMP/codex.txt"
body=$(run_tally)
printf '%s\n' "$body" | grep -Fxq 'NOT_WORSE' || fail '(0,1,1) expected NOT_WORSE'
write_assessor "$TMP/claude.txt" TIE
write_assessor "$TMP/cursor.txt" TIE
: >"$TMP/codex.txt"
body=$(run_tally)
printf '%s\n' "$body" | grep -Fxq 'NOT_WORSE' || fail '(0,2,0) expected NOT_WORSE'
write_assessor "$TMP/claude.txt" WORSE
: >"$TMP/cursor.txt"
: >"$TMP/codex.txt"
body=$(run_tally)
printf '%s\n' "$body" | grep -Fq 'WORSE:' || fail '(0,0,1) expected WORSE'
write_assessor "$TMP/claude.txt" TIE
: >"$TMP/cursor.txt"
: >"$TMP/codex.txt"
body=$(run_tally)
printf '%s\n' "$body" | grep -Fxq 'NOT_WORSE' || fail '(0,1,0) expected NOT_WORSE'
grep -Fq 'EFFECTIVE_ASSESSORS=1' "$TMP/v.txt.env" || fail 'single effective assessor count missing'

write_assessor "$TMP/claude.txt" TIE
write_assessor "$TMP/cursor.txt" TIE
write_assessor "$TMP/codex.txt" TIE
body=$(run_tally)
printf '%s\n' "$body" | grep -Fxq 'NOT_WORSE' || fail 'all-TIE should be NOT_WORSE'
grep -Fq 'TIE_VOTES=3' "$TMP/v.txt.env" || fail 'all-TIE tie count missing'

: >"$TMP/claude.txt"
: >"$TMP/cursor.txt"
: >"$TMP/codex.txt"
body=$(run_tally)
printf '%s\n' "$body" | grep -Fxq 'NOT_WORSE' || fail 'zero-effective should degrade open to NOT_WORSE'
grep -Fq 'EFFECTIVE_ASSESSORS=0' "$TMP/v.txt.env" || fail 'zero-effective assessor count missing'
grep -Fq 'DEGRADED_DEFAULT_OPEN=true' "$TMP/v.txt.env" || fail 'zero-effective should mark degraded default open'
grep -Fq 'QUALIFICATIONS_SUMMARY=Plan-quality assessor panel degraded; no WORSE-majority verdict available.' "$TMP/v.txt.env" || fail 'zero-effective should use degraded summary'

write_assessor "$TMP/claude.txt" WORSE
printf '**ASSESSMENT: WORSE**\nREASONING: md\nQUALIFICATIONS: mdqual\n' >"$TMP/cursor.txt"
write_assessor "$TMP/codex.txt" TIE
body=$(run_tally)
printf '%s\n' "$body" | grep -Fq 'WORSE:' || fail 'markdown-wrapped parse'
grep -Fq 'QUALIFICATIONS_SUMMARY=qual-WORSE | mdqual' "$TMP/v.txt.env" || fail 'distinct worse qualifications should be joined'

cat >"$TMP/claude.txt" <<'EOF'
ASSESSMENT: WORSE
REASONING: no qualification
EOF
: >"$TMP/cursor.txt"
: >"$TMP/codex.txt"
run_tally >/dev/null
grep -Fq 'QUALIFICATIONS_SUMMARY=WORSE-majority assessors supplied no qualifications.' "$TMP/v.txt.env" || fail 'worse-majority fallback summary missing'

cat >"$TMP/claude.txt" <<'EOF'
assessment = tie
reasoning = earlier
ASSESSMENT: WORSE
REASONING: later
QUALIFICATIONS: q1
EOF
: >"$TMP/cursor.txt"
: >"$TMP/codex.txt"
body=$(run_tally)
printf '%s\n' "$body" | grep -Fxq 'NOT_WORSE' || fail 'duplicate assessment block should honor first verdict'
grep -Fq 'QUALIFICATIONS_SUMMARY=Assessors found no WORSE-majority consensus.' "$TMP/v.txt.env" || fail 'duplicate assessment block should ignore later verdict block'

cat >"$TMP/claude.txt" <<'EOF'
ASSESSMENT: WORSE because the latest revision regressed scope control
REASONING: trailing rationale tokenization
QUALIFICATIONS: tokenized
EOF
: >"$TMP/cursor.txt"
: >"$TMP/codex.txt"
body=$(run_tally)
printf '%s\n' "$body" | grep -Fq 'WORSE:' || fail 'assessment with trailing rationale should parse first token'
grep -Fq 'QUALIFICATIONS_SUMMARY=tokenized' "$TMP/v.txt.env" || fail 'trailing-rationale parse must preserve qualification'

cat >"$TMP/claude.txt" <<'EOF'
assessment: worse
reasoning: lowercase
qualifications: lower
EOF
: >"$TMP/cursor.txt"
: >"$TMP/codex.txt"
body=$(run_tally)
printf '%s\n' "$body" | grep -Fq 'WORSE:' || fail 'lowercase assessment tokens should parse'
grep -Fq 'QUALIFICATIONS_SUMMARY=lower' "$TMP/v.txt.env" || fail 'lowercase assessment tokens must preserve qualification'

cat >"$TMP/claude.txt" <<'EOF'
ASSESSMENT: WORSE
REASONING: line one
KEY=spoof
QUALIFICATIONS: first line
NEXT=spoof
EOF
: >"$TMP/cursor.txt"
: >"$TMP/codex.txt"
body=$(run_tally)
printf '%s\n' "$body" | grep -Fq 'WORSE:' || fail 'multiline env-safety case should still be WORSE'
grep -Eq '^KEY=' "$TMP/v.txt.env" && fail 'WORSE justification must not inject extra env keys'
grep -Eq '^NEXT=' "$TMP/v.txt.env" && fail 'QUALIFICATIONS_SUMMARY must not inject extra env keys'
grep -Fq 'QUALIFICATIONS_SUMMARY=first line NEXT=spoof' "$TMP/v.txt.env" || fail 'QUALIFICATIONS_SUMMARY must collapse multiline content onto one line'

grep -Fq 'QUALIFICATIONS_SUMMARY=' "$TMP/v.txt.env" || fail 'missing env sidecar'

pass 'tally-plan-assessor harness'
