# step-8-ship.sh

Step 8+ Python ship-driver wrapper. It rehydrates durable ship argv from `$IMPLEMENT_TMPDIR/ship-pr-state.sh`, derives `EXPECTED_TMPDIR_BASENAME_PREFIX` through a fail-closed `python/cli.py implement clone-tag` capture before `eval` and a `: "${EXPECTED_TMPDIR_BASENAME_PREFIX:?}"` guard, delegates the Python 3.11 guard to `step-8-python-guard.sh`, runs the advisory `8-pre-ship` phantom probe, and invokes `python/cli.py ship pr` with the canonical argv.

## Caller

`skills/implement/SKILL.md` invokes this wrapper from Step 8+ in immediate-background mode. Pre-driver orchestration may run guard, initial seeding, and `oos file` first; post-driver continuations invoke only this wrapper.

## Stdout contract

Wrapper stdout must remain exactly the single JSON object emitted by `python/cli.py ship pr`, except when `step-8-python-guard.sh` fails with Python <3.11 and emits the shared STALLED JSON object. The `8-pre-ship` phantom probe is diagnostic only and redirects stdout to stderr so `PHANTOM_*` records cannot pollute the JSON stream.

## Invariants

- Bash 3.2 portable; no associative arrays or namerefs.
- Self-rehydrates `CLAUDE_PLUGIN_ROOT` from `$IMPLEMENT_TMPDIR/plugin-root.env` where needed.
- Self-rehydrates `BRANCH_NAME`, `ISSUE_NUMBER`, `RUN_ID`, `REPO`, `MERGE`, `DRAFT`, `FORKED_TARGET`, `REPO_UNAVAILABLE`, `MANIFEST_PATH`, `TOOL_LABEL`, `NO_ADMIN_FALLBACK`, and `NO_LOGS_COMMIT` from `ship-pr-state.sh` before invoking the active driver.
- `EXPECTED_TMPDIR_BASENAME_PREFIX` comes from `python/cli.py implement clone-tag`; the ship wrapper and initial state seeder must share the same prefix.
- The Python version guard lives in `step-8-python-guard.sh`.

## Edit-in-sync

Update `skills/implement/SKILL.md`, `step-8-seed-initial.md`, and `skills/implement/scripts/test-step-8-ship.sh` when this contract or argv changes.
