## Goal
Implement issue #4517: [IMPLEMENTING] design: run-summary shows 'Plan review: N/A' despite completed plan review.

## Implementation Plan
## Summary

The `/design` run-summary renders `- **Plan review**: N/A` even when plan review completed (5 rounds in the observed run), because the plan-review line is hardcoded to `N/A` in `python/design_summary.py`. The review status and round count are available (the tracking-issue plan block carries `review_status: complete` and `rounds_completed: 5`) but are never read into the summary. The same summary also showed `Warnings: 0` despite a logged warning, suggesting the warnings count may under-report.

## Original report

Observed during `/design 4460`. The rendered `final-summary.md` contained `- **Plan review**: N/A` and `- **Warnings**: 0`, even though the run completed 5 plan-review rounds and recorded one `### Warnings` entry in `execution-issues.md`. The tracking issue's plan block correctly recorded `review_status: complete` / `rounds_completed: 5`, so the data exists; the summary renderer does not use it.

## Reproduction scenario

1. Run `/design <issue>` so plan review completes one or more rounds.
2. Render the run summary (`design render-final-summary --outcome approved --post-publish-only`).
3. Observe `- **Plan review**: N/A` regardless of the actual review status, and a `Warnings` count that may not match `execution-issues.md`.

## Expected behavior

`- **Plan review**:` reflects the actual review outcome, for example `complete (5 rounds)`, derived from `review_status` / `rounds_completed`. `- **Warnings**:` and `- **Exec issues**:` match the counts in `execution-issues.md`.

## Observed behavior

`- **Plan review**: N/A` (always), and `- **Warnings**: 0` despite a logged warning.

## Root cause analysis

The plan-review line is hardcoded. `python/design_summary.py` passes `--plan-review-line "N/A"` to the summary renderer rather than computing it from `review_status` / `rounds_completed`. The review provenance is available from `.step3-review-result.env` (and is written to the plan block by `design publish`), so the renderer has a source it is not consuming. The `Warnings`/`Exec issues` counts come from `_issue_counts(design_tmpdir)`; the observed `Warnings: 0` (with a real logged warning) suggests either a parsing gap in `_issue_counts` or a timing artifact of when the summary was rendered. The plan-review `N/A` is the high-confidence defect; the warnings under-count is lower-confidence and may be secondary.

This may interact with the missing success-path render (filed separately): if the normal success-path render were wired correctly, confirm whether it would populate these fields differently from a manual post-publish render.

## Evidence

- `python/design_summary.py:168-170` — `--pr-url "N/A"`, `--plan-review-line "N/A"`, `--code-review-line "N/A"` are passed as hardcoded literals.
- `python/design_summary.py:153,174` — the `warnings` value is wired from `_issue_counts`.
- Live run `C5C762F6-...`: `final-summary.md` showed `Plan review: N/A` and `Warnings: 0`; issue #4460 plan block has `review_status: complete` and `rounds_completed: 5`; `execution-issues.md` held one `### Warnings` entry.

## Affected files

- `python/design_summary.py` — populate the plan-review line from `review_status` / `rounds_completed`; verify `_issue_counts` warnings/exec-issues counting against `execution-issues.md`.

## Suggested fix(es)

- Read `review_status` / `rounds_completed` (from `.step3-review-result.env` or the plan block) and render, e.g., `Plan review: complete (5 rounds)` instead of the hardcoded `N/A`. Apply the same treatment to `--code-review-line` if a code-review provenance source exists for design runs.
- Verify `_issue_counts` counts `### Warnings` entries in `execution-issues.md`; add a unit test with a fixture `execution-issues.md` containing a warning and assert the rendered `Warnings` count.

## Open questions

- Is the hardcoded `N/A` intentional for a mode where review did not run, with a missing populate-on-completed-review branch?
- Is the `Warnings: 0` under-count a real `_issue_counts` bug, or an artifact of when the summary was rendered relative to warning logging?

## Test plan
(no test plan section in plan-file)
