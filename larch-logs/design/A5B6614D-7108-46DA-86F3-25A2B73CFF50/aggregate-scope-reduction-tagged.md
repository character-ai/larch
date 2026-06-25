### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/architectural_guidelines.py:18-23
- **Concern**: [SCOPE-REDUCTION] prepare parses unused --output. Scenario: `prepare_main` is specified to parse `--output`, but the plan never wires it into the combined emit/write path (only `materialize-diff` documents that behavior). The /implement wrapper does not pass `--output`, so the new verb would advertise a dead flag and any direct caller relying on it would silently get no file.
- **Proposed resolution**: Drop `--output` from `prepare_main` unless the plan explicitly delegates to the same shared materialization helper path that honors `--output`; keep `--output` only on the retained `materialize-diff` verb.
