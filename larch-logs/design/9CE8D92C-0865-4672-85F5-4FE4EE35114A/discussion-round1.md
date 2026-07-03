## Decision 1: Include Step 3 submodule-path ordering fix
- **Question**: Besides the main Step 5 `_render_specialist_text` reordering fix, should this plan also fix `submodule_paths()` in `checks_lint_fix.py` (non-deterministic order from `git config --get-regexp`) to match the deterministic `sorted(...)` pattern already used in `coder_runner.py`?
- **Resolution**: Yes — include it. Same root-cause category (Step 3 prefix instability) named in the issue; low-risk deterministic-ordering change.
- **Source**: user

## Decision 2: Extend cache-key-discipline guard coverage
- **Question**: Should `scripts/test-cache-key-discipline.sh` be extended to scan `checks_lint_fix.py`, `coder_runner.py`, `review_dispatch_panel.py`, and `round_runner.py` (the files central to this bug, currently outside its enforced coverage despite the companion doc's broader claim), or should that be left as separate follow-up work?
- **Resolution**: Extend guard coverage now, as part of this fix.
- **Source**: user

## Decision 3: No deduplication of double-included diff/plan/feature content
- **Question**: `_render_specialist_text`'s "read that file" pointer sentence and `_claude_runner.py`'s separate `--context-files` inlining both include the same diff/plan/feature content for Claude reviewer dispatch — should this fix also deduplicate that redundancy?
- **Resolution**: No — out of scope. The issue's acceptance criterion requires "checks and review outcomes unchanged"; removing content (even if duplicated) risks changing what the reviewer model sees and could alter review outcomes. This fix is reordering-only, not content removal. Deduplication is a separate, riskier optimization better tracked independently.
- **Source**: codebase (issue acceptance criteria)

## Decision 4: No session/resume infrastructure changes
- **Question**: The issue names "session reuse" as a candidate root cause to investigate — should this fix add `--resume`/`--continue` session continuity to the claude_sub lane?
- **Resolution**: No — out of scope. No `claude` invocation anywhere in the codebase currently uses session/resume flags; every `claude_sub` call is an independent `claude --print` process. Adding session continuity would be a materially larger, separate infrastructure change disproportionate to "fix assembly to keep a stable cacheable prefix," which the issue explicitly scopes as an assembly-ordering fix.
- **Source**: codebase
