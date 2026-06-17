# step-8-python-guard.sh

Shared Python 3.11 guard for /implement Step 8.

## Caller

The pre-driver Step 8 orchestrator path and `skills/implement/scripts/step-8-ship.sh` both call this wrapper through `$IMPLEMENT_TMPDIR/larch-run.sh`.

## Contract

On Python 3.11 or newer, the wrapper exits `0` with no stdout. On older Python, it writes `ERROR: Python ship driver requires Python 3.11 or newer` to stderr, emits the single-line STALLED JSON object on stdout, and exits `4`.

## Edit-in-sync

Keep the stdout JSON shape aligned with `python/ship.py`'s top-level version fallback and the Step 8 JSON routing contract in `skills/implement/SKILL.md`.
