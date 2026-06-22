#!/usr/bin/env bash
# test-architectural-guidelines-step.sh — harness for post-7a guideline staging contracts.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
SKILL="$ROOT/skills/implement/SKILL.md"
TMPDIR="${TMPDIR:-/tmp}/larch-guidelines-step-$$"
rm -rf "$TMPDIR"
mkdir -p "$TMPDIR"
trap 'rm -rf "$TMPDIR"' EXIT

contains() {
  local file="$1" literal="$2" label="$3"
  if ! grep -Fq -- "$literal" "$file"; then
    printf 'missing %s\n' "$label" >&2
    return 1
  fi
}

contains "$SKILL" 'IMMEDIATELY skip to Step 7a for checks/diagrams; architectural-guidelines Phase A staging runs after Step 7a, not on the Step 6 skip branch.' 'step6 skip then post-7a staging'
contains "$SKILL" 'Continue to Architectural guidelines Phase A staging before Step 8 IMMEDIATELY.' 'step7a anti-halt phase-a requirement'
contains "$SKILL" 'Do not call `architectural-guidelines pin-note-from-staged` in Phase A.' 'no durable pin in phase a'

ASSESSMENT="$TMPDIR/assessment.md"
DIFF_FILE="$TMPDIR/architectural-guideline-materialized-diff.txt"
printf 'Consulted ARCHITECTURAL_GUIDELINES.md; no deviations identified.\n' > "$ASSESSMENT"
printf '' > "$DIFF_FILE"
DIFF_FP="$(python3 -c "import hashlib; print(hashlib.sha256(b'').hexdigest())")"
python3 "$ROOT/python/cli.py" architectural-guidelines write-staged-assessment \
  --implement-tmpdir "$TMPDIR" \
  --assessment-file "$ASSESSMENT" \
  --assessed-head-sha head-a \
  --diff-fingerprint "$DIFF_FP" \
  --diff-file "$DIFF_FILE" \
  --base-ref origin/main >/dev/null

test -f "$TMPDIR/architectural-guideline-staged-assessment.md"
test ! -e "$TMPDIR/architectural-guideline-note.meta.env"
PIN_OUT="$(python3 "$ROOT/python/cli.py" architectural-guidelines pin-note-from-staged \
  --implement-tmpdir "$TMPDIR" \
  --head-sha head-b \
  --base-ref origin/main 2>&1)"
printf '%s\n' "$PIN_OUT" | grep -q 'ARCHITECTURAL_GUIDELINES_PIN_STATUS=ok'
cmp "$TMPDIR/architectural-guideline-staged-assessment.md" "$TMPDIR/architectural-guideline-note.md"
