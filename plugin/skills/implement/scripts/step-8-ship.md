# step-8-ship.sh

Step 8+ Python ship-driver bgjob launcher. Foreground mode starts or rejoins bgjob step `implement-step8-ship`; child mode rehydrates durable ship argv from `$IMPLEMENT_TMPDIR/ship-pr-state.sh`, derives `EXPECTED_TMPDIR_BASENAME_PREFIX` through fail-closed `python/cli.py implement clone-tag` capture, delegates the Python 3.11 guard to `step-8-python-guard.sh`, runs the advisory `8-pre-ship` phantom probe, and invokes `python/cli.py ship pr` with the canonical argv.

## Caller

`skills/implement/SKILL.md` invokes this wrapper from Step 8+ as a foreground bgjob launcher. Pre-driver orchestration may run guard, initial seeding, and `${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh oos file` first; post-driver continuations invoke only this wrapper.

## Stdout and result-env contract

Foreground mode delegates start-or-reattach, result replacement, and merge-result publication to `scripts/larch.sh bgjob adapt`. The child rehydrates the durable ship argv, runs the Python-version guard and advisory phantom probe, then invokes `ship pr` with its adapter-provided `--merge-result-env` as `--result-env-path`.

`ship pr` writes its outcome KVs before it emits its human-readable JSON contract. The bgjob daemon merges those KVs with `BGJOB_RC` and `STEP` into `$IMPLEMENT_TMPDIR/bgjob/implement-step8-ship.result.env`; `ship route-exit` reads that one authoritative result env after bgjob `DONE`.

Result-env publication is fail-closed: a result write failure gives the bgjob no ship outcome to route, so `route-exit` stops rather than using stdout. Step 8 is persist-and-resume by design; `bgjob adapt` owns live-job reattachment and completed-result replacement.

## Invariants

- Bash 3.2 portable; no associative arrays or namerefs.
- Self-rehydrates `CLAUDE_PLUGIN_ROOT` from `$IMPLEMENT_TMPDIR/plugin-root.env` where needed.
- Self-rehydrates `BRANCH_NAME`, `ISSUE_NUMBER`, `RUN_ID`, `REPO`, `MERGE`, `DRAFT`, `FORKED_TARGET`, `REPO_UNAVAILABLE`, `MANIFEST_PATH`, `TOOL_LABEL`, `NO_ADMIN_FALLBACK`, and `NO_LOGS_COMMIT` from `ship-pr-state.sh` before invoking the active driver.
- `EXPECTED_TMPDIR_BASENAME_PREFIX` comes from `python/cli.py implement clone-tag`; the ship wrapper and initial state seeder must share the same prefix.
- `ship pr` owns the ship-outcome wire format; Bash neither captures nor parses it.
- `bgjob adapt` refuses a second start when an identity-valid `implement-step8-ship` job is live and replaces only a completed result on a deliberate reship.
- Guard or setup failures without a ship outcome do not reach `route-exit`; they use the existing bgjob failure branch.
- The Python version guard lives in `step-8-python-guard.sh`.

## Edit-in-sync

Update `skills/implement/SKILL.md`, `step-8-seed-initial.md`, `skills/implement/references/ship-pr-exit-matrix.md`, and `python/tests/implement/test_implement_shell_scripts.py` when this contract or argv changes.
