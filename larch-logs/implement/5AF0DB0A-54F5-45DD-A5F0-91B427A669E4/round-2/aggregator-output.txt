Here is the normalized structured finding list (merged by behavioral risk; IDs in first-seen cluster order; `[OUT_OF_SCOPE]` retained where the merge rule or a standalone source requires it).

```text
### FINDING_1: Audit reasons collapse to {} while ns-retry-sidecars count is positive
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: When building the `reasons` histogram, `jq` can fail or emit empty output and the pipeline falls back to `{}` while NDJSON still reports a positive `ns-retry-sidecars` count. Per-cause bins then disagree with the count and hide the breakdown exactly when operators need cause attribution.
- **Suggested revision**: Detect `count>0` with empty reasons and emit a non-empty fallback (for example `UNKNOWN` carrying count `N`), add an explicit warning/detail field, preflight `jq`, or add a `jq`-free histogram path on failure.

### FINDING_2: Plan-text awk parsing vs grep/tail/jq implementation
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: The written plan calls for an `awk`-oriented approach to parse `NS_RETRY_REASON` from meta and build the histogram, but the implementation uses `grep`/`tail`/`jq`. No functional gap was asserted from the excerpt, but plan-to-code traceability is weaker for reviewers checking fidelity.
- **Suggested revision**: Align the plan text with the chosen tooling, or switch the implementation to `awk` if strict plan parity is required.

### FINDING_3: Duplicated NS retry reason token vocabulary between writer and audit normalizer
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: The authoritative token vocabulary is duplicated across `collect-agent-results.sh` and the audit-side normalizer. A token introduced only in the writer can appear as `UNKNOWN` in audits until the second copy is updated.
- **Suggested revision**: Add an explicit cross-reference comment or consolidate to a single shared token list source of truth.

### FINDING_4: [OUT_OF_SCOPE] Near-identical redact_gh_error implementations across scripts
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Multiple scripts carry nearly the same `redact_gh_error` logic (including truncation guards). Future security or redaction tweaks risk inconsistent application and divergent fail-closed behavior across tools.
- **Suggested revision**: Factor into one shared sourced helper or a single template-generated function used everywhere.

### FINDING_5: Append-only NS_RETRY_REASON can duplicate keys in meta JSON
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Append-only recording can grow meta with repeated `NS_RETRY_REASON` keys; semantics depend on last-line-wins conventions in downstream auditing rather than strict single-key hygiene.
- **Suggested revision**: If hygiene matters, replace the key or dedupe before appending.

### FINDING_6: [OUT_OF_SCOPE] Multi-issue diff shape increases review and bisect noise
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: A single change set spanning multiple concerns makes single-feature tracing, bisection, and review throughput worse.
- **Suggested revision**: Split pull requests or narrow diffs to one primary concern where practical.

### FINDING_7: Substantive exits 2 and 3 share NO_ISSUES_FOUND_TOO_THIN; label overfits word-count semantics
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Two distinct substantive validator failure modes (exit 2 thin body vs exit 3 provenance-related failure) collapse to the same `NS_RETRY_REASON` token, so audit histograms cannot separate them. The token name also reads like a pure word-count signal, which can mislead operators interpreting meta and reasons.
- **Suggested revision**: Introduce distinct tokens per exit mode, or explicitly document intentional coarse binning; rename the token or document prominently at the definition line if the name cannot cover both cases.

### FINDING_8: Tests do not exercise the broader NS retry reason token surface
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Coverage focuses on the too-thin path while other mapped tokens such as `OUTPUT_EMPTY`, `JSON_PARSE_FAIL`, and `UNKNOWN` paths for structured exits are not asserted, so mapping drift or breakage may pass CI.
- **Suggested revision**: Extend fixtures or harness assertions (for example `C_NSS`-style checks) to validate `.meta` tokens and audit-scan `reasons` keys for exits 4 and structured 5 paths.

### FINDING_9: [OUT_OF_SCOPE] Branch bundles unrelated security, redaction, plugin bump, and run logs
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: The branch mixes several independent themes, increasing partial-merge and rollback cost and review time scaling with diff size.
- **Suggested revision**: Split by concern or document an explicit merge rationale if atomic bundling is policy-approved.

### FINDING_10: NS_RETRY_REASON meta append path may hide I/O failures
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: If appending the reason to meta fails silently, no `NS_RETRY_REASON` is persisted while audits still bucket as `UNKNOWN`, indistinguishable from legacy runs and giving no signal that persistence failed.
- **Suggested revision**: Log loudly or fail closed when a reason token should be written but the append path errors.

### FINDING_11: [OUT_OF_SCOPE] C_NSR_REASON coverage only asserts the too-thin substantive token
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Optional gap: structured paths like `JSON_PARSE_FAIL` lack parity assertions if reason binning should be symmetric with substantive coverage.
- **Suggested revision**: Widen tests only if that parity is a product requirement; otherwise treat as optional follow-up.

### FINDING_12: [OUT_OF_SCOPE] Large committed run-log surface under larch-logs/implement
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Large run-log diffs are intentional under the repository run-logs policy and are not framed as a functional defect.
- **Suggested revision**: None required for correctness.

### FINDING_13: Plan checklist names C_NS_REASON but harness uses C_NSR_REASON
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Minor traceability friction when mapping review checklists to test identifiers and log strings.
- **Suggested revision**: Rename harness symbols to match the plan, or update the plan to the established `C_NSR_*` convention.
```
