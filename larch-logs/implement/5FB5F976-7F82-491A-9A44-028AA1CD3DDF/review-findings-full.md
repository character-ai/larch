### FINDING_1: panel [code-review/accepted]

## **Important** correctness — `skills/implement/SKILL.md:1389-1393`, `skills/review-and-fix/scripts/review-and-fix.sh:728-801`: the new `exonerated_count` / `neutral_count` fields are not part of the final `/implement` Step 5 contract. `review-and-fix.sh` only passes the current round’s exonerated/neutral counts to `flush_review_batches`, while the skill’s final tally instructions still read only `accepted_count`, `rejected_count`, and `rounds_completed` and call `write-tally.sh` without `--exonerated` or `--neutral`. Concrete scenario: round 1 has one neutral finding and one accepted finding, the accepted fix triggers round 2, and round 2 has no neutral findings; the final `code-review-tally.json` reports `neutral_count: 0` even though the session had one neutral finding. Add exonerated/neutral totals to `review-and-fix-summary.json`, accumulate them like accepted/rejected, emit them from `review-and-fix.sh`, and update the Step 5 instructions to pass those totals into `write-tally.sh`.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** correctness — `skills/implement/SKILL.md:1389-1393`, `skills/review-and-fix/scripts/review-and-fix.sh:728-801`: the new `exonerated_count` / `neutral_count` fields are not part of the final `/implement` Step 5 contract. `review-and-fix.sh` only passes the current round’s exonerated/neutral counts to `flush_review_batches`, while the skill’s final tally instructions still read only `accepted_count`, `rejected_count`, and `rounds_completed` and call `write-tally.sh` without `--exonerated` or `--neutral`. Concrete scenario: round 1 has one neutral finding and one accepted finding, the accepted fix triggers round 2, and round 2 has no neutral findings; the final `code-review-tally.json` reports `neutral_count: 0` even though the session had one neutral finding. Add exonerated/neutral totals to `review-and-fix-summary.json`, accumulate them like accepted/rejected, emit them from `review-and-fix.sh`, and update the Step 5 instructions to pass those totals into `write-tally.sh`.
- **Suggested revision**: Address the concern above.

### FINDING_11: panel [code-review/accepted]

## correctness: scripts/implement-finalize.sh:464-492

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] postbump larch-log commit runs even when version-bump-reasoning write failed Commit can land without the reasoning batch the operator thinks failed write would block Commit only when write succeeded or skip commit on write failure
- **Suggested revision**: Address the concern above.

### FINDING_15: panel [code-review/accepted]

## correctness: skills/review/scripts/tally-code-votes.sh:164-188

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Non-accepted in-scope branch lacks default case for unexpected classify_result. Unknown result drops file output while still emitting FINDING_*_ACCEPTED=false; silent tally/manifest skew vs prior behavior. Add *) fallback matching old append-to-rejected behavior or hard-fail with diagnostic.
- **Suggested revision**: Address the concern above.

### FINDING_2: panel [code-review/accepted]

## **Important** security — `scripts/redact-tmpdir-paths.sh:13-20`, `scripts/redact-tmpdir-paths.md:21-24`: the new `/Users/<name>/<repo>/` redaction misses JSON-escaped newline boundaries, unlike the existing tmpdir expressions. I verified `{"body":"first\\n/Users/alice/larch3/scripts/foo.sh"}` passes through unchanged, while a plain-line `/Users/alice/larch3/scripts/foo.sh` is redacted. This leaks operator-local repo paths in JSON log payloads where markdown bodies are embedded with `\n` escapes. Add a `(\n)`-style escaped-newline sed expression for `/Users/<name>/<repo>/` paths and cover it in `scripts/test-redact-tmpdir-paths.sh`.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** security — `scripts/redact-tmpdir-paths.sh:13-20`, `scripts/redact-tmpdir-paths.md:21-24`: the new `/Users/<name>/<repo>/` redaction misses JSON-escaped newline boundaries, unlike the existing tmpdir expressions. I verified `{"body":"first\\n/Users/alice/larch3/scripts/foo.sh"}` passes through unchanged, while a plain-line `/Users/alice/larch3/scripts/foo.sh` is redacted. This leaks operator-local repo paths in JSON log payloads where markdown bodies are embedded with `\n` escapes. Add a `(\n)`-style escaped-newline sed expression for `/Users/<name>/<repo>/` paths and cover it in `scripts/test-redact-tmpdir-paths.sh`.
- **Suggested revision**: Address the concern above.

### FINDING_20: panel [code-review/accepted]

## risk-integration: scripts/test-write-tally.sh:78-85

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] No assertions on exonerated_count/neutral_count in written code-review-tally JSON. compose/write-tally JSON shape can regress without failing tests. Assert jq fields in test-write-tally.sh code-review paths.
- **Suggested revision**: Address the concern above.

### FINDING_21: panel [code-review/accepted]

## risk-integration: skills/review-and-fix/scripts/review-and-fix.md:59-66 skills/review-and-fix/scripts/review-and-fix.sh:781-799

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Contract lists EXONERATED_COUNT and NEUTRAL_COUNT as stdout keys but review-and-fix.sh never emit_kv them Orchestrators parsing review-and-fix stdout never see those keys despite documentation Emit the keys or fix the contract to point at review-core.env
- **Suggested revision**: Address the concern above.

### FINDING_9: panel [code-review/accepted]

## code-quality: scripts/redact-tmpdir-paths.sh:14-18

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] New OPERATOR_REPO_PATH sed not covered by scripts/test-redact-tmpdir-paths.sh. Regression in the new redaction rule ships without harness signal. Add cases to test-redact-tmpdir-paths.sh and extend redact-tmpdir-paths.md harness list per repo convention.
- **Suggested revision**: Address the concern above.

