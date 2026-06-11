# Review Round 1

- Mode: `diff`
- 6 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Plan voter status and degraded-warning KVs are lost under quiet dispatch
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Quiet-mode plan dispatch calls Python voting status and degraded-warning commands directly, so required `VOTER_*`, `VOTER_PATHS_FILE`, and `DEGRADED_PANEL_WARNING` contract lines go to the quiet log instead of the captured contract stream.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_10: focus-area enum lint coverage was not replaced after harness deletion
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Deleted `check-focus-area-enum.sh` has no pytest replacement, so broken `lint_focus_area_enum_main` may only surface in full `make lint` agent-sync rather than `make py-test`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_11: parse-rate retry lacks an empty-output success test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Missing empty-retry-output `parse-rate-retry` test leaves zero-byte successful retry behavior unverified, so dispatch under `set -e` could return the wrong token or nonzero exit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_5: Code voter test CLI shim hardcodes a local checkout path
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/test-dispatch-code-voters.sh` generates sandbox CLI stubs with `<OPERATOR_REPO_PATH>/python/cli.py`, so CI or other checkout paths cannot run the voting CLI tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_6: Step telemetry marks run before session rehydration
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Step telemetry replacement defines but does not call session rehydration before ledger marks, so wrappers with only `session-env` keys can write token and timing marks to fallback or default ledgers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_9: write-tally pytest coverage was not replaced after harness deletion
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Deleted `test-write-tally.sh` has no voting `write-tally` pytest replacement, so regressions in header validation and larch-log KV re-emission can ship without `py-test` failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


