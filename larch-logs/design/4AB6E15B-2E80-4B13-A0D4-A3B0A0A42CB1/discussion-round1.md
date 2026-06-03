## Decision 1: Reconciliation scope
- **Question**: What should "reconcile link_pr_closes with ship-pr Closes #N composition" produce?
- **Resolution**: Consolidate the two Python `Closes #N` composers to a single canonical helper (one source of truth for the string + idempotency). Not a docs-only note; not a full bash 3-case parity port.
- **Source**: user

## Decision 2: Canonical helper location
- **Question**: Where should the single canonical `Closes #N` helper live?
- **Resolution**: Keep `link_pr_closes` in `python/tracking_issue.py`. `pr_body.compose_pr_body` is updated to call `tracking_issue.link_pr_closes` instead of inlining `f"Closes #{issue_number}"`. (Placement mismatch vs bash is accepted by the user; verified safe — `tracking_issue` does not import `pr_body`, so no circular import.)
- **Source**: user + codebase

## Decision 3: Dead PrBodyParts dataclass
- **Question**: Remove the unused `PrBodyParts` dataclass (and its `closes_line` field) at `pr_body.py:25-30`?
- **Resolution**: Delete it. Verified it is referenced by no other open issue in the sequence (only #3326 itself) and no committed doc/plan; it is never instantiated.
- **Source**: user + codebase

## Decision 4: Fork / no-tracking-issue placeholder parity (non-goal)
- **Question**: Should Python port ship-pr.sh's fork-dry-run (`_Fork CI dry-run…_`) and no-issue (`_No tracking issue…_`) placeholder text?
- **Resolution**: Out of scope. User chose "consolidate", not "full parity". Bash-parity tests do not require it; `pr.ensure_pr` already handles repo-unavailable (local-only) early, and fork mode is not modeled in the Python tree.
- **Source**: user

## Decision 5: Backward-compatibility / test constraints
- **Question**: What must not break?
- **Resolution**: `make py-lint` and `make py-test` must stay green. Preserve `link_pr_closes` idempotency (no duplicate `Closes #N`). Keep `compose_pr_body`'s public signature (`issue_number: int | None = None`) and `pr.ensure_pr` behavior unchanged. Existing tests in `test_pr_body.py`, `test_tracking_issue.py`, `test_pr.py` must continue to pass (update only assertions that pin the pre-consolidation inline blank-line layout, if any).
- **Source**: codebase

## Decision 6: Bash side untouched (non-goal)
- **Question**: Should a `Closes` helper be added to `scripts/tracking-issue-write.sh` for symmetry?
- **Resolution**: No. The bash `Closes #N` composition stays inline in `scripts/ship-pr.sh:run_pr_prep_phase`. This issue reconciles the Python side only; no bash changes.
- **Source**: codebase / inference
