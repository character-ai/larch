### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: present-but-empty invariants are misclassified as dropped
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-arch-knowledge
- **Severity**: major
- **Concern**: A blank `ARCHITECTURAL_INVARIANTS.md` still falls through to `OUTCOME_DROPPED`, so Step 8 can stall even though empty-present invariants should be a clean no-op.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-arch-knowledge: Before the final `else`, classify empty-present results as `OUTCOME_CLEAN` with `reason=REASON_INVARIANTS_EMPTY` and `assessment_kind="clean"`; add a regression test that `_invariants_gate_before_pr()` on a present-but-empty `ARCHITECTURAL_INVARIANTS.md` writes a validator-clean sidecar and does not stall.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: invariant ship-outcome cutover still reuses the guideline version gate
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness
- **Severity**: major
- **Concern**: The invariant ship-outcome version gate is still pegged to the guideline cutover, so older runs can be treated as missing-current instead of informational when invariant sidecars were not yet produced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_5: invariant renderers still miscount violations
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-testing
- **Severity**: minor
- **Concern**: Invariant rows in `skills/fluff-analysis/scripts/fluff-analysis.py` still use guideline counters, so violation assessments can be rendered as zero-deviation or zero-count entries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (0 YES)

### FINDING_7: pre-PR invariant repairs can loop without a cap
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The pre-PR invariant-violation repair path has no bounded attempt cap, so repeated failures can loop without an exhaustion bail-out.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_16: run-logs docs still conflate guideline and invariant cutovers
- **Reviewer(s)**: dyn-dyn-arch-knowledge
- **Severity**: minor
- **Concern**: The `docs/run-logs.md` outcome docs still document cutover with only the guideline constant, and the design section still describes fluff-analysis coverage as guideline-only, so the invariant docs trail is incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-arch-knowledge: Document both cutover constants and both fluff-analysis scans, or add a short shared note that they are separate config tokens today but must stay documented together.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

