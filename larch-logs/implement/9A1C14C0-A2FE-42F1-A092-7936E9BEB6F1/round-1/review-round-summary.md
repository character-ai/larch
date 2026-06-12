# Review Round 1

- Mode: `diff`
- 7 accepted, 2 rejected (2 neutral)

## Accepted Findings

### FINDING_11: gh stderr redaction lacks regression coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_redact_gh_error` lost dedicated coverage when shell tests were removed, so token-shaped GitHub stderr could leak into `ERROR=` envelopes without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_12: implement-bootstrap stubs do not assert real upsert-summary failure streams
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The retargeted bootstrap harness fakes upsert-summary failures without the real `FAILED=true` and `ERROR=` stderr contract, so `upsert_summary_main` stream regressions can pass `make test-implement-bootstrap`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_13: skip-marker coverage covers only one marker family
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Only one skip-marker family is tested, so a broken marker prefix could leak managed comments into `task.md` without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_20: KV emission can traceback on newline-containing values
- **Reviewer(s)**: dyn-fail-closed-output.txt
- **Severity**: important
- **Concern**: `emit_kv` raises on newline or carriage-return values, and some emitted values can include operator or GitHub text, so the CLI can traceback instead of emitting the expected failure envelope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-fail-closed-output.txt: Address the concern above.


### FINDING_21: CLI entry points do not fail closed for unexpected exceptions
- **Reviewer(s)**: dyn-fail-closed-output.txt
- **Severity**: important
- **Concern**: The tracking-issue main functions catch only selected exceptions, so unexpected `OSError`, `ValueError`, or GitHub-layer errors can escape as tracebacks without verb-appropriate failure envelopes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-fail-closed-output.txt: Address the concern above.


### FINDING_4: public rename can raise CliFailure instead of ShipError
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt, dyn-api-stability-output.txt
- **Severity**: important
- **Concern**: `tracking_issue.rename()` now delegates to `rename_with_details()`, which can raise `CliFailure`; `finalize.py` catches `ShipError` only, so rename failures can crash finalization instead of returning failed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.
  - From dyn-api-stability-output.txt: Address the concern above.


### FINDING_5: newline-only body files pass non-empty validation
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_read_text_file` treats files containing only trailing newlines as non-empty, so create or append can post effectively blank bodies instead of failing with the shell-parity empty-body error.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


