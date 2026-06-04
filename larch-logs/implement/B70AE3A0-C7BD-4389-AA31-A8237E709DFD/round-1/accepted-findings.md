### FINDING_1: Ship breadcrumbs bypass shared logging/quiet contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-stream-contract-output.txt
- **Severity**: important
- **Concern**: `ship.py` uses an ad-hoc `_breadcrumb()` writing directly to stderr instead of the existing `logging_util.BreadcrumbWriter`, splitting progress-output policy and quiet-mode behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-stream-contract-output.txt: Address the concern above.


### FINDING_11: ship.py main can lose required JSON envelope on unexpected exceptions
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-stream-contract-output.txt
- **Severity**: important
- **Concern**: `main()` only emits JSON after normal `run_ship()` return; unexpected exceptions can produce a traceback and no single JSON stdout object.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-stream-contract-output.txt: Address the concern above.


### FINDING_15: Planned bash-parity test updates were not applied
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `test_merge_bash_parity.py` still patches obsolete `flush_logs_pre` behavior and lacks planned parity assertions after pre-merge flush removal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_2: Volatile-only refresh skip reason is never emitted
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `REFRESH_SKIP_VOLATILE_ONLY` is included in merge-ok skip reasons but runtime never returns it, leaving callers/docs with a dead or misleading reason.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_22: Volatile cleanup can git-clean too broad a directory
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Cleanup uses `git clean -fd` on the whole relative run-tree path when untracked volatile lines exist, so classifier bugs could delete non-volatile untracked files under that tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


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


### FINDING_3: gh pr create recorded fixture is unused and gate remains stub-only
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-gh-cli-contract-output.txt
- **Severity**: important
- **Concern**: The committed `gh-pr-create-success.txt` fixture is not loaded by tests; coverage still uses inline `RecordingRunner` stubs, so real CLI output/flag drift could pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-gh-cli-contract-output.txt: Address the concern above.


### FINDING_31: Force-push head recovery can merge without a fresh CI monitor cycle
- **Reviewer(s)**: dyn-merge-head-sync-output.txt
- **Severity**: important
- **Concern**: After `_ensure_head_matches_pr` force-pushes recovery to a new head, merge can proceed after a single coarse `pr_checks_all_pass` instead of re-running the full CI monitor for that head.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-merge-head-sync-output.txt: Address the concern above.


### FINDING_38: Volatile skip can undo scrubbed refresh sidecars
- **Reviewer(s)**: dyn-runlog-porcelain-output.txt
- **Severity**: important
- **Concern**: Volatile-only cleanup runs after scrub and may restore tracked refresh sidecars to `HEAD`, potentially reverting scrubbed redactions while skipping the commit that would fix already-committed secret-shaped content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlog-porcelain-output.txt: Address the concern above.


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


