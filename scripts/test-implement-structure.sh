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

def require_text(text, needle, label):
    if needle not in text:
        checks.append(f'{label}: missing {needle!r}')

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

def branch_slice(text, branch):
    marker = f'- **`{branch}`**:'
    start = text.find(marker)
    if start < 0:
        checks.append(f'{branch} branch slice: missing {marker!r}')
        return ''
    match = re.search(r'\n- \*\*`[^`]+`\*\*:', text[start + 1:])
    if match:
        return text[start:start + 1 + match.start()]
    blank = text.find('\n\n', start)
    if blank >= 0:
        return text[start:blank]
    return text[start:]

skill='skills/implement/SKILL.md'
checks_ref='skills/implement/references/checks-repair-loop.md'
step5_branches_ref='skills/implement/references/step5-review-branches.md'
registry_ref='skills/implement/references/extracted-script-registry.md'
if not Path(registry_ref).is_file():
    checks.append(f'missing reference {registry_ref}')
else:
    registry_text = Path(registry_ref).read_text()
    for header in ['**Consumer**:', '**Contract**:', '**When to load**:']:
        if header not in registry_text:
            checks.append(f'{registry_ref} missing {header}')
require(skill, registry_ref, 'SKILL pointer for extracted script registry')
# New mandatory references.
for ref in [
    'rebase-checkpoint-routing.md','phantom-probe.md','ship-pr-exit-matrix.md','step18-cleanup.md',
    'ship-pr-oos-checkpoint-router.md','ship-pr-ci-fix.md',
    'bootstrap-recovery.md','self-review.md',
]:
    path=f'skills/implement/references/{ref}'
    if not Path(path).is_file():
        checks.append(f'missing reference {path}')
    else:
        text=Path(path).read_text()
        for header in ['**Consumer**:', '**Contract**:', '**When to load**:']:
            if header not in text:
                checks.append(f'{path} missing {header}')
        require(skill, f'skills/implement/references/{ref}', f'SKILL pointer for {ref}')

summary_doc = Path('docs/summary-comment-template.md')
if not summary_doc.is_file():
    checks.append('missing docs/summary-comment-template.md')
else:
    summary_text = summary_doc.read_text()
    for marker in [
        '<!-- larch:metadata v1 runid=<R> -->',
        '<!-- larch:diagrams v1 -->',
        '<!-- larch:plan v1 runid=<R> -->',
        '<!-- larch:final-summary v1 runid=<R> -->',
    ]:
        if marker not in summary_text:
            checks.append(f'docs/summary-comment-template.md missing marker {marker!r}')

# Wrapper call sites. The pre-bootstrap Step 0 fences keep the old shape.
for script in [
    'LARCH_CLAUDE_PID="$PPID" "${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-0-bootstrap.sh" --mode initial',
]:
    require(skill, script, f'SKILL old-shape wrapper {script}')
require('skills/implement/references/bootstrap-recovery.md', 'LARCH_CLAUDE_PID="$PPID" "${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-0-bootstrap.sh" --mode resume', 'bootstrap-recovery relocated resume wrapper')

# Collapsed Preflight helper surface.
for path in [
    'python/larch/implement/preflight.py',
    'python/tests/implement/test_preflight.py',
]:
    if not Path(path).is_file():
        checks.append(f'missing {path}')
require(skill, 'python/cli.py" implement preflight', 'SKILL implement preflight CLI reference')
require(skill, 'python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" implement preflight', 'SKILL implement preflight Python invocation')
require(skill, '$PREFLIGHT_TMPDIR/issue.json', 'SKILL preflight issue json path')
require(skill, '$PREFLIGHT_TMPDIR/plan-from-issue.txt', 'SKILL preflight plan path')
require(skill, 'PLAN_PATH', 'SKILL PLAN_PATH envelope binding')
require(skill, 'ISSUE_JSON_PATH', 'SKILL ISSUE_JSON_PATH envelope binding')
require(skill, 'one `KEY=value` record per line', 'SKILL one-record envelope')
require(skill, 'Split each envelope line at the first `=` only', 'SKILL first-equals parser')
require(skill, '`python/cli.py implement preflight` self-validates the success envelope and exits `2` before success parsing when malformed.', 'SKILL Python preflight self-validation')
require(skill, 'On non-zero exit, abort before item 4', 'SKILL nonzero preflight abort')
require(skill, 'Do not parse or require an envelope on non-zero exit.', 'SKILL no exit2 envelope parse')
require(skill, 'Run `admission fork-env`, then the preflight helper, then Step 0 bootstrap.', 'SKILL forked ordering')
require('python/larch/implement/preflight.py', 'SUCCESS_ENVELOPE_KEYS', 'preflight success envelope key tuple')
require('python/larch/implement/preflight.py', 'def _validate_success_envelope', 'preflight validation helper')
require('python/larch/implement/preflight.py', 'duplicate key', 'preflight duplicate key validation')
require('python/larch/implement/preflight.py', 'RESUME must be true or false', 'preflight resume validation')
require('python/larch/implement/preflight.py', 'BYPASS_COUNT must be numeric', 'preflight bypass count validation')
require('python/larch/implement/preflight.py', '"ADMISSION_RESULT"', 'preflight emits admission result')
require('python/larch/implement/preflight.py', '"RESUME"', 'preflight emits resume')
require('python/larch/implement/preflight.py', '"PLAN_PATH"', 'preflight emits plan path')
require('python/larch/implement/preflight.py', '"ISSUE_JSON_PATH"', 'preflight emits issue json path')
require('python/larch/implement/preflight.py', '"BYPASS_COUNT"', 'preflight emits bypass count')
require('python/larch/implement/preflight.py', 'force-bypass.log', 'preflight bypass log destination')
require('python/larch/implement/preflight.py', 'json.load', 'preflight uses stdlib json')
require('python/tests/implement/test_preflight.py', 'test_preflight_success_emits_kv_and_forwards_repo', 'preflight test success coverage')
require('python/tests/implement/test_preflight.py', 'test_preflight_force_missing_plan_uses_raw_body', 'preflight test force coverage')
require('python/tests/implement/test_preflight.py', 'test_preflight_force_short_flag_missing_plan_uses_raw_body', 'preflight test -f coverage')
require(skill, '`--force` and `-f` both set `force_requested=true`', 'SKILL -f alias parse rule')
require(skill, '`--force` / `-f` and `--draft` together', 'SKILL -f draft mutex wording')
require('skills/im/SKILL.md', '`--force`, `-f`', 'im SKILL forwards -f alias')
require('python/tests/state/test_bootstrap.py', 'test_invoke_refuses_symlinked_bootstrap_routing_env', 'bootstrap refusal-path test')
require('python/tests/state/test_bootstrap.py', 'BOOTSTRAP_NEXT=cleanup', 'bootstrap refusal-path emits directive')
require('python/tests/state/test_bootstrap.py', 'BOOTSTRAP_NEXT=step2', 'bootstrap invoke emits step2 directive')
require('python/tests/state/test_bootstrap.py', 'BOOTSTRAP_NEXT=degraded-prompt', 'bootstrap invoke emits degraded directive')
require('python/tests/state/test_bootstrap.py', 'BOOTSTRAP_NEXT=rebase-routing', 'bootstrap resume malformed route directive test')
forbid(skill, '${force_requested:+--force}', 'SKILL preflight force argv')
forbid(skill, 'If `false` and `force_requested=false`, print `**❌ Issue #<N> has no larch:plan block', 'SKILL prompt-side missing-plan fallback prose')
forbid(skill, 'If the script exits **1** and prints `MALFORMED=...`, then when `force_requested=false`', 'SKILL prompt-side malformed-plan fallback prose')
forbid(skill, 'single-line envelope', 'SKILL must not describe single-line envelope')
forbid(skill, 'full seven-key envelope', 'SKILL must not require envelope on exit 2')


launcher = '"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" '
bootstrap_recovery_read = '**MANDATORY: READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/bootstrap-recovery.md` completely.'
self_review_read = '**MANDATORY: READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/self-review.md` completely.'
bootstrap_recovery_read_degraded = '**MANDATORY: READ ENTIRE FILE** `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/bootstrap-recovery.md` for degraded-prompt handling before treating absent routing keys as rebase failure.'
for script in [
    'skills/implement/scripts/step-2-post-dispatch.sh --expected-branch "$BRANCH_NAME"',
    'python/cli.py implement checks-commit-route --checks-site step3 --commit-site step4 --rebase-checkpoint-4r --forked-target "${forked_target:-false}"',
    'skills/implement/scripts/step-5-review.sh',
    'python/cli.py implement checks-step5-resume --checks-site step5-review-fixes --final-round-num "$FINAL_ROUND_NUM"',
    'skills/implement/scripts/step-5-resume.sh --final-round-num "$FINAL_ROUND_NUM" --record-only',
    'skills/implement/scripts/step-6-entry.sh --forked-target "${forked_target:-false}"',
    'python/cli.py implement step-7a --implement-tmpdir "$IMPLEMENT_TMPDIR"',
    'python/cli.py ship pre-driver',
    'skills/implement/scripts/step-8-ship.sh',
    'skills/implement/scripts/step-8-oos-checkpoint.sh',
    'python/cli.py implement step-18-gate-finalize --implement-tmpdir "$IMPLEMENT_TMPDIR" --stall-tracking-memory "${STALL_TRACKING:-false}" --step17-emitted "${STEP17_EMITTED_FOR_STEP18:-false}"',
    'skills/implement/scripts/step-18.sh --phase finalize --step17-emitted "${STEP17_EMITTED_FOR_STEP18:-false}"',
]:
    require(skill, launcher + script, f'SKILL launcher wrapper {script}')

require('skills/implement/references/self-review.md', launcher + 'python/cli.py implement checks-commit-route --checks-site step5-self-review --commit-site step5-self-review', 'self-review relocated composite launcher')
require(skill, 'python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" implement step-16-17 --implement-tmpdir "$IMPLEMENT_TMPDIR"', 'SKILL direct Step 16-17 Python CLI call')

for needle in [
    'BASE_ARGS=()',
    'session read-key --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TOKEN_SESSION_ID',
    '_oos_chk_err=',
    '_restore_finalize=false',
]:
    forbid(skill, needle, 'wrapperized SKILL')

# Script/md sibling and executable coverage for new wrappers.
wrappers = ['step-0-bootstrap','step-0-degraded-gate','step-2-post-dispatch','run-step-checks','step-5-review','step-5-resume','step-6-entry','step-8-python-guard','step-8-seed-initial','step-8-ship','step-8-oos-checkpoint','step-18']
for name in wrappers:
    sh=Path(f'skills/implement/scripts/{name}.sh')
    md=Path(f'skills/implement/scripts/{name}.md')
    if not sh.is_file(): checks.append(f'missing {sh}')
    if not md.is_file(): checks.append(f'missing {md}')
    if sh.is_file() and not os.access(sh, os.X_OK): checks.append(f'{sh} is not executable')

# Existing wrappers that gained behavior.
require('skills/implement/scripts/step-5-review.sh', 'review-and-fix step5', 'step-5-review calls review-and-fix step5')
for needle, label in [
    ('review-and-fix write-loop-identity', 'step-5-review writes loop identity sidecar'),
    ('review-and-fix await-loop-identity', 'step-5-review awaits detached loop identity'),
    ('review-and-fix normalize-status', 'step-5-review normalizes captured stdout'),
    ('review-and-fix teardown-loop-identity', 'step-5-review delegates teardown to identity helper'),
    ("trap '_step5_signal_exit TERM 143' TERM", 'step-5-review traps TERM'),
    ("trap '_step5_signal_exit HUP 129' HUP", 'step-5-review traps HUP'),
    ("trap '_step5_signal_exit INT 130' INT", 'step-5-review traps INT'),
]:
    require('skills/implement/scripts/step-5-review.sh', needle, label)
step5_text = Path('skills/implement/scripts/step-5-review.sh').read_text()
cleanup_start = step5_text.find('_step5_cleanup()')
cleanup_end = step5_text.find('}', cleanup_start) if cleanup_start >= 0 else -1
if cleanup_start < 0 or cleanup_end < 0:
    checks.append('step-5-review cleanup function missing')
elif '.completed/step-5-terminal' in step5_text[cleanup_start:cleanup_end]:
    checks.append('step-5-review must not write terminal sentinel from bare EXIT cleanup')
retired_step5_entry_sh = 'skills/implement/scripts/' + 'step-5-entry.sh'
retired_step5_entry_md = 'step-5-' + 'entry.md'
forbid(skill, retired_step5_entry_sh, 'retired step-5-entry.sh call removed from SKILL')
forbid(skill, retired_step5_entry_md, 'retired step-5-entry.md ref removed from SKILL')
require('python/larch/review/review_and_fix.py', '--stage-all', 'commit-fixes --stage-all')
forbid(skill, 'review-and-fix commit-fixes <specific-files>', 'Step 7 must stage all review fixes')
forbid('python/larch/review/review_and_fix.py', '"git", "add", "-A"', 'commit-fixes must not stage unrelated paths')
forbid('python/larch/review/review_and_fix.py', '"git", "add", "--pathspec-from-file"', 'staging owned by commit_main only')
require('python/larch/review/review_and_fix.py', '"--only",\n        "--pathspec-from-file"', 'commit-fixes pathspec-only commit')
require('python/larch/implement/dispatch_helpers.py', 'LARCH_TIMING_LEDGER', 'commit-implementation telemetry self-rehydration')
require('skills/implement/scripts/step-18.sh', '--phase gate', 'step-18 phase gate argv')
require('skills/implement/scripts/step-18.sh', '--phase finalize', 'step-18 phase finalize argv')
require('skills/implement/scripts/step-18.sh', '_stall_layer_active', 'step-18 stall predicate helper')
require('skills/implement/scripts/step-18.sh', 'STALL_TRACKING_MEMORY_ARG', 'step-18 stall-tracking memory arg')
require('skills/implement/scripts/step-18.sh', 'STALL_TRACKING_DISK=', 'step-18 stall disk layer')
require('skills/implement/scripts/step-18.sh', 'STALL_TRACKING_FINALIZE=', 'step-18 stall finalize layer')
require('skills/implement/scripts/step-18.sh', 'STALL_TRACKING_SESSION=', 'step-18 stall session layer')
require('skills/implement/scripts/step-18.sh', 'STALL_RECOVERY_REQUIRED=', 'step-18 stall recovery kv')
require('skills/implement/scripts/step-18.sh', 'set +e', 'step-18 non-aborting blocks')
require('skills/implement/scripts/step-18.sh', 'final-report step18b --implement-tmpdir "$IMPLEMENT_TMPDIR"', 'step-18 live step18b path')
require('skills/implement/scripts/step-18.sh', 'print_summary_markers', 'step-18 marker helper')
require('skills/implement/scripts/step-18.sh', '---LARCH-SUMMARY-FINAL-BEGIN---', 'step-18 begin marker')
require('skills/implement/scripts/step-18.sh', '_restore_finalize=false', 'step-18 restore gate')
require('skills/implement/scripts/step-18.sh', 'restore-finalize-state --implement-tmpdir "$IMPLEMENT_TMPDIR"', 'step-18 restore finalize argv')
require('skills/implement/scripts/step-18.sh', 'implement-finalize teardown --state-file "$IMPLEMENT_TMPDIR/finalize-state.sh" --implement-tmpdir "$IMPLEMENT_TMPDIR"', 'step-18 exact teardown argv')
require('skills/implement/scripts/step-18.sh', 'LARCH_CLAUDE_PID:-$PPID', 'step-18 claude pid fallback')
require('skills/implement/scripts/step-18.sh', "DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement", 'step-18 timing env')
forbid('skills/implement/scripts/step-18.sh', 'cleanup.sh" --help', 'step-18 must not resurrect cleanup smoke')
forbid('skills/implement/scripts/step-18.sh', 'token report --full', 'step-18 must not resurrect full token report')
forbid('skills/implement/scripts/step-18.sh', 'Step 18 — cleanup', 'step-18 must not resurrect cleanup telemetry mark')
require('skills/implement/scripts/step-0-bootstrap.sh', 'CALLER_ENV_PATH=*) CALLER_ENV_PATH=', 'step-0 fork metadata caller-env parse')
require('skills/implement/scripts/step-0-bootstrap.sh', 'UPSTREAM_REPO=*) UPSTREAM_REPO=', 'step-0 fork metadata upstream parse')
require('skills/implement/scripts/step-0-bootstrap.sh', 'preflight-tmpdir.env', 'step-0 preflight tmpdir resume persistence')
require('skills/implement/scripts/step-0-bootstrap.sh', 'read_session_key FORKED_TARGET', 'step-0 resume fork metadata rehydration')
require('python/larch/state/bootstrap.py', 'preflight-tmpdir.env', 'bootstrap preflight tmpdir persistence')
require('skills/implement/scripts/step-8-ship.sh', 'read_state_key', 'step-8 ship state rehydration')
require('skills/implement/scripts/step-8-python-guard.sh', 'sys.version_info >= (3, 11)', 'step-8 shared python 3.11 guard')
require('skills/implement/scripts/step-8-python-guard.sh', '"outcome":"STALLED"', 'step-8 shared stalled JSON stdout')
require('skills/implement/scripts/step-8-python-guard.sh', 'exit 4', 'step-8 shared stale-python exit 4')
require('skills/implement/scripts/step-8-ship.sh', 'step-8-python-guard.sh', 'step-8 ship delegates python guard')
require('skills/implement/scripts/step-8-ship.sh', 'python/cli.py" implement clone-tag', 'step-8 ship uses clone-tag CLI')
require('python/larch/implement/dispatch_helpers.py', 'def clone_tag_main', 'implement clone-tag CLI handler')
require('skills/implement/scripts/step-8-ship.sh', 'python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" ship pr', 'step-8 python ship invocation')
require('python/larch/cli.py', '("ship", "pre-driver"): ("larch.implement.implement_dispatch", "ship_pre_driver_main")', 'ship pre-driver CLI registry')
require('python/larch/cli.py', '("ship", "pre-driver"),', 'ship pre-driver machine stdout contract')
require('python/larch/cli.py', 'NEXT_ACTION=stall', 'ship pre-driver pre-version stall fast path')
require('python/larch/cli.py', '("implement", "step-18-gate-finalize"): ("larch.implement.implement_dispatch", "step_18_gate_finalize_main")', 'Step 18 composite CLI registry')
require('python/larch/cli.py', '("implement", "step-18-gate-finalize"),', 'Step 18 composite machine stdout contract')
require('python/larch/implement/dispatch_step18.py', 'def step_18_gate_finalize_main', 'Step 18 composite handler')
require('python/larch/implement/dispatch_ship.py', 'def ship_pre_driver_main', 'ship pre-driver handler')
require('python/larch/implement/dispatch_ship.py', '["implement", "step-8-python-guard"]', 'ship pre-driver runs guard first')
require('python/larch/implement/dispatch_ship.py', '["implement", "step-8-seed-initial"]', 'ship pre-driver conditional seeder')
require('python/larch/implement/dispatch_ship.py', '["oos", "file", "--implement-tmpdir", str(implement_tmpdir)]', 'ship pre-driver runs oos file')
require('python/larch/implement/dispatch_ship.py', 'value="halt-seed"', 'ship pre-driver seed halt token')
require('python/larch/implement/dispatch_ship.py', 'value="halt-oos"', 'ship pre-driver oos halt token')
forbid(skill, launcher + 'skills/implement/scripts/step-8-python-guard.sh', 'SKILL standalone step-8 guard fence removed')
forbid(skill, launcher + 'skills/implement/scripts/step-8-seed-initial.sh', 'SKILL standalone step-8 seeder fence removed')
forbid(skill, launcher + 'python/cli.py oos file --implement-tmpdir "$IMPLEMENT_TMPDIR"', 'SKILL standalone pre-driver oos fence removed')
require('skills/implement/scripts/step-0-bootstrap.sh', 'LARCH_CLAUDE_PID="${LARCH_CLAUDE_PID:-$PPID}"', 'step-0 wrapper claude pid export')
require(skill, 'python/cli.py ship seed-initial-state', 'ship state initial seeder authority')
require('skills/implement/scripts/step-8-seed-initial.sh', '--no-admin-fallback', 'ship state no-admin fallback seeder argv')
require('python/larch/implement/ship_state.py', 'NO_ADMIN_FALLBACK', 'ship state no-admin fallback allowed key')
require(skill, '## NEVER List', 'NEVER list heading')
require(skill, 'NEVER call `ScheduleWakeup`', 'NEVER #8 ScheduleWakeup pin')
require(skill, 'Do not spawn a Monitor', 'NEVER #8 background-monitor ban')
require(skill, 'Bootstrap edit gate (NEVER #21)', 'NEVER #21 bootstrap edit gate pin')
for script, timeout in [
    (launcher + 'skills/implement/scripts/step-5-review.sh', 'timeout: 21600000'),
    (launcher + 'python/cli.py implement checks-commit-route --checks-site step3 --commit-site step4 --rebase-checkpoint-4r', 'timeout: 15600000'),
    (launcher + 'python/cli.py implement checks-step5-resume --checks-site step5-review-fixes', 'timeout: 32700000'),
    (launcher + 'skills/implement/scripts/step-6-entry.sh', 'timeout: 15600000'),
    (launcher + 'python/cli.py implement step-7a', 'timeout: 1800000'),
    (launcher + 'skills/implement/scripts/step-8-ship.sh', 'timeout: 21600000'),
]:
    require_near(skill, script, 'Immediate-background required', f'immediate-background pin for {script}', 1400)
    require_near(skill, script, timeout, f'timeout pin for {script}', 1400)
self_review_composite = launcher + 'python/cli.py implement checks-commit-route --checks-site step5-self-review --commit-site step5-self-review'
require_near('skills/implement/references/self-review.md', self_review_composite, 'Immediate-background required', 'self-review immediate-background pin', 1400)
require_near('skills/implement/references/self-review.md', self_review_composite, 'timeout: 14700000', 'self-review timeout pin', 1400)
require_near(skill, launcher + 'skills/implement/scripts/step-5-review.sh', '<task-notification>', 'Step 5 review task notification wait', 1800)
require_near(skill, launcher + 'skills/implement/scripts/step-6-entry.sh', '> **Continue after child returns.**', 'Step 6 unified launcher continuation opener', 2000)
require_near(skill, launcher + 'skills/implement/scripts/step-8-ship.sh', '<task-notification>', 'Step 8 ship task notification wait', 2000)

require(skill, 'PHASE=checks` and `PR_NUMBER` is empty/absent', 'SKILL pre-driver predicate checks phase and empty pr')
require(skill, 'Seeded-but-no-PR state is still pre-driver', 'SKILL seeded no-pr retry stays pre-driver')
require(skill, 'pre-driver retry reruns guard and `oos file`', 'SKILL pre-driver retry reruns oos file')
require(skill, 'On `NEXT_ACTION=ship`, proceed to `step-8-ship.sh`', 'SKILL pre-driver continuation on ship')
forbid(skill, 'write-initial-state-keys:begin', 'SKILL initial state marker removed')
forbid(skill, 'sys.version_info >= (3, 11)', 'SKILL inline python version guard removed')
forbid(skill, 'python/cli.py ship seed-initial-state --tmpdir', 'SKILL direct seeder invocation removed')
require(step5_branches_ref, 'step-8-seed-initial.sh --stall-tracking "$STALL_TRACKING" --stall-step 5', 'Step 5 stall seeder wrapper')
require(step5_branches_ref, '--bail-failure-detail-log "" --draft false', 'Step 5 stall seeder passes draft false without merge override')
require(step5_branches_ref, '## Durable Bail', 'Step 5 Durable Bail section heading')
require(step5_branches_ref, 'overrides `stall`-branch envelope `STALL_TRACKING` retention', 'Durable Bail override authority')
require(step5_branches_ref, '--stall-tracking true', 'Durable Bail literal stall tracking seeder')
require(step5_branches_ref, 'Persist `STALL_TRACKING=true`', 'Durable Bail present-state STALL_TRACKING rewrite')
require('python/larch/state/bootstrap.py', 'ship-seed-input.env', 'bootstrap ship seed input writer')
require(skill, launcher + 'skills/implement/scripts/step-2-post-dispatch.sh', 'phantom 2-post-dispatch probe')
require(skill, 'regardless of wrapper exit code', 'post-dispatch phantom parse before wrapper routing')
require('skills/implement/scripts/step-8-ship.sh', 'python/cli.py" git phantom-probe --step 8-pre-ship', 'phantom 8-pre-ship probe moved into ship wrapper')
forbid(skill, launcher + 'scripts/' + 'phantom-probe-with-warn.sh --step 8-pre-ship', 'standalone orchestrator 8-pre-ship fence removed')
rebase_ref = Path('skills/implement/references/rebase-checkpoint-routing.md').read_text()
for needle in [
    '**Orchestrator contract: absorbed `1.r` (Step 0 envelope only)**',
    '**Orchestrator contract: folded and direct probe relays (`4.r`, `7.r`, `7a.r`)**',
    'CHECKPOINT_NEXT=continue|load-routing',
    'CHECKPOINT_NEXT=load-routing',
    'REBASE_OUTCOME=conflict',
    '**⚠ Rebase onto main failed (non-conflict): $REBASE_ERROR. Bailing to cleanup.**',
    '**⚠ Rebase onto main failed unexpectedly',
    'Call-site registry',
    'caller_kind=early_rebase',
]:
    if needle not in rebase_ref:
        checks.append(f'rebase-checkpoint-routing.md missing {needle!r}')
for needle in [
    'skills/implement/references/bootstrap-recovery.md',
    bootstrap_recovery_read_degraded,
    'DEGRADED_PROMPT_REQUIRED=true',
    'before treating absent routing keys as rebase failure',
]:
    if needle not in rebase_ref:
        checks.append(f'rebase-checkpoint-routing.md missing degraded bootstrap-recovery pointer {needle!r}')
if 'follow the degraded prompt path instead' in rebase_ref:
    checks.append("rebase degraded carve-out must not retain stale inline-degraded prose: forbidden 'follow the degraded prompt path instead' remains in rebase-checkpoint-routing.md")
phantom_ref = Path('skills/implement/references/phantom-probe.md').read_text()
for needle in ['2-post-dispatch', 'step-2-post-dispatch.sh', '8-pre-ship', 'Do not probe when `STATUS=claude_fallback`']:
    if needle not in phantom_ref:
        checks.append(f'phantom-probe.md missing {needle!r}')
require('python/larch/git/push.py', '--forked-target', 'rebase probe forked target flag')
require('python/larch/git/push.py', 'CHECKPOINT_NEXT', 'rebase probe checkpoint directive')
require('python/larch/state/bootstrap.py', '"CHECKPOINT_NEXT"', 'bootstrap checkpoint directive relay')
require(skill, 'CHECKPOINT_NEXT=continue|load-routing', 'SKILL checkpoint directive macro')
require(skill, 'The `7a.r` macro skip is `CHECKPOINT_NEXT`-only', 'SKILL Step 7a checkpoint-only macro skip')
require('skills/implement/references/rebase-checkpoint-routing.md', '--forked-target true|false', 'rebase probe docs')
require('skills/implement/references/rebase-checkpoint-routing.md', 'CHECKPOINT_NEXT=continue|load-routing', 'rebase checkpoint directive docs')
require('Makefile', 'test-implement-fence-shape:', 'Makefile fence-shape target')
require('docs/linting.md', 'make test-implement-fence-shape', 'linting docs fence-shape target')

skill_text = Path(skill).read_text()
require_near(skill, bootstrap_recovery_read, 'BOOTSTRAP_NEXT=degraded-prompt', 'degraded-prompt mandatory read before branch', 900)
require_near(skill, bootstrap_recovery_read, 'BOOTSTRAP_NEXT=dirty-recovery', 'dirty-recovery mandatory read before branch', 900)
require_near(skill, self_review_read, 'When `self_review=true`', 'self-review mandatory read before branch', 900)
require(skill, bootstrap_recovery_read_degraded, 'SKILL Rebase Checkpoint Macro bootstrap-recovery pointer')
require(skill, 'Call sites should invoke **Checks Failure Entry Macro** by name with their pinned `--site` / `--checks-site` arguments instead of restating these read steps.', 'Checks Failure Entry Macro invocation guidance')
step5_macro_token = '--site step5-mav --checks-site step5-review-fixes'
if skill_text.count(step5_macro_token) != 1:
    checks.append(f'SKILL.md must contain exactly one {step5_macro_token!r} macro token occurrence')
mav_idx = skill_text.find('- **`main-agent-vote-required`**:')
coder_idx = skill_text.find('- **`coder-main-agent-required`**:')
shared_step5 = '> **Continue after child returns.** On composite `NEXT_ACTION=checks-failed`, apply **Checks Failure Entry Macro** with pinned `--site step5-mav --checks-site step5-review-fixes`.'
shared_idx = skill_text.find(shared_step5)
resume_idx = skill_text.find('"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py implement checks-step5-resume --checks-site step5-review-fixes --final-round-num "$FINAL_ROUND_NUM"')
if not (mav_idx >= 0 and coder_idx > mav_idx and shared_idx > coder_idx and resume_idx > shared_idx):
    checks.append('SKILL.md must route Step 5 MAV and coder branches through one shared checks block before checks-step5-resume')
else:
    shared_window = skill_text[shared_idx:resume_idx]
    for needle in [
        'NEXT_ACTION=checks-failed',
        'Checks Failure Entry Macro',
        '--site step5-mav --checks-site step5-review-fixes',
        'On checks pass, apply the composite stdout parsing slice and full resume envelope contract below.',
        'NEXT_ACTION=main-agent-edit',
        'Terminal `NEXT_ACTION=stall` from the repair loop is a routing summary only',
        'Do **not** re-invoke the Step 5 loop wrapper.',
    ]:
        if needle not in shared_window:
            checks.append(f'SKILL.md shared Step 5 checks block missing {needle!r}')
old_inline_combo = re.compile(
    r'(read|whitespace-scan)[^\n]*REDACTED_LOG_FILE[^\n]*checks-repair-loop\.md`; then apply \*\*Checks Failure Entry Macro\*\*'
)
if old_inline_combo.search(skill_text):
    checks.append('SKILL.md must not restate REDACTED_LOG_FILE and checks-repair-loop.md before applying the Checks Failure Entry Macro')
for old_subcase in ['Sub-case A', 'Sub-case B', 'Sub-case C']:
    if old_subcase in skill_text:
        checks.append(f'SKILL.md must not retain collapsed exit-code 3 label {old_subcase!r}')
require(skill, 'Follow `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/preflight-plan-audit.md` `## Clarify-request flow after AUDIT=refuse` for post, label, `STATE=ambiguous`, and `STATE=awaiting-response` behavior.', 'SKILL exit-code 3 preflight pointer')
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

# Step 17/18 marker handoff contract must exist without re-spelling the shared algorithm.
require('python/larch/state/closeout.py', '---LARCH-SUMMARY-FINAL-BEGIN---', 'step-16-17 begin marker literal')
require('python/larch/state/closeout.py', '---LARCH-SUMMARY-FINAL-END---', 'step-16-17 end marker literal')
require(skill, 'skills/shared/final-summary-emit.md', 'SKILL shared final-summary emit pointer')
require(skill, 'markers `---LARCH-SUMMARY-FINAL-BEGIN---` / `---LARCH-SUMMARY-FINAL-END---`', 'SKILL implement marker pair binding')
require(skill, 'captured foreground `python/cli.py implement step-16-17` Bash wrapper stdout', 'SKILL Step 17 captured foreground stdout source')
require(skill, 'captured foreground `python/cli.py implement step-18-gate-finalize` Bash wrapper stdout', 'SKILL Step 18 composite stdout source')
require(skill, 'captured foreground `step-18.sh --phase finalize` Bash wrapper stdout', 'SKILL Step 18 captured foreground stdout source')
require(skill, 'not `<task-notification>` output', 'SKILL implement source is not task notification output')
require(skill, 'Read fallback `forbidden`', 'SKILL Read fallback forbidden binding')
require(skill, 'sidecar follow-on `forbidden`', 'SKILL sidecar follow-on forbidden binding')
require(skill, 'do not Read that file on the Step 17 primary path', 'SKILL no Read-tool Step 17 primary path')
require(skill, 'Do not Read `summary-final.md` on the Step 18 path because teardown may have removed the tmpdir.', 'SKILL Step 18 no Read fallback')
require(skill, '**⚠ Step 18: EMIT_BODY=true but marker pair missing from composite stdout.**', 'SKILL Step 18 composite missing-marker warning')
require(skill, '**⚠ Step 18: EMIT_BODY=true but marker pair missing from finalize stdout.**', 'SKILL Step 18 finalize missing-marker warning')
require(skill, 'Relay teardown tail records verbatim from captured composite stdout on `NEXT_ACTION=finalize-done`, or from captured finalize stdout on the stall-recovery path.', 'SKILL Step 18 dual tail relay')
cleanup_read = '**MANDATORY: READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/step18-cleanup.md` completely.'
require_near(
    skill,
    cleanup_read,
    '"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py implement step-18-gate-finalize',
    'Step 18 cleanup read before composite fence',
    1600,
)
forbid(skill, '#### Step 18a.5 — Escalation-success report gate', 'SKILL Step 18a.5 section must be removed')
require(skill, 'During active recovery before `CLEARED=true`, do not run the standalone `--phase finalize` fence.', 'SKILL stall-recovery skip standalone finalize during active recovery')
require(skill, 'After successful recovery (`CLEARED=true`), run the standalone `step-18.sh --phase finalize` fence.', 'SKILL stall-recovery run standalone finalize after cleared')
require(skill, 'Proceed without re-running `python/cli.py implement step-18-gate-finalize` after terminal recovery completes.', 'SKILL Step 18a no composite re-run after terminal recovery')
require(skill, 'Parse `STALL_RECOVERY_REQUIRED` and the four `STALL_TRACKING_*` KVs from captured composite stdout immediately after the composite fence returns.', 'SKILL Step 18a parses stall KVs from composite stdout')
require(skill, 'Branch primarily on `NEXT_ACTION=stall-recovery`', 'SKILL Step 18a primary stall branch trigger')
forbid(skill, 'Use the gate phase below', 'SKILL retired gate-phase prose')
forbid(skill, 'skills/implement/scripts/step-18.sh --phase gate --stall-tracking-memory', 'SKILL retired standalone gate fence')
require(skill, '**Escalation recording owners.**', 'SKILL escalation recording owners preserved')
require(skill, 'Repeat any external reviewer warnings from earlier', 'SKILL Step 18b warnings preserved')
require(skill, 'Cap the per-run token/timing ledgers **before** teardown removes them.', 'SKILL #3425 closing marks preserved')
forbid(skill, 'When `EMIT_BODY=true` and `WFR_RC=0` and `[ -s "$IMPLEMENT_TMPDIR/summary-final.md" ]`', 'SKILL Step 18 Read fallback removed')
require('python/larch/state/closeout.py', '.step17-printed', 'step-16-17 owns .step17-printed')
require(skill, 'write `$IMPLEMENT_TMPDIR/.step17-emitted` only after that plain-chat emission.', 'SKILL Step 17 .step17-emitted orchestrator ownership')
require(skill, 'The orchestrator does not write `.step17-emitted` after finalize returns.', 'SKILL Step 18 .step17-emitted wrapper ownership')
require('python/larch/state/closeout.py', 'step17_rc == 0 and _summary_nonempty(tmpdir)', 'step-16-17 marker gate uses Step 17 rc and non-empty summary')
require(skill, 'Marker emission is gated on captured Step 17 render success and a non-empty `summary-final.md`, not `summary-final.md` presence alone.', 'SKILL stale-summary marker gate')
forbid(skill, 'Do NOT use a Bash `cat` or Python tool call to print the summary body', 'retired Step 17 Bash-cat prohibition string')
forbid(skill, 'via Bash `cat` whose output is then re-emitted as orchestrator text', 'SKILL must not sanction Bash cat for summary emit')

if not re.search(r'timeout: 32700000[\s\S]{0,900}"\$HOME/\.cache/larch/sessions/implement-run-\$PPID\.sh" python/cli\.py implement checks-step5-resume --checks-site step5-review-fixes --final-round-num "\$FINAL_ROUND_NUM"', skill_text):
    checks.append('SKILL.md must background the Step 5 checks-step5-resume composite fence with timeout 32700000')
if re.search(r'(^|[\s])--auto([^A-Za-z0-9_-]|$)', skill_text):
    checks.append('SKILL.md must not document standalone --auto flag token (issue #2497)')
if '--auto-mode' in skill_text:
    checks.append('SKILL.md must not document --auto-mode flag (issue #2497)')
for ref in [
    'conflict-resolution.md', 'codex-manifest-schema.md', 'step5-review-branches.md',
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
        'python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" push rebase --continue --no-push --keep-on-conflict',
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
require(skill, 'LARCH_CLAUDE_PID="$PPID" "${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-0-bootstrap.sh" --mode initial', 'Step 0 initial bootstrap wrapper')
require('skills/implement/references/bootstrap-recovery.md', 'LARCH_CLAUDE_PID="$PPID" "${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-0-bootstrap.sh" --mode resume', 'Step 0 resume bootstrap wrapper relocated')
require('skills/implement/scripts/step-0-bootstrap.sh', 'set +e', 'step-0 bootstrap set +e guard')
require('python/larch/state/bootstrap.py', 'preserve_coder=args.resume == "true"', 'bootstrap parse-routing resume preserves coder')
forbid(skill, launcher + 'skills/implement/scripts/step-0-degraded-gate.sh', 'SKILL active flow must not call step-0-degraded-gate.sh')
require('python/larch/state/bootstrap.py', 'degraded-tools-gate', 'bootstrap absorbed degraded gate')
require('python/larch/state/bootstrap.py', 'checkpoint-probe', 'bootstrap absorbed 1.r probe')
require('python/larch/state/bootstrap.py', 'DEGRADED_PROMPT_REQUIRED', 'bootstrap degraded prompt routing')
require('python/larch/state/bootstrap.py', 'REBASE_RC', 'bootstrap rebase rc synthesis')
require('python/larch/state/bootstrap.py', '_ADVISORY_STDOUT_PREFIXES', 'bootstrap phantom advisory allowlist')
require('python/larch/state/bootstrap.py', 'def _bootstrap_next', 'bootstrap next directive helper')
require('python/larch/state/bootstrap.py', '"BOOTSTRAP_NEXT"', 'bootstrap next routing key')
require('python/larch/state/bootstrap.py', 'continue_tail_attempted = _continue_predicate(data)', 'bootstrap captures continue_tail_attempted after coder restore')
require('python/larch/state/bootstrap.py', 'tail = _run_absorbed_continue_tail', 'bootstrap captures continue_tail_attempted immediately before tail')
require('python/larch/state/bootstrap.py', 'elif _step2_blockers(data) or bail_reason or data.get("STALL_TRACKING") == "true":', 'bootstrap blockers precede malformed route rebase')
require('python/larch/state/bootstrap.py', 'if continue_tail_attempted and route not in {"continue", "conflict", "bail"}:', 'bootstrap malformed route gated on tail attempt')
require('python/larch/state/bootstrap.py', 'data["BOOTSTRAP_NEXT"] = _bootstrap_next(data, continue_tail_attempted=continue_tail_attempted)', 'bootstrap next directive helper sets data')
require('python/larch/state/bootstrap.py', '_merge_tail_routing_and_next(data, tail=tail, continue_tail_attempted=continue_tail_attempted)', 'bootstrap emits next directive before envelope')
require(skill, 'BOOTSTRAP_NEXT=degraded-prompt', 'SKILL degraded prompt directive')
require(skill, 'BOOTSTRAP_NEXT=rebase-routing', 'SKILL rebase directive')
require(skill, 'BOOTSTRAP_NEXT=step2', 'SKILL step2 directive')
require(skill, 'if `BOOTSTRAP_NEXT` is absent or any other value, treat the bootstrap envelope as malformed and abort with exit `2`', 'SKILL fail-closed malformed BOOTSTRAP_NEXT')
require(skill, 'branch only on `BOOTSTRAP_NEXT=rebase-routing` from the Step 0 bootstrap stdout envelope', 'SKILL absorbed 1.r directive branch')
require(skill, 'For checkpoint `1.r`, enter rebase handling only when `BOOTSTRAP_NEXT=rebase-routing` appears in the Step 0 bootstrap envelope.', 'SKILL Step 1.r directive branch')
require(skill, 'Step `4.r` is folded into the Step 3 `checks-commit-route` composite; `7.r` is folded into the Step 6 `step-6-entry` composite and `7a.r` into `step-7a`, each relaying `CHECKPOINT_NEXT=continue|load-routing` for the same **Rebase Checkpoint Macro** routing', 'SKILL folded 7.r and 7a.r relays keep checkpoint macro routing')
require('skills/implement/references/checks-repair-loop.md', 'skills/implement/scripts/step-6-entry.sh --forked-target "${forked_target:-false}"', 'checks-repair-loop Step 6 initial composite launcher')
require('skills/implement/references/checks-repair-loop.md', 'skills/implement/scripts/step-6-entry.sh --forked-target "${forked_target:-false}" --force-checks true', 'checks-repair-loop Step 6 force-checks repair launcher')
require('skills/implement/references/checks-repair-loop.md', 'both `continue` and `main-agent-edit` repair paths must use `skills/implement/scripts/step-6-entry.sh --forked-target "${forked_target:-false}" --force-checks true`', 'checks-repair-loop Step 6 continue and main-agent force-checks')
forbid(checks_ref, 'python/cli.py implement checks-commit-route --checks-site step6', 'checks-repair-loop old Step 6 checks-commit-route launcher removed')
forbid(checks_ref, 'checks-commit-route --checks-site step6 --commit-site step7', 'checks-repair-loop bare Step 6 checks-commit-route repair re-entry removed')
forbid(skill, 'python/cli.py implement checks-commit-route --checks-site step6', 'SKILL old Step 6 checks-commit-route launcher removed')
forbid(skill, 'branch on envelope `ROUTE=` and `REBASE_RC=` from the Step 0 bootstrap stdout envelope', 'SKILL absorbed 1.r direct ROUTE branch removed')
for needle in [
    'agent degraded-tools-gate', '--codex-present', '--cursor-present',
    'agent check-reviewers',
    'read_session_key CODEX_BINARY_FOUND', 'read_session_key CURSOR_BINARY_FOUND',
]:
    require('skills/implement/scripts/step-0-degraded-gate.sh', needle, f'step-0-degraded-gate legacy {needle}')
require('skills/implement/scripts/step-5-resume.sh', 'set +e\n  commit_output="$(python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" implement commit-route --site step5-resume-handoff)"\n  commit_rc=$?\n  set -e', 'step-5-resume errexit-safe commit-route capture')
require('skills/implement/scripts/step-5-resume.sh', "awk -F= '$1 == \"NEXT_ACTION\" || $1 == \"COMMITTED\" || $1 == \"ERROR\" || $1 == \"SHA\" || $1 == \"COMMIT_OUTCOME\" { print }'", 'step-5-resume NEXT_ACTION KV relay')
require('skills/implement/scripts/step-5-resume.sh', "next_action_count=\"$(printf '%s\\n' \"$commit_output\" | commit_kv_count NEXT_ACTION)\"", 'step-5-resume line-anchored NEXT_ACTION count')
require('skills/implement/scripts/step-5-resume.sh', 'case "$next_action_count:$next_action" in\n    1:continue)', 'step-5-resume NEXT_ACTION continue gate')
require('skills/implement/scripts/step-5-resume.sh', "1:stall)\n      printf 'NEXT_ACTION=%s\\n' \"$next_action\"", 'step-5-resume NEXT_ACTION stall relay')
require('skills/implement/scripts/step-5-resume.sh', "printf '%s\\n' \"$commit_output\" | relay_commit_kvs_without_next_action", 'step-5-resume commit KVs after NEXT_ACTION')
forbid('skills/implement/scripts/step-5-resume.sh', 'porcelain="$(git status --porcelain)"', 'step-5-resume porcelain probe moved to commit-route')
forbid('skills/implement/scripts/step-5-resume.sh', 'review-and-fix commit-fixes --stage-all || true', 'step-5-resume must not mask commit failure')
require('skills/implement/scripts/step-5-resume.sh', 'review-and-fix step5', 'step-5-resume review loop resume')
require(skill, 'Parse `FILES_CHANGED`, `UNTRACKED_BASELINE`, `GIT_PROBE_FAILED`, and exactly one line-anchored composite `NEXT_ACTION=` record from the full composite capture.', 'SKILL line-anchored composite NEXT_ACTION parse')
require(skill, 'Whitespace-token-scan only the first physical line for checks keys', 'SKILL composite checks parsing slice')
require(checks_ref, 're-run the section 2-pinned composite launcher with identical argv before any success-path routing', 'checks repair-loop folded-site re-capture authority')
require(skill, 'When stdout contains `STEP5_REVIEW_STATUS=`, route by the Step 5 status table only.', 'SKILL review-loop envelope branch')
require(skill, 'First, `NEXT_ACTION=stall` means durable stall state is already seeded by commit-route; skip to Step 18.', 'SKILL lacks-envelope NEXT_ACTION stall branch')
require(skill, '`NEXT_ACTION=continue` without `STEP5_REVIEW_STATUS=` is not Step 6 continuation.', 'SKILL NEXT_ACTION continue without envelope is not Step 6')
require(skill, 'missing, duplicated, malformed, or non-zero-without-`NEXT_ACTION` output is an invalid composite envelope', 'SKILL invalid composite envelope branch')
require(skill, 'commit-phase success (`NEXT_ACTION=continue`, `COMMIT_ROUTE_OUTCOME=continue`, or `COMMIT_OUTCOME=ok|noop`) alone does not satisfy NEVER #4', 'SKILL commit-route success alone is not review authorization')
require(skill, 'On `NEXT_ACTION=stall`, skip to Step 18 (stall recovery runs before the final report; durable bail is already seeded by commit-route).', 'SKILL Step 7 composite NEXT_ACTION stall branch')
require('skills/implement/references/self-review.md', 'set prompt-side `STALL_TRACKING=true` and `STALL_STEP=5` when durable seed is absent, and skip to Step 18', 'self-review invalid envelope fail-closed')
require(skill, 'set prompt-side `STALL_TRACKING=true` and `STALL_STEP=7` when durable seed is absent, and skip to Step 18', 'SKILL Step 7 invalid envelope fail-closed')
require('python/larch/implement/dispatch_commit_route.py', 'COMMIT_ROUTE_OUTCOME', 'composite commit route child outcome')
require('python/larch/implement/dispatch_commit_route.py', '"--emit-next-action",\n            "false"', 'composite commit route child pin')
require('python/larch/implement/dispatch_leg.py', 'start_new_session=True', 'composite leg process group session')
require('python/larch/core/process_identity.py', 'validate_process_identity', 'identity validation helper')
require('python/larch/implement/dispatch_leg.py', '_ACTIVE_LEG_JSON_FILE', 'active leg JSON sidecar')
require('python/larch/implement/dispatch_leg.py', 'terminate_validated_process_group', 'active leg identity-validated kill')
require('python/larch/implement/dispatch_leg.py', 'ACTIVE_LEG_KILL_LOG_FILE', 'active leg kill logging')
require('python/larch/implement/dispatch_commit_route.py', 'NEXT_ACTION", value="checks-failed"', 'composite checks-failed routing')
require('skills/implement/scripts/step-8-ship.sh', '--state-file "$IMPLEMENT_TMPDIR/ship-pr-state.sh"', 'step-8 state file forwarding')
exit_matrix = Path('skills/implement/references/ship-pr-exit-matrix.md')
if exit_matrix.is_file():
    exit_text = exit_matrix.read_text()
    for needle in [
        'Python-owned post-driver and OOS-checkpoint routing',
        'Preserve `RESUME_PHASE`, `CALLER_KIND`, and `CONFLICT_FILES`',
        '## Branch semantics',
        '**`complete`**',
        '**`reship`**',
        '**`oos-pipeline`**',
        '**`ci-fix`**',
        '**`operator-bail`**',
        'Post-driver `stall`',
        '**`tool-failure`**',
        'python/cli.py ship seed-initial-state` owns the canonical initial',
        'CI_PASSED=true` does not append execution-issues',
        '## Terminal manifest contract',
        'Terminal runs must leave explicit `steps_ran` values through `python/cli.py final-report write`.',
        'skills/implement/scripts/write-final-report.md',
        'python/cli.py pr checks',
    ]:
        if needle not in exit_text:
            checks.append(f'ship-pr-exit-matrix.md missing {needle!r}')
    for needle in [
        'ship-pr-oos-checkpoint-router.md',
        'ship-pr-ci-fix.md',
    ]:
        if needle not in exit_text:
            checks.append(f'ship-pr-exit-matrix.md missing branch reference {needle!r}')
    for needle in [
        '## Transient retry authority',
        '## OOS cap contract',
        '## Bail-time `steps_ran` invariant',
        '## Active driver ownership notes',
        'ship-pr-net-retries-python.count',
        'oos issue-cap',
        'finalize-state.sh',
        'execution-issues-tracking.md',
        'run the `/issue` pipeline',
        'After the OOS pipeline',
        'run the OOS pipeline when needed',
        '## OOS checkpoint router',
        'run the OOS checkpoint router',
        'runs `oos disposition-checkpoint`',
        'never emits `OOS_CHECKPOINT_RC=0` with `NEXT_ACTION=stall`',
        'On disposition rc 0 and successful bookkeeping',
        'oos-disposition-checkpoint.stderr.log',
        '## autonomous main-agent CI-fix sub-procedure',
        'Run autonomous repair',
        'main-agent-ci-fix-$FAILED_RUN_ID.attempted',
        'gh run-logs',
        'Fix CI failure (main-agent)',
        'Make the minimal repo edit',
        'git add -- <paths>',
        'write-staged-assessment',
    ]:
        if needle in exit_text:
            checks.append(f'ship-pr-exit-matrix.md retains moved or stale prose {needle!r}')
    for n in range(1, 13):
        for pattern in (rf'^  {n}\.', rf'^ {n}\.'):
            if re.search(pattern, exit_text, flags=re.MULTILINE):
                checks.append(f'ship-pr-exit-matrix.md retains moved CI-fix numbered step marker {pattern!r}')
    oos_slice = branch_slice(exit_text, 'oos-pipeline')
    for needle in [
        'security sidecar disposition only',
        '$IMPLEMENT_TMPDIR/security-oos-observations.md',
        'SECURITY.md` `## Security Findings in OOS Workflows`',
        'no public `/issue`',
        'clear the sidecar only after private disposition completes',
        'ship-pr-oos-checkpoint-router.md',
    ]:
        require_text(oos_slice, needle, 'matrix oos-pipeline branch security-sidecar route')
    for needle in ['execution-issues-tracking.md', 'oos-pipeline.md', 'run the `/issue` pipeline']:
        if needle in oos_slice:
            checks.append(f'matrix oos-pipeline branch retains stale routing {needle!r}')
    ci_fix_slice = branch_slice(exit_text, 'ci-fix')
    require_text(ci_fix_slice, 'FORKED_TARGET=true', 'matrix ci-fix branch keeps fork skip')
    require_text(ci_fix_slice, 'ship-pr-ci-fix.md', 'matrix ci-fix branch names child reference')
    require_text(ci_fix_slice, 'MANDATORY: READ ENTIRE FILE', 'matrix ci-fix branch carries mandatory-read marker')
    if ci_fix_slice.find('FORKED_TARGET=true') > ci_fix_slice.find('ship-pr-ci-fix.md'):
        checks.append('matrix ci-fix mandatory read must follow fork skip inline text')
    operator_slice = branch_slice(exit_text, 'operator-bail')
    require_text(operator_slice, 'python/cli.py pr checks', 'matrix operator-bail pr checks fallback')
    require_text(operator_slice, 'failed_run_id', 'matrix operator-bail empty failed run id wording')
    if '## Post-driver branch table' in exit_text:
        checks.append('ship-pr-exit-matrix.md must not add a parallel post-driver branch table')
oos_router = Path('skills/implement/references/ship-pr-oos-checkpoint-router.md')
if oos_router.is_file():
    router_text = oos_router.read_text()
    for needle in [
        'without assuming any prior OOS pipeline body ran',
        '## Security sidecar disposition',
        '`security-oos-observations.md` is private-disposition material.',
        'Read `$IMPLEMENT_TMPDIR/security-oos-observations.md`',
        'SECURITY.md` `## Security Findings in OOS Workflows`',
        'no public `/issue`',
        'clear the sidecar only after private disposition completes',
        'Public `/issue` filing is forbidden on this branch.',
        'Checkpoint stall is expected until SECURITY.md disposition clears the sidecar.',
        'OOS issue cap enforcement applies only on the pre-driver `python/cli.py oos file` path for non-security OOS',
        'does not run cap enforcement or public issue batch emission',
        'python/cli.py implement step-8-oos-checkpoint',
        'runs `oos disposition-checkpoint`',
        'emits exactly one `NEXT_ACTION=`',
        'Its process rc is 0 whenever',
        'returns non-zero only when no `NEXT_ACTION` is emitted',
        'never emits `OOS_CHECKPOINT_RC=0` with `NEXT_ACTION=stall`',
        'On disposition rc 0 and successful bookkeeping',
        'writes run-scoped `run-statistics.md`',
        'steps_ran.step9a1=true',
        'OOS_PENDING=false',
        'NEXT_ACTION=reship',
        'with fallback counts only when ndjson is absent',
        'ship._patch_ship_state_keys',
        'leaves `OOS_PENDING` unchanged',
        'writes no stats, and clears no state',
        'On disposition rc 1, rc 2, 126, 127, or other non-zero rc',
        'OOS_CHECKPOINT_RC=0',
        'oos-disposition-checkpoint.stderr.log',
        'The checkpoint wrapper preserves non-empty child-written',
        'Child stdout is not forwarded on success',
        'OOS-checkpoint `stall` is distinct from post-driver `stall`',
    ]:
        require_text(router_text, needle, 'ship-pr-oos-checkpoint-router.md security/checkpoint contract')
    for needle in [
        '## OOS cap contract',
        '## Bail-time `steps_ran` invariant',
        'oos issue-cap',
        '/issue --input-file',
        'run the `/issue` pipeline',
    ]:
        if needle in router_text:
            checks.append(f'ship-pr-oos-checkpoint-router.md retains forbidden {needle!r}')
else:
    checks.append('missing skills/implement/references/ship-pr-oos-checkpoint-router.md')
ci_fix_ref = Path('skills/implement/references/ship-pr-ci-fix.md')
if ci_fix_ref.is_file():
    ci_fix_text = ci_fix_ref.read_text()
    for needle in [
        '# Ship PR autonomous CI-fix',
        'Python driver non-zero routing',
        'first-fixer-non-health',
        'ship-pr-internal-lint-fix',
        'ci-local-unfixable:*',
        'exact `local-unfixable`',
        'ci-fix-exhausted',
        '.ship-route-exit-handoff.env',
        'larch_io.read_kvs',
        'ledger_ready=true',
        'stall-recovery record-escalation',
        'If `FAILED_RUN_ID` is empty',
        'python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" pr checks',
        'route to `operator-bail` or post-driver `stall`',
        'skip steps 3-12',
        'including sentinel writes, `gh run-logs`, autonomous repair, commit, push, and ship re-entry',
        'main-agent-ci-fix-$FAILED_RUN_ID.attempted',
        'main-agent-ci-fix.count',
        'gh run-logs',
        'python/cli.py" push branch',
        'python/cli.py checks run-relevant --site step8-main-agent-fix',
        'Fix CI failure (main-agent)',
        'Make the minimal repo edit',
        'git add -- <paths>',
        'run-log refresh',
        'Do not rerun architectural-guidelines Phase A',
        'NEXT_ACTION=guidelines-assessment',
        're-invoke `step-8-ship.sh`',
    ]:
        require_text(ci_fix_text, needle, 'ship-pr-ci-fix.md CI-fix body')
    for n in range(1, 13):
        require_text(ci_fix_text, f'  {n}.', f'ship-pr-ci-fix.md numbered sub-step {n}')
    require_near('skills/implement/references/ship-pr-ci-fix.md', 'FAILED_RUN_ID', 'pr checks', 'ship-pr-ci-fix empty failed run id fallback', 600)
else:
    checks.append('missing skills/implement/references/ship-pr-ci-fix.md')
write_final_ref = Path('skills/implement/scripts/write-final-report.md')
if write_final_ref.is_file():
    write_final_text = write_final_ref.read_text()
    for needle in [
        '## Bail-time `steps_ran` invariant',
        'If the run ends before Step 9a.1 or before `oos file` succeeds',
        'explicit `manifest.json` `steps_ran.step9a1=true` is valid only together with that file',
        '`python/cli.py final-report write` records explicit `steps_ran.step9a1=false`',
        '`python/cli.py run-log verify-completeness` treats missing/null `steps_ran` like `jq',
    ]:
        require_text(write_final_text, needle, 'write-final-report.md bail-time steps_ran invariant')
else:
    checks.append('missing skills/implement/scripts/write-final-report.md')
matrix_read = '**MANDATORY: READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/ship-pr-exit-matrix.md` completely.'
require(skill, matrix_read, 'ship-pr exit matrix Step 8+ entry read')
require_near(
    skill,
    matrix_read,
    '"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py ship route-exit',
    'Step 8+ matrix read before route-exit fence',
    1200,
)
require_near(
    skill,
    matrix_read,
    '"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py ship pre-driver',
    'Step 8+ matrix read before pre-driver fence',
    1600,
)
require('python/larch/cli.py', '("ship", "route-exit"): ("larch.implement.implement_dispatch", "ship_route_exit_main")', 'ship route-exit registry')
require('python/larch/cli.py', '("ship", "route-exit"),', 'ship route-exit machine stdout')
require('python/larch/cli.py', '("implement", "commit-route"),', 'commit-route machine stdout')
require('python/larch/cli.py', '("implement", "step-8-oos-checkpoint"),', 'step-8-oos-checkpoint machine stdout')
require(skill, '**`stall`** (post-driver only)', 'SKILL post-driver stall paragraph')
require(skill, '**`NEXT_ACTION=stall`** (OOS-checkpoint stall)', 'SKILL OOS-checkpoint stall paragraph')
require(skill, '$IMPLEMENT_TMPDIR/.step-8-ship-handoff.json` is absent', 'SKILL json absent setup-failure gate')
require(skill, 'ship-pr-oos-checkpoint-router.md', 'SKILL oos-pipeline child reference')
require(skill, 'ship-pr-ci-fix.md', 'SKILL ci-fix child reference')
forbid(skill, 'run the autonomous CI-fix sub-procedure from `ship-pr-exit-matrix.md`', 'SKILL retired matrix CI-fix authority')
forbid(skill, 'autonomous CI-fix sub-procedure from `ship-pr-exit-matrix.md`', 'SKILL retired matrix CI-fix authority substring')
forbid(skill, 'Follow `step18-cleanup.md` for the escalation-success report procedure', 'SKILL retired Step 18a.5 cleanup procedure pointer')
for needle in [
    'After the OOS pipeline',
    'run the OOS pipeline when needed',
    'run the `/issue` pipeline',
]:
    forbid(skill, needle, 'SKILL stale OOS pipeline wording')
for needle in [
    'security sidecar disposition only',
    'Do not load `execution-issues-tracking.md`, do not load or run `oos-pipeline.md`, and do not call `/issue` on this branch.',
    'Read `$IMPLEMENT_TMPDIR/security-oos-observations.md`',
    'SECURITY.md` `## Security Findings in OOS Workflows`',
    'clear the sidecar only after private disposition completes',
    'Expect the checkpoint to stall while `security-oos-observations.md` remains non-empty',
    'complete security-sidecar private disposition when applicable, then invoke the checkpoint wrapper',
    'When `RESUME_PHASE=ship-pr-rrr-phase14` and `CALLER_KIND=ship_pr_pre_push`, **MANDATORY: READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/conflict-resolution.md` completely',
]:
    require(skill, needle, 'SKILL security-sidecar branch or phase14 conflict pin')
require_near(skill, 'ship-pr-oos-checkpoint-router.md', 'step-8-oos-checkpoint.sh', 'oos router mandatory read before checkpoint fence', 900)
require_near(skill, '**OOS checkpoint fence.**', 'ship-pr-oos-checkpoint-router.md', 'oos router read before checkpoint fence header', 1500)
skill_ci_fix_slice = branch_slice(skill_text, 'ci-fix')
require_text(skill_ci_fix_slice, 'ship-pr-ci-fix.md', 'SKILL ci-fix branch names child reference')
require_text(skill_ci_fix_slice, 'MANDATORY: READ ENTIRE FILE', 'SKILL ci-fix branch carries mandatory-read marker')
require_near(skill, 'ship-pr-ci-fix.md', '**operator-bail**', 'ci-fix mandatory read precedes operator-bail skeleton', 900)
forbid(skill, 'step18a5-filing.md', 'SKILL must not reference retired step18a5-filing.md')
forbid(skill, '**Post-driver branch table**', 'SKILL post-driver branch table moved to matrix')
forbid(skill, '**Initial state seeder contract.**', 'SKILL full initial state seeder contract moved to matrix')
forbid(skill, '**Bail-time `steps_ran` invariant', 'SKILL bail-time steps_ran invariant moved to matrix')
forbid(skill, '**Execution-issues checkpoint**', 'SKILL execution-issues checkpoint moved to matrix')
forbid(skill, 'The OOS cap contract lives in', 'SKILL OOS cap contract moved to matrix')
forbid(skill, 'The active Step 8+ driver writes `finalize-state.sh`', 'SKILL active driver ownership block moved to matrix')
forbid(skill, '**Python driver routing:**', 'legacy Python driver routing removed')
forbid(skill, 'MANDATORY: READ ENTIRE FILE on any non-zero active Step 8+ driver exit', 'legacy non-zero driver mandatory block removed')
for needle in [
    'non-security accepted OOS is filed by the pre-driver `${CLAUDE_PLUGIN_ROOT}/python/cli.py oos file` path before `step-8-ship.sh`',
    'On `NEXT_ACTION=oos-pipeline`, read `$IMPLEMENT_TMPDIR/security-oos-observations.md`',
    'with no `/issue` call',
    'Only checkpoint `NEXT_ACTION=reship` may write run statistics, stamp the manifest, and clear `OOS_PENDING=false`',
    'Do not run prompt-side direct `oos disposition-checkpoint`, compose run statistics, or patch `OOS_PENDING=false`',
    'after security-sidecar disposition when applicable and before or at the Step 8 OOS checkpoint wrapper on the `oos-pipeline` branch, or after pre-driver `oos file` on the normal path',
]:
    require(skill, needle, 'NEVER #14/#15 Python OOS split pin')
require('skills/implement/references/oos-pipeline.md', 'Do not ask the operator for confirmation before the batch call, and do not use `AskUserQuestion` here. Accepted non-security OOS disposition is automatic for this checkpoint.', 'legacy OOS pipeline must not ask confirmation before issue batch')
cleanup_ref = Path('skills/implement/references/step18-cleanup.md').read_text()
for needle in [
    'Resolve `STALL_TRACKING` from four layers',
    'Mode-specific reminders (`--draft`, `--merge`',
    'The `larch-tokens-&lt;slug&gt;.jsonl` token ledger',
]:
    if needle not in cleanup_ref:
        checks.append(f'step18-cleanup.md missing relocated authority {needle!r}')
for needle in [
    'stall-recovery-escalation-success.env',
    'Escalation evidence is only',
    'step18a5-filing.md',
    'Breakout teardown is owned by `step-18.sh --phase finalize` on stall-recovery and escalation-filing branches.',
]:
    if needle in cleanup_ref:
        checks.append(f'step18-cleanup.md must not retain removed escalation-filing authority {needle!r}')
for needle in [
    'If eligible, Main Claude reads',
    '/larch:issue --input-file',
    'Write `stall-recovery-escalation-success.env` atomically after filed, commented, fallback-printed, dry-run, or operator-action skip result',
    'compose-report --report-kind escalation-success',
]:
    if needle in cleanup_ref:
        checks.append(f'step18-cleanup.md retains moved filing body {needle!r}')
step18a5_filing = Path('skills/implement/references/step18a5-filing.md')
if step18a5_filing.is_file():
    checks.append('step18a5-filing.md must be deleted: escalation-success filing removed from /implement')
forbid(skill, 'Resolve `STALL_TRACKING` from four layers', 'SKILL four-layer STALL_TRACKING detail moved to cleanup ref')
forbid(skill, 'compose-report --report-kind escalation-success', 'SKILL Step 18a.5 procedure body moved to cleanup ref')
forbid(skill, 'Normal teardown is owned by `step-18.sh --phase finalize`', 'SKILL Step 18b extended teardown prose moved to cleanup ref')
forbid(skill, 'Mode-specific reminders (`--draft`, `--merge`', 'SKILL Step 18b warning replay detail moved to cleanup ref')
forbid(skill, 'The `larch-tokens-&lt;slug&gt;.jsonl` token ledger', 'SKILL closing marks rationale moved to cleanup ref')
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
if 'compose-report --report-kind escalation-success' in stall_ref:
    checks.append('stall-recovery.md must not retain escalation-success compose procedure')
require(skill, 'every Step 8+ re-entry goes through `${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-8-ship.sh` only', 'NEVER #13 default-path wrapper re-entry')
for needle in [
    '_restore_finalize=false',
    'restore-finalize-state',
    'implement-finalize teardown',
    'DESIGN_TMPDIR=\'\' LARCH_TIMING_SKILL=implement',
]:
    require('skills/implement/scripts/step-18.sh', needle, f'step-18 {needle}')
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
require('skills/implement/scripts/step-8-ship.sh', ': >"$HANDOFF_CAPTURE"', 'step-8-ship truncates capture')
require('skills/implement/scripts/step-8-ship.sh', 'tee -a "$HANDOFF_CAPTURE"', 'step-8-ship captures stdout through tee')
require('skills/implement/scripts/step-8-ship.sh', 'rm -f "$HANDOFF_JSON"', 'step-8-ship unlinks stale json on rc-only exit')
require('skills/implement/scripts/step-8-ship.sh', 'trap persist_handoff EXIT', 'step-8-ship persists sidecars via EXIT trap')
require('skills/implement/scripts/step-8-oos-checkpoint.sh', 'implement step-8-oos-checkpoint', 'step-8-oos-checkpoint delegates to Python authority')
forbid('skills/implement/scripts/step-8-oos-checkpoint.sh', 'oos disposition-checkpoint', 'step-8-oos-checkpoint wrapper does not call disposition directly')

bootstrap_recovery_ref = 'skills/implement/references/bootstrap-recovery.md'
self_review_ref = 'skills/implement/references/self-review.md'
forbid(skill, '**Degraded prompt handling.**', 'SKILL degraded-prompt body moved to bootstrap-recovery.md')
forbid(skill, 'Step 0 dirty-tree recovery gate:', 'SKILL dirty-tree gate moved to bootstrap-recovery.md')
forbid(skill, '.dirty-tree-prompted-step0-plan-materialize', 'SKILL dirty-tree prompt sentinel moved to bootstrap-recovery.md')
forbid(skill, 'Present the relayed degraded explanation block verbatim (from bootstrap stderr during Step 0)', 'SKILL verbose degraded-prompt table prose moved to bootstrap-recovery.md')
forbid(skill, 'Enter dirty-tree recovery. Preserve `$IMPLEMENT_TMPDIR`', 'SKILL verbose dirty-recovery table prose moved to bootstrap-recovery.md')
forbid(skill, 'python/cli.py timing telemetry-mark --implement-tmpdir "$IMPLEMENT_TMPDIR" --label "Step 5: code review"', 'SKILL self-review telemetry fence moved to self-review.md')
forbid(skill, 'python/cli.py review-and-fix write-pre-self-review-snapshot', 'SKILL self-review snapshot fence moved to self-review.md')
forbid(skill, 'checks-commit-route --checks-site step5-self-review', 'SKILL self-review composite fence moved to self-review.md')
forbid(skill, 'python/cli.py review-and-fix write-self-review-tally', 'SKILL self-review tally fence moved to self-review.md')
forbid(skill, 'timeout: 14700000', 'SKILL self-review timeout pin moved to self-review.md')
forbid(skill, 'set prompt-side `STALL_TRACKING=true` and `STALL_STEP=5` when durable seed is absent', 'SKILL self-review invalid-envelope prose moved to self-review.md')

bootstrap_recovery_text = Path(bootstrap_recovery_ref).read_text()
for needle in [
    '**Degraded prompt handling.**',
    'Step 0 dirty-tree recovery gate:',
    '.dirty-tree-prompted-step0-plan-materialize',
    'Present the relayed degraded explanation block verbatim',
    'AskUserQuestion',
    'Continue (reduced panel — unavailable tools dropped, no cross-tool or Claude padding)',
    'Abort',
    'PRESENCE_INPUT_EMPTY=true',
    'DEGRADED_PROMPT_REQUIRED=true',
    'DEGRADED_HARD_FAIL=true',
    '.degraded-tools-gate-prompted',
    'STATUS=dirty-or-unknown',
    'STAGE=step0-plan-materialize',
    'RECOVERY_REQUIRED=true',
    'RECOVERY_REQUIRED=false',
    'STATUS=clean',
    'python/cli.py dirty-tree checkpoint',
    'Restore a clean tree and continue',
    'Cancel this implement run',
    'unset IMPLEMENT_BAIL_REASON',
    'IMPLEMENT_BAIL_REASON',
    'BRANCH_NAME',
    'BRANCH_ACTION',
    'PLAN_FILE',
    'Bootstrap edit gate (NEVER #21)',
    'LARCH_CLAUDE_PID="$PPID" "${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-0-bootstrap.sh" --mode resume',
    'LARCH_CLAUDE_PLUGIN_ROOT=',
    'Parse the resumed wrapper stdout before',
]:
    if needle not in bootstrap_recovery_text:
        checks.append(f'bootstrap-recovery.md missing relocated authority {needle!r}')

self_review_text = Path(self_review_ref).read_text()
for needle in [
    'python/cli.py timing telemetry-mark --implement-tmpdir "$IMPLEMENT_TMPDIR" --label "Step 5: code review" || true',
    'python/cli.py review-and-fix write-pre-self-review-snapshot',
    'python/cli.py implement checks-commit-route --checks-site step5-self-review --commit-site step5-self-review',
    'python/cli.py review-and-fix write-self-review-tally',
    'timeout: 14700000',
    'Immediate-background required',
    'set prompt-side `STALL_TRACKING=true` and `STALL_STEP=5` when durable seed is absent, and skip to Step 18',
    'NEXT_ACTION=main-agent-edit',
    're-run this same composite launcher with identical argv',
    'parse exactly one line-anchored composite `NEXT_ACTION=` record',
    '$IMPLEMENT_TMPDIR/plan.txt',
    'git diff "$(git merge-base HEAD origin/main)"..HEAD',
    'execution-issues-tracking.md',
    'correctness: logic errors',
    'security: injection',
    'OOS triage policy',
    '### [Code Review] Self-review accepted',
    'rejected-findings.md',
    '> **Continue after child returns.**',
    'Checks Failure Entry Macro',
    '--site step5-self-review',
    '$IMPLEMENT_TMPDIR/self-review-accepted.md',
]:
    if needle not in self_review_text:
        checks.append(f'self-review.md missing relocated authority {needle!r}')
if old_inline_combo.search(self_review_text):
    checks.append('self-review.md must invoke the Checks Failure Entry Macro instead of restating REDACTED_LOG_FILE and checks-repair-loop.md')

# Step 4 skip prose must reference implement commit, not git-commit.sh.
require(skill, 'Skip the `implement commit` invocation.', 'Step 4 skip prose references implement commit')
forbid(skill, 'Skip the `git-commit.sh` invocation.', 'Step 4 skip prose must not reference git-commit.sh')
# The fabricated skill-local commit helper path must not appear under skills/implement/.
import subprocess
fabricated_commit_helper = 'skills/implement/scripts/' + 'git-commit.sh'
r = subprocess.run(
    ['git', 'grep', '-rl', fabricated_commit_helper, '--', 'skills/implement/'],
    capture_output=True, text=True
)
if r.stdout.strip():
    checks.append(f'fabricated commit helper path referenced under skills/implement/: {r.stdout.strip()}')

for raw in Path('python/migrated-scripts.tsv').read_text(encoding='utf-8').splitlines():
    line = raw.strip()
    if not line or line.startswith('#') or '#3678' not in line:
        continue
    retired_path = line.split('\t')[0].strip()
    if retired_path and Path(retired_path).exists():
        checks.append(f'retired #3678 path still exists: {retired_path}')
for retired_ref in [
    'skills/implement/references/summary-comment-template.md',
    'skills/implement/references/pr-body-template.md',
    'skills/implement/references/step-16-17-sentinel.md',
]:
    if Path(retired_ref).is_file():
        checks.append(f'retired reference still exists: {retired_ref}')
for retired_basename in ['commit-review-fixes.md', 'write-rejected-findings.md', 'check-review-changes.md']:
    forbid(skill, retired_basename, f'SKILL must not cite retired {retired_basename}')

if checks:
    print('\n'.join(checks), file=sys.stderr)
    sys.exit(1)
print('PASS: test-implement-structure.sh (wrapperized prompt structure)')
PY
