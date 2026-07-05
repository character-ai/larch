## Decision 1: Fix approach for miscategorization
- **Question**: Should we tighten the prompt-side contract (require `--category Warnings` explicitly) or add a dedicated helper that pins the category?
- **Resolution**: Add a dedicated CLI helper `architectural-guidelines append-deviation-note` that always uses `category="Warnings"`. Update `architectural-guidelines-present.md` to call it explicitly. This is safer than relying on prompt-side argument selection.
- **Source**: codebase (`execution_issues.append_execution_issue_main` defaults `--category` to `"Tool Failures"`; that default is the likely root cause of miscategorization)

## Decision 2: Scope of duplicate-write fix
- **Question**: Should dedup happen on the append path (execution-issues.md), the flush path (ndjson), or both?
- **Resolution**: Dedup on the append path only. The new helper checks whether an identical entry already exists in execution-issues.md before writing (same pattern as `execution_issues.append_execution_issue`). The ndjson-level dedup in `_render_execution_issues_batch` already exists; the append-path dedup prevents the root cause (same text appearing twice in the md file).
- **Source**: codebase (`execution_issues.append_execution_issue` at line 245 already does `if entry in text: return`; the `run_log_batch._append_execution_issue` used elsewhere does not)

## Decision 3: Where to put the new helper
- **Question**: Should the new function live in `architectural_guidelines.py` or `execution_issues.py`?
- **Resolution**: Put it in `architectural_guidelines.py` as `append_deviation_note` and expose via CLI as `architectural-guidelines append-deviation-note`. It belongs with the guideline helpers, not the generic execution-issues helpers.
- **Source**: codebase convention; `architectural_guidelines.py` already owns `write_compose_assessment_main` etc.
