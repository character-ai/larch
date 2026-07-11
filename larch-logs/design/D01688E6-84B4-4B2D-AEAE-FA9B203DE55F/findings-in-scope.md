### FINDING_1: Land #6825 before implementation and rebase
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: major
- **Concern**: The plan omits the required #6825 land-first prerequisite. Both changes edit overlapping regions of `python/larch/core/config.py` and `python/larch/report/report_tokens_cost.py`. Implementing before #6825 is merged risks merge conflicts, incorrect merge resolution, Grok 4.5 regressions, or rate-row drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit Approach or Failure modes step: land #6825 first, rebase this branch, then implement. Re-run the plan’s Grok preservation checks and focused pricing tests on the rebased tree before merge.
  - From Cursor-Innovation: Add an Approach or Failure modes step: do not start until #6825 is merged to main; rebase this branch on updated main; run the listed Grok preservation assertions on the rebased tree before other edits.

### FINDING_2: Explicitly scope both plan-review panel doc_fallback strings
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: The plan does not explicitly scope the `design.plan_review_panel` `doc_fallback` string. An implementer could update the reviewer and fixer fallbacks while leaving the per-slot auto wording at line 442, violating the requirement to remove Cursor auto prose. The final acceptance grep also may miss isolated per-slot auto wording without an adjacent cursor token.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Name both panel `doc_fallback` strings explicitly in the `config.py` section (include `design.plan_review_panel` at line 442). Replace per-slot auto with Composer 2.5 default-resolution wording. Add `python/larch/core/config.py` to the manual inspection list in the testing strategy.
