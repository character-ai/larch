### FINDING_19: [OUT_OF_SCOPE] Symlink enumeration differs from plan wording
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `design-log-publish.sh` finds symlinks and rejects them during validation rather than excluding them up front, which is not a functional gap but differs from the plan sketch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected


### FINDING_3: [OUT_OF_SCOPE] Parser-based vote counting lacks parity with legacy vote extraction
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan-review tally now uses parser-derived votes while other paths still rely on `vote_for_id`; without systematic parity fixtures, edge-case voter lines can produce different accepted/rejected results, TSV values, or `/design` versus `/review` behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_6: [OUT_OF_SCOPE] Code-review tally does not accept main-agent-vote-required
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `tally-code-votes.sh` only accepts the older result labels, so a future zero-eligible code-review path returning `main-agent-vote-required` would abort instead of handling the result.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_7: [OUT_OF_SCOPE] Failed tally can leave a misleading header-only TSV
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `tally-plan-review.sh` resets `findings-classification.tsv` before successful completion, so abort paths can leave or publish a header-only TSV that consumers may treat as a valid empty/zero-finding result.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


