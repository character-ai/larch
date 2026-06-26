## Plan

## Approach

Add a narrow verdict path to the existing ground-truth loop with strict corpus eligibility, unified filtered stats, and degraded-evidence guards.

- Keep normal `/analyze-issues` diagnostics non-failing and best-effort.
- Add explicit verdict mode for the capstone decision.
- Default verdict mode to runs starting on or after `2026-06-26` with manifest `larch_version` `>= 52.1.0`.
- Enforce `--min-runs 150` on unique qualifying `run_dir` values, not classifier files or `run_id`.
- Do not encode a numeric go/no-go alignment threshold.
- Let the report show evidence; record human judgment in `docs/ground-truth-verdict.md`.
- Block GO when enrichment is degraded, when targeted OOS issue fetches fail, when the corpus gate fails, or when calibration-incentive (#5461) is not yet shipped.
- Treat `--since-date`, `--min-runs`, and `--min-larch-version` as no-ops unless `--ground-truth-verdict` is set.

**Render/gate ownership (FINDING_1):** Pin a single owner inside `ground_truth_voter_calibration`. Assign `enrichment_degraded` and `targeted_fetch_degraded` onto `stats` at scan start, run the #5461 incentive check, evaluate the final corpus/degradation/incentive gates, and set `stats.gate_result` / `stats.gate_reason` immediately before the sole `_render_ground_truth_report` call. Calibration returns finished report text after that render. The verdict wrapper only applies argv defaults, calls calibration, prints returned text, and returns non-zero from `stats.gate_result`. Do not evaluate or assign gate fields after calibration returns.

**Cache contract (FINDING_2):** When `verdict_mode` filters are active, the tuple written to `_GROUND_TRUTH_ROW_CACHE` contains only rows from `qualifying_run_dirs`, with outcome buckets, metrics, severity metrics, and scan counters computed on that filtered subset before insert. Cache hits must not re-filter a stored superset or reuse unfiltered rows under a verdict filter key.

**Verdict scan counters (FINDING_3):** In verdict mode, evaluate each `run_dir`'s eligibility before incrementing `files_seen`, `skipped_files`, `scanned_rows`, `eligible_rows`, `prose_rows`, or related discovery counters. Ineligible pre-since, below-version, missing-timestamp, missing-version, and `gc-slimmed` dirs must contribute zero scan counters. Do not increment globally and recompute later.

**Renderer split (FINDINGS_7, 9):** When `stats.verdict_mode` is true, `_render_ground_truth_report` uses a verdict header (no diagnostic-only disclaimer), reads `stats.enrichment_degraded` / `stats.targeted_fetch_degraded` / `stats.gate_result` / `stats.gate_reason` only (no parallel enrichment parameter), emits the filtered verdict corpus block only (suppress the legacy unfiltered `Corpus:` subsection), and still emits outcome buckets, per-voter alignment, severity slice, and examples on the filtered subset.

**#5461 shipped resolution (FINDINGS_2, 7):** Resolve #5461 from the coordinator bulk `issues` sequence via `_merged_issue_index(issues, filed_issue_details)` before `filed_issue_details`-only lookup or live `gh issue view`. Use `closedByPullRequestsReferences` (same field and non-empty-refs predicate as `classify_oos_issue_fate` at lines 746-747) and the existing `NOT_PLANNED` rules from `_has_not_planned_signal`.

## Files to modify/create

### UPDATED: python/analyze_issues.py

Add verdict-mode CLI support and coordinator wiring.

- Add constants:
  - `GROUND_TRUTH_VERDICT_DEFAULT_SINCE_DATE = "2026-06-26"`
  - `GROUND_TRUTH_VERDICT_DEFAULT_MIN_RUNS = 150`
  - `GROUND_TRUTH_VERDICT_MIN_LARCH_VERSION = "52.1.0"`
  - `GROUND_TRUTH_VERDICT_INCENTIVE_ISSUE_NUMBER = 5461`
- Add args to live `run_main`, offline `parse_args`, and `main` / `analyze_main`:
  - `--ground-truth-verdict`
  - `--since-date`
  - `--min-runs`
  - `--min-larch-version` (default `52.1.0`; verdict mode only)
- **Verdict-only flag binding:**
  - Parse the new flags on both coordinators, but forward `since_date`, `min_larch_version`, `min_runs`, `verdict_mode=True`, `enrichment_degraded`, and `targeted_fetch_degraded` into `ground_truth_voter_calibration` only when `--ground-truth-verdict` is set.
  - In normal diagnostic mode, ignore `--since-date`, `--min-runs`, and `--min-larch-version` entirely; do not shrink the corpus or change exit behavior when an operator passes a stray flag.
- **Coordinator verdict branch:**
  - In `run_main` and `main` (the `analyze_main` entry path), when `--ground-truth-verdict` is set:
    - Branch before `_build_analyze_report` (in `main`, branch before the empty-issues early return so verdict mode can run on log-root evidence alone).
    - After bulk issue load / enrichment and `_fetch_filed_oos_issue_details` (live path) or filed-details JSON load (offline path), compute `targeted_fetch_degraded` via `_ground_truth_targeted_fetch_degraded(filed_issue_details)` and pass coordinator `issues`, `enrichment_degraded`, and `targeted_fetch_degraded` into the verdict wrapper / `ground_truth_voter_calibration`.
    - Print only the verdict report to stdout.
    - On gate failure, write a clear `ERROR=` line to stderr (observed/required qualifying runs and named `gate_reason` from `stats`) and `return` the wrapper exit code (non-zero).
    - Skip coverage, growth, waste, fate-adjusted, and executive-summary sections entirely.
  - When `--ground-truth-verdict` is absent, preserve today's `_build_analyze_report` path and exit `0`.
- In normal mode:
  - Preserve current behavior.
  - Continue rendering the ground-truth diagnostic as best-effort.
  - Keep `_ground_truth_run_started_at` `updated_at` fallback for diagnostics only.
  - Do not fail when the corpus is below 150.
- In verdict mode:
  - Render only the ground-truth verdict report.
  - Apply verdict defaults: `--since-date 2026-06-26`, `--min-runs 150`, `--min-larch-version 52.1.0`.
  - Exit non-zero when qualifying unique `run_dir` count is below the threshold, when enrichment is degraded, when any targeted filed-OOS `gh issue view` failed, when #5461 is not shipped, or when verdict evidence is otherwise incomplete for a GO decision.

Add strict manifest readers and since-date parsing.

- Add `_parse_ground_truth_since_date(value: str) -> datetime`:
  - Parse `YYYY-MM-DD` to `datetime(..., tzinfo=timezone.utc)` at midnight UTC.
  - Reject invalid input loudly (coordinator exits non-zero on bad argv).
  - Use in both coordinators before calling calibration; never compare naive date-only values to UTC-aware `started_at`.
- Add `_ground_truth_run_started_at_strict(run_dir) -> datetime | None`:
  - Read `manifest.json` / `run-manifest.json` `started_at` only.
  - Never fall back to `updated_at`.
  - Return `None` when `started_at` is missing or unparsable.
- Add `_ground_truth_run_larch_version(run_dir) -> str | None`:
  - Read manifest `larch_version` when present.
  - Return `None` when missing or unparsable.
- Add `_ground_truth_version_meets_floor(version: str | None, floor: str) -> bool`:
  - Compare with a tiny local tuple compare helper (strip leading `v`, split on `.`, zero-pad numeric segments).
  - Treat missing version as ineligible in verdict mode.
- Keep `_ground_truth_run_started_at` unchanged for unfiltered diagnostic mode.
- In verdict eligibility checks, compare strict `started_at >= since_date_utc` using `_parse_ground_truth_since_date`.

Add log-root-relative run-dir identity helpers for filed-OOS joins and accepted evidence.

- Add `_ground_truth_run_dir_key(run_dir: Path, *, log_root: Path) -> str`:
  - Return `run_dir.relative_to(log_root).as_posix()` (for example `implement/run-1`, `design/run-1`).
  - Derive from the run's phase directory under `log_root`, not classifier discovery `panel_kind`.
  - Do not use classifier tokens such as `code-review` in `run_dir_key`; implement classifier discovery uses `code-review` while log paths live under `implement/`.
- Add `run_dir_key: str` to `GroundTruthRow`.
- When building `GroundTruthRow`, keep `run_id = run_dir.name` for display and `panel_kind = prep.panel` (`design` / `code-review`) for metrics display only; set `run_dir_key` from the helper above.
- When emitting filed OOS records in **every** builder path, including `iter_filed_oos_records`, `_join_implement_run_records`, `_parse_oos_issues_created`, `_append_design_accepted_block_records`, `_row_from_block`, `_ambiguous_stable_id_row`, `_ambiguous_rollup_expansion_row`, `_rollup_expansion_shortfall_result`, cap-rollup expansion paths, and related append helpers:
  - Thread `log_root` into emitters as needed.
  - Add `run_dir_key` from `_ground_truth_run_dir_key(run_dir, log_root=log_root)` to every emitted dict.
  - Preserve existing `run_id` basename for backward-compatible display.
- In `ground_truth_voter_calibration`, index filed records by `run_dir_key`, not basename `run_id`:
  - `filed_by_run_key: dict[str, list[Mapping[str, Any]]]`
  - Pass `filed_by_run_key.get(row.run_dir_key, [])` into `_ground_truth_oos_outcome`.
- Update `_match_oos_filed_record` to require `str(record.get("run_dir_key") or "") == row.run_dir_key` before round/title matching; do not match on basename `run_id` alone.
- Add `run_dir_key: str` to `GroundTruthEvidence`.
- Populate `run_dir_key` in `_ground_truth_accepted_finding_evidence` from `row.run_dir_key`.
- Update `_evidence_later_than_row` same-run ordering to compare `evidence.run_dir_key == row.run_dir_key` (not basename `run_id` alone).
- Update accepted-evidence dedupe in `_candidate_evidence_for_row` to key on `(item.run_dir_key, item.title, item.round_num)` instead of `(item.run_id, ...)`.

Extend `GroundTruthStats` with verdict corpus, filter metadata, degradation, and gate fields.

- Add verdict corpus counters:
  - `qualifying_runs: int`
  - `excluded_pre_since_runs: int`
  - `excluded_missing_started_at_runs: int`
  - `excluded_below_version_runs: int`
  - `excluded_missing_version_runs: int`
  - `excluded_gc_slimmed_runs: int` (report-only; never qualify)
  - `qualifying_run_dirs: set[Path]`
- Add filter metadata stored during the scan (for renderer and wrapper reuse):
  - `verdict_mode: bool`
  - `since_date: datetime | None`
  - `min_larch_version: str | None`
  - `min_runs: int`
- Add incentive-era gate fields:
  - `incentive_era_shipped: bool`
  - `incentive_gate_reason: str`
- Add degradation fields for single-stats rendering:
  - `enrichment_degraded: str | None`
  - `targeted_fetch_degraded: str | None`
- Add final gate fields:
  - `gate_result: bool`
  - `gate_reason: str`
- **Update `_copy_ground_truth_stats` to copy every new field above**, including copied `qualifying_run_dirs`, `buckets`, degradation fields, and `gate_result` / `gate_reason`.
- Audit any other stats clone/reset path introduced alongside these fields and keep it in sync with `_copy_ground_truth_stats`.
- Include `(log_root, since_date, min_larch_version, verdict_mode, min_runs)` in `_GROUND_TRUTH_ROW_CACHE` keys so filtered and unfiltered reports cannot share stale rows, stats, or gate thresholds.

Extend `ground_truth_voter_calibration` with a single filtered verdict scan, pre-render gate setup, and internal render.

- Add optional verdict filter parameters:
  - `verdict_mode: bool = False`
  - `since_date`, `min_larch_version`, `min_runs` only when coordinator set `--ground-truth-verdict`
  - `enrichment_degraded: str | None = None` (coordinator value; assign onto `stats` at scan start)
  - `targeted_fetch_degraded: str | None = None` (coordinator helper output; assign onto `stats` at scan start)
- Store the active filter tuple on `GroundTruthStats` at scan start, including `min_runs`.
- Assign coordinator `enrichment_degraded` and `targeted_fetch_degraded` onto `stats` before discovery, incentive check, gate evaluation, and render.
- During discovery, for each non-`gc-slimmed` `run_dir`:
  - When `verdict_mode` and filters are active, evaluate run-dir eligibility **before** incrementing `files_seen`, `scanned_rows`, `eligible_rows`, or any related scan counters for classifier paths under that `run_dir`. Skip ineligible `run_dir` values entirely; do not increment counters for them and do not recompute global totals afterward.
  - Resolve `started_at` with the strict reader when `since_date` is set.
  - Resolve `larch_version` when `min_larch_version` is set.
  - Track exclusion buckets on `GroundTruthStats`.
  - Maintain `qualifying_run_dirs: set[Path]`.
  - Increment `qualifying_runs` only on first sighting of a `run_dir` that passes all verdict filters.
  - Do not count classifier TSV multiplicity or `run_id` basename collisions across `design/` vs `implement/`.
- When verdict filters are active:
  - Build the working row list from qualifying runs only.
  - Recompute all corpus counters, outcome buckets, metrics, and severity metrics on that filtered subset only.
  - Do not mix global unfiltered totals into the verdict corpus block.
  - Compute `large_corpus` from `len(filtered_rows)`, not the full cached historical row list.
  - Build `accepted_evidence` from filtered rows only, keyed by `run_dir_key`.
  - **Before cache insert**, store only `filtered_rows` and the recomputed filtered `stats` in `_GROUND_TRUTH_ROW_CACHE[cache_key]`. Cache hits must return that filtered tuple as-is.
- When verdict filters are inactive:
  - Preserve current unfiltered diagnostic behavior and counters.
- **Pre-render gate sequence inside calibration (FINDING_1):**
  - After outcome/metrics/severity loops on the filtered working row set, run `_ground_truth_calibration_incentive_shipped` with the coordinator `issues` sequence and `filed_issue_details`.
  - Store `incentive_era_shipped` and `incentive_gate_reason` on `stats`.
  - Evaluate final `stats.gate_result` / `stats.gate_reason` once on `stats` in priority order: incentive not shipped, enrichment degraded, targeted fetch degraded, corpus below `min_runs`, else pass.
  - Call `_render_ground_truth_report` exactly once with gate fields already set on `stats`.
  - Return finished report text and stats; do not mutate degradation or gate fields after render.

Add calibration-incentive (#5461) programmatic gate with bulk-issue resolution (FINDINGS_2, 7).

- Add `_ground_truth_calibration_incentive_shipped(*, issues: Sequence[Mapping[str, Any]], filed_issue_details: Mapping[int, Mapping[str, Any]] | None = None, repo: str | None = None) -> tuple[bool, str]`:
  - Resolve #5461 from `_merged_issue_index(issues=issues, filed_issue_details=filed_issue_details or {})` first.
  - If absent from the merged index and `repo` is available, call `gh issue view 5461 --json state,stateReason,closedByPullRequestsReferences` (same subprocess style and field list as `_fetch_filed_oos_issue_details`).
  - Return `(True, "")` only when issue state is `CLOSED`, `stateReason` is not `NOT_PLANNED` per `_has_not_planned_signal`, and `closedByPullRequestsReferences` is a non-empty list (same predicate as `classify_oos_issue_fate` lines 746-747).
  - Return `(False, "calibration_incentive_not_shipped")` when state is open, closed as `NOT_PLANNED`, closed without a non-empty `closedByPullRequestsReferences` list, or otherwise not demonstrably shipped.
  - Return `(False, "calibration_incentive_check_unavailable")` when the merged index lacks #5461 and `gh` or repo resolution fails (conservative NO-GO).
- In verdict mode, run this check inside calibration before final gate evaluation and store results on `GroundTruthStats`.
- Force `gate_result=false` with `gate_reason=incentive_gate_reason` until #5461 is demonstrably shipped, regardless of corpus size or alignment metrics.
- Do not treat `larch_version >= 52.1.0` alone as proof that incentivized scoring shipped.
- Do not request `closingIssuesReferences`; use only `closedByPullRequestsReferences`.

Add enrichment-degraded and targeted-fetch verdict guards.

- Add `_ground_truth_targeted_fetch_degraded(filed_issue_details: Mapping[int, Mapping[str, Any]]) -> str | None`:
  - Return a named reason when any detail dict has `__fetch_failed__` true.
- In the verdict coordinator path, after `_fetch_filed_oos_issue_details` or offline filed-details load:
  - Pass coordinator `issues`, `enrichment_degraded`, and `targeted_fetch_degraded` into `ground_truth_voter_calibration`.
  - Calibration assigns both degradation values onto `stats` before incentive check, gate evaluation, and render.
  - Treat targeted fetch failure like enrichment degradation for gate purposes even when bulk issue enrichment succeeded.
- If `verdict_mode` and (`stats.enrichment_degraded` or `stats.targeted_fetch_degraded`):
  - Still render the verdict report with a prominent degraded-evidence banner naming the reason(s) from `GroundTruthStats`.
  - Force `gate_result=false` with `gate_reason` naming the degradation (`enrichment_degraded` and/or `targeted_fetch_degraded`).
  - Exit non-zero with `ERROR=` aligned to `stats.gate_reason`.
  - Do not treat the output as sufficient evidence for a GO artifact.

Add severity-aware realized-outcome output wired through loop and renderer.

- Extend `GroundTruthVoter` with `severity: str = ""`.
- Populate from `agreement["voters"][*]["severity"]`.
- Add `_ground_truth_update_severity_metrics(...)` that mirrors `_ground_truth_update_metrics`:
  - Iterate only outcomes where `outcome.decisive` is true.
  - Include only ballots with `vote == "YES"`.
  - Use the same `supports_acceptance` / `contradicts_acceptance` alignment rules as per-voter metrics.
- In the `ground_truth_voter_calibration` outcome loop, call `_ground_truth_update_severity_metrics` beside `_ground_truth_update_metrics` for every outcome.
- Add a compact severity slice table for decisive YES votes:
  - panel
  - voter
  - severity
  - decisive YES rows
  - aligned
  - misaligned
  - realized alignment
  - missing-severity rows (decisive YES ballots with blank severity)
- Extend `_render_ground_truth_report` to accept severity metrics and emit the severity slice table in **both** verdict and diagnostic reports (including missing-severity row count).
- Keep existing acceptance alignment metrics unchanged.
- Surface blank-severity coverage explicitly so denominator shrinkage is visible.

Add verdict-mode rendering and a thin wrapper.

- Refactor `_render_ground_truth_report`:
  - When `stats.verdict_mode` is true:
    - Use verdict-oriented header copy (capstone evidence for token-allocation decision); omit the "Diagnostic only..." disclaimer.
    - Read `stats.enrichment_degraded`, `stats.targeted_fetch_degraded`, `stats.gate_result`, and `stats.gate_reason` only; ignore the legacy `enrichment_degraded` function parameter on this branch.
    - Emit the filtered **Verdict corpus** block from `GroundTruthStats` only:
      - since date (`stats.since_date`)
      - min larch version (`stats.min_larch_version`)
      - required runs (`stats.min_runs`)
      - qualifying runs (unique `run_dir`)
      - excluded pre-since / missing-`started_at` / below-version / missing-version / `gc-slimmed` counts
      - incentive-era shipped status and `incentive_gate_reason`
      - enrichment degraded and targeted-fetch degraded status
      - **Gate result:** `PASS` or `FAIL` from `stats.gate_result`
      - **Gate reason:** `stats.gate_reason` (empty when pass)
    - Suppress the legacy unfiltered `Corpus:` subsection (`files_seen`, global `scanned_rows`, etc.).
    - Continue with filtered outcome buckets, per-voter alignment, severity slice, examples, and verdict-oriented notes.
  - When `stats.verdict_mode` is false:
    - Preserve today's diagnostic header, legacy `enrichment_degraded` parameter path, unfiltered `Corpus:` subsection, and severity slice addition.
- Add a thin verdict wrapper around `ground_truth_voter_calibration` that:
  - applies argv defaults when coordinator flags are omitted
  - passes `issues`, degradation values, and verdict filter parameters into calibration
  - prints the returned report text to stdout
  - writes stderr `ERROR=` from `stats.gate_reason` and `stats.qualifying_runs` when `stats.gate_result` is false
  - returns `0` when `stats.gate_result` is true, else non-zero
- Do not assign `gate_result` / `gate_reason` in the wrapper after calibration returns.
- Gate, report, stderr `ERROR=`, and process exit must all read the same `stats.gate_result`, `stats.gate_reason`, and `stats.qualifying_runs` set inside calibration before render.
- On cache hit, `_copy_ground_truth_stats` must preserve qualifying/exclusion tallies, filter metadata, degradation fields, and gate fields so gate and render stay consistent.
- In verdict mode, print the report even when the gate fails.

### UPDATED: python/test_analyze_issues.py

Add targeted regression tests.

- Normal `analyze_main` / `main` still exits 0 with an empty or missing log root when verdict mode is off.
- Normal mode with a stray `--since-date` or `--min-runs` does not shrink the diagnostic corpus or change exit behavior.
- **Integration:** `run_main` with `--ground-truth-verdict` omits `## Executive Summary` and returns non-zero when `--min-runs` is unmet.
- Verdict mode exits non-zero when `--min-runs` is not met.
- Verdict mode exits 0 when enough post-`2026-06-26`, `>= 52.1.0` runs exist and all gates pass (mock #5461 closed with `closedByPullRequestsReferences` and healthy enrichment).
- **Offline bulk JSON:** verdict mode exits 0 when #5461 is present only in the coordinator bulk `issues` dump with closed state, non-`NOT_PLANNED` `stateReason`, and non-empty `closedByPullRequestsReferences`, without calling `gh`.
- `--since-date 2026-06-26` excludes a `2026-06-25` run and includes a `2026-06-26` run at UTC midnight boundary (`_parse_ground_truth_since_date` contract).
- Invalid `--since-date` fails loudly.
- A run with missing `started_at` but recent `updated_at` is excluded from the verdict corpus and counted in the missing-timestamp bucket; diagnostic mode may still use fallback behavior.
- A post-date run with `larch_version: 52.0.6` does not count toward `--min-runs`.
- A run with missing `larch_version` is excluded and counted in the missing-version bucket.
- Two classifier TSVs under one `run_dir` count as one qualifying run.
- Distinct `design/run-1` and `implement/run-1` paths count as two runs when both qualify.
- `design/run-1` filed OOS evidence does not join `implement/run-1` rows and vice versa.
- An implement run with filed OOS evidence joins when `run_dir_key` is `implement/run-1`, not `code-review/run-1`.
- Ambiguous / rollup filed-OOS helper records include `run_dir_key` and do not join across panel roots.
- `gc-slimmed` runs do not count toward `--min-runs`.
- Verdict mode with `enrichment_degraded` exits non-zero and reports degraded evidence from `GroundTruthStats` in the verdict corpus block (not a stale parameter-only banner).
- Verdict mode with a `__fetch_failed__` targeted issue detail exits non-zero, sets `stats.targeted_fetch_degraded` before render, and prints targeted-fetch failure in the verdict corpus block even when bulk enrichment succeeded.
- Verdict mode exits non-zero with `calibration_incentive_not_shipped` when #5461 is open.
- Verdict mode exits non-zero when #5461 is `CLOSED` with `NOT_PLANNED` or without non-empty `closedByPullRequestsReferences`.
- Verdict mode computes `large_corpus_skip` from the filtered row subset, not the full historical cache.
- Verdict corpus counters in the report match `stats.qualifying_runs` and filtered row totals; legacy global `Corpus:` lines are absent in verdict output.
- Verdict corpus block includes since-date, min larch version, required runs, `gate_result`, and `gate_reason` from `GroundTruthStats`.
- Verdict output does not include the diagnostic-only disclaimer.
- A second verdict-mode call in one process with the same filtered cache key preserves `qualifying_runs`, exclusion tallies, and gate fields via `_copy_ground_truth_stats`.
- A cache hit under a different filter key (including mismatched `--min-runs` with the same date/version) does not reuse stale qualifying counts, unfiltered rows, or gate thresholds.
- Cache insert under verdict filters stores only filtered rows (assert row count equals filtered qualifying set, not full log root).
- Verdict mode scan counters (`files_seen`, `scanned_rows`) reflect filtered corpus only; ineligible pre-since `run_dir` values contribute zero scan counters.
- The severity slice includes only decisive YES ballots and excludes a non-decisive YES row.
- The severity slice reports missing-severity decisive YES rows explicitly and appears in rendered verdict output (not helper-only).
- Accepted-evidence dedupe and `_evidence_later_than_row` treat `design/run-1` and `implement/run-1` as distinct via `run_dir_key`.
- Rendered verdict output includes `gate_result` / `gate_reason` in the corpus block before wrapper exit; wrapper does not mutate gate fields after calibration returns.
- Existing ground-truth tests still pass with the default unfiltered diagnostic path.

### UPDATED: .claude/skills/analyze-issues/SKILL.md

Document verdict mode.

- Update usage to include:
  - `--since-date DATE`
  - `--min-runs N`
  - `--min-larch-version VERSION`
- Add a short "Ground-truth Verdict Mode" section.
- State verdict defaults:
  - `--since-date 2026-06-26` (midnight UTC)
  - `--min-runs 150`
  - `--min-larch-version 52.1.0`
- State that `--since-date`, `--min-runs`, and `--min-larch-version` are ignored unless `--ground-truth-verdict` is set.
- State that verdict mode prints only the ground-truth verdict report (no legacy diagnostic corpus subsection) and exits non-zero below the corpus gate, when enrichment is degraded, when targeted OOS issue fetches fail, or when #5461 is not demonstrably shipped.
- State that qualifying runs are unique `run_dir` values with strict `started_at`, not `updated_at`.
- State that filed-OOS joins and accepted-evidence matching are keyed by log-root-relative `run_dir_key` (for example `implement/run-1`, `design/run-1`), not classifier `panel_kind` or basename `run_id` alone.
- State that the verdict report includes an explicit gate PASS/FAIL line aligned with exit code.
- State that #5461 shipped detection consults bulk-loaded issues first and requires `closedByPullRequestsReferences`, not bare `CLOSED`.
- State that no token allocation should ship until:
  - calibration-incentive (#5461) is shipped (mechanical gate checks closed-with-PR, not `NOT_PLANNED`), and
  - `docs/ground-truth-verdict.md` records a GO decision over an eligible post-`52.1.0` incentivized-era corpus.
- Keep `SKILL.md` as a thin coordinator.

### UPDATED: README.md

Update the `/analyze-issues` argument row.

- Add the verdict flags in the command synopsis.
- Keep the description concise.
- Mention that verdict mode gates token allocation on a post-`52.1.0`, post-`2026-06-26`, incentivized-era realized-outcome corpus with strict `started_at` eligibility and a mechanical #5461 shipped check (closed with `closedByPullRequestsReferences`, not `NOT_PLANNED`).
- Note that verdict mode skips the full backlog report, emits a filtered verdict corpus block with explicit gate PASS/FAIL, and returns the wrapper exit code.

### UPDATED: docs/skills.md

Update the `/analyze-issues` section.

- Add the verdict flags to the argument list.
- Explain the default date (UTC midnight), version floor, and unique-`run_dir` run gate.
- Distinguish normal diagnostic mode from verdict mode (verdict-only output, no legacy corpus subsection, non-zero exit on gate failure).
- Note that filter flags are no-ops outside verdict mode.
- Note strict `started_at` filtering, log-root-relative `run_dir_key` filed-OOS joins and accepted-evidence keys, degraded-enrichment NO-GO behavior, targeted-fetch NO-GO behavior surfaced from `GroundTruthStats`, explicit gate PASS/FAIL in the report, bulk-issue resolution for #5461 before `gh`, and the `closedByPullRequestsReferences` shipped gate (not bare `CLOSED`).
- Link the verdict decision to `docs/ground-truth-verdict.md`.

### UPDATED: docs/point-competition.md

Update the Future Plans dependency.

- Replace the open-ended "do not ship token allocation" note with the concrete gate:
  - token allocation remains NO-GO unless calibration-incentive (#5461) is demonstrably shipped and `docs/ground-truth-verdict.md` records GO.
- State that the verdict must use post-`2026-06-26`, manifest `larch_version >= 52.1.0` runs with strict `started_at`.
- State that the CLI mechanically blocks verdict success until #5461 is closed with a non-empty `closedByPullRequestsReferences` list and not as `NOT_PLANNED`.
- State that historical `v51.3.19+` flat-scoring runs are out of scope for this capstone even if they reach 150 runs.
- State that the decision uses human judgment over the generated report, not a hard-coded alignment threshold.

### NEW: docs/ground-truth-verdict.md

Create the committed verdict artifact.

Recommended shape:

- Title: `# Ground-truth Verdict for Token Allocation`
- Scope:
  - incentivized-era validation only; blocked until calibration-incentive (#5461) ships
  - `since-date: 2026-06-26` with strict manifest `started_at` (UTC midnight boundary)
  - `min-larch-version: 52.1.0`
  - `min-runs: 150` unique qualifying `run_dir` values
- Command:
  - `python3 python/cli.py analyze-issues run --ground-truth-verdict --since-date 2026-06-26 --min-larch-version 52.1.0 --min-runs 150`
- Preconditions:
  - calibration-incentive (#5461) closed/shipped with non-empty `closedByPullRequestsReferences` (CLI-enforced via bulk issues or `gh`; not bare `CLOSED` / not `NOT_PLANNED`)
  - enrichment not degraded
  - no targeted filed-OOS `gh issue view` failures
  - corpus gate satisfied
- Corpus gate result:
  - observed qualifying runs
  - since-date / min-larch-version / required-runs thresholds
  - incentive-era shipped status
  - enrichment and targeted-fetch degradation status
  - gate PASS/FAIL and `gate_reason` from the report (must match exit code and stderr `ERROR=`)
  - command exit status
- Verdict:
  - `GO` or `NO-GO`
- Decision:
  - explicit statement for token allocation #4771
- Evidence summary:
  - paste or summarize the generated report's filtered verdict corpus block, outcome buckets, acceptance alignment, severity slice, and missing-severity coverage
- Notes:
  - no numeric alignment threshold was encoded
  - conservative matching can undercount realized outcomes
  - pre-incentive and pre-`52.1.0` runs are excluded by design
  - `design/` and `implement/` runs with the same basename are distinct qualifying runs
  - filed-OOS joins and accepted-evidence matching use log-root-relative keys (`implement/run-1`, not `code-review/run-1`)

If the current corpus is below 150 qualifying runs, enrichment is degraded, targeted fetches failed, or #5461 is not demonstrably shipped, record `NO-GO` with the specific blocking reason. Do not fabricate a positive value-signal verdict.

### MAY_UPDATE: docs/linting.md

Update the `make test-analyze` description only if the new tests make the existing description materially stale.

## Edge cases

- Runs without parsable manifest `started_at` must not qualify for a date-gated verdict, even when `updated_at` is recent.
- Date-only `--since-date 2026-06-26` means midnight UTC on that date; all comparisons use UTC-aware datetimes via `_parse_ground_truth_since_date`.
- Multiple classifier TSVs in one run must count as one qualifying `run_dir`.
- Distinct runs that share a `run_id` basename under different panel roots must not collapse together for corpus counting, filed-OOS joins, or accepted-evidence dedupe.
- `run_dir_key` must come from `run_dir.relative_to(log_root)`, not classifier `panel_kind`; implement rows use `implement/...` even when `panel_kind` is `code-review`.
- Post-date runs with `larch_version < 52.1.0` or missing version must not satisfy `--min-runs`.
- `gc-slimmed` runs may be reported but must not satisfy the corpus gate.
- Normal diagnostics must remain useful on small local fixtures and may keep `updated_at` fallback.
- Stray `--since-date` / `--min-runs` / `--min-larch-version` without `--ground-truth-verdict` must not change normal diagnostics.
- Verdict mode must print only the verdict report and enough filtered context even when it exits non-zero.
- Verdict mode must not present global unfiltered corpus totals as post-since evidence or alongside the verdict corpus block.
- Verdict discovery must not increment scan counters for ineligible `run_dir` values; there is no post-discovery global recompute path.
- Degradation, incentive, and gate fields must be set on `stats` inside calibration before the sole `_render_ground_truth_report` call; the wrapper must not mutate them after return.
- Verdict mode must force NO-GO when enrichment is degraded or any targeted filed-OOS fetch failed, with both reasons visible in the rendered verdict corpus block.
- Verdict mode must force NO-GO when #5461 is open, closed as `NOT_PLANNED`, or closed without non-empty `closedByPullRequestsReferences`, even if the filtered corpus and alignment look healthy.
- Offline replay with #5461 present only in bulk JSON must not require `gh` for the incentive gate.
- Cache hits must not zero out verdict corpus counters, store unfiltered rows under a verdict key, or reuse a cached `min_runs` threshold from a prior argv.
- Verdict coordinators must not call `_build_analyze_report` or return exit `0` on a failed corpus gate.
- Report `gate_result` / `gate_reason` must match stderr `ERROR=` and process exit code.

## Failure modes

- A stale cache key can mix filtered and unfiltered stats or gate thresholds. Key the cache by `log_root`, `since_date`, `min_larch_version`, `verdict_mode`, and `min_runs`; store only filtered rows under verdict keys.
- Caching unfiltered rows under a verdict filter key can produce false GO/NO-GO on cache hits. Recompute and cache the filtered subset only.
- Omitting new fields from `_copy_ground_truth_stats` can make cache hits report `qualifying_runs=0` or stale `gate_result` while rows look healthy. Copy every verdict, degradation, and gate field and add a same-process cache reuse test.
- Forwarding filter flags outside verdict mode can silently shrink diagnostics. Gate coordinator forwarding on `--ground-truth-verdict` only.
- Using `updated_at` for verdict filtering can admit maintenance-rewritten manifests and inflate toward a false GO. Use strict `started_at` only in verdict mode.
- Naive since-date parsing can misclassify boundary runs or raise naive/aware comparison errors. Centralize UTC midnight parsing in `_parse_ground_truth_since_date`.
- Date-only filtering can admit pre-incentive flat-scoring runs. Enforce manifest `larch_version >= 52.1.0` for qualifying runs and a separate #5461 shipped gate.
- Treating any `CLOSED` #5461 as shipped can pass flat-scoring eras. Require non-empty `closedByPullRequestsReferences` and reject `NOT_PLANNED`.
- Requesting `closingIssuesReferences` from `gh` can fail or return empty refs and force false NO-GO. Use `closedByPullRequestsReferences` only.
- Ignoring bulk-loaded `issues` for #5461 can force `calibration_incentive_check_unavailable` when `gh` is down but offline JSON already proves shipped state. Resolve via `_merged_issue_index` first.
- Enforcing `--min-runs` in normal mode would break existing diagnostic use. Gate only verdict mode unless explicitly requested.
- Counting classifier files instead of `run_dir` can satisfy the gate with far fewer real runs. Deduplicate on full `run_dir`.
- Joining filed OOS records by basename `run_id` or classifier `panel_kind` can cross-contaminate `design/run-1` and `implement/run-1`. Key joins by log-root-relative `run_dir_key` on every record builder.
- Accepted-evidence dedupe keyed on basename `run_id` can match wrong-run evidence and flip verdict alignment. Thread `run_dir_key` through `GroundTruthEvidence` and dedupe keys.
- Post-return wrapper gate assignment can print a report missing PASS/FAIL while exit code reflects a later gate. Compute all gates inside calibration before the sole render.
- Divergent gate vs report counts can mislead operators. Compute `qualifying_runs` and `gate_result` once on `GroundTruthStats` before render and reuse for exit gating.
- `large_corpus_skip` on unfiltered rows can disable accepted evidence in a small post-since verdict slice. Compute it on filtered rows only in verdict mode.
- Incrementing global scan counters before verdict eligibility filtering can show qualifying runs from the filtered set beside full-log `scanned_rows`. Skip ineligible dirs before any counter increment.
- Emitting legacy diagnostic `Corpus:` lines in verdict mode can paste contradictory evidence into `docs/ground-truth-verdict.md`. Suppress legacy subsection when `stats.verdict_mode`.
- A severity slice detached from decisive gating or renderer output can overstate calibrated-severity alignment. Wire loop invocation and renderer table in both modes.
- Hidden blank severities can shrink the severity denominator silently. Report missing-severity decisive YES rows explicitly.
- Per-issue `__fetch_failed__` entries that never reach `stats.targeted_fetch_degraded` can hide docked/combined-away OOS fate while the run-count gate passes. Promote targeted fetch failures into verdict NO-GO before render.
- Coordinators that always call `_build_analyze_report` and return `0` make the capstone command non-mechanical. Branch early in `run_main` and `main` and return the wrapper exit code.
- A GO artifact from degraded enrichment, failed targeted fetches, or pre-#5461 flat scoring would answer the wrong question. Force NO-GO and document the precondition.

## Testing strategy

Run focused tests first:

- `python3 -m pytest python/test_analyze_issues.py`

Then run required repo checks for Python changes:

- `make py-lint`
- `make py-test`
- `make lint`

Manual smoke command:

- `python3 python/cli.py analyze-issues run --ground-truth-verdict --since-date 2026-06-26 --min-larch-version 52.1.0 --min-runs 150`

Expected smoke behavior depends on the local corpus:

- If fewer than 150 qualifying unique `run_dir` values exist, it prints the filtered verdict report only (no legacy `Corpus:` subsection, with explicit gate FAIL) and exits non-zero.
- If enrichment is degraded or any targeted filed-OOS fetch failed, it prints the report and exits non-zero with degraded-evidence failure named in the verdict corpus block.
- If #5461 is still open, closed as `NOT_PLANNED`, or closed without non-empty `closedByPullRequestsReferences`, it prints the report and exits non-zero with `calibration_incentive_not_shipped`.
- If at least 150 qualifying post-`52.1.0` runs exist, enrichment is healthy, targeted fetches succeeded, and #5461 is demonstrably shipped, it exits 0 and the report can support the docs verdict after human review.
- Output must not include `## Executive Summary`, the diagnostic-only disclaimer, or unfiltered global corpus totals.

## Acceptance

Run focused tests first:

- `python3 -m pytest python/test_analyze_issues.py`

Then run required repo checks for Python changes:

- `make py-lint`
- `make py-test`
- `make lint`

Manual smoke command:

- `python3 python/cli.py analyze-issues run --ground-truth-verdict --since-date 2026-06-26 --min-larch-version 52.1.0 --min-runs 150`

Expected smoke behavior depends on the local corpus:

- If fewer than 150 qualifying unique `run_dir` values exist, it prints the filtered verdict report only (no legacy `Corpus:` subsection, with explicit gate FAIL) and exits non-zero.
- If enrichment is degraded or any targeted filed-OOS fetch failed, it prints the report and exits non-zero with degraded-evidence failure named in the verdict corpus block.
- If #5461 is still open, closed as `NOT_PLANNED`, or closed without non-empty `closedByPullRequestsReferences`, it prints the report and exits non-zero with `calibration_incentive_not_shipped`.
- If at least 150 qualifying post-`52.1.0` runs exist, enrichment is healthy, targeted fetches succeeded, and #5461 is demonstrably shipped, it exits 0 and the report can support the docs verdict after human review.
- Output must not include `## Executive Summary`, the diagnostic-only disclaimer, or unfiltered global corpus totals.

review_status: complete
rounds_completed: 5
diff_added: 640
diff_deleted: 52
mechanical_churn: false
diff_lines: 692
