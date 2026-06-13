# Review Round 1

- Mode: `diff`
- 3 accepted, 3 rejected (2 neutral)

## Accepted Findings

### FINDING_12: correctness: scripts/test-lint-fix-loop.sh stale-env regression has weak session-id assertion
- **Reviewer(s)**: dyn-token-env-codex-output.txt
- **Severity**: important
- **Concern**: The stale-env regression seeds `LARCH_TOKEN_SESSION_ID=stale-parent-session` but only asserts the active row lands somewhere under `$SESSION0A/larch-tokens-*.jsonl`. A leaked `LARCH_TOKEN_SESSION_ID` still writes under `$IMPLEMENT_TMPDIR` using the stale-session slug for the ledger filename, so the test can pass while `lint-fix-loop.sh` regresses to mis-attributing rows to the parent token session.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-token-env-codex-output.txt: Write a known `$SESSION0A/session-id` and assert the exact expected `larch-tokens-<sha256(session-id)>.jsonl` exists, or assert no file with the `sha256("stale-parent-session")` slug exists.


### FINDING_2: correctness: scripts/test-lint-fix-loop.sh missing runtime record-vendor-sidecar stderr-relay fixture
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required runtime stderr-relay coverage for `record-vendor-sidecar` is absent; only static source greps exist. A regression that stops relaying `record-vendor-sidecar` stderr on failure could pass `make test-lint-fix-loop` while violating plan acceptance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add a harness case stubbing failing record-vendor-sidecar with known stderr and assert warning text in captured output
  - From cursor-specialist-testing-output.txt: Add a harness case that forces record-vendor-sidecar failure with known stderr and asserts it is relayed in lint-fix output


### FINDING_8: correctness: skills/research/references/validation-phase.md captures $? after if ! command
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-token-env-codex-output.txt
- **Severity**: important
- **Concern**: The validation sidecar ingestion snippet captures exit status inside `if ! ...; then` blocks. In Bash, `$?` there reflects the negation status, so a failing `token append-record` or `token record-vendor-sidecar` is reported as `exit 0`. That breaks warning relay and makes real ledger failures look successful.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Capture the command status before applying !, for example with set +e, command, rc=$?, set -e, then branch on rc.
  - From codex-specialist-edge-cases-output.txt: Use set +e around each token command, capture rc immediately after the command, then restore set -e before warning handling.
  - From codex-specialist-testing-output.txt: Use set +e; command; rc=$?; set -e; if (( rc != 0 )) or another form that preserves the command's real status.
  - From dyn-token-env-codex-output.txt: Capture status without `!`, for example `set +e; ...; _append_rc=$?; set -e; if ((_append_rc != 0)); then ...`, and do the same for the active-ledger command.


