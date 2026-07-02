### FINDING_1:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:39-45
- **Concern**: Plan only threads the fallback remap into Top reviewers; reviewer slot failures still format from the unreconciled label map.. Scenario: After this PR, `/review --diff` vendor fallback will still print the failure block as the slot's nominal vendor, so the issue's reviewer-status attribution stays wrong on one of its two visible surfaces.
- **Proposed resolution**: Apply the same remap when building the Reviewer slot failures section, and have the regression assert both Top reviewers and Reviewer slot failures show the `(via Codex)` label.



### FINDING_2:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/report/progress_report.py:493-685
- **Concern**: The plan only remaps Top reviewers. Reviewer slot failures still come from _failed_reviewers without the fallback label remap, so vendor-fallback code-review rows stay credited to the configured slot in that section.. Scenario: A fallback like cursor/arch executed by Codex would show the correct “(via Codex)” label in Top reviewers but still show cursor/arch in Reviewer slot failures, leaving the reported reviewer-status bug unresolved.
- **Proposed resolution**: Apply the same remap to _failed_reviewers output, or have render_phase_detail remap both tables through one shared helper, and add a regression that asserts the failure list also shows “(via Codex)”.



### FINDING_3:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/SKILL.md:58-73; python/larch/review/review_tally.py:629,1051-1059; python/larch/report/progress_report.py:587-594
- **Concern**: The plan tests a fabricated `/review` round directory shape instead of the actual standalone `/review` artifact shape. Scenario: Standalone `/review --diff` runs `review core --output-dir "$REVIEW_TMPDIR"`, writes classification as `findings-classification-round-N.tsv` at the tmpdir root, and prints `review-round-summary.md`; `render_phase_detail` only accepts `design` or `implement` and returns no completed rounds without `round-N/round-meta.json`, so the proposed `root/round-1` fixture can pass while real `/review` attribution remains unreconciled
- **Proposed resolution**: Revise the plan to cover the actual `/review` root artifacts and final summary/log surface, or explicitly change `/review` to materialize/read the round layout before relying on `progress_report`; add the regression with root `panel-manifest.ndjson`, root `collector-results.env`, and `findings-classification-round-N.tsv` rather than only `round-1/` files.



