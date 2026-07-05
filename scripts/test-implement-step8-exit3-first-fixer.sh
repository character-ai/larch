#!/usr/bin/env bash
# Step 8+ autonomous main-agent CI-fix prose harness.

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

def require_near(text, before, after, label, limit=900):
    idx=text.find(before)
    if idx < 0:
        errors.append(f'{label}: missing anchor {before!r}')
        return
    window=text[max(0, idx-limit):idx+limit]
    if after not in window:
        errors.append(f'{label}: missing {after!r} near {before!r}')

skill=Path('skills/implement/SKILL.md').read_text()
matrix_path=Path('skills/implement/references/ship-pr-exit-matrix.md')
ci_fix_path=Path('skills/implement/references/ship-pr-ci-fix.md')
if not matrix_path.is_file():
    errors.append('missing ship-pr-exit-matrix reference')
    matrix=''
else:
    matrix=matrix_path.read_text()
if not ci_fix_path.is_file():
    errors.append('missing ship-pr-ci-fix reference')
    ci_fix=''
else:
    ci_fix=ci_fix_path.read_text()

require(skill, 'skills/implement/references/ship-pr-exit-matrix.md', 'SKILL.md exit matrix pointer')
require(skill, 'skills/implement/references/ship-pr-ci-fix.md', 'SKILL.md ci-fix pointer')
require(skill, 'step-8-ship.sh', 'SKILL.md ship wrapper invocation')
require(skill, 'Python ship driver wrapper', 'SKILL.md Python ship wrapper prose')
for needle in [
    '# Ship PR autonomous CI-fix',
    'Python driver non-zero routing',
    'first-fixer-non-health',
    'ci-fix-exhausted',
    '.ship-route-exit-handoff.env',
    'ledger_ready=true',
    'stall-recovery record-escalation',
    'main-agent-ci-fix.count',
    'gh run-logs',
    'python/cli.py" push branch',
    'Make the minimal repo edit',
    'git add --',
    'run-log refresh',
    're-invoke `step-8-ship.sh`',
]:
    require(ci_fix, needle, 'ship-pr-ci-fix.md body')
for n in range(1,13):
    require(ci_fix, f'  {n}.', f'ship-pr-ci-fix.md autonomous sub-step {n}')
for needle in [
    'Python driver non-zero routing',
    'read .ship-route-exit-handoff.env',
    'larch_io.read_kvs',
    'larch.io.read_kvs',
]:
    forbid(matrix, needle, 'ship-pr-exit-matrix.md stripped ci-fix body')
require_near(ci_fix, 'MANDATORY: READ ENTIRE FILE', 're-invoke `step-8-ship.sh`', 'ci-fix procedure read before ship re-entry')

if errors:
    print('\n'.join(errors), file=sys.stderr)
    sys.exit(1)
print('PASS: test-implement-step8-exit3-first-fixer.sh (ci-fix reference)')
PY
