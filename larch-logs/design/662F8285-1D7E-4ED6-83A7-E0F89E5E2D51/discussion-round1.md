## Decision 1: OOS_1 fix status
- **Question**: Is the stale scout manifest across review rounds already fixed?
- **Resolution**: Yes. `step3_loop_clear_stale_scout_manifest()` in `review-design-step3-loop.sh:311-314` clears the manifest before calling `revise-plan-with-waterfall.sh`. Added in commit `cec11db39` (issue #4061).
- **Source**: codebase

## Decision 2: OOS_2 fix status
- **Question**: Are the design drafter launchers already applying `--filter-manifest`?
- **Resolution**: Yes. Both `launch-codex-drafter.sh` and `launch-claude-drafter.sh` call `scout-plan-archetypes-wrapper.sh --filter-manifest` after `parse-drafter-output.py`. Added in commit `cec11db39` (issue #4061). Remaining gap in `parse-drafter-output.py` to be investigated during plan drafting.
- **Source**: codebase

## Decision 3: OOS_3 fix status
- **Question**: Is the Claude fallback per-round scout issue already fixed?
- **Resolution**: Yes. `run-step5-review.sh:235-236` passes `--dynamic-archetypes 0` when no eligible marker exists. Added in commit `cec11db39` (issue #4061).
- **Source**: codebase

## Decision 4: OOS_4 primary remaining work
- **Question**: Is `normalize_coder_scout_manifest` still divergent from `filter_and_cap_manifest`?
- **Resolution**: Yes. The function in `step2-implement.sh:488-552` has a shorter reserved list (missing `arch`, `edge`, `innovation`, `pragmatic`, `requirements` vs `filter_and_cap_manifest` in `scout-plan-archetypes-wrapper.sh`). Added in commit `cec11db39` (issue #4061) but with incomplete reserved list.
- **Source**: codebase

## Decision 5: OOS_4 fix direction
- **Question**: Should `normalize_coder_scout_manifest` delegate to `--filter-manifest` or just update the reserved list?
- **Resolution**: Delegate — replace the inline jq with a call to `scout-plan-archetypes-wrapper.sh --filter-manifest`. Single source of truth.
- **Source**: user

## Decision 6: OOS_1 — delete manifest direction
- **Question**: After plan revision in rounds 2+, should the scout manifest be deleted (static-only) or re-scouted?
- **Resolution**: Delete (static-only rounds 2+). Already implemented correctly.
- **Source**: user (confirmed by codebase: already done)
