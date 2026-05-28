### [rejected] FINDING_15

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_15: Inconsistent heredoc indentation in vendor_verify_empty_tsv launcher stub
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: In `scripts/test-ship-pr.sh`, one `printf 'X\n' >> sentinel-fix.txt` line in the `vendor_verify_empty_tsv` launcher stub has four leading spaces while surrounding heredoc stub commands use zero indentation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Rule 2 misses multibyte regex content split across awk body lines
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `scripts/lint-awk-multibyte-regex.sh` only detects Rule 2 when non-ASCII text and a regex token appear on the same line, so multibyte regex values assigned on one awk body line and consumed by `match()` or similar on another can escape linting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Rule 2 skips double-quoted awk program bodies
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/lint-awk-multibyte-regex.sh` does not treat double-quoted awk program strings as awk body spans, so forms like `awk "BEGIN { match($0, \"—\") }"` can avoid Rule 2 detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Generic heredoc mode creates a full blind spot for embedded awk
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Generic heredoc handling in `scripts/lint-awk-multibyte-regex.sh` skips all body-line scanning, so embedded awk invocations or `awk -v` content inside non-awk heredocs are invisible to Rule 1 and Rule 2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Default ship-pr test launcher now commits in too many scenarios
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/test-ship-pr.sh` changed default `write_stubs` launchers to auto-commit on every `make_repo`, which may affect unlisted test cases that assumed a no-commit launcher and could alter check counts, stall behavior, or exit paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Inner-loop fix tests may have stale assumptions after launcher commit behavior changed
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Inner-loop fix cases in `scripts/test-ship-pr.sh` still use the default launcher, so launcher pre-commits before `_stage_and_push` may desync expected `run-relevant-checks` invocation counts from documented exhaustion behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_8: Test shard growth may pressure CI wall time
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The enlarged `test-harnesses-5` and `test-ship-pr-fix-loop` coverage may approach timeout under CI load if shard wall time regresses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_9: Breadcrumb wording does not match HEAD-based bail logic
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `scripts/ship-pr.sh` reports “no commits” even when `refresh-run-logs` may have advanced HEAD, making operator-facing breadcrumbs disagree with the actual HEAD-based logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

