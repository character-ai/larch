### FINDING_1: Duplicate SIMPLE sentinel write fences can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: The SIMPLE sentinel writes are duplicated in the Step 2a entry fence and Step 2a.5 repair fence, creating drift risk if future edits update ordering or filenames in only one place.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Step 2a.2 marker-only skip can bypass sentinel repair and sketch work
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-resume-output.txt, dyn-shell-fences-output.txt
- **Severity**: important
- **Concern**: Step 2a.2 can skip directly to Step 2b when completion markers exist even if SIMPLE sentinel artifacts are missing, stale, or corrupt. This can bypass the Step 2a.5 repair fence and proceed with bad synthesis inputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-resume-output.txt, dyn-shell-fences-output.txt: Address the concern above.

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

### FINDING_5: FINALIZE failure handling is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: FINALIZE failure handling appears in both Step 3b and Step 4 compatibility guards, creating drift risk for warning text or exit behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Duplicate zero-findings routing prose in plan-review
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `plan-review.md` duplicates zero-findings routing prose, so future routing changes require editing repeated long text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

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

### FINDING_10: Routing guard can miss bare Step 3b-to-Step 4 routing on mixed lines
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The routing guard skips whole lines containing the completion-boundary phrase, even if the same line also contains an unsafe bare Step 3b-to-Step 4 route.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: Compatibility tests inline-copy SKILL fence logic
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-harness-output.txt
- **Severity**: latent
- **Concern**: Legacy pause/resume fixtures copy compatibility-fence shell logic instead of sharing or parsing the authoritative SKILL fences, allowing test behavior to drift from runtime prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-harness-output.txt: Address the concern above.

### FINDING_12: Step 4 FINALIZE compatibility guard trusts symlink sentinel
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Step 4 checks `.completed/finalize` with `-f` but does not refuse symlinks, so local tmpdir tampering could bypass artifact validation before Gate C/publish.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Approval-gates bypass prose omits completion boundary
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-harness-output.txt
- **Severity**: nit
- **Concern**: `approval-gates.md` says bypass paths go before Step 3b without naming the Step 3b completion boundary before Step 4, weakening documentation consistency.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-harness-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Pause step inference may drift from FINALIZE sentinel naming
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Pause step inference skips registry step 5 while FINALIZE uses `.completed/finalize`, which could desynchronize future step-5 sentinel changes from FINALIZE idempotency.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Legacy pause/resume paths appear sound
- **Reviewer(s)**: dyn-resume-output.txt, dyn-shell-fences-output.txt
- **Severity**: nit
- **Concern**: Reviewers observed that legacy SIMPLE and FINALIZE compatibility paths appear to repair or fail as intended.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-output.txt, dyn-shell-fences-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Pause-save/load ordering appears consistent with new boundary
- **Reviewer(s)**: dyn-resume-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed that pause-save inference and HARD 3b-to-3.6 remapping remain consistent with the new completion boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-output.txt: Address the concern above.

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

### FINDING_19: Passive-summary auto-continue routing is ambiguous
- **Reviewer(s)**: dyn-routing-output.txt
- **Severity**: latent
- **Concern**: Passive-summary auto-continue lists Step 3b, the completion boundary, and “the next Step 3 entry” ambiguously, which can be read as routing backward instead of forward through Step 4/Gate C.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-routing-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] Assessor references do not forward-declare completion boundary
- **Reviewer(s)**: dyn-routing-output.txt
- **Severity**: nit
- **Concern**: Assessor-related files still say to continue to Step 3b without explicitly declaring the Step 3b completion boundary before Step 4.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-routing-output.txt: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] FINALIZE idempotency is now load-bearing for re-review routing
- **Reviewer(s)**: dyn-routing-output.txt
- **Severity**: latent
- **Concern**: `design-driver.sh` skips FINALIZE when `.completed/finalize` exists; this pre-existing behavior becomes risky if any re-review route fails to hit the Step 3b completion boundary and fresh Step 4 read.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-routing-output.txt: Address the concern above.

### FINDING_22: Step 2a.2 can mistake HARD zero-sketch sentinels for SIMPLE entry completion
- **Reviewer(s)**: dyn-shell-fences-output.txt
- **Severity**: important
- **Concern**: Step 2a.2 treats bare sentinel presence as proof the SIMPLE entry fence completed, but the HARD zero-sketch degraded path can write the same sentinel before the Step 2a success marker, causing resume/registry inconsistency.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-fences-output.txt: Address the concern above.

### FINDING_23: Step 2a.5 marker-only branch lacks shell failure checking
- **Reviewer(s)**: dyn-shell-fences-output.txt
- **Severity**: latent
- **Concern**: The Step 2a.5 marker-only repair branch writes completion markers without `set -e` or explicit status checks, so disk/permission failures may leave the run believing repair succeeded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-fences-output.txt: Address the concern above.

### FINDING_24: SIMPLE guard literal is fragile
- **Reviewer(s)**: dyn-shell-fences-output.txt
- **Severity**: latent
- **Concern**: The SIMPLE guard compares against an unquoted literal pattern in the Step 2a entry and 2a.5 repair fences, which the reviewer flagged as fragile and harness-pinned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-fences-output.txt: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] Routing guard scanned surfaces appear aligned
- **Reviewer(s)**: dyn-shell-fences-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed that the scanned routing surfaces currently align with the folded-boundary design and contain no bare Step 3b-to-Step 4 bypasses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-fences-output.txt: Address the concern above.

### FINDING_26: Structure test does not prove SIMPLE sentinel writes are inside guard
- **Reviewer(s)**: dyn-harness-output.txt
- **Severity**: latent
- **Concern**: `assert_step2a_entry_simple_guard` checks marker writes inside the SIMPLE block but does not assert all three sentinel artifact writes are before the closing `fi`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-output.txt: Address the concern above.

### FINDING_27: New structure-test helpers lack negative self-tests
- **Reviewer(s)**: dyn-harness-output.txt
- **Severity**: latent
- **Concern**: Several new structure-test helpers only have positive pins, so inverted awk logic or broken failure detection could remain green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-output.txt: Address the concern above.

### FINDING_28: Routing guard verb matching can false-positive on substrings
- **Reviewer(s)**: dyn-harness-output.txt
- **Severity**: nit
- **Concern**: The route guard matches `enter` as a bare substring, so words like `re-enter`, `entering`, or `center` may trigger false positives on lines mentioning Step 3b and Step 4.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-output.txt: Address the concern above.

### FINDING_29: Gate-B-bypass route scan excludes Step 3.5 body
- **Reviewer(s)**: dyn-harness-output.txt
- **Severity**: latent
- **Concern**: The Gate-B-bypass route scan stops before the Step 3.5 region, so unsafe bypass routing added inside Step 3.5 could evade the guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-output.txt: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] Step 4 anchor strings diverge in structure test
- **Reviewer(s)**: dyn-harness-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-design-structure.sh` uses two different Step 4 anchor strings, which both match today but could deslice regions after future edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-output.txt: Address the concern above.
