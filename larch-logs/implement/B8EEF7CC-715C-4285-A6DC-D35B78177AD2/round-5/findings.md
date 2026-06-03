### FINDING_1: Driver acceptance matrix coverage is missing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-harness-gate-output.txt
- **Severity**: important
- **Concern**: `python/test_ship.py` covers only a small subset of the Phase 7 driver acceptance matrix, leaving draft/forked/repo-unavailable/transient/GOTO-rebase/cap-exhaustion/single-flush and JSON handback regressions unguarded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-harness-gate-output.txt: Address the concern above.

### FINDING_2: Finalize unit and parity coverage is too shallow
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-finalize-parity-output.txt, dyn-harness-gate-output.txt
- **Severity**: important
- **Concern**: `python/test_finalize.py` and `python/test_finalize_bash_parity.py` do not cover the planned postbump gates, teardown/session guards, rename branches, remote-check routing, or true bash parity against `implement-finalize.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-finalize-parity-output.txt, dyn-harness-gate-output.txt: Address the concern above.

### FINDING_3: Session tmpdir allowlist logic is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `python/ship.py` and `python/finalize.py` duplicate tmpdir root/session validation, so future edits can make ship accept paths that finalize refuses or vice versa.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Unexpected exceptions are converted to STALLED
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Broad `except Exception` handling in `run_ship` maps implementation bugs like `AttributeError` or `KeyError` to operator-facing `STALLED` instead of surfacing a clear traceback/failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_5: `run_ship` is too monolithic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The large inline orchestrator in `python/ship.py` makes phase ordering and state-write regressions harder to review and maintain.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Dead merge race-gate stub remains
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_version_race_gate` remains as a dead stub with linter suppressions, confusing the merge-path behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: Legacy exit constants can confuse Outcome routing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Legacy `EXIT_BAIL` / `EXIT_STALL` constants coexist with the newer `OUTCOME_EXIT_MAP`, risking future semantic inversion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_8: Terminal state writes bypass the helper
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Several stall/failure paths bypass `_write_terminal_state`, making `finalize-state.sh` metadata inconsistent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: `flush_logs_post` mutates manifest inconsistently
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `flush_logs_post` duplicates `pr_number` across manifest fields and bypasses `update_manifest`, risking disagreement among manifest consumers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_10: CI monitor uses inconsistent working directory
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `ci_monitor.monitor` can receive `cwd` while other phases use `repo_root`, so `cwd=None` can make CI/rebase/check phases run against inconsistent repository state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] Test runner helpers are duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `RecordingRunner` is copied across many test modules, increasing harness duplication.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] `RunContext` has duplicate alias fields
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Duplicate `RunContext` aliases like `branch`/`branch_name` and `forked`/`forked_target` can drift if updates set only one side.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_13: Tool availability ignores session-env flags
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `codex_present` / `cursor_present` are derived from env/tool labels instead of Step 0 `CODEX_PRESENT` / `CURSOR_PRESENT`, so checks can misroute or skip external lint-fix tiers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_14: Post-create final-report refresh is fail-closed
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: After PR creation succeeds, `write-final-report --comment-only` failure makes Python return `STALLED` instead of continuing to CI with a warning like bash.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_15: OOS checkpoint reads the wrong run-log ID
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `oos-disposition-checkpoint.sh` uses session-id as `RUN_ID`, so it can miss Python-filed OOS issue URLs under `larch-logs/implement/<RUN_ID>/` and block `OOS_PENDING` clearing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_16: CI monitor transient bail path lacks coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The new monitor bail-to-`TRANSIENT` path has no pytest coverage, so transient network bails may regress to `STALLED`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_17: Run-log post-flush ordering is not tested
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The planned `flush_logs_post` ordering test is absent, so final reports could be written before manifest `status=done` / `pr_number` without CI detecting it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_18: Python Step 8+ cutover docs and harness remain bash-state centric
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-cutover-docs-output.txt
- **Severity**: important
- **Concern**: `skills/implement/SKILL.md` only partially describes the Python ship path; much of Step 8+ still seeds/parses `ship-pr-state.sh`, re-invokes bash, and lacks structural checks for the JSON-driven Python branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-cutover-docs-output.txt: Address the concern above.

### FINDING_19: PR URL is emitted without outbound redaction
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `pr_url` is printed/journaled in Step 8+ JSON without `redact_outbound`, potentially leaking private hostnames despite `SECURITY.md` claims.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_20: OOS checkpoint carve-outs may miss Python state
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Python runs may lack `ship-pr-state.sh`, so forked/repo-unavailable OOS checkpoint skips can fail unless helpers also read session/finalize state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] Python redaction lacks internal-URL handling
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `python/redact.py` lacks repository-wide internal URL scrubbing for outbound session-derived text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_22: Python ship lacks resume/short-circuit semantics
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-ship-driver-output.txt
- **Severity**: important
- **Concern**: Re-invoking `python/ship.py` restarts checks/postbump/PR prep instead of resuming from persisted phase or ground truth, causing redundant rebase/push/CI churn.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-ship-driver-output.txt: Address the concern above.

### FINDING_23: Pre-push report rendering failure is fail-closed
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-runlog-manifest-output.txt
- **Severity**: important
- **Concern**: `flush_logs_pre` treats `write-final-report.sh` failure as a hard `ShipError`, while bash treats report rendering as non-fatal and still attempts log commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-runlog-manifest-output.txt: Address the concern above.

### FINDING_24: Post-merge flush can run before postmerge success is validated
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The driver can write post-merge done artifacts before validating `postmerge` outcome, leaving a done manifest even when postmerge later stalls.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_25: Post-merge manifest can say done before terminal renders succeed
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-runlog-manifest-output.txt
- **Severity**: important
- **Concern**: `flush_logs_post` writes `status=done` before final report/token/timing renders; redaction/render failure can leave incomplete terminal artifacts with a done manifest.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-runlog-manifest-output.txt: Address the concern above.

### FINDING_26: CI goto-rebase ignores rebase result
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The CI loop does not check `RebaseResult`, so failed or incomplete rebases can appear successful and spin until caps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_27: Postmerge flush gate reads stale context
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `_postmerge_should_flush` and `flush_logs_post` use the pre-postmerge `ctx` instead of updated `state_ctx`, so `pr_closed`/merge-result changes can be missed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_28: CI-loop counters are not persisted and diverge from bash
- **Reviewer(s)**: dyn-ship-driver-output.txt, dyn-ci-rebase-output.txt
- **Severity**: important
- **Concern**: `iteration`, `rebase_count`, `fix_attempts`, and `transient_retries` live only in process memory and use different reset/increment rules than bash, so caps can be bypassed across reinvokes or exhausted too early within a run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-driver-output.txt, dyn-ci-rebase-output.txt: Address the concern above.

### FINDING_29: Python JSON lacks a stable phase for transient retry budgeting
- **Reviewer(s)**: dyn-ship-driver-output.txt, dyn-cutover-docs-output.txt
- **Severity**: important
- **Concern**: Step 8+ exit-6 retry accounting still keys off `PHASE` from `ship-pr-state.sh`, but Python does not persist or emit a stable phase, so transient budgets cannot match bash.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-driver-output.txt, dyn-cutover-docs-output.txt: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] Driver test coverage gap noted as non-runtime
- **Reviewer(s)**: dyn-ship-driver-output.txt, dyn-ci-rebase-output.txt
- **Severity**: latent
- **Concern**: Additional reviewers also observed `python/test_ship.py` lacks broad driver/goto-rebase/cap/transient coverage, while marking it out of scope relative to their runtime focus.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-driver-output.txt, dyn-ci-rebase-output.txt: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] Postmerge unexpected-verification behavior matches bash
- **Reviewer(s)**: dyn-ship-driver-output.txt
- **Severity**: nit
- **Concern**: `postmerge` returning `OK` on unexpected main verification is a pre-existing/bash-matching behavior, not a Python-only regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-driver-output.txt: Address the concern above.

### FINDING_32: Python postmerge cleanup lacks bash local-cleanup parity
- **Reviewer(s)**: dyn-finalize-parity-output.txt
- **Severity**: important
- **Concern**: `finalize.postmerge()` reimplements cleanup without bash’s fetch/retry, orphan larch-log reset, ahead diagnostics, and verify-main behavior, yet can still return `OK` with partial cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-finalize-parity-output.txt: Address the concern above.

### FINDING_33: Remote branch probe failure maps differently from bash
- **Reviewer(s)**: dyn-finalize-parity-output.txt
- **Severity**: important
- **Concern**: Python maps some remote-branch probe failures to `TRANSIENT` reinvoke, while bash stalls on `remote-check-failed`, changing operator recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-finalize-parity-output.txt: Address the concern above.

### FINDING_34: Postbump log refresh and force-push ordering diverge from bash
- **Reviewer(s)**: dyn-finalize-parity-output.txt
- **Severity**: important
- **Concern**: Python folds log refresh/rebase/force-push into postbump and can perform two pre-PR log commits, unlike bash’s single refresh plus gated rebase/push flow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-finalize-parity-output.txt: Address the concern above.

### FINDING_35: Python teardown omits live bash Step 18 substeps
- **Reviewer(s)**: dyn-finalize-parity-output.txt
- **Severity**: important
- **Concern**: Planned Python teardown omits execution-issue safety net, manifest recovery, optional teardown log commit, background-process kill, and bash cleanup-tmpdir behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-finalize-parity-output.txt: Address the concern above.

### FINDING_36: [OUT_OF_SCOPE] Bash postbump state validation uses legacy fields
- **Reviewer(s)**: dyn-finalize-parity-output.txt
- **Severity**: latent
- **Concern**: Bash postbump state validation still references legacy `BUMP_TYPE` / `NEW_VERSION` fields, a pre-existing cross-path consistency risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-finalize-parity-output.txt: Address the concern above.

### FINDING_37: Pre-push probe misses finalize-state and sentinel fallback
- **Reviewer(s)**: dyn-runlog-manifest-output.txt
- **Severity**: important
- **Concern**: State-file-less `_pre_push_probe` does not consult `finalize-state.sh` or `post-merge-sentinel`, causing wrong post-merge skip classification and unnecessary refresh work after reinvocation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlog-manifest-output.txt: Address the concern above.

### FINDING_38: [OUT_OF_SCOPE] Run-log post-flush ordering test is absent
- **Reviewer(s)**: dyn-runlog-manifest-output.txt
- **Severity**: nit
- **Concern**: The plan-requested `flush_logs_post` call-order regression test is missing, but this reviewer marked it out of scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlog-manifest-output.txt: Address the concern above.

### FINDING_39: [OUT_OF_SCOPE] Commit-failed skip behavior is consistent for Phase 7
- **Reviewer(s)**: dyn-runlog-manifest-output.txt
- **Severity**: nit
- **Concern**: `REFRESH_SKIP_COMMIT_FAILED` being non-fatal matches the current ship-driver Phase 7 path, despite older review expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlog-manifest-output.txt: Address the concern above.

### FINDING_40: CI rebase/fixer ordering diverges from bash
- **Reviewer(s)**: dyn-ci-rebase-output.txt
- **Severity**: important
- **Concern**: Python evaluates/fixes CI failures before performing required rebase work, and also sets `goto_rebase` after fix-only pushes with `behind_count=0`, causing unnecessary or incorrectly ordered force-push/rebase cycles.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-rebase-output.txt: Address the concern above.

### FINDING_41: CI rebase conflicts lack bash handoff
- **Reviewer(s)**: dyn-ci-rebase-output.txt, dyn-cutover-docs-output.txt
- **Severity**: important
- **Concern**: Postbump and CI rebases use `allow_conflict_fix=False`, turning routine rebase conflicts into bare `STALLED` exits without bash’s `CONFLICT_FILES` / resume-phase handoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-rebase-output.txt, dyn-cutover-docs-output.txt: Address the concern above.

### FINDING_42: [OUT_OF_SCOPE] CI fixer push mode diverges after rebase
- **Reviewer(s)**: dyn-ci-rebase-output.txt
- **Severity**: latent
- **Concern**: `stage_and_push` uses normal `git push` where bash uses force-push after rebase or `CI_FIX_REBASE_PENDING`; reviewer marked this as pre-existing but amplified by Phase 7.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-rebase-output.txt: Address the concern above.

### FINDING_43: [OUT_OF_SCOPE] CI-fix parity divergences predate cutover docs
- **Reviewer(s)**: dyn-cutover-docs-output.txt
- **Severity**: latent
- **Concern**: Prior Python CI-fix divergences remain behaviorally relevant once the Python ship path is enabled, but are not introduced solely by the cutover docs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cutover-docs-output.txt: Address the concern above.

### FINDING_44: Python CI-fix log refresh still uses stale bash state
- **Reviewer(s)**: dyn-cutover-docs-output.txt
- **Severity**: important
- **Concern**: The autonomous CI-fix procedure still calls `refresh-run-logs.sh --state-file "$IMPLEMENT_TMPDIR/ship-pr-state.sh"`, which Python does not update, so log refresh can use stale or missing run state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cutover-docs-output.txt: Address the concern above.

### FINDING_45: Step 18 stall recovery does not read Python finalize-state
- **Reviewer(s)**: dyn-cutover-docs-output.txt
- **Severity**: important
- **Concern**: Step 18a resolves `STALL_TRACKING` from memory, `ship-pr-state.sh`, and session-env, but Python records stalls in `finalize-state.sh`, so Python stalls can skip recovery/title-prefix handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cutover-docs-output.txt: Address the concern above.

### FINDING_46: Python `--no-logs-commit` flag shape differs from bash docs
- **Reviewer(s)**: dyn-cutover-docs-output.txt
- **Severity**: important
- **Concern**: Docs say to pass the same argv as bash, but bash passes an explicit boolean while Python defines `--no-logs-commit` as `store_true`, so copying the bash invoke shape can invert behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cutover-docs-output.txt: Address the concern above.

### FINDING_47: [OUT_OF_SCOPE] Legacy exit constants are unused but confusing
- **Reviewer(s)**: dyn-cutover-docs-output.txt
- **Severity**: nit
- **Concern**: `EXIT_BAIL` / `EXIT_STALL` remain near the correct outcome map and could mislead future callers, though this was marked out of scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cutover-docs-output.txt: Address the concern above.

### FINDING_48: [OUT_OF_SCOPE] Default bash selection remains intact
- **Reviewer(s)**: dyn-cutover-docs-output.txt
- **Severity**: nit
- **Concern**: Documentation preserves the default `bash` path and optional `python` strangler-fig selection; no repo script flips the default.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cutover-docs-output.txt: Address the concern above.

### FINDING_49: [OUT_OF_SCOPE] Positive Python state fallback work landed
- **Reviewer(s)**: dyn-cutover-docs-output.txt
- **Severity**: nit
- **Concern**: `write-final-report.sh` and `oos-disposition-checkpoint.sh` gained `finalize-state.sh` fallbacks, and `SECURITY.md` documents the Python stdout/finalize-state boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cutover-docs-output.txt: Address the concern above.

### FINDING_50: `test-merge-parity` is missing from linting docs
- **Reviewer(s)**: dyn-harness-gate-output.txt
- **Severity**: nit
- **Concern**: `docs/linting.md` documents `make test-merge-pr` but not the new `make test-merge-parity` target wired into shard 5.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-gate-output.txt: Address the concern above.

### FINDING_51: `test-merge-parity` invocation style differs from Python test suite
- **Reviewer(s)**: dyn-harness-gate-output.txt
- **Severity**: nit
- **Concern**: The Makefile runs merge parity tests from repo root, unlike `py-test`’s `cd python` style, making the target easier to break when copied or run from other directories.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-gate-output.txt: Address the concern above.

### FINDING_52: Merge parity module-level bash skip hides pure-Python tests
- **Reviewer(s)**: dyn-harness-gate-output.txt
- **Severity**: nit
- **Concern**: A module-level `skipif(bash missing)` skips pure-Python merge parity tests that do not require bash, allowing the target to pass with all tests skipped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-gate-output.txt: Address the concern above.

### FINDING_53: [OUT_OF_SCOPE] `test-merge-pr` linting doc row is stale
- **Reviewer(s)**: dyn-harness-gate-output.txt
- **Severity**: nit
- **Concern**: The existing `test-merge-pr` docs still mention removed same-version race-gate machinery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-gate-output.txt: Address the concern above.

### FINDING_54: [OUT_OF_SCOPE] Shard-balance comment says `ship-pr` was removed
- **Reviewer(s)**: dyn-harness-gate-output.txt
- **Severity**: nit
- **Concern**: A Makefile shard-balance comment says `test-ship-pr` was removed entirely in favor of Python, while `scripts/ship-pr.sh` remains the default bash path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-gate-output.txt: Address the concern above.
