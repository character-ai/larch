### FINDING_2:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:56-83
- **Concern**: [SCOPE-REDUCTION] `python/cleanup_skill.py` resolved-symlink reaping and `_read_design_tmpdir` exceed the filed OOS symptom. Scenario: The binding OOS observation targets design vs implement ranking parity (`_design_candidate` still uses pointer mtime while implement uses ledger activity). `_design_candidate` already returns `None` when the resolved tmpdir is missing (`python/progress_report.py:188-189`), so resolved symlinks with dead tmpdirs do not enter discovery today. Current cleanup only removes dangling design symlinks (`python/cleanup_skill.py:133-135`). Adding export-aware parsing plus removal of resolved symlinks whose tmpdir path is absent adds a second subsystem and ~4 cleanup tests without fixing a discovery correctness gap the issue describes.
- **Proposed resolution**: Drop the `python/cleanup_skill.py` section (and its `python/test_cleanup_skill.py` additions) from this change. Keep the fix to `python/progress_report.py` and `python/test_progress_report.py` only. File symlink hygiene separately if pointer pile-up is still a problem after ranking parity lands.

### FINDING_3:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/cleanup_skill.py:132-135
- **Concern**: [SCOPE-REDUCTION] The cleanup_skill reaper/parser changes are not required for the live-run discovery liveness fix.. Scenario: progress_report._design_candidate already ignores missing design tmpdirs on the discovery path, so the feature can be completed by the progress_report ranking and ledger-parser changes without changing /cleanup behavior or adding cleanup tests.
- **Proposed resolution**: Remove the python/cleanup_skill.py and python/test_cleanup_skill.py sections from this plan. Keep the existing dangling-symlink cleanup unchanged. Track resolved-design-symlink reaping separately if still desired.
