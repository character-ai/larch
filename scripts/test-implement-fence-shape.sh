#!/usr/bin/env bash
# Validate /implement SKILL.md Bash fences are thin script-call wrappers.

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
AWK_FALLBACK_PREFIX = '[ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ] && CLAUDE_PLUGIN_ROOT=$(awk '
LAUNCHER_PREFIX = 'bash "$IMPLEMENT_TMPDIR/larch-run.sh" '
EXPECTED_OLD = 5
EXPECTED_NEW = 32

def normalized_logical_command(body):
    parts = []
    for _, raw in body:
        stripped = raw.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if stripped == CANONICAL_GUARD:
            continue
        if stripped.startswith(AWK_FALLBACK_PREFIX):
            continue
        if stripped in {'export IMPLEMENT_TMPDIR', 'export CLAUDE_PLUGIN_ROOT'}:
            continue
        if stripped.endswith('\\'):
            stripped = stripped[:-1].rstrip()
        parts.append(stripped)
    return ' '.join(parts)

def old_target_kind(cmd):
    if 'scripts/extract-closes-issue-from-pr.sh' in cmd:
        return 'structured-invocation'
    if 'python/cli.py' in cmd and 'plan-block read' in cmd and '--repo "$UPSTREAM_REPO"' in cmd:
        return 'preflight-plan-fork'
    if 'python/cli.py' in cmd and 'plan-block read' in cmd:
        return 'preflight-plan-default'
    if 'skills/implement/scripts/step-0-bootstrap.sh' in cmd and '--mode initial' in cmd:
        return 'step-0-initial'
    if 'skills/implement/scripts/step-0-bootstrap.sh' in cmd and '--mode resume' in cmd:
        return 'dirty-tree-resume'
    return ''

def has_guard(body):
    return any(raw.strip() == CANONICAL_GUARD for _, raw in body)

def has_awk(body):
    return any(raw.strip().startswith(AWK_FALLBACK_PREFIX) for _, raw in body)

def nonblank_lines(body):
    return [(ln, raw) for ln, raw in body if raw.strip()]

def validate_old(start, end, body, cmd, kind):
    if not has_guard(body):
        errors.append(f'fence {start}-{end}: old-shape {kind} missing canonical plugin-root.env guard')
    awk = has_awk(body)
    requires_awk = kind in {'structured-invocation', 'step-0-initial', 'dirty-tree-resume'}
    if requires_awk and not awk:
        errors.append(f'fence {start}-{end}: old-shape {kind} missing session-env awk fallback')
    if not requires_awk and awk:
        errors.append(f'fence {start}-{end}: preflight plan-block read must remain guard-only without awk fallback')
    if kind == 'step-0-initial' and '--mode initial' not in cmd:
        errors.append(f'fence {start}-{end}: Step 0 initial old-shape target missing --mode initial')
    if kind == 'dirty-tree-resume' and '--mode resume' not in cmd:
        errors.append(f'fence {start}-{end}: dirty-tree resume old-shape target missing --mode resume')
    if re.search(r'(^|[\s;])(\|\||&&|;|\bif\s|\bwhile\s|\buntil\s|\bcase\s)', cmd):
        errors.append(f'fence {start}-{end}: inline shell control logic is not allowed: {cmd}')


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
    if len(tokens) < 3:
        errors.append(f'fence {start}-{end}: new-shape launcher call missing script target: {stripped}')
        return
    if tokens[0] != 'bash' or tokens[1] != '$IMPLEMENT_TMPDIR/larch-run.sh':
        errors.append(f'fence {start}-{end}: launcher path must be exactly "$IMPLEMENT_TMPDIR/larch-run.sh": {stripped}')
    target = tokens[2]
    if target.startswith('/') or '..' in target:
        errors.append(f'fence {start}-{end}: launcher target must be repo-relative without ..: {target}')
    if not (target.endswith('.sh') or target.endswith('.py')):
        errors.append(f'fence {start}-{end}: launcher target must be a .sh or .py path: {target}')
    if target.endswith('.py'):
        saw_py_launcher = True
    if re.search(r'(^|[\s;])(\|\||&&|;|\bif\s|\bwhile\s|\buntil\s|\bcase\s)', stripped):
        errors.append(f'fence {start}-{end}: inline shell control logic is not allowed: {stripped}')
    if re.search(r'/(?:token-ledger|timing-ledger|token-report|timing-report)\.sh\b', stripped):
        errors.append(f'fence {start}-{end}: telemetry-only script invocation is not allowed: {stripped}')

for start, end, body in fences:
    for _, raw in body:
        if 'session read-key' in raw:
            errors.append(f'fence {start}-{end}: inline session read-key is not allowed')
            break
    cmd = normalized_logical_command(body)
    kind = old_target_kind(cmd)
    if kind:
        old_count += 1
        validate_old(start, end, body, cmd, kind)
    else:
        new_count += 1
        validate_new(start, end, body)

for (_, end_a, _), (start_b, _, _) in zip(fences, fences[1:]):
    between = lines[end_a:start_b-1]
    if all(not line.strip() for line in between):
        errors.append(f'fences {end_a} and {start_b} are separated only by blank lines')

if old_count != EXPECTED_OLD or new_count != EXPECTED_NEW:
    errors.append(f'expected old={EXPECTED_OLD} new={EXPECTED_NEW} bash fences, found old={old_count} new={new_count}')

if saw_py_launcher:
    bootstrap = Path('python/bootstrap.py').read_text()
    required = '*.py) exec python3 "$CLAUDE_PLUGIN_ROOT/$script" "$@" ;;'
    forbidden = '*.py) exec "$CLAUDE_PLUGIN_ROOT/$script" "$@" ;;'
    if required not in bootstrap:
        errors.append('larch-run.sh template must dispatch .py targets through python3')
    if forbidden in bootstrap:
        errors.append('larch-run.sh template must not bare-exec .py targets')

if errors:
    print('\n'.join(errors), file=sys.stderr)
    sys.exit(1)
print(f'PASS: test-implement-fence-shape.sh (old={old_count} new={new_count})')
PY
