### OOS_1: _renumber_oos_headings still matches OOS headings over splitlines without fence gating
- **Description**: _renumber_oos_headings still matches OOS headings over splitlines without fence gating. Scenario: The repo-wide markdown-heading lint will likely surface _renumber_oos_headings because it re.match(r"^### OOS_\d+:", line) over text.splitlines() with no fenced-line skip, even though the module already uses _balanced_fence_line_indices in _validate_issue_cap_input. Baselining without fixing leaves the #6676 failure mode alive for renumbered OOS bodies that contain fenced ### lines.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/issue/file_oos.py:703-713
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

