### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: Unused write_collect_one_nit helper
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `write_collect_one_nit()` is dead helper code in `skills/design/scripts/test-plan-review-loop.sh`; new tests call `write_collect one_nit` directly, leaving maintainers unclear about the intended helper API.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Duplicated dispatch stub helper
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `write_dispatch_round2_degraded` near-duplicates existing one-slot dispatch helpers, increasing maintenance cost if slot manifest behavior changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Dedup test extracts pipeline with brittle awk/eval
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The section-aware dedup test extracts `_run_post_apply_pipeline` via `awk` and `eval`, which can truncate or fail under harmless function formatting changes and produce false positives or unrelated harness failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Separate important round-2 collect stub duplicates collect modes
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `write_collect_important_round2` duplicates the existing `write_collect` mode pattern instead of extending it, increasing harness duplication without adding capability.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_8: H1 Constraints protection can leak into later H2 sections
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: After a `# Constraints` heading, protection does not clear on later `##` non-Constraints headings, so duplicate lines outside the intended Constraints chapter may remain undeduped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Dedup pipeline test does not exercise full loop post-apply path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Section-aware dedup is tested through an extracted helper rather than a full loop post-apply path, so bugs in emit/validate ordering or snapshot paths may not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

