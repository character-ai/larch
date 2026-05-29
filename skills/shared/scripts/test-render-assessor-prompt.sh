#!/usr/bin/env bash
# Offline harness for render-assessor-prompt.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd -P)"
SUBJECT="$ROOT/skills/shared/scripts/render-assessor-prompt.sh"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; }

TMP=$(mktemp -d "${TMPDIR:-/tmp}/trap.XXXXXX")
trap 'rm -rf "$TMP"' EXIT
printf 'feature\n' >"$TMP/feature.txt"
printf 'orig\n' >"$TMP/orig.txt"
printf 'prev\n' >"$TMP/prev.txt"
printf 'curr\n' >"$TMP/curr.txt"
out="$TMP/prompt.txt"

"$SUBJECT" \
  --plan-original "$TMP/orig.txt" \
  --plan-prev "$TMP/prev.txt" \
  --plan-current "$TMP/curr.txt" \
  --feature-file "$TMP/feature.txt" \
  --output "$out"

grep -Fq 'ASSESSMENT:' "$out" || fail 'missing ASSESSMENT token'
grep -Fq 'REASONING:' "$out" || fail 'missing REASONING token'
grep -Fq 'QUALIFICATIONS:' "$out" || fail 'missing QUALIFICATIONS token'
grep -Fq 'orig' "$out" || fail 'missing inlined orig'
grep -Fq 'prev' "$out" || fail 'missing inlined prev'
grep -Fq 'curr' "$out" || fail 'missing inlined curr'

set +e
"$SUBJECT" --plan-original "$TMP/missing.txt" --plan-prev "$TMP/prev.txt" \
  --plan-current "$TMP/curr.txt" --feature-file "$TMP/feature.txt" --output "$out" 2>/dev/null
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail 'expected non-zero for missing input'

pass 'render-assessor-prompt harness'
