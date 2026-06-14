## Goal
Implement issue #4277: [IMPLEMENTING] [BUG] Another problem with /implement final report reviews section.

## Implementation Plan
## Plan

Approach

- Fix the final report renderer at the source: `scripts/render-review-phase-detail.sh`.
- Keep the generic `python/gantt.py` renderer unchanged.
- Keep the table Time and Cost windows unchanged.
- Change only the reviewer timing chart rows and chart window:
  - Exclude CI-fix, CI-test, CI-output, and launcher probe timing rows from reviewer timing charts.
  - Compute the chart window from the remaining displayed chart rows, not the full round window.
  - Keep the existing best-effort behavior when extraction or rendering fails.
- Preserve existing reviewer, vote, aggregator, scout, and autofix rows unless they are clearly CI or launcher probe rows.
- Do not filter by `skill`, because existing Gantt preservation depends on rows that overlap the wider unfiltered round window.

Files to modify/create

### UPDATED: `scripts/render-review-phase-detail.sh`

- Add small AWK predicates near the Gantt extraction code.
- Filter chart candidates before sorting and before `head -n 25`.
- Exclude rows when task kind is CI-like:
  - Exact known kinds: `codex-ci`, `cursor-ci`, `claude-ci`, `codex-ci-fix`, `cursor-ci-fix`, `claude-ci-fix`.
  - Suffix forms: `*-ci`, `*-ci-fix`, `*-ci-test`.
- Exclude rows when output basename is CI-like:
  - `ci.out`
  - `codex-ci.out`
  - `cursor-ci.out`
  - `claude-ci.out`
  - `ci-fix-*.out`
- Exclude launcher probe rows when the basename is:
  - `claude.out`
  - `codex.out`
  - `cursor.out`
- Avoid broad basename filtering for ordinary reviewer outputs.
- Keep slot-map matches as reviewer rows unless the row is CI-like or launcher-probe-like.
- After writing `tasks_file`, derive `chart_start` and `chart_end` from that filtered file:
  - min column 2
  - max column 3
- Pass `chart_start` and `chart_end` to `python3 python/cli.py gantt render`.
- Use `chart_end - chart_start` for the title span.
- If no rows remain after filtering, keep the existing no-task message.
- If extraction or render fails, keep the existing unavailable message.

### UPDATED: `scripts/test-render-review-phase-detail.sh`

- Update the main Gantt fixture:
  - Add CI-like timing rows near the end of a round.
  - Add `ci-fix-codex.out` or another `ci-fix-*.out` row with a non-CI-looking task kind.
  - Add `unknown/claude.out` near the end of the round.
  - Add symmetric launcher probe coverage for `codex.out` or `cursor.out` when practical.
  - Keep existing reviewer, aggregator, scout, vote, and autofix rows.
- Assert CI and launcher probe rows do not appear:
  - no `ci.out`
  - no `cursor/ci.out`
  - no `claude/ci.out`
  - no `ci-fix-codex.out`
  - no `unknown/claude.out`
- Update the expected chart title span from the full round duration to the filtered task span.
- Ensure the span ends at the last displayed reviewer-related row, not at the tail CI or probe row.
- Keep existing chart invariant checks.
- Keep the Gantt preservation test for unfiltered round overlap.
- Add a focused regression case where a round contains only CI and launcher probe rows after filtering.
  - Expect the round table to render.
  - Expect `No reviewer timing tasks overlapped this round.` under that round timing heading.

### UPDATED: `scripts/render-review-phase-detail.md`

- Document that reviewer timing charts are filtered views.
- State that CI-fix, CI-test, CI-output, and launcher probe timing rows are excluded.
- State that excluded basenames include `ci.out`, `*-ci.out`, `ci-fix-*.out`, `claude.out`, `codex.out`, and `cursor.out`.
- State that chart axes use the span of displayed rows, while table Time still uses the round timing row.
- Keep the best-effort and `--no-gantt` behavior documented.

Edge cases

- If every candidate row is filtered out, show the no-task note.
- If one row remains, `python/gantt.py` already handles a positive span.
- If malformed timing rows exist, keep the current extraction failure behavior.
- If a real reviewer output is named `ci.out`, `ci-fix-*.out`, `claude.out`, `codex.out`, or `cursor.out`, it will be hidden. Those basenames are reserved by observed CI and launcher probe output.
- Do not filter by `skill`, because existing Gantt preservation depends on rows that overlap the wider unfiltered round window.

Failure modes

- A too-broad filter could hide real reviewer rows.
  - Limit filters to CI task kinds, CI-like basenames, and launcher probe basenames.
- A too-narrow filter could leave a 1s tail row and preserve the large empty chart gap.
  - Cover `ci-fix-*.out`, suffix task kinds, and `claude.out` with tests.
- A tight chart window can make the chart title differ from the table Time.
  - Document this clearly.
- Sorting or rendering failures should not break final report generation.
  - Preserve current neutral fallback messages.

Testing strategy

- Run `bash scripts/test-render-review-phase-detail.sh`.
- Run `bash scripts/relevant-checks.sh`.

## Acceptance

- `scripts/test-render-review-phase-detail.sh` passes with new assertions that CI and launcher probe rows are absent from chart output.
- The chart title span reflects the filtered reviewer rows only (not the full round window).
- A round with only CI rows renders the table but shows `No reviewer timing tasks overlapped this round.` for the chart.
- `bash scripts/relevant-checks.sh` passes.

diff_lines: 96

## Test plan
(no test plan section in plan-file)
