---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_4

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/report/progress_report.py:880-892
- **Concern**: [SCOPE-REDUCTION] Plan still migrates and keeps `_strip_md_for_terminal` after mid-run removal. Scenario: `_strip_md_for_terminal` is only called from `_call_render_phase_detail`, which is only reached by `_render_review_detail` and `_render_design_review_detail`; all three are mid-run-only and slated for deletion. Migrating the helper and `test_strip_md_for_terminal` preserves dead code against the retirement goal
- **Proposed resolution**: Drop `_strip_md_for_terminal` and `_call_render_phase_detail` from the pre-delete keep checklist and Step 3 keep list; delete `test_strip_md_for_terminal` with the mid-run tests instead of migrating it ## Findings ### 1. [risk-integration] `python/larch/report/progress_report.py:1108-1607` — Mid-run subtree can survive a passing audit The revised plan improves helper migration and test fixture ordering, but retirement verification still keys off import-block removal and four live-discovery tokens. A large block of mid-run-only functions remains defined directly in `progress_report.py` (for example `_render_review_detail`, `_render_design_review_detail`, `_call_render_phase_detail`, and the design freshness helpers). None appear in the named Step 2 delete list, and the proposed `rg` check would not fail if they are left behind. **Suggested revision:** Name those local mid-run symbols in Step 2 and add a second post-removal `rg` audit that asserts they are gone from `progress_report.py`. ### 2. [architecture] `python/larch/report/progress_report.py:880-892` — [SCOPE-REDUCTION] `_strip_md_for_terminal` becomes dead weight The plan still treats `_strip_md_for_terminal` as a retained helper and includes `test_strip_md_for_terminal` in the migration set. After mid-run renderers are removed, that helper has no production caller; only `_call_render_phase_detail` uses it, and that wrapper is itself mid-run-only. **Suggested revision:** Do not migrate `_strip_md_for_terminal` or its unit test. Delete it with `_call_render_phase_detail` and the mid-run wrapper renderers.


### [Plan Review] FINDING_5

### FINDING_5:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/report/progress_report.py:880-892
- **Concern**: [SCOPE-REDUCTION] `_strip_md_for_terminal` is listed as a retained migrate symbol but is mid-run-only. Scenario: The pre-delete checklist and Step 3 keep list require moving `_strip_md_for_terminal` for `_call_render_phase_detail`, yet `_call_render_phase_detail` is only called from `_render_review_detail` / `_render_design_review_detail`, which Step 2 deletes with other mid-run renderers. Final-report callers use `review_phase_detail._invoke_renderer` → `_render_phase_detail_best_effort` without this stripper. Migrating the helper and `test_strip_md_for_terminal` adds dead code against the retirement/minimum-change goal.
- **Proposed resolution**: Remove `_strip_md_for_terminal`, `_call_render_phase_detail`, `_render_review_detail`, and `_render_design_review_detail` from the migrate/keep lists; delete them with the mid-run block; drop `test_strip_md_for_terminal` from the migration list and delete `test_render_review_detail_*` with other live tests.


### [Plan Review] FINDING_6

### FINDING_6:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/write-final-report.md:115-129
- **Concern**: [SCOPE-REDUCTION] Plan misses shipped prompt prose that still describes retired terminal progress. Scenario: After the planned live-renderer deletion, this shipped contract still says `--no-gantt` is reserved for terminal progress and that terminal progress skips the shared renderer during live Step 5 or design review, contradicting the new supported surfaces.
- **Proposed resolution**: Add `skills/implement/scripts/write-final-report.md` to the plan and remove or reword the terminal-progress paragraphs to describe final-report and CLI behavior only.

---LARCH-REJECTED-END---
