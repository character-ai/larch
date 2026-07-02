# Review Round 2

- Mode: `diff`
- 6 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: agent_voters._panel_artifact_context missing round-N subdirectory fallback
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-panel-env
- **Severity**: important
- **Concern**: `_panel_artifact_context` lacks the `round-{N}/` subdirectory fallback that `review_dispatch_panel` gained in round 2. When `review_tmpdir` is a run root and round-scoped outputs live under `round-{N}/`, specialists log to `round-{N}/panel-prompt-sizes.tsv` but voters log to the parent tmpdir, splitting one panel round across two TSVs. Telemetry fragments, `review log-phase` sibling auto-write may only see the run-root copy, and committed review/implement round artifacts can miss voter rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Mirror review_dispatch_panel artifact-dir resolution (or extract a shared resolve_panel_artifact_dir helper) and use opts.round_num when choosing review_tmpdir/round-{N}/.
  - From dyn-dyn-panel-env: Mirror the `review_dispatch_panel` fallback in `_panel_artifact_context()` (`round_subdir = review_tmpdir / f"round-{round_num}"; use it when `is_dir()`), pass that directory through `--panel-artifact-dir` and `build_panel_dispatch_env(round_dir=...)`, and add a voter dispatch test analogous to the dispatch-panel round-subdir harness.


### FINDING_2: review_aggregate._artifact_dir_for_aggregation missing round-N subdirectory fallback
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-panel-env
- **Severity**: important
- **Concern**: `_artifact_dir_for_aggregation` has the same missing `round-{N}/` fallback; `review_core` does not pass round-num into aggregate-findings. With run-root plus `round-{N}/` layout, aggregator rows land at the run root while specialist rows land under `round-{N}/`, so a single review cycle can produce separate TSVs (specialists, aggregator, voters). Per-round panel cost is fragmented, `measure_panel-cost` under-reports combined round telemetry, and per-round committed artifacts and sibling auto-publish paths are incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add --round-num to aggregate-findings, pass it from review_core_body, and resolve artifact_dir with the same helper used by dispatch-panel.
  - From dyn-dyn-panel-env: Add the same `round-{round_num}` subdirectory probe used in `review_dispatch_panel.py:726-729`, prefer that directory when present, and extend `test_review_aggregate.py` to assert aggregator rows materialize under the round-local TSV for that layout.


### FINDING_4: _panel_slot_kind_from_env mis-tags dynamic design plan-review slots
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: important
- **Concern**: Design dynamic plan-review slots from `python/larch/review/plan_review_panel.py:250-251` use names like `dyn-cursor-plan-*`, but `_panel_slot_kind_from_env()` returns `specialist` for any `dyn-` slot before checking `plan-review` phase or `design` site. This mis-tags dynamic design plan-review prompt rows as code-review specialists, so `panel-prompt-sizes.tsv` and `token measure-panel-cost` split those costs into the wrong slot bucket.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Classify `phase=plan-review*` or `site` starting with design as `plan-review` before the generic `dyn-` specialist fallback, while keeping review/code dynamic slots as `specialist`.


### FINDING_5: measure_panel_cost does not reject symlinked panel-prompt-sizes.tsv files
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: blocking
- **Concern**: `measure_panel_cost()` glob-reads every matching `panel-prompt-sizes.tsv` without rejecting symlinks. A malicious or malformed committed log can add `larch-logs/review/<run>/panel-prompt-sizes.tsv` as a symlink to `/dev/zero` or another outside path, causing the new aggregation CLI to hang or read outside the log tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Filter to regular non-symlink files before opening, matching the existing run-log scanners' no-symlink pattern.


### FINDING_6: Missing plan-review panel-prompt-sizes.tsv materialization tests
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: Plan-required design plan-review TSV materialization tests are missing. Panel/voter tests stub waterfall/Popen and only check `--panel-artifact-dir` argv. Removing `append_panel_prompt_size` from design producers would not fail CI, so design run logs could ship without per-slot sizes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add integration tests asserting specialist and voter rows land in plan-review/round-N/panel-prompt-sizes.tsv and no top-level design TSV is created.


### FINDING_7: Missing aggregator panel-prompt-sizes.tsv row materialization tests
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: important
- **Concern**: Plan-required aggregator TSV materialization tests are missing for plan and code modes. Existing coverage stops at argv/env forwarding (`test_aggregate_forwards_panel_artifact_dir_and_env` only captures env via `AGGREGATE_DISPATCH_SH`); no test verifies aggregator rows in `panel-prompt-sizes.tsv` with `slot_kind=aggregator` and `agent_file=agents/orchestrator-aggregator.md`. Aggregator instrumentation or launcher-side prompt-file logging could be removed without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add plan-mode and code-mode tests that materialize aggregator rows with agent_file=agents/orchestrator-aggregator.md under the expected artifact_dir.
  - From codex-specialist-testing: Add plan-mode and code-mode aggregate tests that run through the real waterfall/launcher path or a count-only harness that exercises `append_panel_prompt_size`, then assert the expected TSV path, `slot_kind=aggregator`, and `agent_file=agents/orchestrator-aggregator.md`.


