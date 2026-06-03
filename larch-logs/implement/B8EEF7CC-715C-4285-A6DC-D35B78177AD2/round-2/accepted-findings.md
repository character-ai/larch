### FINDING_1: Driver e2e acceptance scenarios are under-tested
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-harness-gate-output.txt
- **Severity**: important
- **Concern**: `python/test_ship.py` covers only a small happy-path subset. Required draft/forked/repo-unavailable/transient/stall/GOTO-rebase/cap/short-circuit/teardown and flush invariants can regress with green tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-harness-gate-output.txt: Address the concern above.


### FINDING_13: PR title derivation diverges from bash
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: Python titles use raw `HEAD` subject and omit `Fixes #N:`. After log flush commits, PR titles can become `chore(larch-logs): flush …` and lose issue auto-link/close semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-bash-parity-output.txt: Address the concern above.


### FINDING_14: Post-create final report comment failure is fatal
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-ship-state-output.txt
- **Severity**: important
- **Concern**: `write_final_report_comment` raises after PR creation, turning a best-effort comment refresh into a stalled ship run and potentially leaving an open PR without finalize state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-ship-state-output.txt: Address the concern above.


### FINDING_15: Post-merge log finalization can mark done before report success
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-harness-gate-output.txt
- **Severity**: important
- **Concern**: `flush_logs_post` can persist `status=done` before final report/render failures are known, and tests do not enforce manifest-before-report ordering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-harness-gate-output.txt: Address the concern above.


### FINDING_18: Feature branch deletion lacks option separator and branch validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `git branch -D` is invoked without `--`; branch names beginning with option-like characters could be misinterpreted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_2: Finalize parity and unit coverage are too shallow
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: `python/test_finalize_bash_parity.py` and finalize unit tests smoke-test only a narrow subset, leaving postbump, force-push gate, teardown/stall, session guard, and rename parity with `implement-finalize.sh` uncovered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt: Address the concern above.


### FINDING_22: Postbump uses CI conflict-resolution path instead of bash Step 8b
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-bash-parity-output.txt, dyn-finalize-flow-output.txt
- **Severity**: important
- **Concern**: Python postbump calls `rebase_and_rebump` / `rebase_and_push`, which can launch automated conflict fixers. Bash Step 8b stalls on conflicts and separates no-push rebase from force-push gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-bash-parity-output.txt, dyn-finalize-flow-output.txt: Address the concern above.


### FINDING_23: Stalled terminal outcomes do not persist finalize stall metadata
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: Checks/postbump/pre-push/CI stall exits can return exit 4 without writing `finalize-state.sh` / stall flags, while Step 18 expects that state and Python does not maintain `ship-pr-state.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-bash-parity-output.txt: Address the concern above.


### FINDING_24: Postmerge verify/cleanup failures can still return success
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-finalize-flow-output.txt
- **Severity**: important
- **Concern**: Verify-main, branch cleanup, pull, or local cleanup failures can yield `Outcome.OK`, a done manifest, or stale main state instead of failing closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-finalize-flow-output.txt: Address the concern above.


### FINDING_28: Python cutover docs and invocation routing are incomplete
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: `skills/implement/SKILL.md` still has bash-only state-file/routing assumptions, lacks a complete Python invoke contract, and omits env/argv needed for retries, log commits, and teardown guards.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt: Address the concern above.


### FINDING_3: Fork-aware CI rebase/behind checks use the wrong base remote
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: The CI loop does not thread fork-aware `base_remote` / `base_ref`, so forked targets can rebase/check against `origin/main` instead of `upstream/main`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_30: Merge result case matrix is incomplete before postmerge
- **Reviewer(s)**: dyn-ship-state-output.txt
- **Severity**: important
- **Concern**: After `merge.merge_pr`, Python only loops on `ci_not_ready` and `main_advanced`. Other bash-handled outcomes like `version_already_published`, `policy_denied`, `admin_failed`, or head-divergence can fall through to postmerge and return success without a merge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-state-output.txt: Address the concern above.


### FINDING_31: OOS disposition gate lacks bash inputs
- **Reviewer(s)**: dyn-ship-state-output.txt
- **Severity**: important
- **Concern**: `_oos_gate` does not pass commit-range messages or `oos-issues.ndjson`, so inline triage or rejected-marker disposition can be missed and cause spurious exit 3 handbacks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-state-output.txt: Address the concern above.


### FINDING_32: Postmerge finalize state is written too late
- **Reviewer(s)**: dyn-ship-state-output.txt
- **Severity**: important
- **Concern**: Postmerge can return before `write_finalize_state` when `flush_logs_post` skips/fails. Bash writes finalize state at postmerge entry and treats report/log refresh failures as warnings after a successful merge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-state-output.txt: Address the concern above.


### FINDING_33: Python postmerge path does not write the post-merge sentinel
- **Reviewer(s)**: dyn-ship-state-output.txt
- **Severity**: important
- **Concern**: Python does not create `$IMPLEMENT_TMPDIR/post-merge-sentinel`, weakening the mechanical guard that prevents post-merge commits by helpers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-state-output.txt: Address the concern above.


### FINDING_34: OOS checkpoint still depends on `ship-pr-state.sh`
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: After Python-path `oos-filing` handback, `oos-disposition-checkpoint.sh` derives fork/repo-unavailable flags only from absent bash state, causing false or incorrectly strict validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.


### FINDING_35: Final report rendering reads stale bash state on Python path
- **Reviewer(s)**: dyn-runlogs-output.txt
- **Severity**: important
- **Concern**: `write-final-report.sh` derives merge and PR fields from `ship-pr-state.sh`, but Python updates `RunContext`/`finalize-state.sh` instead. Reports can render as bailed or with placeholder PR data despite a done manifest.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlogs-output.txt: Address the concern above.


### FINDING_36: Live log flush callers can still honor stale state files
- **Reviewer(s)**: dyn-runlogs-output.txt
- **Severity**: important
- **Concern**: Some Python live-path `flush_logs_pre` calls do not clear `state_file`; stale `SHIP_PR_STATE_FILE` values can skip required pre-push or pre-rebase log commits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlogs-output.txt: Address the concern above.


### FINDING_37: Postmerge manifest recovery is weaker than bash
- **Reviewer(s)**: dyn-runlogs-output.txt
- **Severity**: important
- **Concern**: Python does not fully port bash’s missing-manifest recovery before setting done/reporting, so report generation can proceed after best-effort recovery where bash would fail closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlogs-output.txt: Address the concern above.


### FINDING_4: Postbump remote probe can use the wrong branch semantics
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-finalize-flow-output.txt
- **Severity**: important
- **Concern**: Postbump probes `origin/{branch}` and collapses missing branches with transport errors. Forked runs or transient lookup failures can skip required force-pushes or disagree with bash remote-check behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-finalize-flow-output.txt: Address the concern above.


### FINDING_40: Tracking issue rename can run after `gh issue view` failure
- **Reviewer(s)**: dyn-finalize-flow-output.txt
- **Severity**: latent
- **Concern**: `_rename_issue` only enforces the OPEN-state guard when `gh issue view` succeeds; a failed view can still proceed to rename.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-finalize-flow-output.txt: Address the concern above.


### FINDING_41: Stalled auto-stash treats `git status` failure as clean
- **Reviewer(s)**: dyn-finalize-flow-output.txt
- **Severity**: latent
- **Concern**: `auto_stash_stalled_changes` returns no stash and no warning on non-zero `git status`, so operators may think a dirty tree was clean or stashed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-finalize-flow-output.txt: Address the concern above.


### FINDING_43: CI monitor transient bail maps to stalled instead of transient
- **Reviewer(s)**: dyn-ci-handback-output.txt
- **Severity**: important
- **Concern**: `ci_monitor.monitor()` maps bail decisions to `Outcome.STALLED` even when the bail reason matches transient network signatures, causing exit 4 instead of retryable exit 6.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-handback-output.txt: Address the concern above.


### FINDING_44: `rebase_then_evaluate` split changes CI loop accounting
- **Reviewer(s)**: dyn-ci-handback-output.txt
- **Severity**: important
- **Concern**: Python separates rebase from evaluate-failure handling, consuming extra CI-loop iterations and potentially adding another full poll wait compared with bash’s atomic handler.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-handback-output.txt: Address the concern above.


### FINDING_46: Finalize bash parity module is skipped under `make py-test`
- **Reviewer(s)**: dyn-harness-gate-output.txt
- **Severity**: important
- **Concern**: `python/test_finalize_bash_parity.py` resolves `scripts/implement-finalize.sh` relative to CWD. Since `make py-test` runs from `python/`, the module silently skips in CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-gate-output.txt: Address the concern above.


### FINDING_5: Checks phase hardcodes external fixer availability
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: `run_checks_phase()` is called with `codex_present=True` and `cursor_present=True`, ignoring session probes. Degraded sessions may invoke unavailable external fixer tiers instead of bash-equivalent fallback behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-bash-parity-output.txt: Address the concern above.


### FINDING_6: CI transient retry count is not persisted across loop iterations
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-ci-handback-output.txt
- **Severity**: latent
- **Concern**: `transient_retries` remains `0` across CI loop iterations, so transient rerun budget can diverge from bash `TRANSIENT_RETRIES` semantics and repeat rerun paths incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-ci-handback-output.txt: Address the concern above.


### FINDING_7: Version race gate still runs on the ship merge path
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `_version_race_gate` remains active in `merge_pr`, so ship can still hit obsolete version-race branches despite the trimmed Phase 7 ship scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.


