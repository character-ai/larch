### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: SIMPLE predicates still rely on mental `design_classification`
- **Reviewer(s)**: dyn-workflow-state-output.txt, dyn-contract-sync-output.txt
- **Severity**: latent
- **Concern**: Step 2a.3 and Step 2a.5 skip prose still key off an unqualified orchestrator mental `design_classification == SIMPLE` instead of the shared helper / artifact / marker predicate, reintroducing classification-source divergence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-workflow-state-output.txt: Address the concern above.
  - From dyn-contract-sync-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_15: Step 2a.5 marker-only branch does not fail fast on marker write failure
- **Reviewer(s)**: dyn-shell-guards-output.txt
- **Severity**: latent
- **Concern**: The marker-only `elif` branch lacks the fail-fast pattern used by the full repair branch, so `mkdir` or marker write failure could still allow the fence to proceed toward Step 2b without `.completed/step-2a.5`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-guards-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Duplicated SIMPLE sentinel and FINALIZE shell blocks risk drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: SIMPLE sentinel writes and FINALIZE invocation patterns are duplicated across several SKILL fences and harness copies, making fail-fast ordering, warnings, and normative/test behavior prone to multi-site drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Step 2a entry guard structure test has brittle block-boundary assumptions
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-shell-guards-output.txt
- **Severity**: latent
- **Concern**: `assert_step2a_entry_simple_guard` relies on fragile line ordering / first-`fi` matching, so harmless reformatting or a nested conditional can make the harness validate the wrong region, false-fail, or false-pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From dyn-shell-guards-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Step 2a success-boundary prose is ambiguous for SIMPLE zero-sketch paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Step 2a success-boundary prose still appears to write `step-2a` on zero-sketch paths even though SIMPLE entry already writes `step-2a` and `step-2a.5`, which may confuse orchestrators about whether SIMPLE should reach that boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Classification helper warnings are suppressed
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-shell-guards-output.txt
- **Severity**: nit
- **Concern**: Step 2a entry and Step 2a.5 repair fences call `read-design-classification.sh` with `2>/dev/null`, hiding the helper’s default-to-HARD warnings when `run-params.json` is missing or malformed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From dyn-shell-guards-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Step 3b FINALIZE fail-closed coverage is incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Tests and structure pins cover Step 4 FINALIZE handling more thoroughly than the fresh-run Step 3b completion boundary, so regressions in Step 3b `set +e` / `_finalize_rc` / non-zero exit behavior may slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

