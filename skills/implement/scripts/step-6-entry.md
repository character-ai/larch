# step-6-entry.sh

Step 6 review boundary bgjob launcher. The foreground wrapper rehydrates telemetry keys, truncates the Step 6 merge-result env, and starts `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" implement step-6-entry` as a bgjob.

## Caller

`skills/implement/SKILL.md` invokes this wrapper from the named `/implement` Step 6 composite fence. Launcher stdout is exactly `BGJOB_STATUS=STARTED STEP=implement-step6-checks PGID=<n>`; the orchestrator then calls `python/cli.py bgjob wait --step implement-step6-checks` until `DONE`.

## Arguments

- `--forked-target true|false`: forwarded to the folded Step 6 checks/commit/`7.r` composite. Defaults to `false`.
- `--force-checks true|false`: repair re-entry only. Bypasses review-change detection and always runs the Step 6 checks/commit/`7.r` composite. Defaults to `false`.

## KV grammar

The Python entrypoint writes `$IMPLEMENT_TMPDIR/.review-boundary-passed` before child legs.

Normal entry (`--force-checks false`) runs `review-and-fix check-changes` with these pinned baselines under `$IMPLEMENT_TMPDIR`:

- `--baseline pre-review-untracked.txt`
- `--head-baseline pre-review-head.txt`

It relays these change-detection KVs before any composite routing:

- `FILES_CHANGED=true|false`
- `UNTRACKED_BASELINE=present|missing`
- `GIT_PROBE_FAILED=true|false`

When `FILES_CHANGED=false`, it emits `NEXT_ACTION=skip-to-7a` and does not run checks. When `FILES_CHANGED=true`, it conditionally runs the fixed Step 6 checks/commit/`7.r` composite and relays that composite envelope.

When change detection fails (malformed or missing `FILES_CHANGED`, or `check-changes` exits non-zero), the entrypoint seeds durable stall state with `stall_step=6` and `bail_reason=review-change-detection-failed`, then emits `NEXT_ACTION=stall`. Seeding failure returns non-zero without `NEXT_ACTION`.

Repair re-entry (`--force-checks true`) skips change detection, never emits `NEXT_ACTION=skip-to-7a`, and relays only the fixed Step 6 checks/commit/`7.r` composite envelope.

Valid routing records are newline-delimited and line-anchored:

- `NEXT_ACTION=skip-to-7a|continue|checks-failed|stall`
- `CHECKPOINT_NEXT=continue|load-routing`, only with `NEXT_ACTION=continue`

## Invariants

- Bash 3.2 portable; no associative arrays or namerefs.
- Self-rehydrates `CLAUDE_PLUGIN_ROOT` from `$IMPLEMENT_TMPDIR/plugin-root.env` where needed.
- Step 6 relies on the telemetry contract in `skills/shared/session-setup-output.md` and reads the session-env copy under `$IMPLEMENT_TMPDIR`.
- Uses bgjob step slug `implement-step6-checks`, clears stale `.completed/step-6-terminal`, and passes that sentinel to `bgjob start`.
- The wrapper does not write `.bg-wait-active`; the terminal sentinel is written by the bgjob daemon and by the child cleanup as a compatibility marker.
- The wrapper does not call `review-and-fix check-changes` directly. Python owns the composite routing.

## Edit-in-sync

Update `skills/implement/SKILL.md`, `skills/implement/references/checks-repair-loop.md`, and the implement structure/timing harnesses when this contract or argv changes.
