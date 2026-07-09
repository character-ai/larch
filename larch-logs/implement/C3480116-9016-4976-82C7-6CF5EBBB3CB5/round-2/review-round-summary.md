# Review Round 2

- Mode: `diff`
- 2 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: ensure_pr refusal path lacks zero-mutation proof
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: major
- **Concern**: The ship-entry refusal path for `ensure_pr` is not proven to stop before any mutating git/gh operation, so a gate-order regression could still mutate before `NeedsUserInput` is raised.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Add test_ensure_pr_scope_disposition_refuses_before_push with gate-relevant ctx.tmpdir RecordingRunner and empty _mutating_calls


### FINDING_2: create_main/body_update_main refusal tests do not prove no mutations
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, cursor-specialist-plan-fidelity-auto
- **Severity**: major
- **Concern**: The refusal-path tests for `create_main` and `body_update_main` do not establish that zero mutating git/gh calls occur before the refusal return, so a regression could still push or edit successfully while the tests pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Monkeypatch proc with RecordingRunner and assert _mutating_calls(runner) == [] alongside the existing halt KVs
  - From codex-specialist-testing: Use a RecordingRunner or monkeypatch proc and assert no mutating calls before the needs-user return.
  - From cursor-specialist-plan-fidelity-auto: Monkeypatch proc or forbid create_pr_parity/push/pr_create and assert no mutating runner calls on the needs-user path
  - From cursor-specialist-plan-fidelity-auto: Use RecordingRunner or a forbidden gh pr edit stub and assert no mutating calls on refusal


