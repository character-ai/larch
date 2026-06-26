#!/usr/bin/env bash
# test-architectural-guidelines-step.sh — harness for post-7a guideline staging contracts.
# shellcheck disable=SC2016  # literal Markdown snippets intentionally include $, backticks, and quotes.

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

not_contains() {
  local file="$1" literal="$2" label="$3"
  if grep -Fq -- "$literal" "$file"; then
    printf 'unexpected %s\n' "$label" >&2
    return 1
  fi
}

contains "$SKILL" 'IMMEDIATELY skip to Step 7a for checks/diagrams; architectural-guidelines Phase A staging runs after Step 7a, not on the Step 6 skip branch.' 'step6 skip then post-7a staging'
contains "$SKILL" 'Continue to Architectural guidelines Phase A staging before Step 8 IMMEDIATELY.' 'step7a anti-halt phase-a requirement'
contains "$SKILL" 'The prepare helper clears stale Phase A artifacts at entry; do not add an orchestrator-side `rm` loop for those files.' 'prepare clears stale artifacts'
contains "$SKILL" 'bash "$IMPLEMENT_TMPDIR/larch-run.sh" skills/implement/scripts/step-architectural-guidelines-prepare.sh' 'prepare wrapper fence'
contains "$SKILL" 'Capture the prepare fence exit code and stdout together. Apply this exit-code routing before any `ARCHITECTURAL_GUIDELINES_STATUS` branching:' 'prepare exit-code routing before status branching'
contains "$SKILL" 'If the prepare fence exits non-zero and stdout does not contain `ARCHITECTURAL_GUIDELINES_STATUS=present` or `ARCHITECTURAL_GUIDELINES_STATUS=invalid`, append `ARCHITECTURAL_GUIDELINES_WARNING` to `Warnings` in `$IMPLEMENT_TMPDIR/execution-issues.md` and stop Phase A without continuing to Step 8.' 'prepare hard-fail routing'
contains "$SKILL" 'If the prepare fence exits `1` and stdout contains `ARCHITECTURAL_GUIDELINES_STATUS=present` with `ARCHITECTURAL_GUIDELINES_DIFF_STATUS=failed`, log `ARCHITECTURAL_GUIDELINES_WARNING`, continue without staged or durable artifacts, then proceed to Step 8.' 'prepare present diff-failure routing'
contains "$SKILL" 'Continue to Step 8 only after Phase A completes successfully or is skipped via the explicit `absent` / `invalid` / present-with-diff-failure continue paths above; hard prepare failures stop before Step 8.' 'phase-a anti-halt hard-failure stop'
contains "$SKILL" 'Do not call `architectural-guidelines pin-note-from-staged` in Phase A.' 'no durable pin in phase a'
not_contains "$SKILL" 'step-architectural-guidelines-read.sh' 'retired read wrapper reference'
not_contains "$SKILL" 'step-architectural-guidelines-read.md' 'retired read doc reference'
not_contains "$SKILL" 'step-architectural-guidelines-materialize.sh' 'retired materialize wrapper reference'
not_contains "$SKILL" 'step-architectural-guidelines-materialize.md' 'retired materialize doc reference'
test ! -e "$ROOT/skills/implement/scripts/step-architectural-guidelines-read.sh"
test ! -e "$ROOT/skills/implement/scripts/step-architectural-guidelines-read.md"
test ! -e "$ROOT/skills/implement/scripts/step-architectural-guidelines-materialize.sh"
test ! -e "$ROOT/skills/implement/scripts/step-architectural-guidelines-materialize.md"
test -x "$ROOT/skills/implement/scripts/step-architectural-guidelines-prepare.sh"

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
