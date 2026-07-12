## Plan

### Approach

Use `python/cli.py bgjob adapt` as the single start-or-reattach authority for `/design` Steps 3, 4, and 5c. Keep only parent-only routing before delegation; run child work only under the adapter’s standard `--bgjob-child --merge-result-env <path>` suffix.

Provide one shared, trusted session-env resolver for wrappers to invoke before any parent-only routing. It validates and exports only allowlisted session values, so parent logic receives `DESIGN_TMPDIR` and related bindings even when launchers supply only `--session-env-path`. The adapter independently resolves the same trusted input for its locked decision path.

Extend the shared adapter only for two workflow-neutral needs: clearing a path immediately before a confirmed fresh launch and explicitly replacing a completed result under the decision lock. Default terminal-result reattachment remains unchanged.

## Files to modify/create

### UPDATED: python/larch/bgjob/cli.py

- Add adapter-only parsing for trusted `--session-env-path`, `--clear-on-fresh <path>`, and explicit `--replace-completed-result`.
- Add a shared session-env resolution command for shell wrappers that validates the trusted allowlist and emits shell-safe exports only after rejecting malformed, unsafe, missing, or non-directory `DESIGN_TMPDIR` values with stable `BGJOB_ERROR` output.
- Resolve `DESIGN_TMPDIR` from the trusted session env when `--tmpdir` is otherwise unavailable.
- Keep `--tmpdir`, `--step`, `--budget-s`, and optional `--owner-pid` explicit in every design caller.

### UPDATED: python/larch/bgjob/adapt.py

- Carry the new adapter options through the locked decision path.
- Preserve the default policy: a valid terminal result emits `BGJOB_STATUS=DONE` without launching or mutating completion state.
- For `--clear-on-fresh`, validate the regular, non-symlink path under the job tmpdir and clear it only after terminal-result and live-job checks establish a fresh launch, immediately before merge-env preparation and daemon start.
- For `--replace-completed-result`, reject active or identity-unverifiable jobs; under the decision lock, safely invalidate only the terminal result for an explicit retry, then follow the normal fresh-launch path.
- Continue creating and truncating the adapter-owned merge env, append `--bgjob-child --merge-result-env <path>` to the child command, and retain fail-closed registry, identity, and path validation.

### UPDATED: python/tests/bgjob/test_bgjob_adapt.py

- Cover shared session-env resolution, wrapper-consumable exports, adapter tmpdir resolution, and malformed or unsafe failures.
- Cover default completed-result `DONE` reattachment, fresh-only sentinel clearing, and the guarantee that neither occurs for live jobs.
- Cover explicit completed-result replacement, including refusal when a registry is live or identity cannot be verified, and concurrent callers launching at most once.
- Retain merge publication and adapter child-suffix coverage.

### UPDATED: skills/design/scripts/design-step3-review.sh

- Resolve `--session-env-path` through the shared trusted resolver before parent-only result reads, resume validation, state writes, pause handling, or tmpdir use; do not source session-env files locally.
- Replace `--run-loop-child` with terminal-suffix parsing for `--bgjob-child --merge-result-env <path>`; reject duplicate, incomplete, or non-terminal adapter controls and preserve all non-control resume/public argv cells unchanged.
- Keep the parent-only `--read-result-env` normalization branch, resume validation/state writes, pause-save branch, tmpdir validation, and parent routing behavior outside child mode.
- Delegate launch/reattach to `bgjob adapt` with `--step design-step3-review`, `--tmpdir "$DESIGN_TMPDIR"`, `--budget-s 21600`, `--session-env-path` when present, and `--owner-pid "$CLAUDE_PID"` when present.
- Pass `--replace-completed-result` when `STEP3_REVIEW_HAS_RESUME_STATE=true`; retain default completed-result reattachment for ordinary duplicate invocations.
- Pass the existing child argv without legacy self-reexec flags and request `--clear-on-fresh "$DESIGN_TMPDIR/.completed/step-3"` so valid `DONE` reattachment preserves the marker.
- Keep scope-anchor validation, loop execution, stderr capture, and status normalization in child mode.
- After every handled child terminal path—including missing scope anchor, panel-init failure, pause race, and normal normalization—atomically publish the current invocation’s required routing envelope to the adapter merge path, then exit zero. Reserve non-zero child exits for failure to create or publish a complete required envelope.
- Retain `.step3-review-result.env` as the compatibility sidecar, but reject stale or incomplete sidecar rows instead of allowing them to satisfy the new result.
- Remove wrapper-local registry inspection, stale bgjob-result deletion, merge-env recreation, argv tempfile transport, direct `bgjob start`, and self-reexec logic.

### UPDATED: skills/design/scripts/design-step3b-tail.sh

- Resolve `--session-env-path` through the shared trusted resolver before parent pause handling or tmpdir use.
- Replace `--run-tail-child` with the standard adapter child suffix and required merge-path parsing.
- Delegate `design-step4-tail` through `bgjob adapt` with explicit tmpdir, 900-second budget, shared session-env resolution, and optional owner PID.
- Preserve parent pause handling before delegation and make an in-flight child pause publish its terminal routing outcome to the supplied merge env.
- Preserve FINALIZE, rejected-finding rendering, Gate C, preview generation, and completion markers in child mode.
- Atomically publish `SKIP_APPROVE_REQUESTED_GATEC`, rejected-body paths, preview paths, and the optional dialectic digest to the adapter merge env on successful completion; fail non-zero if required publication fails.
- Remove local liveness checks, stale-result deletion, merge-env recreation, direct start, self-reexec, and session-env sourcing.

### UPDATED: skills/design/scripts/design-step5c.sh

- Resolve `--session-env-path` through the shared trusted resolver before parent-only routing or tmpdir use.
- Replace `--run-step5c-child` with standard terminal adapter-control parsing and remove only those controls before forwarding the original public argv to `python/cli.py design step5c`.
- Delegate through `bgjob adapt` with explicit `--step design-step5c`, `--tmpdir "$DESIGN_TMPDIR"`, 21600-second budget, shared session-env resolution, and optional owner PID.
- Add a wrapper-private explicit retry flag that maps to adapter `--replace-completed-result`; do not forward that control to the Python child. Ordinary invocations retain default terminal-result `DONE` reattachment.
- In child mode, copy the freshly produced Step 5c status envelope to the adapter merge path atomically and fail non-zero if required publish, validation, summary, or cleanup rows are absent.
- Remove local session-env sourcing, registry inspection, stale-result deletion, merge-env recreation, direct start, and self-reexec logic.

### UPDATED: python/larch/design/design_step5c.py

- Ensure pause, missing-Step-5b, and other pre-publish terminal branches write the authoritative Step 5c status envelope before returning.
- Preserve existing publish refusal, validator, assessment, final-summary, and cleanup rows so the shell child can publish a complete adapter result for both success and handled refusal outcomes.

### UPDATED: skills/design/SKILL.md

- Change documented Step 5c retry actions—missing composition, validator repair, size override, and return-from-Gate-C assessment repair—to invoke the wrapper’s explicit fresh-attempt control.
- Keep ordinary Step 5c re-entry on the default completed-result reattachment path.

### UPDATED: skills/design/references/finalize-step5.md

- Require the wrapper-private fresh-attempt token for every documented Step 5c rerun, including missing-composition repair.

### UPDATED: skills/design/references/validator-failure.md

- Require the explicit retry token for both autofix-ok and Fix-and-retry Step 5c paths.

### UPDATED: skills/design/references/approval-gates.md

- Require the explicit retry token for Step 5c reruns after Gate C assessment repair.

### UPDATED: skills/design/references/decompose-panel.md

- Require the explicit retry token for the size Override Step 5c rerun.

### UPDATED: skills/design/scripts/test-design-step3-review.sh

- Update fake adapter coverage and static assertions for trusted pre-parent session resolution, `bgjob adapt`, explicit tmpdir/owner/session arguments, standard child controls, adapter-owned merge paths, and removal of retired lifecycle helpers.
- Exercise launcher-style invocation with `DESIGN_TMPDIR` initially unset, fresh launch, valid completed-result reattachment, resume forwarding, and fresh-only Step 3 completion-marker clearing.
- Seed a completed result plus resume argv/state and assert the resume path requests replacement and starts a fresh child rather than reattaching stale `DONE`.
- Exercise normalized merge rows, missing-scope routing publication, panel-init failure, pause routing, and rejection of stale compatibility-sidecar rows.
- Assert handled missing-scope and panel-init terminal routes publish the expected `NEXT_ACTION` with `BGJOB_RC=0`; assert merge-publication failure remains non-zero.

### UPDATED: skills/design/scripts/test-design-step5c.sh

- Update the fake launcher for trusted pre-parent session resolution, the adapter contract, and injected child suffix.
- Verify public argv forwarding, explicit tmpdir/owner/session bindings, fresh merge publication, default completed-result reattachment, and no relaunch on an ordinary duplicate invocation.
- Exercise an explicit retry after validator, size, and assessment refusal; assert it replaces the terminal result only for that retry and launches a new child.

### NEW: skills/design/scripts/test-design-step3b-tail.sh

- Exercise the Step 4 tail adapter contract, including trusted pre-parent session resolution, standard child controls, explicit tmpdir/owner/session arguments, completed-result reattachment, required Gate C merge rows, and pause-race terminal publication.

### UPDATED: Makefile

- Add `test-design-step3b-tail` to `.PHONY`, include it in the harness shard, and run the new tail adapter harness through the timing wrapper.

### UPDATED: scripts/residual-bash-paths.txt

- Register `skills/design/scripts/test-design-step3b-tail.sh` as an approved residual Bash harness.

### UPDATED: agent-lint.toml

- Add the new Makefile-only Step 4 tail harness to the existing harness exclusions so lint recognizes its registered execution path.

### UPDATED: skills/design/scripts/test-step3-orchestrator-fence.sh

- Keep Step 3 normalization and starting-round coverage aligned with the standard child-mode shape.
- Assert file-first result reads, non-zero postplan-failure routing, preservation of a valid completed result without clearing the Step 3 completion marker, and fresh launch for a completed-result resume invocation.

### UPDATED: scripts/test-design-structure.sh

- Require all three adapters to resolve supplied session env before parent routing and invoke `bgjob adapt` with explicit step, tmpdir, budget, and conditional owner binding.
- Pin standard `--bgjob-child --merge-result-env` child parsing and prohibit legacy `--run-*-child` gates.
- Reject direct `bgjob start`, local registry-liveness heredocs, wrapper-owned stale-result deletion, wrapper merge-env recreation, and wrapper session-env sourcing.
- Preserve `/design` wait, `BGJOB_RC=0`, result-env, completion-boundary, explicit-Step-3-resume-replacement, and explicit-Step-5c-retry assertions.

### UPDATED: skills/design/scripts/design-step3-review.md

- Document shared trusted session resolution before parent behavior, the standard adapter child suffix, parent-only result/resume/pause behavior, fresh-only Step 3 marker clearing, and child-side atomic routing publication.
- Specify that handled terminal routing outcomes publish complete rows and exit zero; only envelope/publication failure is non-zero.
- Document resume-state replacement of a completed result while retaining ordinary duplicate reattachment.
- Retain compatibility-sidecar and normalization contracts while stating that stale sidecar rows cannot satisfy a new adapter result.

### UPDATED: skills/design/scripts/design-step3b-tail.md

- Replace wrapper-local lifecycle claims with shared adapter ownership and document trusted pre-parent session resolution plus explicit tmpdir/owner/session bindings.
- Define the standard child suffix, Gate C merge rows, completed-result policy, and pause-race terminal publication.

### UPDATED: skills/design/scripts/design-step5c.md

- Document shared trusted session resolution before parent behavior, default completed-result reattachment, the standard child suffix, adapter merge env, and authoritative Step 5c status-envelope transfer.
- Define the wrapper-private explicit retry control and limit its use to documented repair/refusal retry paths.

## Edge cases

- A valid completed result emits `DONE` without launching, clearing Step 3’s marker, or replacing a Step 5c terminal envelope.
- A launcher that supplies only `--session-env-path` receives validated session values before wrapper parent routing.
- A Step 3 invocation with resume state replaces a completed result and launches its requested fresh phase; ordinary duplicates still reattach.
- A live identity-valid job reattaches without wrapper-specific liveness decisions.
- Unsafe, malformed, expired-live, or identity-unverifiable registry state fails closed through stable adapter errors.
- Standard adapter controls remain parseable after public argv; only the terminal control suffix is stripped.
- Missing scope, panel-init, and pause-race exits publish required terminal routing rows rather than producing a generic successful daemon result.
- Explicit Step 5c retry replaces a completed result only after the adapter has ruled out active or unverifiable ownership.
- Merge-env paths remain regular, non-symlink files under the bgjob directory in `DESIGN_TMPDIR`.

## Failure modes

- Missing or unsafe session-env/tmpdir resolution returns a machine-readable adapter error before parent routing or launch.
- Failure to publish required child rows prevents normal Step 3, Gate C, or Step 5c continuation.
- Handled Step 3 terminal routing failures exit zero only after complete envelope publication; publication failure is non-zero.
- Adapter reattachment never erases authoritative result envelopes or relaunches terminal work absent explicit Step 3 resume replacement or Step 5c retry control.
- Child-side merge publication failure produces a non-zero bgjob result rather than partial success.

## Testing strategy

- Run `make test-design-step3-review`.
- Run `make test-design-step3b-tail`.
- Run `make test-design-step5c`.
- Run `make test-step3-orchestrator-fence`.
- Run `make test-design-structure`.
- Run `python3 -m pytest python/tests/bgjob/test_bgjob_adapt.py`.
- Run `make lint` and `make py-test`.

## Acceptance

- Run `make test-design-step3-review`.
- Run `make test-design-step3b-tail`.
- Run `make test-design-step5c`.
- Run `make test-step3-orchestrator-fence`.
- Run `make test-design-structure`.
- Run `python3 -m pytest python/tests/bgjob/test_bgjob_adapt.py`.
- Run `make lint` and `make py-test`.

review_status: complete
rounds_completed: 2
difficulty: HARD
diff_added: 365
diff_deleted: 400
mechanical_churn: true
oversize_override: operator
diff_lines: 765
