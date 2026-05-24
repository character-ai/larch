### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: One branch bundles unrelated behavioral changes
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Multiple independent behavioral surfaces ship together (e.g. design plan-size work alongside ship-pr / voter / harness changes), which makes regressions harder to attribute, rollback, bisect, and triage in CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_10: `--plan-file` is not constrained under resolved `DESIGN_TMPDIR`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Callers can aim the helper at arbitrary readable paths; symlinks may escape the session root and leak file-derived counts or headings into the FD3 contract stream.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Sentinel touch after successful `gh` can break idempotency
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The sentinel is touched only after a successful `gh` post; if `gh` succeeds but creating the HOME cache or touching the sentinel fails, a later run can duplicate the upstream tracking comment without an `append-tool-failure` capture for the touch failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_13: SEMANTIC_SOFT_ESTIMATE can re-fire without a session latch
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Gate B or discussion-driven plan re-emits can re-invoke Step 2b.5 and re-trigger semantic soft prompts for the same judgment because nothing persists a once-per-session latch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Empty or whitespace-only plan misclassified as missing-diff-lines
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: An empty plan body surfaces `missing-diff-lines` rather than a clearer empty-or-missing-body status, which misleads debugging.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: `emit_kv` key order in flags.md may not match the script
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Readers or naive line-order parsers may assume a wire contract that does not match `check-plan-size.sh` or the plan’s helper bullet order.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Duplicated YES↔EXONERATE prose
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The same YES↔EXONERATE wording exists in more than one place, so future edits can drift and undermine voting consistency.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: SEMANTIC_SOFT_ESTIMATE is orchestrator-only and untested
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The soft semantic threshold is not covered by CI; genuinely multi-stream plans below the hard threshold may skip the soft-partition UI with no automated signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: rc=2 append-tool-failure instructions are ambiguous about log vs capture
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Orchestrators could misread whether to append from a log file versus in-memory capture and append the wrong payload into `execution-issues.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

