### FINDING_1: Feasibility preflight must use the same target set as `pack()`
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-dyn-math-bound
- **Severity**: important
- **Concern**: If `_check_feasibility` is added per the plan but derives `max_target_time` and `ideal_shard` from all `medians.values()`, it will disagree with `pack()`, which only uses `measured = {t: medians[t] for t in medians if t in all_shard_targets}` (line 344). Baseline CI logs can retain timing rows for targets no longer listed in Makefile shards. Those orphan medians inflate `ideal_shard` and can pick a heaviest target that is not in the packed workload, so the warn-only preflight may stay silent when the 15s threshold is still impossible for the real partition LPT will build.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Compute measured = {t: medians[t] for t in medians if t in all_shard_targets} before _check_feasibility; derive max_target_time and ideal_shard from measured.values() only
  - From Cursor-Pragmatic: Compute measured before the check; pass measured into _check_feasibility; use max(measured.values(), default=0.0) and ideal_shard = sum(measured.values()) / n_shards. Call the helper after measured is built and immediately before pack()
  - From Cursor-dyn-math-bound: Build the same measured dict (plus extras at 0s) before _check_feasibility; compute max_target_time and ideal_shard from that packed universe only



