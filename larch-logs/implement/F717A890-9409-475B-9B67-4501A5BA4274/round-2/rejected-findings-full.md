### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: GitHub PR lookup failures are degraded to fresh reruns
- **Reviewer(s)**: dyn-github-pr-output.txt
- **Severity**: important
- **Concern**: `_resume_plan()` treats transient and non-transient `gh.pr_view` failures as `fresh`, which can rerun checks/postbump, reset CI budgets, or churn an already-open PR instead of preserving resume metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-github-pr-output.txt: Distinguish `TransientNetworkError` (return `Outcome.TRANSIENT` without a full fresh pipeline) from permanent lookup failures; when state + branch are valid but `gh` is temporarily unreachable, prefer `open-pr` resume using persisted identity or a safe-refuse that preserves counters rather than `fresh` with zero-seeded CI locals.
  - From dyn-github-pr-output.txt: Catch `TransientNetworkError` separately for the handback above; map other `ShipError`/`ShipError`-family read failures to `NEEDS_USER_INPUT` or `STALLED` with explicit detail, leaving counters and `RESUME_PHASE` intact.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: State durable flags can force gh-skipped resume behavior
- **Reviewer(s)**: dyn-state-io-output.txt
- **Severity**: important
- **Concern**: Resume treats durable flags from `ship-pr-state.sh` as authoritative without cross-checking the invoking session, so tampered state can set `REPO_UNAVAILABLE=true` or `FORKED_TARGET=true` and bypass GitHub-authoritative checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-io-output.txt: Treat state durable flags as a cache, not sole truth: on non-fresh resume, require agreement with argv/`session-env.sh` (or a signed bootstrap nonce), or refuse resume when `ctx.forked_target`/`ctx.repo_unavailable` disagree with hydrated state unless `repo_unavailable` was explicitly established at session start.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_19: Open-pr branch redundantly rereads OOS_PENDING
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The open-pr branch reads `OOS_PENDING` from state even though `_hydrate_resume_context()` already populated `pr_context.oos_pending`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Simplify to `elif pr_context.oos_pending:`.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_20: Dead `_ = step` assignment is misleading
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_ = step` adds no semantics because `step` is already used as `stall_step=step`, and it misleadingly suggests the value is discarded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove `_ = step`.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: `_write_ship_state` repeatedly rereads resume metadata
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_write_ship_state()` reads `RESUME_PHASE` and `CALLER_KIND` from disk on common-path writes, adding repeated file reads through the CI loop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Read `RESUME_PHASE`/`CALLER_KIND` once in `_resume_plan` or at the top of `run_ship()`, store them on the context or pass them through, and remove the in-place reads from `_write_ship_state`.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: State boolean parsing is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `ship.py` duplicates the boolean parsing already implemented in `run_logs._state_bool_or_default()`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Export `state_bool_or_default` from `run_logs` and call it from `ship.py` instead of the local copy.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_24: Open-pr-only branch is hidden behind a bare else
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: A bare `else` hides that the branch is only reachable for `resume.start == "open-pr"`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Replace `else:` with `elif resume.start == "open-pr":` (and optionally add a final `else: raise AssertionError(resume.start)` for safety).


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Resume can proceed without a durable persisted branch anchor
- **Reviewer(s)**: dyn-resume-state-output.txt
- **Severity**: important
- **Concern**: For normal repos, resume validation can fall back to argv/env branch values when persisted `BRANCH_NAME` is empty, weakening the durable branch validation guarantee.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt: After `blocked-rebase-continuation`, require a non-empty persisted `BRANCH_NAME` for any non-`fresh` resume (not only `gh_skipped`), and safe-refuse when it is missing or does not equal the probed current branch; do not fall back to `ctx.branch` for anchor validation once a state file exists.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

