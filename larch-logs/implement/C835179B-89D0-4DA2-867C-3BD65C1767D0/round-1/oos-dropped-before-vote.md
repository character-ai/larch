### OOS_1: [OUT_OF_SCOPE] correctness: regression test coverage gaps
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: The regression test at `python/test_gantt.py:101-119` matches the plan but does not assert the out-of-window label is absent from rendered chart text and does not cover the `progress_report` pre-filtered call path. The test can pass without proving production Gantt behavior or that ghost labels stay out of chart output. Add `assert long_label not in chart` and, if the production path is the acceptance target, add a `progress_report` integration test.

### OOS_2: [OUT_OF_SCOPE] risk-integration: progress_report pre-filters rows before render_gantt
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `_progress_vendor_rows` in `python/progress_report.py` drops fully out-of-window vendor/timing rows before building `GanttRow` lists passed to `render_gantt`. On that path every row in `rows` is also in `filtered`, so this diff is a no-op for production reviewer-timing charts. If #5587 reproduces only on `progress_report` output, the root cause may lie elsewhere (e.g. row capping via `_cap_gantt_rows_reserving_apply`). The fix hardens the generic `render_gantt`/CLI contract; a `progress_report` integration test was not plan-required, and misalignment from capped-off rows would be a separate scenario. Pre-existing caller behavior; not introduced or amplified by this diff.

### OOS_3: [OUT_OF_SCOPE] correctness: out-of-window long label shrinks track on default-width path
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: On the default-width path (`python/gantt.py:85-86`), an out-of-window row with a very long label now shrinks the track via `90 - label_width - duration_width - 4` even though that label is not rendered. That is consistent with “reserve width for all names,” but can produce a wide left margin and a very narrow bar. Intentional plan behavior; not a regression for in-window rendering.

### OOS_4: [OUT_OF_SCOPE] code-quality: regression test omits corner/edge alignment checks
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The new regression test at `python/test_gantt.py:101-119` checks left `│` alignment via `_border_cols` but does not assert `└`/`┘` or right-edge alignment the way `test_edges_align` does. Extra coverage polish; the new test already covers the reported bug mechanism.

### OOS_5: [OUT_OF_SCOPE] risk-integration: new test missing from shard assignments
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `test_label_width_uses_all_rows_not_just_filtered` is not listed in `python/shard-assignments.json`. `python/conftest.py` round-robins unassigned nodeids into sharded CI, so the test still runs; this is shard-balancing hygiene, not a coverage gap for this fix.

### OOS_6: [OUT_OF_SCOPE] risk-integration: existing fixture out-of-window label too short to expose bug
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `_lines()` / `test_edges_align` include an out-of-window `"outside"` row, but that label is shorter than in-window labels, so the old filtered-only `label_width` logic would still pass. Belt-and-suspenders hardening of an existing fixture, not a gap in the plan-mandated regression test for #5587.
```

**Merge notes**

- **FINDING_3 + FINDING_7 (input)** → **FINDING_3 (output)**: same behavioral risk (`progress_report` drops OOW rows before `render_gantt`, making the diff a production no-op); merged under `[OUT_OF_SCOPE]` with both edge-cases and testing slots attributed.
- **FINDING_1** kept separate from OOS `progress_report` items: in-scope correctness challenge to plan/fix effectiveness; OOS items kept distinct per source tagging.
- **FINDING_2** kept separate from **FINDING_5**: in-scope test gap (nit) vs OOS alignment-polish (nit); different fixes/paths.
- **Suggested revisions** omitted for all slots: every source listed only the placeholder “Address the concern above,” with actionable detail already embedded in **Concern** text.

