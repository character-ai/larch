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
    'skills/implement/scripts/step-2-post-dispatch.sh',
    'skills/implement/scripts/run-step-checks.sh --site step3',
    'skills/implement/scripts/step-5-review.sh',
    'skills/implement/scripts/run-step-checks.sh --site step5-self-review',
    'python/cli.py review-and-fix commit-fixes --stage-all',
    'skills/implement/scripts/run-step-checks.sh --site step5-review-fixes',
    'skills/implement/scripts/step-5-resume.sh --final-round-num "$FINAL_ROUND_NUM" --record-only',
    'skills/implement/scripts/step-5-resume.sh --final-round-num "$FINAL_ROUND_NUM" --ready-to-commit',
    'skills/implement/scripts/step-6-entry.sh',
    'skills/implement/scripts/run-step-checks.sh --site step6',
    'python/cli.py implement step-7a --implement-tmpdir "$IMPLEMENT_TMPDIR"',
    'skills/implement/scripts/step-8-python-guard.sh',
    'skills/implement/scripts/step-8-seed-initial.sh',
    'skills/implement/scripts/step-8-ship.sh',
    'skills/implement/scripts/step-8-oos-checkpoint.sh',
    'skills/implement/scripts/step-16-17.sh',
    'skills/implement/scripts/step-18a-gate.sh --stall-tracking-memory "${STALL_TRACKING:-false}"',
    'python/cli.py final-report step18b --implement-tmpdir "$IMPLEMENT_TMPDIR"',
    'skills/implement/scripts/step-18-finalize.sh',
]:
    require(skill, launcher + script, f'SKILL launcher wrapper {script}')

for needle in [
    'BASE_ARGS=()',
    'session read-key --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TOKEN_SESSION_ID',
    '_oos_chk_err=',
    '_restore_finalize=false',
]:
    forbid(skill, needle, 'wrapperized SKILL')

# Script/md sibling and executable coverage for new wrappers.
wrappers = ['step-0-bootstrap','step-0-degraded-gate','step-2-entry','step-2-post-dispatch','run-step-checks','step-5-review','step-5-resume','step-6-entry','step-8-python-guard','step-8-seed-initial','step-8-ship','step-8-oos-checkpoint','step-16','step-16-17','step-17','step-18a-gate','step-18-finalize']
for name in wrappers:
    sh=Path(f'skills/implement/scripts/{name}.sh')
    md=Path(f'skills/implement/scripts/{name}.md')
    if not sh.is_file(): checks.append(f'missing {sh}')
    if not md.is_file(): checks.append(f'missing {md}')
    if sh.is_file() and not os.access(sh, os.X_OK): checks.append(f'{sh} is not executable')

# Existing wrappers that gained behavior.
require('skills/implement/scripts/step-5-review.sh', 'review-and-fix step5', 'step-5-review calls review-and-fix step5')
retired_step5_entry_sh = 'skills/implement/scripts/' + 'step-5-entry.sh'
retired_step5_entry_md = 'step-5-' + 'entry.md'
forbid(skill, retired_step5_entry_sh, 'retired step-5-entry.sh call removed from SKILL')
forbid(skill, retired_step5_entry_md, 'retired step-5-entry.md ref removed from SKILL')
require('python/review_and_fix.py', '--stage-all', 'commit-fixes --stage-all')
require('python/review_and_fix.py', '"git", "add", "-A"', 'commit-fixes stage all implementation')
require('python/implement_dispatch.py', 'LARCH_TIMING_LEDGER', 'commit-implementation telemetry self-rehydration')
require('skills/implement/scripts/step-18b-final-report.sh', 'cleanup.sh" --help', 'step-18b cleanup smoke')
require('skills/implement/scripts/step-18b-final-report.sh', 'Step 18 — cleanup', 'step-18b telemetry mark')
require('skills/implement/scripts/step-0-bootstrap.sh', 'CALLER_ENV_PATH=*) CALLER_ENV_PATH=', 'step-0 fork metadata caller-env parse')
require('skills/implement/scripts/step-0-bootstrap.sh', 'UPSTREAM_REPO=*) UPSTREAM_REPO=', 'step-0 fork metadata upstream parse')
require('skills/implement/scripts/step-0-bootstrap.sh', 'preflight-tmpdir.env', 'step-0 preflight tmpdir resume persistence')
require('skills/implement/scripts/step-0-bootstrap.sh', 'read_session_key FORKED_TARGET', 'step-0 resume fork metadata rehydration')
require('python/bootstrap.py', 'preflight-tmpdir.env', 'bootstrap preflight tmpdir persistence')
require('skills/implement/scripts/step-8-ship.sh', 'read_state_key', 'step-8 ship state rehydration')
require('skills/implement/scripts/step-8-python-guard.sh', 'sys.version_info >= (3, 11)', 'step-8 shared python 3.11 guard')
require('skills/implement/scripts/step-8-python-guard.sh', '"outcome":"STALLED"', 'step-8 shared stalled JSON stdout')
require('skills/implement/scripts/step-8-python-guard.sh', 'exit 4', 'step-8 shared stale-python exit 4')
require('skills/implement/scripts/step-8-ship.sh', 'step-8-python-guard.sh', 'step-8 ship delegates python guard')
require('skills/implement/scripts/step-8-ship.sh', 'lib-implement-clone-tag.sh', 'step-8 ship uses clone-tag helper')
require('skills/implement/scripts/step-8-ship.sh', 'python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" ship pr', 'step-8 python ship invocation')
require('skills/implement/scripts/step-0-bootstrap.sh', 'LARCH_CLAUDE_PID="${LARCH_CLAUDE_PID:-$PPID}"', 'step-0 wrapper claude pid export')
require('skills/implement/scripts/step-18-finalize.sh', 'LARCH_CLAUDE_PID:-$PPID', 'step-18-finalize claude pid fallback')
require('skills/implement/scripts/step-18a-gate.sh', 'STALL_TRACKING_MEMORY_ARG', 'step-18a stall-tracking memory arg')
require('skills/implement/scripts/step-18a-gate.sh', 'STALL_TRACKING_DISK=', 'step-18a stall disk layer')
require('skills/implement/scripts/step-18a-gate.sh', 'STALL_TRACKING_FINALIZE=', 'step-18a stall finalize layer')
require('skills/implement/scripts/step-18a-gate.sh', 'STALL_TRACKING_SESSION=', 'step-18a stall session layer')
require(skill, 'python/cli.py ship seed-initial-state', 'ship state initial seeder authority')
require('skills/implement/scripts/step-8-seed-initial.sh', '--no-admin-fallback', 'ship state no-admin fallback seeder argv')
require('python/ship.py', 'NO_ADMIN_FALLBACK', 'ship state no-admin fallback allowed key')
require(skill, '## NEVER List', 'NEVER list heading')
require(skill, 'NEVER call `ScheduleWakeup`', 'NEVER #8 ScheduleWakeup pin')
require(skill, 'Do not spawn a Monitor', 'NEVER #8 background-monitor ban')
for script, timeout in [
    (launcher + 'skills/implement/scripts/step-5-review.sh', 'timeout: 21600000'),
    (launcher + 'python/cli.py implement step-7a', 'timeout: 1800000'),
    (launcher + 'skills/implement/scripts/step-8-ship.sh', 'timeout: 21600000'),
]:
    require_near(skill, script, 'Immediate-background required', f'immediate-background pin for {script}', 1400)
    require_near(skill, script, timeout, f'timeout pin for {script}', 1400)
require_near(skill, launcher + 'skills/implement/scripts/step-5-review.sh', '<task-notification>', 'Step 5 review task notification wait', 1800)
require_near(skill, launcher + 'skills/implement/scripts/step-8-ship.sh', '<task-notification>', 'Step 8 ship task notification wait', 2000)

require(skill, 'PHASE=checks` and `PR_NUMBER` is empty/absent', 'SKILL pre-driver predicate checks phase and empty pr')
require(skill, 'Seeded-but-no-PR state is still pre-driver', 'SKILL seeded no-pr retry stays pre-driver')
require(skill, 'pre-driver retry reruns guard and `oos file`', 'SKILL pre-driver retry reruns oos file')
forbid(skill, 'write-initial-state-keys:begin', 'SKILL initial state marker removed')
forbid(skill, 'sys.version_info >= (3, 11)', 'SKILL inline python version guard removed')
forbid(skill, 'python/cli.py ship seed-initial-state --tmpdir', 'SKILL direct seeder invocation removed')
require('skills/implement/references/step5-review-branches.md', 'step-8-seed-initial.sh --stall-tracking "$STALL_TRACKING" --stall-step 5', 'Step 5 stall seeder wrapper')
require('skills/implement/references/step5-review-branches.md', '--merge false --draft false', 'Step 5 stall merge draft false')
require('python/bootstrap.py', 'ship-seed-input.env', 'bootstrap ship seed input writer')
require(skill, launcher + 'skills/implement/scripts/step-2-post-dispatch.sh', 'phantom 2-post-dispatch probe')
require(skill, 'regardless of wrapper exit code', 'post-dispatch phantom parse before wrapper routing')
require('skills/implement/scripts/step-8-ship.sh', 'phantom-probe-with-warn.sh --step 8-pre-ship', 'phantom 8-pre-ship probe moved into ship wrapper')
forbid(skill, launcher + 'scripts/phantom-probe-with-warn.sh --step 8-pre-ship', 'standalone orchestrator 8-pre-ship fence removed')
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
for needle in ['2-post-dispatch', 'step-2-post-dispatch.sh', '8-pre-ship', 'Do not probe when `STATUS=claude_fallback`']:
    if needle not in phantom_ref:
        checks.append(f'phantom-probe.md missing {needle!r}')
require('scripts/rebase-checkpoint-probe.sh', '--forked-target', 'rebase probe forked target flag')
require('scripts/rebase-checkpoint-probe.md', '--forked-target true|false', 'rebase probe docs')
require('Makefile', 'test-implement-fence-shape:', 'Makefile fence-shape target')
require('docs/linting.md', 'make test-implement-fence-shape', 'linting docs fence-shape target')

skill_text = Path(skill).read_text()
# LARCH_FINAL_SUMMARY_BEGIN/END must not appear inside bash fences in implement SKILL.md
text_impl = Path(skill).read_text()
in_fence = False
fence_has_marker = False
for line in text_impl.splitlines():
    stripped = line.strip()
    if stripped == '```bash':
        in_fence = True
    elif stripped == '```':
        in_fence = False
    elif in_fence and ('LARCH_FINAL_SUMMARY_BEGIN' in line or 'LARCH_FINAL_SUMMARY_END' in line):
        fence_has_marker = True
        break
if fence_has_marker:
    checks.append('SKILL.md bash fence must not reference LARCH_FINAL_SUMMARY_BEGIN or LARCH_FINAL_SUMMARY_END')

# Step 17 marker handoff contract must exist.
require('skills/implement/scripts/step-16-17.sh', '---LARCH-SUMMARY-FINAL-BEGIN---', 'step-16-17 begin marker literal')
require('skills/implement/scripts/step-16-17.sh', '---LARCH-SUMMARY-FINAL-END---', 'step-16-17 end marker literal')
require(skill, 'extract the first balanced whole-line `---LARCH-SUMMARY-FINAL-BEGIN---` / `---LARCH-SUMMARY-FINAL-END---` pair from captured wrapper output', 'SKILL marker extraction contract')
require(skill, 'emit the extracted body verbatim as plain chat markdown', 'SKILL marker body plain-chat emission')
require(skill, 'do not Read that file on the Step 17 primary path', 'SKILL no Read-tool Step 17 primary path')
require(skill, 'When `EMIT_BODY=true` and `WFR_RC=0` and `[ -s "$IMPLEMENT_TMPDIR/summary-final.md" ]`', 'SKILL Step 18b Read fallback retained')
require('skills/implement/scripts/step-16-17.sh', 'touch "$IMPLEMENT_TMPDIR/.step17-printed"', 'step-16-17 owns .step17-printed')
require(skill, 'Write `$IMPLEMENT_TMPDIR/.step17-emitted` only after that plain-chat emission.', 'SKILL .step17-emitted orchestrator ownership')
require('skills/implement/scripts/step-16-17.sh', 'if [ "$STEP17_RC" -eq 0 ] && [ -s "$IMPLEMENT_TMPDIR/summary-final.md" ]; then', 'step-16-17 marker gate uses Step 17 rc and non-empty summary')
require(skill, 'Marker emission is gated on captured Step 17 render success and a non-empty `summary-final.md`, not `summary-final.md` presence alone.', 'SKILL stale-summary marker gate')
forbid(skill, 'Do NOT use a Bash `cat` or Python tool call to print the summary body', 'retired Step 17 Bash-cat prohibition string')
forbid(skill, 'via Bash `cat` whose output is then re-emitted as orchestrator text', 'SKILL must not sanction Bash cat for summary emit')

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
        're-invoke `${CLAUDE_PLUGIN_ROOT}/python/cli.py ship pr --resume-phase ship-pr-rrr-phase14`',
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
    'agent check-reviewers',
    'read_session_key CODEX_BINARY_FOUND', 'read_session_key CURSOR_BINARY_FOUND',
]:
    require('skills/implement/scripts/step-0-degraded-gate.sh', needle, f'step-0-degraded-gate legacy {needle}')
require('skills/implement/scripts/step-5-resume.sh', 'review-and-fix commit-fixes --stage-all || true', 'step-5-resume commit failure guard')
require('skills/implement/scripts/step-5-resume.sh', 'review-and-fix step5', 'step-5-resume review loop resume')
require('skills/implement/scripts/step-8-ship.sh', '--state-file "$IMPLEMENT_TMPDIR/ship-pr-state.sh"', 'step-8 state file forwarding')
exit_matrix = Path('skills/implement/references/ship-pr-exit-matrix.md')
if exit_matrix.is_file():
    exit_text = exit_matrix.read_text()
    for needle in [
        'Python driver non-zero routing',
        'Phase 4 exit 0 re-invokes the active Step 8+ selector',
        'ship-pr-net-retries-python.count',
        'Read `CONFLICT_FILES` from `ship-pr-state.sh` on conflict handoff paths.',
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
require(skill, 'every Step 8+ re-entry goes through `${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-8-ship.sh` only', 'NEVER #13 default-path wrapper re-entry')
for needle in [
    '_restore_finalize=false',
    'restore-finalize-state',
    'implement-finalize teardown',
    'DESIGN_TMPDIR=\'\' LARCH_TIMING_SKILL=implement',
]:
    require('skills/implement/scripts/step-18-finalize.sh', needle, f'step-18-finalize {needle}')
for needle in [
    'Python ship driver wrapper',
    '## Load-Bearing Invariants',
    'Two invariants enforced across multiple steps',
]:
    if needle not in skill_text:
        checks.append(f'SKILL.md missing {needle!r}')
for retired in [
    'Version Bump Freshness', 'Degraded-Git Fail-Closed', '### Step 8a',
    'phantom-probe-with-warn.sh" --step 8-pre-bump',
]:
    if retired in skill_text:
        checks.append(f'SKILL.md must not retain retired surface {retired!r}')
require('skills/implement/scripts/step-8-oos-checkpoint.sh', 'command grep', 'step-8-oos-checkpoint command grep probes')
require('skills/implement/scripts/step-8-oos-checkpoint.sh', 'OOS_CHECKPOINT_RC', 'step-8-oos-checkpoint rc relay')

# Step 4 skip prose must reference implement commit, not git-commit.sh.
require(skill, 'Skip the `implement commit` invocation.', 'Step 4 skip prose references implement commit')
forbid(skill, 'Skip the `git-commit.sh` invocation.', 'Step 4 skip prose must not reference git-commit.sh')
# The fabricated path skills/implement/scripts/git-commit.sh must not appear under skills/implement/.
import subprocess
r = subprocess.run(
    ['git', 'grep', '-rl', 'skills/implement/scripts/git-commit.sh', '--', 'skills/implement/'],
    capture_output=True, text=True
)
if r.stdout.strip():
    checks.append(f'fabricated path skills/implement/scripts/git-commit.sh referenced under skills/implement/: {r.stdout.strip()}')

for raw in Path('python/migrated-scripts.tsv').read_text(encoding='utf-8').splitlines():
    line = raw.strip()
    if not line or line.startswith('#') or '#3678' not in line:
        continue
    retired_path = line.split('\t')[0].strip()
    if retired_path and Path(retired_path).exists():
        checks.append(f'retired #3678 path still exists: {retired_path}')
for retired_basename in ['commit-review-fixes.md', 'write-rejected-findings.md', 'check-review-changes.md']:
    forbid(skill, retired_basename, f'SKILL must not cite retired {retired_basename}')

if checks:
    print('\n'.join(checks), file=sys.stderr)
    sys.exit(1)
print('PASS: test-implement-structure.sh (wrapperized prompt structure)')
PY
