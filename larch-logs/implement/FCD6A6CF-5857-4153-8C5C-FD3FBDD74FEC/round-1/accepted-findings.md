### FINDING_1: Stale up-to-date/fresh wording for admin merge in merge-pr.sh and merge-pr.md
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Documentation and the `merge-pr.sh` header/safety comments still require the branch to be up-to-date or fresh before `--admin`, even though code and partially updated invariants now treat clean `BEHIND` as admin-eligible. Contributors or operators following these stale sources may skip valid admin merges, restore `BEHIND`→`main_advanced` short-circuits, or treat clean behind PRs as policy violations. Align `merge-pr.sh` header/safety invariant #2 and `merge-pr.md` `admin_merged` / `policy_denied` / `--no-admin-fallback` rows with CI-pass plus admin-eligible merge state including `BEHIND`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


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


### FINDING_2: Stale up-to-date-only summary in ci-decide.sh header
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The opening comment at `scripts/ci-decide.sh:7-8` still says merge requires the branch to be up-to-date, despite the conflict-aware matrix and code allowing pass+behind+conflict-free merge. Maintainers editing from the header may regress Phase 2 behavior by restoring pass+!behind-only gating. Rewrite lines 7-8 to document conflict-free merge while behind, matching `ci-decide.md`, the matrix header, and the `--conflicted` column.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


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


