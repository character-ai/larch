## Plan

## Approach

- Use the Piece 1 factories only where their result and queue semantics match.
- Preserve specialized runners and failure results.
- Limit assertion cleanup to touched hunks and stable machine tokens.
- All five target modules import applicable shared test support; `test_checks.py` retains `StubRunner` for fd-routing and call-record semantics while using `ok()` for compatible successful responses.

### UPDATED: python/tests/implement/test_ship.py

- Add `ok` to the existing `test_support` import.
- Replace successful inline `CommandResult` values with `ok()` when argv and stdout are known.
- Keep explicit failure, stderr, and timing-sensitive results unchanged.

### UPDATED: python/tests/agents/test_agents.py

- Import the applicable `RecordingRunner`, `ok()`, and `completed()` helpers.
- Replace equivalent successful `CommandResult` and `CompletedProcess` fakes.
- Replace queue-compatible local runner behavior with `RecordingRunner`.
- Retain specialized runners that capture environment data or compute responses dynamically.
- Preserve the intentional `LARCH_QUIET_DISABLE` removal used to test quiet routing.

### UPDATED: python/tests/review/test_review_and_fix.py

- Import `ok()` and replace equivalent successful `CommandResult` constructions.
- Keep nonzero, stderr-bearing, and timing-sensitive results explicit.
- Remove redundant per-test `LARCH_QUIET_DISABLE` setup now provided by `python/conftest.py`.
- Replace touched prose assertions with stable finding IDs, status KVs, or artifact keys without weakening outcomes.

### UPDATED: python/tests/implement/test_checks.py

- Import and use shared `ok()` for equivalent successful command responses.
- Retain `StubRunner` because its call records and fd-routing behavior differ from `RecordingRunner`.
- Retain local result construction only where nonzero or fd-routing-specific behavior is asserted.
- In touched assertion groups, prefer exit codes, argv evidence, KV keys, and status tokens over complete warning text.

### UPDATED: python/tests/implement/test_ci_monitor.py

- Keep the keyed local `RecordingRunner`.
- Import `ok()` and replace successful `_cr()` or inline `CommandResult` values where no stderr or failure behavior is needed.
- Retain `_cr()` for keyed failures and custom stderr.
- Convert touched prose assertions to stable state or KV tokens when equivalent.

### UPDATED: docs/linting.md

- Add a short Python test convention: assert stable machine tokens and structured keys instead of full human-facing warning strings.

## Edge cases

- Do not replace results whose nonzero return code, stderr, duration, argv shape, fd routing, or call-record structure drives the test.
- Preserve the specialized `StubRunner` behavior in `test_checks.py`.
- Do not remove environment changes that deliberately opt into quiet-routing behavior.
- Keep the migration within the five test modules and `docs/linting.md`.

## Failure modes

- A factory replacement may alter command argv or response ordering.
- Removing the wrong environment setup may expose inherited quiet state.
- Broad token cleanup may weaken a test by dropping its behavioral assertion.
- Duplicate-code lint may reveal partially migrated fixture blocks.

## Testing strategy

- Run focused pytest coverage for all five changed test modules.
- Confirm each target module imports applicable shared support, with `test_checks.py` retaining only its behaviorally necessary local runner support.
- Run `make py-test`.
- Run `make py-lint-duplicate-code`.
- Run changed-file linting for the Python and Markdown files.
- Confirm the five test modules have a visible net line reduction.

## Acceptance

- Run focused pytest coverage for all five changed test modules.
- Confirm each target module imports applicable shared support, with `test_checks.py` retaining only its behaviorally necessary local runner support.
- Run `make py-test`.
- Run `make py-lint-duplicate-code`.
- Run changed-file linting for the Python and Markdown files.
- Confirm the five test modules have a visible net line reduction.

review_status: complete
rounds_completed: 2
difficulty: MODERATE
diff_added: 80
diff_deleted: 210
mechanical_churn: true
diff_lines: 290
