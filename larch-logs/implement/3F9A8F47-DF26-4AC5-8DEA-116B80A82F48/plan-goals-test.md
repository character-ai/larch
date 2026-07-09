## Goal
Implement issue #6769: [IMPLEMENTING] chore(larch-logs) issue should have in both title and body the number of issue whose /design run generated the run logs.

## Implementation Plan
## Plan

Implement the approved narrow change in the design log publisher and keep `/audit-runs` design-log PR title matching working with the new title shape.

## Files to modify/create

### UPDATED: python/larch/design/design_log_publish_flow.py

In `_publish_design_logs`, include `request.issue` in both `gh pr create` surfaces:

- PR title:
  - Current: `chore(larch-logs): design run {request.run_id}`
  - New: `chore(larch-logs): design run {request.run_id} (issue #{request.issue})`
- PR body file text:
  - Current: `Automated design log directory for run {request.run_id}. Merged once required CI checks pass.`
  - New: append `(issue #{request.issue})` to that sentence.
  - Keep `--body-file`; do not introduce inline `--body`.

Do not add CLI flags or request fields. `_PublishDesignLogsRequest.issue` already carries the required value and is validated by `log_publish_main`.

### UPDATED: python/tests/design/test_design_log_publish_flow.py

Add regression coverage for the `gh pr create` argv and body file content.

Recommended minimal test shape:

- Extend `_write_gh_stub` with an optional `capture_path: Path | None = None`.
- When the stub handles `gh pr create` and `capture_path` is set:
  - Write the full argv to the capture file (one argument per line or another stable parseable format).
  - Read the path passed to `--body-file` **inside the stub before exit** and append the body text to the same capture file (e.g. a `BODY:` section). Do not rely on reading `--body-file` after `_run_publish` returns; `_publish_design_logs` removes `wt_parent` in `finally` after `gh` returns.
- In `test_log_publish_commits_pushes_and_opens_pr`, pass a tmpdir capture path into `_write_gh_stub`, then parse the capture file after `_run_publish`.
- Assert:
  - `--title` value contains `issue #33`.
  - `--body-file` is still used.
  - Captured body text contains `issue #33`.
  - No inline `--body` argument appears in captured argv.

Keep the existing integration assertions for clean worktree, pushed branch content, PR URL, and metadata.

### UPDATED: python/larch/issue/audit_runs.py

Broaden both anchored design-log PR title regexes to accept an optional trailing issue suffix while keeping the UUID run-id capture unchanged:

- `_DESIGN_RUN_TITLE_RE`: append `(?: \(issue #[0-9]+\))?$` after the existing UUID anchor.
- `_DESIGN_RUN_ID_RE`: append the same optional suffix after the existing capture group so `extract_design_run_log_pr_id` still returns only the UUID.

Legacy exact-UUID titles without the suffix must continue to match.

### UPDATED: python/tests/issue/test_audit_runs.py

Extend `test_design_run_id_extraction_requires_strict_uuid_title`:

- Add a suffixed title case, e.g. `chore(larch-logs): design run 12345678-1234-1234-1234-123456789ABC (issue #33)`.
- Assert `match_design_run_log_pr_title` is true and `extract_design_run_log_pr_id` still returns the UUID.
- Keep existing unsuffixed and loose-title negative assertions unchanged.

## Approach

Make the smallest producer-only change at the `gh pr create` construction site.

Update the audit-runs title matchers in the same change so newly published design-log PRs remain discoverable by `/audit-runs` skill filtering and run-id extraction.

Keep the title and body format additive. This preserves existing branch naming, commit behavior, PR detection, admin-merge routing, and run-log schema.

## Edge cases

- Pause publishes also use `_publish_design_logs`; they should get the same issue traceability.
- Invalid or missing issue values are already rejected before `_PublishDesignLogsRequest` is built.
- Body text remains one line and controlled by code, so it should not introduce line-oriented wire risks.
- Suffixed titles must not weaken UUID strictness: only an exact `(issue #<digits>)` suffix is accepted; arbitrary trailing text must still fail matching.

## Failure modes

- If the test captures the wrong process boundary, it may miss the real `gh pr create` argv. Capture inside the stub branch that handles `pr create`, and snapshot body text there before the stub exits.
- If audit-runs regexes are not updated, `/audit-runs` will stop recognizing new design-log PRs even though prefix-based admin-merge routing still works.
- Do not change commit subjects. The approved outline excludes `/implement` flush commit subject changes and log commit format changes.
- Do not change PR discovery or admin-merge filters beyond accepting the optional title suffix for audit matching.

## Testing strategy

Run the changed test files only:

```bash
python3 -m pytest python/tests/design/test_design_log_publish_flow.py python/tests/issue/test_audit_runs.py -k 'test_log_publish_commits_pushes_and_opens_pr or test_design_run_id_extraction_requires_strict_uuid_title'
```

If local lint is requested, run the Python lint for changed files only or the repo’s relevant-checks path after implementation.

## Acceptance

Run the changed test files only:

```bash
python3 -m pytest python/tests/design/test_design_log_publish_flow.py python/tests/issue/test_audit_runs.py -k 'test_log_publish_commits_pushes_and_opens_pr or test_design_run_id_extraction_requires_strict_uuid_title'
```

If local lint is requested, run the Python lint for changed files only or the repo’s relevant-checks path after implementation.

diff_lines: 68

## Test plan
(no test plan section in plan-file)
