## Decision 1: Scope — all 5 items including the exec-main refactor
- **Question**: Should the plan cover all 5 combined items, including the lower-priority `launch_codex_exec_main --workdir` omitted-argument refactor in Item 5?
- **Resolution**: Yes. Fix Items 1-5 in one plan/PR, including `launch_codex_exec_main`, `launch_codex_ci_main`, and `launch_cursor_ci_main`.
- **Source**: user

## Decision 2: pr_body.py — align all counting paths
- **Question**: Item 2 targets only the structured-NDJSON-rows path (717-723). Should the fix also align the sibling paths (the `execution-issues.md` path at 694-708 and the body_text NDJSON fallback at 734-747), which use a bold-only bullet regex and would not count plain `- a` bullets?
- **Resolution**: Align all three counting paths to count top-level `^- ` bullets so plain and bold-label bullets count consistently across every path. The structured-rows path keeps `max(1, count)` per row.
- **Source**: user

## Decision 3: bootstrap.py provenance strip — terminal-region only
- **Question**: Should the materialization strip remove every line starting with `review_status:` / `rounds_completed:` globally, or only in the terminal metadata region near `diff_lines:`?
- **Resolution**: Strip only contiguous recognized provenance lines in the terminal trailer region near the final `diff_lines:` trailer. Preserve matching lines elsewhere in plan prose, examples, and code fences. (The issue's own Failure Modes flag global stripping as data loss.)
- **Source**: codebase / issue

## Decision 4: Hard constraints to preserve
- **Question**: What existing behavior must not break?
- **Resolution**:
  - Do NOT modify `preflight/plan-from-issue.txt` during materialization (preflight reads provenance from it).
  - Do NOT remove `diff_lines:` or other size trailers from the materialized `plan.txt`.
  - Cursor CI fix-role MUST keep `stall_channel="stdout"`; non-fix role uses `tree:{resolved_workdir}`.
  - Explicit `--workdir` passed to `launch_codex_exec_main` MUST be validated and honored unchanged, even when equal to `str(Path.cwd())`.
  - `step_7a.py`: when `LARCH_RUN_ID` is set in `session-env.sh`, resolve it regardless of whether the `session-id` file exists.
- **Source**: codebase / issue

## Decision 5: Same-PR test coverage required
- **Question**: Are regression tests required in the same PR?
- **Resolution**: Yes. Add/extend regression tests for all five fixes in their sibling test modules (`test_step_7a.py`, `test_pr_body.py`, `test_execution_issues.py`, `test_bootstrap.py`, `test_agents.py`). Launcher argv changes require same-PR coverage per `.claude/rules/launcher-argv-test-coverage.md`, and honor Codex/Cursor parity per `.claude/rules/external-tool-launcher-parity.md`. Also update `skills/implement/references/preflight-plan-audit.md` and `scripts/test-plan-adequacy-audit.sh`.
- **Source**: codebase / issue
