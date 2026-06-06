### [rejected] FINDING_11

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_11: Successful restore can lose one warning when both body drift and marker deletion failure occur
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-ship-resume-output.txt
- **Severity**: latent
- **Concern**: The success path emits or stores only one `WARN` value, so `body-drift` can be overwritten by `marker-delete-failed`; operators lose one degradation signal despite docs and route parsing expecting both warnings to be possible.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-ship-resume-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

