### [Plan Review] FINDING_1

### FINDING_1: `_run_round` → `_surface_dropped_reviewer_warning` handoff underspecified
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan defines `_surface_dropped_reviewer_warning(..., threshold_env, dropped_slots_file, panel_manifest)` and STRAGGLER backstop logic that reads dropped-slots TSV and/or manifest for `dyn-*` evidence, but `_run_round` does not pin how those inputs are resolved. `DROPPED_SLOTS_FILE` is emitted on `dispatch_panel` stdout but is not persisted into `review-core.env` rows today; `_core_common_rows` omits `DYNAMIC_*`, `STRAGGLER_DROPPED_COUNT`, `WATERFALL_WARN`, and `DROPPED_SLOTS_FILE`. An implementer that only passes the parsed `core` dict (no threshold sidecar, no dropped-slots path) can skip the backstop TSV/manifest probe, leave `warn_count` at 0 on the #5499 path even when threshold accounting succeeded, and either miss dynamic warnings or regress static-only straggler runs (`STRAGGLER_DROPPED_COUNT=1`, `DYNAMIC_*=0`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `review_pipeline.py` review-core, append `DROPPED_SLOTS_FILE`, `STRAGGLER_DROPPED_COUNT`, `DYNAMIC_FAILED_SLOTS`, `DYNAMIC_DROPPED_SLOTS`, and `WATERFALL_WARN` to emitted `rows` (same pattern as `PARSE_FAILED_COUNT`). In `_run_round`, call `_surface_dropped_reviewer_warning` once after the degraded-retry loop with `threshold_env=round_dir/"review-core-threshold.env"`, `panel_manifest=round_dir/"panel-manifest.ndjson"`, and `dropped_slots_file=Path(core["DROPPED_SLOTS_FILE"])` when set else the first `round_dir.glob("*.output-files.dropped-slots")` or `*.dropped-slots` match.
  - From Cursor-Innovation: Firm-require `_run_round` to call `_surface_dropped_reviewer_warning` with `threshold_env=round_dir / "review-core-threshold.env"`, `dropped_slots_file` resolved from dispatch/`*.output-files.dropped-slots`, and `panel_manifest=round_dir / "panel-manifest.ndjson"`; alternatively require `rows.extend` of `DYNAMIC_FAILED_SLOTS`, `DYNAMIC_DROPPED_SLOTS`, `STRAGGLER_DROPPED_COUNT`, `WATERFALL_WARN`, and `DROPPED_SLOTS_FILE` onto every post-threshold `ReviewCoreResult` before any `panel-failed` return, plus an integration test with `REVIEW_CORE_STATUS=panel-failed`.
  - From Cursor-Requirements: Pin the `_run_round` call: pass `threshold_env=round_dir / "review-core-threshold.env"`, `panel_manifest=round_dir / "panel-manifest.ndjson"`, and `dropped_slots_file` from `review-core-dispatch.env` `DROPPED_SLOTS_FILE` (or a round-dir `*.dropped-slots` glob). Alternatively, append `DYNAMIC_*` and `STRAGGLER_DROPPED_COUNT` to review-core result rows at threshold time so `core` alone is sufficient.


### [Plan Review] FINDING_2

### FINDING_2: Static `generalist` dropped-row fallback missing carve-out
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The plan's `_dropped_reviewer_output_base` fallback maps every static slot through `{tool}-specialist-{slot}-output.txt`. The `generalist` slot's real basename is `codex-generalist-output.txt` (see `_static_slug_for_file`). On a manifest miss, a dropped `generalist` row resolves to `codex-specialist-generalist-output.txt`, is skipped or miscounted, and `FAILED_SLOTS`/`COUNTED_SLOTS` stay low even though a static panel member dropped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: A dropped `generalist` row with no manifest hit is skipped from threshold accounting, weakening static slot coverage adjacent to the dynamic fix. Add an explicit fallback branch: `slot == "generalist"` and `tool == "codex"` → `codex-generalist-output.txt` (before the generic specialist template), and add a dropped-row unit test for manifest miss.


### [Plan Review] FINDING_8

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:17-22
- **Concern**: [SCOPE-REDUCTION] Firm diagnostics preservation branch exceeds issue acceptance criteria. Scenario: The issue requires dynamic slot accounting, threshold inclusion, dropped-slots ledger visibility, and Warnings via `execution-issues.md`. The firm plan still mandates `agent_waterfall` bounded stderr copies, `_finalize_dropped_reviewer_round`, `run_logs.py` allowlist expansion for `dropped-*-*.txt`, `SECURITY.md`, and extra harness surface without changing whether dynamic drops count as failures or whether warnings fire. That is ~150+ lines of artifact-policy work beyond the stated acceptance criteria.
- **Proposed resolution**: Drop the firm diagnostics/run-log/SECURITY branch; keep waterfall `*.dropped-slots`, threshold `DYNAMIC_*` KVs, `progress_report` labeling from committed TSV plus `panel-manifest.ndjson`, and `review_and_fix` post-retry warning surfacing only. Treat stderr preservation as a separate follow-up issue if still wanted.


