## Proposed Design Outline

### Goals
- Make `tracking_issue.link_pr_closes` the single canonical `Closes #N` composer (one source of truth for the string + idempotency).
- Have `pr_body.compose_pr_body` call `link_pr_closes` instead of inlining `f"Closes #{issue_number}"`.
- Delete the dead `PrBodyParts` dataclass (and its `closes_line` field).

### Non-goals
- No fork-dry-run / no-tracking-issue placeholder parity (bash 3-case `closes` logic stays bash-only).
- No bash changes: `scripts/ship-pr.sh` and `scripts/tracking-issue-write.sh` are untouched.
- Do not wire `compose_pr_body` into `pr.ensure_pr` (that integration belongs to a later rework phase).

### Approach sketch
- Keep `link_pr_closes` in `tracking_issue.py`; `pr_body.py` adds `import tracking_issue` (verified no circular import).
- `compose_pr_body` builds the Summary / Code Flow / Test plan body, then appends `Closes #N` through `link_pr_closes(body, issue_number)` when `issue_number is not None`.
- Remove the `PrBodyParts` dataclass from `pr_body.py`.
- Leave `pr.ensure_pr` as-is (it already calls `tracking_issue.link_pr_closes`).
- Update tests to the consolidated single-blank-line layout; keep the idempotency assertion.

### Surfaces in scope
- `python/pr_body.py` — use `link_pr_closes`; drop `PrBodyParts`.
- `python/tracking_issue.py` — canonical helper (no behavior change).
- `python/test_pr_body.py`, `python/test_tracking_issue.py` — test updates.

### Open questions
- `compose_pr_body` currently emits two blank lines before `Closes #N`; `link_pr_closes` emits one (and matches bash better). Recommended: adopt the single-blank-line form and update any test that pins the old layout. Flag if you want the old two-blank-line layout preserved instead.
