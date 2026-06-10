#!/usr/bin/env bash
# Rebase checkpoint macro harness for wrapperized /implement.

set -euo pipefail

python3 <<'PY'
from pathlib import Path
import sys
errors=[]
skill=Path('skills/implement/SKILL.md').read_text()
ref=Path('skills/implement/references/rebase-checkpoint-routing.md').read_text()
probe=Path('scripts/rebase-checkpoint-probe.sh').read_text()
step7a=Path('skills/implement/scripts/step-7a.sh').read_text()

if skill.count('rebase-checkpoint-probe.sh" 1.r') != 1: errors.append('missing one 1.r direct probe call')
if skill.count('rebase-checkpoint-probe.sh" 4.r') != 1: errors.append('missing one 4.r direct probe call')
if skill.count('rebase-checkpoint-probe.sh" 7.r') != 1: errors.append('missing one 7.r direct probe call')
if skill.count("rebase-checkpoint-probe.sh\" 1.r 'plan materialization' --forked-target \"${forked_target:-false}\"") != 1: errors.append('1.r direct probe must pass --forked-target')
if skill.count("rebase-checkpoint-probe.sh\" 4.r 'commit (impl)' --forked-target \"${forked_target:-false}\"") != 1: errors.append('4.r direct probe must pass --forked-target')
if skill.count("rebase-checkpoint-probe.sh\" 7.r 'commit (review)' --forked-target \"${forked_target:-false}\"") != 1: errors.append('7.r direct probe must pass --forked-target')
if 'BASE_ARGS=()' in skill: errors.append('SKILL.md still contains inline BASE_ARGS blocks')
for needle in ['**Orchestrator contract — parse the wrapper stdout**', 'REBASE_OUTCOME=conflict', 'Call-site registry', '7a.r']:
    if needle not in ref: errors.append(f'rebase reference missing {needle}')
if '--forked-target)' not in probe or 'base_remote=upstream' not in probe or 'base_ref=main' not in probe:
    errors.append('rebase-checkpoint-probe.sh does not implement --forked-target upstream/main mapping')
if step7a.count('rebase-checkpoint-probe.sh" 7a.r') != 1:
    errors.append('step-7a.sh must keep one internal 7a.r probe invocation')
if 'BASE_ARGS=(--base-remote "$base_remote" --base-ref "$base_ref")' not in step7a:
    errors.append('step-7a.sh must keep its internal base derivation')
if errors:
    print('\n'.join(errors), file=sys.stderr)
    sys.exit(1)
print('PASS: test-implement-rebase-macro.sh (routing reference + --forked-target calls)')
PY
