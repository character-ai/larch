Here is the merged structured finding list (sources treated as evidence only).

```text
### FINDING_1: partial_data skips all category-stats counter deltas
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Concern**: When `category-stats` sets `partial_data` (e.g. after jq/mangled-path failures), `audit-compute-counters.sh` skips every category-stats clean/blank delta even if canonical or OOS blank lines were still emitted, so a PR can silently lose OOS clean/blank counter movement while the scan NDJSON still looks partially healthy; related: error-path lines may lack counts while the same skip policy applies, risking a “zero delta” cumulative read on failure.
- **Suggested revision**: Narrow what `partial_data` means (or split flags) and change `audit-compute-counters` to skip only fields that are provably invalid; align counter policy with partial/error semantics or document intentional zero-deltas on error.

### FINDING_2: SKILL.md mis-documents CATEGORY_STATS_PARTIAL
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: `CATEGORY_STATS_PARTIAL` / `partial_data` documentation in `SKILL.md` still implies “missing JSONL only,” which will mislead operators once `partial_data` is also set for jq/mangled-category failures.
- **Suggested revision**: Update `SKILL.md` so partial triggers match the implemented scan and counter behavior after counter/partial semantics are finalized.

### FINDING_3: Duplicate jq passes over the same JSONL
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Concern**: `audit-scan-run.sh` runs the same `jq -f audit-scan-run-mangled-rows.jq` work twice per JSONL, doubling CPU/temp churn and duplicating failure handling.
- **Suggested revision**: Run the mangled-row jq once per JSONL and reuse its output for both emission sites (or cache to a single temp artifact per run).

### FINDING_4: Plan checklist omitted counter-contract updates
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: The implementation plan called out registry/script/tests but not coordinated updates to counter semantics docs/scripts when `partial_data` broadens beyond “missing file,” so cumulative counter behavior can drift without an explicit checklist guardrail.
- **Suggested revision**: Extend planning/checklist templates to include `audit-compute-counters.sh` and `audit-compute-counters.md` whenever category-stats partial semantics change.

### FINDING_5: [OUT_OF_SCOPE] audit-compute-counters.md CATEGORY_STATS_PARTIAL contract is stale
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: `audit-compute-counters.md` still documents `CATEGORY_STATS_PARTIAL` / `partial_data` as missing-`review-findings-full.jsonl` only; after the branch, `partial_data` can also reflect jq/mangled-category failures, so readers can mis-debug skipped OOS clean/blank deltas. (One source notes the file was not modified on this branch.)
- **Suggested revision**: Update `audit-compute-counters.md` to list every `partial_data` cause and the resulting effect on OOS clean/blank deltas, consistent with `audit-scan-run.md` / implementation.

### FINDING_6: [OUT_OF_SCOPE] Archived plan text about gh classify --state open
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Historical flushed plan text in the implement run log may still claim `gh classify` uses `--state open` for C.1, which can mislead someone who reads only that archived artifact.
- **Suggested revision**: Treat as historical record or edit the archived log in a follow-up if archival accuracy matters.

### FINDING_7: Missing harness for category-stats NDJSON on jq/mangle errors
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: No test asserts category-stats NDJSON when `oos-category-mangle` jq errors, so regressions in `partial_data` / `detail` / mangled semantics could ship without `test-audit-runs.sh` failing.
- **Suggested revision**: Add a hermetic fixture test: invalid JSONL → expect OOS result error plus category-stats `partial_data` with expected `detail` and mangled placeholder behavior.

### FINDING_8: C.2 version-window workflow lacks integration coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: The C.2 version-window / `gh`+`git` disambiguation path is not exercised by `test-audit-runs.sh`, so operator mistakes there will not be caught by the harness.
- **Suggested revision**: Accept the gap or add offline golden fixtures covering `version_window_checks`.

### FINDING_9: [OUT_OF_SCOPE] Implement run logs outside audit-runs test surface
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Per review scope, committed implement run logs are not part of the audit-runs automated test surface.
- **Suggested revision**: N/A for audit-runs harness scope; handle any follow-up outside this review surface if desired.

### FINDING_10: jq stderr embedded in NDJSON detail fields
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: On `oos-category-mangle` and `category-stats` partial paths, jq stderr can be copied into NDJSON `detail`, potentially leaking fragments of run-log JSON, paths, or other sensitive context into shared/archived scan output.
- **Suggested revision**: Replace raw stderr echo with opaque error codes or heavily redacted diagnostics consistently on both jq passes.

### FINDING_11: [OUT_OF_SCOPE] RUN_DIR not canonicalized/prefix-checked before jq reads
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: A mistaken or hostile `RUN_DIR` could point reads outside the intended implement log tree; behavior is largely pre-existing but remains a latent footgun.
- **Suggested revision**: Canonicalize `RUN_DIR` and enforce an expected run-log root prefix before opening inputs.

### FINDING_12: New jq helper omitted from plan traceability checklist
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: `audit-scan-run-mangled-rows.jq` is not reflected in the issue plan’s touched-path checklist, weakening traceability from plan to shipped helpers.
- **Suggested revision**: Optionally extend planning templates to list shared jq helper files explicitly.

### FINDING_13: Test echo labels / IDs drift from plan numbering
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Harness test numbering/extra C.2 cases do not match the plan’s 55–60 labels, making it harder to map plan bullets to assertions.
- **Suggested revision**: Rename harness labels or update the issue plan so labels align with final test IDs.

### FINDING_14: Mangled-row counting can undercount (null/missing `.id`, `wc -l` newline semantics)
- **Reviewer(s)**: dyn-jq-filter-semantics-output.txt
- **Concern**: `audit-scan-run-mangled-rows.jq` ends with `select(...) | .id` and the shell counts matches via `wc -l` on `jq -r` output; missing/JSON-null `.id` can emit no line, and a final value without a trailing newline can make `wc -l` report 0, allowing non-canonical category rows to yield `pass` with `count:0`.
- **Suggested revision**: Count matches inside jq (e.g. length over selected inputs, `add` of 1s, or one sentinel per match) so aggregates do not depend on `.id` printability or newline-terminated temp files.

### FINDING_15: Structured non-string `.category` values can be false negatives
- **Reviewer(s)**: dyn-jq-filter-semantics-output.txt
- **Concern**: Arrays/objects collapse to empty `catstr`, so `(catstr != "")` is false and those rows are never treated as mangled despite clearly non-canonical structured payloads under plan-review acceptance signals.
- **Suggested revision**: Decide policy: treat structured categories as mangled/fail (e.g. stringify or explicit non-string branch), or document as intentionally ignored only if the producer schema forbids non-strings.

### FINDING_16: [OUT_OF_SCOPE] Unrelated implement run artifacts broaden PR surface
- **Reviewer(s)**: dyn-jq-filter-semantics-output.txt
- **Concern**: Added files under `larch-logs/implement/9C7CDB30-2B1E-45E4-B7EB-77EDC4557CB3/` add PR surface area unrelated to the stated audit-runs jq/skill fixes.
- **Suggested revision**: Drop or relocate those artifacts in a follow-up if PR scope hygiene matters.

### FINDING_17: [OUT_OF_SCOPE] Broader SKILL/harness edits outside jq-counting focus
- **Reviewer(s)**: dyn-jq-filter-semantics-output.txt
- **Concern**: Documentation/harness updates in `SKILL.md` and `test-audit-runs.sh` (C.1/C.2/C.4 tables, session-summary stubs) are outside the narrow jq/`wc -l` correctness lens but appear directionally consistent with the described feature.
- **Suggested revision**: No action required for the jq-focused review thread; track separately if a narrower PR is desired.

### FINDING_18: SKILL “Revised Orchestrator Flow” overstates when session-summary runs
- **Reviewer(s)**: dyn-skill-orchestration-spec-output.txt
- **Concern**: The flow line implies session-summary posts whenever an audit-report issue exists, but normative prose and hermetic stubs indicate it must not run after step 2’s zero-findings short-circuit (empty proposals), so the diagram can disagree with the spec and tests.
- **Suggested revision**: Tighten the flow line to match step 4 verbatim (e.g. require non-empty `AUDIT_REPORT_NUMBER` and no step-2 short-circuit), or split short-circuit vs post-walkthrough branches.

### FINDING_19: PR disambiguation tie-break lacks explicit fallback when no merge is after issue creation
- **Reviewer(s)**: dyn-skill-orchestration-spec-output.txt
- **Concern**: “Prefer mergedAt closest after issue createdAt” has no stated rule when no candidate merges strictly after `createdAt`, inviting arbitrary LLM choices and weakening “no silent suppression” for `version_window_checks`.
- **Suggested revision**: Add an explicit empty-set fallback aligned with ambiguity handling (e.g. latest mergedAt among `closes #N` candidates, or mark `in_scope: true` with both PRs and rationale if still indeterminate).
```
