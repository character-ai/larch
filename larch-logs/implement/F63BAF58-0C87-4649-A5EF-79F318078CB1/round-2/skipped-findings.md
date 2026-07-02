### OOS_1: Tool-absent excuse treats non-empty surviving outputs as success without collector OK
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: blocking
- **Concern**: In `python/larch/review/review_core_body.py`, the tool-absent excuse still treats non-empty surviving outputs as success via `review_threshold.py`, not just collector OK/cap_hit rows. When one vendor is absent and the survivor writes a non-empty but collector-rejected or non-substantive file, `_static_coverage_reason()` can return empty and the panel passes with no successful reviewer for that archetype.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Base the excuse on collector success for the surviving slot, or require collector OK/cap_hit before removing the absent vendor from missing
