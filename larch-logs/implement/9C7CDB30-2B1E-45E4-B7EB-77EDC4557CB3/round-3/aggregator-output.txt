```text
### FINDING_1: OOS mangled cumulative counters ignore `oos-category-mangle` error NDJSON
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: When per-run NDJSON reports `oos-category-mangle` with a non-pass/error `result`, the mangled delta path can still behave like “count-only” success (often contributing `0`), so cumulative counters can disagree with scan-visible failures unless aggregation keys off `result` (or treats errors as partial/non-numeric explicitly).
- **Suggested revision**: Gate mangled deltas on `result` (and/or propagate a partial/failure aggregate state) so error lines cannot be silently folded into “clean pass” counter math; add/adjust a contract test for “error NDJSON + counter delta” if behavior becomes normative.

### FINDING_2: `audit-scan-run.sh` can emit contradictory outputs on jq/JSONL corruption (OOS error vs `category-stats` “complete” zeros)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: `oos-category-mangle` can surface jq/parse failures as a structured scan error while the `category-stats` jq path may swallow failures into plausible zeros with `partial_data:false`, producing internally inconsistent NDJSON for the same input artifact.
- **Suggested revision**: Reuse one parse path or align contracts so jq failures set `partial_data` (or an explicit error/partial flag) on `category-stats` whenever the OOS scan is in an error state; avoid “error + plausible zeros” contradictions.

### FINDING_3: Duplicated `jq` programs / drift between OOS scan and `category-stats` mangled aggregation
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-jq-filter-asymmetry-output.txt
- **Concern**: The same (or closely related) `jq` filtering logic exists in multiple places, so fixes to error handling, narrowing, or normalization can diverge and reintroduce mismatches between `oos-category-mangle` and `category-stats.mangled`.
- **Suggested revision**: Factor a single shared `jq` program (literal or helper-sourced) used by both code paths, and update both together when semantics change.

### FINDING_4: `catstr` drops non-scalar `.category` values, weakening mangled detection vs prior behavior
- **Reviewer(s)**: dyn-jq-filter-asymmetry-output.txt
- **Concern**: Mapping non-strings to `""` makes `catstr != ""` false for array/object categories, silently excluding rows from both `oos-category-mangle` and `category-stats.mangled`, which can yield false `pass`/zero mangled where older pipelines still surfaced a non-canonical signal for malformed payloads.
- **Suggested revision**: Treat present-but-non-string categories as explicit failures (strict) or normalize with a dedicated branch/`tostring` fallback so malformed categories cannot “disappear” from the regression detector.

### FINDING_5: `mktemp` / temp path handling is fragile under resource errors and weakens downstream error contracts
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Unchecked `mktemp` can yield empty/problematic temp paths; combined with redirects/`set -e`, failures may abort broader scanning or degrade into non-deterministic jq errors instead of a single structured scan error object.
- **Suggested revision**: Assert `mktemp` success (non-empty paths), validate before use, and emit a structured scan error (optionally scoped so one failure doesn’t necessarily nuke unrelated scans, depending on intended UX).

### FINDING_6: Narrow OOS filter depends on exact phase/outcome strings with limited boundary coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Strict string equality on phase/outcome (and narrowed plan-review/accepted semantics) is sensitive to casing/legacy enum drift; without fixtures, producer changes could shift pass/fail without CI signal.
- **Suggested revision**: Normalize canonical strings (or explicitly support legacy spellings) and add fixtures covering accepted/rejected plan-review rows plus casing/prose edge cases as appropriate.

### FINDING_7: Operator confusion risk: `category-stats` canonical/blank universes vs narrowed `mangled`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: After narrowing `mangled`, readers may misread totals as complementary with canonical/blank even though scopes differ.
- **Suggested revision**: Document the scope split adjacent to the scan table in operator-facing docs (`SKILL.md` / scan contract docs) so totals aren’t misinterpreted.

### FINDING_8: Misleading harness section labeling around “Test 61” / empty short-circuit cases
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Section titles/echo text don’t reflect cases like empty `AUDIT_REPORT_NUMBER` / zero-findings short circuits covered nearby, increasing maintenance confusion.
- **Suggested revision**: Rename section output to explicitly include the empty/zero-findings cases the harness exercises.

### FINDING_9: Shell snippet safety: examples interpolate search terms/timestamps without strong argv-safe guidance
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: `gh`/`git` examples that embed dynamic fragments can be unsafe if copied into wrappers that concatenate untrusted text, risking broken quoting or unintended execution boundaries.
- **Suggested revision**: Document argv-safe patterns (`gh --jq`, `jq --arg`, env vars) and warn against naive `bash -c` / string-concatenation of untrusted substrings.

### FINDING_10: Ambiguous discuss-first completion semantics for session-summary triggering
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: If “discuss-first” completion is ambiguous, the session-summary trigger may misfire or be skipped, affecting downstream audit-report commenting behavior.
- **Suggested revision**: Define an explicit completion sentinel / decision rule for discuss-first paths in the skill procedure.

### FINDING_11: Plan appendix vs harness test numbering/traceability mismatch
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Plan checklist numbering doesn’t match harness labels (extra/missing tests), creating traceability noise for reviewers grepping plan vs code.
- **Suggested revision**: Align labels or add a short mapping table in PR/issue notes linking plan items to harness test IDs.

### FINDING_12: Plan text vs shipped skill: C.1 “open-only” implication vs C.2 `--state all`
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Readers relying on plan §C.1 alone may infer open-only `gh` search while the final skill reflects C.2 broader state semantics.
- **Suggested revision**: Clarify in planning docs that C.2 supersedes the earlier open-only note (doc-only reconciliation).

### FINDING_13: Vacuous “suppress when fix version > all audited versions” if audited-version set is empty
- **Reviewer(s)**: dyn-version-window-logic-output.txt
- **Concern**: Universal quantification over an empty audited-version list makes “greater than every audited version” vacuously satisfiable, which could wrongly justify suppression unless explicitly guarded; harness logic already biases toward `propose` on empty lists.
- **Suggested revision**: Add normative SKILL text: suppression applies only when there is at least one successfully parsed audited `larch_version`; if empty, do not suppress—propose and record rationale in `version_window_checks`.

### FINDING_14: [OUT_OF_SCOPE] Ancillary `larch-logs/implement/...` material, optional doc hygiene, and non-defect confirmations
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-version-window-logic-output.txt, dyn-jq-filter-asymmetry-output.txt
- **Concern**: Multiple slots flag committed implement run-log chunks / flushed plan artifacts / optional counter-doc sample updates / intentional canonical-vs-mangled asymmetry already documented in `audit-scan-run.md` / meta `git log` notes as orthogonal widening or “no product defect” observations rather than required functional fixes.
- **Suggested revision**: Treat as repo policy / optional hygiene unless redaction or doc standards tighten; no functional change required solely on these grounds.
```
