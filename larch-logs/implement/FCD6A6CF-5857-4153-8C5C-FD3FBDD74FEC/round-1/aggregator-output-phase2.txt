### FINDING_1: Stale up-to-date/fresh wording for admin merge in merge-pr.sh and merge-pr.md
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Documentation and the `merge-pr.sh` header/safety comments still require the branch to be up-to-date or fresh before `--admin`, even though code and partially updated invariants now treat clean `BEHIND` as admin-eligible. Contributors or operators following these stale sources may skip valid admin merges, restore `BEHIND`→`main_advanced` short-circuits, or treat clean behind PRs as policy violations. Align `merge-pr.sh` header/safety invariant #2 and `merge-pr.md` `admin_merged` / `policy_denied` / `--no-admin-fallback` rows with CI-pass plus admin-eligible merge state including `BEHIND`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Stale up-to-date-only summary in ci-decide.sh header
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The opening comment at `scripts/ci-decide.sh:7-8` still says merge requires the branch to be up-to-date, despite the conflict-aware matrix and code allowing pass+behind+conflict-free merge. Maintainers editing from the header may regress Phase 2 behavior by restoring pass+!behind-only gating. Rewrite lines 7-8 to document conflict-free merge while behind, matching `ci-decide.md`, the matrix header, and the `--conflicted` column.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: Duplicated CONFLICTED classification without bash/Python parity test
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `CONFLICTED` classification is duplicated across `scripts/ci-status.sh:201-206` and `python/ci_monitor.py:110-120` with no cross-language parity test. A new `mergeStateStatus` value handled differently in bash vs Python can cause merge/rebase loops.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Duplicate BEHIND merge test mocks across Python test modules
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `python/test_merge.py` and `python/test_merge_bash_parity.py` duplicate BEHIND merge test mocks. Fixing stub behavior requires two edits and risks skew.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Monitor driver fixtures omit mergeStateStatus default
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Monitor driver fixtures in `python/test_ci_monitor.py:1469-1525` omit `mergeStateStatus`, defaulting to conflicted=true. Future pass+behind tests on those fixtures would expect merge but get rebase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Fetch-failure path in ci-status.sh skips CONFLICTED derivation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: In `scripts/ci-status.sh:85-91`, fetch-failure early exit skips `CONFLICTED` derivation; the trap emits `CONFLICTED=false` even when `MERGE_STATE_STATUS` was `DIRTY`/`UNKNOWN`. Fetch can fail after `gh pr view` returns `DIRTY`, so `ci-wait` may publish `CONFLICTED=false` for that poll while Python `gather_status` would emit `conflicted=true`. Derive `CONFLICTED` right after reading `mergeStateStatus` (before fetch), or set it on the fetch-fail exit path from `MERGE_STATE_STATUS`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: Missing DIRTY merge-state harness coverage in test-merge-pr
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Docs claim `DIRTY` merge states return `main_advanced`, but `scripts/test-merge-pr.sh` has no `GH_MERGE_STATE=DIRTY` case. A regression treating `DIRTY` as admin-eligible could attempt squash merge on a conflicted PR; only `ci-decide` `CONFLICTED` routing would catch it in the loop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: Missing pass+behind=0+conflicted=true parity test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan requires `behind==0` merges independent of `CONFLICTED`, but there is no test for pass+behind=0+conflicted=true. Flaky `UNKNOWN` on an up-to-date branch could be mis-modeled as conflicted and block merge at `ci-decide`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: BEHIND recovery tests use pending CI only, not passing CI
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: G4/G6/Q2 `BEHIND` recovery cases in `scripts/test-merge-pr.sh` use pending CI only, while `test-merge-pr.md` documents green CI → `admin_merged`. Post-`UNKNOWN` `BEHIND` recovery with passing CI could regress to `ci_not_ready` or `main_advanced` without a failing test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: test-ci-wait-exit-trap Sub-test A omits full 8-key KV contract
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Sub-test A in `scripts/test-ci-wait-exit-trap.sh:128-133` does not assert `CONFLICTED=` (or the full 8-key contract) in the `--output-file` KV payload. File-mode consumers could miss `CONFLICTED` in published output after the contract change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: Duplicate section number 8 in test-merge-pr.md coverage list
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Duplicate section number 8 in the `scripts/test-merge-pr.md:16-17` coverage list confuses harness contract readers during future edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: ci-wait.sh defaults missing CONFLICTED to false
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: In `scripts/ci-wait.sh:216-221`, a missing `CONFLICTED` line defaults to false. Partial upgrade (old `ci-status` without `CONFLICTED`) with pass+behind>0 and a `DIRTY` PR can loop merge then `main_advanced` until caps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: No dedicated CLEAN mergeStateStatus test in test-ci-status.sh
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-ci-status.sh:70-88` has no dedicated `CLEAN` `mergeStateStatus` / `CONFLICTED=false` test case per the plan test list. Regression in `CLEAN` classification could slip through because only default-stub pending cases assert `CONFLICTED=false`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
