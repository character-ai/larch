## Plan

### Summary

Add an opt-in adaptive straggler cutoff to the reviewer waterfall in `python/agent_waterfall.py`. A reviewer phase waits until half its slots produce a **collector-validated** substantive success (`STATUS` in `{OK, cap_hit}` plus the same result/first-line gates `_collect_phase` already applies), then caps the remaining slots at `clamp(2.5 × half-mark, 300s, --timeout)`. Slots still running at the deadline are killed and dropped with no fallback. Only the two reviewer-dispatch sites opt in (`/design` plan-review, `/implement`+`/review` code-review); voters, the findings aggregator, and the decompose panel keep today's wait-for-all. Straggler drops are excluded from both `check_reviewer_failure_threshold` and the static archetype coverage gate in `review_core`.

### Approach

The chokepoint is `_reap_phase`, which today blocks on every `process.wait()` with no early cutoff and is shared by every `dispatch-waterfall` caller. Two design constraints from Round 1 shape the change:

- **Scope is gated, not global.** Add a valueless `--straggler-cutoff` flag to the dispatcher. The cutoff engages only when that flag is present. Only `python/review_pipeline.py` and `python/plan_review_panel.py` pass it. `python/agent_voters.py`, `python/review_aggregate.py`, and `python/decompose.py` are left untouched, so a cut slot can never drop a vote, a merged finding, or a decomposition piece.
- **Anchor is the half-mark (median), counting collector-validated successes only.** Within a phase of N launched slots, count a slot toward the half only after it exits and passes the **same acceptance predicate `_collect_phase` uses post-`collect-results`**: `STATUS` in `{OK, cap_hit}`, then `result_pattern` / `first_line_pattern` gates when configured. Raw `rc==0`, non-empty file, `NOT_SUBSTANTIVE`, malformed output, and `result-gate-miss` / `format-gate-miss` never count. When `ceil(N/2)` such validated successes have completed, the elapsed time of that half-mark crossing is the anchor. `deadline = clamp(multiple × anchor, floor, ceiling)`. Fast crashes, empty exits, and collector-rejected outputs cannot arm the cutoff.

**Anchor validation mechanics.** Extract a shared `_slot_collector_accepted(launch, opts, result_pattern, first_line_pattern) -> bool` in `agent_waterfall.py` that:
1. Runs `agent collect-results --timeout <opts.timeout> --summary-only <launch.output>` for the finished slot.
2. Parses the summary block via existing `_parse_block` / gate helpers.
3. Returns `True` only when `_collect_phase` would assign `final_outputs[idx]` (not append to `failed`).

`_reap_phase` takes `result_pattern` and `first_line_pattern` from `dispatch_waterfall` (same patterns `_collect_phase` already compiles). On each poll-tick finish, when `cutoff_enabled`, call `_slot_collector_accepted` before incrementing the half-mark counter. `_collect_phase` keeps its batch `collect-results` call unchanged; the per-finish probes during reap are anchor-only and idempotent with the later full collect.

Two env readers mirror the existing `LARCH_FALLBACK_CLAUDE_WARN_THRESHOLD` pattern: `_straggler_multiple()` reads `LARCH_REVIEWER_STRAGGLER_MULTIPLE` (float, default 2.5; `<= 0` disables and restores wait-for-all; unparseable falls back to 2.5) and `_straggler_floor()` reads `LARCH_REVIEWER_STRAGGLER_FLOOR_SECONDS` (int, default 300). The ceiling stays the existing per-reviewer `--timeout` (1860 design / 1800 review-implement); the cutoff only ever fires below it.

Disabling fallback for a straggler is mechanical: straggler indexes are returned from `_reap_phase` and `_collect_phase` records them as a distinct `DropState("straggler-dropped", ...)` and skips appending them to `failed`. Only `failed` indexes feed phase2 (other-tool) and phase3 (claude), so straggler slots skip both, in fallback-active and `--no-fallback` modes alike. Their `final_outputs` entry stays empty and is excluded from the paths file and `ALL_OUTPUT_FILES`.

**Gap 1 (failure threshold).** `check_reviewer_failure_threshold` skips `straggler-dropped` rows in `DROPPED_SLOTS_FILE` before counting static failures.

**Gap 3 (static coverage).** `_static_coverage_reason` gains an optional `dropped_slots_file` argument. A new `_straggler_excused_static_slugs(dropped_file)` helper reads tab rows, keeps rows where `reason == "straggler-dropped"` and the slot is a static archetype (not `dyn-`), and returns those slug names. When computing `missing = expected - success`, subtract `straggler_excused` so intentional straggler cuts on the sole vendor for an archetype do not flip `COVERAGE_GATE_OK=false` while `THRESHOLD_OK=true`. `review_core` passes the same `DROPPED_SLOTS_FILE` path already threaded into the threshold check.

### Files to modify/create

### UPDATED: `python/agent_waterfall.py`

Core change.

- Add `import time` to the stdlib imports.
- Add two env readers near the existing helpers: `_straggler_multiple() -> float` (env `LARCH_REVIEWER_STRAGGLER_MULTIPLE`, default 2.5, `<= 0` disables, unparseable falls back to 2.5) and `_straggler_floor() -> int` (env `LARCH_REVIEWER_STRAGGLER_FLOOR_SECONDS`, default 300, unparseable falls back to 300).
- Add `_slot_collector_accepted(launch, opts, result_pattern, first_line_pattern) -> bool`: single-output `collect-results --summary-only`, then mirror the `_collect_phase` acceptance branch (`OK`/`cap_hit` + pattern gates). Returns `False` on collector failure, `NOT_SUBSTANTIVE`, empty, `result-gate-miss`, `format-gate-miss`, unreadable result, or non-zero process exit without a keeper status. **Do not** add a separate `_has_nonempty_output` anchor predicate.
- `Options`: add field `straggler_cutoff: bool = False`. `_parse_args`: seed `"straggler_cutoff": False` in `values`, add an `elif arg == "--straggler-cutoff": values["straggler_cutoff"] = True; idx += 1` arm next to the existing `--no-fallback` arm, and pass `straggler_cutoff=bool(values["straggler_cutoff"])` to the `Options(...)` construction. Extend `_USAGE` to mention the flag.
- Rewrite `_reap_phase` into one concurrent poll loop. New signature `_reap_phase(launches, opts, result_pattern, first_line_pattern) -> set[int]` returning straggler-dropped slot indexes (`launch.idx`):
  - `cutoff_enabled = opts.straggler_cutoff and _straggler_multiple() > 0 and len(launches) >= 2`.
  - `start = time.monotonic()`; `needed = (len(launches) + 1) // 2`. Poll all pending launches with `process.poll()` on the existing 0.05s cadence (`time.sleep(0.05)` between ticks). On each finish: close stderr, write `.done` with the rc when absent, drop from `_ACTIVE_LAUNCHES`/`_DISPATCH_LAUNCHES` (preserve current reap side effects).
  - Track validated successes: when `cutoff_enabled` and the anchor is unset and `_slot_collector_accepted(...)` returns `True`, increment a counter; when it reaches `needed`, set `anchor = elapsed` (the slowest validated success of the half so far) and `deadline = min(float(ceiling), max(multiple * anchor, float(floor)))`, `ceiling = int(opts.timeout)`.
  - When a deadline is set and `time.monotonic() - start >= deadline`, `_terminate_launch(...)` each remaining launch, write its `.done`, drop it from the active lists, add its `idx` to the straggler set, and stop.
  - When `cutoff_enabled` is False or no half-mark is ever reached, never set a deadline and wait for every launch exactly as today. Returns an empty set.
- `_collect_phase`: change the `_reap_phase(launches)` call to `straggler_idxs = _reap_phase(launches, opts, result_pattern, first_line_pattern)`. At the top of the per-launch loop, when `launch.idx in straggler_idxs`, set `drops[idx] = DropState("straggler-dropped", "cut at adaptive straggler deadline")` and `continue`. Reuse `_slot_collector_accepted` logic inside the existing batch collect loop via a shared `_apply_collector_block(...)` helper to avoid drift between anchor and final acceptance.
- Output assembly: drop empty `final_outputs` entries unconditionally instead of only under `opts.no_fallback`. Change the `ALL_OUTPUT_FILES`/`ALL_OUTPUT_TOOLS` loop guard from `if opts.no_fallback and not output:` to `if not output:`, and change `_write_paths_file` to skip empty outputs regardless of `no_fallback`.
- `_write_drops` / `DROPPED_SLOTS_FILE`: call `_write_drops(...)` whenever drops exist rather than gating on `opts.no_fallback`. Keep the `--no-fallback`-only `ALL_SLOTS_DROPPED` emit unchanged.
- Observability: after the phases, compute `straggler_dropped_count = sum(1 for d in drops if d.reason == "straggler-dropped")`, always `emit_kv("STRAGGLER_DROPPED_COUNT", ...)`, and when `> 0` emit `WARN=reviewer-straggler-dropped`.

### UPDATED: `python/review_pipeline.py`

Opt-in flag, Gap 1 threshold fix, and Gap 3 static coverage fix.

- In the reviewer-panel dispatch (`waterfall_args` builder feeding `agent dispatch-waterfall`), append `"--straggler-cutoff"`. Leave the `--no-fallback` logic and `--timeout 1800` unchanged.
- **Gap 1:** in `check_reviewer_failure_threshold`, capture the reason field (`slot, tool, reason, *_rest = [*line.split("\t"), "", "", ""]`) and `continue` when `reason == "straggler-dropped"`, before the `statuses[base] = "ERROR"` / `failed += 1` / `dropped_static += 1` block.
- **Gap 3:** add `_straggler_excused_static_slugs(dropped_file: Path) -> set[str]` that parses `DROPPED_SLOTS_FILE` rows (`slot`, `tool`, `reason`, ...), keeps static slots (`not slot.startswith("dyn-")`, `tool in {codex, cursor}`) with `reason == "straggler-dropped"`, and returns the slot names (archetype slugs).
- Extend `_static_coverage_reason(collector, manifest, outputs, *, dropped_slots_file: str = "") -> str`: when `dropped_slots_file` is a readable file, compute `excused = _straggler_excused_static_slugs(Path(dropped_slots_file))` and set `missing = sorted((expected - success) - excused)` instead of `sorted(expected - success)`.
- In `review_core` (~1946), pass the already-resolved `dropped` path into coverage: `_static_coverage_reason(collector_results, Path(panel_manifest), external_array + claude_array, dropped_slots_file=dropped)`.

### UPDATED: `python/plan_review_panel.py`

Opt-in flag for `/design` plan-review. Append `"--straggler-cutoff"` to the `dispatch-waterfall` argv list (alongside `--slots-file`, `--plan-file`, `--timeout`, etc.). Fallback stays active for `/design`; straggler slots simply skip it.

### UPDATED: `python/test_agent_waterfall.py`

Reuse the existing real-subprocess stub harness. Add tests with low `LARCH_REVIEWER_STRAGGLER_MULTIPLE` / `LARCH_REVIEWER_STRAGGLER_FLOOR_SECONDS`:

- With `--straggler-cutoff` and a multi-slot phase where most slots return fast and one delays past the deadline, the slow slot is SIGTERM'd, recorded as `straggler-dropped`, absent from `ALL_OUTPUT_FILES`/paths file, and present in `DROPPED_SLOTS_FILE`; `STRAGGLER_DROPPED_COUNT` and `WARN=reviewer-straggler-dropped` are emitted.
- **Collector-validated half-mark:** stub `collect-results` so two fast slots return `STATUS=OK` with valid gated output and the half-mark arms; a slot that exits `rc==0` with empty output does NOT count; a fast non-zero crash does NOT count; a slot that exits `rc==0` with non-empty malformed output returning `STATUS=NOT_SUBSTANTIVE` (or failing pattern gates) does NOT count toward the half and does NOT arm the deadline.
- **`cap_hit` counts:** a fast slot returning `STATUS=cap_hit` with non-empty output does count toward the half when collector accepts it.
- Straggler-dropped index never launches phase2 or phase3, in both fallback-active and `--no-fallback` modes.
- Without `--straggler-cutoff`, a slow slot is NOT cut; with `--straggler-cutoff` but `LARCH_REVIEWER_STRAGGLER_MULTIPLE=0`, also not cut.
- Floor enforced; ceiling clamp holds; single-slot phase never cut; fewer-than-half validated successes never arm a deadline.

### UPDATED: `python/test_review_pipeline.py`

- Assert the reviewer-panel dispatch argv includes `--straggler-cutoff`.
- Add `check_reviewer_failure_threshold` case: dropped-slots file whose only rows have `reason=straggler-dropped` keeps `THRESHOLD_OK=true`; a genuine-failure row still flips it.
- Add `_static_coverage_reason` unit case: with `expected` archetypes `{arch, testing}` and success only on `arch`, a dropped-slots file excusing `testing` via `straggler-dropped` returns `""` (no missing archetypes).
- Add `review_core` integration case mirroring `test_review_core_panel_failed_on_missing_static_archetype`: panel has two valid static reviews plus one `straggler-dropped` row for the missing archetype's sole slot; `THRESHOLD_OK=true`, `COVERAGE_GATE_OK=true`, and `review_core` proceeds (does not return `panel-failed`).

### UPDATED: `python/test_plan_review_panel.py`

Teach the dispatch stub to accept the valueless `--straggler-cutoff` flag and assert the flag is forwarded on plan-review dispatch.

### UPDATED: `docs/configuration-and-permissions.md`

Document `LARCH_REVIEWER_STRAGGLER_MULTIPLE` (default 2.5, `0` disables and restores wait-for-all) and `LARCH_REVIEWER_STRAGGLER_FLOOR_SECONDS` (default 300). State: adaptive cutoff applies to reviewer panels only (`/design` plan-review, `/implement`+`/review` code-review); the anchor is the half-mark of **collector-validated** successes; `--timeout` stays the absolute ceiling; timed-out stragglers are dropped without fallback; straggler drops do not count toward the reviewer-failure-threshold gate or the static archetype coverage gate.

### Edge cases

- `multiple <= 0` or flag absent: no deadline, wait-for-all. Single-slot phase: `cutoff_enabled` False.
- Fewer than `ceil(N/2)` collector-validated successes ever: anchor never sets, no cutoff.
- `floor > ceiling` misconfig: `clamp` keeps `deadline <= ceiling`.
- Malformed `rc==0` non-empty, `NOT_SUBSTANTIVE`, and pattern-gate misses: excluded from half-mark; normal collector/failure handling in `_collect_phase`.
- Straggler drop on sole vendor for a static archetype: excused from coverage missing set; other drop reasons (`collector-failure`, `tool-absent`, `result-gate-miss`) still count.
- Fallback phases: half-mark applies per phase; phases with `< 2` slots are never cut.
- Per-finish `collect-results` probes during reap add modest overhead only while waiting for the half-mark; conservative when validation is slow (anchor arms later).

### Failure modes

1. **Over-aggressive cut (anchor too low).** Mitigation: half must be collector-validated OK/cap_hit, plus 2.5× multiple and 300s floor. Signal: rising `STRAGGLER_DROPPED_COUNT`. Knob: raise multiple/floor or set `LARCH_REVIEWER_STRAGGLER_MULTIPLE=0`.
2. **Anchor/collect drift.** If `_slot_collector_accepted` diverges from `_collect_phase` acceptance, the half-mark could arm on slots later rejected (or miss valid anchors). Mitigation: single shared `_apply_collector_block` helper used by both paths; dedicated malformed-output test.
3. **Coverage gate regression (Gap 3).** If straggler-excused slugs are not subtracted, `review_core` panel-fails despite threshold pass. Signal: `THRESHOLD_OK=true` with `COVERAGE_GATE_REASON=no successful static reviewer...` and non-zero `STRAGGLER_DROPPED_COUNT`. Guarded by `_static_coverage_reason` unit test and `review_core` partial-panel test.

### Testing strategy

- New `python/test_agent_waterfall.py` cases cover cutoff, collector-validated half-mark (including malformed rc0 non-empty and NOT_SUBSTANTIVE), fallback suppression, disable paths, and clamp bounds.
- New `python/test_review_pipeline.py` cases cover opt-in argv, Gap 1 threshold exclusion, Gap 3 `_static_coverage_reason` excusal, and `review_core` partial-panel proceed path.
- `python/test_plan_review_panel.py` keeps the stub green and asserts forwarding.

## Acceptance

- Reviewer rounds in `/design`, `/implement`, and `/review` cap wall time near `clamp(2.5 × half-mark, 300s, existing --timeout)` instead of waiting for the slowest reviewer, where the half-mark is the elapsed of the `ceil(N/2)`-th collector-validated success in the phase.
- The cutoff is opt-in: only the reviewer-panel dispatch sites pass `--straggler-cutoff` (`/design` plan-review via `plan_review_panel.py`, `/implement`+`/review` code-review via `review_pipeline.py`). Voters, the findings aggregator, and the decompose panel keep wait-for-all unchanged.
- A straggler exceeding the deadline is SIGTERM'd and dropped; it does NOT trigger the codex→cursor→claude waterfall fallback (verified in both `--no-fallback` and fallback-active modes).
- The anchor counts only collector-validated successes (`STATUS` in `{OK, cap_hit}` plus configured gates). Exit-0-empty, crashes, `NOT_SUBSTANTIVE`, and malformed non-empty outputs never anchor. When fewer than `ceil(N/2)` validated successes ever complete, no deadline arms and the round waits to the ceiling (today's behavior).
- `LARCH_REVIEWER_STRAGGLER_MULTIPLE=0` reproduces today's wait-for-all behavior exactly; `LARCH_REVIEWER_STRAGGLER_FLOOR_SECONDS` floors the deadline; the existing per-reviewer `--timeout` remains the absolute ceiling.
- Straggler drops do NOT count toward `check_reviewer_failure_threshold` (Gap 1) or the static archetype coverage gate `_static_coverage_reason` (Gap 3), so intentional cuts never flip `THRESHOLD_OK=false` or `COVERAGE_GATE_OK=false`.
- Genuine crashes and empty outputs still fall back as today.
- `python/test_agent_waterfall.py`, `python/test_review_pipeline.py`, and `python/test_plan_review_panel.py` cover the listed cases; `make py-lint`, `make py-test`, and `make lint` pass.

review_status: complete
rounds_completed: 2
diff_added: 380
diff_deleted: 50
diff_lines: 430
