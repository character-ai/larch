## Decision 1: Item 3 implementation approach
- **Question**: Extract shared `_write_bg_wait_marker` to `bg_wait.py`, or add field-set test?
- **Resolution**: Extract to `python/larch/implement/bg_wait.py`; both modules import from it.
- **Source**: user

## Decision 2: Items 7/8 parity harness approach
- **Question**: Documented exclusion comment, or semantic comparison that normalizes function names?
- **Resolution**: Semantic comparison (normalize names, extract and compare bodies).
- **Source**: user
