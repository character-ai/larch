#!/usr/bin/env bash
# Validate /implement SKILL.md Bash fences are thin script-call wrappers.

set -euo pipefail


python3 <<'PY'
from pathlib import Path
import re, sys
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

CANONICAL_GUARD = '[ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/plugin-root.env" ] && . "$IMPLEMENT_TMPDIR/plugin-root.env"'

def logical_commands(body):
    commands = []
    cur = []
    for _, raw in body:
        stripped = raw.strip()
        if not stripped or stripped.startswith('#'):
            continue
        # Canonical plugin-root guards and pre-bootstrap awk fallback/export are prelude.
        if stripped == CANONICAL_GUARD:
            continue
        if stripped.startswith('[ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ] && CLAUDE_PLUGIN_ROOT=$(awk '):
            continue
        if stripped == 'export CLAUDE_PLUGIN_ROOT':
            continue
        if stripped == 'export IMPLEMENT_TMPDIR':
            continue
        cur.append(stripped)
        if not stripped.endswith('\\'):
            commands.append(' '.join(cur))
            cur = []
    if cur:
        commands.append(' '.join(cur))
    return commands

script_call = re.compile(r'^(?:[A-Za-z_][A-Za-z0-9_]*=\S+\s+)*(?:python3\s+)?"?\$\{?CLAUDE_PLUGIN_ROOT\}?/[^\s]+\.(?:sh|py)"?\b')
telemetry_only = re.compile(r'/(?:token-ledger|timing-ledger|token-report|timing-report)\.sh\b')
for start, end, body in fences:
    cmds = logical_commands(body)
    if len(cmds) != 1:
        errors.append(f'fence {start}-{end}: expected one script invocation command after prelude, found {len(cmds)}: {cmds!r}')
        continue
    cmd = cmds[0]
    if not script_call.search(cmd):
        errors.append(f'fence {start}-{end}: command is not a repo script invocation: {cmd}')
    if re.search(r'(^|[\s;])(\|\||&&|;|\bif\s|\bwhile\s|\buntil\s|\bcase\s)', cmd):
        errors.append(f'fence {start}-{end}: inline shell control logic is not allowed: {cmd}')
    if telemetry_only.search(cmd):
        errors.append(f'fence {start}-{end}: telemetry-only script invocation is not allowed: {cmd}')
    if script_call.search(cmd):
        if not any(raw.strip() == CANONICAL_GUARD for _, raw in body):
            errors.append(f'fence {start}-{end}: missing canonical plugin-root.env guard before CLAUDE_PLUGIN_ROOT script call')
    for _, raw in body:
        if 'session read-key' in raw:
            errors.append(f'fence {start}-{end}: inline session read-key is not allowed')
            break

for (_, end_a, _), (start_b, _, _) in zip(fences, fences[1:]):
    between = lines[end_a:start_b-1]
    if all(not line.strip() for line in between):
        errors.append(f'fences {end_a} and {start_b} are separated only by blank lines')

if errors:
    print('\n'.join(errors), file=sys.stderr)
    sys.exit(1)
print(f'PASS: test-implement-fence-shape.sh ({len(fences)} bash fences)')
PY
