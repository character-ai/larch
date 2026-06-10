#!/usr/bin/env bash
# Step 8+ autonomous main-agent CI-fix prose harness.

set -euo pipefail

python3 <<'PY'
from pathlib import Path
import sys
errors=[]
skill=Path('skills/implement/SKILL.md').read_text()
ref_path=Path('skills/implement/references/ship-pr-exit-matrix.md')
if not ref_path.is_file():
    errors.append('missing ship-pr-exit-matrix reference')
    ref=''
else:
    ref=ref_path.read_text()
if 'skills/implement/references/ship-pr-exit-matrix.md' not in skill:
    errors.append('SKILL.md must point to ship-pr-exit-matrix.md')
for needle in ['first-fixer-non-health', 'ci-fix-exhausted', 'autonomous main-agent CI-fix sub-procedure', 'main-agent-ci-fix.count', 'scripts/gh-run-logs.sh', 'scripts/git-push.sh']:
    if needle not in ref:
        errors.append(f'ship-pr exit matrix missing {needle}')
for n in range(1,13):
    if f'  {n}.' not in ref:
        errors.append(f'ship-pr exit matrix missing autonomous sub-step {n}')
if 'Apply the following exit matrix **only when `LARCH_SHIP_PR_IMPL=bash`**' not in ref:
    errors.append('ship-pr exit matrix must retain bash-only gate')
if 'step-8-ship.sh' not in skill:
    errors.append('SKILL.md must invoke step-8-ship.sh')
if 'Python driver selector' not in skill:
    errors.append('SKILL.md must keep Python driver selector prose inline')
if errors:
    print('\n'.join(errors), file=sys.stderr)
    sys.exit(1)
print('PASS: test-implement-step8-exit3-first-fixer.sh (exit matrix reference)')
PY
