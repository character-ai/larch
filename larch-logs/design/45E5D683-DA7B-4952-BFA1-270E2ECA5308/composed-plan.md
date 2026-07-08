## Plan

## Approach

The likely defect is that post-Step-0 `/implement` fences run through `implement-run-$PPID.sh`, then `larch-run.sh`, then the Step 5 wrapper. That path does not currently re-export the stable Claude PID embedded in the launcher name. Step 5 therefore falls back to the wrapper shell `$PPID` for `bgjob start --owner-pid`. That parent can exit soon after launch, so the bgjob daemon marks the review orphaned after `BGJOB_OWNER_GRACE_S=120`.

Fix the transport, not Step 5 only:

- Export `LARCH_CLAUDE_PID` from the generated `implement-run-<pid>.sh` launcher before it execs `larch-run.sh`.
- Preserve an explicit inherited `LARCH_CLAUDE_PID` if present.
- Leave `bgjob` orphan detection and grace timing unchanged.
- Leave Step 5 wrapper ownership code unchanged unless tests reveal a direct mismatch.

## Files to modify/create

### UPDATED: python/larch/state/session_env.py

In `_implement_run_launcher_text(pid)`, add an export before `exec "$LARCH_RUN_SH" "$@"`:

- `export LARCH_CLAUDE_PID="${LARCH_CLAUDE_PID:-<pid>}"`
- Keep `IMPLEMENT_TMPDIR` export unchanged.
- Do not add this key to `current-implement-env-<pid>.sh`; the PID is already trusted from the validated `--claude-pid` used to generate the launcher.

### UPDATED: python/tests/state/test_session_env.py

Extend `test_write_and_clear_implement_env_pointer` so the fake `larch-run.sh` writes the visible `LARCH_CLAUDE_PID`.

Assert:

- The stable runner still works without `IMPLEMENT_TMPDIR`.
- The child sees `LARCH_CLAUDE_PID=12345`.
- Existing pointer contents stay unchanged, unless the implementation intentionally writes the PID there.

### UPDATED: scripts/test-implement-fence-shape.sh

Update the generated stable-runner sandbox to assert the stable `implement-run-12345.sh` path exports `LARCH_CLAUDE_PID=12345` to `.sh` children.

Keep the existing argv passthrough assertion.

### MAY_UPDATE: skills/implement/scripts/test-step-5-review.sh

Only update this harness if the implementation touches `skills/implement/scripts/step-5-review.sh`.

If updated, add a targeted assertion that fresh `bgjob start` receives the exported `--owner-pid` value, not an incidental shell parent PID.

## Edge cases

- Resumed `/implement` runs should rewrite the PID-keyed launcher during Step 0 bootstrap, so the new Claude session PID becomes the owner for later bgjobs.
- In-flight runs already launched with an old runner may still orphan; the fix applies after rerun or resume refreshes the launcher.
- Direct calls to `$IMPLEMENT_TMPDIR/larch-run.sh` still have no embedded Claude PID. They may keep the current `$PPID` fallback. That is outside the normal orchestrator path.
- If `LARCH_CLAUDE_PID` is already exported, keep it. This avoids surprising nested wrappers and preserves the current Step 0 behavior.

## Failure modes

- If the runner does not export the PID, Step 5 can still hit `BGJOB_RC=orphaned` at about 120 seconds.
- If the exported PID is stale, `bgjob start` may fail to capture owner identity or the daemon may orphan later. Step 0 already validates and rewrites the launcher for the current Claude PID.
- Do not raise `BGJOB_OWNER_GRACE_S`; that would mask the broken owner identity and weaken orphan cleanup for every bgjob user.

## Testing strategy

Run only targeted checks:

- `python3 -m pytest python/tests/state/test_session_env.py`
- `bash scripts/test-implement-fence-shape.sh`
- If `skills/implement/scripts/test-step-5-review.sh` changes: `bash skills/implement/scripts/test-step-5-review.sh`
- Optional focused lint for Python edits: `python3 -m ruff check python/larch/state/session_env.py python/tests/state/test_session_env.py`

## Difficulty

This is workflow-affecting and changes a session launcher that bgjob-owned Step 5 depends on. It also touches a session-env writer surface, so the floor is `MODERATE`.

## Acceptance

Run only targeted checks:

- `python3 -m pytest python/tests/state/test_session_env.py`
- `bash scripts/test-implement-fence-shape.sh`
- If `skills/implement/scripts/test-step-5-review.sh` changes: `bash skills/implement/scripts/test-step-5-review.sh`
- Optional focused lint for Python edits: `python3 -m ruff check python/larch/state/session_env.py python/tests/state/test_session_env.py`

review_status: ok
rounds_completed: 1
difficulty: MODERATE
diff_lines: 30
