#!/usr/bin/env bash
# Structural timing/telemetry rehydration checks for /implement.

# shellcheck disable=SC2016 # single-quoted strings are intentional grep literals
set -euo pipefail

skill_file="skills/implement/SKILL.md"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

# Invariant A: stale two-key exports must not return.
if python3 - "$skill_file" <<'PY2'
from pathlib import Path
import sys
sys.exit(0 if 'export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE' in Path(sys.argv[1]).read_text() else 1)
PY2
then
  fail 'SKILL.md still exports the stale two-key token context without LARCH_TIMING_LEDGER'
fi

# Invariant B/D: SKILL.md fences do not inline telemetry/read-key work.
python3 <<'PY'
from pathlib import Path
import sys
lines=Path('skills/implement/SKILL.md').read_text().splitlines()
blocked=('session read-key','python3 python/cli.py token','python3 python/cli.py timing','python3 python/cli.py token report','python3 python/cli.py timing report','python3 python/cli.py timing telemetry-mark')
in_fence=False; start=0; errors=[]
for i,line in enumerate(lines,1):
    if line.lstrip().startswith('```bash'):
        in_fence=True; start=i
    elif in_fence and line.lstrip().startswith('```'):
        in_fence=False
    elif in_fence:
        for token in blocked:
            if token in line:
                errors.append(f'fence starting {start}: inline telemetry/read-key token {token!r}')
if errors:
    print('\n'.join(errors), file=sys.stderr)
    sys.exit(1)
PY

# Invariant B moved into wrappers: telemetry consumers self-rehydrate session keys.
for wrapper in \
  skills/implement/scripts/step-5-resume.sh \
  skills/implement/scripts/step-18.sh; do
  command grep -Fq 'LARCH_TIMING_LEDGER' "$wrapper" || fail "$wrapper does not resolve LARCH_TIMING_LEDGER"
  command grep -Fq 'LARCH_TIMING_SKILL=implement' "$wrapper" || fail "$wrapper does not mark timing with LARCH_TIMING_SKILL=implement"
done

command grep -Fq '_rehydrate_larch_triplet(tmpdir)' python/implement_dispatch.py || fail 'run_dispatch_main does not rehydrate telemetry keys'
command grep -Fq '.step2-telemetry-marked' python/implement_dispatch.py || fail 'run_dispatch_main does not guard Step 2 telemetry once-only'
command grep -Fq 'args.answers' python/implement_dispatch.py || fail 'run_dispatch_main does not skip telemetry on answers redispatch'

# Invariant C: every plugin-rooted Bash fence carries the same-fence source guard.
python3 <<'PY'
from pathlib import Path
import sys
lines=Path('skills/implement/SKILL.md').read_text().splitlines()
source_guard='[ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/plugin-root.env" ] && . "$IMPLEMENT_TMPDIR/plugin-root.env"'
tmpdir_export='export IMPLEMENT_TMPDIR'
# The direct Step 16-17 Python CLI fence is a single self-contained call that
# scripts/test-implement-fence-shape.sh accepts as a one-line new-shape fence,
# so it cannot carry the multi-line guard/export. It runs after Step 0 exports
# CLAUDE_PLUGIN_ROOT, so it is exempt from the early-fence source guard/export.
step_16_17_call='python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" implement step-16-17 --implement-tmpdir "$IMPLEMENT_TMPDIR"'
in_fence=False; start=0; body=[]; errors=[]; guard_count=0; awk_count=0
for i,line in enumerate(lines,1):
    if line.lstrip().startswith('```bash'):
        in_fence=True; start=i; body=[]
    elif in_fence and line.lstrip().startswith('```'):
        text='\n'.join(body)
        exempt=any(raw.strip()==step_16_17_call for raw in body)
        if '${CLAUDE_PLUGIN_ROOT}' in text and source_guard not in text and not exempt:
            errors.append(f'fence starting {start}: missing canonical plugin-root source guard')
        if '${CLAUDE_PLUGIN_ROOT}' in text and '$IMPLEMENT_TMPDIR' in text and tmpdir_export not in text and not exempt:
            errors.append(f'fence starting {start}: missing IMPLEMENT_TMPDIR export')
        guard_count += sum(1 for raw in body if raw.strip()==source_guard)
        awk_count += sum(1 for raw in body if 'LARCH_CLAUDE_PLUGIN_ROOT=' in raw)
        in_fence=False
    elif in_fence:
        body.append(line)
if guard_count == 0:
    errors.append('no plugin-root source guards found')
if awk_count < 2:
    errors.append(f'expected at least two pre-bootstrap awk fallbacks to remain, found {awk_count}')
if errors:
    print('\n'.join(errors), file=sys.stderr)
    sys.exit(1)
print(f'plugin-root guards={guard_count} awk-fallbacks={awk_count}')
PY

# Invariant E (#3425): closing marks stay inside step-18.sh before teardown.
finalizer="skills/implement/scripts/step-18.sh"
done_mark_line=$(awk '/Step 18 — done/ {print NR; exit}' "$finalizer")
teardown_line=$(awk '/implement-finalize teardown/ {print NR; exit}' "$finalizer")
[ -n "$done_mark_line" ] || fail 'step-18.sh lacks Step 18 done mark'
[ -n "$teardown_line" ] || fail 'step-18.sh lacks implement-finalize teardown'
[ "$done_mark_line" -lt "$teardown_line" ] || fail 'Step 18 done mark must precede teardown in step-18.sh'
finalize_invocations=$(command grep -Fc 'bash "$IMPLEMENT_TMPDIR/larch-run.sh" skills/implement/scripts/step-18.sh' "$skill_file" || true)
[ "$finalize_invocations" -eq 1 ] || fail "expected one step-18.sh invocation in SKILL.md, found $finalize_invocations"
command grep -Fq 'bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py implement step-18-gate-finalize' "$skill_file" || fail 'SKILL.md lacks composite Step 18 launcher'
command grep -Fq 'implement-finalize teardown --state-file "$IMPLEMENT_TMPDIR/finalize-state.sh" --implement-tmpdir "$IMPLEMENT_TMPDIR"' "$finalizer" || fail 'step-18.sh lacks exact teardown argv'
command grep -Fq 'final-report step18b --implement-tmpdir "$IMPLEMENT_TMPDIR"' "$finalizer" || fail 'step-18.sh lacks live step18b argv'
command grep -Fq 'print_summary_markers' "$finalizer" || fail 'step-18.sh lacks marker helper'
command grep -Fq 'set +e' "$finalizer" || fail 'step-18.sh lacks set +e tolerance blocks'

# Invariant F (#4286): round timing duplicate probe returns success when the row exists.
step5_resume="skills/implement/scripts/step-5-resume.sh"
python3 - "$step5_resume" <<'PY'
from pathlib import Path
import sys
text = Path(sys.argv[1]).read_text()
required = 'END { exit found ? 0 : 1 }'
forbidden = 'END { exit found }'
errors = []
if required not in text:
    errors.append(f'{sys.argv[1]} lacks {required!r}')
if forbidden in text:
    errors.append(f'{sys.argv[1]} still uses bare {forbidden!r}')
if errors:
    print('\n'.join(errors), file=sys.stderr)
    sys.exit(1)
PY

echo "PASS: test-implement-timing-rehydration.sh (wrappers self-rehydrate; closing marks line $done_mark_line < teardown line $teardown_line)"
