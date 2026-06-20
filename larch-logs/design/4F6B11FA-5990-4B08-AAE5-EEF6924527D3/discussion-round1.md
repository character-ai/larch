## Decision 1: Cleanup placement
- **Question**: Where should the guarded stale-`.git/index.lock` sweep live?
- **Resolution**: Centralize in `python/git.py` at the `cli.py git commit` layer (`commit_main` and the `commit` / `commit_with_trailer` helpers). All commit paths — the Step 5 review round commit (`_stage_and_commit_round`), the stall-recovery commit (`commit_fixes`), and the dispatcher — inherit one safe policy. Single chokepoint, single test surface.
- **Source**: user

## Decision 2: Removal guard
- **Question**: What guard must a lock satisfy before larch auto-removes it?
- **Resolution**: Auto-remove `.git/index.lock` only when it is **0-byte AND no git process is operating on the repo** (consistent with larch's single-runner invariant), then retry the commit **once**. Do not remove non-empty locks; do not remove when a live git process is detected.
- **Source**: user

## Decision 3: Diagnostic on non-removable lock
- **Question**: When a lock is present but does NOT pass the removal guard (non-empty, or a live git process), how should the failure surface?
- **Resolution**: Surface a **distinct, actionable diagnostic** naming the lock path (e.g. `stale .git/index.lock`) instead of the opaque `coder-failed`, so the operator knows exactly what to clear. A new distinct token may be threaded through the Step 5 `coder-failed` surface.
- **Source**: user

## Decision 4: Dispatcher detect-and-bail (parity only) — OUT OF SCOPE
- **Question**: Should the dispatcher's `index.lock` detect-and-bail (`implement_dispatch.py:1445-1448`) be upgraded to detect-and-clean?
- **Resolution**: Leave unchanged. That check is a post-timeout `dirty-state-after-timeout` guard, not a commit-path failure; it intentionally bails rather than commits. The central commit-layer sweep does not alter it. Listed in the issue "for contrast/parity" only.
- **Source**: codebase (inference)

## Decision 5: Stall-recovery (Step 18a / step5-review) — covered by central fix
- **Question**: Does `python/stall_recovery.py` need a separate stale-lock sweep?
- **Resolution**: No separate change required. With the guarded sweep at the commit layer, the documented `step5-review` recovery retry clears the stale lock on its next commit automatically (the recovery commit `review-and-fix commit-fixes` funnels through the same `cli.py git commit` entrypoint). Keep the change minimal; do not modify `stall_recovery.py` classification.
- **Source**: codebase (inference)
