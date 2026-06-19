## Decision 1: Cutoff scope — reviewers only, opt-in flag
- **Question**: `_reap_phase` is the shared reaper for all `dispatch-waterfall` panels (reviewers, the 3-way voting panel, the 8-slot decompose panel, the aggregator). Where should the straggler cutoff apply?
- **Resolution**: Reviewers only. The cutoff is gated behind an opt-in CLI flag that only reviewer-panel callers pass. Voters, decompose, and aggregator keep today's wait-for-all behavior. Rationale: a global 3x-fastest cutoff would kill votes (issue chart: `cursor/vote` 93s vs `claude/vote` 304s) and could drop decomposition proposals.
- **Source**: user

## Decision 2: Reviewer-panel call sites (which callers pass the flag)
- **Question**: Which `dispatch-waterfall` callers are reviewer panels that should opt into the cutoff?
- **Resolution**: `python/plan_review_panel.py` (/design plan-review) and `python/review_pipeline.py` (/implement + /review code-review) pass the opt-in flag. `python/agent_voters.py` (voting), `python/decompose.py` (decompose panel), and `python/review_aggregate.py` (findings aggregator, single-slot anyway) do NOT pass it.
- **Source**: codebase

## Decision 3: Anchor basis — quorum-th completion
- **Question**: Once enough reviewers finish, what does the deadline anchor on?
- **Resolution**: Anchor on the quorum-th (slowest-of-quorum) successful reviewer. Do not arm the deadline until at least a quorum fraction of slots exit successfully; then anchor on that quorum-th reviewer's elapsed time, so the anchor reflects typical speed, not a single fast outlier. Success-only counting (a failed/crashed slot does not count toward quorum).
- **Source**: user

## Decision 4: Deadline formula and safety bounds
- **Question**: How is the deadline computed and bounded?
- **Resolution**: `deadline = clamp(multiple * quorum_anchor_elapsed, floor, ceiling)`. Multiple default 3 (env `LARCH_REVIEWER_STRAGGLER_MULTIPLE`; `0` disables and restores wait-for-all). Floor default 300s (env `LARCH_REVIEWER_STRAGGLER_FLOOR_SECONDS`). Quorum fraction default 0.5, env-configurable (new env var). Ceiling = existing per-reviewer `--timeout` (1860 design plan-review / 1800 code-review). Elapsed measured from phase start via `time.monotonic()`.
- **Source**: user + issue

## Decision 5: Timed-out stragglers — killed and dropped, no fallback
- **Question**: What happens to reviewers that exceed the deadline?
- **Resolution**: Killed (SIGTERM via existing `_terminate_launch`, process group + descendants) and dropped. Waterfall fallback is DISABLED for them: no codex->cursor->claude cascade. The round proceeds with the reviews already collected. Only deadline-exceeded stragglers skip fallback; genuine crashes and empty outputs still fall back as today.
- **Source**: user + issue

## Decision 6: Disable / no-op paths
- **Question**: When is the cutoff inactive?
- **Resolution**: Inactive when the opt-in flag is absent (all non-reviewer panels), when `LARCH_REVIEWER_STRAGGLER_MULTIPLE=0`, when no quorum of successes is ever reached, or when fewer than 2 slots run. In every inactive case behavior is identical to today (each launch self-terminates at its own `--timeout`).
- **Source**: user + issue

Round 1 decisions resolved: 6 (2 from codebase, 4 from user/issue).
