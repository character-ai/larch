## Decision 1: Optional consumer migration scope
- **Question**: Is the "optionally repoint 3–5 test_support consumers" in scope for this piece?
- **Resolution**: Out of scope. The firm headings (`### NEW: python/tests/support/`, `### UPDATED: python/test_support.py`) name only two targets. Acceptance criteria do not require consumer changes. Later pieces in the series handle migration.
- **Source**: codebase (feature description + acceptance criteria)

## Decision 2: python/tests/support/__init__.py content
- **Question**: Empty or thin re-export for the new package init?
- **Resolution**: Empty (just a docstring). Existing test subdirectories (`design/`, `research/`, etc.) have no `__init__.py`; tests import `from test_support import ...` directly via pytest's sys.path discovery. Consistency favors empty.
- **Source**: codebase

## Decision 3: RecordingRunner "second variant" meaning
- **Question**: Since `RecordingRunner` already has `strict=True/False` and `default=...`, what does "second variant" mean?
- **Resolution**: Add class-method factories: `RecordingRunner.strict_queue(*responses)` for the strict variant and `RecordingRunner.default_queue(default=None)` for the lenient variant. No separate class needed.
- **Source**: codebase (existing RecordingRunner implementation in test_support.py)
