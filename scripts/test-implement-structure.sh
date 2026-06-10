#!/usr/bin/env bash
# High-level /implement prompt structure harness for wrapperized Bash fences.

set -euo pipefail

fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }

python3 <<'PY'
from pathlib import Path
import sys, os
checks = []

def require(path, needle, label):
    text = Path(path).read_text()
    if needle not in text:
        checks.append(f'{label}: missing {needle!r} in {path}')

def forbid(path, needle, label):
    text = Path(path).read_text()
    if needle in text:
        checks.append(f'{label}: forbidden {needle!r} remains in {path}')

skill='skills/implement/SKILL.md'
# New mandatory references.
for ref in ['rebase-checkpoint-routing.md','phantom-probe.md','ship-pr-exit-matrix.md']:
    path=f'skills/implement/references/{ref}'
    if not Path(path).is_file():
        checks.append(f'missing reference {path}')
    else:
        text=Path(path).read_text()
        for header in ['**Consumer**:', '**Contract**:', '**When to load**:']:
            if header not in text:
                checks.append(f'{path} missing {header}')
        require(skill, f'skills/implement/references/{ref}', f'SKILL pointer for {ref}')

# Wrapper call sites.
for script in [
    'step-0-bootstrap.sh" --mode initial',
    'step-0-degraded-gate.sh',
    'step-0-bootstrap.sh" --mode resume',
    'step-2-entry.sh" --coder "$coder"',
    'run-step-checks.sh" --site step3',
    'step-5-entry.sh',
    'run-step-checks.sh" --site step5-self-review',
    'commit-review-fixes.sh" --stage-all',
    'run-step-checks.sh" --site step5-review-fixes',
    'step-5-resume.sh" --final-round-num "$FINAL_ROUND_NUM" --ready-to-commit',
    'step-6-entry.sh',
    'run-step-checks.sh" --site step6',
    'step-8-ship.sh',
    'step-8-oos-checkpoint.sh',
    'step-16.sh',
    'step-17.sh',
    'step-18a-gate.sh',
    'step-18b-final-report.sh" --implement-tmpdir "$IMPLEMENT_TMPDIR"',
    'step-18-finalize.sh',
]:
    require(skill, script, f'SKILL wrapper {script}')

for needle in [
    'BASE_ARGS=()',
    'session read-key --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TOKEN_SESSION_ID',
    '_oos_chk_err=',
    '_restore_finalize=false',
    'if [ "${LARCH_SHIP_PR_IMPL:-python}" != "bash" ]; then',
]:
    forbid(skill, needle, 'wrapperized SKILL')

# Script/md sibling and executable coverage for new wrappers.
wrappers = ['step-0-bootstrap','step-0-degraded-gate','step-2-entry','run-step-checks','step-5-entry','step-5-resume','step-6-entry','step-8-ship','step-8-oos-checkpoint','step-16','step-17','step-18a-gate','step-18-finalize']
for name in wrappers:
    sh=Path(f'skills/implement/scripts/{name}.sh')
    md=Path(f'skills/implement/scripts/{name}.md')
    if not sh.is_file(): checks.append(f'missing {sh}')
    if not md.is_file(): checks.append(f'missing {md}')
    if sh.is_file() and not os.access(sh, os.X_OK): checks.append(f'{sh} is not executable')

# Existing wrappers that gained behavior.
require('skills/implement/scripts/commit-review-fixes.sh', '--stage-all', 'commit-review-fixes --stage-all')
require('skills/implement/scripts/commit-review-fixes.sh', 'git add -A', 'commit-review-fixes stage all implementation')
require('skills/implement/scripts/commit-implementation.sh', 'LARCH_TIMING_LEDGER', 'commit-implementation telemetry self-rehydration')
require('skills/implement/scripts/step-18b-final-report.sh', 'cleanup.sh" --help', 'step-18b cleanup smoke')
require('skills/implement/scripts/step-18b-final-report.sh', 'Step 18 — cleanup', 'step-18b telemetry mark')
require('scripts/rebase-checkpoint-probe.sh', '--forked-target', 'rebase probe forked target flag')
require('scripts/rebase-checkpoint-probe.md', '--forked-target true|false', 'rebase probe docs')
require('Makefile', 'test-implement-fence-shape:', 'Makefile fence-shape target')
require('docs/linting.md', 'make test-implement-fence-shape', 'linting docs fence-shape target')

if checks:
    print('\n'.join(checks), file=sys.stderr)
    sys.exit(1)
print('PASS: test-implement-structure.sh (wrapperized prompt structure)')
PY
