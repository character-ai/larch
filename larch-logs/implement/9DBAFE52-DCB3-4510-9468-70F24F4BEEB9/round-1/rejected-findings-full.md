### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Original issue prose vs revised landed scope (launcher / subprocess / trust boundary)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Original issue text promised no behavior change and no Voter1 launcher change while the branch follows a revised plan (subprocess voter, aggregator mode), so operators trusting the original issue may underestimate runtime deltas and ballot shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: `test-plan-review-loop.md` implies fuller harness than smoke tests deliver
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Documentation admits smoke-only coverage but structural pins can still imply deep loop coverage to casual readers; clarify that the scenario harness is follow-up (or align pins/messages).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_14: Plan input mode in `aggregate-findings.sh` skips merged-output severity validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Plan input mode skips merged-output severity validation that code mode still enforces, weakening automatic detection of malformed aggregator merges for `/design` (e.g. missing severity on merged blocks can pass where code mode fails closed).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: `emit_loop_kvs` overloads aggregator/tally KVs with synthetic values when subsystems did not run
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Synthetic `AGGREGATOR_STATUS` / `TALLY_PLAN_REVIEW_STATUS` values when neither subsystem ran can mislead telemetry or future consumers that assume tally KVs always reflect `tally-plan-review.sh` output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: `design-driver.md` lacks explicit backward-compat note for `ACTION=TALLY`
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Missing explicit note that `ACTION=TALLY` remains for backward-compatible older callers, so out-of-tree or legacy SKILL snapshots lose rationale for keeping the TALLY arm.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_6: Non-OK collect statuses skip TSV and prose fallback before discarding reviewer output
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Non-OK collect statuses (e.g. NOT_SUBSTANTIVE, EMPTY_OUTPUT) never run TSV or prose fallback extraction, so readable narrative findings can be logged as collector failures yet contribute zero ballot blocks, silently shrinking the review surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_7: Embedded TSV parser Python uses confusing / dead `fi`/`oi` assignments
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Module-level or pre-`main()` assignments use names resembling Bash `fi` and look like dead numbering, which risks mis-read control flow and wrong mental model around dedup renumbering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_8: Branch mixes driver, harness, logs, version/changelog (review / bisect coupling)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: The branch merges the #2676 driver with harness work, version/changelog bumps, and `larch-logs` flushes, making bisect and failure attribution harder because failures may not map cleanly to plan-review changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

