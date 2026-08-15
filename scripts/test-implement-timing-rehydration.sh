#!/usr/bin/env bash
# Structural timing/telemetry rehydration checks for /implement.

# shellcheck disable=SC2016 # single-quoted strings are intentional grep literals
unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
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
blocked=('session read-key','python3 python/cli.py token','python3 python/cli.py timing','scripts/larch.sh timing report','scripts/larch.sh timing telemetry-mark')
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

# Invariant B: the Python Step 5 adapter and the Step 18 wrapper own telemetry.
command grep -Fq '_rehydrate_larch_triplet(implement_tmpdir)' python/larch/implement/dispatch_commit_route.py || fail 'Step 5 Python adapter does not rehydrate telemetry keys'
command grep -Fq 'rust_runtime.timing_mark(' python/larch/implement/dispatch_commit_route.py || fail 'Step 5 Python adapter does not call the Rust timing owner'
command grep -Fq 'label="Step 5: review handoff"' python/larch/implement/dispatch_commit_route.py || fail 'Step 5 Python adapter does not mark implement timing'
command grep -Fq 'LARCH_TIMING_LEDGER' python/larch/implement/dispatch_helpers.py || fail 'dispatch_helpers does not resolve LARCH_TIMING_LEDGER'
command grep -Fq '_rehydrate_larch_triplet(implement_tmpdir)' python/larch/implement/dispatch_step18.py || fail 'step-18 Python does not rehydrate telemetry keys'
command grep -Fq '"LARCH_TIMING_SKILL": "implement"' python/larch/implement/dispatch_step18.py || fail 'step-18 Python does not mark implement timing'
command grep -Fq 'implement step-18 "$@"' skills/implement/scripts/step-18.sh || fail 'step-18.sh does not delegate to Python step-18'

# run_dispatch_main now lives in dispatch_step2.py; check there and fall back to implement_dispatch.py
( command grep -Fq '_rehydrate_larch_triplet(tmpdir)' python/larch/implement/dispatch_step2.py || command grep -Fq '_rehydrate_larch_triplet(tmpdir)' python/larch/implement/implement_dispatch.py ) || fail 'run_dispatch_main does not rehydrate telemetry keys'
( command grep -Fq '.step2-telemetry-marked' python/larch/implement/dispatch_step2.py || command grep -Fq '.step2-telemetry-marked' python/larch/implement/implement_dispatch.py ) || fail 'run_dispatch_main does not guard Step 2 telemetry once-only'
( command grep -Fq 'args.answers' python/larch/implement/dispatch_step2.py || command grep -Fq 'args.answers' python/larch/implement/implement_dispatch.py ) || fail 'run_dispatch_main does not skip telemetry on answers redispatch'

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
in_fence=False; start=0; body=[]; errors=[]; guard_count=0; root_fallback_count=0
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
        root_fallback_count += sum(1 for raw in body if '--print-plugin-root' in raw)
        in_fence=False
    elif in_fence:
        body.append(line)
if guard_count == 0:
    errors.append('no plugin-root source guards found')
if root_fallback_count < 1:
    errors.append(f'expected at least one pre-bootstrap plugin-root fallback to remain, found {root_fallback_count}')
if errors:
    print('\n'.join(errors), file=sys.stderr)
    sys.exit(1)
print(f'plugin-root guards={guard_count} root-fallbacks={root_fallback_count}')
PY

# Invariant E (#3425): closing marks stay inside Step 18 before terminal
# snapshot preparation, while teardown remains Step 19-owned.
finalizer="python/larch/implement/dispatch_step18.py"
cleanup="python/larch/implement/dispatch_step19.py"
done_mark_line=$(awk '/Step 18 — logs flush/ {print NR; exit}' "$finalizer")
snapshot_call_line=$(awk '/run_log_rc = _complete_terminal_run_log/ {print NR; exit}' "$finalizer")
[ -n "$done_mark_line" ] || fail 'dispatch_step18.py lacks Step 18 logs-flush mark'
[ -n "$snapshot_call_line" ] || fail 'dispatch_step18.py lacks terminal snapshot call'
[ "$done_mark_line" -lt "$snapshot_call_line" ] || fail 'Step 18 logs-flush mark must precede terminal snapshot preparation'
finalize_invocations=$(command grep -Fc '"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" skills/implement/scripts/step-18.sh' "$skill_file" || true)
[ "$finalize_invocations" -eq 1 ] || fail "expected one step-18.sh invocation in SKILL.md, found $finalize_invocations"
command grep -Fq '"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py implement step-18-gate-logs-flush' "$skill_file" || fail 'SKILL.md lacks composite Step 18 launcher'
command grep -Fq '"implement-finalize",' "$cleanup" || fail 'dispatch_step19.py lacks exact teardown argv'
command grep -Fq '"final-report", "step18b"' "$finalizer" || fail 'dispatch_step18.py lacks live step18b argv'
command grep -Fq 'def _print_summary_markers' "$finalizer" || fail 'dispatch_step18.py lacks marker helper'
command grep -Fq 'implement step-18 "$@"' skills/implement/scripts/step-18.sh || fail 'step-18.sh must remain a thin Python delegate'
command grep -Fq 'implement step-19 "$@"' skills/implement/scripts/step-19.sh || fail 'step-19.sh must remain a thin Python delegate'

# Invariant F (#4286): round timing duplicate probe returns success when the row exists.
step5_resume="python/larch/implement/dispatch_commit_route.py"
python3 - "$step5_resume" <<'PY'
from pathlib import Path
import sys
text = Path(sys.argv[1]).read_text()
required = 'if _step5_round_timing_row_exists(cols, round_decimal=round_decimal, start_s=start_s):'
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

echo "PASS: test-implement-timing-rehydration.sh (Python adapter rehydrates Step 5; closing marks line $done_mark_line < terminal snapshot line $snapshot_call_line; teardown is Step 19-owned)"
