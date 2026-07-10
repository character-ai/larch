### FINDING_1: Correlate bgjob liveness with the active progress run
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Run Lifecycle Integrity
- **Severity**: major
- **Concern**: The planned `entry.run_id == active_run_id` match is incompatible with production launch behavior: progress activation uses `SESSION_ID` or a requested `--run-id`, while bgjob registry rows default to a hash of the temporary directory because launchers omit `--run-id`. Consequently, live Step 3/5/8 and related daemons are not recognized as belonging to the active run, so reset, stale/hide suppression, and finalize preservation behave incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Revise the plan to make bgjob registry identity match progress identity. Either update bgjob start/wait defaults to resolve the persisted design or implement run id from the tmpdir session state, or update every design and implement bgjob launcher/rejoin path to pass --run-id explicitly. Add tests that current larch run ids, not tmpdir-hash defaults, are used for active-run liveness matching.
  - From Cursor-Innovation: Match live rows to the active pointer by registry TMPDIR identity instead of RUN_ID alone (e.g. read tmpdir/session-id or .larch-keepalive SESSION_ID and compare to current), or forward the progress run id through every bgjob start/wait pair; document the chosen contract in statusline.py and test_progress_statusline.py with hash-based registry rows plus uuid progress ids.
  - From Cursor-Pragmatic: Define an explicit correlation key: persist the session tmpdir at activate and treat registry rows with the same entry.tmpdir as belonging to the active run, or pass the progress run id into every bgjob start after normalizing to bgjob slug rules; update statusline.py, finalize.py, and tests to use that contract instead of raw RUN_ID equality
  - From Cursor-Requirements: Correlate live registry rows to the active progress run by clone plus session tmpdir identity (e.g. entry.tmpdir/session-id or run-id.txt equals active run id), or pass the progress run id into every bgjob start --run-id; update tests accordingly
  - From Cursor-dyn-Run Lifecycle Integrity: Resolve progress run_id from entry.tmpdir session state (session-id source-env LARCH_RUN_ID) before comparing to current or pass the activated progress run_id into every bgjob start wrapper.


### FINDING_2: Deactivate progress on Step 0 abort cleanup
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: minor
- **Concern**: The Step 0 abort-cleanup path can delete the temporary directory without clearing the activated progress pointer. An operator abort after activation can therefore leave the aborted run displayed until a later SessionStart or another lifecycle action.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add run-matched deactivation to this abort path before temporary-directory cleanup, using the persisted run ID and repository root when available. If no run identity exists, stage terminal failure state through the existing safe path or explicitly document why no pointer can be cleared.
  - From Cursor-Innovation: Add step0_abort_cleanup_main to the design_step0.py plan bullets: after successful abort staging, call progress deactivate with the activated RUN_ID/SESSION_ID and REPO_ROOT before cleanup-tmpdir, using compare-and-clear semantics; extend test_design_lifecycle.py for Step 0 abort.
  - From Cursor-Pragmatic: Add run-matched progress deactivate to step0_abort_cleanup_main (and any other Step 0 hard-abort exits that skip design_terminal staging), using REPO_ROOT plus SESSION_ID or --run-id from parsed Step 0 state, after successful cleanup and before exit


### FINDING_3: Preserve reviewer-probe ordering and outputs
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: major
- **Concern**: Removing `--check-reviewers` from session setup without explicitly pinning the replacement probe and persistence sequence can leave `CODEX_`/`CURSOR_` availability values empty or stale before degraded-tools routing, changing behavior that the plan intends to preserve.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: After early progress activate, invoke the existing python/cli.py agent check-reviewers surface (or an extracted helper returning the same KVs) and persist results before write-design-env/write-env and degraded-tools-gate; pin this in both file sections and keep test_bootstrap.py / test_design_lifecycle.py degraded-routing assertions.
  - From Cursor-Requirements: Pin order: session setup without probe, progress clear+activate, agent check-reviewers probe, persist presence into session env/source-env, then degraded-tools-gate; mirror the same contract in design_step0.py before write-design-env and gate


### FINDING_4: Persist and consistently resolve custom design run IDs
- **Reviewer(s)**: Codex-Innovation, Cursor-Requirements, Codex-Pragmatic, Codex-Requirements, Cursor-dyn-Run Lifecycle Integrity
- **Severity**: major
- **Concern**: A custom design `--run-id` can be activated without being persisted or reused consistently by pause, plan-review, terminal, timing, and Step 6 lifecycle paths. Those paths may fall back to `SESSION_ID`, causing writes and compare-and-clear deactivation to target a different run and leaving the custom pointer active.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Carry the effective RUN_ID through persisted design state and use it for Step 6 deactivation, or explicitly guarantee and enforce that SESSION_ID and the activated run ID are identical
  - From Codex-Innovation: Persist the effective run ID in source-env and every staged design state consumed by pause, terminal, review, and timing paths, then require all design lifecycle operations to resolve that value rather than assuming SESSION_ID is the run ID
  - From Cursor-Requirements: Resolve the progress run id the same way as activation (parsed run_id from .design-step0-parsed.env, else session-id file, else SESSION_ID) in design_pause.py, design_terminal.py, and design_step6.py; add a lifecycle test with distinct --run-id
  - From Codex-Pragmatic: Persist the selected active run ID as `RUN_ID` or `LARCH_RUN_ID` when writing design state, then require all planned design writers and deactivation paths to read that field, using `SESSION_ID` only as a backward-compatible fallback.
  - From Codex-Requirements: Persist the resolved design run ID through `session write-design-env` as `LARCH_RUN_ID`; require design writers and lifecycle deactivation to prefer it and fall back to `SESSION_ID`; add custom-run-ID coverage to the mandated design lifecycle and plan-review tests
  - From Cursor-dyn-Run Lifecycle Integrity: In design_pause resolve RUN_ID from the same persisted source as activation (run-params run_id source-env LARCH_RUN_ID or activated id) not SESSION_ID alone.


### FINDING_5: Cover all terminal and cancellation exits with deactivation
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: Several operator-cancel and other early `/design` summary exits bypass Step 6 and terminal staging, leaving `current` set after the run has ended.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Wire progress deactivate on every terminal /design SUMMARY_OUTCOME exit (centralize in step_final_summary_core or design_terminal after summary staging) with compare-and-clear; extend test_design_lifecycle cancel-route coverage


### FINDING_7: Make SessionStart reset compare-and-clear run-matched
- **Reviewer(s)**: Codex-dyn-Run Lifecycle Integrity
- **Severity**: major
- **Concern**: SessionStart reset can inspect run A, then clear the pointer after run B activates, allowing the unscoped clear to delete run B's pointer and hide legitimate live work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Run Lifecycle Integrity: Pass the captured active run ID to `deactivate_run` and make a mismatch a no-op.


### FINDING_8:
- **Reviewer(s)**: Cursor-dyn-Run Lifecycle Integrity
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/statusline.py:24-25 python/larch/report/statusline.py:129-139 python/larch/report/progress_file.py:127-129 python/tests/report/test_progress_statusline.py:901-912
- **Concern**: [SCOPE-REDUCTION] resume and compact reset with bgjob-only preservation clears foreground runs. Scenario: Plan adds resume and compact to RESET_SESSION_SOURCES and only blocks reset when a matching live in-budget bgjob exists. Most /design and /implement steps before the first bgjob write through append_breadcrumb which no-ops without current. Claude --continue or compact mid-run clears current and silences the statusline for the rest of the run. End-of-run deactivate already fixes finished-run resume stale status without resume reset.
- **Proposed resolution**: Keep resume and compact as no-op reset sources or gate reset on an active in-progress run signal (persisted tmpdir still live or fresh breadcrumb mtime) not only bgjob liveness.


### FINDING_1: Persist the effective design run ID through session environment refreshes
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: Custom or otherwise effective design run IDs are activated but are not durably written through `source-env.sh`. Later pause, terminal, plan-review, timing, resume, and bgjob paths can fall back to `SESSION_ID`, causing run-scoped writes and compare-and-clear operations to target the wrong run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add LARCH_RUN_ID to WRITE_DESIGN_ENV_KEYS, accept --run-id on write-design-env, and pass the effective run from design_step0.py, design_router.py init_runparams, and resume refresh. List design_router.py in firm file changes or fold those call sites into the design_step0 contract explicitly.
  - From Cursor-Innovation: Add `LARCH_RUN_ID` to `WRITE_DESIGN_ENV_KEYS`, accept `--run-id` on `write-design-env`, and pass the effective id from Step 0 after resolve/persist; extend lifecycle tests to assert `source-env.sh` carries the custom id.
  - From Cursor-Pragmatic: Add session write-design-env support for LARCH_RUN_ID (allowlist plus --run-id flag) and list python/larch/state/session_env.py in firm plan files; pass the effective run ID from design Step 0 and resume refresh
  - From Cursor-Pragmatic: Thread the effective LARCH_RUN_ID through design_router init_runparams and design_step0 resume write-design-env refresh, or preserve the prior LARCH_RUN_ID when refreshing source-env
  - From Cursor-Requirements: A named plan step must persist LARCH_RUN_ID into durable design session state before bgjobs start, for example extend write-design-env/SOURCE_ENV_ALLOW or write run-id.txt and teach the shared resolver and bgjob lookup to read it. Cover with the planned custom --run-id lifecycle test.


### FINDING_2: Align bgjob registry run-ID validation with the progress run-ID contract
- **Reviewer(s)**: Cursor-Arch, Codex-Arch
- **Severity**: major
- **Concern**: Valid progress/design run IDs can contain uppercase characters, dots, underscores, or be longer than the bgjob registry’s slug limit. Session-bound bgjob startup may therefore reject valid effective run IDs, preventing registry writes and breaking wait, liveness, and statusline correlation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Align registry RUN_ID validation with progress validate_run_id (or normalize once in the shared resolver) and add a test that a default UUID SESSION_ID survives bgjob start, wait, and statusline correlation.
  - From Codex-Arch: Use one shared run-ID validator for progress and bgjob registry paths, or explicitly constrain and validate custom IDs before activation. Update bgjob start, wait, registry-path handling, and tests so every accepted effective run ID can be recorded and recovered consistently.


### FINDING_3: Propagate the effective run ID to all direct registry lookups
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: Direct `registry.read_for` callers such as Step 6 in-flight detection and abandoned-check recovery still default to the tmpdir-hash identity. Once session-bound bgjobs are keyed by the persisted effective run ID, these callers can miss live jobs and deactivate progress or delete tmpdirs while work remains active.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Either teach registry.read_for to resolve persisted LARCH_RUN_ID from the owning tmpdir/session state before the tmpdir-hash fallback, or explicitly update design_step6.py and _tokens.py (and any other direct read_for callers) to pass the resolved run id; add regression coverage for custom run IDs.
  - From Cursor-Innovation: Pass the resolved `LARCH_RUN_ID` into `registry.read_for` (and any related result-env checks) in `_step6_in_flight` before Step 6 cleanup/deactivation decisions.
  - From Cursor-Pragmatic: Resolve LARCH_RUN_ID from persisted design state and pass it to registry.read_for in _step6_in_flight; add a lifecycle test for custom run IDs with live Step 5c
  - From Codex-Pragmatic: Thread the persisted effective run ID into every direct `registry.read_for` call, including design Step 6 and token recovery, or change the shared default resolver in `python/larch/bgjob/registry.py:138-142`. List and test those affected paths.
  - From Cursor-Requirements: Pass the persisted effective design run ID into registry.read_for for Step 5c in-flight checks, and add a lifecycle test with a custom run ID distinct from SESSION_ID.


### FINDING_7: Serialize activation and compare-and-clear
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: Compare-and-clear is still racy if activation can replace `current` between the deactivator’s read and unlink. A deactivator handling run A can then unlink newly activated run B, preserving the SessionStart or delayed-cleanup race.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Use one clone-local lock across `activate_run` pointer replacement and `deactivate_run` comparison plus unlink. Add the planned deterministic interleaving test that pauses deactivation after reading A, activates B, then verifies B remains.


### FINDING_8: Clear active progress on all terminal and abort exits
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: Terminal cleanup clears progress only when abort or terminal artifact staging succeeds. If staging fails and the command still exits, the ended run remains active and can reappear as stale status on a later Claude resume.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Preserve failed artifacts and recovery state, but compare-and-clear the run pointer before every actual terminal exit after the staging attempt. Retain the pointer only when the workflow will continue or same-run background work is still live.


