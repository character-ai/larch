### FINDING_12:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/review/snapshot.py:672-691
- **Concern**: [SCOPE-REDUCTION] Preserve safe reuse of an existing snapshot root instead of requiring every root creation to be exclusive. Scenario: `_write_pre_coder_snapshot` currently clears and rewrites the deterministic per-round directory. After an interrupted attempt leaves a valid directory, literal exclusive root creation makes the next attempt fail before it can replace stale or partial artifacts, breaking existing recovery and requiring manual cleanup.
- **Proposed resolution**: Create the directory exclusively only when absent. When it already exists, validate the directory and every ancestor without following symlinks, then safely clear and republish the snapshot artifacts.
