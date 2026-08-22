#!/usr/bin/env bash
# test-architectural-guidelines-step.sh — harness for the Step 8 assessment adapter route.
# shellcheck disable=SC2016  # literal Markdown snippets intentionally include $, backticks, and quotes.

unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
SKILL="$ROOT/skills/implement/SKILL.md"
INVARIANTS_REF="$ROOT/skills/implement/references/architectural-invariants-present.md"
PRESENT_REF="$ROOT/skills/implement/references/architectural-guidelines-present.md"
INVARIANTS_WRITE_COMPOSE_MD="$ROOT/skills/implement/scripts/step-architectural-invariants-write-compose.md"
CONFLICT_REF="$ROOT/skills/implement/references/conflict-resolution.md"
EXIT_MATRIX_REF="$ROOT/skills/implement/references/ship-pr-exit-matrix.md"
TMPDIR="${TMPDIR:-/tmp}/larch-guidelines-step-$$"
rm -rf "$TMPDIR"
mkdir -p "$TMPDIR"
trap 'rm -rf "$TMPDIR"' EXIT

contains() {
  local file="$1" literal="$2" label="$3"
  if ! grep -Fq -- "$literal" "$file"; then
    printf 'missing %s
' "$label" >&2
    return 1
  fi
}

not_contains() {
  local file="$1" literal="$2" label="$3"
  if grep -Fq -- "$literal" "$file"; then
    printf 'unexpected %s
' "$label" >&2
    return 1
  fi
}

contains "$SKILL" 'Step 8 owns the subagent assessment route. After later `HEAD` movement, `architectural-assessment materialize` re-runs its deterministic pre-filter against incremental scope, reuses valid coverage for nonintersecting changes, and re-assesses (via a fresh `larch:arch-assessor`) only when a later code change newly intersects architectural scope.' 'step7a scoped reassessment'
contains "$SKILL" 'scripts/larch.sh ship normalize-assessment-handoff --implement-tmpdir "$IMPLEMENT_TMPDIR"' 'normalization fence'
contains "$SKILL" 'rewrites the legacy aliases to `NEXT_ACTION=assessments`, persists canonical `DETAIL`, and emits the canonical kind list.' 'alias normalization and canonicalization'
contains "$SKILL" 'Do not repair malformed data, add a kind token, or add a fallback parser.' 'malformed detail fail closed'
contains "$SKILL" 'scripts/larch.sh architectural-assessment materialize --implement-tmpdir "$IMPLEMENT_TMPDIR" --repo-root "$REPO_ROOT" --kind <each requested kind>' 'materialize fence'
contains "$SKILL" 'spawn exactly one Agent-tool subagent with `subagent_type` `larch:arch-assessor`, covering every pending kind' 'subagent authoring'
contains "$SKILL" 'A `submit` exit code `10` means HEAD drifted between materialize and submit' 'head-drift retry'
contains "$SKILL" 'Capture `ASSESSMENT_REQUESTED_KINDS` from the normalization fence stdout.' 'normalization stdout binding'
contains "$SKILL" 'Require `ASSESSMENT_MATERIALIZE_STATUS=ok`.' 'materialize status'
contains "$SKILL" 'Require `ASSESSMENT_STATUS=complete` for every pending kind.' 'submit complete coverage'
contains "$SKILL" 'An unparseable final message, or `submit` `ASSESSMENT_STATUS=invalid-note`, gets exactly one fresh `larch:arch-assessor` respawn' 'unparseable respawn'
contains "$SKILL" 'return to the Step 8 ship launcher above exactly once. Do not relaunch once per kind.' 'single ship relaunch'
not_contains "$SKILL" '**MANDATORY: READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/architectural-invariants-present.md` completely. Author' 'no invariant prompt authorship'
not_contains "$SKILL" '**MANDATORY: READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/architectural-guidelines-present.md` completely. Invariant assessment' 'no guideline prompt authorship'
not_contains "$SKILL" 'step-architectural-guidelines-prepare.sh' 'retired prepare wrapper live reference'
not_contains "$SKILL" 'step-architectural-guidelines-write-staged.sh' 'retired staged writer live reference'

for path in "$PRESENT_REF" "$INVARIANTS_REF" "$INVARIANTS_WRITE_COMPOSE_MD" "$CONFLICT_REF" "$EXIT_MATRIX_REF"; do
  test -f "$path"
done
contains "$INVARIANTS_REF" 'This file is a route reference, not an assessment-work prompt.' 'invariant route reference'
contains "$INVARIANTS_REF" 'The dormant `NEXT_ACTION=invariants-assessment` compatibility alias normalizes to `NEXT_ACTION=assessments` with `DETAIL=invariants` before the materialize step.' 'invariant dormant alias'
contains "$INVARIANTS_REF" 'A reported invariant violation continues to block normal PR compose.' 'invariant blocking'
contains "$PRESENT_REF" 'This file is a route reference, not an assessment-work prompt.' 'guideline route reference'
contains "$PRESENT_REF" 'The dormant `NEXT_ACTION=guidelines-assessment` compatibility alias normalizes to `NEXT_ACTION=assessments` with `DETAIL=guidelines` before the materialize step.' 'guideline dormant alias'
contains "$PRESENT_REF" 'The caller does not read the materialized diff, write an assessment draft, call the deviation appender or a compose writer, or use inline fallback.' 'guideline no prompt-side work'
contains "$EXIT_MATRIX_REF" '`architectural-assessments` maps to `assessments`; `DETAIL` is a comma-separated kind list containing `invariants`, `guidelines`, or `invariants,guidelines`.' 'exit matrix combined reason mapping'
contains "$EXIT_MATRIX_REF" '`architectural-guidelines-assessment` maps to `guidelines-assessment`.' 'exit matrix guideline compatibility mapping'
contains "$EXIT_MATRIX_REF" '`architectural-invariants-assessment` maps to `invariants-assessment`.' 'exit matrix invariant compatibility mapping'
contains "$EXIT_MATRIX_REF" 'normalize once immediately before the `architectural-assessment materialize` step.' 'exit matrix normalization ordering'
contains "$EXIT_MATRIX_REF" 'After validation, relaunch `step-8-ship.sh` exactly once for all requested kinds.' 'exit matrix single relaunch'
not_contains "$EXIT_MATRIX_REF" 'author the compose-time note from the materialized final diff' 'exit matrix no prompt authorship'
not_contains "$EXIT_MATRIX_REF" 'after all listed writers succeed' 'exit matrix no per-kind writer ordering'

ASSESSMENT="$TMPDIR/architectural-guideline-assessment-draft.md"
printf 'Consulted ARCHITECTURAL_GUIDELINES.md; no deviations identified.\n' > "$ASSESSMENT"
HEAD_SHA="$(git -C "$ROOT" rev-parse HEAD)"
cat > "$TMPDIR/architectural-guideline-materialize.env" <<EOF
STATUS=present
HEAD_SHA=$HEAD_SHA
ASSESSED_HEAD_SHA=$HEAD_SHA
BASE_REF=origin/main
DIFF_FINGERPRINT=$(python3 -c "import hashlib; print(hashlib.sha256(b'').hexdigest())")
DIFF_SNAPSHOT=$TMPDIR/architectural-guideline-materialized-diff.txt
GUIDELINES_STATUS=present
EOF
printf '' > "$TMPDIR/architectural-guideline-materialized-diff.txt"
printf 'legacy staged\n' > "$TMPDIR/architectural-guideline-staged-assessment.md"
printf 'legacy drop\n' > "$TMPDIR/architectural-guideline-drop-notice.txt"
(
  cd "$ROOT"
  IMPLEMENT_TMPDIR="$TMPDIR" CLAUDE_PLUGIN_ROOT="$ROOT" \
    "$ROOT/skills/implement/scripts/step-architectural-guidelines-write-compose.sh" architectural-guideline-assessment-draft.md clean >/dev/null
)

test -f "$TMPDIR/architectural-guideline-note.md"
test -f "$TMPDIR/architectural-guideline-note.meta.env"
test ! -e "$TMPDIR/architectural-guideline-staged-assessment.md"
test ! -e "$TMPDIR/architectural-guideline-drop-notice.txt"
cmp "$ASSESSMENT" "$TMPDIR/architectural-guideline-note.md"
grep -Fxq "ASSESSMENT_KIND=clean" "$TMPDIR/architectural-guideline-note.meta.env"

# The retained wrapper also accepts an absolute assessment path under the run tmpdir.
IMPLEMENT_TMPDIR="$TMPDIR" CLAUDE_PLUGIN_ROOT="$ROOT" \
  "$ROOT/skills/implement/scripts/step-architectural-guidelines-write-compose.sh" "$ASSESSMENT" clean >/dev/null
cmp "$ASSESSMENT" "$TMPDIR/architectural-guideline-note.md"

MISSING_OUTCOME_TMP="$TMPDIR/missing-outcome"
mkdir -p "$MISSING_OUTCOME_TMP"
cp "$TMPDIR/architectural-guideline-materialize.env" "$MISSING_OUTCOME_TMP/architectural-guideline-materialize.env"
printf 'Consulted ARCHITECTURAL_GUIDELINES.md; no deviations identified.\n' > "$MISSING_OUTCOME_TMP/draft.md"
set +e
IMPLEMENT_TMPDIR="$MISSING_OUTCOME_TMP" CLAUDE_PLUGIN_ROOT="$ROOT" \
  "$ROOT/skills/implement/scripts/step-architectural-guidelines-write-compose.sh" draft.md >/dev/null
missing_outcome_rc=$?
set -e
test "$missing_outcome_rc" -eq 7
test ! -e "$MISSING_OUTCOME_TMP/architectural-guideline-note.md"

INVARIANT_ASSESSMENT="$TMPDIR/architectural-invariant-assessment-draft.md"
printf 'Consulted ARCHITECTURAL_INVARIANTS.md; no violations identified.\n' > "$INVARIANT_ASSESSMENT"
cat > "$TMPDIR/architectural-invariant-materialize.env" <<EOF
STATUS=present
HEAD_SHA=$HEAD_SHA
ASSESSED_HEAD_SHA=$HEAD_SHA
BASE_REF=origin/main
DIFF_FINGERPRINT=$(python3 -c "import hashlib; print(hashlib.sha256(b'').hexdigest())")
DIFF_SNAPSHOT=$TMPDIR/architectural-invariant-materialized-diff.txt
INVARIANTS_STATUS=present
EOF
printf '' > "$TMPDIR/architectural-invariant-materialized-diff.txt"
printf 'legacy staged\n' > "$TMPDIR/architectural-invariant-staged-assessment.md"
printf 'legacy drop\n' > "$TMPDIR/architectural-invariant-drop-notice.txt"
(
  cd "$ROOT"
  IMPLEMENT_TMPDIR="$TMPDIR" CLAUDE_PLUGIN_ROOT="$ROOT" \
    "$ROOT/skills/implement/scripts/step-architectural-invariants-write-compose.sh" architectural-invariant-assessment-draft.md clean >/dev/null
)

test -f "$TMPDIR/architectural-invariant-note.md"
test -f "$TMPDIR/architectural-invariant-note.meta.env"
test ! -e "$TMPDIR/architectural-invariant-staged-assessment.md"
test ! -e "$TMPDIR/architectural-invariant-drop-notice.txt"
cmp "$INVARIANT_ASSESSMENT" "$TMPDIR/architectural-invariant-note.md"
grep -Fxq "STATUS=present" "$TMPDIR/architectural-invariant-note.meta.env"
grep -Fxq "HEAD_SHA=$HEAD_SHA" "$TMPDIR/architectural-invariant-note.meta.env"
grep -Fxq "ASSESSED_HEAD_SHA=$HEAD_SHA" "$TMPDIR/architectural-invariant-note.meta.env"
grep -Fxq "INVARIANTS_STATUS=present" "$TMPDIR/architectural-invariant-note.meta.env"
grep -Fxq "ASSESSMENT_KIND=clean" "$TMPDIR/architectural-invariant-note.meta.env"

IMPLEMENT_TMPDIR="$TMPDIR" CLAUDE_PLUGIN_ROOT="$ROOT" \
  "$ROOT/skills/implement/scripts/step-architectural-invariants-write-compose.sh" "$INVARIANT_ASSESSMENT" clean >/dev/null
cmp "$INVARIANT_ASSESSMENT" "$TMPDIR/architectural-invariant-note.md"

STAGED_TMPDIR="$TMPDIR/staged-wrapper"
mkdir -p "$STAGED_TMPDIR"
printf 'No architectural guideline deviations were found.\n' > "$STAGED_TMPDIR/assessment.md"
printf '' > "$STAGED_TMPDIR/architectural-guideline-materialized-diff.txt"
cat > "$STAGED_TMPDIR/architectural-guideline-materialize.env" <<EOF
STATUS=present
HEAD_SHA=$HEAD_SHA
BASE_REF=origin/main
DIFF_FINGERPRINT=$(python3 -c "import hashlib; print(hashlib.sha256(b'').hexdigest())")
EOF
(
  cd "$TMPDIR"
  IMPLEMENT_TMPDIR="$STAGED_TMPDIR" CLAUDE_PLUGIN_ROOT="$ROOT" \
    "$ROOT/skills/implement/scripts/step-architectural-guidelines-write-staged.sh" assessment.md clean >/dev/null
)
grep -Fxq "ASSESSED_HEAD_SHA=$HEAD_SHA" "$STAGED_TMPDIR/architectural-guideline-staged-assessment.env"

set +e
IMPLEMENT_TMPDIR="$TMPDIR" CLAUDE_PLUGIN_ROOT="$ROOT" \
  "$ROOT/skills/implement/scripts/step-architectural-guidelines-write-compose.sh" >/dev/null 2>&1
missing_guideline_arg_rc=$?
IMPLEMENT_TMPDIR="$TMPDIR" CLAUDE_PLUGIN_ROOT="$ROOT" \
  "$ROOT/skills/implement/scripts/step-architectural-invariants-write-compose.sh" >/dev/null 2>&1
missing_invariant_arg_rc=$?
set -e
test "$missing_guideline_arg_rc" -ne 0
test "$missing_invariant_arg_rc" -ne 0
