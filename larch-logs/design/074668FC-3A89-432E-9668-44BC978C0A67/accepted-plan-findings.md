### FINDING_3: Shipped `/implement` SKILL.md Step 9a.1 completion semantics conflict with Python-path checkpoint behavior
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Generic
- **Severity**: important
- **Concern**: The plan changes Python Step 9a.1 completion semantics but omits updates to the shipped `/implement` prompt contract. Current SKILL.md text (NEVER #14–15 at `skills/implement/SKILL.md:58-60`, pre-ship `oos file` hook at `768-774`, bail-time invariant at `792`) still treats pre-gate `oos-issues.ndjson` as proof Step 9a.1 ran or as evidence that suppresses `steps_ran.step9a1=false`, and describes disposition-checkpoint primarily on the bash `OOS_PENDING` path. After a checkpoint-failed Python OOS filing leaves provisional `oos-issues.ndjson` without `run-statistics.md`, orchestrator and audit tooling can disagree on whether Step 9a.1 completed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add `skills/implement/SKILL.md` update: Step 9a.1 complete only with `run-statistics.md` or explicit `steps_ran.step9a1=true`; provisional ndjson alone is not completion
  - From Codex-Generic: Add `skills/implement/SKILL.md` to the plan and update the Python `oos file` and bail-time invariant text so only post-checkpoint `run-statistics.md` or explicit `steps_ran.step9a1=true` marks Step 9a.1 complete


### FINDING_4: OOS retry dedup keyed on title can miss after combine rewrites titles
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Retry matching in `python/oos_filer.py` (`_working_batch`, lines 104-124) keys dedup on normalized title. If checkpoint fails after partial issue creation and a combine step rewrites titles, a retry with the same accepted blocks and persisted ndjson may fail to match prior filings and re-file duplicate public issues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Match persisted sentinel and ndjson by Filed URL first; secondary-match titles via existing `_normalize_title`; reuse `_FILED_URL_LINE_RE` and `_working_batch` patterns


### FINDING_6: Plan omits `test_pr_body.py` coverage for bail-time `step9a1` stamping
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan names only `python/test_ship.py` or an unspecified final-report test for Step 9a.1 false stamping, but `_stamp_skipped_steps_for_terminal_report` lives in `python/pr_body.py:854-868` and neither `python/test_pr_body.py` nor `python/test_ship.py` covers `step9a1` stamping today. The ndjson-only fix in `pr_body.py` can ship without regression coverage because the plan does not pin `python/test_pr_body.py`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add `### UPDATED: python/test_pr_body.py` with an explicit test of `_stamp_skipped_steps_for_terminal_report` asserting ndjson without `run-statistics.md` still stamps `steps_ran.step9a1=false`


