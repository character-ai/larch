## Decision 1: Scope — which panels
- **Question**: Which reviewer panels does the straggler cutoff cover?
- **Resolution**: The three reviewer panels: `/design` plan-review, `/implement` review, `/review` code-review. They funnel through `agent dispatch-waterfall` (`python/agent_waterfall.py`), so one reaper change reaches all three.
- **Source**: issue / user

## Decision 2: Cutoff reach across dispatch-waterfall callers
- **Question**: `_reap_phase` is shared by reviewers, voters, the findings aggregator, and the decompose panel. How wide should the cutoff reach?
- **Resolution**: Reviewer panels ONLY. Gate the cutoff behind an opt-in flag passed only by the two reviewer dispatch sites (`review_pipeline.py` for `/review`+`/implement`, `plan_review_panel.py` for `/design`). Voters (`agent_voters.py`), aggregator (`review_aggregate.py`), and decompose (`decompose.py`) keep wait-for-all, so a cut slot can never drop a vote.
- **Source**: user (Round 1)

## Decision 3: Anchor policy — half-mark (median)
- **Question**: What anchors the adaptive deadline?
- **Resolution**: The half-mark. Wait until ceil(N/2) slots in the phase exit rc==0 with non-empty output (N = slots launched in this phase). The anchor is the elapsed time of the slowest of that completed half (the moment the half-success mark is crossed). This supersedes a per-reviewer fastest-success anchor and is robust to a single fast or empty success anchoring early.
- **Source**: user (Round 1)

## Decision 4: What counts toward the half
- **Question**: Do failures and empty exits count toward the half?
- **Resolution**: No. Only successful, non-empty completions (rc==0 AND non-empty output file) count. Fast crashes and the cited exit-0-empty case cannot drag the anchor down. If fewer than ceil(N/2) ever succeed substantively, no cutoff fires and the round waits to the ceiling (today's behavior).
- **Source**: user (Round 1)

## Decision 5: Cap formula and safety bounds
- **Question**: How is the deadline computed and bounded?
- **Resolution**: `deadline = clamp(multiple x anchor, floor, ceiling)`. Multiple default 2.5 via `LARCH_REVIEWER_STRAGGLER_MULTIPLE` (0 disables and restores wait-for-all; parsed as a float). Floor default 300s via `LARCH_REVIEWER_STRAGGLER_FLOOR_SECONDS`. Ceiling = existing per-reviewer `--timeout` (1860 design / 1800 review-implement). In the issue's example (median ~216s) the deadline is ~540s: keeps every legit reviewer (max ~296s) and cuts the 1674s straggler.
- **Source**: user (Round 1)

## Decision 6: Straggler handling — drop, no fallback
- **Question**: What happens to a reviewer that exceeds the deadline?
- **Resolution**: Killed (`_terminate_launch`: process-group + descendant SIGTERM) and dropped. Waterfall fallback is DISABLED for stragglers: they are NOT appended to `failed`, so they skip phase2 (other-tool) and phase3 (claude) in both fallback-active and `--no-fallback` modes. The round proceeds with the reviews already collected.
- **Source**: issue / user

## Decision 7: Gap 1 — keep straggler drops out of the failure-threshold gate
- **Question**: Should straggler drops count toward the >50% reviewer-failure gate?
- **Resolution**: No. `check_reviewer_failure_threshold` (`python/review_pipeline.py:1391`, wired ~1922) counts `DROPPED_SLOTS_FILE` toward the panel-fail gate. Straggler drops must be distinguishable from genuine failures (separate marker/KV the threshold logic ignores) so intentional cuts never flip `THRESHOLD_OK=false`.
- **Source**: issue

## Decision 8: Gap 2 — do not let an empty success anchor the cap
- **Question**: Can an exit-0-but-empty launch anchor the deadline?
- **Resolution**: No. The half-mark + successful-non-empty anchor (Decisions 3 and 4) subsumes this: a single fast empty success can no longer anchor, because the anchor requires half the panel to produce non-empty successes.
- **Source**: issue / user
