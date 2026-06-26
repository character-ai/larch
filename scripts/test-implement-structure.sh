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
checks_ref='skills/implement/references/checks-repair-loop.md'
step5_branches_ref='skills/implement/references/step5-review-branches.md'
# New mandatory references.
for ref in ['rebase-checkpoint-routing.md','phantom-probe.md','ship-pr-exit-matrix.md','step18-cleanup.md']:
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
    'python/preflight.py',
    'python/test_preflight.py',
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
require('python/preflight.py', 'SUCCESS_ENVELOPE_KEYS', 'preflight success envelope key tuple')
require('python/preflight.py', 'def _validate_success_envelope', 'preflight validation helper')
require('python/preflight.py', 'duplicate key', 'preflight duplicate key validation')
require('python/preflight.py', 'RESUME must be true or false', 'preflight resume validation')
require('python/preflight.py', 'BYPASS_COUNT must be numeric', 'preflight bypass count validation')
require('python/preflight.py', '"ADMISSION_RESULT"', 'preflight emits admission result')
require('python/preflight.py', '"RESUME"', 'preflight emits resume')
require('python/preflight.py', '"PLAN_PATH"', 'preflight emits plan path')
require('python/preflight.py', '"ISSUE_JSON_PATH"', 'preflight emits issue json path')
require('python/preflight.py', '"BYPASS_COUNT"', 'preflight emits bypass count')
require('python/preflight.py', 'force-bypass.log', 'preflight bypass log destination')
require('python/preflight.py', 'json.load', 'preflight uses stdlib json')
require('python/test_preflight.py', 'test_preflight_success_emits_kv_and_forwards_repo', 'preflight test success coverage')
require('python/test_preflight.py', 'test_preflight_force_missing_plan_uses_raw_body', 'preflight test force coverage')
require('python/test_preflight.py', 'test_preflight_force_short_flag_missing_plan_uses_raw_body', 'preflight test -f coverage')
require(skill, '`--force` and `-f` both set `force_requested=true`', 'SKILL -f alias parse rule')
require(skill, '`--force` / `-f` and `--draft` together', 'SKILL -f draft mutex wording')
require('skills/im/SKILL.md', '`--force`, `-f`', 'im SKILL forwards -f alias')
require('python/test_bootstrap.py', 'test_invoke_refuses_symlinked_bootstrap_routing_env', 'bootstrap refusal-path test')
require('python/test_bootstrap.py', 'BOOTSTRAP_NEXT=cleanup', 'bootstrap refusal-path emits directive')
require('python/test_bootstrap.py', 'BOOTSTRAP_NEXT=step2', 'bootstrap invoke emits step2 directive')
require('python/test_bootstrap.py', 'BOOTSTRAP_NEXT=degraded-prompt', 'bootstrap invoke emits degraded directive')
require('python/test_bootstrap.py', 'BOOTSTRAP_NEXT=rebase-routing', 'bootstrap resume malformed route directive test')
forbid(skill, '${force_requested:+--force}', 'SKILL preflight force argv')
forbid(skill, 'If `false` and `force_requested=false`, print `**❌ Issue #<N> has no larch:plan block', 'SKILL prompt-side missing-plan fallback prose')
forbid(skill, 'If the script exits **1** and prints `MALFORMED=...`, then when `force_requested=false`', 'SKILL prompt-side malformed-plan fallback prose')
forbid(skill, 'single-line envelope', 'SKILL must not describe single-line envelope')
forbid(skill, 'full seven-key envelope', 'SKILL must not require envelope on exit 2')


launcher = 'bash "$IMPLEMENT_TMPDIR/larch-run.sh" '
for script in [
    'skills/implement/scripts/step-2-entry.sh --coder "$coder"',
    'skills/implement/scripts/step-2-post-dispatch.sh',
    'skills/implement/scripts/run-step-checks.sh --site step3',
    'skills/implement/scripts/step-5-review.sh',
    'python/cli.py implement checks-commit-route --checks-site step5-self-review --commit-site step5-self-review',
    'python/cli.py implement checks-step5-resume --checks-site step5-review-fixes --final-round-num "$FINAL_ROUND_NUM"',
    'skills/implement/scripts/step-5-resume.sh --final-round-num "$FINAL_ROUND_NUM" --record-only',
    'skills/implement/scripts/step-6-entry.sh',
    'python/cli.py implement checks-commit-route --checks-site step6 --commit-site step7 --emit-step7-breadcrumb --rebase-checkpoint-7r --forked-target "${forked_target:-false}"',
    'python/cli.py implement step-7a --implement-tmpdir "$IMPLEMENT_TMPDIR"',
    'python/cli.py ship pre-driver',
    'skills/implement/scripts/step-8-ship.sh',
    'skills/implement/scripts/step-8-oos-checkpoint.sh',
    'skills/implement/scripts/step-18.sh --phase gate --stall-tracking-memory "${STALL_TRACKING:-false}"',
    'skills/implement/scripts/step-18.sh --phase finalize --step17-emitted "${STEP17_EMITTED_FOR_STEP18:-false}"',
]:
    require(skill, launcher + script, f'SKILL launcher wrapper {script}')

require(skill, 'python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" implement step-16-17 --implement-tmpdir "$IMPLEMENT_TMPDIR"', 'SKILL direct Step 16-17 Python CLI call')

for needle in [
    'BASE_ARGS=()',
    'session read-key --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TOKEN_SESSION_ID',
    '_oos_chk_err=',
    '_restore_finalize=false',
]:
    forbid(skill, needle, 'wrapperized SKILL')

# Script/md sibling and executable coverage for new wrappers.
wrappers = ['step-0-bootstrap','step-0-degraded-gate','step-2-entry','step-2-post-dispatch','run-step-checks','step-5-review','step-5-resume','step-6-entry','step-8-python-guard','step-8-seed-initial','step-8-ship','step-8-oos-checkpoint','step-18']
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
forbid(skill, 'review-and-fix commit-fixes <specific-files>', 'Step 7 must stage all review fixes')
forbid('python/review_and_fix.py', '"git", "add", "-A"', 'commit-fixes must not stage unrelated paths')
forbid('python/review_and_fix.py', '"git", "add", "--pathspec-from-file"', 'staging owned by commit_main only')
require('python/review_and_fix.py', '"--only",\n        "--pathspec-from-file"', 'commit-fixes pathspec-only commit')
require('python/implement_dispatch.py', 'LARCH_TIMING_LEDGER', 'commit-implementation telemetry self-rehydration')
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
require('python/bootstrap.py', 'preflight-tmpdir.env', 'bootstrap preflight tmpdir persistence')
require('skills/implement/scripts/step-8-ship.sh', 'read_state_key', 'step-8 ship state rehydration')
require('skills/implement/scripts/step-8-python-guard.sh', 'sys.version_info >= (3, 11)', 'step-8 shared python 3.11 guard')
require('skills/implement/scripts/step-8-python-guard.sh', '"outcome":"STALLED"', 'step-8 shared stalled JSON stdout')
require('skills/implement/scripts/step-8-python-guard.sh', 'exit 4', 'step-8 shared stale-python exit 4')
require('skills/implement/scripts/step-8-ship.sh', 'step-8-python-guard.sh', 'step-8 ship delegates python guard')
require('skills/implement/scripts/step-8-ship.sh', 'python/cli.py" implement clone-tag', 'step-8 ship uses clone-tag CLI')
require('python/implement_dispatch.py', 'def clone_tag_main', 'implement clone-tag CLI handler')
require('skills/implement/scripts/step-8-ship.sh', 'python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" ship pr', 'step-8 python ship invocation')
require('python/cli.py', '("ship", "pre-driver"): ("implement_dispatch", "ship_pre_driver_main")', 'ship pre-driver CLI registry')
require('python/cli.py', '("ship", "pre-driver"),', 'ship pre-driver machine stdout contract')
require('python/cli.py', 'NEXT_ACTION=stall', 'ship pre-driver pre-version stall fast path')
require('python/implement_dispatch.py', 'def ship_pre_driver_main', 'ship pre-driver handler')
require('python/implement_dispatch.py', '["implement", "step-8-python-guard"]', 'ship pre-driver runs guard first')
require('python/implement_dispatch.py', '["implement", "step-8-seed-initial"]', 'ship pre-driver conditional seeder')
require('python/implement_dispatch.py', '["oos", "file", "--implement-tmpdir", str(implement_tmpdir)]', 'ship pre-driver runs oos file')
require('python/implement_dispatch.py', 'value="halt-seed"', 'ship pre-driver seed halt token')
require('python/implement_dispatch.py', 'value="halt-oos"', 'ship pre-driver oos halt token')
forbid(skill, launcher + 'skills/implement/scripts/step-8-python-guard.sh', 'SKILL standalone step-8 guard fence removed')
forbid(skill, launcher + 'skills/implement/scripts/step-8-seed-initial.sh', 'SKILL standalone step-8 seeder fence removed')
forbid(skill, launcher + 'python/cli.py oos file --implement-tmpdir "$IMPLEMENT_TMPDIR"', 'SKILL standalone pre-driver oos fence removed')
require('skills/implement/scripts/step-0-bootstrap.sh', 'LARCH_CLAUDE_PID="${LARCH_CLAUDE_PID:-$PPID}"', 'step-0 wrapper claude pid export')
require(skill, 'python/cli.py ship seed-initial-state', 'ship state initial seeder authority')
require('skills/implement/scripts/step-8-seed-initial.sh', '--no-admin-fallback', 'ship state no-admin fallback seeder argv')
require('python/ship.py', 'NO_ADMIN_FALLBACK', 'ship state no-admin fallback allowed key')
require(skill, '## NEVER List', 'NEVER list heading')
require(skill, 'NEVER call `ScheduleWakeup`', 'NEVER #8 ScheduleWakeup pin')
require(skill, 'Do not spawn a Monitor', 'NEVER #8 background-monitor ban')
require(skill, 'Bootstrap edit gate (NEVER #21)', 'NEVER #21 bootstrap edit gate pin')
for script, timeout in [
    (launcher + 'skills/implement/scripts/step-5-review.sh', 'timeout: 21600000'),
    (launcher + 'python/cli.py implement checks-commit-route --checks-site step5-self-review', 'timeout: 14700000'),
    (launcher + 'python/cli.py implement checks-step5-resume --checks-site step5-review-fixes', 'timeout: 32700000'),
    (launcher + 'python/cli.py implement checks-commit-route --checks-site step6', 'timeout: 15600000'),
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
require('python/bootstrap.py', 'ship-seed-input.env', 'bootstrap ship seed input writer')
require(skill, launcher + 'skills/implement/scripts/step-2-post-dispatch.sh', 'phantom 2-post-dispatch probe')
require(skill, 'regardless of wrapper exit code', 'post-dispatch phantom parse before wrapper routing')
require('skills/implement/scripts/step-8-ship.sh', 'python/cli.py" git phantom-probe --step 8-pre-ship', 'phantom 8-pre-ship probe moved into ship wrapper')
forbid(skill, launcher + 'scripts/' + 'phantom-probe-with-warn.sh --step 8-pre-ship', 'standalone orchestrator 8-pre-ship fence removed')
rebase_ref = Path('skills/implement/references/rebase-checkpoint-routing.md').read_text()
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
]:
    if needle not in rebase_ref:
        checks.append(f'rebase-checkpoint-routing.md missing {needle!r}')
phantom_ref = Path('skills/implement/references/phantom-probe.md').read_text()
for needle in ['2-post-dispatch', 'step-2-post-dispatch.sh', '8-pre-ship', 'Do not probe when `STATUS=claude_fallback`']:
    if needle not in phantom_ref:
        checks.append(f'phantom-probe.md missing {needle!r}')
require('python/larch/git/push.py', '--forked-target', 'rebase probe forked target flag')
require('python/larch/git/push.py', 'CHECKPOINT_NEXT', 'rebase probe checkpoint directive')
require('python/bootstrap.py', '"CHECKPOINT_NEXT"', 'bootstrap checkpoint directive relay')
require(skill, 'CHECKPOINT_NEXT=continue|load-routing', 'SKILL checkpoint directive macro')
require(skill, 'The `7a.r` macro skip is `CHECKPOINT_NEXT`-only', 'SKILL Step 7a checkpoint-only macro skip')
require('skills/implement/references/rebase-checkpoint-routing.md', '--forked-target true|false', 'rebase probe docs')
require('skills/implement/references/rebase-checkpoint-routing.md', 'CHECKPOINT_NEXT=continue|load-routing', 'rebase checkpoint directive docs')
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

# Step 17/18 marker handoff contract must exist without re-spelling the shared algorithm.
require('python/closeout.py', '---LARCH-SUMMARY-FINAL-BEGIN---', 'step-16-17 begin marker literal')
require('python/closeout.py', '---LARCH-SUMMARY-FINAL-END---', 'step-16-17 end marker literal')
require(skill, 'skills/shared/final-summary-emit.md', 'SKILL shared final-summary emit pointer')
require(skill, 'markers `---LARCH-SUMMARY-FINAL-BEGIN---` / `---LARCH-SUMMARY-FINAL-END---`', 'SKILL implement marker pair binding')
require(skill, 'captured foreground `python/cli.py implement step-16-17` Bash wrapper stdout', 'SKILL Step 17 captured foreground stdout source')
require(skill, 'captured foreground `step-18.sh --phase finalize` Bash wrapper stdout', 'SKILL Step 18 captured foreground stdout source')
require(skill, 'not `<task-notification>` output', 'SKILL implement source is not task notification output')
require(skill, 'Read fallback `forbidden`', 'SKILL Read fallback forbidden binding')
require(skill, 'sidecar follow-on `forbidden`', 'SKILL sidecar follow-on forbidden binding')
require(skill, 'do not Read that file on the Step 17 primary path', 'SKILL no Read-tool Step 17 primary path')
require(skill, 'Do not Read `summary-final.md` on the Step 18 path because teardown may have removed the tmpdir.', 'SKILL Step 18 no Read fallback')
require(skill, '**⚠ Step 18: EMIT_BODY=true but marker pair missing from finalize stdout.**', 'SKILL Step 18 missing-marker warning')
require(skill, 'Relay teardown tail records verbatim from captured finalize stdout.', 'SKILL Step 18 tail relay')
cleanup_read = '**MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/step18-cleanup.md` completely.'
require_near(
    skill,
    cleanup_read,
    'bash "$IMPLEMENT_TMPDIR/larch-run.sh" skills/implement/scripts/step-18.sh --phase gate',
    'Step 18 cleanup read before gate fence',
    900,
)
require(skill, '#### Step 18a.5 — Escalation-success report gate', 'SKILL Step 18a.5 section presence')
require(skill, 'Do not run Step 18a.5 or `--phase finalize` on this path.', 'SKILL Step 18a.5 skip on stall recovery path')
require(skill, 'Step 18a.5 runs before this fence and remains prompt-side.', 'SKILL Step 18a.5 runs before finalize fence')
require(skill, 'proceed without re-running `--phase gate`.', 'SKILL Step 18a no gate re-run after terminal recovery')
require(skill, '**Escalation recording owners.**', 'SKILL escalation recording owners preserved')
require(skill, 'Repeat any external reviewer warnings from earlier', 'SKILL Step 18b warnings preserved')
require(skill, 'Cap the per-run token/timing ledgers **before** teardown removes them.', 'SKILL #3425 closing marks preserved')
forbid(skill, 'When `EMIT_BODY=true` and `WFR_RC=0` and `[ -s "$IMPLEMENT_TMPDIR/summary-final.md" ]`', 'SKILL Step 18 Read fallback removed')
require('python/closeout.py', '.step17-printed', 'step-16-17 owns .step17-printed')
require(skill, 'write `$IMPLEMENT_TMPDIR/.step17-emitted` only after that plain-chat emission.', 'SKILL Step 17 .step17-emitted orchestrator ownership')
require(skill, 'The orchestrator does not write `.step17-emitted` after finalize returns.', 'SKILL Step 18 .step17-emitted wrapper ownership')
require('python/closeout.py', 'step17_rc == 0 and _summary_nonempty(tmpdir)', 'step-16-17 marker gate uses Step 17 rc and non-empty summary')
require(skill, 'Marker emission is gated on captured Step 17 render success and a non-empty `summary-final.md`, not `summary-final.md` presence alone.', 'SKILL stale-summary marker gate')
forbid(skill, 'Do NOT use a Bash `cat` or Python tool call to print the summary body', 'retired Step 17 Bash-cat prohibition string')
forbid(skill, 'via Bash `cat` whose output is then re-emitted as orchestrator text', 'SKILL must not sanction Bash cat for summary emit')

if skill_text.count('timeout: 10800000') < 1:
    checks.append('SKILL.md must keep the 10800000 timeout tier for Step 3')
if not re.search(r'timeout: 32700000`\.\*\*\s+```bash\s+bash "\$IMPLEMENT_TMPDIR/larch-run\.sh" python/cli\.py implement checks-step5-resume --checks-site step5-review-fixes --final-round-num "\$FINAL_ROUND_NUM"', skill_text):
    checks.append('SKILL.md must background the Step 5 checks-step5-resume composite fence with timeout 32700000')
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
require(skill, 'step-0-bootstrap.sh" --mode initial', 'Step 0 initial bootstrap wrapper')
require(skill, 'step-0-bootstrap.sh" --mode resume', 'Step 0 resume bootstrap wrapper')
require('skills/implement/scripts/step-0-bootstrap.sh', 'set +e', 'step-0 bootstrap set +e guard')
require('python/bootstrap.py', 'preserve_coder=args.resume == "true"', 'bootstrap parse-routing resume preserves coder')
forbid(skill, launcher + 'skills/implement/scripts/step-0-degraded-gate.sh', 'SKILL active flow must not call step-0-degraded-gate.sh')
require('python/bootstrap.py', 'degraded-tools-gate', 'bootstrap absorbed degraded gate')
require('python/bootstrap.py', 'checkpoint-probe', 'bootstrap absorbed 1.r probe')
require('python/bootstrap.py', 'DEGRADED_PROMPT_REQUIRED', 'bootstrap degraded prompt routing')
require('python/bootstrap.py', 'REBASE_RC', 'bootstrap rebase rc synthesis')
require('python/bootstrap.py', '_ADVISORY_STDOUT_PREFIXES', 'bootstrap phantom advisory allowlist')
require('python/bootstrap.py', 'def _bootstrap_next', 'bootstrap next directive helper')
require('python/bootstrap.py', '"BOOTSTRAP_NEXT"', 'bootstrap next routing key')
require('python/bootstrap.py', 'continue_tail_attempted = _continue_predicate(data)', 'bootstrap captures continue_tail_attempted after coder restore')
require('python/bootstrap.py', 'tail = _run_absorbed_continue_tail', 'bootstrap captures continue_tail_attempted immediately before tail')
require('python/bootstrap.py', 'elif _step2_blockers(data) or bail_reason or data.get("STALL_TRACKING") == "true":', 'bootstrap blockers precede malformed route rebase')
require('python/bootstrap.py', 'if continue_tail_attempted and route not in {"continue", "conflict", "bail"}:', 'bootstrap malformed route gated on tail attempt')
require('python/bootstrap.py', 'data["BOOTSTRAP_NEXT"] = _bootstrap_next(data, continue_tail_attempted=continue_tail_attempted)', 'bootstrap next directive helper sets data')
require('python/bootstrap.py', '_merge_tail_routing_and_next(data, tail=tail, continue_tail_attempted=continue_tail_attempted)', 'bootstrap emits next directive before envelope')
require(skill, 'BOOTSTRAP_NEXT=degraded-prompt', 'SKILL degraded prompt directive')
require(skill, 'BOOTSTRAP_NEXT=rebase-routing', 'SKILL rebase directive')
require(skill, 'BOOTSTRAP_NEXT=step2', 'SKILL step2 directive')
require(skill, 'if `BOOTSTRAP_NEXT` is absent or any other value, treat the bootstrap envelope as malformed and abort with exit `2`', 'SKILL fail-closed malformed BOOTSTRAP_NEXT')
require(skill, 'branch only on `BOOTSTRAP_NEXT=rebase-routing` from the Step 0 bootstrap stdout envelope', 'SKILL absorbed 1.r directive branch')
require(skill, 'For checkpoint `1.r`, enter rebase handling only when `BOOTSTRAP_NEXT=rebase-routing` appears in the Step 0 bootstrap envelope.', 'SKILL Step 1.r directive branch')
require(skill, 'Step `4.r` keeps a direct foreground `python/cli.py push checkpoint-probe` fence below; `7.r` is folded into the Step 6 `checks-commit-route` composite and `7a.r` into `step-7a`, each relaying `CHECKPOINT_NEXT=continue|load-routing` for the same **Rebase Checkpoint Macro** routing', 'SKILL folded 7.r and 7a.r relays keep checkpoint macro routing')
require('skills/implement/references/checks-repair-loop.md', 'python/cli.py implement checks-commit-route --checks-site step6 --commit-site step7 --emit-step7-breadcrumb --rebase-checkpoint-7r --forked-target "${forked_target:-false}"', 'checks-repair-loop Step 6 composite launcher')
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
require(skill, 'After the composite fence returns, parse exactly one line-anchored composite `NEXT_ACTION=` record.', 'SKILL line-anchored composite NEXT_ACTION parse')
require(skill, 'Whitespace-token-scan only the first physical line for checks keys', 'SKILL composite checks parsing slice')
require(checks_ref, 're-run the section 2-pinned composite launcher with identical argv before any success-path routing', 'checks repair-loop folded-site re-capture authority')
require(skill, 'When stdout contains `STEP5_REVIEW_STATUS=`, route by the Step 5 status table only.', 'SKILL review-loop envelope branch')
require(skill, 'First, `NEXT_ACTION=stall` means durable stall state is already seeded by commit-route; skip to Step 18.', 'SKILL lacks-envelope NEXT_ACTION stall branch')
require(skill, '`NEXT_ACTION=continue` without `STEP5_REVIEW_STATUS=` is not Step 6 continuation.', 'SKILL NEXT_ACTION continue without envelope is not Step 6')
require(skill, 'missing, duplicated, malformed, or non-zero-without-`NEXT_ACTION` output is an invalid composite envelope', 'SKILL invalid composite envelope branch')
require(skill, 'commit-phase success (`NEXT_ACTION=continue`, `COMMIT_ROUTE_OUTCOME=continue`, or `COMMIT_OUTCOME=ok|noop`) alone does not satisfy NEVER #4', 'SKILL commit-route success alone is not review authorization')
require(skill, 'On composite `NEXT_ACTION=stall`, skip to Step 18 (stall recovery runs before the final report; durable bail is already seeded by commit-route).', 'SKILL Step 7 composite NEXT_ACTION stall branch')
require(skill, 'set prompt-side `STALL_TRACKING=true` and `STALL_STEP=5` when durable seed is absent, and skip to Step 18', 'SKILL self-review invalid envelope fail-closed')
require(skill, 'set prompt-side `STALL_TRACKING=true` and `STALL_STEP=7` when durable seed is absent, and skip to Step 18', 'SKILL Step 7 invalid envelope fail-closed')
require('python/implement_dispatch.py', 'COMMIT_ROUTE_OUTCOME', 'composite commit route child outcome')
require('python/implement_dispatch.py', '"--emit-next-action",\n            "false"', 'composite commit route child pin')
require('python/implement_dispatch.py', 'start_new_session=True', 'composite leg process group session')
require('python/implement_dispatch.py', 'os.killpg(pgid, signal.SIGKILL)', 'composite leg process group kill')
require('python/implement_dispatch.py', 'NEXT_ACTION", value="checks-failed"', 'composite checks-failed routing')
require('skills/implement/scripts/step-8-ship.sh', '--state-file "$IMPLEMENT_TMPDIR/ship-pr-state.sh"', 'step-8 state file forwarding')
exit_matrix = Path('skills/implement/references/ship-pr-exit-matrix.md')
if exit_matrix.is_file():
    exit_text = exit_matrix.read_text()
    for needle in [
        'Python-owned post-driver and OOS-checkpoint routing',
        'Preserve `RESUME_PHASE`, `CALLER_KIND`, and `CONFLICT_FILES`',
        'ship-pr-net-retries-python.count',
        'OOS-checkpoint `stall` is distinct from post-driver `stall`',
    ]:
        if needle not in exit_text:
            checks.append(f'ship-pr-exit-matrix.md missing {needle!r}')
    for needle in [
        '## Branch semantics',
        '**`complete`**',
        '**`reship`**',
        '**`oos-pipeline`**',
        '**`ci-fix`**',
        '**`operator-bail`**',
        'Post-driver `stall`',
        '**`tool-failure`**',
        'python/cli.py ship seed-initial-state` owns the canonical initial',
        'steps_ran.step9a1',
        'CI_PASSED=true` does not append execution-issues',
        'oos issue-cap',
        'finalize-state.sh',
    ]:
        if needle not in exit_text:
            checks.append(f'ship-pr-exit-matrix.md missing relocated authority {needle!r}')
    if '## Post-driver branch table' in exit_text:
        checks.append('ship-pr-exit-matrix.md must not add a parallel post-driver branch table')
matrix_read = '**MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/ship-pr-exit-matrix.md` completely.'
require(skill, matrix_read, 'ship-pr exit matrix Step 8+ entry read')
require_near(
    skill,
    matrix_read,
    'bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py ship route-exit',
    'Step 8+ matrix read before route-exit fence',
    1200,
)
require_near(
    skill,
    matrix_read,
    'bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py ship pre-driver',
    'Step 8+ matrix read before pre-driver fence',
    1200,
)
require('python/cli.py', '("ship", "route-exit"): ("implement_dispatch", "ship_route_exit_main")', 'ship route-exit registry')
require('python/cli.py', '("ship", "route-exit"),', 'ship route-exit machine stdout')
require('python/cli.py', '("implement", "commit-route"),', 'commit-route machine stdout')
require('python/cli.py', '("implement", "step-8-oos-checkpoint"),', 'step-8-oos-checkpoint machine stdout')
require(skill, '**`stall`** (post-driver only)', 'SKILL post-driver stall paragraph')
require(skill, '**`NEXT_ACTION=stall`** (OOS-checkpoint stall)', 'SKILL OOS-checkpoint stall paragraph')
require(skill, '$IMPLEMENT_TMPDIR/.step-8-ship-handoff.json` is absent', 'SKILL json absent setup-failure gate')
forbid(skill, '**Post-driver branch table**', 'SKILL post-driver branch table moved to matrix')
forbid(skill, '**Initial state seeder contract.**', 'SKILL full initial state seeder contract moved to matrix')
forbid(skill, '**Bail-time `steps_ran` invariant', 'SKILL bail-time steps_ran invariant moved to matrix')
forbid(skill, '**Execution-issues checkpoint**', 'SKILL execution-issues checkpoint moved to matrix')
forbid(skill, 'The OOS cap contract lives in', 'SKILL OOS cap contract moved to matrix')
forbid(skill, 'The active Step 8+ driver writes `finalize-state.sh`', 'SKILL active driver ownership block moved to matrix')
forbid(skill, '**Python driver routing:**', 'legacy Python driver routing removed')
forbid(skill, 'MANDATORY — READ ENTIRE FILE on any non-zero active Step 8+ driver exit', 'legacy non-zero driver mandatory block removed')
require(skill, 'Only checkpoint `NEXT_ACTION=reship` may write run statistics, stamp the manifest, and clear `OOS_PENDING=false`', 'NEVER #14 checkpoint success ownership')
require(skill, 'Do not run prompt-side direct `oos disposition-checkpoint`, compose run statistics, or patch `OOS_PENDING=false`', 'NEVER #14 forbids orchestrator-side checkpoint bookkeeping')
cleanup_ref = Path('skills/implement/references/step18-cleanup.md').read_text()
for needle in [
    'Resolve `STALL_TRACKING` from four layers',
    'compose-report --report-kind escalation-success',
    'Normal teardown is owned by `step-18.sh --phase finalize`',
    'Mode-specific reminders (`--draft`, `--merge`',
    'The `larch-tokens-&lt;slug&gt;.jsonl` token ledger',
]:
    if needle not in cleanup_ref:
        checks.append(f'step18-cleanup.md missing relocated authority {needle!r}')
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
if 'skills/implement/references/step18-cleanup.md' not in stall_ref:
    checks.append('stall-recovery.md must forward Step 18a.5 to step18-cleanup.md')
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
for retired_basename in ['commit-review-fixes.md', 'write-rejected-findings.md', 'check-review-changes.md']:
    forbid(skill, retired_basename, f'SKILL must not cite retired {retired_basename}')

if checks:
    print('\n'.join(checks), file=sys.stderr)
    sys.exit(1)
print('PASS: test-implement-structure.sh (wrapperized prompt structure)')
PY
