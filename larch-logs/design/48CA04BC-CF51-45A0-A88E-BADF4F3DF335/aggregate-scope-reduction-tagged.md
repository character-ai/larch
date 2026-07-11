### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: plan Goal / Approach §10
- **Concern**: [SCOPE-REDUCTION] Goal claims every known mutation path but the file list omits several live mutators. Scenario: Step 10 requires inventory yet tracking_issue, clarify, combine_issues, and report_tokens_issue are absent; implementers may ship partial coverage while the goal still reads as exhaustive
- **Proposed resolution**: Narrow Goal acceptance to the enumerated choke points, or add explicit ### MAY_UPDATE: exclusions plus a short residual-path table in SECURITY.md

### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: architecture
- **Location**: scripts/file-failure-report-cross-repo.sh:1-328 and python/larch/cli.py
- **Concern**: [SCOPE-REDUCTION] Shell authorization validation has no pinned Python CLI delegate, inviting duplicated Bash rules. Scenario: Approach item 2 calls for a shell-compatible validation route but the file list does not add a `python/cli.py` entrypoint. The helper is likely to reimplement symlink, session-root, boolean, and run-id checks separately from `issue_create.py`, which can drift and fail open on one side only.
- **Proposed resolution**: Add one `python/cli.py` authorization-check verb (implemented in `session_env.py`); have `file-failure-report-cross-repo.sh` call it and map refusal KVs; keep Bash limited to argument plumbing.

### FINDING_14:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: architecture
- **Location**: Plan Goal section
- **Concern**: [SCOPE-REDUCTION] Goal claims coverage of every known issue-mutation path while firm files omit several live surfaces. Scenario: Binding issue acceptance only requires filing choke-point refusal plus reporter regression; keeping the broad Goal without `tracking_issue.py`, `decompose.py` close-original, or `clarify.py` updates either over-scopes the 865-line plan or leaves a false completeness claim
- **Proposed resolution**: Narrow the Goal to the binding acceptance surfaces explicitly listed in approach steps 3-9, or add firm `### UPDATED:` rows for each remaining live mutation module before claiming full-path coverage
