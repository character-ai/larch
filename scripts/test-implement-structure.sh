#!/usr/bin/env bash
# High-level /implement prompt structure harness for wrapperized Bash fences.

set -euo pipefail

fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }

python3 <<'PY'
from pathlib import Path
import re, sys, os
checks = []

def require(path, needle, label):
    text = Path(path).read_text()
    if needle not in text:
        checks.append(f'{label}: missing {needle!r} in {path}')

def forbid(path, needle, label):
    text = Path(path).read_text()
    if needle in text:
        checks.append(f'{label}: forbidden {needle!r} remains in {path}')

def require_near(path, before, after, label, limit=900):
    text = Path(path).read_text()
    idx = text.find(before)
    if idx < 0:
        checks.append(f'{label}: missing anchor {before!r} in {path}')
        return
    window = text[max(0, idx - limit):idx + limit]
    if after not in window:
        checks.append(f'{label}: missing {after!r} near {before!r} in {path}')

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

# Wrapper call sites. The pre-bootstrap Step 0 fences keep the old shape.
for script in [
    'step-0-bootstrap.sh" --mode initial',
    'step-0-bootstrap.sh" --mode resume',
]:
    require(skill, script, f'SKILL old-shape wrapper {script}')

# Collapsed Preflight helper surface.
for path in [
    'scripts/implement-preflight.sh',
    'scripts/implement-preflight.md',
    'scripts/test-implement-preflight.sh',
    'scripts/test-implement-preflight.md',
]:
    if not Path(path).is_file():
        checks.append(f'missing {path}')
require(skill, 'scripts/implement-preflight.sh', 'SKILL implement-preflight reference')
require(skill, 'bash "${CLAUDE_PLUGIN_ROOT}/scripts/implement-preflight.sh"', 'SKILL implement-preflight bash invocation')
require(skill, '$PREFLIGHT_TMPDIR/issue.json', 'SKILL preflight issue json path')
require(skill, '$PREFLIGHT_TMPDIR/plan-from-issue.txt', 'SKILL preflight plan path')
require(skill, 'PLAN_PATH', 'SKILL PLAN_PATH envelope binding')
require(skill, 'ISSUE_JSON_PATH', 'SKILL ISSUE_JSON_PATH envelope binding')
require(skill, 'one `KEY=value` record per line', 'SKILL one-record envelope')
require(skill, 'Split each envelope line at the first `=` only', 'SKILL first-equals parser')
require(skill, 'Require `RESUME` to be exactly `true` or `false`.', 'SKILL resume boolean parser')
require(skill, 'Do not accept `RESUME=empty`.', 'SKILL no resume empty token')
require(skill, 'On non-zero exit, abort before item 4', 'SKILL nonzero preflight abort')
require(skill, 'Do not parse or require an envelope on non-zero exit.', 'SKILL no exit2 envelope parse')
require(skill, 'Run `admission fork-env`, then the preflight helper, then Step 0 bootstrap.', 'SKILL forked ordering')
require('scripts/implement-preflight.md', 'Emit one `KEY=value` record per line.', 'preflight docs one-record envelope')
require('scripts/implement-preflight.md', 'Emit `RESUME=true` only when admission stdout contains exactly `RESUME=true`.', 'preflight docs resume true')
require('scripts/implement-preflight.md', 'Emit `RESUME=false` when admission stdout lacks `RESUME=`.', 'preflight docs resume false')
require('scripts/implement-preflight.md', 'Emit the envelope only on successful exit `0`.', 'preflight docs success-only envelope')
require('scripts/implement-preflight.md', 'Source the final success-envelope `TITLE` from `issue.json`, not admission stdout.', 'preflight docs title source')
require('scripts/implement-preflight.md', 'Use Python stdlib `json`', 'preflight docs stdlib json')
require('scripts/implement-preflight.md', 'Capture admission stdout before branching on the admission return code.', 'preflight docs admission parse before rc')
require('scripts/implement-preflight.md', 'BLOCKERS=<value>', 'preflight docs blockers echo')
require('scripts/implement-preflight.md', 'TITLE=<value>', 'preflight docs title echo')
require('scripts/implement-preflight.md', '$PREFLIGHT_TMPDIR/emergency-bypass.log', 'preflight docs bypass log destination')
forbid(skill, '${emergency_requested:+--emergency}', 'SKILL preflight emergency argv')
forbid(skill, 'If `false` and `emergency_requested=false`, print `**❌ Issue #<N> has no larch:plan block', 'SKILL prompt-side missing-plan fallback prose')
forbid(skill, 'If the script exits **1** and prints `MALFORMED=...`, then when `emergency_requested=false`', 'SKILL prompt-side malformed-plan fallback prose')
forbid(skill, 'single-line envelope', 'SKILL must not describe single-line envelope')
forbid(skill, 'full seven-key envelope', 'SKILL must not require envelope on exit 2')


launcher = 'bash "$IMPLEMENT_TMPDIR/larch-run.sh" '
for script in [
    'skills/implement/scripts/step-2-entry.sh --coder "$coder"',
    'skills/implement/scripts/run-step-checks.sh --site step3',
    'skills/implement/scripts/step-5-entry.sh',
    'skills/implement/scripts/run-step-checks.sh --site step5-self-review',
    'skills/implement/scripts/commit-review-fixes.sh --stage-all',
    'scripts/run-step5-review.sh --implement-tmpdir "$IMPLEMENT_TMPDIR" --mode loop --starting-round 1',
    'skills/implement/scripts/run-step-checks.sh --site step5-review-fixes',
    'skills/implement/scripts/step-5-resume.sh --final-round-num "$FINAL_ROUND_NUM" --record-only',
    'skills/implement/scripts/step-5-resume.sh --final-round-num "$FINAL_ROUND_NUM" --ready-to-commit',
    'skills/implement/scripts/step-6-entry.sh',
    'skills/implement/scripts/run-step-checks.sh --site step6',
    'skills/implement/scripts/step-7a.sh --implement-tmpdir "$IMPLEMENT_TMPDIR"',
    'skills/implement/scripts/step-8-ship.sh',
    'skills/implement/scripts/step-8-oos-checkpoint.sh',
    'skills/implement/scripts/step-16.sh',
    'skills/implement/scripts/step-17.sh',
    'skills/implement/scripts/step-18a-gate.sh --stall-tracking-memory "${STALL_TRACKING:-false}"',
    'skills/implement/scripts/step-18b-final-report.sh --implement-tmpdir "$IMPLEMENT_TMPDIR"',
    'skills/implement/scripts/step-18-finalize.sh',
]:
    require(skill, launcher + script, f'SKILL launcher wrapper {script}')

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
require('python/bootstrap.py', 'preflight-tmpdir.env', 'bootstrap preflight tmpdir persistence')
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
for script, timeout in [
    (launcher + 'scripts/run-step5-review.sh', 'timeout: 21600000'),
    (launcher + 'skills/implement/scripts/step-7a.sh', 'timeout: 1800000'),
    (launcher + 'skills/implement/scripts/step-8-ship.sh', 'timeout: 21600000'),
]:
    require_near(skill, script, 'Immediate-background required', f'immediate-background pin for {script}', 1400)
    require_near(skill, script, timeout, f'timeout pin for {script}', 1400)
require_near(skill, launcher + 'scripts/run-step5-review.sh', '<task-notification>', 'Step 5 review task notification wait', 1800)
require_near(skill, launcher + 'skills/implement/scripts/step-8-ship.sh', '<task-notification>', 'Step 8 ship task notification wait', 2000)
require(skill, launcher + 'scripts/phantom-probe-with-warn.sh --step 2-post-dispatch', 'phantom 2-post-dispatch probe')
require(skill, launcher + 'scripts/phantom-probe-with-warn.sh --step 8-pre-ship', 'phantom 8-pre-ship probe')
require(skill, 'git-current-branch.sh', 'post-dispatch branch assertion')
rebase_ref = Path('skills/implement/references/rebase-checkpoint-routing.md').read_text()
for needle in [
    '**Orchestrator contract — absorbed `1.r` (Step 0 envelope only)**',
    '**Orchestrator contract — direct probe fences (`4.r`, `7.r`, `7a.r`)**',
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

skill_text = Path(skill).read_text()
if skill_text.count('timeout: 10800000') < 4:
    checks.append('SKILL.md must use the 10800000 timeout tier for all run-step-checks fences')
if not re.search(r'timeout: 21600000`\.\*\*\s+```bash\s+bash "\$IMPLEMENT_TMPDIR/larch-run\.sh" skills/implement/scripts/step-5-resume\.sh --final-round-num "\$FINAL_ROUND_NUM" --ready-to-commit', skill_text):
    checks.append('SKILL.md must background the Step 5 ready-to-commit resume fence with timeout 21600000')
if re.search(r'(^|[\s])--auto([^A-Za-z0-9_-]|$)', skill_text):
    checks.append('SKILL.md must not document standalone --auto flag token (issue #2497)')
if '--auto-mode' in skill_text:
    checks.append('SKILL.md must not document --auto-mode flag (issue #2497)')
for ref in [
    'summary-comment-template.md', 'conflict-resolution.md', 'codex-manifest-schema.md',
    'pr-body-template.md', 'step5-review-branches.md',
]:
    path = f'skills/implement/references/{ref}'
    if not Path(path).is_file():
        checks.append(f'missing reference {path}')
require(skill, 'references/step5-review-branches.md', 'Step 5 review branches pointer')
conflict_ref = Path('skills/implement/references/conflict-resolution.md')
if conflict_ref.is_file():
    conflict_text = conflict_ref.read_text()
    for needle in ['caller_kind=ship_pr_pre_push', 'caller_kind=early_rebase']:
        if needle not in conflict_text:
            checks.append(f'conflict-resolution.md missing {needle!r}')
    for needle in [
        '${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-8-ship.sh',
        'run_in_background: true',
        'timeout: 21600000',
        '<task-notification>',
    ]:
        if needle not in conflict_text:
            checks.append(f'conflict-resolution.md missing Step 8 wrapper re-entry contract {needle!r}')
    for forbidden in [
        'default Python foreground argv',
        'Python foreground argv',
        'foreground `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" ship pr`',
        're-invoke `${CLAUDE_PLUGIN_ROOT}/scripts/ship-pr.sh --resume-phase ship-pr-rrr-phase14`',
    ]:
        if forbidden in conflict_text:
            checks.append(f'conflict-resolution.md must not use direct foreground ship re-entry prose {forbidden!r}')
require(skill, 'step-0-bootstrap.sh" --mode initial', 'Step 0 initial bootstrap wrapper')
require(skill, 'step-0-bootstrap.sh" --mode resume', 'Step 0 resume bootstrap wrapper')
require('skills/implement/scripts/step-0-bootstrap.sh', 'set +e', 'step-0 bootstrap set +e guard')
require('python/bootstrap.py', 'preserve_coder=args.resume == "true"', 'bootstrap parse-routing resume preserves coder')
forbid(skill, launcher + 'skills/implement/scripts/step-0-degraded-gate.sh', 'SKILL active flow must not call step-0-degraded-gate.sh')
require('python/bootstrap.py', 'degraded-tools-gate', 'bootstrap absorbed degraded gate')
require('python/bootstrap.py', 'rebase-checkpoint-probe.sh', 'bootstrap absorbed 1.r probe')
require('python/bootstrap.py', 'DEGRADED_PROMPT_REQUIRED', 'bootstrap degraded prompt routing')
require('python/bootstrap.py', 'REBASE_RC', 'bootstrap rebase rc synthesis')
require('python/bootstrap.py', '_ADVISORY_STDOUT_PREFIXES', 'bootstrap phantom advisory allowlist')
require(skill, 'DEGRADED_PROMPT_REQUIRED=true', 'SKILL degraded prompt route row')
for needle in [
    'agent degraded-tools-gate', '--codex-present', '--cursor-present',
    'read_session_key CODEX_PRESENT', 'read_session_key CURSOR_PRESENT',
    'read_session_key CODEX_BINARY_FOUND', 'read_session_key CURSOR_BINARY_FOUND',
]:
    require('skills/implement/scripts/step-0-degraded-gate.sh', needle, f'step-0-degraded-gate legacy {needle}')
require('skills/implement/scripts/step-5-resume.sh', 'commit-review-fixes.sh" --stage-all || true', 'step-5-resume commit failure guard')
require('skills/implement/scripts/step-5-resume.sh', 'run-step5-review.sh', 'step-5-resume review loop resume')
require('scripts/ship-pr.sh', 'pr-create) advance_phase pr-prep; state_set RESUME_PHASE ""', 'ship-pr pr-create resume token consumption')
exit_matrix = Path('skills/implement/references/ship-pr-exit-matrix.md')
if exit_matrix.is_file():
    exit_text = exit_matrix.read_text()
    for needle in [
        'Apply the following exit matrix **only when `LARCH_SHIP_PR_IMPL=bash`**',
        'Phase 4 exit 0 re-invokes the active Step 8+ selector',
        'ship-pr-net-retries-python.count',
        'RESUME_PHASE=pr-create',
        'Read `RESUME_PHASE`, `CALLER_KIND`, and `CONFLICT_FILES` from `ship-pr-state.sh` on both paths.',
    ]:
        if needle not in exit_text:
            checks.append(f'ship-pr-exit-matrix.md missing {needle!r}')
require(skill, 'skills/implement/references/ship-pr-exit-matrix.md', 'ship-pr exit matrix pointer')
stall_ref = Path('skills/implement/references/stall-recovery.md').read_text()
for needle in [
    'step-8-ship.sh',
    'run_in_background: true',
    'timeout: 21600000',
    '<task-notification>',
    'Dispatch by `RESUME_HINT`',
    '`step2-impl` means record escalation before edits, then Main Claude reads `$IMPLEMENT_TMPDIR/plan.txt` and implements inline',
    '`step8-shippr` is the only retry branch that re-invokes `${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-8-ship.sh`',
]:
    if needle not in stall_ref:
        checks.append(f'stall-recovery.md missing {needle!r}')
if 'python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" ship pr` with the Step 8+ argv' in stall_ref:
    checks.append('stall-recovery.md must not re-enter ship via direct python/cli.py prose')
require(skill, 're-invoke `${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-8-ship.sh` per the selector', 'NEVER #13 default-path wrapper re-entry')
for needle in [
    '_restore_finalize=false',
    'restore-finalize-state',
    'implement-finalize.sh" teardown',
    'LARCH_SHIP_PR_IMPL:-python}" = "bash"',
    'DESIGN_TMPDIR=\'\' LARCH_TIMING_SKILL=implement',
]:
    require('skills/implement/scripts/step-18-finalize.sh', needle, f'step-18-finalize {needle}')
for needle in [
    'default `LARCH_SHIP_PR_IMPL=python` runs the Python branch',
    'Python driver selector',
    'Unless `LARCH_SHIP_PR_IMPL=bash`, the `step-8-ship.sh` wrapper runs',
    '## Load-Bearing Invariants',
    'Two invariants enforced across multiple steps',
]:
    if needle not in skill_text:
        checks.append(f'SKILL.md missing {needle!r}')
for retired in [
    'Version Bump Freshness', 'Degraded-Git Fail-Closed', '### Step 8a',
    'phantom-probe-with-warn.sh" --step 8-pre-bump',
    'default `LARCH_SHIP_PR_IMPL=bash` runs the bash contract',
]:
    if retired in skill_text:
        checks.append(f'SKILL.md must not retain retired surface {retired!r}')
require('skills/implement/scripts/step-8-oos-checkpoint.sh', 'command grep', 'step-8-oos-checkpoint command grep probes')
require('skills/implement/scripts/step-8-oos-checkpoint.sh', 'OOS_CHECKPOINT_RC', 'step-8-oos-checkpoint rc relay')

# Step 4 skip prose must reference commit-implementation.sh, not git-commit.sh.
require(skill, 'Skip the `commit-implementation.sh` invocation.', 'Step 4 skip prose references commit-implementation.sh')
forbid(skill, 'Skip the `git-commit.sh` invocation.', 'Step 4 skip prose must not reference git-commit.sh')
# The fabricated path skills/implement/scripts/git-commit.sh must not appear under skills/implement/.
import subprocess
r = subprocess.run(
    ['git', 'grep', '-rl', 'skills/implement/scripts/git-commit.sh', '--', 'skills/implement/'],
    capture_output=True, text=True
)
if r.stdout.strip():
    checks.append(f'fabricated path skills/implement/scripts/git-commit.sh referenced under skills/implement/: {r.stdout.strip()}')

if checks:
    print('\n'.join(checks), file=sys.stderr)
    sys.exit(1)
print('PASS: test-implement-structure.sh (wrapperized prompt structure)')
PY
