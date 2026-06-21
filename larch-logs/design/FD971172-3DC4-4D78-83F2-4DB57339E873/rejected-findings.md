### [Plan Review] FINDING_2

### FINDING_2: oos-file-conflict pre-pass failure lacks operator-visible breadcrumb
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan requires an operator-visible `**⚠ /implement: oos-file-conflict pre-pass failed**` breadcrumb on non-zero CLI exit for the file-conflict pre-pass, but the `### UPDATED: python/oos_filer.py` branch only names `_append_tool_failure`. That helper writes to `execution-issues.md`; on the Python ship path `python/cli.py oos file` stdout is JSON-only, so a non-zero pre-pass exit can degrade silently with no terminal breadcrumb for the operator.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In ### UPDATED: python/oos_filer.py branch 3 specify stderr print (or a JSON payload field the ship driver surfaces) for the exact warning string in addition to _append_tool_failure


