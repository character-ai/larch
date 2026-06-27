# Review Round 1

- Mode: `diff`
- 2 accepted, 7 rejected (1 neutral)

## Accepted Findings

### FINDING_9: risk-integration: python/test_review_and_fix.py
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan acceptance requires a fix-applied round simulation to produce a claude-relevant-checks ledger row; new Step 5 tests only verify record_round_timing deferral. Acceptance criterion "timing ledger contains at least one claude-relevant-checks row after simulated fix-applied round" is unverified; regressions in end-to-end Gantt labeling would not be caught by current tests. Add integration test that exercises fix-applied path with checks producing a vendor row and asserts timing-ledger.tsv content, or revise acceptance if Step 5 no longer calls checks post-apply.
- **Suggested revision**: Address the concern above.


### FINDING_20: **architecture** `python/checks.py:2129-2141`, `python/agents.py:5754-5776`, `python/progress_report.py:1190-1236` — The outer `run_lint_fix` wrapper skips recording when `outcome.coder_tool == "claude"`, so the only Claude success bar comes from `launch-claude-lint-fix`, which records `task_kind=claude-lint-fix` with output basename `claude.log`. `_progress_core_from_output` strips only `.txt`, so that basename derives to `unknown/claude.log`, not `claude/lint-fix`. The new allow-list entry and `claude-lint-fix.txt` basename contract therefore do not produce the intended Gantt label on the primary Claude lint-fix path. **Suggested fix:** Either record the outer envelope for Claude with the canonical `.txt` basename (and dedupe ledger rows another way), or change the inner launcher output basename to `claude-lint-fix.txt` so `_progress_derived_label` maps both paths to `claude/lint-fix`.
- **Reviewer**: dyn-dyn-gantt-labels-output.txt
- **Concern**: - **architecture** `python/checks.py:2129-2141`, `python/agents.py:5754-5776`, `python/progress_report.py:1190-1236` — The outer `run_lint_fix` wrapper skips recording when `outcome.coder_tool == "claude"`, so the only Claude success bar comes from `launch-claude-lint-fix`, which records `task_kind=claude-lint-fix` with output basename `claude.log`. `_progress_core_from_output` strips only `.txt`, so that basename derives to `unknown/claude.log`, not `claude/lint-fix`. The new allow-list entry and `claude-lint-fix.txt` basename contract therefore do not produce the intended Gantt label on the primary Claude lint-fix path. **Suggested fix:** Either record the outer envelope for Claude with the canonical `.txt` basename (and dedupe ledger rows another way), or change the inner launcher output basename to `claude-lint-fix.txt` so `_progress_derived_label` maps both paths to `claude/lint-fix`.
- **Suggested revision**: Address the concern above.


