### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: Multi-candidate extractor exceeds planned scope
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Implementation diverges from the agreed minimal preamble/fence stripping plan by adding a large multi-candidate Awk extractor, increasing review and regression risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: Missing real revise-loop integration test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `ok-fallback` is tested through stub KV injection, but no end-to-end case wires the real revise script through `plan-review-loop.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_17: Live `git apply --recount` may apply wrong boundaries on long lines
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Applying with `--recount` on very long plan lines may let a miscounted patch apply with plausible but incorrect boundaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_18: Tier-4 status ranking conflicts with documented severity
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `merge_tier4_status` ranks `invalid-patch` above `apply-failed`, which may hide the more actionable status and diverge from docs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_19: Tier-4 file replacement drops `## Plan` heading
- **Reviewer(s)**: dyn-awk-extraction-output.txt
- **Severity**: important
- **Concern**: `extract_file_replacement_candidate` treats `## Plan` as an opener but does not include it in the emitted block, so tier-4 can write a structurally invalid plan while reporting `ok-fallback`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-awk-extraction-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_7: Non-winning candidate artifacts remain published
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Failed scratch candidate patch files remain in revise logs and may be published, creating misleading artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

