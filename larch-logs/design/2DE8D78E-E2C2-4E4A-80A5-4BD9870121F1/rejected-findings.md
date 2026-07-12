### [Plan Review] FINDING_2

### FINDING_2: Preserve transport versus parse failure contracts
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Concern**: The plan does not define how callers retain distinct transport and parse failure categories, including existing messages and warning codes such as `gh_api_failed` versus `json_invalid`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add a typed read/parse distinction or shared classifier, then map each caller’s existing failure contract explicitly and test both paths


### [Plan Review] FINDING_3

### FINDING_3: Preserve learn-from-bugs fields
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: The `learn_from_bugs` wrapper must request the fields consumed by `build_digest`; otherwise rows may have empty bodies and silently degrade scan output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add fields=("number","title","body","closedAt","url","state") to the learn_from_bugs plan (mirror combine_issues) and require the same tuple in test_learn_from_bugs wrapper assertions


### [Plan Review] FINDING_4

### FINDING_4: Preserve list-issues zero exit status
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: `list_issues_main` must translate `ShipError` into `LIST_STATUS=failed` with warnings while retaining its established exit code of `0`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: State that ShipError translation in list_issues_main emits LIST_STATUS=failed plus warnings and returns 0; add an explicit exit-code assertion to the test_issue_create failure rows

