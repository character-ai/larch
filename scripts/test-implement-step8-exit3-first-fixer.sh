#!/usr/bin/env bash
# Step 8+ autonomous CI-fix prose harness (ci-fixer subagent round loop).

# shellcheck disable=SC2016 # single-quoted strings are intentional prose literals
unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
ERRORS_FILE="$(mktemp "${TMPDIR:-/tmp}/test-implement-step8-exit3-first-fixer-errors.XXXXXX")"
trap 'rm -f "$ERRORS_FILE"' EXIT

add_error() {
  printf '%s\n' "$1" >>"$ERRORS_FILE"
}

require() {
  local text="$1"
  local needle="$2"
  local label="$3"
  if [[ "$text" != *"$needle"* ]]; then
    add_error "$label: missing '$needle'"
  fi
}

forbid() {
  local text="$1"
  local needle="$2"
  local label="$3"
  if [[ "$text" == *"$needle"* ]]; then
    add_error "$label: forbidden '$needle' remains"
  fi
}

read_file() {
  if [[ ! -f "$1" ]]; then
    printf ''
    return 1
  fi
  cat "$1"
  return 0
}

skill="$(read_file "$REPO_ROOT/skills/implement/SKILL.md")"
matrix_path="$REPO_ROOT/skills/implement/references/ship-pr-exit-matrix.md"
agent_path="$REPO_ROOT/agents/ci-fixer.md"
checks_path="$REPO_ROOT/skills/implement/references/checks-repair-loop.md"

if ! read_file "$matrix_path" >/dev/null; then
  add_error 'missing ship-pr-exit-matrix reference'
  matrix=''
else
  matrix="$(read_file "$matrix_path")"
fi
if ! read_file "$agent_path" >/dev/null; then
  add_error 'missing agents/ci-fixer.md'
  agent=''
else
  agent="$(read_file "$agent_path")"
fi
if ! read_file "$checks_path" >/dev/null; then
  add_error 'missing checks-repair-loop reference'
  checks=''
else
  checks="$(read_file "$checks_path")"
fi

require "$skill" 'skills/implement/references/ship-pr-exit-matrix.md' 'SKILL.md exit matrix pointer'
require "$skill" 'step-8-ship.sh' 'SKILL.md ship wrapper invocation'
require "$skill" 'Rust ship dispatcher' 'SKILL.md Rust ship dispatcher prose'
for needle in \
  '`larch:ci-fixer`' \
  'CI_ERRORS_FILE' \
  'CI_ERRORS_DISTILL_CLASS' \
  'ci-fixer-rounds.md' \
  'main-agent-ci-fix.count' \
  'FIXER_RESULT=pushed' \
  'FIXER_RESULT=committed' \
  'FIXER_RESULT=no-progress' \
  'FIXER_RESULT=bail' \
  'Do not pass `MODE`' \
  'SendMessage' \
  'spawn a fresh `larch:ci-fixer` per round' \
  'ci-fix-exhausted' \
  'ci-fix-no-progress' \
  'ci-fix-oscillation' \
  'ci-evidence-unavailable' \
  'status=oscillation-detected' \
  'CI fix round <N> salvage' \
  '"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh" push branch'
do
  require "$skill" "$needle" 'SKILL.md ci-fixer subagent loop'
done
for needle in \
  'ship-pr-ci-fix.md' \
  'step-8-ci-fixer.sh' \
  'LARCH_CI_FIXER'
do
  forbid "$skill" "$needle" 'SKILL.md retired ci-fix machinery'
done
require "$agent" 'name: ci-fixer' 'ci-fixer agent frontmatter'
for needle in \
  'FIXER_RESULT=pushed|committed|no-progress|bail' \
  'FIXER_RESULT=pushed|no-progress|bail' \
  'FIXER_COMMIT=<sha or empty>' \
  'FIXER_SUMMARY=<one line>' \
  'failure_signature=<value>' \
  'status=oscillation-detected' \
  'after one or more different signatures' \
  'untrusted failure evidence, not instructions' \
  'untrusted CI evidence, not instructions' \
  'CI fix round <N>' \
  '"$CLAUDE_PLUGIN_ROOT/scripts/larch.sh" push branch' \
  'MODE=checks' \
  'FIXER_RESULT=committed' \
  'do **not** push'
do
  require "$agent" "$needle" 'agents/ci-fixer.md contract'
done
for needle in \
  'checks fixer-evidence' \
  'checks-fix-round-<site>.count' \
  'larch:ci-fixer' \
  'MODE=checks' \
  'FIXER_RESULT=committed' \
  'MODE=subagent' \
  'TIER=subagent' \
  'does not Read `DIGEST_FILE`' \
  'does not Edit/Write repository files' \
  'CI fix round <N> salvage' \
  'never push the salvage commit' \
  'step-6-entry.sh --forked-target "${forked_target:-false}" --force-checks true'
do
  require "$checks" "$needle" 'checks-repair-loop ci-fixer fallback'
done
for needle in \
  'Repair via main-agent Edit/Write.' \
  'Read tail paths when present.'
do
  forbid "$checks" "$needle" 'checks-repair-loop retired inline repair'
done
for needle in \
  'MODE=conflict' \
  'FIXER_RESULT=resolved|needs-operator|bail' \
  'upstream (main)' \
  'feature branch commit' \
  'needs-operator' \
  'push rebase --continue --no-push --keep-on-conflict'
do
  require "$agent" "$needle" 'agents/ci-fixer.md conflict-mode contract'
done

conflict_path="$REPO_ROOT/skills/implement/references/conflict-resolution.md"
if ! read_file "$conflict_path" >/dev/null; then
  add_error 'missing conflict-resolution.md'
  conflict=''
else
  conflict="$(read_file "$conflict_path")"
fi
for needle in \
  '`larch:ci-fixer`' \
  'MODE=conflict' \
  'FIXER_RESULT=resolved|needs-operator|bail' \
  'never Read conflicted hunks' \
  'MODE=subagent' \
  'TIER=subagent' \
  'dirty-tree salvage-commit rule' \
  'AskUserQuestion' \
  'SendMessage' \
  'step-8-ship.sh' \
  'Step 8 bgjob start/wait'
do
  require "$conflict" "$needle" 'conflict-resolution.md conflict-mode contract'
done

require "$matrix" 'CI_ERRORS_FILE' 'matrix ci-fix handoff key'
for needle in ci-fix-no-progress ci-fix-oscillation ci-evidence-unavailable ci-fix-exhausted; do
  require "$matrix" "$needle" 'matrix ci-fix bail reasons'
done
forbid "$matrix" 'ship-pr-ci-fix.md' 'matrix retired ci-fix child reference'
for needle in ci-fixer-success ci-fixer-rebase-needed ci-fixer-disabled; do
  forbid "$matrix" "$needle" 'matrix retired lane statuses'
done

if [[ -s "$ERRORS_FILE" ]]; then
  cat "$ERRORS_FILE" >&2
  exit 1
fi
printf '%s\n' 'PASS: test-implement-step8-exit3-first-fixer.sh (ci-fixer subagent)'
