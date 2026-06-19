## Plan

### Approach

Implement the cutoff in the shared waterfall reaper, but keep it inactive unless a reviewer caller passes a new opt-in flag.

Use this policy:

- Add `--reviewer-straggler-cutoff` to `agent dispatch-waterfall`.
- Default inactive when the flag is absent.
- Default active for reviewer panels that pass the flag.
- Arm the deadline only after a successful quorum completes.
- Compute quorum as `ceil(successful_phase_slots * quorum_fraction)`.
- Use only exit `0` launches for quorum.
- Compute `deadline = clamp(multiple * quorum_anchor_elapsed, floor, ceiling)`.
- Use `opts.timeout` as the ceiling.
- Kill remaining phase launches at the deadline.
- Mark killed slots as `straggler-dropped`.
- Do not feed `straggler-dropped` slots into phase2 or phase3 fallback.
- Keep genuine crashes, empty outputs, result-gate misses, and collector failures on today's fallback path.

Add env tuning:

- `LARCH_REVIEWER_STRAGGLER_MULTIPLE`, default `3`; exact `0` disables.
- `LARCH_REVIEWER_STRAGGLER_FLOOR_SECONDS`, default `300`.
- `LARCH_REVIEWER_STRAGGLER_QUORUM_FRACTION`, default `0.5`.

Use conservative parsing:

- Invalid multiple falls back to `3`.
- Exact multiple `0` disables.
- Invalid floor falls back to `300`.
- Invalid quorum fraction falls back to `0.5`.
- Clamp quorum fraction to valid `0 < fraction <= 1` behavior by falling back on invalid values.

### Files to modify/create

### UPDATED: python/agent_waterfall.py

Add the core cutoff.

- Add `import math` and `import time`.
- Add `reviewer_straggler_cutoff: bool = False` to `Options`.
- Parse `--reviewer-straggler-cutoff`.
- Update `_USAGE`.
- Add helper readers:
  - `_reviewer_straggler_multiple() -> float`
  - `_reviewer_straggler_floor_seconds() -> float`
  - `_reviewer_straggler_quorum_fraction() -> float`
- Add a small finalize helper for completed launches:
  - close stderr handle
  - write `<output>.done` when absent
  - remove from `_ACTIVE_LAUNCHES`
  - remove from `_DISPATCH_LAUNCHES`
- Rewrite `_reap_phase(launches, opts) -> set[int]`.

Reaper behavior:

- Return an empty set when:
  - no launches
  - opt-in flag absent
  - multiple is `0`
  - fewer than 2 launches are in the phase
- Poll all remaining launches together on the current `0.05s` cadence.
- Track elapsed time with `time.monotonic()`.
- When a launch exits:
  - finalize it
  - if `rc == 0`, append its elapsed time to successful completions
- Once successful completions reach quorum:
  - anchor on the quorum-th successful elapsed time
  - compute the deadline once
  - do not move the deadline later
- When elapsed time reaches the deadline:
  - call `_terminate_launch()` for each remaining launch
  - write its `.done` file if still absent
  - remove it from active launch lists
  - add its `idx` to the returned straggler set
- If no quorum is ever reached, wait for all launches as today.

Update `_collect_phase`:

- Call `_reap_phase(launches, opts)`.
- For each straggler index:
  - set `drops[idx] = DropState("straggler-dropped", "reviewer exceeded quorum-anchored deadline")`
  - leave `final_outputs[idx]` empty
  - do not append it to `failed`
- Run `agent collect-results --summary-only` only for non-straggler launches.
- Preserve current block-to-launch mapping by collecting and iterating over a filtered launch list.

Update fallback flow:

- Only `failed` indexes feed phase2 and phase3.
- Straggler-dropped slots never enter the fallback queues.
- Existing non-straggler failures keep current behavior.

Update output assembly:

- Build `ALL_OUTPUT_FILES` and `ALL_OUTPUT_TOOLS` by skipping empty `final_outputs` unconditionally.
- Update `_write_paths_file` to skip empty outputs unconditionally.
- Write the dropped-slots sidecar when either:
  - `opts.no_fallback` is true, or
  - at least one straggler was dropped.
- Emit `STRAGGLER_DROPPED_COUNT=<N>` every run.
- Include `WARN=reviewer-straggler-dropped` when `N > 0`.
- Preserve the existing cost-fallback warning by assembling warnings in a list and emitting one `WARN` value only when non-empty.
- Keep `DISPATCH_OK` semantics aligned with current degraded dispatch behavior.
- Mark `STATIC_DISPATCH_OK` or `DYNAMIC_DISPATCH_OK` false for dropped slots based on slot name, matching current drop reporting.

### UPDATED: python/plan_review_panel.py

Pass the opt-in flag only for the reviewer panel dispatch.

- Add `--reviewer-straggler-cutoff` to the `agent dispatch-waterfall` argv in `panel-dispatch`.
- Do not add it to voter dispatch.

### UPDATED: python/review_pipeline.py

Pass the opt-in flag only for code-review reviewer panels.

- Add `--reviewer-straggler-cutoff` to `waterfall_args` in `dispatch-panel`.
- Keep existing `--no-fallback` logic unchanged.
- Do not add the flag to code-review voters or aggregation.

### UPDATED: python/test_agent_waterfall.py

Add focused tests for the reaper and collection behavior.

Cover:

- Opt-in cutoff drops a slow straggler after quorum and keeps fast reviewers.
- Dropped straggler does not enter phase2 or phase3 when fallback is active.
- Dropped straggler does not relaunch when `--no-fallback` is active.
- Missing opt-in flag preserves wait-for-all behavior.
- `LARCH_REVIEWER_STRAGGLER_MULTIPLE=0` preserves wait-for-all behavior.
- Quorum uses the quorum-th successful reviewer, not the first success.
- Fast non-zero exits do not count toward quorum.
- Floor is enforced.
- Ceiling clamps to `opts.timeout`.
- Fewer than 2 launches disables cutoff.
- No quorum disables cutoff.
- `STRAGGLER_DROPPED_COUNT=0` emits without warning when no drop occurs.
- `STRAGGLER_DROPPED_COUNT>0`, `WARN=reviewer-straggler-dropped`, and `DROPPED_SLOTS_FILE` emit when a drop occurs.
- `ALL_OUTPUT_FILES` and the paths sidecar omit empty straggler slots in fallback-active mode.

Prefer fast unit-style tests with fake processes and monkeypatched `time.monotonic()` where possible. Avoid sleeping for the default `300s` floor.

### UPDATED: python/test_plan_review_panel.py

Update or add a small argv test for reviewer panel dispatch.

- Assert `--reviewer-straggler-cutoff` is passed by `plan-review panel-dispatch`.
- Ensure the existing waterfall stub accepts the new flag.
- Do not assert the flag for voter dispatch.

### UPDATED: python/test_review_pipeline.py

Update the existing `dispatch-panel` waterfall argv test.

- Assert `--reviewer-straggler-cutoff` is present for reviewer panel dispatch.
- Keep the existing `--no-fallback` assertion for both-vendor cases.
- Do not add the flag to voter or aggregator expectations.

### UPDATED: docs/configuration-and-permissions.md

Document the new reviewer cutoff knobs near the external reviewer configuration section.

Include:

- The cutoff applies only to reviewer panels:
  - `/design` plan-review
  - `/implement` review
  - `/review` code-review
- Voting, decomposition, and aggregation keep wait-for-all behavior.
- `LARCH_REVIEWER_STRAGGLER_MULTIPLE`
  - default `3`
  - exact `0` disables and restores wait-for-all
- `LARCH_REVIEWER_STRAGGLER_FLOOR_SECONDS`
  - default `300`
- `LARCH_REVIEWER_STRAGGLER_QUORUM_FRACTION`
  - default `0.5`
- Existing per-reviewer `--timeout` remains the absolute ceiling.
- Dropped stragglers are killed and excluded from waterfall fallback.
- Genuine failures and empty outputs still use existing fallback behavior.

### Edge cases

- **No opt-in flag:** wait for all launches as today.
- **Multiple `0`:** wait for all launches as today.
- **No successful quorum:** wait for all launches as today.
- **Fast crash:** does not anchor the deadline.
- **Single launch:** no cutoff.
- **Floor greater than ceiling:** clamp to the ceiling.
- **All finish before deadline:** no drop.
- **Fallback-active straggler:** leave output empty, omit from paths, do not fallback.
- **No-fallback straggler:** same drop reporting as other no-fallback dropped slots.
- **Cost warning plus straggler warning:** emit both in one warning value without changing no-straggler output.

### Failure modes

- **Over-aggressive cutoff:** users can raise the multiple, raise the floor, raise quorum, or set multiple to `0`.
- **Process tree survives SIGTERM:** reuse `_terminate_launch()` so existing process-group and descendant cleanup applies.
- **Collector block mismatch after filtering:** collect only non-straggler launches and iterate over that same filtered list.
- **Downstream paths parsing:** omit empty outputs from `ALL_OUTPUT_FILES` and paths files in all modes.

### Testing strategy

Run:

- `python3 -m pytest python/test_agent_waterfall.py`
- `python3 -m pytest python/test_plan_review_panel.py python/test_review_pipeline.py`
- `make py-lint`
- `make py-test`
- `make lint`

## Acceptance

- Reviewer panels (`/design` plan-review, `/implement` review, `/review` code-review) pass `--reviewer-straggler-cutoff`; voting, decomposition, and aggregation do not.
- With the flag set, reviewer rounds cap near `clamp(3 * quorum_anchor_elapsed, 300s, opts.timeout)`: the deadline arms only after a successful quorum (`ceil(successful_slots * 0.5)` by default) and anchors on the quorum-th successful reviewer, not the single fastest.
- A reviewer exceeding the deadline is SIGTERM'd and dropped; it does NOT trigger the codex->cursor->claude waterfall fallback, in both `--no-fallback` and fallback-active modes.
- `LARCH_REVIEWER_STRAGGLER_MULTIPLE=0`, a missing opt-in flag, no successful quorum, or fewer than 2 slots each reproduce today's wait-for-all behavior exactly.
- Fast non-zero exits do not anchor the deadline; genuine crashes and empty outputs still fall back as today.
- `STRAGGLER_DROPPED_COUNT` is emitted every run; `WARN=reviewer-straggler-dropped` and the dropped-slots sidecar appear only when a straggler is dropped.
- `python/test_agent_waterfall.py`, `python/test_plan_review_panel.py`, and `python/test_review_pipeline.py` cover the listed cases; `make py-lint`, `make py-test`, and `make lint` pass.

review_status: complete
rounds_completed: 1
diff_lines: 365
