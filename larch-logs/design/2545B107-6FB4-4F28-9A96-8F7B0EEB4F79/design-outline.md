## Proposed Design Outline

### Goals
- Add `ok()`, `completed()` factory functions and `RecordingRunner` class-method constructors to `test_support.py`.
- Add `repo_root()` function that returns the repo root path.
- Create `python/tests/support/` package with `test_foundation.py` unit tests for the new functions.

### Non-goals
- Consumer file migration (3-5 files): deferred to later pieces.
- Wire/session fixture factories, plan-body helpers, or vote-line factories: not in this piece.
- R0801 deduplication across existing test files: no cross-file changes.

### Approach sketch
- Add `ok(argv, stdout="")` and `completed(argv, stdout="")` as standalone factories in `test_support.py`.
- Add `RecordingRunner.strict_queue(*responses)` and `RecordingRunner.default_queue(default=None)` as class methods.
- Add `repo_root()` returning existing `ROOT` constant.
- Create `python/tests/support/__init__.py` with a docstring only (empty package sentinel).
- Create `python/tests/support/test_foundation.py` covering all new functions and class methods.

### Surfaces in scope
- `python/test_support.py`
- `python/tests/support/` (new directory)
- `python/tests/support/__init__.py`
- `python/tests/support/test_foundation.py`

### Open questions
- None.
