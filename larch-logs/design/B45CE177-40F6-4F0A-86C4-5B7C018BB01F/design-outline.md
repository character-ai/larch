## Proposed Design Outline

### Goals
- Fix `_oos_info()` in `design_summary.py` to parse the `OOS_FILE_MAP\t<n>\t<url>` lines that `cmd_annotate` actually writes, instead of the stale `https://`-prefix check.
- Add a regression test pinning the reader/writer line-format contract so this class of drift is caught mechanically.

### Non-goals
- No changes to the writer (`cmd_annotate` in `design_oos.py`) or its three existing correct `OOS_FILE_MAP` readers.
- No broader refactor of `oos-issues-created.md`'s sentinel format or a shared cross-module parsing helper.

### Approach sketch
- Rewrite `_oos_info()`'s per-line match to key off `OOS_FILE_MAP\t`, split on tab, and extract the URL field — mirroring the existing parsing at `design_oos.py:547` and `:572`.
- Guard short/malformed lines the same defensive way the other readers do.
- Add unit tests in `test_design_summary.py`: real `OOS_FILE_MAP` lines counted and joined correctly, missing file, and malformed lines ignored.

### Surfaces in scope
- `python/larch/design/design_summary.py` (`_oos_info`)
- `python/tests/design/test_design_summary.py`

### Open questions
- None.
