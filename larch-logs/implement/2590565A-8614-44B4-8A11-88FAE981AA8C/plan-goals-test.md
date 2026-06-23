## Goal
Implement issue #5125: [IMPLEMENTING] review-points-overhaul-II Measure voter severity calibration (per-voter severity distribution).

## Implementation Plan
## Plan

Drafted from direct repo inspection because `approach-synthesis.txt` is `NO_SKETCHES`.

## Approach

Add a shared **YES-vote severity distribution** path next to the existing voter agreement path.

- Reuse `HIGH_SEVERITIES = frozenset({JudgeSeverity.blocker.value, JudgeSeverity.major.value})`.
- Carry optional severity data in voter rows with a **fixed positional contract** (see below).
- Count only `YES` votes for severity distribution.
- Count valid severities by enum value: `blocker`, `major`, `minor`, `nit`, `uncertain`.
- Treat `uncertain` as a **valid non-high** bucket included in `valid_yes_severity_count` (same spirit as points logic: it is a real judge signal, not absence of severity).
- Map empty strings, invalid tokens, and absent severity on YES votes to **Missing Severity**, excluded from `valid_yes_severity_count`.
- Compute `high_rate = (blocker + major) / valid_yes_severity_count`.
- Set `uncalibrated = true` only when `high_rate > high_severity_threshold` (strict `>`).
- Return `high_rate = None` and `uncalibrated = false` when no valid YES severity exists.
- Append severity scoreboards immediately after **every** agreement scoreboard render site (main tally loops and degraded/zero early-return paths).
- Mirror agreement global rollup: panel table from raw rows; global table from `_global_rows(rows)`.
- Do not change voting decisions, quorum, point awards, TSV schemas, or existing agreement table columns.

### Positional severity contract

`voter_severities[i]` must align with `voter_votes[i]` **before** label filtering:

- Live tallies and TSV ingestion both pass a **three-element** severity list for slots 1..3.
- Use `""` for absent/dead slots; never pass variable-length lists from `_votes_and_severities_for_item`.
- In `voter_agreement_row_from_panel`, when building each voter dict from `(label, vote)` at index `i`, attach `"severity": voter_severities[i]` when `voter_severities` is provided.
- `voter_agreement_rows_from_tsv` always supplies `voter_severities=[row.get(f"v{pos}_severity") or "" for pos in (1,2,3)]` alongside the existing three-slot `voter_votes` list.
- When `voter_votes` is empty (MainAgent adjudication with `tally_voter_file` set), omit `voter_severities` or pass `None`; never pass a three-element list against an empty `voter_votes` list.

### MainAgent sole-voter path

When sole `--voter MainAgent:<vote-file>` is used, `plan_review_tally.py` sets `tally_voter_file` and `eligible=1`, but agreement rows stay empty (`voter_votes=[]`). Severity collection and the `voter_severities` kwarg must remain gated on `eligible > 0 and not self.tally_voter_file` so the length guard never fires on this path. Harness coverage must name this contract explicitly (see `test_tally_plan_review_main_agent_sole_voter_severity_scoreboard` below); vague "extend MainAgent coverage" is insufficient.

## Files to modify/create

### UPDATED: `python/voting.py`

Add shared severity helpers.

- Extend `voter_agreement_row_from_panel` with additive severity support:
  - Keep existing `voter_votes` behavior intact.
  - Add optional keyword-only `voter_severities: list[str] | None = None`.
  - Require `len(voter_severities) == len(voter_votes)` when provided; raise `ValueError` on mismatch.
  - Store `"severity"` on each voter dict at the same index as its vote tuple (including empty-label slots skipped later for agreement math).
- Extend `voter_agreement_rows_from_tsv` to read `v{pos}_severity` when present:
  - Always pass a three-element `voter_severities` list aligned to slots 1..3.
  - Preserve existing malformed and ineligible row handling.
  - Preserve existing agreement row eligibility.
- Add `compute_voter_severity_distribution(rows, *, high_severity_threshold: float = 0.90)`.
  - Aggregate by `(panel, voter)`.
  - Count YES votes and severity buckets: `blocker`, `major`, `minor`, `nit`, `uncertain`.
  - Count `high = blocker + major`.
  - Count `missing_severity` for YES votes whose token is empty or fails `valid_panel_severity`.
  - Compute `high_rate` from valid buckets only (`blocker+major+minor+nit+uncertain`).
  - Flag `uncalibrated` with strict `>` threshold.
  - Sort records by `(panel, voter)`, like agreement.
- Add `render_voter_severity_scoreboard(records)`.
  - Heading: `## Voter Severity Scoreboard`.
  - Columns: `Panel`, `Voter`, `YES Votes`, `Blocker`, `Major`, `Minor`, `Nit`, `Uncertain`, `Missing Severity`, `High Rate`, `Uncalibrated`.
  - Use existing `_format_rate` helper.
  - Render explanatory empty-table note when no records exist.
- Add `render_voter_agreement_and_severity_scoreboards(agreement_rows, *, high_severity_threshold: float = 0.90) -> str` helper that returns agreement plus blank line plus severity for a given row list (used by live tallies and zero/degraded paths with `[]` when needed).
- Add `## Voter Severity Scoreboard` to `_ALLOWED_CODE_REVIEW_HEADERS`.

### UPDATED: `skills/voter-calibration/scripts/voter-calibration.py`

Add severity distribution to the analyzer.

- Import `compute_voter_severity_distribution` and `render_voter_severity_scoreboard` from `python/voting.py` (no local table helper; use shared renderer only).
- Add `--high-severity-threshold` to `_parse_args`, `type=float`, default `0.90`.
- Pass `high_severity_threshold=args.high_severity_threshold` into both severity aggregations.
- Render severity sections next to matching agreement sections:
  - after `## Agreement Table`, add panel-level severity via `compute_voter_severity_distribution(rows, ...)`.
  - after `## Global Voter Agreement`, add global severity via `compute_voter_severity_distribution(_global_rows(rows), ...)` (mirror agreement rollup).
- Add a short note that severity calibration is diagnostic-only and does not affect live decisions.
- Keep `--outlier-threshold`, existing agreement output, and file discovery unchanged.

### UPDATED: `skills/voter-calibration/scripts/test-voter-calibration.sh`

Extend offline harness so severity output cannot regress silently.

- Seed fixture TSV rows with varied `vN_severity` values (include at least one all-high YES voter and one mixed voter under default threshold).
- After primary analyzer run, assert **both** panel and global severity sections exist using **fail-closed** checks:
  - `severity_count=$(grep -c '## Voter Severity Scoreboard' "$run_out" || true); [[ "$severity_count" -ge 2 ]]`
  - Bounded awk band for panel: `awk '/^## Agreement Table$/,/^## Global Voter Agreement$/ {print}' "$run_out" | grep -Fq '## Voter Severity Scoreboard'`
  - Bounded awk band for global: `awk '/^## Global Voter Agreement$/,/^## [^#]/ {if (/^## Voter Severity Scoreboard$/) found=1} END {exit !found}' "$run_out"`
- Assert at least one `uncalibrated` `true` row under default `--high-severity-threshold 0.90`.
- Assert severity table includes `Uncertain` column header.
- Add a secondary run with `--high-severity-threshold 0.50` proving threshold forwarding changes flagging.
- Keep existing agreement greps unchanged.

### UPDATED: `python/review_tally.py`

Append live code-review severity scoreboards at every agreement render site.

- In the main tally loop, build `voter_severities` with the **same branch-specific three-slot padding** as `voter_votes`:
  - **`three_slot` path:** `voter_severities = [cells[idx][2] if idx < len(cells) else "" for idx in range(3)]`
  - **Legacy path:** `voter_severities = [cells[pos - 1][2] if pos - 1 < len(cells) else "" for pos in range(1, 4)]`
- Pass `voter_severities=voter_severities` into `voter_agreement_row_from_panel`.
- Replace bare `render_voter_scoreboard(...)` calls with `render_voter_agreement_and_severity_scoreboards(agreement_rows)` on the main path.
- On the zero-judge early-return path (`eligible == 0`), use `render_voter_agreement_and_severity_scoreboards([])`.
- Preserve existing `voting-tally.md` sections and table columns.
- Preserve classification TSV writes.

### UPDATED: `python/plan_review_tally.py`

Append live plan-review severity scoreboards with slot-aligned severity collection.

- In `_Tally._render`, build `voter_votes` and `voter_severities` only under the same guard: `self.eligible > 0 and not self.tally_voter_file`.
  - Inside that guard, build `voter_severities: list[str]` in the same `for pos in (1, 2, 3)` loop; use `""` on absent slot or parse failure.
  - When the guard is false, omit `voter_severities` kwarg (or pass `None`) so the length guard never fires.
  - Do not pass `_votes_and_severities_for_item` output into `voter_agreement_row_from_panel`.
- Replace bare `render_voter_scoreboard(...)` with `render_voter_agreement_and_severity_scoreboards(agreement_rows)` in `_render`.
- On `eligible == 0` early return, use `render_voter_agreement_and_severity_scoreboards([])`.
- Preserve existing tally artifacts and classification TSV layout.

### UPDATED: `python/plan_review_round.py`

Cover zero-findings tally cleanup.

- In `_reset_zero_findings_tally_artifacts`, replace `voting.render_voter_scoreboard([])` with `voting.render_voter_agreement_and_severity_scoreboards([])`.

### UPDATED: `python/test_voting.py`

Add unit coverage for the shared severity math.

- Cover `voter_agreement_row_from_panel` with three-element `voter_severities` and index-aligned `"severity"` on voter dicts.
- Cover length-mismatch guard (`ValueError` on mismatch).
- Cover empty `voter_votes` with omitted/`None` `voter_severities` (MainAgent path).
- Cover `voter_agreement_rows_from_tsv` reading `vN_severity` for design and code-review TSVs with three-slot alignment.
- Cover `compute_voter_severity_distribution`:
  - counts only YES votes; buckets `blocker` and `major` as high; counts `uncertain` as valid non-high; leaves NO severities out; maps invalid/empty to missing; flags only when `high_rate > threshold` (not at equality); respects custom threshold; 9 blocker + 1 uncertain → `high_rate = 0.900`, `uncalibrated = false`.
- Cover empty renderer output.

### UPDATED: `python/test_review_tally.py`

Add or extend code-review tally assertions.

- Extend `test_tally_zero_voters_main_agent_vote_required`: assert `## Voter Severity Scoreboard` immediately after `## Voter Agreement Scoreboard`.
- Extend `test_tally_code_review_voter_agreement_scoreboard_three_slot`: assert severity scoreboard present; at least one `uncalibrated` true with all-high voter.
- Extend `test_tally_excludes_narrative_only_voter_parse_rate_check` (legacy path, `cells` length 2): assert severity scoreboard; assert no `ValueError`; assert padded `v3=""` severity is not zip-shifted.
- Update write-tally header allowlist test to include `## Voter Severity Scoreboard`.

### UPDATED: `python/test_plan_review.py`

Add or extend plan-review tally assertions.

- In existing voter agreement scoreboard tests: assert severity scoreboard rows match `compute_voter_severity_distribution(voter_agreement_rows_from_tsv(...).rows)`.
- Add missing-middle-slot case proving severity stays positionally aligned.
- Add zero-findings path assertion: severity heading appears after agreement heading.
- Add `test_tally_plan_review_main_agent_sole_voter_severity_scoreboard`:
  - sole `--voter MainAgent:<file>` run completes with `TALLY_PLAN_REVIEW_STATUS=ok` and no `ValueError`;
  - `voting-tally.md` contains `## Voter Severity Scoreboard` after `## Voter Agreement Scoreboard` (empty table acceptable).

## Edge cases

- **Neutral panels:** excluded by existing agreement row eligibility.
- **Single parseable voter:** excluded from rows (agreement undefined).
- **YES without severity:** missing severity; excluded from `valid_yes_severity_count`.
- **YES with `uncertain`:** valid non-high bucket; included in denominator.
- **NO with severity:** ignored entirely.
- **Invalid severity token:** missing severity on YES votes.
- **No valid YES severities:** `n/a` high rate; `uncalibrated = false`.
- **Threshold equality:** not flagged at exactly `0.90`; only strictly above (9 blocker + 1 uncertain → 90.0% → not flagged).
- **Degraded slot alignment:** empty middle slots keep `""` severity at index 2; never compress lists.
- **Legacy code-review path:** pad `voter_severities` to three slots matching `voter_votes` padding.
- **MainAgent plan-review path:** `voter_votes=[]`; omit `voter_severities`; severity scoreboard still renders (empty table).
- **Zero/degraded paths:** paired severity scoreboards; empty tables acceptable.

## Failure modes

- Live tally divergence from committed TSV if severity collected with variable-length lists or wrong index alignment. Mitigate via three-slot positional contract and explicit `three_slot` vs legacy padding branches.
- Legacy `review_tally.py` zip-shifting severities when `cells` shorter than three entries. Mitigate by mirroring `voter_votes` padding branch for `voter_severities`.
- `plan_review_tally.py` passing three-element `voter_severities` when `voter_votes=[]` on MainAgent path. Mitigate via guard; named harness.
- `write-tally` rejecting new heading unless `_ALLOWED_CODE_REVIEW_HEADERS` updated.
- Forgetting `plan_review_round.py` leaves zero-findings paths without severity scoreboard.
- Global severity misleading if aggregating per-panel rows instead of `_global_rows` rollup.
- Offline harness with unbounded slice passing when only one section visible. Mitigate with `[[ "$severity_count" -ge 2 ]]` and bounded awk bands.

## Testing strategy

Run:

- `make py-lint`
- `make py-test`
- `make test-voter-calibration`
- `make lint`

Targeted checks:

- `python3 -m pytest python/test_voting.py`
- `python3 -m pytest python/test_review_tally.py -k severity`
- `python3 -m pytest python/test_plan_review.py -k "severity or main_agent_sole_voter"`

## Acceptance

- `/voter-calibration` shows agreement and severity distribution (panel and global), global severity via `_global_rows`.
- Offline harness proves **both** panel and global `## Voter Severity Scoreboard` sections via `[[ "$severity_count" -ge 2 ]]` plus bounded awk bands.
- Code-review and plan-review `voting-tally.md` show severity scoreboards after agreement on **all** paths (main tally, zero judges, zero findings, eligible==0).
- Legacy code-review tally pads `voter_severities` to three slots; no `ValueError`.
- MainAgent sole-voter plan-review completes with `TALLY_PLAN_REVIEW_STATUS=ok`; no `ValueError`; `test_tally_plan_review_main_agent_sole_voter_severity_scoreboard` encodes contract.
- Voter with `>90%` high YES-vote severities (among valid severities) marked uncalibrated.
- `uncertain` YES severities handled as valid non-high calibration input.
- Degraded panels with empty middle slots keep severity positionally aligned.
- `test_tally_zero_voters_main_agent_vote_required` asserts severity scoreboard on zero-judge code-review path.
- Offline harness asserts uncalibrated rows and threshold forwarding.
- No live decision, quorum, point score, or TSV schema changes.

diff_lines: 400

## Test plan
(no test plan section in plan-file)
