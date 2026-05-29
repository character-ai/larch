### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Gate A/B direct rewrites lack mechanical trailer enforcement beyond prose
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Operator can skip gate-b snapshot before rewrite; dedup snapshots post-rewrite keys and cannot detect trailers dropped at rewrite time. Needs mechanical pre-`EMIT_PLAN` check against `.gate-b-optional-trailer-keys` on all Gate B paths (and related Gate A discussion rewrites per `approval-gates.md`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Plan byte-stable `check-plan-size.sh` lines 1–90 vs shared lib extraction
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Plan said keep lines 1–90 byte-stable; implementation extracted a shared library instead. Low risk if harness stays green, but reviewers expecting minimal append-only diff may be surprised.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Self-declared diff trailers — honor-system trust boundary
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Self-declared `diff_added` and `mechanical_churn` control hard vs soft diff gating with no independent verification; designers/agents can under-report additions or set `mechanical_churn: true` to bypass Split/Cancel on large estimated diffs while still reaching `/implement`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

