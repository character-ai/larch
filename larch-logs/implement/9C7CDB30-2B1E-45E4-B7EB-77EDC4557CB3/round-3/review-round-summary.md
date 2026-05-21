# Review Round 3

- Mode: `diff`
- Accepted findings: 2
- Rejected findings: 0
- Exonerated findings: 9
- Neutral findings: 2

## Accepted Findings

### FINDING_2: `audit-scan-run.sh` can emit contradictory outputs on jq/JSONL corruption (OOS error vs `category-stats` “complete” zeros)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: `oos-category-mangle` can surface jq/parse failures as a structured scan error while the `category-stats` jq path may swallow failures into plausible zeros with `partial_data:false`, producing internally inconsistent NDJSON for the same input artifact.
- **Suggested revision**: Reuse one parse path or align contracts so jq failures set `partial_data` (or an explicit error/partial flag) on `category-stats` whenever the OOS scan is in an error state; avoid “error + plausible zeros” contradictions.


### FINDING_3: Duplicated `jq` programs / drift between OOS scan and `category-stats` mangled aggregation
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-jq-filter-asymmetry-output.txt
- **Concern**: The same (or closely related) `jq` filtering logic exists in multiple places, so fixes to error handling, narrowing, or normalization can diverge and reintroduce mismatches between `oos-category-mangle` and `category-stats.mangled`.
- **Suggested revision**: Factor a single shared `jq` program (literal or helper-sourced) used by both code paths, and update both together when semantics change.


