### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Success path does not assert exactly eight stdout KV lines
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Harness success paths do not assert exactly eight stdout KV lines or one occurrence per contract key on exit 0. Extra stdout lines could confuse orchestrator KV parsing without failing tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert line count 8 and one occurrence per contract key on exit 0.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: `POSITIONAL_KIND=none` does not gate before session-setup / `gh issue view`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `/design` with only flags or empty argv yields `POSITIONAL_KIND=none` but still proceeds to Step 0a session setup and later `gh issue view` with unset/empty `ISSUE_NUMBER` instead of aborting early with an explicit cancel path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Abort before session-setup or define explicit cancel path when POSITIONAL_KIND=none.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: `--run-id` value not validated as log slug at parse time
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `--run-id` accepts arbitrary strings without slug validation. Future wiring of `RUN_ID` to larch-logs paths could allow path traversal or invalid directory names.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Apply larch_log_slug_is_valid at parse time; test ../bad and newline run-id.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Empty sole positional classified as `none`, not `verbal`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: A sole positional argument that is an empty string (`parse-design-argv.sh ""`) is classified as `POSITIONAL_KIND=none` because `[ -z "$first_positional" ]` runs before the verbal branch. The “non-empty non-numeric → verbal” rule never applies to an empty first token.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: If empty verbal tails matter, treat `first_positional` present-but-empty as `verbal` with `POSITIONAL_VALUE=`; otherwise document that empty argv tokens collapse to `none`.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Success path does not fail-closed when expected KVs are missing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: On `_argv_rc=0`, the Step 0-pre fence does not assert that all eight success KVs were present. Truncated stdout or missing keys leave defaults (`hard_requested=false`, `POSITIONAL_KIND=none`, etc.) and `/design` continues with wrong flags and positional kind.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: After parsing, require non-empty `POSITIONAL_KIND` and that `HARD_REQUESTED` (and optionally all five `*_REQUESTED` keys) appeared in `_argv_out` before Step 0a.
  - From cursor-specialist-edge-cases-output.txt: Fail closed unless POSITIONAL_KIND is valid and all expected KVs were parsed.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

