### [BUG] /design report fallback required

The /design failure reporter could not safely file an issue.

| Field | Value |
|---|---|
| Outcome | `failed-plan-write` |
| Reason | `missing-terminal-state` |

Use the local artifacts in `DESIGN_TMPDIR` to investigate. This fallback contains no log tail.
