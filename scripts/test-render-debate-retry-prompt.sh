#!/usr/bin/env bash
# test-render-debate-retry-prompt.sh — offline harness for render-debate-retry-prompt.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd -P)"
RDR="$SCRIPT_DIR/render-debate-retry-prompt.sh"
PASS=0
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { PASS=$((PASS + 1)); }

[[ -x "$RDR" ]] || fail "render-debate-retry-prompt.sh missing or not executable"

tmpdir=$(mktemp -d "${TMPDIR:-/tmp}/larch-test-debate-retry.XXXXXX")
trap 'rm -rf "$tmpdir"' EXIT

orig="$tmpdir/original.txt"
prev="$tmpdir/previous.txt"
printf '%s\n' 'ORIGINAL_PROMPT_BODY_LINE_1' >"$orig"
printf '%s\n' 'previous output stub' >"$prev"

# (a) unknown flag
if "$RDR" --not-a-flag 2>/dev/null; then
  fail "expected non-zero exit on unknown flag"
fi
pass "unknown flag rejected"

# (b) missing required original file
if "$RDR" \
  --original-prompt-file "$tmpdir/missing.txt" \
  --previous-output-file "$prev" \
  --failure-reason no_output \
  --retry-tool cursor \
  --output "$tmpdir/out.txt" 2>/dev/null; then
  fail "expected failure when original missing"
fi
pass "missing original rejected"

outp="$tmpdir/rendered.txt"

run_render() {
  local reasons="$1" tool="$2"
  rm -f "$outp"
  "$RDR" \
    --original-prompt-file "$orig" \
    --previous-output-file "$prev" \
    --failure-reason "$reasons" \
    --retry-tool "$tool" \
    --output "$outp"
}

# (c) stdout KV contract
lines=$(run_render "no_output" codex | tr '\n' '|')
case "$lines" in
  *RENDERED=true*|*OUTPUT_FILE="$outp"*) ;;
  *) fail "stdout missing KV lines: $lines" ;;
esac
pass "stdout KV contract"

# (d) original body verbatim tail (missing_tag value embeds comma — use semicolon between multi-tokens)
run_render "missing_tag:claim,evidence" cursor
grep -Fq 'ORIGINAL_PROMPT_BODY_LINE_1' "$outp" || fail "original body not preserved verbatim"
pass "verbatim original body"

# (e) failure summary lists expected tokens
run_render "missing_tag:claim,evidence" cursor
grep -Fq 'missing_tag: claim,evidence' "$outp" || fail "missing_tag detail missing"
pass "missing_tag colon form"

for pair in \
  'bad_recommend|bad_recommend' \
  'missing_citation|missing_citation' \
  'role_mismatch:emitted ANTI_THESIS but role is thesis|role_mismatch: emitted ANTI_THESIS but role is thesis' \
  'substantive_empty|substantive_empty' \
  'no_output|no_output'
do
  IFS='|' read -r token needle <<<"$pair"
  run_render "$token" codex
  grep -Fq "$needle" "$outp" || fail "token $token not reflected (want $needle)"
done
pass "single-token reason lines"

# (f) comma-separated combo (distinct known tokens)
run_render "missing_citation,bad_recommend:dup" cursor
grep -Fq 'missing_citation' "$outp" || fail "combo missing missing_citation"
grep -Fq 'bad_recommend: dup' "$outp" || fail "combo missing bad_recommend detail"
pass "comma-separated combo"

# (g) Claude branch appends self-identify prohibition
run_render "no_output" claude
grep -Fq 'Do not self-identify your underlying model in your output' "$outp" || fail "claude branch missing self-id line"
pass "claude self-identify guard"

# (h) non-claude does not append self-identify line
run_render "no_output" cursor
if grep -Fq 'Do not self-identify your underlying model in your output' "$outp"; then
  fail "cursor retry should not append self-identify line"
fi
pass "non-claude omits self-identify line"

# (i) OUTPUT FORMAT appears soon after the corrective preamble when the original leads with it
orig2="$tmpdir/orig2.txt"
{
  printf '%s\n' 'OUTPUT FORMAT — probe block must appear early when upstream templates lead with OUTPUT FORMAT'
  cat "$orig"
} >"$orig2"
"$RDR" \
  --original-prompt-file "$orig2" \
  --previous-output-file "$prev" \
  --failure-reason no_output \
  --retry-tool codex \
  --output "$outp"
line_no=$(grep -nF 'OUTPUT FORMAT' "$outp" | head -1 | cut -d: -f1 || true)
[[ -n "$line_no" && "$line_no" -lt 30 ]] || fail "OUTPUT FORMAT not near top of rendered prompt (line=$line_no)"
pass "OUTPUT FORMAT early-window pin"

# (j) dialectic-execution documents retry output basename pattern (contract pin)
DEX="$SCRIPT_DIR/../skills/design/references/dialectic-execution.md"
grep -Fq 'debate-<n>-<retry-tool>-<side>-retry1.txt' "$DEX" \
  || fail "dialectic-execution.md missing retry1 filename pattern"
grep -Fq 'debate-<n>-claude-<side>-retry2.txt' "$DEX" \
  || fail "dialectic-execution.md missing claude retry2 filename pattern"
pass "retry filename patterns documented"

# (k) invalid retry tool
if run_render "no_output" vendor 2>/dev/null; then
  fail "expected invalid retry-tool rejection"
fi
pass "invalid retry-tool rejected"

# (l) unknown failure-reason token head rejected
if run_render "totally_unknown_reason" cursor 2>/dev/null; then
  fail "expected rejection on unknown failure-reason head"
fi
pass "unknown failure-reason head rejected"

# (m) bounded prior-output excerpt embedded
printf '%s\n' 'LINE_FROM_PREVIOUS_DEBATER_OUTPUT' >"$prev"
run_render "no_output" codex
grep -Fq 'Prior attempt (bounded excerpt' "$outp" || fail "prior excerpt header missing"
grep -Fq 'LINE_FROM_PREVIOUS_DEBATER_OUTPUT' "$outp" || fail "prior excerpt body missing"
pass "prior output excerpt embedded"

printf 'PASS: test-render-debate-retry-prompt.sh — %s checks\n' "$PASS"
