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
    'step-5-resume.sh" --final-round-num "$FINAL_ROUND_NUM" --record-only',
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
require('skills/implement/scripts/step-0-bootstrap.sh', 'CALLER_ENV_PATH=*) CALLER_ENV_PATH=', 'step-0 fork metadata caller-env parse')
require('skills/implement/scripts/step-0-bootstrap.sh', 'UPSTREAM_REPO=*) UPSTREAM_REPO=', 'step-0 fork metadata upstream parse')
require('skills/implement/scripts/step-0-bootstrap.sh', 'preflight-tmpdir.env', 'step-0 preflight tmpdir resume persistence')
require('skills/implement/scripts/step-0-bootstrap.sh', 'read_session_key FORKED_TARGET', 'step-0 resume fork metadata rehydration')
require('scripts/implement-bootstrap.sh', 'preflight-tmpdir.env', 'bootstrap preflight tmpdir persistence')
require('skills/implement/scripts/step-8-ship.sh', 'read_state_key', 'step-8 ship state rehydration')
require('skills/implement/scripts/step-8-ship.sh', 'sys.version_info >= (3, 11)', 'step-8 python 3.11 guard')
require('skills/implement/scripts/step-8-ship.sh', '"outcome":"STALLED"', 'step-8 stalled JSON stdout')
require('skills/implement/scripts/step-8-ship.sh', 'exit 4', 'step-8 stale-python exit 4')
require('skills/implement/scripts/step-8-ship.sh', '${_resume_args[@]+"${_resume_args[@]}"}', 'step-8 bash32-safe resume args')
require('skills/implement/scripts/step-0-bootstrap.sh', 'LARCH_CLAUDE_PID="${LARCH_CLAUDE_PID:-$PPID}"', 'step-0 wrapper claude pid export')
require('skills/implement/scripts/step-18-finalize.sh', 'LARCH_CLAUDE_PID:-$PPID', 'step-18-finalize claude pid fallback')
require('skills/implement/scripts/step-18a-gate.sh', 'STALL_TRACKING_MEMORY_ARG', 'step-18a stall-tracking memory arg')
require('skills/implement/scripts/step-18a-gate.sh', 'STALL_TRACKING_DISK=', 'step-18a stall disk layer')
require('skills/implement/scripts/step-18a-gate.sh', 'STALL_TRACKING_FINALIZE=', 'step-18a stall finalize layer')
require('skills/implement/scripts/step-18a-gate.sh', 'STALL_TRACKING_SESSION=', 'step-18a stall session layer')
require(skill, 'NO_ADMIN_FALLBACK=$no_admin_fallback', 'ship state no-admin fallback persistence')
require(skill, '## NEVER List', 'NEVER list heading')
require(skill, 'NEVER call `ScheduleWakeup`', 'NEVER #8 ScheduleWakeup pin')
require(skill, 'Do not spawn a Monitor', 'NEVER #8 background-monitor ban')
require(skill, 'phantom-probe-with-warn.sh" --step 2-post-dispatch', 'phantom 2-post-dispatch probe')
require(skill, 'phantom-probe-with-warn.sh" --step 8-pre-ship', 'phantom 8-pre-ship probe')
require(skill, 'git-current-branch.sh', 'post-dispatch branch assertion')
rebase_ref = Path('skills/implement/references/rebase-checkpoint-routing.md').read_text()
for needle in [
    '**Orchestrator contract — parse the wrapper stdout**',
    'REBASE_OUTCOME=conflict',
    '**⚠ Rebase onto main failed (non-conflict): $REBASE_ERROR. Bailing to cleanup.**',
    '**⚠ Rebase onto main failed unexpectedly',
    'Call-site registry',
    'caller_kind=early_rebase',
]:
    if needle not in rebase_ref:
        checks.append(f'rebase-checkpoint-routing.md missing {needle!r}')
phantom_ref = Path('skills/implement/references/phantom-probe.md').read_text()
for needle in ['2-post-dispatch', '8-pre-ship', 'Do not probe when `STATUS=claude_fallback`']:
    if needle not in phantom_ref:
        checks.append(f'phantom-probe.md missing {needle!r}')
require('scripts/rebase-checkpoint-probe.sh', '--forked-target', 'rebase probe forked target flag')
require('scripts/rebase-checkpoint-probe.md', '--forked-target true|false', 'rebase probe docs')
require('Makefile', 'test-implement-fence-shape:', 'Makefile fence-shape target')
require('docs/linting.md', 'make test-implement-fence-shape', 'linting docs fence-shape target')

if checks:
    print('\n'.join(checks), file=sys.stderr)
    sys.exit(1)
print('PASS: test-implement-structure.sh (wrapperized prompt structure)')
PY
