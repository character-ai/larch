# Review Round 1

- Mode: `diff`
- 1 accepted, 3 rejected (3 neutral)

## Accepted Findings

### FINDING_1: emit-rejected verbatim passthrough when ledger exists but no Plan Review blocks
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-code-quality-output.txt, dyn-risk-integration-output.txt
- **Severity**: important
- **Concern**: When `.step3-applied-finding-keys.tsv` is non-empty but `rejected-findings.md` lacks `^### [Plan Review] ` block markers, `emit_rejected_findings` takes the verbatim branch (exit 0) and skips applied-key filtering. Gate C can then show already-applied findings as unimplemented (#4849 failure mode) without triggering the shell `if !` fallback, if tally format drifts, the file is hand-edited, or headers are dropped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Warn and fail closed, or add a secondary FINDING_N block splitter, before verbatim fallback.
  - From cursor-specialist-edge-cases-output.txt: Log a warning and fail closed or use a secondary block splitter instead of verbatim passthrough
  - From cursor-specialist-testing-output.txt: consider a warning when ledger is non-empty but no markers match
  - From dyn-code-quality-output.txt: If `applied` is non-empty and `matches` is empty, either fail closed (non-zero exit so `design-step3b-tail.sh` falls back to raw `cat`, with a stderr diagnostic) or emit a `WARN` KV and filter with the same `^### FINDING_[0-9]+:` splitter continuation already uses; add a unit test for the mismatch case.
  - From dyn-risk-integration-output.txt: Treat “ledger present + zero recognizable blocks” as a reconciliation failure: log a warning to `execution-issues.md`, and either emit an empty body or fail closed (non-zero exit) so the shell does not silently pass through stale rejected content.


