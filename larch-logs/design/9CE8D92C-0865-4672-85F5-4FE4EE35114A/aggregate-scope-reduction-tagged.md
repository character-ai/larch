### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-cache-key-discipline.sh
- **Concern**: [SCOPE-REDUCTION] `round_runner.py` listed without prompt construction. Scenario: `python/larch/review/round_runner.py` orchestrates review rounds and delegates prompt work to `review_pipeline` / `coder_runner`; it contains no prompt assembly. Adding it to the cache-key guard expands harness scope without protecting a Step 3/5 `claude_sub` surface and adds maintenance noise.
- **Proposed resolution**: Drop `python/larch/review/round_runner.py` from the explicit prompt-surface file list; keep the three files that actually assemble or dispatch prompts (`checks_lint_fix.py`, `coder_runner.py`, `review_dispatch_panel.py`).
