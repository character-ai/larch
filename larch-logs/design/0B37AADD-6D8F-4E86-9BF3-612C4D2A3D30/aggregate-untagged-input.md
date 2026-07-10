### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/state/session_env.py:61-73
- **Concern**: Persist effective design LARCH_RUN_ID in source-env.sh. Scenario: The plan requires every design lifecycle path to resolve the persisted effective run ID, but write-design-env only allowlists SESSION_ID and has no --run-id writer. init_runparams and resume refresh in design_router.py also call write-design-env without a run id. Custom --run-id and pause/terminal/Step 6 compare-and-clear can still target SESSION_ID while current points elsewhere.
- **Proposed resolution**: Add LARCH_RUN_ID to WRITE_DESIGN_ENV_KEYS, accept --run-id on write-design-env, and pass the effective run from design_step0.py, design_router.py init_runparams, and resume refresh. List design_router.py in firm file changes or fold those call sites into the design_step0 contract explicitly.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/bgjob/model.py:66-73
- **Concern**: Bgjob registry run-id charset must match progress run IDs. Scenario: The plan makes session-bound registry rows use the persisted progress run ID, but bgjob validate_slug only allows lowercase [a-z0-9-] while progress validate_run_id and default SESSION_ID values allow uppercase, dot, and underscore. Typical uuidgen session IDs fail registry writes, so bgjob start/wait cannot record the active run and statusline correlation regresses to the tmpdir-hash mismatch the plan removes.
- **Proposed resolution**: Align registry RUN_ID validation with progress validate_run_id (or normalize once in the shared resolver) and add a test that a default UUID SESSION_ID survives bgjob start, wait, and statusline correlation.

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/bgjob/registry.py:138-142
- **Concern**: Direct registry.read_for callers still default to tmpdir-hash IDs. Scenario: Only bgjob/cli.py is listed for session run-id resolution. design_step6.py _step6_in_flight and python/larch/state/_tokens.py abandoned-checks detection call registry.read_for without a run id, so after registry rows move to LARCH_RUN_ID they will miss live Step 5c/checks jobs, skip in-flight guards, and may deactivate or delete tmpdirs while work is still running.
- **Proposed resolution**: Either teach registry.read_for to resolve persisted LARCH_RUN_ID from the owning tmpdir/session state before the tmpdir-hash fallback, or explicitly update design_step6.py and _tokens.py (and any other direct read_for callers) to pass the resolved run id; add regression coverage for custom run IDs.

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/state/finalize.py:744-748
- **Concern**: Probe live bgjob preservation before killing session background work. Scenario: The plan says finalize should preserve the active pointer when an exact-run registry row is live, but teardown already calls kill_session_background_processes before tmpdir removal. If liveness is checked only after that kill, the preserve branch always sees dead work and clears current during races where a same-run bgjob is still live.
- **Proposed resolution**: Run the exact-run, in-budget registry preservation probe before kill_session_background_processes, skip compare-and-clear deactivation when preservation applies, then kill and delete tmpdir; cover this ordering in test_finalize.py.

### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/bgjob/cli.py:19-26; python/larch/bgjob/model.py:66-79
- **Concern**: Align bgjob run-ID validation with the progress and design run-ID contract.. Scenario: The plan permits persisted custom design IDs and progress IDs accepted by `validate_run_id`, including uppercase characters and up to 128 characters. Session-bound bgjob startup still routes the resolved ID through `model.validate_slug`, which rejects uppercase IDs and IDs longer than 97 characters. A valid custom run can therefore fail to start its background job, and subsequent wait or liveness correlation cannot complete.
- **Proposed resolution**: Use one shared run-ID validator for progress and bgjob registry paths, or explicitly constrain and validate custom IDs before activation. Update bgjob start, wait, registry-path handling, and tests so every accepted effective run ID can be recorded and recovered consistently.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/design_step0.py:162-212, python/larch/state/bootstrap.py:463-508
- **Concern**: [ALREADY_ADDRESSED] Step 0 pinned ordering still clears progress after session setup. Scenario: Approach §2 requires clearing the stale pointer before setup or preflight can block, but the pinned design/implement order is setup → clear → activate → probe. Session setup can still run while `current` names the previous run, so the job-start stale breadcrumb from RC2 survives through setup.
- **Proposed resolution**: Move unconditional stale-pointer removal to the first Step 0 action (before `session setup`), then keep resolve/persist/activate immediately after setup returns a session id and before reviewer probing.

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/progress_file.py:405-420, python/larch/design/design_step0.py
- **Concern**: Step 0 entry clear must remove the active pointer, not compare against the new run id. Scenario: The plan makes `deactivate_run` compare-and-clear on an expected run id. At Step 0 entry the new effective run is not active yet, so `deactivate_run(repo, new_run_id)` no-ops while the previous run stays current and the statusline stays stale.
- **Proposed resolution**: Define entry stale-clear separately: read `current` (or unconditional unlink) and deactivate that id, or add a dedicated clear-active helper; reserve compare-and-clear only for lifecycle/SessionStart/finalize callers that own a specific run id.

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/state/session_env.py:997-1074, python/larch/design/design_step0.py:192-197
- **Concern**: Custom design run ids are activated but not written into `source-env.sh`. Scenario: `write-design-env` allowlist omits `LARCH_RUN_ID` and has no `--run-id`, while pause/terminal/Step 6/bgjob resolution are planned to read persisted `LARCH_RUN_ID`. A custom `--run-id` activates progress but later paths fall back to `SESSION_ID`, so deactivation and run-scoped writes target the wrong id and the custom pointer can remain active (accepted FINDING_4 gap).
- **Proposed resolution**: Add `LARCH_RUN_ID` to `WRITE_DESIGN_ENV_KEYS`, accept `--run-id` on `write-design-env`, and pass the effective id from Step 0 after resolve/persist; extend lifecycle tests to assert `source-env.sh` carries the custom id.

### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/design_step6.py:57-73, python/larch/bgjob/registry.py:138-141
- **Concern**: Step 6 Step 5c in-flight guard still defaults registry lookup to the tmpdir hash. Scenario: After session-bound bgjobs record the persisted effective run id, `_step6_in_flight` still calls `registry.read_for` without `run_id`, so it probes the legacy tmpdir-hash row. Step 6 can treat a live Step 5c job as absent and delete the tmpdir (or deactivate) while publish is still running.
- **Proposed resolution**: Pass the resolved `LARCH_RUN_ID` into `registry.read_for` (and any related result-env checks) in `_step6_in_flight` before Step 6 cleanup/deactivation decisions.

### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/state/session_env.py:61-73
- **Concern**: Plan omits durable design LARCH_RUN_ID writer surface. Scenario: Custom --run-id is activated in Step 0 but WRITE_DESIGN_ENV_KEYS and write-design-env do not emit LARCH_RUN_ID; source-env rehydration leaves ctx.larch_run_id empty so pause, terminal, plan-review, timing, and bgjob identity resolution fall back to SESSION_ID and compare-and-clear targets the wrong run
- **Proposed resolution**: Add session write-design-env support for LARCH_RUN_ID (allowlist plus --run-id flag) and list python/larch/state/session_env.py in firm plan files; pass the effective run ID from design Step 0 and resume refresh

### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/design_router.py:203-221
- **Concern**: Init-runparams source-env refresh can erase persisted run identity. Scenario: After Step 0a activation, init-runparams rewrites source-env.sh without the effective run ID; later readers lose the custom LARCH_RUN_ID before pause, terminal, or bgjob paths run
- **Proposed resolution**: Thread the effective LARCH_RUN_ID through design_router init_runparams and design_step0 resume write-design-env refresh, or preserve the prior LARCH_RUN_ID when refreshing source-env

### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/design_step6.py:57-73
- **Concern**: Step 6 in-flight detection still uses tmpdir-hash registry identity. Scenario: Once session-bound bgjobs record persisted UUID/custom LARCH_RUN_ID, registry.read_for without that run_id misses live design-step5c work and Step 6 can deactivate and delete tmpdir while Step 5c is still running
- **Proposed resolution**: Resolve LARCH_RUN_ID from persisted design state and pass it to registry.read_for in _step6_in_flight; add a lifecycle test for custom run IDs with live Step 5c

### FINDING_14:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/report/progress_file.py:348-357,405-420
- **Concern**: Prior accepted compare-and-clear fix remains incomplete because the plan does not serialize activation with deactivation. Scenario: The deactivator can read run A, then run B can atomically replace `current`, then the deactivator can unlink run B. This preserves the SessionStart and delayed-cleanup race that the plan claims to close.
- **Proposed resolution**: Use one clone-local lock across `activate_run` pointer replacement and `deactivate_run` comparison plus unlink. Add the planned deterministic interleaving test that pauses deactivation after reading A, activates B, then verifies B remains.

### FINDING_15:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/design_step6.py:57-73
- **Concern**: The new persisted bgjob registry identity is not propagated to direct `registry.read_for` callers. Scenario: After bgjob start keys the Step 5c entry by `LARCH_RUN_ID`, `_step6_in_flight` still looks under the legacy tmpdir-derived ID. It can miss a live Step 5c job and proceed into Step 6 cleanup. `python/larch/state/_tokens.py:206-224` has the same lookup mismatch for abandoned checks jobs.
- **Proposed resolution**: Thread the persisted effective run ID into every direct `registry.read_for` call, including design Step 6 and token recovery, or change the shared default resolver in `python/larch/bgjob/registry.py:138-142`. List and test those affected paths.

### FINDING_16:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/design_step6.py:57-73
- **Concern**: Step 6 in-flight detection still uses default tmpdir-hash registry lookup. Scenario: After bgjob rows store the persisted LARCH_RUN_ID, registry.read_for(tmpdir=..., step=...) without run_id resolves a different registry path than the live Step 5c job. _step6_in_flight returns false while design-step5c is still running, so Step 6 can deactivate progress and delete the tmpdir early despite the plan rule to keep the pointer while Step 5c work remains live.
- **Proposed resolution**: Pass the persisted effective design run ID into registry.read_for for Step 5c in-flight checks, and add a lifecycle test with a custom run ID distinct from SESSION_ID.

### FINDING_18:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/state/session_env.py:61-73
- **Concern**: Custom design run ID persistence is not pinned to a readable session surface. Scenario: FINDING_4 fix is incomplete on the write path: design activates --run-id and plan-review/pause/terminal/bgjob paths must read LARCH_RUN_ID, but write-design-env only allows WRITE_DESIGN_ENV_KEYS and that set omits LARCH_RUN_ID. source-env.sh therefore cannot carry the activated custom ID unless another listed step adds an explicit writer/resolver contract.
- **Proposed resolution**: A named plan step must persist LARCH_RUN_ID into durable design session state before bgjobs start, for example extend write-design-env/SOURCE_ENV_ALLOW or write run-id.txt and teach the shared resolver and bgjob lookup to read it. Cover with the planned custom --run-id lifecycle test.

### FINDING_19:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/design_step0.py:159-212; python/larch/state/bootstrap.py:463-503
- **Concern**: The pinned Step 0 ordering contradicts the required early clear. Both file sections say session setup runs before clearing prior progress, despite adjacent requirements that clearing happen before setup or preflight.. Scenario: If session setup or its probes block or fail, the previous run remains visible during the same stale window this feature must remove. The implementer may follow the explicitly pinned ordering and preserve the reported bug.
- **Proposed resolution**: Pin one unambiguous order for both flows: capture and compare-clear the prior pointer first, then create or load session state, persist and activate the effective run ID, probe reviewers, persist probe results, write the environment, and route degraded tools.

### FINDING_20:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/design_step0.py:706-760; python/larch/design/design_terminal.py:720-815
- **Concern**: The prior terminal-exit fix remains incomplete because the plan clears progress only when abort or terminal artifact staging succeeds and explicitly retains the pointer when staging fails.. Scenario: A terminal summary or abort-staging failure can end the command while leaving its run active. A later Claude resume then renders that ended run as current, recreating the stale-status symptom on a required bail path.
- **Proposed resolution**: Preserve failed artifacts and recovery state, but compare-and-clear the run pointer before every actual terminal exit after the staging attempt. Retain the pointer only when the workflow will continue or same-run background work is still live.
