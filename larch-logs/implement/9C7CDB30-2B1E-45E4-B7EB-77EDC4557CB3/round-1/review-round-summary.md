# Review Round 1

- Mode: `diff`
- Accepted findings: 5
- Rejected findings: 0
- Exonerated findings: 2
- Neutral findings: 2

## Accepted Findings

### FINDING_1: C.1 tests do not enforce IN PROGRESS / gh-search classification contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-test-numbering-coverage-output.txt
- **Concern**: Harness “C.1” coverage is effectively a yes/no stub around generic open-match routing (e.g. `yes`/`no` literals) and does not model issue titles, `[IN PROGRESS]`, `--state all` vs open-only, or other precedence/exclusion rules from `SKILL.md`, so regressions restoring title exclusion or wrong search state could still leave CI green while contradicting the documented operator contract (including assertion text that implies an `[IN PROGRESS]` path the stub never exercises).
- **Suggested revision**: Replace or extend with hermetic fixture issue JSON (or a shared sourced classifier) that encodes the real precedence/exclusion rules and fails on the regressions above; align assertion text with what the test actually models.


### FINDING_2: scan_oos_category_mangle jq counting is brittle under pipefail and can jq-fatal on non-string categories
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-jq-pipeline-counting-output.txt, dyn-version-window-semantics-output.txt
- **Concern**: Under `set -euo pipefail`, the `oos-category-mangle` count pipeline lacks the localized soft-fail pattern used by sibling scans (e.g. `|| echo 0` on comparable `jq|wc|tr` substitutions), so `jq`/JSONL parse or I/O failures can abort the entire driver before emitting remaining scan NDJSON. Separately, `test()`/string ops on `.category` without enforcing string type can turn odd-typed `category` values into jq errors with the same “kill the whole run” failure mode.
- **Suggested revision**: Match the defensive substitution style of `scan_rej_category_blank` / `category-stats` (or emit a bounded per-scan `result:"error"` without aborting other scans), and guard or coerce `.category` as a string before classification predicates.


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


