#!/usr/bin/env bash
# Rebase checkpoint macro harness for wrapperized /implement.

set -euo pipefail

python3 <<'PY'
from pathlib import Path
import sys
errors=[]
skill=Path('skills/implement/SKILL.md').read_text()
ref=Path('skills/implement/references/rebase-checkpoint-routing.md').read_text()
probe=Path('python/larch/git/push.py').read_text()
bootstrap=Path('python/larch/state/bootstrap.py').read_text()
step7a=Path('skills/implement/scripts/step-7a.sh').read_text()
step7a_py=Path('python/step_7a.py').read_text()

if skill.count('larch-run.sh" python/cli.py push checkpoint-probe 1.r') != 0:
    errors.append('SKILL.md must not call prompt-side 1.r probe')
if '"push"' not in bootstrap or '"checkpoint-probe"' not in bootstrap or '"1.r"' not in bootstrap:
    errors.append('python/larch/state/bootstrap.py must invoke push checkpoint-probe for 1.r')
if 'plan materialization' not in bootstrap:
    errors.append('python/larch/state/bootstrap.py 1.r probe must use plan materialization label')
if '--forked-target' not in bootstrap or 'REBASE_RC' not in bootstrap:
    errors.append('python/larch/state/bootstrap.py must pass --forked-target and synthesize REBASE_RC')
if '"CHECKPOINT_NEXT"' not in bootstrap:
    errors.append('python/larch/state/bootstrap.py must relay CHECKPOINT_NEXT')
if 'CHECKPOINT_NEXT' not in probe or 'load-routing' not in probe:
    errors.append('python/larch/git/push.py must emit CHECKPOINT_NEXT continue/load-routing directives')
for needle in [
    'CHECKPOINT_NEXT=continue|load-routing',
    'CHECKPOINT_NEXT=continue` is the only macro no-op predicate',
    'Missing or malformed `CHECKPOINT_NEXT` fails closed',
    'DEGRADED_PROMPT_REQUIRED=true',
    'The `7a.r` macro skip is `CHECKPOINT_NEXT`-only',
]:
    if needle not in skill:
        errors.append(f'SKILL.md missing CHECKPOINT_NEXT macro contract {needle!r}')
if skill.count('larch-run.sh" python/cli.py push checkpoint-probe 4.r') != 1:
    errors.append('missing one 4.r launcher probe call')
if skill.count('larch-run.sh" python/cli.py push checkpoint-probe 7.r') != 0:
    errors.append('7.r standalone launcher probe call must be folded into the Step 6 composite')
if skill.count("python/cli.py push checkpoint-probe 4.r 'commit (impl)' --forked-target \"${forked_target:-false}\"") != 1:
    errors.append('4.r launcher probe must pass --forked-target')
if skill.count('python/cli.py implement checks-commit-route --checks-site step6 --commit-site step7 --emit-step7-breadcrumb --rebase-checkpoint-7r --forked-target "${forked_target:-false}"') != 1:
    errors.append('Step 6 composite launcher must carry --rebase-checkpoint-7r and --forked-target')
if 'BASE_ARGS=()' in skill:
    errors.append('SKILL.md still contains inline BASE_ARGS blocks')
for needle in [
    '**Orchestrator contract — absorbed `1.r` (Step 0 envelope only)**',
    '**Orchestrator contract — direct probe fences (`4.r`, `7.r`, `7a.r`)**',
    'CHECKPOINT_NEXT=continue|load-routing',
    'CHECKPOINT_NEXT=load-routing',
    'REBASE_OUTCOME=conflict',
    '**⚠ Rebase onto main failed (non-conflict): $REBASE_ERROR. Bailing to cleanup.**',
    '**⚠ Rebase onto main failed unexpectedly',
    'Call-site registry',
    'caller_kind=early_rebase',
    '7a.r',
    'Absorbed Step 1.r',
]:
    if needle not in ref:
        errors.append(f'rebase reference missing {needle}')
if '--forked-target' not in probe or 'base_remote = args.base_remote or ("upstream"' not in probe or 'base_ref = args.base_ref or "main"' not in probe:
    errors.append('python/larch/git/push.py does not implement --forked-target upstream/main mapping')
if 'implement step-7a' not in step7a or 'python/cli.py' not in step7a:
    errors.append('step-7a.sh must delegate to python/cli.py implement step-7a')
if '"push"' not in step7a_py or '"checkpoint-probe"' not in step7a_py or '"7a.r"' not in step7a_py:
    errors.append('python/step_7a.py must keep one internal 7a.r probe invocation')
if '"--base-remote"' not in step7a_py or '"--base-ref"' not in step7a_py or 'base_remote = "upstream"' not in step7a_py:
    errors.append('python/step_7a.py must keep its internal base derivation')
if errors:
    print('\n'.join(errors), file=sys.stderr)
    sys.exit(1)
print('PASS: test-implement-rebase-macro.sh (routing reference + absorbed 1.r + folded 7.r + --forked-target calls)')
PY
