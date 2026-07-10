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


