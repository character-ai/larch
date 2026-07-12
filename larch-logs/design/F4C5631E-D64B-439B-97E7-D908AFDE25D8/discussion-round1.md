## Decision 1: Correct liveness policy
- **Question**: Should `adapt` use `child_liveness AND daemon_liveness` or `OR` when deciding if a job is live?
- **Resolution**: Use `OR`. Seven out of eight step scripts use `or`; `registry.has_live_entry` uses `or`. `step-5-review.sh:75` using `and` is the bug/drift the issue targets.
- **Source**: codebase

## Decision 2: Stale-clear semantics
- **Question**: Should `adapt` clear a dead entry and restart, or fail closed on a dead entry?
- **Resolution**: Fail closed. Acceptance criteria says "fails closed on a dead registry entry". Stale-clear applies only to truly expired/invalid entries before the fresh start path.
- **Source**: issue body

## Decision 3: Re-attach behavior on second call
- **Question**: When a live entry exists, what does `adapt` emit?
- **Resolution**: Emit `BGJOB_STATUS=STARTED STEP=<step> PGID=<pgid>` matching the `bgjob start` contract, so callers can proceed to `bgjob wait` identically regardless of start vs. re-attach.
- **Source**: issue body / bgjob start contract in daemon.py

## Decision 4: Non-goals
- **Resolution**: Do NOT convert any existing step script. Do NOT move assessment/ship token vocabularies.
- **Source**: issue non-goals

0 decisions deferred.
