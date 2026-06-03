### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: `LARCH_CURSOR_RETRY_EMPTY_RESULT` only disables on literal `0`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `LARCH_CURSOR_RETRY_EMPTY_RESULT` only treats literal `0` as disable; values like `false` still enable empty-envelope retries, contrary to typical operator intent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document literal-0 semantics or normalize falsy values to disabled.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: `LARCH_CURSOR_RETRY_EMPTY_RESULT` re-read each auth-loop iteration
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The retry-disable env gate is re-read on each auth-loop iteration though the plan specified env gates are read once—minor contract drift unless env changes mid-loop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Hoist the retry-disable flag to a variable set once before the while loop.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Large inline empty-result diagnostic block in `_launch_cursor`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: A large inline diagnostic block in `_launch_cursor` (approx. lines 1170–1217) hurts readability; future envelope fields risk copy-paste drift from collector KV grammar.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract _cursor_write_empty_result_diag helper beside _cursor_transient_backoff.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Whitespace-only `.result` not treated as empty
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The empty `.result` jq probe does not treat whitespace-only `.result` as empty. Backend may return `result:" "` with exit 0: no retry, no `CURSOR_EMPTY_RESPONSE`, possible silent collector drop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Tighten jq probe or document whitespace-only as out of scope if never seen.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Non-string `.result` not treated as empty
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The jq empty probe does not treat non-string `.result` (e.g. `{}`) as empty. Cursor may return `{"result":{}}`: no retry, no `CURSOR_EMPTY_RESPONSE`; `OUTPUT` may become `"{}"` and pass collectors incorrectly. Applies to in-loop probe and post-loop promotion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Treat non-string .result as empty in both the in-loop probe and post-loop promotion; add a harness fixture.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: No harness for malformed JSON or missing `jq`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No harness covers plan edge cases where malformed JSON or absent `jq` skips empty-result retry; production falls back to legacy no-retry behavior and a jq-guard regression would not be caught by current SL cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add one stub case each for invalid JSON and jq-absent PATH with invocation-count assertions.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: CI shard 2 load from new multi-invocation cases
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Many new multi-invocation cases were added to an already heavy `test-launch-review` shard (`Makefile:test-harnesses-2`). CI may slow or flake under load without functional failures in the new logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Monitor harness duration; split or gate the slowest SL cases if the shard regresses.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

