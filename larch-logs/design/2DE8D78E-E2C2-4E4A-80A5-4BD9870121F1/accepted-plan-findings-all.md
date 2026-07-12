### FINDING_1: Normalize issue state casing
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-dyn-Issue Contract Migration
- **Severity**: major
- **Concern**: `gh issue list` returns uppercase `OPEN`/`CLOSED` states, so lowercase comparisons can silently omit all rows while reporting success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In ### UPDATED: python/larch/issue/issue_create.py, require lowercasing (or equivalent) for filter and TSV output, e.g. state_key = str(issue.get("state") or "").lower(); extend test_issue_create.py fixtures to gh-style OPEN/CLOSED and assert tabular stdout still uses open/closed
  - From Codex-Arch: Normalize state for comparisons and output, and test uppercase wrapper states
  - From Codex-Innovation: Lowercase state before comparisons and preserve the existing lowercase output contract
  - From Codex-Pragmatic: Lowercase or casefold `state` before comparisons and add an uppercase-state regression fixture
  - From Codex-dyn-Issue Contract Migration: Normalize state for comparisons and preserve lowercase state in the TSV output


### FINDING_2: Flatten `list_issues_main` wrapper rows
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The wrapper returns a flat list of dictionaries, but retaining the paginated-document outer loop can skip every issue and emit an empty successful snapshot.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In issue_create.py list_issues_main, iterate the wrapper rows directly, drop the outer doc loop, and keep filtering on each issue dict. Extend test_issue_create.py to assert non-empty output from a flat camelCase fixture.
  - From Cursor-Pragmatic: Iterate wrapper rows directly, remove the outer `doc` loop, and add a test with a flat camelCase fixture.
  - From Cursor-Requirements: In the `issue_create.py` plan step, require deleting `_json_documents` and iterating wrapper dict rows in one loop (same pattern as other migrated callers); add/keep a test that asserts non-empty output when the wrapper returns issues


### FINDING_3: Specify `list_open_main` fields
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: `list_open_main` must explicitly request every field it emits; otherwise labels and body data can disappear silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In ### UPDATED: python/larch/issue/combine_issues.py, specify fields=("number","title","body","labels") (or the exact current snapshot set) for list_open_main and assert that sequence in test_combine_issues.py wrapper mocks
  - From Cursor-Innovation: Name the explicit `fields` tuple for `list_open_main` (at minimum `number,title,state,labels,body`) and add a wrapper mock assertion in `test_combine_issues.py` matching `fetch_main`.
  - From Cursor-Pragmatic: In the combine_issues.py plan section, require fields number,title,state,labels,body (matching fetch_main) and assert that tuple in test_combine_issues.py.
  - From Cursor-Pragmatic: Document `number,title,state,labels,body` in the plan and assert it in tests.


### FINDING_5: Preserve degraded preflight-read semantics
- **Reviewer(s)**: Cursor-dyn-Issue Contract Migration
- **Severity**: major
- **Concern**: The preflight concurrency probe currently converts issue-list failures to an empty list and continues successfully; allowing wrapper errors to propagate would change audit behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Issue Contract Migration: In `audit_runs.py` preflight only, catch `ShipError`, coerce to `[]`, and keep the existing cutoff logic; do not route this probe through the same hard-fail `ISSUE_LIST_FAILED` / `_kv_error` translation used by `close_priors_main` and `resolve_prs_main`.


