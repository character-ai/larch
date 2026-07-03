#!/usr/bin/env bash
# test-architectural-guidelines-step.sh — harness for post-7a guideline staging contracts.
# shellcheck disable=SC2016  # literal Markdown snippets intentionally include $, backticks, and quotes.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
SKILL="$ROOT/skills/implement/SKILL.md"
PRESENT_REF="$ROOT/skills/implement/references/architectural-guidelines-present.md"
CONFLICT_REF="$ROOT/skills/implement/references/conflict-resolution.md"
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

contains "$SKILL" 'This includes the Step 6 `FILES_CHANGED=false` skip-to-7a path and Step 7 skipped/no-op paths.' 'step6 skip then post-7a staging'
contains "$SKILL" 'Continue to Architectural guidelines Phase A staging before Step 8 IMMEDIATELY.' 'step7a anti-halt phase-a requirement'
contains "$SKILL" 'The prepare helper clears stale Phase A artifacts at entry; do not add an orchestrator-side `rm` loop for those files.' 'prepare clears stale artifacts'
contains "$SKILL" '"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" skills/implement/scripts/step-architectural-guidelines-prepare.sh' 'prepare wrapper fence'
contains "$SKILL" 'Capture the prepare fence exit code and stdout together. Apply this exit-code routing before any `ARCHITECTURAL_GUIDELINES_STATUS` branching:' 'prepare exit-code routing before status branching'
contains "$SKILL" 'If the prepare fence exits non-zero and stdout does not contain `ARCHITECTURAL_GUIDELINES_STATUS=present` or `ARCHITECTURAL_GUIDELINES_STATUS=invalid`, append `ARCHITECTURAL_GUIDELINES_WARNING` to `Warnings` in `$IMPLEMENT_TMPDIR/execution-issues.md` and stop Phase A without continuing to Step 8.' 'prepare hard-fail routing'
contains "$SKILL" 'If the prepare fence exits `1` and stdout contains `ARCHITECTURAL_GUIDELINES_STATUS=present` with `ARCHITECTURAL_GUIDELINES_DIFF_STATUS=failed`, log `ARCHITECTURAL_GUIDELINES_WARNING`, continue without staged or durable artifacts, then proceed to Step 8.' 'prepare present diff-failure routing'
contains "$SKILL" 'read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/architectural-guidelines-present.md` completely, then follow it for prompt-side assessment, staged persistence, chat output, warnings, and Step 8 continuation.' 'present ok mandatory reference pointer'
contains "$SKILL" 'Continue to Step 8 only after Phase A completes successfully or is skipped via the explicit `absent` / `invalid` / present-with-diff-failure continue paths above; hard prepare failures stop before Step 8.' 'phase-a anti-halt hard-failure stop'
not_contains "$SKILL" 'step-architectural-guidelines-write-staged.sh' 'write-staged wrapper moved to present reference'
not_contains "$SKILL" 'step-architectural-guidelines-read.sh' 'retired read wrapper reference'
not_contains "$SKILL" 'step-architectural-guidelines-read.md' 'retired read doc reference'
not_contains "$SKILL" 'step-architectural-guidelines-materialize.sh' 'retired materialize wrapper reference'
not_contains "$SKILL" 'step-architectural-guidelines-materialize.md' 'retired materialize doc reference'
test ! -e "$ROOT/skills/implement/scripts/step-architectural-guidelines-read.sh"
test ! -e "$ROOT/skills/implement/scripts/step-architectural-guidelines-read.md"
test ! -e "$ROOT/skills/implement/scripts/step-architectural-guidelines-materialize.sh"
test ! -e "$ROOT/skills/implement/scripts/step-architectural-guidelines-materialize.md"
test -x "$ROOT/skills/implement/scripts/step-architectural-guidelines-prepare.sh"

test -f "$PRESENT_REF"
test -f "$CONFLICT_REF"
contains "$PRESENT_REF" '# Architectural Guidelines Present Path' 'present reference heading'
contains "$PRESENT_REF" '**When to load**: MANDATORY only after prepare stdout shows `ARCHITECTURAL_GUIDELINES_STATUS=present` with `ARCHITECTURAL_GUIDELINES_DIFF_STATUS=ok`.' 'present reference load predicate'
contains "$PRESENT_REF" 'Compare the parsed guideline entries and materialized diff using prompt-side judgment, then persist an orchestrator-authored assessment.' 'present reference assessment judgment'
contains "$PRESENT_REF" 'The assessment body must be either `Consulted ARCHITECTURAL_GUIDELINES.md; no deviations identified.` or a short deviation list with rationale.' 'present reference assessment body'
contains "$PRESENT_REF" '"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" skills/implement/scripts/step-architectural-guidelines-write-staged.sh architectural-guideline-assessment-draft.md' 'present reference write-staged fence'
contains "$PRESENT_REF" 'When the note indicates deviations, also append it under `Warnings` in `$IMPLEMENT_TMPDIR/execution-issues.md`.' 'present reference deviation warnings'
contains "$PRESENT_REF" 'Do not call `architectural-guidelines pin-note-from-staged` in Phase A.' 'present reference no durable pin'
contains "$PRESENT_REF" 'Continue to Step 8 only after the present-plus-ok assessment and staged persistence complete successfully.' 'present reference step 8 continuation'
contains "$CONFLICT_REF" 're-enter the `### Architectural guidelines (Phase A — staging)` subsection in `${CLAUDE_PLUGIN_ROOT}/skills/implement/SKILL.md` in full before the ship re-invoke.' 'conflict rerun full phase-a subsection'
contains "$CONFLICT_REF" 'including the mandatory read of `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/architectural-guidelines-present.md` only after prepare stdout shows `ARCHITECTURAL_GUIDELINES_STATUS=present` with `ARCHITECTURAL_GUIDELINES_DIFF_STATUS=ok`.' 'conflict rerun present reference predicate'
not_contains "$CONFLICT_REF" 'prompt-side assessment and calls' 'abbreviated conflict rerun prose'
not_contains "$CONFLICT_REF" 'write-staged-assessment' 'direct conflict rerun staged writer call'

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
