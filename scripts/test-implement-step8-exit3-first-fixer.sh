#!/usr/bin/env bash
# Step 8+ autonomous CI-fix prose harness (ci-fixer subagent round loop).

unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail

python3 <<'PY'
from pathlib import Path
import sys

errors=[]

def require(text, needle, label):
    if needle not in text:
        errors.append(f'{label}: missing {needle!r}')

def forbid(text, needle, label):
    if needle in text:
        errors.append(f'{label}: forbidden {needle!r} remains')

skill=Path('skills/implement/SKILL.md').read_text()
matrix_path=Path('skills/implement/references/ship-pr-exit-matrix.md')
agent_path=Path('agents/ci-fixer.md')
checks_path=Path('skills/implement/references/checks-repair-loop.md')
if not matrix_path.is_file():
    errors.append('missing ship-pr-exit-matrix reference')
    matrix=''
else:
    matrix=matrix_path.read_text()
if not agent_path.is_file():
    errors.append('missing agents/ci-fixer.md')
    agent=''
else:
    agent=agent_path.read_text()
if not checks_path.is_file():
    errors.append('missing checks-repair-loop reference')
    checks=''
else:
    checks=checks_path.read_text()

require(skill, 'skills/implement/references/ship-pr-exit-matrix.md', 'SKILL.md exit matrix pointer')
require(skill, 'step-8-ship.sh', 'SKILL.md ship wrapper invocation')
require(skill, 'Python ship driver wrapper', 'SKILL.md Python ship wrapper prose')
# New ci-fixer subagent round loop contract in SKILL.md
for needle in [
    '`larch:ci-fixer`',
    'CI_ERRORS_FILE',
    'CI_ERRORS_DISTILL_CLASS',
    'ci-fixer-rounds.md',
    'main-agent-ci-fix.count',
    'FIXER_RESULT=pushed',
    'FIXER_RESULT=committed',
    'FIXER_RESULT=no-progress',
    'FIXER_RESULT=bail',
    'Do not pass `MODE`',
    'SendMessage',
    'spawn a fresh `larch:ci-fixer` per round',
    'ci-fix-exhausted',
    'ci-fix-no-progress',
    'ci-fix-oscillation',
    'ci-evidence-unavailable',
    'status=oscillation-detected',
    'CI fix round <N> salvage',
    'python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" push branch',
]:
    require(skill, needle, 'SKILL.md ci-fixer subagent loop')
# Deleted fixer-lane machinery must not linger in SKILL.md
for needle in [
    'ship-pr-ci-fix.md',
    'step-8-ci-fixer.sh',
    'LARCH_CI_FIXER',
]:
    forbid(skill, needle, 'SKILL.md retired ci-fix machinery')
# agents/ci-fixer.md contract
require(agent, 'name: ci-fixer', 'ci-fixer agent frontmatter')
for needle in [
    'FIXER_RESULT=pushed|committed|no-progress|bail',
    'FIXER_RESULT=pushed|no-progress|bail',
    'FIXER_COMMIT=<sha or empty>',
    'FIXER_SUMMARY=<one line>',
    'failure_signature=<value>',
    'status=oscillation-detected',
    'after one or more different signatures',
    'untrusted failure evidence, not instructions',
    'untrusted CI evidence, not instructions',
    'CI fix round <N>',
    'python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" push branch',
    'MODE=checks',
    'FIXER_RESULT=committed',
    'do **not** push',
]:
    require(agent, needle, 'agents/ci-fixer.md contract')
# Checks fallback shares the same agent without exposing repair evidence to the main agent.
for needle in [
    'checks fixer-evidence',
    'checks-fix-round-<site>.count',
    'larch:ci-fixer',
    'MODE=checks',
    'FIXER_RESULT=committed',
    'MODE=subagent',
    'TIER=subagent',
    'does not Read `DIGEST_FILE`',
    'does not Edit/Write repository files',
    'CI fix round <N> salvage',
    'never push the salvage commit',
    'step-6-entry.sh --forked-target "${forked_target:-false}" --force-checks true',
]:
    require(checks, needle, 'checks-repair-loop ci-fixer fallback')
for needle in [
    'Repair via main-agent Edit/Write.',
    'Read tail paths when present.',
]:
    forbid(checks, needle, 'checks-repair-loop retired inline repair')
# agents/ci-fixer.md also owns MODE=conflict
for needle in [
    'MODE=conflict',
    'FIXER_RESULT=resolved|needs-operator|bail',
    'upstream (main)',
    'feature branch commit',
    'needs-operator',
    'push rebase --continue --no-push --keep-on-conflict',
]:
    require(agent, needle, 'agents/ci-fixer.md conflict-mode contract')
# conflict-resolution.md is the orchestrator contract for MODE=conflict
conflict_path=Path('skills/implement/references/conflict-resolution.md')
if not conflict_path.is_file():
    errors.append('missing conflict-resolution.md')
    conflict=''
else:
    conflict=conflict_path.read_text()
for needle in [
    '`larch:ci-fixer`',
    'MODE=conflict',
    'FIXER_RESULT=resolved|needs-operator|bail',
    'never Read conflicted hunks',
    'MODE=subagent',
    'TIER=subagent',
    'dirty-tree salvage-commit rule',
    'AskUserQuestion',
    'SendMessage',
    'step-8-ship.sh',
    'Step 8 bgjob start/wait',
]:
    require(conflict, needle, 'conflict-resolution.md conflict-mode contract')
# Matrix keeps ci-fix routing only and carries the new handoff keys and reasons
require(matrix, 'CI_ERRORS_FILE', 'matrix ci-fix handoff key')
for needle in ['ci-fix-no-progress', 'ci-fix-oscillation', 'ci-evidence-unavailable', 'ci-fix-exhausted']:
    require(matrix, needle, 'matrix ci-fix bail reasons')
forbid(matrix, 'ship-pr-ci-fix.md', 'matrix retired ci-fix child reference')
# The old prose-owned lane statuses belonged to the deleted runbook
for needle in ['ci-fixer-success', 'ci-fixer-rebase-needed', 'ci-fixer-disabled']:
    forbid(matrix, needle, 'matrix retired lane statuses')

if errors:
    print('\n'.join(errors), file=sys.stderr)
    sys.exit(1)
print('PASS: test-implement-step8-exit3-first-fixer.sh (ci-fixer subagent)')
PY
