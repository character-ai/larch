### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: Gate B manual mode can degrade to auto-apply without mechanical persisted-state read
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Gate B manual/auto mode resolution relies on prompt memory or readable run-params instead of mechanically re-reading persisted manual intent. On `/design --manual`, jq/write-run-params failure or context loss can cause Gate B to auto-apply accepted findings despite `MANUAL_REQUESTED=true` existing on disk, contradicting argv and SECURITY.md. The normative docs also leave the `--manual` session-env override and precedence chain under-specified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Gate B rollback semantics diverge from the plan
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Gate A re-entry rollback semantics differ from the planned subsequent Gate B adjustment path. After Gate C sends an operator back to Gate A, the current docs require a Step 3 re-run instead of having the next Gate B honor `discussion-round2.md`, which may violate expected rollback behavior unless codified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Blocked-by dependency edge is not evidenced
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The acceptance criteria require a native blocked-by edge from #2667 to #2930, but the branch evidence does not show that dependency being recorded. Without it, #2667 may proceed against stale Gate B contract assumptions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Gate B prose is duplicated across multiple normative surfaces
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Gate B mode and apply-path guidance is duplicated in SKILL Step 3, Step 3.5, approval-gates.md, and SECURITY.md, creating risk that future gate changes update only one surface and leave contradictory operator guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Apply-all body uses inconsistent lowercase “execute”
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: The Apply-all body uses lowercase `execute` for the shared post-apply pipeline while other call sites use `Execute`, creating a minor normative consistency issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Default Gate B auto-apply can merge untrusted accepted findings before per-finding consent
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Default Gate B auto-apply writes all voted-in reviewer findings into `plan.txt` without per-finding operator consent. Malicious or mistaken accepted finding text can influence the plan before Gate C, including later validator dry-runs of plan command blocks. Security guidance should clearly direct high-risk runs to `--manual` and full Gate C review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Auto-apply breadcrumb exposes only truncated concern excerpts
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Gate B auto-apply shows truncated concern excerpts, so operators may not see the full accepted reviewer text before the plan is revised.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

