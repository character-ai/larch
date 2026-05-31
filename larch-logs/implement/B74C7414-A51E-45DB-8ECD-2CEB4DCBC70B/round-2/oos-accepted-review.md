### FINDING_11: [OUT_OF_SCOPE] Harness trust-boundary fixture does not mirror production cache layout
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-step5-flow-output.txt
- **Severity**: latent
- **Concern**: Some harness layouts keep `IMPLEMENT_TMPDIR` under the work tree, so they do not exercise the production expectation that snapshots live outside the repo / all Codex workspace grants.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-step5-flow-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_13: [OUT_OF_SCOPE] Step5 loop coupling should be documented
- **Reviewer(s)**: dyn-bash32-output.txt
- **Severity**: nit
- **Concern**: `review-implement-step5-loop.sh` now depends on symbols defined by `review-and-fix.sh`; production ordering is acceptable, but standalone sourcing expectations should stay explicit in the Step 5 loop documentation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash32-output.txt: Address the concern above.

Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated


### FINDING_5: [OUT_OF_SCOPE] Duplicated carryover head-load logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Two residue functions duplicate carryover head-loading logic, creating maintenance noise for future carryover behavior changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_8: [OUT_OF_SCOPE] Pre-existing `step5-starting-round` CI blind spot
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The whole `step5-starting-round` section was already absent from CI before this branch, so the new relocation tests amplify a pre-existing harness coverage gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral


### FINDING_9: [OUT_OF_SCOPE] Relocation still assumes Codex sandbox confinement
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-snapshot-tamper-output.txt, dyn-bash32-output.txt
- **Severity**: latent
- **Concern**: The relocation relies on Codex `--full-auto` being confined to declared workspace/add-dir roots. If Codex can write outside those roots or traverse into sibling snapshot directories, relocation alone is insufficient; follow-up sandbox hardening or read-only snapshot defenses may be needed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-snapshot-tamper-output.txt, dyn-bash32-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


