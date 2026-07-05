### FINDING_4: Conditional Outcome append can duplicate the new bullet
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Concern**: The plan adds an unconditional Outcome bullet but never removes the existing conditional Outcome append, so several non-success paths can emit duplicate or conflicting Outcome bullets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In the pr_body.py step, remove the conditional Outcome block entirely and keep one unconditional first bullet: - **Outcome**: {_map_outcome_display(outcome)}


### FINDING_5: Flush test still only guards lowercase stalled
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: The flush pre-recovery test still asserts against lowercase stalled only, so it can miss cases where the rendered outcome bullet becomes STALLED or fails to become DONE after recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add an explicit plan step for this test: stall phase expects `- **Outcome**: STALLED`; recovery phase expects `- **Outcome**: DONE` (not only absence of lowercase `stalled`)
  - From Cursor-Requirements: In the same flush test, assert `- **Outcome**: DONE` after recovery and reject both `stalled` and `STALLED` residue in the Outcome bullet


