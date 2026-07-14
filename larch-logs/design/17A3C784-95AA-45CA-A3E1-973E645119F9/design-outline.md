## Proposed Design Outline

### Goals
- Adopt `test_support.RecordingRunner`, `ok()`, and `completed()` across the five high-churn test files.
- Strip redundant per-test `LARCH_QUIET_DISABLE` sets covered by root conftest.
- Convert mechanical prose asserts to stable machine tokens in touched hunks only.

### Non-goals
- Replacing the keyed dict-based `RecordingRunner` in `test_ci_monitor.py` (keep it local).
- Replacing `StubRunner` in `test_checks.py` (calls-structure differs; would require broad assertion surgery).
- Changing any test behavior or assertions beyond the token-stabilization scope.
- Touching files outside the five targets and `docs/linting.md`.

### Approach sketch
- `test_review_and_fix.py`: add `from test_support import ok`; replace `proc.CommandResult(tuple(argv), 0, "...", "", 0.0)` with `ok(argv, "...")`; strip all redundant `LARCH_QUIET_DISABLE` monkeypatch calls.
- `test_agents.py`: add `from test_support import ok`; replace `CommandResult(tuple(argv), 0, "", "", 0.0)` lambdas with `ok(argv)`; preserve the one intentional `delenv` call.
- `test_ship.py`: already imports `RecordingRunner`; add `ok` to imports; replace inline `CommandResult(...)` lambdas with `ok(...)` where the argv is known.
- `test_checks.py`: keep `StubRunner` and `_ok()`; convert mechanical prose asserts to stable tokens in touched hunks only.
- `test_ci_monitor.py`: keep keyed `RecordingRunner`; add `from test_support import ok`; replace `_cr(argv, 0)` calls with `ok(argv)` where appropriate.
- `docs/linting.md`: add a short convention note: assert stable machine tokens, not full warning strings.

### Surfaces in scope
- `python/tests/implement/test_ship.py`
- `python/tests/agents/test_agents.py`
- `python/tests/review/test_review_and_fix.py`
- `python/tests/implement/test_checks.py`
- `python/tests/implement/test_ci_monitor.py`
- `docs/linting.md`

### Open questions
- None.
