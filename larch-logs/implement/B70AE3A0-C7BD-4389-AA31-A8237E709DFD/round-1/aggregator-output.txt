### FINDING_1: Ship breadcrumbs bypass shared logging/quiet contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-stream-contract-output.txt
- **Severity**: important
- **Concern**: `ship.py` uses an ad-hoc `_breadcrumb()` writing directly to stderr instead of the existing `logging_util.BreadcrumbWriter`, splitting progress-output policy and quiet-mode behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-stream-contract-output.txt: Address the concern above.

### FINDING_2: Volatile-only refresh skip reason is never emitted
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `REFRESH_SKIP_VOLATILE_ONLY` is included in merge-ok skip reasons but runtime never returns it, leaving callers/docs with a dead or misleading reason.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_3: gh pr create recorded fixture is unused and gate remains stub-only
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-gh-cli-contract-output.txt
- **Severity**: important
- **Concern**: The committed `gh-pr-create-success.txt` fixture is not loaded by tests; coverage still uses inline `RecordingRunner` stubs, so real CLI output/flag drift could pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-gh-cli-contract-output.txt: Address the concern above.

### FINDING_4: PR resolution logic is duplicated across create paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Post-create and conflict-recovery PR resolution duplicate similar URL/list-lag logic, increasing the chance future fixes land in only one path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Volatile cleanup lacks fail-closed git failure tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Tests do not cover non-zero `git restore`, `clean`, or `reset` during volatile-only cleanup, so regressions could silently leave dirty porcelain.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_6: Duplicate Makefile .PHONY entry
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `test-parse-bootstrap-routing-envelope` appears in duplicate `.PHONY` declarations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: OID polling reuses merge-state retry constant
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `MERGE_PR_POST_PUSH_UNKNOWN_RETRIES` is reused for OID polling, making retry tuning misleading.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: Volatile-only helper adds thin indirection
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_volatile_only_under_run_tree` is a thin wrapper that adds indirection in an already large module.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] ci_monitor stderr helpers diverge from ship breadcrumbs
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `ci_monitor.py` uses separate stderr helpers, making future operator-facing progress standardization harder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Bash path lacks volatile-only skip behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-runlog-porcelain-output.txt
- **Severity**: latent
- **Concern**: Bash `larch-log.sh` still commits refresh churn without the new volatile-only classify/restore path, creating bash/python divergence until cutover or parity work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-runlog-porcelain-output.txt: Address the concern above.

### FINDING_11: ship.py main can lose required JSON envelope on unexpected exceptions
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-stream-contract-output.txt
- **Severity**: important
- **Concern**: `main()` only emits JSON after normal `run_ship()` return; unexpected exceptions can produce a traceback and no single JSON stdout object.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-stream-contract-output.txt: Address the concern above.

### FINDING_12: Merge convergence acceptance lacks end-to-end single-CI-cycle test
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Existing tests mainly assert no pre-merge `flush_logs_pre`; they do not prove the clean green ship path completes with one CI/monitor cycle.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: ship.py lacks executable Python 3.11 runtime guard
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-runtime-compat-output.txt
- **Severity**: latent
- **Concern**: The Python 3.11 floor is documented but not enforced at `ship.py` entry, so direct invocation under older interpreters can fail opaquely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-runtime-compat-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Parity-file monkeypatch cleanup treated as optional by one reviewer
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: One reviewer marked stale `test_merge_bash_parity.py` flush monkeypatches as non-regressing/optional cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_15: Planned bash-parity test updates were not applied
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `test_merge_bash_parity.py` still patches obsolete `flush_logs_pre` behavior and lacks planned parity assertions after pre-merge flush removal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_16: Stream/breadcrumb coverage mocks the behavior it should prove
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-stream-contract-output.txt
- **Severity**: important
- **Concern**: Tests manually call or isolate breadcrumb/output helpers instead of exercising real `main()`/`run_ship()` phase emission and stdout/stderr separation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-stream-contract-output.txt: Address the concern above.

### FINDING_17: implement skill lacks mechanical Python-path version fence
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-runtime-compat-output.txt
- **Severity**: important
- **Concern**: The Step 8+ skill fence still relies on prose/orchestrator discipline rather than a bash-enforced Python 3.11 probe and Python driver branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-runtime-compat-output.txt: Address the concern above.

### FINDING_18: Volatile-only tests target private helper instead of public flush integration
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Tests exercise `_larch_log_commit` directly rather than `flush_logs_pre` publish/classify/restore paths, leaving integration regressions possible.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_19: CI poll breadcrumb test omits elapsed-time assertion
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The CI poll breadcrumb test does not assert elapsed-seconds formatting from the injected clock.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_20: Rebase loop can still flush logs and retrigger CI churn
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Although `merge_pr` no longer pre-flushes, the open-PR CI rebase loop still calls `flush_logs_pre` on each `goto_rebase`, risking repeated run-log commits and CI retriggers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_21: Conflict URL recovery assumes recovered PR is open
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `_recover_pr_from_conflict_text` hardcodes state `OPEN`, so closed or merged PR URLs could be treated as mergeable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_22: Volatile cleanup can git-clean too broad a directory
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Cleanup uses `git clean -fd` on the whole relative run-tree path when untracked volatile lines exist, so classifier bugs could delete non-volatile untracked files under that tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] main catch-all JSON envelope also noted as pre-existing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: A reviewer separately marked broad exception-to-JSON handling as pre-existing/out-of-scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] CI breadcrumbs may stay silent before first wait
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Breadcrumbs only emit on the wait branch, so some immediate decisions can lack an initial progress line.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] Workflow automation docs omit Python 3.11+ ship requirement
- **Reviewer(s)**: dyn-runtime-compat-output.txt
- **Severity**: nit
- **Concern**: Installation/setup workflow automation prerequisites do not mention Python 3.11+ for the future Python ship driver.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runtime-compat-output.txt: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] Runtime floor propagation otherwise appears consistent
- **Reviewer(s)**: dyn-runtime-compat-output.txt
- **Severity**: nit
- **Concern**: Reviewer noted floor propagation across Python config, docs, report-tokens, and CI appears internally aligned, with no 3.12-only syntax found.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runtime-compat-output.txt: Address the concern above.

### FINDING_27: Successful gh create URL recovery ignores stderr
- **Reviewer(s)**: dyn-gh-cli-contract-output.txt
- **Severity**: important
- **Concern**: On rc=0, PR URL recovery parses only stdout; if `gh pr create` emits the URL on stderr with warnings/progress, Python can stall despite a created PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-cli-contract-output.txt: Address the concern above.

### FINDING_28: Python create path lacks bash branch-context gh pr view fallback
- **Reviewer(s)**: dyn-gh-cli-contract-output.txt
- **Severity**: important
- **Concern**: If create succeeds with non-URL stdout and branch listing lags/errors, Python lacks bash’s `gh pr view` fallback and may stall while an open PR exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-cli-contract-output.txt: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] Python ensure_pr omits explicit --base
- **Reviewer(s)**: dyn-gh-cli-contract-output.txt
- **Severity**: latent
- **Concern**: `ensure_pr` does not pass an explicit base to `gh.pr_create`, unlike bash; reviewer marked it pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-cli-contract-output.txt: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] Success-path post-create list failure branch lacks test
- **Reviewer(s)**: dyn-gh-cli-contract-output.txt
- **Severity**: nit
- **Concern**: rc=0 create with failing post-create `pr list` plus stdout URL is not tested, though code appears correct on inspection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-cli-contract-output.txt: Address the concern above.

### FINDING_31: Force-push head recovery can merge without a fresh CI monitor cycle
- **Reviewer(s)**: dyn-merge-head-sync-output.txt
- **Severity**: important
- **Concern**: After `_ensure_head_matches_pr` force-pushes recovery to a new head, merge can proceed after a single coarse `pr_checks_all_pass` instead of re-running the full CI monitor for that head.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-merge-head-sync-output.txt: Address the concern above.

### FINDING_32: OID polling does not verify non-empty OID or remote ref agreement
- **Reviewer(s)**: dyn-merge-head-sync-output.txt
- **Severity**: latent
- **Concern**: `_poll_head_oid_match` treats `headRefOid == local_head` as sufficient without rejecting empty OIDs or comparing the remote tracking ref.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-merge-head-sync-output.txt: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] Duplicate closed-PR noop checks remain
- **Reviewer(s)**: dyn-merge-head-sync-output.txt
- **Severity**: nit
- **Concern**: `_merge_noop_if_pr_closed` is called twice back-to-back after pre-merge flush removal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-merge-head-sync-output.txt: Address the concern above.

### FINDING_34: [OUT_OF_SCOPE] Python OID polling is stricter than bash
- **Reviewer(s)**: dyn-merge-head-sync-output.txt
- **Severity**: nit
- **Concern**: Reviewer noted Python’s new OID polling is stricter than bash and considered an improvement, not a parity regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-merge-head-sync-output.txt: Address the concern above.

### FINDING_35: [OUT_OF_SCOPE] config comment still references pre-merge flush
- **Reviewer(s)**: dyn-merge-head-sync-output.txt
- **Severity**: nit
- **Concern**: A comment in `python/config.py` still describes pre-merge flush skips even though `merge_pr` no longer calls `flush_logs_pre`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-merge-head-sync-output.txt: Address the concern above.

### FINDING_36: [OUT_OF_SCOPE] Single-CI-cycle convergence test also noted as acceptance gap
- **Reviewer(s)**: dyn-merge-head-sync-output.txt
- **Severity**: latent
- **Concern**: Reviewer separately marked missing ship-loop single-CI-cycle convergence coverage as mostly covered by flush removal but still not directly asserted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-merge-head-sync-output.txt: Address the concern above.

### FINDING_37: Volatile cleanup can stall on AM tracked sidecars
- **Reviewer(s)**: dyn-runlog-porcelain-output.txt
- **Severity**: important
- **Concern**: Cleanup decides restore targets from pre-reset porcelain and skips `A` rows; an `AM` tracked refresh sidecar can remain worktree-modified after reset, causing a fail-closed dirty-porcelain stall.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlog-porcelain-output.txt: Address the concern above.

### FINDING_38: Volatile skip can undo scrubbed refresh sidecars
- **Reviewer(s)**: dyn-runlog-porcelain-output.txt
- **Severity**: important
- **Concern**: Volatile-only cleanup runs after scrub and may restore tracked refresh sidecars to `HEAD`, potentially reverting scrubbed redactions while skipping the commit that would fix already-committed secret-shaped content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlog-porcelain-output.txt: Address the concern above.

### FINDING_39: [OUT_OF_SCOPE] Token/timing sidecars still force substantive commits
- **Reviewer(s)**: dyn-runlog-porcelain-output.txt
- **Severity**: nit
- **Concern**: Token/timing sidecars are excluded from the volatile allowlist, so some pre-push refreshes still commit; reviewer marked this as matching the plan rather than a cleanup bug.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlog-porcelain-output.txt: Address the concern above.

### FINDING_40: [OUT_OF_SCOPE] Final-report warning uses one-off stderr write
- **Reviewer(s)**: dyn-stream-contract-output.txt
- **Severity**: nit
- **Concern**: `write_final_report_comment` warning output does not share `_breadcrumb()` or shared formatting policy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stream-contract-output.txt: Address the concern above.

### FINDING_41: [OUT_OF_SCOPE] Python ship lacks report-tokens-style quiet-session handling
- **Reviewer(s)**: dyn-stream-contract-output.txt
- **Severity**: nit
- **Concern**: Report-tokens restores stdout/stderr after lib-quiet, while Python ship has no analogous quiet-session handling; reviewer marked this as possibly intentional.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stream-contract-output.txt: Address the concern above.

### FINDING_42: Success-path PR URL fallback is not scoped to the expected repo
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `_recover_pr_from_conflict_text` can take the last pull URL from success stdout without verifying the repo slug, so a lagging `pr_for_branch` plus extra URLs could resolve the wrong PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
