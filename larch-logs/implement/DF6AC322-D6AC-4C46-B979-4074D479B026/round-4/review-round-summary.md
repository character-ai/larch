# Review Round 4

- Mode: `diff`
- 9 accepted, 1 rejected (1 exonerated)

## Accepted Findings

### FINDING_1: Dynamic Codex log allow uses forbidden catch-all suffix glob
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-fd-routing-output.txt, dyn-state-kv-output.txt, dyn-artifact-globs-output.txt, dyn-pr-base-output.txt
- **Severity**: important
- **Concern**: `scripts/larch-log.sh` allows `dyn-*-codex-output-*.txt` and sidecars despite the plan/docs requiring narrow unphased/phase/optional retry shapes. This widens committed run-log surface and makes prompt/telemetry exclusion depend on deny ordering. The nearby comment/docs also misleadingly claim no catch-all dependency.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-fd-routing-output.txt, dyn-state-kv-output.txt, dyn-artifact-globs-output.txt, dyn-pr-base-output.txt: Address the concern above.


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


### FINDING_2: Dynamic Codex regression pin requires the forbidden catch-all
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-state-kv-output.txt, dyn-artifact-globs-output.txt, dyn-pr-base-output.txt
- **Severity**: important
- **Concern**: `scripts/test-larch-log.sh` uses a broken `dyn_catchall` detector that does not match `dyn-*-codex-output-*.txt`, while also treating that forbidden glob as the required allow line. CI can therefore pass with the exact catch-all the plan intended to prevent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-state-kv-output.txt, dyn-artifact-globs-output.txt, dyn-pr-base-output.txt: Address the concern above.


### FINDING_20: Python ship hard-codes PR base to `main`
- **Reviewer(s)**: dyn-pr-base-output.txt
- **Severity**: important
- **Concern**: `python/ship.py` now passes `base="main"` into PR creation, diverging from the bash path’s default-branch detection and breaking repos whose default branch is not `main`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pr-base-output.txt: Address the concern above.


### FINDING_3: Retry dynamic Codex fixture is tested without a production producer
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-state-kv-output.txt
- **Severity**: important
- **Concern**: `scripts/test-larch-log-write-round.sh` and related assertions include `dyn-*-codex-output-retry*.txt` even though reviewers found no runtime producer. The tests currently validate retry inclusion via the broad catch-all rather than a real, explicit contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-state-kv-output.txt: Address the concern above.


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


