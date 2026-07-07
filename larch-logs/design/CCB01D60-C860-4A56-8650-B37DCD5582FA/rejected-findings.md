### [Plan Review] FINDING_2

### FINDING_2: Step 18 cleanup still uses the retired .bg-wait-active stall marker
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: The Step 18 cleanup reference still describes the fifth stall layer with the old `.bg-wait-active` marker, but abandoned-checks detection is moving to identity-checked bgjob registry rows, so killed self-review legs can miss the intended retry path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: skills/implement/references/step18-cleanup.md. Document the fifth derived signal as identity-checked dead bgjob registry rows for implement-step3-checks and implement-step5-self-review, not .bg-wait-active.
  - From Cursor-Requirements: Add ### UPDATED: skills/implement/references/step18-cleanup.md: replace the fifth-layer .bg-wait-active rule with identity-checked dead bgjob registry rows for implement-step3-checks and implement-step5-self-review, aligned with stall-recovery.md


### [Plan Review] FINDING_5

### FINDING_5: Parallel research lanes need distinct bgjob STEP names
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: The research-phase migration does not pin unique bgjob STEP slugs per lane, so concurrent research starts can share one registry row and corrupt lane ownership.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In research-phase.md and validation-phase.md assign one bgjob STEP per external lane, for example research-arch and research-edge, and require waiting each STEP independently per skills/shared/bgjob-wait.md.


