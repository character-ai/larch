### [rejected] FINDING_1

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_1: tier-4 status merge ranking is inverted
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `tier4_rank` / `merge_tier4_status` can select a less severe tier-4 outcome over a worse one, so final tier-4 status may be misleading or mapped incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: tier-4 file replacement can overwrite plan with weak validation
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: tier-4 file replacement can fully overwrite `plan.txt` after diff tiers fail with only structural/trailer validation, allowing accepted edits or required coverage to be dropped while continuing as `ok-fallback`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: file-replacement extractor accepts ambiguous multiple plan blocks
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: file-replacement extraction keeps the last `## Plan` block with a `diff_lines` trailer, so appended plan blocks can supersede the intended revision.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: git apply --recount can accept miscounted hunks
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: using `git apply --recount` relaxes hunk header integrity and may apply miscounted or ambiguous patches that strict mode would reject.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: tier-4 overwrites earlier raw launcher outputs
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: tier-4 reuses the same launcher output filenames, so corrupt tier 1-3 outputs can be lost from forensic artifacts after fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: post-apply failure can conflict with ok-fallback round summary
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `revise_status=ok-fallback` can coexist with terminal `LOOP_STATUS=emit-plan-failed`, making round summary and Gate B status disagree unless the split is aligned or documented.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: implementation diverges from explicit plan constraint for file replacement
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: the plan required file-replacement `extract_patch` to remain `cp "$output" "$patch"`, but implementation uses `extract_file_replacement_candidate`; this may be justified but needs an approved plan amendment or conditional compliance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: inter-hunk blank-line extraction truncates patches with multiple blank lines
- **Reviewer(s)**: dyn-awk-diff-extraction-output.txt
- **Severity**: nit
- **Concern**: the awk extractor only peeks one line ahead for blank lines between hunks, so two consecutive blank lines can truncate later hunks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-awk-diff-extraction-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_3: stale numbered candidate patches can survive re-extract
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: only the primary `*-candidate.patch` is removed before re-extraction, so stale numbered candidates may still be selected if they pass `git apply --check`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_4: diff-git-only patches are rejected by header validation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `validate_unified_headers` requires `---` / `+++` headers even when a valid `diff --git a/plan.txt b/plan.txt` header is present, causing unnecessary fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_9: python3 dependency in case8d is unguarded
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: case8d requires `python3` without checking availability, so the harness can fail before testing the intended path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

