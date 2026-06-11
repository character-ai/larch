### OOS_1: [OUT_OF_SCOPE] Rich Step 3 ignores voter-slot progress
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Rich Step 3 progress counts plan-review slots only. During voting, `plan-voter-slots.ndjson` and its sidecar may be the active artifacts, but the header can still show plan reviewers as complete and hide voter dispatch progress.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


