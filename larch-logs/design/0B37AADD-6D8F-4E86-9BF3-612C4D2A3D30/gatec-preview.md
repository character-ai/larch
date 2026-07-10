## Final Design Plan

The plan is very large. Showing the full plan body below.

## Plan

## Approach

1. Make progress-pointer activation and deactivation atomic, run-matched operations.
   - Expose `progress deactivate --repo-root … --run-id …`.
   - Use one clone-local, fd-relative, symlink-safe lock across `activate_run` replacement and `deactivate_run` compare-and-clear.
   - While holding that lock, deactivate only when `current` is a valid regular pointer naming the supplied expected run ID; absent state, mismatches, invalid IDs, and unsafe paths are silent no-ops.
   - Retain run directories and breadcrumb logs.
   - Make SessionStart capture the active run ID and call the same atomic compare-and-clear operation, so a reset that observed run A cannot unlink a newly activated run B pointer.

2. Remove the lifecycle-entry stale window without changing reviewer-routing semantics.
   - Clear the prior pointer before design or implement setup/preflight can block.
   - Create or load session state without bundled reviewer probing.
   - Resolve one effective run ID, persist it as `LARCH_RUN_ID`, and activate it before external probes.
   - Run the existing reviewer probe, persist `CODEX_`/`CURSOR_` availability KVs into session/source environment, then write the design/implement environment and evaluate degraded-tools routing.
   - Re-activate the persisted effective run ID on `--resume-plan-tail`.
   - Preserve the effective design run ID across every `source-env.sh` refresh so later lifecycle, review, timing, and bgjob paths do not fall back to `SESSION_ID`.

3. Make progress, bgjob registry, and direct liveness lookup use one run-ID contract.
   - Define or reuse one shared validator accepted by progress activation, progress deactivation, and bgjob registry paths; accepted progress IDs—including UUIDs, uppercase characters, dots, underscores, and supported lengths—must be recordable and recoverable by bgjobs.
   - Persist the effective progress run ID in design and implement session state before session-bound bgjobs can start.
   - Update bgjob start, rejoin, wait/default-resolution, and registry lookup paths to recover `LARCH_RUN_ID` from the owning tmpdir/session state before using the legacy tmpdir-hash fallback.
   - Preserve explicit `--run-id` precedence and legacy compatibility only when no session-owned effective identity exists.
   - Update every direct `registry.read_for` caller, including design Step 6 in-flight checks and token/abandoned-job recovery, to pass or resolve the effective persisted run ID instead of silently defaulting to tmpdir-hash identity.
   - Keep statusline matching canonical clone path, exact effective run ID, process liveness, and budget. A live registry row counts as active work only when its recorded run ID equals the active pointer’s run ID.

4. Preserve active foreground runs on `resume` and `compact`, while removing ended runs.
   - Keep `resume` and `compact` out of reset sources rather than clearing a foreground run merely because it has no bgjob yet.
   - Continue applying run-scoped reset only to explicit startup and clear sources, with atomic compare-and-clear protection.
   - Rely on terminal, cancellation, pause, abort, and teardown deactivation to remove ended-run pointers before a later resume.
   - Use the exact-run active-bgjob predicate for SessionStart preservation, stale marking, one-hour hiding, and finalize preservation; unrelated, malformed, legacy-unidentified, cross-clone, expired, or dead rows must not preserve or freshen an active pointer.

5. Stop cross-run breadcrumb contamination.
   - Resolve a writer’s run ID from explicit command input or persisted process/session state.
   - Route asynchronous review, CI, ship, plan-review, and timing writes through `append_breadcrumb_for_run`.
   - Do not fall back to `current` in daemon-capable or delayed telemetry paths.
   - Preserve the run ID through daemon launch, rejoin, and round wrappers so registry rows and breadcrumbs use the same owning identity.
   - Keep absent or invalid telemetry identity best-effort and fail-silent without affecting the primary operation.

6. Cover every terminal and abort exit without hiding recoverable live work.
   - Deactivate after durable pause, terminal, summary, or teardown staging succeeds.
   - If staging fails but the command is nevertheless taking a real terminal exit, preserve failure artifacts/recovery information and compare-and-clear the matching pointer after the staging attempt; retain it only when the workflow will continue or that exact run still owns live, in-budget background work.
   - Add Step 0 abort cleanup deactivation before tmpdir removal when an activated run identity is available.
   - Centralize design `SUMMARY_OUTCOME` cleanup so operator cancellation and summary exits that bypass Step 6 compare-and-clear after required staging or failed-staging handling.
   - Ensure late cleanup from old runs cannot affect newer runs.

## Files to modify/create

### UPDATED: python/larch/report/progress_file.py

- Extend `deactivate_run` to require an expected run ID for lifecycle and reset callers and compare it with `current` inside existing fd-relative, symlink-safe traversal before unlinking.
- Add a clone-local lock shared by `activate_run` and `deactivate_run`; hold it across pointer read/validation/comparison and replacement or unlink so activation cannot race a delayed deactivator.
- Add `progress_deactivate_main`.
- Define silent no-op behavior for absent state, ownership mismatch, invalid run IDs, and unsafe paths without duplicating pointer-removal logic.
- Expose or reuse a single run-ID validation contract for progress and bgjob registry consumers.
- Add or refine a shared resolver for explicit or persisted process-owned run IDs. It must prefer `LARCH_RUN_ID` and must not consult `current`.

### UPDATED: python/larch/report/statusline.py

- Keep `RESET_SESSION_SOURCES` limited to explicit startup and clear reset sources; retain `resume` and `compact` as no-op reset sources so foreground work without a bgjob remains visible.
- Capture the active run ID once with its breadcrumb path.
- Replace clone-wide bgjob detection with an active-run predicate that checks canonical clone path, exact registry run ID, process liveness, and configured budget.
- Use the captured active run ID as the expected ID for atomic SessionStart deactivation.
- Apply the same scoped predicate to stale marking and one-hour hide decisions.
- Ensure unrelated, malformed, cross-clone, legacy-unidentified, expired, or dead rows neither preserve a pointer nor suppress stale/hide behavior.

### UPDATED: python/larch/cli.py

- Register `progress deactivate`.
- Keep it out of machine-stdout command sets unless the implementation introduces and documents a machine grammar.

### UPDATED: python/larch/bgjob/registry.py

- Align registry run-ID validation and path handling with the shared progress run-ID contract.
- Make `read_for` and related default-resolution helpers recover a persisted session-owned `LARCH_RUN_ID` from the owning tmpdir/session state before falling back to the legacy tmpdir-hash identity.
- Preserve explicit run-ID input and compatibility behavior for non-session or legacy callers.
- Ensure registry reads, writes, wait/rejoin operations, and cleanup all use the same resolved identity.

### UPDATED: python/larch/bgjob/cli.py

- Make session-bound bgjob start and rejoin paths resolve the effective persisted progress identity from their owning tmpdir/session state before falling back to the legacy tmpdir-derived registry ID.
- Record the resolved effective run ID in newly written registry entries so statusline and finalization can correlate daemon liveness with `current`.
- Preserve existing registry compatibility, process-management behavior, and explicit `--run-id` precedence.
- Ensure wait/rejoin paths retain the registry run ID rather than recomputing a different default.
- Accept every run ID accepted by progress/session activation, including default UUID session IDs and supported custom IDs.

### UPDATED: python/larch/state/session_env.py

- Add `LARCH_RUN_ID` to the durable design source-environment allowlist and `WRITE_DESIGN_ENV_KEYS`.
- Add a `--run-id` input to `write-design-env`, validate it under the shared run-ID contract, and write or preserve the effective value during refreshes.
- Preserve an already persisted valid `LARCH_RUN_ID` when callers refresh `source-env.sh` without replacing it.
- Keep existing source-env security and machine-output contracts unchanged.

### UPDATED: python/larch/design/design_router.py

- Thread the effective `LARCH_RUN_ID` through design run-parameter initialization and any design-environment refresh invocation.
- Ensure resume and router-owned refreshes do not overwrite a custom effective run ID with `SESSION_ID`.
- Preserve existing invocation and recovery contracts.

### UPDATED: python/larch/design/design_step0.py

- Clear any prior active pointer at Step 0 entry before setup or preflight work.
- Split session creation from reviewer probing.
- Resolve the effective run ID from requested `--run-id` or session ID, persist it as `LARCH_RUN_ID` in parsed, persisted, and source-environment design state, and activate it before reviewer probes.
- Pin replacement ordering: session setup without reviewer check; clear prior progress; resolve, persist, and activate the effective run; run the existing reviewer probe; persist probe KVs; write design environment including `LARCH_RUN_ID`; then run degraded-tools routing.
- Preserve existing degraded-tools output, retry behavior, and failure contracts.
- Update `step0_abort_cleanup_main` and every direct Step 0 hard-abort route to deactivate the effective run before tmpdir removal after abort/terminal staging succeeds.
- When abort staging fails but the command exits terminally, preserve staged failure/recovery artifacts and still compare-and-clear after the attempt unless the workflow remains recoverable and continuing or same-run live work must preserve the pointer.
- If no run identity was ever established, leave pointer state unchanged and preserve the existing recoverable failure path.

### UPDATED: python/larch/state/bootstrap.py

- Clear the prior pointer before implement preflight and setup work.
- Create the session without the bundled reviewer probe, resolve and persist the effective implement run ID, and activate it before later reviewer work.
- Pin replacement ordering: session setup; clear; resolve/persist/activate; reviewer probe; persist probe KVs into session/source environment; write environment; degraded-tools gate and existing routing.
- On `--resume-plan-tail`, resolve `LARCH_RUN_ID` from persisted session state before falling back to compatible session identity, then re-activate it before later progress writes or bgjob joins.
- Keep activation best-effort and preserve existing bootstrap routing and failure contracts.

### UPDATED: python/larch/design/design_pause.py

- Resolve the progress run ID from persisted `LARCH_RUN_ID`/effective design state, with `SESSION_ID` only as a backward-compatible fallback.
- After publish, marker write, and pause completion succeed, deactivate that exact saved design run.
- Do not clear progress when publication, marker, or pause-save work fails and the workflow remains active or recoverable.
- If the command takes an actual terminal exit after failed pause staging, preserve failure artifacts and compare-and-clear the matching pointer after the failed attempt unless same-run live work or continuation requires preservation.
- Resolve repository root from trusted persisted design state rather than ambient cwd.

### UPDATED: python/larch/design/design_terminal.py

- Resolve the effective persisted design run ID rather than assuming `SESSION_ID`.
- Deactivate after terminal failure state has been staged successfully.
- Route every terminal design summary outcome, including operator cancellation and exits that bypass Step 6, through common compare-and-clear cleanup after required summary/terminal artifacts are durable.
- For terminal exits following failed staging, preserve failure/recovery artifacts but still perform matching cleanup after the attempt unless execution continues or exact-run live work must preserve the pointer.
- Keep failed staging visible and recoverable rather than discarding artifacts before cleanup.

### UPDATED: python/larch/design/design_step6.py

- Resolve `LARCH_RUN_ID` from persisted design state and use it for terminal Step 6 cleanup.
- Pass that resolved identity into Step 5c in-flight checks and every direct `registry.read_for` lookup so custom run IDs discover their own live bgjobs.
- Deactivate terminal Step 6 paths, including artifact-preserving outcomes, only after required final artifacts succeed.
- Do not deactivate when Step 5c work remains live or when pause-save owns the terminal transition.
- If a Step 6 path exits terminally after failed final staging and no same-run live work remains, preserve artifacts and compare-and-clear before tmpdir deletion.
- Deactivate before tmpdir deletion, using persisted repository and effective run identity.

### UPDATED: python/larch/report/_tokens.py

- Resolve the effective persisted run ID for abandoned-check, recovery, and direct registry lookup paths.
- Pass that run ID into `registry.read_for` and related result-env checks instead of silently selecting a tmpdir-hash default.
- Preserve legacy fallback only for sessions with no valid persisted effective identity.

### UPDATED: python/larch/state/finalize.py

- Deactivate the implement run during teardown and standalone cleanup through `ctx.run_id`.
- Perform deactivation before tmpdir deletion.
- Preserve the pointer only when a registry entry for that exact run ID is live and in budget under the resolved run-ID contract.
- Use atomic compare-and-clear semantics so delayed teardown from an old process cannot clear a newer run.
- For teardown paths that exit terminally after failed staging, retain recovery artifacts but clear the matching pointer unless execution will continue or matching live background work remains.

### UPDATED: python/larch/review/review_core_body.py

- Pass the review command’s explicit or resolved run ID to progress writes.
- Route reviewer dispatch, collection, aggregation, voting, and check breadcrumbs to that run’s log.
- Preserve the run ID through daemon launches so registry rows and review breadcrumbs agree with the active progress identity.

### UPDATED: python/larch/review/review_and_fix.py

- Bind progress writes and any session-bound bgjob launch/rejoin work to the run ID resolved from CLI and persisted session state.
- Ensure resumed or delayed review processes retain their original run identity rather than following `current`.

### UPDATED: python/larch/review/plan_review.py

- Resolve the design run ID from persisted `LARCH_RUN_ID` in durable design session/source state.
- Write plan-review loop breadcrumbs directly to that run rather than following `current`.
- Preserve the same identity when launching or rejoining plan-review background work.

### UPDATED: python/larch/review/plan_review_round.py

- Carry the effective design run ID through round command wrappers, background-job inputs, and explicit progress writes.
- Preserve current command and result contracts.

### UPDATED: python/larch/implement/ci_monitor.py

- Thread the owning implement run ID into local verification, CI-fix progress writes, and session-bound bgjob launches.
- Prefer existing `RunContext` or explicit `run_id` inputs over environment fallback.
- Ensure an old CI monitor cannot append to a newly activated run or register as live work for it.

### UPDATED: python/larch/implement/ship_state.py

- Make ship progress writes run-aware.
- Resolve identity from ship `RunContext` or persisted ship state and call the explicit run writer.
- Preserve the identity for any ship-related background work.
- Keep logging breadcrumbs separate from statusline progress breadcrumbs.

### UPDATED: python/larch/report/timing.py

- Make timing-derived progress marks resolve the process-owned design or implement `LARCH_RUN_ID`.
- Continue recording timing data when progress identity is absent or invalid.
- Do not use `current` as a fallback for timing writers that may outlive their run.

### UPDATED: python/tests/report/test_progress_statusline.py

- Cover the new deactivate CLI, shared run-ID validation, and atomic compare-and-clear behavior.
- Add a deterministic interleaving test that pauses deactivation after observing run A, activates run B, then verifies B remains active after A cleanup resumes.
- Verify a stale old-run deactivation and a SessionStart reset that captured run A cannot clear a newer run B pointer.
- Retain `resume` and `compact` preservation expectations for active foreground runs without matching bgjobs.
- Test startup and clear reset behavior with matching active-run bgjobs versus unrelated same-clone bgjobs.
- Test live, expired, dead, malformed, cross-clone, legacy-unidentified, and exact-run registry entries.
- Verify only matching live, in-budget work suppresses stale marking and hiding.
- Cover statusline correlation where the active progress ID is a UUID/custom ID and the bgjob was started from its session tmpdir, proving the registry stores the persisted effective run ID rather than a tmpdir-hash default.
- Reproduce an old-run explicit writer after a new run activates and assert each log remains isolated.

### UPDATED: python/tests/bgjob/test_cli.py

- Cover start and rejoin/default-resolution paths that read persisted session `LARCH_RUN_ID`.
- Verify explicit `--run-id` wins, session-bound jobs record the effective progress ID, and non-session jobs retain the compatible fallback identity.
- Verify registry identity remains stable across start, wait, and rejoin operations.
- Cover IDs accepted by progress but previously rejected by registry validation, including default UUIDs and supported uppercase, dot, underscore, and custom-ID forms.

### UPDATED: python/tests/bgjob/test_registry.py

- Cover shared run-ID validation, persisted session-ID lookup, and legacy tmpdir-hash fallback.
- Verify `read_for` resolves persisted `LARCH_RUN_ID` by default for session-owned work.
- Verify explicit IDs override persisted values and malformed persisted state falls back only where compatibility requires it.

### UPDATED: python/tests/design/test_design_lifecycle.py

- Assert Step 0 clears stale progress before setup, persists and activates the effective run before reviewer probing, and keeps degraded-tool routing intact.
- Assert probe KVs are persisted before design-env writing and degraded-tools gating.
- Assert `source-env.sh` and refreshed design environment retain a custom `LARCH_RUN_ID` distinct from `SESSION_ID`.
- Cover design router and resume refreshes so they cannot overwrite the effective run ID.
- Cover a custom `--run-id` through Step 0, terminal failure, Step 6 success, preserved terminal state, and lifecycle cleanup.
- Cover Step 0 abort cleanup deactivation before tmpdir deletion.
- Cover terminal exit after failed abort/terminal staging, asserting preserved artifacts plus matching pointer cleanup unless the workflow continues.
- Cover all terminal summary and operator-cancellation routes that bypass Step 6.
- Verify lifecycle cleanup cannot clear a replacement run and pause ownership prevents premature deactivation.
- Cover custom run ID Step 5c live-work detection, proving direct registry lookup preserves the pointer and tmpdir while matching work remains.

### UPDATED: python/tests/design/test_design_pause.py

- Assert successful pause-save deactivates the persisted effective run only after all durable pause steps succeed.
- Assert publication or marker failures retain the active pointer while the run remains active or recoverable.
- Cover terminal failed-pause exits, asserting preserved failure artifacts and matching cleanup when no continuation remains.
- Cover a custom run ID and a newer-run pointer replacing the paused run before cleanup.

### UPDATED: python/tests/state/test_bootstrap.py

- Assert fresh implement bootstrap clears stale state, persists and activates the effective run before reviewer probes, and writes probe KVs before environment/degraded routing.
- Assert `--resume-plan-tail` restores the persisted `LARCH_RUN_ID` as active.
- Preserve probe retry, session-env, and routing expectations.

### UPDATED: python/tests/state/test_finalize.py

- Cover deactivation for successful teardown, bail or stall teardown, and standalone cleanup.
- Cover terminal teardown after failed staging, asserting recovery artifacts survive while matching progress clears unless continued or exact-run live work preserves it.
- Verify same-run live background work is preserved only when the registry row carries the exact effective progress run ID.
- Verify unrelated same-clone jobs do not preserve the pointer.
- Verify compare-and-clear protects a newer run and cleanup still completes.

### UPDATED: python/tests/report/test_tokens.py

- Cover custom persisted design run IDs in abandoned-check recovery and direct registry lookup.
- Verify live jobs keyed by a custom effective run ID are found rather than treated as absent through a tmpdir-hash fallback.

### UPDATED: python/tests/state/test_session_env.py

- Cover `write-design-env --run-id`, the `LARCH_RUN_ID` allowlist, validation, durable source-environment serialization, and refresh preservation.
- Verify a custom effective run ID survives later environment refreshes and is not replaced with `SESSION_ID`.

### UPDATED: python/tests/review/test_plan_review.py

- Assert plan-review breadcrumbs and session-bound background work target the persisted custom design run after `current` changes.

### UPDATED: python/tests/review/test_plan_review_round.py

- Update progress and bgjob test doubles for explicit run-aware calls.
- Assert round subprocess breadcrumbs and registry identity retain the owning run ID.

### UPDATED: python/tests/review/test_review_and_fix.py

- Assert delayed review progress and bgjob work use the review’s resolved run ID rather than the active pointer.

### UPDATED: python/tests/implement/test_ci_monitor.py

- Cover explicit run propagation through local verification, CI-fix, and relevant bgjob paths.
- Assert an old monitor cannot refresh a newer run’s log or preserve its pointer.

### UPDATED: python/tests/implement/test_ship_state.py

- Cover run-aware ship progress identity, background-work identity where applicable, and missing-identity fail-silent behavior.

### UPDATED: python/tests/report/test_timing.py

- Assert timing marks write to the process-owned effective run ID.
- Verify timing ledger success remains independent from progress-write success.

### UPDATED: docs/progress-reporting.md

- Document silent end-of-run and cancellation clearing with atomic run-matched ownership.
- Document clone-local activation/deactivation serialization and SessionStart compare-and-clear protection.
- Document Step 0 clear, effective-run persistence in source environment, early activation, and pinned reviewer-probe ordering.
- Document that startup and clear reset stale pointers unless the active run owns live, in-budget, run-matched bgjob work.
- State that `resume` and `compact` do not reset an active pointer, protecting foreground runs that have not launched a bgjob.
- Explain that session-bound bgjobs record the persisted effective run ID, direct registry readers recover it, and asynchronous writers use their own run IDs rather than following a later pointer.
- Retain the one-active-run-per-clone user contract.

### UPDATED: SECURITY.md

- Document run-matched pointer deletion, atomic activation/deactivation, SessionStart compare-and-clear, and explicit run-scoped daemon writes as integrity protections.
- Note that progress pointer, log, and registry operations retain symlink and invalid-state refusal.
- Describe protection against an old process clearing, preserving, or contaminating a newer run.

## Edge cases

- `current` is absent, malformed, symlinked, non-regular, or changes between read and removal.
- A deactivator reads run A while run B attempts activation; clone-local serialization must leave B active.
- A SessionStart reset captures run A while run B activates before its deactivate call.
- A new run activates while an old run is entering teardown, terminal summary, pause-save, or Step 0 abort cleanup.
- A registry row matches the clone but not the active run.
- A session-bound registry row must use a persisted UUID/custom `LARCH_RUN_ID`, not a tmpdir-hash fallback.
- Valid progress/design IDs contain uppercase characters, dots, underscores, or supported lengths that registry handling previously rejected.
- A matching row is alive but over budget, or the daemon is alive after its child exits.
- A registry row lacks valid run identity because it predates the new contract or has malformed session state.
- Direct `registry.read_for` paths run with a custom persisted effective ID and must still discover Step 5c or abandoned recovery work.
- SessionStart receives malformed JSON, no source, no repository, or statusline opt-out.
- `resume` or `compact` occurs during foreground Step 0 before the first bgjob is launched.
- Step 0 fails before a session ID or effective run ID exists.
- A custom design run ID differs from the session ID and survives source-environment refreshes.
- `--resume-plan-tail` has missing or invalid persisted run identity.
- Reviewer probing fails or returns degraded availability after early activation.
- Pause publication or marker creation fails.
- Terminal or abort staging fails but the workflow exits rather than continuing.
- Design Step 6 preserves artifacts but has no live work.
- An operator cancellation reaches a terminal summary path without Step 6.
- Progress identity is missing in a telemetry-only writer; the primary operation must continue.
- A daemon writes after its run has been deactivated. Its old log may receive the row, but the row must not render unless that run is active again.

## Failure modes

- Do not clear a pointer merely because a lifecycle process believes it owns the clone; require an exact run-ID match under the shared lock.
- Do not let a deactivator or SessionStart reset delete a pointer that changed after it was inspected.
- Do not treat unrelated same-clone bgjobs as evidence that the active run is alive.
- Do not compare active progress UUIDs/custom IDs with legacy tmpdir-hash registry IDs for session-bound jobs; make registry identity and direct registry lookups follow persisted effective run identity.
- Do not reject IDs in bgjob paths that the progress lifecycle accepts.
- Do not clear active foreground work on `resume` or `compact` solely because no bgjob has started.
- Do not hide the active run when its own live, in-budget, run-matched work remains.
- Do not make progress telemetry failures fail review, CI, ship, timing, pause publication, terminal cleanup, or bgjob lifecycle operations.
- Do not delete run logs during deactivation.
- Do not weaken existing fd-relative, lock, and symlink protections.
- Do not reintroduce reviewer probe results after activation in an order that changes degraded-tools routing.
- Do not let lifecycle deactivation happen before required pause, abort, summary, or terminal artifacts are attempted and durable artifacts are preserved.
- Do not leave a progress pointer active after a real terminal exit solely because artifact staging failed; retain it only for continuation or matching live work.
- Do not let custom design run IDs fall back silently to `SESSION_ID` when persisted `LARCH_RUN_ID` is available.

## Testing strategy

- Run focused Python tests for every changed module:
  - `python/tests/report/test_progress_statusline.py`
  - `python/tests/bgjob/test_cli.py`
  - `python/tests/bgjob/test_registry.py`
  - `python/tests/design/test_design_lifecycle.py`
  - `python/tests/design/test_design_pause.py`
  - `python/tests/state/test_bootstrap.py`
  - `python/tests/state/test_finalize.py`
  - `python/tests/state/test_session_env.py`
  - `python/tests/report/test_tokens.py`
  - the listed review, CI, ship, and timing tests.
- Run the SessionStart statusline harness to preserve hook ordering and silent stdout behavior.
- Run CLI registry tests for the new `progress deactivate` verb, atomic activation/deactivation behavior, shared validator, and bgjob identity contract.
- Run Python lint and type checks only for changed Python files.
- Run the existing design structure and implement Step 18 harnesses if lifecycle call placement changes their pinned behavior.
- Repeat the issue reproduction with distinct effective run IDs:
  1. Finish or deactivate run A and confirm no status renders.
  2. Enter run B Step 0 and confirm run A never renders while setup and reviewer probing run.
  3. Start a session-bound run-B bgjob and confirm its registry row records run B’s persisted UUID/custom run ID rather than the tmpdir hash.
  4. Keep an unrelated run-A bgjob live and confirm startup or clear resets run A.
  5. Keep run B’s own live, in-budget bgjob and confirm SessionStart preserves B.
  6. Resume or compact run B before its first bgjob and confirm B remains visible.
  7. Write from an old run-A process after B activates and confirm only A’s log changes.
  8. Abort Step 0 and exercise each design cancellation summary route, including failed staging terminal exits, confirming matching cleanup occurs before tmpdir cleanup unless work continues.
  9. Deterministically interleave A deactivation with B activation and confirm the locked compare-and-clear never removes B.
  10. Refresh design source environment and launch/rejoin Step 5c or plan-review work using a custom run ID distinct from `SESSION_ID`; confirm every writer, registry lookup, and cleanup path retains that exact ID.

difficulty: HARD
diff_added: 980
diff_deleted: 255
mechanical_churn: false
oversize_override: operator
diff_lines: 1235
