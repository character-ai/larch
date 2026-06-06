### FINDING_1: [OUT_OF_SCOPE] Unrelated Python ship/run-log changes are bundled with pause/resume PR
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-pause-lifecycle-output.txt, dyn-ship-resume-output.txt, dyn-contract-sync-output.txt
- **Severity**: important
- **Concern**: The branch mixes substantial Python ship/run-log/resume changes with the design pause/resume shell fix, increasing review scope, regression blast radius, and making pause/resume work harder to bisect, revert, or validate against its plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-pause-lifecycle-output.txt: Address the concern above.
  - From dyn-ship-resume-output.txt: Address the concern above.
  - From dyn-contract-sync-output.txt: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] Existing `.pause-requested` in caller tmpdir may survive successful restore
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `design-pause-load.sh` removes `.pause-requested` only from the staging tree before `cp -R`; if `$DESIGN_TMPDIR` already contains a local `.pause-requested`, successful restore may leave it behind and immediately re-trigger pause handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] Remote recovery branch lacks real-git FETCH_HEAD resume coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The remote recovery path using `FETCH_HEAD` is not covered by a real-git harness case, so regressions in fetched-object commit resolution or `ls-tree`/`show` extraction for `larch-log-design-<RUN_ID>` could pass stub-backed tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.

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

### FINDING_7: [OUT_OF_SCOPE] `relevant-checks.sh` does not route pause script edits to pause/resume harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/relevant-checks.sh` maps design-log-publish edits to its harness but lacks equivalent mappings for `design-pause-load.sh` / `design-pause-save.sh`, so local relevant checks may skip the dedicated pause/resume tests after pause script edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Pause restore binds git objects to caller cwd rather than `--repo`
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-ship-resume-output.txt
- **Severity**: latent
- **Concern**: `design-pause-load.sh` resolves `REPO_TOP` from the caller’s current git worktree while `--repo` only scopes GitHub issue access, so a cwd/repo mismatch could restore objects from the wrong clone despite issue/repo marker binding.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-ship-resume-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] Merged PR recovery skips head branch re-validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `_validate_recovered_pr` returns already-merged PRs without re-checking `head_ref == branch`, widening PR recovery if session state or URL history is poisoned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Pause-load failures fall through to title/re-entry routing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-ship-resume-output.txt, dyn-contract-sync-output.txt
- **Severity**: latent
- **Concern**: When a pause marker is present but `LOAD_OK=false`, `design-route.sh` can continue into title eligibility or re-entry routing instead of terminating with a pause-load error, obscuring retryable restore failures and potentially starting fresh design flow while the marker remains.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-ship-resume-output.txt: Address the concern above.
  - From dyn-contract-sync-output.txt: Address the concern above.

### FINDING_11: Successful restore can lose one warning when both body drift and marker deletion failure occur
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-ship-resume-output.txt
- **Severity**: latent
- **Concern**: The success path emits or stores only one `WARN` value, so `body-drift` can be overwritten by `marker-delete-failed`; operators lose one degradation signal despite docs and route parsing expecting both warnings to be possible.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-ship-resume-output.txt: Address the concern above.

### FINDING_12: Plan manifest omits route/SKILL surfaces for `MARKER_CLEARED`
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `MARKER_CLEARED` propagation touches `design-route.sh`, `skills/design/SKILL.md`, and structure tests, but those surfaces were not listed in the plan file manifest, weakening future plan-to-diff audits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Failed pause-marker deletion is not made sufficiently operator-visible and can hijack later `/design`
- **Reviewer(s)**: dyn-pause-lifecycle-output.txt
- **Severity**: important
- **Concern**: If resume succeeds but deleting the GitHub pause marker fails, the run continues with only machine-oriented output while the stale marker can later force another `/design` invocation down obsolete resume routing, even after the issue has a terminal plan/title.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pause-lifecycle-output.txt: Address the concern above.

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
