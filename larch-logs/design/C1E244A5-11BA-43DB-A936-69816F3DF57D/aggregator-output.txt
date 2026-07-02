### FINDING_1: Reviewer slot failures omit fallback label remap
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic
- **Severity**: blocking
- **Concern**: The plan only threads the fallback remap into Top reviewers; Reviewer slot failures still format from the unreconciled label map (`_failed_reviewers` without the same remap). On vendor fallback, Top reviewers can show the correct `(via <ExecutingTool>)` label while Reviewer slot failures still credit the slot's configured vendor, so reviewer-status attribution stays wrong on one of the two visible report surfaces.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Apply the same remap when building the Reviewer slot failures section, and have the regression assert both Top reviewers and Reviewer slot failures show the `(via Codex)` label.
  - From Codex-Pragmatic: Apply the same remap to _failed_reviewers output, or have render_phase_detail remap both tables through one shared helper, and add a regression that asserts the failure list also shows “(via Codex)”.

### FINDING_2: Regression fixture does not match standalone `/review` artifact layout
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The plan tests a fabricated `/review` round directory shape instead of the actual standalone `/review` artifact shape. Standalone `/review --diff` runs `review core --output-dir "$REVIEW_TMPDIR"`, writes classification as `findings-classification-round-N.tsv` at the tmpdir root, and prints `review-round-summary.md`; `render_phase_detail` only accepts `design` or `implement` and returns no completed rounds without `round-N/round-meta.json`, so a proposed `root/round-1` fixture can pass while real `/review` attribution remains unreconciled.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Revise the plan to cover the actual `/review` root artifacts and final summary/log surface, or explicitly change `/review` to materialize/read the round layout before relying on `progress_report`; add the regression with root `panel-manifest.ndjson`, root `collector-results.env`, and `findings-classification-round-N.tsv` rather than only `round-1/` files.
