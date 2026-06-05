# Review Round 3

- Mode: `diff`
- 11 accepted, 10 rejected (9 exonerated)

## Accepted Findings

### FINDING_17: Gate C re-run review routing can skip Step 3b completion boundary
- **Reviewer(s)**: dyn-routing-output.txt
- **Severity**: important
- **Concern**: The Gate C re-run review option names the review steps but not the mandatory Step 3b completion boundary and Step 4 return path, so an orchestrator could re-enter Gate C without convergence FINALIZE.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-routing-output.txt: Address the concern above.


### FINDING_18: Gate C discuss-further re-entry tail omits Step 3b boundary
- **Reviewer(s)**: dyn-routing-output.txt
- **Severity**: important
- **Concern**: The Gate C discuss-further path says eventual re-review proceeds to Step 4/4b without spelling out Step 3.6, Step 3b, and the Step 3b completion boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-routing-output.txt: Address the concern above.


### FINDING_2: Step 2a.2 marker-only skip can bypass sentinel repair and sketch work
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-resume-output.txt, dyn-shell-fences-output.txt
- **Severity**: important
- **Concern**: Step 2a.2 can skip directly to Step 2b when completion markers exist even if SIMPLE sentinel artifacts are missing, stale, or corrupt. This can bypass the Step 2a.5 repair fence and proceed with bad synthesis inputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-resume-output.txt, dyn-shell-fences-output.txt: Address the concern above.


### FINDING_22: Step 2a.2 can mistake HARD zero-sketch sentinels for SIMPLE entry completion
- **Reviewer(s)**: dyn-shell-fences-output.txt
- **Severity**: important
- **Concern**: Step 2a.2 treats bare sentinel presence as proof the SIMPLE entry fence completed, but the HARD zero-sketch degraded path can write the same sentinel before the Step 2a success marker, causing resume/registry inconsistency.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-fences-output.txt: Address the concern above.


### FINDING_26: Structure test does not prove SIMPLE sentinel writes are inside guard
- **Reviewer(s)**: dyn-harness-output.txt
- **Severity**: latent
- **Concern**: `assert_step2a_entry_simple_guard` checks marker writes inside the SIMPLE block but does not assert all three sentinel artifact writes are before the closing `fi`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-output.txt: Address the concern above.


### FINDING_29: Gate-B-bypass route scan excludes Step 3.5 body
- **Reviewer(s)**: dyn-harness-output.txt
- **Severity**: latent
- **Concern**: The Gate-B-bypass route scan stops before the Step 3.5 region, so unsafe bypass routing added inside Step 3.5 could evade the guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-output.txt: Address the concern above.


### FINDING_3: Step 2a classification/artifact skip contract is inconsistent
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Step 2a prose and skip logic mix artifact/marker checks with mental or run-param classification. SIMPLE resumes without entry-fence artifacts may launch HARD sketch paths, while other prose suggests classification alone is enough to skip.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_4: Routing-guard documentation undercounts scanned files
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-design-structure.md` does not list every routing surface scanned by the implementation, so contributors may not know edits to files like `plan-review.md` or `run-step3-review.md` are guarded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_7: Plan inventory omits touched routing docs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `plan-review.md` and `collaborative-sketches.md` were updated but not listed in the plan file inventory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_8: Structure test misses required FINALIZE repair warning
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `assert_step3b_finalize_boundary` verifies exit-on-FINALIZE-failure but not the required repair warning text, so CI could pass while operators lose the primary failure breadcrumb.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_9: Pause/resume tests do not execute Step 3b FINALIZE boundary
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-resume-output.txt
- **Severity**: important
- **Concern**: Gate-B-bypass and fresh-run pause/resume fixtures assert resume state but do not execute the Step 3b completion-boundary fence or verify FINALIZE success/failure artifacts and marker behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-resume-output.txt: Address the concern above.


