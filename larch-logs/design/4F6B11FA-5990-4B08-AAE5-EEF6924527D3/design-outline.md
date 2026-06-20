## Proposed Design Outline

### Goals
- Auto-clear a stale `.git/index.lock` (0-byte, no live git holder) so the Step 5 review coder commit succeeds instead of an opaque `coder-failed` stall.
- Centralize the guarded sweep at the `cli.py git commit` layer so the review round commit, stall-recovery commit, and dispatcher all share one safe policy.
- Surface a distinct, actionable diagnostic when a lock is present but cannot be safely removed.

### Non-goals
- No change to the dispatcher's `index.lock` detect-and-bail timeout guard (`implement_dispatch.py:1443-1448`); it is a separate post-timeout check, kept for parity only.
- No change to `stall_recovery.py` classification — the central fix makes the documented `step5-review` retry clear the lock on its next commit automatically.
- Never remove a non-empty lock or a lock held by a live git process.

### Approach sketch
- Add a guarded sweep helper in `python/git.py`: remove `.git/index.lock` only when it is 0-byte AND no git process is operating on the repo, then retry the commit once.
- Wire the sweep into the `cli.py git commit` entrypoint (`commit_main`) so `commit` / `commit_with_trailer` callers inherit it without per-call-site changes.
- On a present-but-non-removable lock, emit a distinct diagnostic naming the lock path and thread a distinct reason token through the `coder-failed` surface in `python/review_and_fix.py`.

### Surfaces in scope
- `python/git.py` — commit entrypoint + new guarded stale-lock sweep helper.
- `python/review_and_fix.py` — distinct diagnostic/reason on the coder-failed surface.
- `python/test_git.py`, `python/test_review_and_fix.py` — regression coverage (0-byte removal+retry, non-empty/live-process refusal, distinct diagnostic).

### Open questions
- None. Placement, removal guard, and diagnostic were resolved in Step 1c.
