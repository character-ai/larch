## Proposed Design Outline

### Goals
- Make `issue_wire` the single owner of `larch:plan` marker composition and recognition.
- Repoint all three bypass sites to `issue_wire` public API with no behavior change at callers.
- Pin each repointing with a regression test.

### Non-goals
- Do not change `issue_wire`'s marker format or ownership contract.
- Do not alter plan heading or trailer grammar (that belongs to #7000).
- Do not fix the analogous `design-pause` literal at `design_router.py:85` (out of scope).

### Approach sketch
- Add `named_block_marker_re(marker, kind)` to `issue_wire.py`; returns the marker regex compiled with `re.MULTILINE` for use in `.search()` contexts.
- `decompose.py`: import `compose_named_block` and call it for the partition-issue plan stub. Remove inline marker literals.
- `learn_from_bugs.py`: replace the lax `re.IGNORECASE` marker pattern with `issue_wire.named_block_marker_re(marker="plan", kind="start")`.
- `design_router.py`: import `parse_named_block` and use it instead of the two-substring check.
- Add one targeted regression test per site (3 tests total).

### Surfaces in scope
- `python/larch/issue/issue_wire.py` (add `named_block_marker_re`)
- `python/larch/design/decompose.py` (repoint composition)
- `python/larch/issue/learn_from_bugs.py` (repoint recognition)
- `python/larch/design/design_router.py` (repoint recognition)
- `python/tests/design/test_decompose.py`
- `python/tests/issue/test_learn_from_bugs.py`
- `python/tests/design/test_design_lifecycle.py`

### Open questions
- None.
