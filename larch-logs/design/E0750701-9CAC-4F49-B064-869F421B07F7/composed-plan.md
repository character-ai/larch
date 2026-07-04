## Plan

## Approach

- Treat the supplied approach synthesis as `NO_SKETCHES`. Draft from direct code inspection and the supplied approved outline.
- Keep Step 8 code unchanged. Its `.step-8-ship-handoff.rc` path already persists signal exits for `ship route-exit`.
- Implement Step 5 like the current Step 3 pattern:
  - launch `review-and-fix step5 --mode loop --new-process-group` in the background;
  - capture stdout to a temp file and stderr to an implement tmpdir log;
  - record an identity sidecar with implement-specific filenames;
  - trap `TERM`, `HUP`, and `INT`;
  - on external signal, write a detached marker and skip terminal completion sentinel creation;
  - on next wrapper entry, reattach to the detached loop, wait for completion, replay or normalize the captured Step 5 envelope, then write `.completed/step-5-terminal`.
- Add an orphan timeout to detached loops only. Use the approved default `7200` seconds and keep it below the existing `TIMEOUT_S=21600` marker.
- Add Python support behind `python/cli.py`. Do not add new shell shims.

## Files to modify/create

### UPDATED: skills/implement/scripts/step-5-review.sh

Refactor the wrapper from a foreground Python call plus unconditional `EXIT` sentinel into a signal-aware launcher.

- Add wrapper state variables for loop pid, stdout capture path, identity-ready flag, and external-signal rc.
- Add `TERM`, `HUP`, and `INT` traps that set an external-signal flag and exit with `143`, `129`, or `130`.
- Add detached-marker helpers using `$IMPLEMENT_TMPDIR/.step5-wrapper-detached`.
- Register EXIT and TERM/HUP/INT traps immediately after entry, before the detached-marker entry check and before any `await-loop-identity` call (mirrors `design-step3-review.sh` lines 536–541).
- Add reattach flow at entry — MUST execute before any stale-sentinel cleanup or fresh-loop launch:
  - detect a regular, non-symlink `.step5-wrapper-detached` marker as the first entry check;
  - read `PID` and `STDOUT_FILE` from the marker;
  - call `python/cli.py review-and-fix await-loop-identity --implement-tmpdir ...`;
  - call `python3 cli.py session kill-background-processes --implement-tmpdir ...` MANDATORILY after await and before normalize (mirrors Step 3 `_step3_review_kill_tmpdir_processes` ordering); extend `kill-background-processes` to accept `--implement-tmpdir` with the same validated allowlist as `--design-tmpdir`;
  - call `python/cli.py review-and-fix normalize-status --implement-tmpdir ... --stdout-file ... --loop-rc 0`;
  - write `.completed/step-5-terminal` and remove `.bg-wait-active` only after normalize succeeds;
  - clear marker and identity sidecar only after successful normalize;
  - if await or normalize returns non-zero: restore the detached marker (write `.step5-wrapper-detached` from saved PID/STDOUT_FILE/SIGNAL); remove `.step5-reattach-active`; emit a preflight-failure or stall envelope to stdout so the orchestrator gets a parseable signal; remove `.bg-wait-active`; exit non-zero without spawning a fresh loop.
- Only when no detached marker is present: clear stale `step-5-terminal` sentinel and launch the fresh loop in the background with `--new-process-group --orphan-timeout-s 7200`.
- Reattach handshake (consistent with await contract): the wrapper writes a `.step5-reattach-active` sidecar BEFORE removing `.step5-wrapper-detached`; then calls `await-loop-identity --reattach` (which skips the detached-marker prerequisite); the Python orphan check pauses when `.step5-reattach-active` exists; on await success: remove `.step5-reattach-active`; on TERM/HUP/INT during await: re-write the detached marker (restoring PID/STDOUT_FILE/SIGNAL), remove `.step5-reattach-active`, disown, and exit.
- Call `review-and-fix write-loop-identity` after launch with expected signature `review-and-fix step5`.
- On normal wait completion, clear the identity sidecar, normalize captured stdout, then write `.completed/step-5-terminal`.
- On external signal after identity publication, write the detached marker and `disown -h` the loop. Do not write `.completed/step-5-terminal`.
- On external signal before identity publication (pre-identity window): the wrapper holds the raw `$_loop_pid` from the `&` launch; validate the PID is still alive and has the expected command signature (`review-and-fix step5`) via `ps` with expected PGID matching PID; then kill the process group by PGID; do not write the detached marker; do not write `.completed/step-5-terminal`. This sidecarless path is required because the identity file has not been written yet. Add a harness assertion that the fake pre-identity child process group actually exits.
- Add a targeted harness case in `test-step-5-review.sh` for signal arrival between loop launch and identity-ready, asserting that neither `.step5-wrapper-detached` nor `.completed/step-5-terminal` is written.
- Preserve dynamic archetype cap validation, difficulty override forwarding, bg-wait marker contents, and banner text unless an argv note must change.

### UPDATED: skills/implement/scripts/step-5-review.md

Update the contract.

- Replace the invariant that says the `EXIT` trap writes `.completed/step-5-terminal` on every exit.
- Document signal detach, detached marker, identity sidecar, stdout capture, reattach behavior, and the orphan timeout.
- State that `.completed/step-5-terminal` is a terminal-review sentinel, not a wrapper-exit sentinel.
- Keep Bash 3.2 portability requirements.

### UPDATED: skills/implement/SKILL.md

Update Step 5 prose and post-notification routing.

- Keep the existing launcher fence unchanged.
- Replace “execs `review-and-fix step5`” wording with “launches the file-backed review loop.”
- State that a signal-induced wrapper stop does not satisfy Step 5 completion.
- Keep the existing no-polling and notification behavior. Do not add prompt-side signal handling.
- Add a post-notification detached-marker carve-out BEFORE the preflight-failure branch: when `$IMPLEMENT_TMPDIR/.step5-wrapper-detached` is a regular, non-symlink file and `$IMPLEMENT_TMPDIR/.completed/step-5-terminal` is absent, re-invoke the same `step-5-review.sh` immediate-background fence and wait again; do not enter the preflight-failure or absent-sentinel stall path.
- Add a NEVER #8 note: absent `step-5-terminal` together with an existing `.step5-wrapper-detached` marker is expected detach, not hook inconsistency; do not treat it as stall-step-5.

### UPDATED: skills/design/scripts/design-step3-review.sh

Add orphan cap and reattach handshake to the detached Step 3 loop.

- Pass `--orphan-timeout-s 7200` to both fresh and `--starting-round` `plan-review run --mode loop --new-process-group` calls.
- Reattach handshake (consistent with await contract): in `_step3_review_reattach_detached_loop`, write `.step3-reattach-active` sidecar BEFORE removing `.step3-wrapper-detached`; call `plan-review await-loop-identity --reattach` (skips marker check); on signal during wait: re-write the detached marker, remove `.step3-reattach-active`, disown; on failed await/normalize: restore the detached marker, remove `.step3-reattach-active`.
- Keep existing signal traps, identity sidecar, sentinel rules, and teardown path intact.

### UPDATED: skills/design/scripts/design-step3-review.md

Document the Step 3 orphan timeout.

- State that detached Step 3 loops self-stop after the configured orphan bound.
- Clarify that the cap applies to detached loops and does not change normal attached review routing.

### UPDATED: skills/implement/scripts/step-8-ship.md

Document Step 8 as persist-and-resume by design.

- State that `persist_handoff` records rc `143` on `SIGTERM`.
- State that `.step-8-ship-handoff.rc` is the hook release sentinel and `ship route-exit` owns recovery.
- Explicitly say Step 8 does not use detach-and-reattach.

### UPDATED: python/larch/core/config.py

Add single-source constants.

- `IMPLEMENT_STEP5_LOOP_IDENTITY_FILE = ".step5-loop-identity.json"`
- `IMPLEMENT_STEP5_WRAPPER_DETACHED_FILE = ".step5-wrapper-detached"`
- `IMPLEMENT_STEP5_REATTACH_ACTIVE_FILE = ".step5-reattach-active"`
- `IMPLEMENT_STEP5_KILL_LOG_FILE = "implement-step5-kill.log.jsonl"`
- `DETACHED_REVIEW_ORPHAN_TIMEOUT_DEFAULT_S = 7200`
- Add equivalent `DESIGN_STEP3_REATTACH_ACTIVE_FILE = ".step3-reattach-active"` for Step 3 parity.

### UPDATED: python/larch/core/process_identity.py

Generalize loop identity helpers without breaking Step 3.

- Preserve the existing `plan-review` CLI behavior and design filenames.
- Add implement-specific entry points for:
  - `write_step5_loop_identity_main`
  - `await_step5_loop_identity_main`
  - `teardown_step5_loop_identity_main`
- Reuse the existing identity validation, stable-process retry, and process-group termination code.
- Keep Step 5 sidecars under `$IMPLEMENT_TMPDIR` and use the new config constants.
- For Step 5 await, wait for the identity process to exit or disappear. Do not require `.step3-review-result.env`.
- Add `--reattach` flag to `await_step5_loop_identity_main`: when set, skip the `.step5-wrapper-detached` prerequisite check and proceed directly to polling; the orphan cap pauses because `.step5-reattach-active` is present.
- Require a regular, non-symlink Step 5 detached marker ONLY on the normal (non-reattach) await path.
- Log Step 5 teardown to `IMPLEMENT_STEP5_KILL_LOG_FILE`.

### UPDATED: python/larch/cli.py

Register the new verbs.

- `("review-and-fix", "write-loop-identity")`
- `("review-and-fix", "await-loop-identity")`
- `("review-and-fix", "teardown-loop-identity")`
- `("review-and-fix", "normalize-status")`
- Add `("review-and-fix", "normalize-status")` to `_MACHINE_STDOUT_KEYS` so it routes directly to stdout and bypasses the quiet-init log path.

### UPDATED: python/larch/state/finalize.py (or session kill-background-processes host)

Extend `kill-background-processes` for implement tmpdir.

- Add `--implement-tmpdir` flag that accepts the implement session tmpdir path with the same validated allowlist as `--design-tmpdir`.
- When `--implement-tmpdir` is supplied, kill processes whose recorded tmpdir matches the implement path.
- Keep `--design-tmpdir` behavior unchanged.

### UPDATED: python/larch/review/review_and_fix.py

Add Step 5 loop support.

- Add parser flags:
  - `--new-process-group`
  - `--orphan-timeout-s`
- Call `os.setsid()` when `--new-process-group` is present, matching the Step 3 implementation style.
- Validate `--orphan-timeout-s` as a positive number when supplied.
- During loop mode, check whether `$IMPLEMENT_TMPDIR/.step5-wrapper-detached` exists and has exceeded the orphan timeout.
- When the orphan cap fires, emit a normal Step 5 envelope:
  - `STEP5_REVIEW_STATUS=stall`
  - `STALL_TRACKING=true`
  - `STALL_REASON=orphan-timeout`
  - preserve known round counts and cap data.
- Orphan check reads `.step5-wrapper-detached` marker age at each loop boundary; when the marker is absent OR `.step5-reattach-active` is present, the orphan cap does not fire (loop is considered attached or actively being reattached).
- Add `normalize-status` support that reads a captured stdout file, verifies it contains a `STEP5_REVIEW_STATUS` envelope, replays it to stdout, and returns a failing rc when the envelope is absent. Must NOT call `quiet_init`; must write the replay directly to stdout (registered in `_MACHINE_STDOUT_KEYS`).
- Add `await-loop-identity` support with a `--reattach` flag that skips the detached-marker prerequisite while still requiring a valid identity sidecar.
- Keep existing loop statuses and prompt-side branch contracts unchanged.

### UPDATED: python/larch/review/plan_review.py

Add Step 3 orphan support.

- Add `--orphan-timeout-s` to `plan-review run`.
- Validate it as positive when supplied.
- In the Step 3 loop, check the detached marker age at safe loop boundaries; skip the orphan check when `.step3-reattach-active` is present (wrapper is actively reattaching).
- When the cap fires, persist and emit a terminal failure envelope with an `orphan-timeout` reason while routing through existing failed-review handling.
- Do not change normal review rounds, Gate B handoffs, or postplan routing.

### UPDATED: python/larch/review/plan_review_normalize.py

Normalize Step 3 orphan output.

- When `plan-review run` emits `REASON=orphan-timeout`, map it to the following pinned values: `STEP3_REVIEW_LOOP_STATUS=panel-failed`, `LOOP_STATUS=panel-failed`, `REASON=orphan-timeout`, `NEXT_ACTION=step3b-bypass`.
- Keep orphan-timeout out of `_STEP3_INTERACTIVE_STATUSES` so sentinel synthesis is not suppressed.
- Extend `test-design-step3-review.sh` and/or `test_plan_review.py` to assert the normalized envelope for orphan-timeout fires `NEXT_ACTION=step3b-bypass` and does not enter Gate B.
- Preserve all other sentinel synthesis exclusions and interactive-status rules unchanged.

### UPDATED: python/tests/core/test_process_identity.py

Add identity helper coverage.

- Assert Step 5 identity write uses `IMPLEMENT_STEP5_LOOP_IDENTITY_FILE`.
- Assert Step 5 await requires the Step 5 detached marker.
- Assert Step 5 teardown uses the implement kill log and does not touch Step 3 sidecars.
- Keep existing Step 3 tests passing unchanged.

### UPDATED: python/tests/implement/test_implement_dispatch.py

Update CLI registry assertions for the new `review-and-fix` verbs.

### UPDATED: python/tests/review/test_review_and_fix.py

Add Step 5 Python and wrapper tests.

- Assert `--new-process-group` calls `os.setsid()` and fails closed when unavailable.
- Assert invalid `--orphan-timeout-s` exits as a parser or preflight error.
- Assert orphan-timeout emits a Step 5 stall envelope with `STALL_REASON=orphan-timeout`.
- Extend the shell wrapper argv capture test to require `--new-process-group` and `--orphan-timeout-s 7200`.
- Add a deterministic wrapper signal test if feasible with the existing shim:
  - send `SIGTERM` to the wrapper while the fake child is running;
  - assert `.step5-wrapper-detached` exists;
  - assert `.completed/step-5-terminal` is absent.

### UPDATED: skills/design/scripts/test-design-step3-review.sh

Extend Step 3 static and live checks.

- Assert both fresh and resume launch paths pass `--orphan-timeout-s 7200`.
- Assert the wrapper still uses `--new-process-group`, identity write, and identity teardown.
- Add a Python-level assertion that orphan-timeout is normalized to a terminal failed-review route.

### NEW: skills/implement/scripts/test-step-5-review.sh

Add a Bash harness for the Step 5 wrapper contract.

- Use a fake plugin root or Python shim like the existing Python wrapper tests.
- Assert the wrapper writes `.bg-wait-active` with `STEP=implement-step5-review`.
- Assert normal completion writes `.completed/step-5-terminal`.
- Assert signal-induced detach does not write `.completed/step-5-terminal`.
- Assert reentry with a detached marker calls `review-and-fix await-loop-identity` and `review-and-fix normalize-status`.
- Assert stale detached markers do not launch duplicate loops.

### NEW: skills/implement/scripts/test-step-5-review.md

Document the new harness.

- List the signal-detach, false-sentinel, reattach, and normal-completion contracts.
- Note that the harness uses stubs and does not launch real reviewers.

### UPDATED: scripts/test-implement-structure.sh

Add static guards for the changed Step 5 contract.

- Assert `step-5-review.sh` contains `review-and-fix write-loop-identity`, `await-loop-identity`, and `normalize-status`.
- Assert `step-5-review.sh` calls `review-and-fix teardown-loop-identity` in the cleanup path.
- Assert it traps `TERM`, `HUP`, and `INT`.
- Assert the terminal sentinel is not written unconditionally in a bare `EXIT` cleanup path.

### UPDATED: Makefile

Wire the new Step 5 wrapper harness.

- Add `test-step-5-review`.
- Add it to exactly one `test-harnesses-N` shard.
- Keep `make test-harness-shards-coverage` passing.

## Edge cases

- Signal before identity sidecar exists: do not disown blindly. Fall back to cleanup and do not stamp terminal completion.
- Signal after identity sidecar exists: detach and preserve the identity sidecar for reattach.
- Detached marker is symlink or malformed: reject it, clean safe sidecars, and launch or fail through existing preflight behavior.
- Captured stdout lacks `STEP5_REVIEW_STATUS`: treat as Step 5 preflight or loop failure. Do not authorize Step 6.
- Orphan timeout fires during an attached run: should not happen because the detached marker is absent.
- Orphan timeout fires after a real session death: emit a stall/failure envelope and stop before unbounded reviewer spend.
- Step 8 `SIGTERM`: preserve existing rc-only handoff behavior.

## Failure modes when non-trivial

- False completion sentinel remains possible if `_step5_cleanup` still writes `.completed/step-5-terminal` before normalization. Tests must guard this.
- Reattach can double-run Step 5 if marker cleanup happens before captured output is normalized. Clean marker only after successful await and normalize.
- Process identity reuse can kill the wrong process if Step 5 reuses Step 3 sidecars. Use separate config constants and expected signatures.
- Orphan timeout can create a new status that prompt-side routing does not understand. Normalize it into existing terminal routes.
- Long in-flight reviewer subprocesses may only observe orphan checks at loop boundaries. Avoid adding unsafe prompt-side polling to compensate.

## Testing strategy

Run only changed-file relevant checks.

- `bash skills/implement/scripts/test-step-5-review.sh`
- `bash skills/design/scripts/test-design-step3-review.sh`
- `bash scripts/test-implement-structure.sh`
- `python3 -m pytest python/tests/core/test_process_identity.py -q`
- `python3 -m pytest python/tests/implement/test_implement_dispatch.py -q -k registry`
- `python3 -m pytest python/tests/review/test_review_and_fix.py -q -k 'step5 or new_process_group or orphan'`
- `make test-harness-shards-coverage`
- `make py-lint-main` if Python files changed enough for lint coverage.
- `make py-test` is optional unless scoped pytest or lint suggests wider Python breakage.

## Acceptance

Run only changed-file relevant checks.

- `bash skills/implement/scripts/test-step-5-review.sh`
- `bash skills/design/scripts/test-design-step3-review.sh`
- `bash scripts/test-implement-structure.sh`
- `python3 -m pytest python/tests/core/test_process_identity.py -q`
- `python3 -m pytest python/tests/implement/test_implement_dispatch.py -q -k registry`
- `python3 -m pytest python/tests/review/test_review_and_fix.py -q -k 'step5 or new_process_group or orphan'`
- `make test-harness-shards-coverage`
- `make py-lint-main` if Python files changed enough for lint coverage.
- `make py-test` is optional unless scoped pytest or lint suggests wider Python breakage.

review_status: cap-hit
rounds_completed: 2
difficulty: HARD
diff_lines: 950
