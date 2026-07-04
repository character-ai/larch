# step-5-review.sh

Step 5 review loop launcher. Marks Step 5 telemetry, writes the bg-wait marker, prints the scripted-review banner, reads the persisted difficulty override when present, and launches the file-backed `review-and-fix step5 --mode loop` worker.

## Caller

`skills/implement/SKILL.md` invokes this wrapper from the scripted review loop so the prompt-side Bash fence remains one launcher call with immediate-background handling.

## KV grammar

None of its own on success. The wrapper captures the worker stdout to a temp file, normalizes it through `review-and-fix normalize-status`, then relays the Step 5 status grammar unchanged.

On reattach or stdout-capture failure it emits a parseable Step 5 stall envelope so prompt-side routing never treats an absent envelope as success.

## Invariants

- Bash 3.2 portable; no associative arrays or namerefs.
- Self-rehydrates `CLAUDE_PLUGIN_ROOT` from `$IMPLEMENT_TMPDIR/plugin-root.env` where needed.
- Telemetry marking is best-effort and must not block the review loop.
- `dynamic_archetypes_cap` resolves from `$IMPLEMENT_TMPDIR/session-env.sh`, then from process `LARCH_DYNAMIC_ARCHETYPES_MAX`, then the implement-mode default `1`.
- Writes a `.bg-wait-active` marker (`STEP=implement-step5-review`) before launch, copying `CLONE_PATH` from `$IMPLEMENT_TMPDIR/.larch-keepalive` when available.
- Launches the Python worker in a new process group with `--new-process-group --orphan-timeout-s 7200`, captures stdout in a regular temp file, and quarantines worker stderr in `$IMPLEMENT_TMPDIR/review-and-fix-step5-loop.stderr`.
- Publishes `$IMPLEMENT_TMPDIR/.step5-loop-identity.json` after launch. The identity is used for signal detach, safe teardown, and reattach.
- On `TERM`, `HUP`, or `INT` after identity publication, writes `$IMPLEMENT_TMPDIR/.step5-wrapper-detached`, disowns the worker, removes `.bg-wait-active`, and does **not** write `.completed/step-5-terminal`.
- On signal before identity publication, validates the raw child pid/process-group shape before killing the fresh process group; it does not write a detached marker or terminal sentinel.
- On a later entry with a regular, non-symlink `.step5-wrapper-detached` marker, writes `.step5-reattach-active`, awaits the recorded identity with `--reattach`, performs tmpdir-scoped background cleanup, normalizes the captured stdout, then writes `.completed/step-5-terminal`.
- `.completed/step-5-terminal` is a terminal-review sentinel, not a wrapper-exit sentinel. It is written only after a captured Step 5 envelope normalizes successfully.

## Edit-in-sync

Update `skills/implement/SKILL.md`, `scripts/test-implement-structure.sh`, `skills/implement/scripts/test-step-5-review.sh`, and Python Step 5 identity/normalization tests when this contract or argv changes.
