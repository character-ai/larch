# Review Round 4

- Mode: `diff`
- 7 accepted, 2 rejected (2 neutral)

## Accepted Findings

### FINDING_1: Empty create-issue title reaches gh
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `tracking-issue create-issue --title ""` can reach `gh issue create` instead of failing locally as a usage error before side effects.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_10: Read with prompt success path lacks coverage
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The successful `read --issue --prompt` path lacks tests for append ordering, comment URL recovery, success KVs, task source, and final prompt bytes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_11: Upsert-summary update path lacks coverage
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Existing-comment `upsert-summary` paths lack tests for marker search, duplicate detection, `--comment-id` bypass, exact body framing, and failure envelopes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_4: Newline-only read prompt can trigger empty append mutation
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_append_comment_cli()` only rejects exactly empty bodies, so a newline-only `read --issue --prompt` body can redact to empty and still attempt a gh mutation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_6: Write-verb redaction exit 3 lacks pytest coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Compose-time redaction failures for tracking issue write verbs lack pytest coverage, so regressions in exit code 3 or stdout envelopes could break shell consumers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_7: Read delegated append RedactionFailure lacks coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `read --issue --prompt` maps delegated append failures to exit 2, but append-time `RedactionFailure` is not tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_8: Upsert-summary stderr failure stream lacks subprocess coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-stream-parity-output.txt
- **Severity**: important
- **Concern**: `upsert-summary` failure envelopes must go to stderr under inherited quiet, but subprocess coverage does not verify that contract for representative validation, gh, or redaction failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-stream-parity-output.txt: Add subprocess helpers mirroring `_tracking_issue_subprocess_redirected` for stderr, with cases for validation (`invalid marker`, `content file not found`, `invalid repo`), `gh` failure, and exit `3` redaction failure; assert stdout stays empty and stderr contains `FAILED=true` and `ERROR=` under inherited quiet. Keep the implement-bootstrap harness stub assertion on `tracking-issue-cli-summary.stderr.log` as a second line of defense.


