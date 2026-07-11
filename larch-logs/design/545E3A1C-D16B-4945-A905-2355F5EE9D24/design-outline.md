## Proposed Design Outline

### Goals
- Recognize h2-h4 (`#{2,4}`) section headings in `/learn-from-bugs` bug-body digests.
- Ignore heading-shaped lines inside fenced code blocks when splitting sections.

### Non-goals
- Near-miss heading-name mapping (`Problem`->`summary`, etc.).
- h5 and deeper heading support.

### Approach sketch
- Widen `_HEADING_RE` in `python/larch/issue/learn_from_bugs.py` from `#{2,3}` to `#{2,4}`.
- Add fenced-code state tracking to `_split_sections` so heading matches inside fences are skipped, per G-Md-3.
- Preserve the existing first-word dedup in `_pick_sections` so `root cause` maps to one section.

### Surfaces in scope
- `python/larch/issue/learn_from_bugs.py`
- `python/tests/issue/test_learn_from_bugs.py`

### Open questions
- None.
