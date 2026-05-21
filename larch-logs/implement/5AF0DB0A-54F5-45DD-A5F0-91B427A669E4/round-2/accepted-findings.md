### FINDING_1: Audit reasons collapse to {} while ns-retry-sidecars count is positive
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: When building the `reasons` histogram, `jq` can fail or emit empty output and the pipeline falls back to `{}` while NDJSON still reports a positive `ns-retry-sidecars` count. Per-cause bins then disagree with the count and hide the breakdown exactly when operators need cause attribution.
- **Suggested revision**: Detect `count>0` with empty reasons and emit a non-empty fallback (for example `UNKNOWN` carrying count `N`), add an explicit warning/detail field, preflight `jq`, or add a `jq`-free histogram path on failure.


