### [Bug] /design report fallback required

The /design failure reporter could not safely file an issue.

| Field | Value |
|---|---|
| Outcome | `failed-publish-tail` |
| Reason | `compose-status-missing` |

Use the local artifacts in `DESIGN_TMPDIR` to investigate. This fallback contains no log tail.
