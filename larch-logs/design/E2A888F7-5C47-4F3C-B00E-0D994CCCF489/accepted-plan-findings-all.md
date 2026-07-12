### FINDING_1: `issue_list_read` omits optional `--limit`
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-dyn-Gh Wrapper Contract Auditor
- **Severity**: major
- **Concern**: The planned `issue_list_read` signature has no `limit` parameter and never emits `--limit`. Every audited `gh issue list` call site in `python/larch/` (`audit_runs.py`, `combine_issues.py`, `learn_from_bugs.py`, `analyze_issues.py`) passes explicit limits (e.g. 50, 200, 100000, or caller-supplied values); none rely on `--paginate` alone. Without a typed `limit` knob, sibling repointing cannot preserve those argv shapes and callers would silently fall back to `gh`'s default page size, truncating results and failing the stated coverage goal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add optional keyword-only limit: int | None = None; emit --limit str(limit) only when set. Add tests for omission, inclusion, and stable argv ordering alongside existing paginate cases.
  - From Codex-Arch: Add a limit parameter and emit --limit when supplied, or document and verify that every audited caller can safely use the wrapper without that option
  - From Cursor-Innovation: Add keyword-only limit: int | None = None; emit --limit str(limit) only when limit is not None; extend argv-order tests for limit omission/inclusion and stable placement relative to --json/--paginate
  - From Codex-Innovation: Use the supported `gh issue list --limit` pagination contract, or define a valid pagination strategy and corresponding parameter. Align the tests and audited raw argv coverage with that strategy.
  - From Cursor-Pragmatic: Add keyword-only limit: int | None = None; emit --limit only when supplied; extend argv-order and omission tests; document that high-volume callers use limit while full scans may use paginate=true
  - From Codex-Pragmatic: Add an optional limit parameter, preserve its caller-supplied value in argv, and test omission and inclusion without changing existing callers
  - From Cursor-Requirements: Add optional limit: int | None = None; emit --limit only when supplied. Extend argv-order tests for inclusion and omission. Document that paginate and limit are independent optional flags.
  - From Codex-dyn-Gh Wrapper Contract Auditor: Add a keyword-only limit parameter and emit one --limit pair when supplied, preserving the existing option value and ordering.


### FINDING_2: `issue_list_read` plans unsupported `--paginate` flag
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: The planned wrapper exposes `paginate=True`, but `--paginate` is not a supported flag for `gh issue list`. Any call with `paginate=True` would construct an invalid command before `loads_json_paginated_list` can apply its parsing authority, breaking the intended paginated issue-list path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Use the supported `gh issue list --limit` pagination contract, or define a valid pagination strategy and corresponding parameter. Align the tests and audited raw argv coverage with that strategy.


### FINDING_6: Missing `--body-file` issue-edit wrapper
- **Reviewer(s)**: Codex-dyn-Gh Wrapper Contract Auditor
- **Severity**: major
- **Concern**: The planned edit additions do not cover the raw `--body-file` issue-edit shape used by `deps_audit.py`. That caller passes an existing body-file path. Planned label-edit wrappers and content-based body helpers do not accept a caller-owned body-file path, so repointing would require reading/rewriting the file or retaining a raw argv site and the audited edit variants remain incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Gh Wrapper Contract Auditor: Add an issue edit body-file wrapper accepting the path and optional repo, using one _gh call and returning CommandResult without mutation retries.


### FINDING_7:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/git/gh.py
- **Concern**: [SCOPE-REDUCTION] New batch label-edit wrapper duplicates existing retry helpers. Scenario: Audited raw label argv uses single --add-label or --remove-label per call (difficulty.py, oos_priority.py). issue_label_add/issue_label_remove already exist; the only gap is optional repo. A new multi-label mutation wrapper adds surface area and splits retry policy without a audited caller need.
- **Proposed resolution**: Extend issue_label_add/issue_label_remove with repo: str | None = None (and cwd if needed) instead of adding a separate batch label-edit wrapper; keep issue_edit title/body unchanged.


### FINDING_2: Plain issue-view command shape lacks wrapper coverage
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic
- **Severity**: major
- **Concern**: The audit identifies callers using plain `gh issue view <issue>` without `--json`, but the planned template wrapper and existing field helpers cover only JSON-based views. Without a plain-view wrapper, the stated view-shape coverage goal remains incomplete and future callers must retain raw issue-view construction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add a retrying plain-view wrapper for `gh issue view <issue>` with optional `repo` and `cwd`, or explicitly document and justify excluding these audited shapes from the coverage goal.
  - From Codex-Pragmatic: Add a minimal read wrapper for plain issue view, returning `CommandResult` through `_retry_read`, plus exact argv coverage


