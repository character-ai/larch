## Proposed Design Outline

### Goals
- Make `_INVARIANT_ID_RE` and `_INVARIANT_HEADING_RE` agree on the canonical `I-*` shape.
- Prevent future grammar drift with a cross-parser regression test.

### Non-goals
- Widening `_INVARIANT_HEADING_RE` to accept `INV-*`.
- Adding a runtime warning inside `coverage_index` for dropped entries.
- Updating documentation about invariant-ID conventions.

### Approach sketch
- Drop `(?:INV|I)` from `_INVARIANT_ID_RE` in `learn_from_bugs.py`; replace with `I` only.
- Add a parametrized or shared test asserting both regexes accept `I-*` and reject `INV-*`.
- Place the test where both modules are visible: `python/tests/` (likely alongside `test_architectural_guidelines.py` or `test_learn_from_bugs.py`).

### Surfaces in scope
- `python/larch/issue/learn_from_bugs.py` — `_INVARIANT_ID_RE` (line 63)
- `python/tests/issue/test_learn_from_bugs.py` — new invariant-index test cases
- `python/tests/core/test_architectural_guidelines.py` — cross-parser shape fixture

### Open questions
- None.
