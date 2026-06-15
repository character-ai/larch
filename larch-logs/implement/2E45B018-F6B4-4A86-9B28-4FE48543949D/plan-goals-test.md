## Goal
Implement issue #4336: [IMPLEMENTING] [BUG] (URGENT) Multiple failures caused /design plan review to silently skip and still publish [DESIGNED].

## Implementation Plan
## Plan

See full plan in plan.txt (553 lines)

## Acceptance

- [ ] All 7 bugs from issue #4336 are fixed
- [ ] `panel-init-failed` is a terminal hard stop before Gate C
- [ ] `review_status:` and `rounds_completed:` are written to every new `larch:plan` block
- [ ] `/implement` Preflight refuses explicit `panel-init-failed` / `panel-skipped` / `rounds_completed: 0`
- [ ] Scope anchor created and validated before Step 3 background launch
- [ ] `mechanical_churn:` accepts numeric input as boolean normalization
- [ ] `feature-description.txt` written on already-planned→replace path
- [ ] `design-log-publish.sh` cleanup-and-retry for stale same-RUN_ID worktrees
- [ ] Failure reporter files issue on panel failure regardless of COMPOSE_STATUS
- [ ] All modified Python modules and shell scripts pass `bash scripts/relevant-checks.sh`

diff_lines: 1825

## Test plan
(no test plan section in plan-file)
