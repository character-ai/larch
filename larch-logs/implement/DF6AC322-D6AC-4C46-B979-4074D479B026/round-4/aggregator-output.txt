### FINDING_1: Dynamic Codex log allow uses forbidden catch-all suffix glob
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-fd-routing-output.txt, dyn-state-kv-output.txt, dyn-artifact-globs-output.txt, dyn-pr-base-output.txt
- **Severity**: important
- **Concern**: `scripts/larch-log.sh` allows `dyn-*-codex-output-*.txt` and sidecars despite the plan/docs requiring narrow unphased/phase/optional retry shapes. This widens committed run-log surface and makes prompt/telemetry exclusion depend on deny ordering. The nearby comment/docs also misleadingly claim no catch-all dependency.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-fd-routing-output.txt, dyn-state-kv-output.txt, dyn-artifact-globs-output.txt, dyn-pr-base-output.txt: Address the concern above.

### FINDING_2: Dynamic Codex regression pin requires the forbidden catch-all
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-state-kv-output.txt, dyn-artifact-globs-output.txt, dyn-pr-base-output.txt
- **Severity**: important
- **Concern**: `scripts/test-larch-log.sh` uses a broken `dyn_catchall` detector that does not match `dyn-*-codex-output-*.txt`, while also treating that forbidden glob as the required allow line. CI can therefore pass with the exact catch-all the plan intended to prevent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-state-kv-output.txt, dyn-artifact-globs-output.txt, dyn-pr-base-output.txt: Address the concern above.

### FINDING_3: Retry dynamic Codex fixture is tested without a production producer
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-state-kv-output.txt
- **Severity**: important
- **Concern**: `scripts/test-larch-log-write-round.sh` and related assertions include `dyn-*-codex-output-retry*.txt` even though reviewers found no runtime producer. The tests currently validate retry inclusion via the broad catch-all rather than a real, explicit contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-state-kv-output.txt: Address the concern above.

### FINDING_4: Deny/allow ordering invariants are fragile or under-documented
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Sensitive prompt/telemetry denials and static specialist denials depend on case-arm ordering, but the ordering rationale is unclear after reordering. Future edits could place broad allows or static denies before sensitive sidecar denials and change what gets retained.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Branch mixes unrelated dynamic-log and Python ship changes
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The branch combines dynamic Codex log contract work with unrelated Python ship/finalize/test changes, increasing review burden and making CI failures harder to attribute.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Python ship cutover security review remains pending
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The documented Phase 7 security review for the Python ship path has not been completed, leaving possible trust-boundary gaps outside the larch-log artifact-policy scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] `shell_unquote_simple` handles only single-quoted state values
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/refresh-run-logs.sh` may parse double-quoted or complex escaped finalize-state values incorrectly if such values are introduced later.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: Python ship contract JSON can miss captured stdout under inherited fd 3
- **Reviewer(s)**: dyn-fd-routing-output.txt
- **Severity**: important
- **Concern**: When `python/ship.py` runs under a quiet parent with inherited fd 3, contract output can be written to the inherited fd instead of the orchestrator-captured stdout stream, leaving Step 8+ without parseable JSON.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-fd-routing-output.txt: Address the concern above.

### FINDING_9: Python ship skips contract fallback for existing internal errors
- **Reviewer(s)**: dyn-fd-routing-output.txt
- **Severity**: important
- **Concern**: If the primary contract-stream write fails while the result is already `INTERNAL_ERROR`, `emit_result()` does not attempt the fallback path, so the orchestrator can receive no parseable contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-fd-routing-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Breadcrumb fd 4 write failures can drop messages silently
- **Reviewer(s)**: dyn-fd-routing-output.txt
- **Severity**: latent
- **Concern**: `BreadcrumbWriter.emit()` marks breadcrumbs routed even when fd 4 write fails, preventing stderr fallback when quiet routing is miswired.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-fd-routing-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] Pre-existing broad output allow already covered unphased dynamic Codex output
- **Reviewer(s)**: dyn-state-kv-output.txt
- **Severity**: nit
- **Concern**: The prior broad `*-output-*.txt` allow already included unphased `dyn-*-codex-output.txt`; the gap was documentation/regression coverage rather than a live exclusion bug.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-kv-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Phased dynamic Codex fixtures may be forward-looking
- **Reviewer(s)**: dyn-state-kv-output.txt
- **Severity**: nit
- **Concern**: Current dispatch wiring appears to emit unphased dynamic Codex basenames, so phased fixtures/docs may be forward-looking unless another producer exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-kv-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] No concrete finalize-state quoting incompatibility found
- **Reviewer(s)**: dyn-state-kv-output.txt
- **Severity**: nit
- **Concern**: Python/bash finalize-state quoting changes appeared internally consistent for normal keys; no concrete incompatibility was identified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-kv-output.txt: Address the concern above.

### FINDING_14: Python ship loop counters reset across orchestrator re-entry
- **Reviewer(s)**: dyn-ship-cutover-output.txt
- **Severity**: important
- **Concern**: `python/ship.py` cold-starts iteration/rebase/fix/retry counters instead of hydrating them from `ship-pr-state.sh`, so repeated Step 8+ re-entry can bypass cumulative merge-loop and retry budgets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-cutover-output.txt: Address the concern above.

### FINDING_15: Stall recovery still dispatches bash ship path under Python ship cutover
- **Reviewer(s)**: dyn-ship-cutover-output.txt
- **Severity**: important
- **Concern**: Stall recovery documentation/scripts still hard-require `scripts/ship-pr.sh`, so a Python-path stall can resume through the bash driver and lose Python-specific JSON routing and state semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-cutover-output.txt: Address the concern above.

### FINDING_16: Stall clearing is asymmetric across ship and finalize state
- **Reviewer(s)**: dyn-ship-cutover-output.txt
- **Severity**: important
- **Concern**: Recovery clears stall state only in `ship-pr-state.sh`, while `restore-finalize-state.sh` can preserve stale `finalize-state.sh` stall metadata and resurrect a cleared stall during teardown.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-cutover-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Dynamic Codex catch-all also violates the plan from ship-cutover review
- **Reviewer(s)**: dyn-ship-cutover-output.txt
- **Severity**: latent
- **Concern**: The ship-cutover reviewer independently flagged the same `dyn-*-codex-output-*.txt` catch-all as outside that review’s scope but contrary to the attached plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-cutover-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Finalize-state merged writer uses sorted key order
- **Reviewer(s)**: dyn-ship-cutover-output.txt
- **Severity**: nit
- **Concern**: `write_finalize_state_merged()` emits sorted keys instead of the canonical finalize-state key ordering, creating multiple on-disk shapes for the same contract file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-cutover-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] Pre-existing broad sidecar globs can include vote-prompt-shaped sidecars
- **Reviewer(s)**: dyn-artifact-globs-output.txt
- **Severity**: latent
- **Concern**: Existing broad sidecar allows may retain `.meta`/`.json` siblings for vote-prompt-shaped basenames because the `*-vote-prompt.txt` deny only covers the `.txt` basename.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-globs-output.txt: Address the concern above.

### FINDING_20: Python ship hard-codes PR base to `main`
- **Reviewer(s)**: dyn-pr-base-output.txt
- **Severity**: important
- **Concern**: `python/ship.py` now passes `base="main"` into PR creation, diverging from the bash path’s default-branch detection and breaking repos whose default branch is not `main`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pr-base-output.txt: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] Existing open PRs keep their current base
- **Reviewer(s)**: dyn-pr-base-output.txt
- **Severity**: latent
- **Concern**: `python/pr.py` reuses the base of an existing open PR and does not correct a previously mis-based PR; reviewer notes this matches bash behavior and was not introduced by the current change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pr-base-output.txt: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] Python OOS/resume re-entry restarts full driver
- **Reviewer(s)**: dyn-pr-base-output.txt
- **Severity**: latent
- **Concern**: Python ship resume re-invocations restart from checks rather than resuming from persisted `PHASE`, causing extra latency and possible duplicate side effects if phases are not idempotent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pr-base-output.txt: Address the concern above.
