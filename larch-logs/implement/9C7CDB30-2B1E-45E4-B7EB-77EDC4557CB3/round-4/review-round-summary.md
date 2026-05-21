# Review Round 4

- Mode: `diff`
- Accepted findings: 5
- Rejected findings: 0
- Exonerated findings: 7
- Neutral findings: 1

## Accepted Findings

### FINDING_1: partial_data skips all category-stats counter deltas
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Concern**: When `category-stats` sets `partial_data` (e.g. after jq/mangled-path failures), `audit-compute-counters.sh` skips every category-stats clean/blank delta even if canonical or OOS blank lines were still emitted, so a PR can silently lose OOS clean/blank counter movement while the scan NDJSON still looks partially healthy; related: error-path lines may lack counts while the same skip policy applies, risking a “zero delta” cumulative read on failure.
- **Suggested revision**: Narrow what `partial_data` means (or split flags) and change `audit-compute-counters` to skip only fields that are provably invalid; align counter policy with partial/error semantics or document intentional zero-deltas on error.


### FINDING_19: PR disambiguation tie-break lacks explicit fallback when no merge is after issue creation
- **Reviewer(s)**: dyn-skill-orchestration-spec-output.txt
- **Concern**: “Prefer mergedAt closest after issue createdAt” has no stated rule when no candidate merges strictly after `createdAt`, inviting arbitrary LLM choices and weakening “no silent suppression” for `version_window_checks`.
- **Suggested revision**: Add an explicit empty-set fallback aligned with ambiguity handling (e.g. latest mergedAt among `closes #N` candidates, or mark `in_scope: true` with both PRs and rationale if still indeterminate).
```

### FINDING_2: SKILL.md mis-documents CATEGORY_STATS_PARTIAL
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: `CATEGORY_STATS_PARTIAL` / `partial_data` documentation in `SKILL.md` still implies “missing JSONL only,” which will mislead operators once `partial_data` is also set for jq/mangled-category failures.
- **Suggested revision**: Update `SKILL.md` so partial triggers match the implemented scan and counter behavior after counter/partial semantics are finalized.


### FINDING_3: Duplicate jq passes over the same JSONL
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Concern**: `audit-scan-run.sh` runs the same `jq -f audit-scan-run-mangled-rows.jq` work twice per JSONL, doubling CPU/temp churn and duplicating failure handling.
- **Suggested revision**: Run the mangled-row jq once per JSONL and reuse its output for both emission sites (or cache to a single temp artifact per run).


### FINDING_7: Missing harness for category-stats NDJSON on jq/mangle errors
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: No test asserts category-stats NDJSON when `oos-category-mangle` jq errors, so regressions in `partial_data` / `detail` / mangled semantics could ship without `test-audit-runs.sh` failing.
- **Suggested revision**: Add a hermetic fixture test: invalid JSONL → expect OOS result error plus category-stats `partial_data` with expected `detail` and mangled placeholder behavior.


