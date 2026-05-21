# Review Round 3

- Mode: `diff`
- Accepted findings: 2
- Rejected findings: 0
- Exonerated findings: 7
- Neutral findings: 2

## Accepted Findings

### FINDING_10: v2 manifest omit-key semantics vs cross-cutting docs and consumer tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-schema-v2-consumer-coverage-output.txt
- **Concern**: For `schema_version >= 2`, `ended_at_null` / `pr_number_null` no longer mean “field absent” the same way as v1; typical flushed v2 manifests omit keys and report false for those flags, inverting prior NDJSON meaning. Shipped `audit-scan-run.md` (and examples) still describe the older “empty field” mental model, misleading dashboards/aggregators.
- **Suggested revision**: Add regression tests pinning v1 vs v2 cross-cutting lines; rewrite `audit-scan-run.md` (and examples) to spell out v1 vs v2 `has(...)` / null / omit semantics and how `manifest_pr_number_mismatch_with_audited_pr` behaves with present non-null `pr_number`.


### FINDING_3: Ambiguous PR-body closing-keyword → wrong issue mapping
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Concern**: First `Closes`/`Fixes`/`Resolves` match (e.g. `grep | head -1` / file order) can map a run to the wrong parent issue when multiple lines exist; order is not GitHub’s semantic priority.
- **Suggested revision**: Use a canonical rule (e.g. prefer `Closes` pass, or disambiguate using manifest `closes_issue` / parent-issue `ISSUE_NUMBER`), or detect ambiguity and refuse mapping like other ambiguous branches.


