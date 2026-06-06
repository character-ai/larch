### FINDING_1: [OUT_OF_SCOPE] Duplicate skipped-findings security classifier call
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-portability-output.txt
- **Severity**: important
- **Concern**: Skipped-OOS/security routing in `review-and-fix.sh` calls `is_security_block` twice for non-security blocks and includes confusing or unreachable branching. This is inefficient and obscures the classifier failure contract; one source treats it as out-of-scope for portability.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-bash-portability-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_11: [OUT_OF_SCOPE] Review-core stubs cannot test production tally-to-emit chain
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-harness-wiring-output.txt
- **Severity**: latent
- **Concern**: `test-review-core.sh` stubs the production emit path, so production tally-to-emit overwrite bugs must remain covered by dedicated harnesses instead of review-core tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-harness-wiring-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_12: [OUT_OF_SCOPE] Design tally tests lack expanded security-routing fixtures
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Design-path tally integration tests were not updated for expanded security routing forms, leaving design tally regression coverage behind the shared library behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_17: [OUT_OF_SCOPE] Final zero-OOS round can clobber accumulated review OOS mirror
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-oos-pipeline-output.txt
- **Severity**: important
- **Concern**: In multi-round runs, a later round with no accepted/skipped OOS can overwrite the parent `oos-accepted-review.md` with an empty file while durable OOS remain only in `accumulated-oos.md`, making gate input empty.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-oos-pipeline-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_18: [OUT_OF_SCOPE] Design OOS producers still emit legacy headers
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Design-path OOS producers were not normalized, so legacy `FINDING` headers in `oos-accepted-design.md` can still be dropped by counters/gates in mixed design+review runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_19: [OUT_OF_SCOPE] Legacy OOS tag matching is case-sensitive
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Variant casings such as `[out_of_scope]` can bypass normalization paths and still count as zero at the gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_25: [OUT_OF_SCOPE] Normalized temp OOS blocks are not deleted
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: nit
- **Concern**: `tally-code-votes.sh` writes normalized temporary OOS block files and never deletes them. This is harmless for typical rounds and unrelated to the reviewed portability surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


