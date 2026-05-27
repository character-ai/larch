### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Review cap can approve against stale external artifacts after plan edits
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: After the review cap is reached, Discuss-further can change the plan while stale panel artifacts still gate approval, allowing approval without fresh external review of the edited plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Sourcing cap env file creates same-UID shell injection risk
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `skills/design/SKILL.md` sources `.step3-review-cap.env` from `DESIGN_TMPDIR`, allowing a same-UID writer to inject shell code before orchestration reads the values.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Failed panels consume review cap without usable findings
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `panel-failed` persists the review-round count, so repeated dispatch failures can exhaust the SIMPLE/HARD cap without producing review findings or voting output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_9: SIMPLE tier external-review trust boundary is underdocumented
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Replacing TRIVIAL quick mode with SIMPLE can send plans and context to external Codex/Cursor reviewers, while operators migrating from `--trivial` may still expect Claude-only review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

