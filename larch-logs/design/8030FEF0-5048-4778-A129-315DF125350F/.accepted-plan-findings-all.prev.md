### FINDING_1: Step 7a orchestrator deleted without Python replacement
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Pragmatic, Codex-Requirements, Cursor-dyn-finalize-runlog-auditor, Codex-dyn-finalize-runlog-auditor
- **Severity**: important
- **Concern**: The plan retires `step-7a.sh` (and its harness) while only porting `generate-code-flow-diagram.sh` into `pr_body.py`. Step 7a is a consolidated orchestrator: small/non-runtime classifier, diagram generation, `larch:diagrams` upsert, embedded `7a.r` rebase relay, pre-ship `run-log` flush, `flush-execution-issues`, transcript capture, and the terminal KV tail (`DIAGRAM_STATUS`, `DIAGRAM_PATH`, `COMMENT_URL`, `LOG_FLUSH_STATUS`, `STEP_7A_BAIL_REASON`, `REBASE_OUTCOME`). `SKILL.md` still invokes `skills/implement/scripts/step-7a.sh`. Deleting the script without a single replacement entrypoint breaks `/implement` Step 7a before Step 8 and leaves no pytest home for `test-step-7a.sh` coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit port: either NEW python/step_7a.py (or implement-step7a CLI) with the full KV contract, or UPDATED step-7a.sh that delegates to python/cli.py subcommands; update SKILL.md Step 7a fence, rebase-checkpoint-routing.md, and add matching pytest before deletion
  - From Codex-Arch: Add a Python Step 7a entrypoint and cli.py verb that preserves the current wrapper contract before deleting step-7a.sh.
  - From Cursor-Innovation: Add an explicit Step 7a port: either `python/implement_step7a.py` (or similar) with `python/cli.py implement step7a` preserving the current KV tail (`DIAGRAM_STATUS`, `REBASE_OUTCOME`, `LOG_FLUSH_STATUS`, etc.), or [SCOPE-REDUCTION] keep `step-7a.sh` as a thin orchestrator that only calls the new Python leaf verbs and update SKILL.md accordingly.
  - From Codex-Innovation: Add a Python CLI owner for the full Step 7a orchestration, update SKILL.md to call it, and port test-step-7a coverage before deleting the shell
  - From Cursor-Pragmatic, Cursor-Requirements: Add an `implement step-7a` (or equivalent) CLI that preserves the full `step-7a.md` KV/exit contract, update `skills/implement/SKILL.md` and `scripts/test-implement-structure.sh`, then retire the bash file
  - From Codex-Pragmatic: Add a Python Step 7a importable function and CLI verb, preserve the existing stdout KVs and routing, then update SKILL.md and tests to call it
  - From Codex-Requirements: Add a minimal Python Step 7a API and CLI, or explicitly map every Step 7a sub-contract to Python calls in SKILL.md, and port test-step-7a.sh coverage to pytest before deleting the script.
  - From Cursor-dyn-finalize-runlog-auditor: Add an explicit Step 7a port (thin `python/cli.py` verb or retained wrapper calling Python) covering the full `step-7a.sh` orchestration, KV tail, and pytest ported from `test-step-7a.sh`; register it in `python/cli.py` and update `skills/implement/SKILL.md`.
  - From Codex-dyn-finalize-runlog-auditor: Add an explicit Python Step 7a entrypoint and CLI verb, then update SKILL.md to invoke it. Preserve the current KV tail, rebase exit behavior, and best-effort run-log flush semantics.


### FINDING_2: compose-pr-summary.sh retired without ship-pr.sh cutover
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Codex-Requirements, Codex-dyn-migration-surface-sweeper
- **Severity**: important
- **Concern**: The plan deletes `scripts/compose-pr-summary.sh` and ports `compose_summary_bullets` into `python/pr_body.py`, but registers no CLI verb and does not update the live bash ship driver caller. `scripts/ship-pr.sh` still falls back to `compose-pr-summary.sh` when manifest summary is empty during PR prep. After deletion, PR prep loses the plan-goals summary path or fails with a missing script reference.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add a small cli.py verb around pr_body.compose_summary_bullets and update scripts/ship-pr.sh to call that verb before deleting compose-pr-summary.sh.
  - From Codex-Pragmatic: Port compose-pr-summary into Python, register a CLI verb, and update ship-pr.sh before deleting the script
  - From Codex-Requirements: Register a small Python CLI for compose_summary_bullets, update scripts/ship-pr.sh to call it directly, and replace the bash harness/parity references with pytest coverage.
  - From Codex-dyn-migration-surface-sweeper: Extend the scripts/ship-pr.sh step to replace compose-pr-summary.sh with the new Python implementation


### FINDING_3: New CLI verbs missing from machine-stdout whitelist
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: Several planned new `python/cli.py` verbs will emit parsed KVs or captured bodies. Under inherited lib-quiet state, Python quiet routing can send contract output to inherited fd3 instead of the caller's stdout capture, so callers miss `POSTED`, `EMIT_BODY`, `WFR_RC`, `FLUSH_STATUS`, and similar KVs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add every new stdout-contract verb to _MACHINE_STDOUT_KEYS when registering it, unless that main never calls quiet_init and writes directly to stdout.


### FINDING_4: Step 2 materialize-manifest-oos call site not cut over
- **Reviewer(s)**: Codex-Pragmatic, Cursor-dyn-oos-gate-auditor, Codex-dyn-oos-gate-auditor
- **Severity**: important
- **Concern**: The plan deletes `materialize-manifest-oos.sh` and adds an `oos materialize-manifest` CLI, but `step2-implement.sh` still shells to the retired helper twice (including `--count-only`). External implementer complete paths can bail with `manifest-oos-materialization-failed` or lose `oos_observations` routing after deletion. The harness `test-step2-dispatch.sh` also depends on this path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Update step2-implement.sh to invoke python/cli.py oos materialize-manifest, including the count-only path and failure logging labels
  - From Cursor-dyn-oos-gate-auditor: Add ### UPDATED: skills/implement/scripts/step2-implement.sh calling python/cli.py oos materialize-manifest; keep OOS_CHECKPOINT_RC= relay and exit-code passthrough
  - From Codex-dyn-oos-gate-auditor: Add skills/implement/scripts/step2-implement.sh and its harness to the update list; replace both calls with python3 "$PLUGIN_ROOT/python/cli.py" oos materialize-manifest while preserving --count-only, failure logging, and LARCH_TEST_MATERIALIZE_FORCE_FAIL behavior


### FINDING_5: Step 8 OOS checkpoint wrapper still shells to retired script
- **Reviewer(s)**: Codex-Pragmatic, Cursor-dyn-oos-gate-auditor, Codex-dyn-oos-gate-auditor
- **Severity**: important
- **Concern**: `step-8-oos-checkpoint.sh` still invokes `oos-disposition-checkpoint.sh`, which the plan retires without listing this wrapper in `### UPDATED` cutovers. With `OOS_PENDING=true`, the checkpoint cannot clear after filing because the wrapper calls a deleted script; `run-statistics` and `OOS_PENDING=false` never run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Update the wrapper to invoke python/cli.py oos disposition-checkpoint, or absorb the wrapper into a Python CLI while preserving OOS_CHECKPOINT_RC and Tool Failures behavior
  - From Cursor-dyn-oos-gate-auditor: Add ### UPDATED: skills/implement/scripts/step-8-oos-checkpoint.sh calling python/cli.py oos disposition-checkpoint; ### UPDATED: skills/implement/scripts/step2-implement.sh calling python/cli.py oos materialize-manifest; keep OOS_CHECKPOINT_RC= relay and exit-code passthrough
  - From Codex-dyn-oos-gate-auditor: Add skills/implement/scripts/step2-implement.sh and its harness to the update list; replace both calls with python3 "$PLUGIN_ROOT/python/cli.py" oos materialize-manifest while preserving --count-only, failure logging, and LARCH_TEST_MATERIALIZE_FORCE_FAIL behavior


### FINDING_6: Steps 17/18/18b and cleanup wrappers omitted from cutover
- **Reviewer(s)**: Codex-Innovation, Cursor-dyn-migration-surface-sweeper, Codex-dyn-migration-surface-sweeper
- **Severity**: important
- **Concern**: The plan updates `SKILL.md` prose but omits `/implement` wrapper scripts that still shell out to absorbed helpers. After deletion of `write-final-report.sh`, `implement-finalize.sh`, and related helpers, Steps 17, 18, and 18b break at runtime while only skill prose changes. `cleanup.sh` smoke paths are also unaddressed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add explicit UPDATED entries and cut these callers over to the new Python CLI verbs, or delete wrappers only if SKILL.md no longer calls them; update the matching tests/contracts
  - From Cursor-dyn-migration-surface-sweeper: Add ### UPDATED rows for each wrapper above; replace bash paths with python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" oos|execution-issues|diagram|final-report|implement-finalize verbs; drop cleanup.sh --help smoke or call session cleanup-tmpdir directly
  - From Codex-dyn-migration-surface-sweeper: Add UPDATED entries for these wrappers and invoke python/cli.py directly


### FINDING_7: stall-recovery-report.sh callers not cut over
- **Reviewer(s)**: Codex-Pragmatic, Codex-dyn-migration-surface-sweeper
- **Severity**: important
- **Concern**: Tier B stall report validation and generic escalation still depend on `stall-recovery-report.sh`, which the plan deletes. `file-failure-report-cross-repo.sh` falls back to `unsafe-tier-b-body` / `unsafe-tier-b-comment` instead of filing validated public reports. `review_and_fix.py` and `design-step-validator-autofix.sh` lose escalation ledger paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Update this helper to call python/cli.py stall-recovery validate-tier-b-public-file with the same profile and corpus arguments
  - From Codex-dyn-migration-surface-sweeper: Add these callers to the cutover and route them through python/cli.py stall-recovery


### FINDING_8: Python ship driver bypasses security-only OOS checkpoint
- **Reviewer(s)**: Codex-dyn-oos-gate-auditor
- **Severity**: important
- **Concern**: The plan ports checkpoint fail-closed behavior but does not update the live pre-PR OOS signal path in `python/ship.py`. When `OOS_PENDING=true` and only `security-oos-observations.md` is present, `ship.py` checks only non-security accepted files and proceeds past the OOS handoff, so the proposed checkpoint never runs and private security disposition is not enforced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-oos-gate-auditor: Add python/ship.py to the plan; use file_oos.detect or equivalent before PR creation and return needs_user_input=oos-filing when security_present is true unless forked or repo_unavailable; add focused python/test_ship.py coverage


### FINDING_9: file_oos block counting drops spaced Focus area security routing
- **Reviewer(s)**: Codex-dyn-oos-gate-auditor
- **Severity**: important
- **Concern**: Reusing existing `file_oos` block counting loses the retired gate's security routing for spaced `Focus area` labels. The retired AWK predicate strips markup and accepts both `focus-area` and `Focus area` labels, but `file_oos` currently matches only `focus-area`. A block with `- **Focus area**: security` would be counted as non-security, risking public filing or incorrect disposition.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-oos-gate-auditor: Revise the plan to port the retired AWK predicate exactly or centralize on a shared focus[- \t]*area matcher; add a pytest case for a spaced Focus area security block


### FINDING_10: Bootstrap still calls retired post-tracking-issue.sh
- **Reviewer(s)**: Codex-dyn-finalize-runlog-auditor, Codex-dyn-migration-surface-sweeper
- **Severity**: important
- **Concern**: The plan deletes `post-tracking-issue.sh` and adds a Python verb, but `python/bootstrap.py` still directly invokes the shell script during Step 0 tracking adoption. After deletion, metadata posting returns rc 127, sets `DEFERRED`, and can skip the confirmed `parent-issue.md` sentinel path. `python/test_bootstrap.py` still mocks the shell path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-finalize-runlog-auditor: Add python/bootstrap.py to the plan. Replace the shell argv with the new Python CLI verb and preserve POSTED COMMENT_URL ERROR KVs plus the success-only parent-issue sentinel write.
  - From Codex-dyn-migration-surface-sweeper: Add python/bootstrap.py and python/test_bootstrap.py to the plan and call the new Python CLI verb directly



