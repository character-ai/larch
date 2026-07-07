# run-step-checks.sh

Captured relevant-checks wrapper and Step 3 checks/commit composite bgjob launcher.
The wrapper rehydrates telemetry keys, truncates a per-step merge-result env, and launches a bgjob whose foreground stdout is exactly `BGJOB_STATUS=STARTED STEP=<name> PGID=<n>`.

## Caller

`skills/implement/SKILL.md` invokes this wrapper for active Step 3 with `--site step3 --commit-site step4 --rebase-checkpoint-4r`. Legacy helper-only call sites may still pass only `--site SITE` to launch `python/cli.py checks run-relevant` through the same bgjob transport.

## KV grammar

The bgjob child tees the underlying helper stdout into the merge-result env. After `python/cli.py bgjob wait` returns `DONE`, the orchestrator reads `$IMPLEMENT_TMPDIR/bgjob/<step>.result.env` and gates continuation on `BGJOB_RC=0` plus the required site KVs.

## Invariants

- Bash 3.2 portable; no associative arrays or namerefs.
- Self-rehydrates `CLAUDE_PLUGIN_ROOT` from `$IMPLEMENT_TMPDIR/plugin-root.env` where needed.
- Session telemetry key names live in `skills/shared/session-setup-output.md`; check wrappers consume the `$IMPLEMENT_TMPDIR/session-env.sh` copy.
- When `--site step3`, uses bgjob step slug `implement-step3-checks`, clears stale `.completed/step-3-terminal`, and passes that sentinel to `bgjob start`.
- The wrapper does not write `.bg-wait-active`; legacy marker helpers remain elsewhere until the cleanup chunk removes them.

## Edit-in-sync

Update `skills/implement/SKILL.md` and the implement structure/timing harnesses when this contract or argv changes.
