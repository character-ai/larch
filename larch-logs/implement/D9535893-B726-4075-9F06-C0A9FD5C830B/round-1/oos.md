### FINDING_3: [OUT_OF_SCOPE] Step 5 tests still miss failure/replay result-env parity
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-bgjob-kv
- **Severity**: minor
- **Concern**: The Step 5 test coverage still mostly pins the happy-path completion envelope. Failure branches such as preflight-failed, stall, and normalize replay are not all asserting `.step5-review-result.env`, so a future regression could still pass CI while the bgjob contract breaks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
  - From dyn-dyn-bgjob-kv: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_4: [OUT_OF_SCOPE] plan/file-scope drift around the review chunk
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-bgjob-kv
- **Severity**: minor
- **Concern**: The surrounding plan and acceptance text names modules that this branch does not actually change, so the review scope reads broader than the code motion. That is documentation drift rather than a runtime regression, but it can misstate what was validated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-bgjob-kv: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_5: [OUT_OF_SCOPE] Step 3 merge-file tests assert only a subset of required keys
- **Reviewer(s)**: codex-specialist-testing, dyn-dyn-bgjob-kv
- **Severity**: minor
- **Concern**: The Step 3 merge-file test does not pin the full envelope shape, so keys such as `NEXT_ACTION` and the other routing fields could disappear without breaking CI. A fuller equality check or explicit required-key assertion is still missing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.
  - From dyn-dyn-bgjob-kv: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

