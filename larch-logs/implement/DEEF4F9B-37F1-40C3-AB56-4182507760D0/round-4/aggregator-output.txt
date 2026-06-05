Positive/no-risk observations were not promoted to findings.

### FINDING_1: [OUT_OF_SCOPE] Gate B routing prose omits the Step 3b completion boundary before Step 4
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-contract-sync-output.txt
- **Severity**: important
- **Concern**: Gate B / Gate-B-bypass prose in `approval-gates.md` can still be read as routing directly through Step 3b to Step 4 without explicitly requiring the Step 3b completion boundary that runs FINALIZE and writes `step-3b`; stale harness pins may preserve that ambiguity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From dyn-contract-sync-output.txt: Address the concern above.

### FINDING_2: Duplicated SIMPLE sentinel and FINALIZE shell blocks risk drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: SIMPLE sentinel writes and FINALIZE invocation patterns are duplicated across several SKILL fences and harness copies, making fail-fast ordering, warnings, and normative/test behavior prone to multi-site drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Pause/resume tests miss the marker-only Step 2a.5 repair path
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-compat-output.txt
- **Severity**: important
- **Concern**: Existing legacy SIMPLE pause fixtures exercise full artifact repair, but not the branch where valid SIMPLE artifacts and `step-2a` exist while only `step-2a.5` is missing; one reviewer also calls out the missing HARD negative case for the same sentinel layout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-resume-compat-output.txt: Address the concern above.

### FINDING_4: Step 2a entry guard structure test has brittle block-boundary assumptions
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-shell-guards-output.txt
- **Severity**: latent
- **Concern**: `assert_step2a_entry_simple_guard` relies on fragile line ordering / first-`fi` matching, so harmless reformatting or a nested conditional can make the harness validate the wrong region, false-fail, or false-pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From dyn-shell-guards-output.txt: Address the concern above.

### FINDING_5: Step 2a success-boundary prose is ambiguous for SIMPLE zero-sketch paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Step 2a success-boundary prose still appears to write `step-2a` on zero-sketch paths even though SIMPLE entry already writes `step-2a` and `step-2a.5`, which may confuse orchestrators about whether SIMPLE should reach that boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] HARD zero-sketch marker contract is inconsistent
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-workflow-state-output.txt, dyn-contract-sync-output.txt
- **Severity**: latent
- **Concern**: HARD zero-sketch / both-tools-down paths can produce the same sentinel artifacts as SIMPLE without consistently writing `.completed/step-2a` and `.completed/step-2a.5`, while anti-pattern and success-boundary prose imply those markers exist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From dyn-workflow-state-output.txt: Address the concern above.
  - From dyn-contract-sync-output.txt: Address the concern above.

### FINDING_7: Classification helper warnings are suppressed
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-shell-guards-output.txt
- **Severity**: nit
- **Concern**: Step 2a entry and Step 2a.5 repair fences call `read-design-classification.sh` with `2>/dev/null`, hiding the helper’s default-to-HARD warnings when `run-params.json` is missing or malformed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From dyn-shell-guards-output.txt: Address the concern above.

### FINDING_8: Step 3b→Step 4 routing guard has coverage gaps
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-shell-guards-output.txt
- **Severity**: latent
- **Concern**: The structure guard can miss direct Step 3b→Step 4 prose because it does not catch Unicode-arrow forms and does not scan the Step 3.6 slice.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-shell-guards-output.txt: Address the concern above.

### FINDING_9: Step 3b FINALIZE fail-closed coverage is incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Tests and structure pins cover Step 4 FINALIZE handling more thoroughly than the fresh-run Step 3b completion boundary, so regressions in Step 3b `set +e` / `_finalize_rc` / non-zero exit behavior may slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Collaborative sketches doc has no drift guard
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `docs/collaborative-sketches.md` was updated for Step 2a entry-fence semantics but is outside the plan file list and harness scan surfaces, so future drift from SKILL.md / sketch-launch.md may go untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] Step 4 compatibility guard trusts `.completed/finalize` without artifact validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: A local actor or corrupt session tmpdir could create `.completed/finalize` while required artifacts are absent, causing Step 4 compatibility FINALIZE to be skipped under the existing idempotency model.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_12: Corrupt SIMPLE sessions can bypass repair or launch regular sketch work
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-workflow-state-output.txt
- **Severity**: important
- **Concern**: SIMPLE routing is inconsistent when classification says SIMPLE but sentinel/marker package checks fail: prose can route directly to Step 2b or fall through to regular sketch launch before the Step 2a.5 repair block runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-workflow-state-output.txt: Address the concern above.

### FINDING_13: SIMPLE predicates still rely on mental `design_classification`
- **Reviewer(s)**: dyn-workflow-state-output.txt, dyn-contract-sync-output.txt
- **Severity**: latent
- **Concern**: Step 2a.3 and Step 2a.5 skip prose still key off an unqualified orchestrator mental `design_classification == SIMPLE` instead of the shared helper / artifact / marker predicate, reintroducing classification-source divergence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-workflow-state-output.txt: Address the concern above.
  - From dyn-contract-sync-output.txt: Address the concern above.

### FINDING_14: Step 2a.5 SIMPLE repair can clobber non-sentinel synthesis artifacts
- **Reviewer(s)**: dyn-resume-compat-output.txt
- **Severity**: important
- **Concern**: If `run-params.json` is corrupt or restored as SIMPLE for a session that already has real sketch synthesis, the Step 2a.5 repair branch can overwrite non-empty, non-sentinel artifacts before detecting the mismatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-compat-output.txt: Address the concern above.

### FINDING_15: Step 2a.5 marker-only branch does not fail fast on marker write failure
- **Reviewer(s)**: dyn-shell-guards-output.txt
- **Severity**: latent
- **Concern**: The marker-only `elif` branch lacks the fail-fast pattern used by the full repair branch, so `mkdir` or marker write failure could still allow the fence to proceed toward Step 2b without `.completed/step-2a.5`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-guards-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Assessor prose still says “continue to Step 3b” without boundary wording
- **Reviewer(s)**: dyn-contract-sync-output.txt
- **Severity**: nit
- **Concern**: `skills/design/references/assessor.md` contains older “continue to Step 3b” wording without naming the completion boundary, although risk is lower because the path enters the Step 3b region where FINALIZE is now mandatory before Step 4.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-sync-output.txt: Address the concern above.
