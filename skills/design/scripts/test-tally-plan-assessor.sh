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

grep -Fq 'QUALIFICATIONS_SUMMARY=' "$TMP/v.txt.env" || fail 'missing env sidecar'

pass 'tally-plan-assessor harness'
