#!/usr/bin/env bash
# Validate /implement SKILL.md Bash fences are thin script-call wrappers.

unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail


python3 <<'PY'
from pathlib import Path
import re, shlex, sys

path = Path('skills/implement/SKILL.md')
lines = path.read_text().splitlines()
fences = []
in_fence = False
start = 0
body = []
for idx, line in enumerate(lines, 1):
    if line.lstrip().startswith('```bash'):
        in_fence = True
        start = idx
        body = []
    elif in_fence and line.lstrip().startswith('```'):
        fences.append((start, idx, body[:]))
        in_fence = False
    elif in_fence:
        body.append((idx, line))

errors = []
old_count = 0
new_count = 0
saw_py_launcher = False

CANONICAL_GUARD = '[ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/plugin-root.env" ] && . "$IMPLEMENT_TMPDIR/plugin-root.env"'
ROOT_FALLBACK_PREFIX = '[ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -x "$IMPLEMENT_TMPDIR/larch-run.sh" ] && CLAUDE_PLUGIN_ROOT=$("$IMPLEMENT_TMPDIR/larch-run.sh" --print-plugin-root'
LAUNCHER_PREFIX = '"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" '
EXPECTED_OLD = 2
EXPECTED_NEW = 31

def old_logical_commands(body):
    commands = []
    parts = []
    for _, raw in body:
        stripped = raw.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if stripped == CANONICAL_GUARD:
            continue
        if stripped.startswith(ROOT_FALLBACK_PREFIX):
            continue
        if stripped in {'export IMPLEMENT_TMPDIR', 'export CLAUDE_PLUGIN_ROOT'}:
            continue
        if stripped.endswith('\\'):
            stripped = stripped[:-1].rstrip()
            parts.append(stripped)
            continue
        parts.append(stripped)
        commands.append(' '.join(parts))
        parts = []
    if parts:
        commands.append(' '.join(parts))
    return commands

def old_target_kind(cmd):
    if 'scripts/larch.sh' in cmd and 'pr closes-issue' in cmd:
        return 'structured-invocation'
    if 'larch.sh' in cmd and 'implement preflight' in cmd:
        return 'preflight-helper'
    if ('python/cli.py' in cmd or 'larch.sh' in cmd) and 'plan-block read' in cmd:
        return 'preflight-plan-direct'
    if 'skills/implement/scripts/step-0-bootstrap.sh' in cmd and '--mode initial' in cmd:
        return 'step-0-initial'
    if 'skills/implement/scripts/step-0-bootstrap.sh' in cmd and '--mode resume' in cmd:
        return 'dirty-tree-resume'
    return ''

def has_guard(body):
    return any(raw.strip() == CANONICAL_GUARD for _, raw in body)

def has_root_fallback(body):
    return any(raw.strip().startswith(ROOT_FALLBACK_PREFIX) for _, raw in body)

def nonblank_lines(body):
    return [(ln, raw) for ln, raw in body if raw.strip()]

def validate_old(start, end, body, commands, cmd, kind):
    if kind == 'preflight-plan-direct':
        errors.append(f'fence {start}-{end}: direct Preflight plan-block read fence is forbidden')
        return
    if kind == 'preflight-helper':
        validate_preflight_helper(start, end, body, commands, cmd)
        return
    if len(commands) != 1:
        errors.append(f'fence {start}-{end}: old-shape {kind} must have exactly one logical command, found {len(commands)}')
    if not has_guard(body):
        errors.append(f'fence {start}-{end}: old-shape {kind} missing canonical plugin-root.env guard')
    root_fallback = has_root_fallback(body)
    requires_root_fallback = kind in {'structured-invocation', 'step-0-initial', 'dirty-tree-resume'}
    if requires_root_fallback and not root_fallback:
        errors.append(f'fence {start}-{end}: old-shape {kind} missing larch-run.sh --print-plugin-root fallback')
    if not requires_root_fallback and root_fallback:
        errors.append(f'fence {start}-{end}: old-shape {kind} must remain guard-only without a plugin-root fallback')
    if kind == 'step-0-initial' and '--mode initial' not in cmd:
        errors.append(f'fence {start}-{end}: Step 0 initial old-shape target missing --mode initial')
    if kind == 'step-0-initial' and 'LARCH_CLAUDE_PID="$PPID" ' not in cmd:
        errors.append(f'fence {start}-{end}: Step 0 initial old-shape target missing LARCH_CLAUDE_PID prefix')
    if kind == 'dirty-tree-resume' and '--mode resume' not in cmd:
        errors.append(f'fence {start}-{end}: dirty-tree resume old-shape target missing --mode resume')
    if kind == 'dirty-tree-resume' and 'LARCH_CLAUDE_PID="$PPID" ' not in cmd:
        errors.append(f'fence {start}-{end}: dirty-tree resume old-shape target missing LARCH_CLAUDE_PID prefix')
    if re.search(r'(^|[\s;])(\|\||&&|;|\bif\s|\bwhile\s|\buntil\s|\bcase\s)', cmd):
        errors.append(f'fence {start}-{end}: inline shell control logic is not allowed: {cmd}')


def validate_preflight_helper(start, end, body, commands, cmd):
    if not has_guard(body):
        errors.append(f'fence {start}-{end}: preflight-helper missing canonical plugin-root.env guard')
    if has_root_fallback(body):
        errors.append(f'fence {start}-{end}: preflight-helper must not use a plugin-root fallback')
    if cmd.count('larch.sh') != 1 or 'implement preflight' not in cmd:
        errors.append(f'fence {start}-{end}: preflight-helper must invoke scripts/larch.sh implement preflight exactly once')
    required = [
        '"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh" implement preflight',
        '--issue "$TARGET_ISSUE_NUMBER"',
        '--preflight-tmpdir "$PREFLIGHT_TMPDIR"',
        'preflight_args=(',
        '"${preflight_args[@]}"',
    ]
    for needle in required:
        if needle not in cmd:
            errors.append(f'fence {start}-{end}: preflight-helper missing {needle}')
    if '--repo "$UPSTREAM_REPO"' not in cmd or '[ -n "${UPSTREAM_REPO:-}" ]' not in cmd:
        errors.append(f'fence {start}-{end}: preflight-helper must add --repo only inside the UPSTREAM_REPO non-empty branch')
    if '--force' not in cmd or '[ "${force_requested:-false}" = true ]' not in cmd:
        errors.append(f'fence {start}-{end}: preflight-helper must add --force only inside the force_requested=true branch')
    if '${force_requested:+--force}' in cmd:
        errors.append(f'fence {start}-{end}: preflight-helper must not use parameter-expansion force argv')

def validate_new(start, end, body):
    global saw_py_launcher
    physical = nonblank_lines(body)
    if len(physical) != 1:
        errors.append(f'fence {start}-{end}: new-shape fence must have exactly one nonblank physical line, found {len(physical)}')
        return
    line_no, raw = physical[0]
    stripped = raw.strip()
    if raw.lstrip().startswith('#'):
        errors.append(f'fence {start}-{end}: new-shape fence must not contain comments')
        return
    if stripped.endswith('\\'):
        errors.append(f'fence {start}-{end}: new-shape fence must not use a line continuation')
    if not stripped.startswith(LAUNCHER_PREFIX):
        errors.append(f'fence {start}-{end}: new-shape command must start with {LAUNCHER_PREFIX!r}: {stripped}')
        return
    try:
        tokens = shlex.split(stripped)
    except ValueError as exc:
        errors.append(f'fence {start}-{end}: new-shape command is not shell-parseable: {exc}: {stripped}')
        return
    if len(tokens) < 2:
        errors.append(f'fence {start}-{end}: new-shape launcher call missing script target: {stripped}')
        return
    if tokens[0] != '$HOME/.cache/larch/sessions/implement-run-$PPID.sh':
        errors.append(f'fence {start}-{end}: launcher path must be exactly "$HOME/.cache/larch/sessions/implement-run-$PPID.sh": {stripped}')
    target = tokens[1]
    if target.startswith('/') or '..' in target:
        errors.append(f'fence {start}-{end}: launcher target must be repo-relative without ..: {target}')
    if not (target.endswith('.sh') or target.endswith('.py')):
        errors.append(f'fence {start}-{end}: launcher target must be a .sh or .py path: {target}')
    if target.endswith('.py'):
        saw_py_launcher = True
    best_effort_timing = stripped == '"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" scripts/larch.sh timing telemetry-mark --implement-tmpdir "$IMPLEMENT_TMPDIR" --label "Step 5 — code review" || true'
    if re.search(r'(^|[\s;])(\|\||&&|;|\bif\s|\bwhile\s|\buntil\s|\bcase\s)', stripped) and not best_effort_timing:
        errors.append(f'fence {start}-{end}: inline shell control logic is not allowed: {stripped}')
    if re.search(r'/(?:token-ledger|timing-ledger|token-report|timing-report)\.sh\b', stripped):
        errors.append(f'fence {start}-{end}: telemetry-only script invocation is not allowed: {stripped}')

for start, end, body in fences:
    body_text = '\n'.join(raw for _, raw in body)
    if '8-pre-ship' in body_text and 'step-8-ship.sh' not in body_text:
        errors.append(f'fence {start}-{end}: standalone orchestrator 8-pre-ship fence is forbidden')
    if 'python/cli.py ship seed-initial-state' in body_text:
        errors.append(f'fence {start}-{end}: Step 8 seed fences must delegate to step-8-seed-initial.sh')
    for _, raw in body:
        if 'session read-key' in raw:
            errors.append(f'fence {start}-{end}: inline session read-key is not allowed')
            break
    if ('python/cli.py' in body_text or 'larch.sh' in body_text) and 'plan-block read' in body_text:
        errors.append(f'fence {start}-{end}: direct Preflight plan-block read call is forbidden')
    if 'gh issue view' in body_text:
        errors.append(f'fence {start}-{end}: direct Preflight gh issue view call is forbidden')
    commands = old_logical_commands(body)
    cmd = ' '.join(commands)
    kind = old_target_kind(cmd)
    if kind:
        old_count += 1
        validate_old(start, end, body, commands, cmd, kind)
    else:
        new_count += 1
        validate_new(start, end, body)

for (_, end_a, _), (start_b, _, _) in zip(fences, fences[1:]):
    between = lines[end_a:start_b-1]
    if all(not line.strip() for line in between):
        errors.append(f'fences {end_a} and {start_b} are separated only by blank lines')

if old_count != EXPECTED_OLD or new_count != EXPECTED_NEW:
    errors.append(f'expected old={EXPECTED_OLD} new={EXPECTED_NEW} bash fences, found old={old_count} new={new_count}')


skill_text = path.read_text()
try:
    reship_start = skill_text.index('- **`reship`**:')
    oos_start = skill_text.index('- **`oos-pipeline`**:', reship_start)
    reship_slice = skill_text[reship_start:oos_start]
    reship_pre_fix = reship_slice.index('ship pre-fix-rebase --implement-tmpdir "$IMPLEMENT_TMPDIR"')
    reship_continue = reship_slice.index('`NEXT_ACTION=continue` proceeds to the Step 8 bgjob `step-8-ship.sh` relaunch')
    if reship_pre_fix > reship_continue:
        errors.append('reship branch must require ship pre-fix-rebase before stale-handoff clear')
except ValueError as exc:
    errors.append(f'reship branch must document ship pre-fix-rebase ordering: {exc}')
try:
    ci_fix_start = skill_text.index('- **`ci-fix`**:')
    conflict_start = skill_text.index('- **`conflict-fix`**', ci_fix_start)
    ci_fix_slice = skill_text[ci_fix_start:conflict_start]
    ci_fix_pre_fix = ci_fix_slice.index('ship pre-fix-rebase --implement-tmpdir "$IMPLEMENT_TMPDIR"')
    ci_fix_loop = ci_fix_slice.index('`larch:ci-fixer`')
    if ci_fix_pre_fix > ci_fix_loop:
        errors.append('ci-fix branch must run ship pre-fix-rebase before the ci-fixer subagent loop')
except ValueError as exc:
    errors.append(f'ci-fix branch must document ship pre-fix-rebase before the subagent loop: {exc}')
try:
    assessments_start = skill_text.index('- **`assessments`**, **`invariants-assessment`**, or **`guidelines-assessment`**:')
    reship_start = skill_text.index('- **`reship`**:', assessments_start)
    assessments_slice = skill_text[assessments_start:reship_start]
    normalization = assessments_slice.index('scripts/larch.sh ship normalize-assessment-handoff --implement-tmpdir "$IMPLEMENT_TMPDIR"')
    materialize = assessments_slice.index('scripts/larch.sh architectural-assessment materialize')
    assessor = assessments_slice.index('`larch:arch-assessor`')
    submit = assessments_slice.index('scripts/larch.sh architectural-assessment submit')
    relaunch = assessments_slice.index('return to the Step 8 ship launcher above exactly once')
    if not (normalization < materialize < assessor < submit < relaunch):
        errors.append('assessment branch must normalize, materialize, spawn one arch-assessor subagent, submit, then allow one Step 8 ship relaunch')
    if assessments_slice.count('scripts/larch.sh ship normalize-assessment-handoff --implement-tmpdir "$IMPLEMENT_TMPDIR"') != 1:
        errors.append('assessment branch must contain exactly one normalize-assessment-handoff launcher')
    if 'For clean state, use the canonical one-sentence note with no G-* or I-* identifier.' not in assessments_slice:
        errors.append('assessment branch must remind arch-assessor that clean notes are identifier-free')
    if 'scripts/larch.sh bgjob wait --step implement-step8-assessment' in assessments_slice:
        errors.append('assessment branch must not expose a prompt-side assessment wait fence')
    for forbidden in ('step-architectural-invariants-write-compose.sh', 'step-architectural-guidelines-write-compose.sh', 'architectural-invariant-assessment-draft.md', 'architectural-guideline-assessment-draft.md'):
        if forbidden in assessments_slice:
            errors.append(f'assessment branch must not retain legacy prompt-side work: {forbidden}')
except ValueError as exc:
    errors.append(f'assessment branch must document subagent-first ordering: {exc}')


resume_text = Path('skills/implement/references/bootstrap-recovery.md').read_text()
if 'LARCH_CLAUDE_PID="$PPID" "${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-0-bootstrap.sh" --mode resume' not in resume_text:
    errors.append('bootstrap-recovery resume fence must prefix step-0-bootstrap.sh with LARCH_CLAUDE_PID="$PPID"')

if saw_py_launcher:
    bootstrap = Path('crates/larch-cli/src/bootstrap_commands.rs').read_text()
    required = 'trap _larch_cleanup_active_leg EXIT INT TERM'
    forbidden_exec = '*.py) exec python3 "$CLAUDE_PLUGIN_ROOT/$script" "$@" ;;'
    forbidden = '*.py) exec "$CLAUDE_PLUGIN_ROOT/$script" "$@" ;;'
    if required not in bootstrap:
        errors.append('larch-run.sh template must trap active-leg cleanup for .py targets')
    if 'export LARCH_ACTIVE_LEG_OWNER_TOKEN="$_larch_active_leg_owner_token"' not in bootstrap:
        errors.append('larch-run.sh template must export active-leg owner token before .py target')
    if 'implement kill-active-leg --owner-token "$_larch_active_leg_owner_token" --implement-tmpdir' not in bootstrap:
        errors.append('larch-run.sh template must forward owner token to implement kill-active-leg')
    if 'kill-active-leg --implement-tmpdir "$IMPLEMENT_TMPDIR" 2>/dev/null' in bootstrap:
        errors.append('larch-run.sh template must not silence kill-active-leg stderr')
    if forbidden_exec in bootstrap:
        errors.append('larch-run.sh template must not exec .py targets (outer fence needs trap cleanup)')
    if forbidden in bootstrap:
        errors.append('larch-run.sh template must not bare-exec .py targets')

if errors:
    print('\n'.join(errors), file=sys.stderr)
    sys.exit(1)
print(f'PASS: test-implement-fence-shape.sh (old={old_count} new={new_count})')
PY
