# Review Round 4

- Mode: `diff`
- 6 accepted, 1 rejected (0 exonerated)

## Accepted Findings

### FINDING_12: Plan manifest omits route/SKILL surfaces for `MARKER_CLEARED`
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `MARKER_CLEARED` propagation touches `design-route.sh`, `skills/design/SKILL.md`, and structure tests, but those surfaces were not listed in the plan file manifest, weakening future plan-to-diff audits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_14: Python ship resume fresh-fallback can reset consumed counters and rerun side-effect phases
- **Reviewer(s)**: dyn-ship-resume-output.txt
- **Severity**: important
- **Concern**: `_resume_plan()` may fall back to a fresh resume plan while preserving counters, but `run_ship()` then takes the fresh path and resets merge-loop counters, potentially rerunning pre-ship side effects and bypassing consumed iteration/fix/retry budgets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-resume-output.txt: Address the concern above.


### FINDING_15: Remote recovery commit pinning contract is under-documented
- **Reviewer(s)**: dyn-contract-sync-output.txt
- **Severity**: latent
- **Concern**: Implementation resolves `FETCH_HEAD` to an immutable commit SHA before `ls-tree`/`git show`, but updated docs no longer explicitly preserve that contract, increasing risk that future edits extract from mutable `FETCH_HEAD` directly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-sync-output.txt: Address the concern above.

### FINDING_4: Pre-fetch validation failures do not assert pause marker retention
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Tests for early validation failures such as issue mismatch, repo mismatch, invalid run id, invalid step, and invalid recovery branch check error tokens but not that the pause marker remains, leaving WI3’s keep-on-failure guarantee under-tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_5: Git stub does not model rev-parse/object-id handoff accurately
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The pause/resume git stub returns a directory path from `rev-parse` and lets `ls-tree`/`show` ignore object ids, so stub tests can miss invalid `snapshot_sha` handling or ref-peeling bugs in the production `rev-parse` → `ls-tree`/`show` chain.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_6: Primary round-trip test omits `MARKER_CLEARED=true` assertion
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The main pause/resume round-trip success fixture verifies marker absence from the body but not the emitted `MARKER_CLEARED=true` contract, so a regression dropping that output could slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


