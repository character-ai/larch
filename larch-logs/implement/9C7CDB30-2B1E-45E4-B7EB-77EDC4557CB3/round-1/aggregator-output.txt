Aggregating duplicate reviewer themes into one normalized list. Merging overlapping items (same file/behavior): **oos-category-mangle** pipefail/`|| echo 0` + **string type guard** on `.category`; **C.1** stub coverage; **test numbering**; **Augmentations** header; **SKILL** session-summary vs short-circuit; **C.2 / version-window** documentation gaps; **shell quoting** in examples. **Out-of-scope** items are separate tagged findings per your rules.

```text
### FINDING_1: C.1 tests do not enforce IN PROGRESS / gh-search classification contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-test-numbering-coverage-output.txt
- **Concern**: Harness “C.1” coverage is effectively a yes/no stub around generic open-match routing (e.g. `yes`/`no` literals) and does not model issue titles, `[IN PROGRESS]`, `--state all` vs open-only, or other precedence/exclusion rules from `SKILL.md`, so regressions restoring title exclusion or wrong search state could still leave CI green while contradicting the documented operator contract (including assertion text that implies an `[IN PROGRESS]` path the stub never exercises).
- **Suggested revision**: Replace or extend with hermetic fixture issue JSON (or a shared sourced classifier) that encodes the real precedence/exclusion rules and fails on the regressions above; align assertion text with what the test actually models.

### FINDING_2: scan_oos_category_mangle jq counting is brittle under pipefail and can jq-fatal on non-string categories
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-jq-pipeline-counting-output.txt, dyn-version-window-semantics-output.txt
- **Concern**: Under `set -euo pipefail`, the `oos-category-mangle` count pipeline lacks the localized soft-fail pattern used by sibling scans (e.g. `|| echo 0` on comparable `jq|wc|tr` substitutions), so `jq`/JSONL parse or I/O failures can abort the entire driver before emitting remaining scan NDJSON. Separately, `test()`/string ops on `.category` without enforcing string type can turn odd-typed `category` values into jq errors with the same “kill the whole run” failure mode.
- **Suggested revision**: Match the defensive substitution style of `scan_rej_category_blank` / `category-stats` (or emit a bounded per-scan `result:"error"` without aborting other scans), and guard or coerce `.category` as a string before classification predicates.

### FINDING_3: category-stats mangled metric can disagree with narrowed oos-category-mangle counts
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: `category-stats` / `mangled_count` appears to count mangled categories across broader phases than the narrowed `oos-category-mangle` scan (e.g. plan-review accepted rows only), so NDJSON tables can contradict each other and confuse audit triage—potentially more visible after narrowing the scan by design.
- **Suggested revision**: Align the `mangled_count` jq filter with the `oos-category-mangle` scope, or split/rename into two explicitly labeled metrics with clear semantics in emitted NDJSON.

### FINDING_4: Session-summary / “no audit number” tests are mostly static shape checks, not orchestration-faithful
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Tests largely validate static heredocs/trivial guards, so markdown template drift from the real posting path could go undetected while still passing as “shape tests.”
- **Suggested revision**: Rename/mark as shape-only tests, factor a shared builder used by the skill flow and test that, or otherwise anchor assertions to the same composition function the orchestration uses.

### FINDING_5: Harness test IDs/comments drift from written plan numbering (55–60 vs 56–61)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-jq-pipeline-counting-output.txt, dyn-test-numbering-coverage-output.txt
- **Concern**: Plan-to-harness traceability is weakened when test numbering/labels don’t match the implementation plan, increasing review mis-mapping risk.
- **Suggested revision**: Renumber comments/labels to match the plan, or add a short stable mapping table in the harness header documenting the correspondence.

### FINDING_6: Session-summary composition test omits Augmentations table header coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: The session-summary markdown test can pass if the Augmentations table is deleted while other headers/footer remain, reducing regression signal for that required section.
- **Suggested revision**: Add an explicit assertion/grep for the Augmentations markdown table header (or equivalent structural check).

### FINDING_7: SKILL.md prose/diagram implies session-summary always accompanies certain post-report steps
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Operator-facing flow text pairs session-summary with later steps (e.g. 3-way walkthrough) in ways that read unconditional, but zero-proposals / early exits can skip session-summary posting, creating expectation mismatch versus actual control flow (including “run whenever an audit report exists”-style overstatements).
- **Suggested revision**: Clarify branching/ordering: explicitly document when session-summary is skipped vs posted, and align the revised orchestrator flow block/diagram wording with the real short-circuit paths.

### FINDING_8: C.2 version-window procedure is operationally under-specified (semver, bump extraction, gh ambiguity, YAML examples)
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-version-window-semantics-output.txt, dyn-test-numbering-coverage-output.txt
- **Concern**: The skill adds non-trivial manual steps (open+closed search, fix timing, bump/version correlation, semver comparisons vs batch `larch_version`, unknown bump handling, `version_window_checks` row grammar) without a normative mechanical recipe: ad hoc ordering can mis-rank semver; `git log --oneline --grep` + subject parsing is not a stable file-shaped contract; `gh pr list --search` can be empty/ambiguous without tie-break rules; examples under-document `decision`/`in_scope` combinations including `propose`. Automated coverage asymmetry vs C.3-style scan tests increases the chance these ambiguities ship as silent operator judgment.
- **Suggested revision**: Document explicit normalization + comparator approach, bind `fix_shipped_version` extraction to a stable source (e.g. `plugin.json` at a chosen revision with fallback), add PR disambiguation rules (or require recording candidates + rationale), expand YAML examples to cover the full decision grammar, and optionally add offline golden tests for the classifier/YAML row shapes.

### FINDING_9: SKILL.md examples encourage risky shell quoting for gh/git search text
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Double-quoted search strings/ISO instants in copy-pastable examples increase foot-gun risk if operators paste metacharacters into composed shell one-liners.
- **Suggested revision**: Prefer single-quoted searches, env-based args, `printf %q`, or otherwise mirror the repo’s “body-file safety” style for user-supplied text.

### FINDING_10: [OUT_OF_SCOPE] Committed implement run-log tree and related reviewer-noise concerns
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-jq-pipeline-counting-output.txt, dyn-version-window-semantics-output.txt, dyn-test-numbering-coverage-output.txt
- **Concern**: Multiple reviewers flag the added `larch-logs/implement/9C7CDB30-2B1E-45E4-B7EB-77EDC4557CB3/` tree (including `manifest.json` placeholder paths, embedded plan snapshots predating final SKILL wording) as potentially distracting or looking like accidental noise; sources also note this may be intentional per run-log policy rather than an audit-runs logic defect.
- **Suggested revision**: Treat as policy/process hygiene separate from the audit-runs behavior change (confirm intentional run-log commit conventions; optional editorial refresh of historical artifacts only if desired).

### FINDING_11: [OUT_OF_SCOPE] Offline harness cannot validate live gh/git failure modes and full C.2 end-to-end behavior
- **Reviewer(s)**: dyn-version-window-semantics-output.txt, dyn-test-numbering-coverage-output.txt
- **Concern**: Sources characterize gaps (no real `gh` issue search / `git log` bump resolution / `gh issue comment` failure handling in offline tests) as acceptable limitations of a lightweight harness rather than proof those paths are correct.
- **Suggested revision**: None required for merge-blocking audit-runs logic review; optionally add scoped integration checks if the project wants stronger guarantees.

### FINDING_12: [OUT_OF_SCOPE] Scout clarification: `.id` null lines vs `wc -l` is not the primary miscount hazard
- **Reviewer(s)**: dyn-jq-pipeline-counting-output.txt
- **Concern**: For rows that pass `select`, counting lines from `jq -r ... .id` is not inherently invalidated by JSON `null` ids in the way some scout notes feared; the substantive robustness issue called out elsewhere is `jq`/pipeline failure behavior under `pipefail` aborting the driver.
- **Suggested revision**: Keep investigation focused on localized jq failure handling and category typing/guards (see in-scope scan robustness finding), not the `.id` null/`wc` red herring.
```
