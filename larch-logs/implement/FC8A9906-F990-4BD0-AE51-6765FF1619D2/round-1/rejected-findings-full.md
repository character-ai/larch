### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Passive-summary auto-continue still runs Step 3.6–4 before Gate C (`approval-gates.md:100`)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Passive-summary auto-continue removes Gate B discussion exit but still mandates Step 3.6–4 before Gate C. On HARD `converged|cap-hit`, an operator who would have picked Switch to discussion mode now runs the assessor first; worse-majority can surface Continue/Stop (or Stop cancels) instead of Gate A discussion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document the tradeoff in passive-summary prose or restore a documented pre-3.6 discussion escape (e.g. --manual).


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

