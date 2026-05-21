### FINDING_1: changelog-rebase-conflicts NDJSON `result` vs `count` mismatch
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: `changelog-rebase-conflicts` NDJSON can report `result=pass` while `count>0`, so consumers that only trust `result` treat heuristic hits as clean while counters still increment (inconsistent with other scans’ semantics).
- **Suggested revision**: Align `result` with non-zero `count` (e.g., fail/neutral) **or** explicitly document counter-only semantics across `audit-scan-run.md` / `SKILL.md` and any downstream parsers.


### FINDING_10: Missing `--run-dir` NDJSON `scan` field mismatches plan/examples
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Missing `--run-dir` emits a “setup” style scan identifier rather than the plan-literal/required-file-presence sentinel, so fixtures/automation keyed to the plan’s first NDJSON line won’t match actual stdout.
- **Suggested revision**: Align emitted `scan` values with the written plan **or** update plan + all consumers/tests consistently.


### FINDING_11: Incomplete hermetic NDJSON happy/fail coverage across `scans.tsv` registry scans
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Concern**: Coverage is partial for several registry scans; regressions in scans like codex/cache could ship while the hermetic suite stays green.
- **Suggested revision**: Add minimal per-scan fixture NDJSON assertions driven through `audit-scan-run.sh` for remaining scan types (happy + representative fail paths where applicable).


### FINDING_12: `audit-map-runs.sh` picks newest run via raw `started_at` string ordering
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Lexicographic compare of mixed ISO timestamp formats can mis-order manifests and select the wrong newest `RUN_ID`.
- **Suggested revision**: Compare normalized timestamps (`jq` parsing) or version-sort normalized values, not raw strings.


### FINDING_13: `audit-title.sh` PR de-duplication/contiguity heuristics + missing long-list regression tests
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Concern**: Duplicate PR numbers can break contiguous-range detection and pollute title hashes; long explicit non-contiguous lists lack automated snapshot coverage, so formatting bugs may ship unnoticed.
- **Suggested revision**: Sort/dedupe PR tokens before contiguity checks/title build; add a bash-level `audit-title.sh` case with many PRs and snapshot `TITLE=` output.


### FINDING_14: Contract docs claim pervasive exit `0` while unknown argv exits `1` (preflight + resolve)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Markdown contracts imply success/exit-`0` posture, but unknown argv can exit `1` with stderr-only diagnostics—host parsers that ignore exit codes may continue incorrectly.
- **Suggested revision**: Align documentation with real exit semantics **or** emit explicit `PREFLIGHT_OK=false` / structured `ERROR` and exit `0` for argv errors (pick one contract and apply consistently).


### FINDING_15: `parent-issue.md` fallback path in `audit-map-runs.sh` lacks hermetic coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Unmapped `pr_number` fallback behavior (issue parsing/manifest fill) is not exercised end-to-end; regressions in `ISSUE_NUMBER` parsing or post-fallback mapping may not fail `make test-audit-runs`.
- **Suggested revision**: Add fixture log-root + optional `gh pr view` stub returning `Closes #N`, asserting stable TSV output from the real `audit-map-runs.sh`.


### FINDING_16: No hermetic coverage for `audit-compute-counters.sh --prior-frontmatter`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Real YAML prior parsing and additive totals can regress without failing CI.
- **Suggested revision**: Add a prior-frontmatter fixture and assert cumulative KV totals via the real script invocation.


### FINDING_17: `cumulative_counters` schema churn may break external parsers
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Removing/renaming keys (e.g., dropping `ns_retries_cursor_specialist_launches`) can break downstream consumers expecting older schemas.
- **Suggested revision**: Document migration guidance and/or temporarily duplicate deprecated keys while consumers update.


### FINDING_19: Command injection via unquoted heredoc expanding `PR_LIST` (`audit-map-runs.sh`)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: An unquoted heredoc can expand `PR_LIST` before `read`, allowing command substitution/metacharacters in the list string to execute under the operator’s shell.
- **Suggested revision**: Use `<<'EOF'` (no expansion) and feed tokens safely (e.g., `IFS=',' read -r -a ... <<<"$PR_LIST"`) with strict numeric validation.


### FINDING_29: `parent-issue` fallback can pick the wrong run when multiple globs match (`audit-map-runs.sh`)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: “First glob match” behavior can be nondeterministic when multiple runs share an `ISSUE_NUMBER`, mapping to the wrong `run_id`.
- **Suggested revision**: Disambiguate by newest `started_at` (normalized), or error on ambiguity.


### FINDING_33: `set -e` + `grep -c` can abort before empty `--pr-list` error handling (`audit-title.sh`)
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Concern**: When all PR tokens are invalid and `SORTED_PRS` is empty, `grep -c .` returns exit status 1 and can terminate the script before the intended user-facing error path.
- **Suggested revision**: Count lines without a failing pipeline on zero matches (e.g., `awk` counter, or `grep -c` wrapped so the assignment never inherits failure under `set -e`).


### FINDING_34: Leading-zero PR tokens can break Bash 3.2 arithmetic / octal interpretation (`audit-title.sh`, `test-audit-runs.sh`)
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Concern**: `grep -E '^[0-9]+$'` still allows leading zeros; `10#` radix issues can make contiguity width wrong or error on invalid “octal-looking” values (same pattern in `is_contiguous` tests).
- **Suggested revision**: Force decimal radix (`$((10#LAST - 10#FIRST + 1))`) **or** normalize PR tokens to strip leading zeros before arithmetic.


### FINDING_35: `SKILL.md` title flow omits stripping `TITLE=` prefix while script emits KV-shaped stdout
- **Reviewer(s)**: dyn-kv-contract-output.txt
- **Concern**: Examples treat `TITLE_OUT` as a bare title string, but `audit-title.sh` prints `TITLE=...`; naive piping into issue creation can literally prefix titles with `TITLE=`.
- **Suggested revision**: Document `sed -n 's/^TITLE=//p'` (or equivalent) alongside the `PACIFIC_TIMESTAMP` stripping pattern, and align examples with actual stdout.


### FINDING_36: `SKILL.md` “Close Prior Reports” omits partial-failure / stderr KV surface emitted by `audit-close-priors.sh`
- **Reviewer(s)**: dyn-kv-contract-output.txt
- **Concern**: Skill text narrows success to `CLOSED_NUMBER=...` lines, but the script can emit `ISSUE_LIST_FAILED`, per-issue `CLOSE_FAILED`, and `REASON` while still exiting `0` in some partial-failure modes—risk of treating half-failed closes as full success.
- **Suggested revision**: Enumerate stdout keys + exit-code rules in `SKILL.md` (fail-fast cases vs scan-for-`CLOSE_FAILED` on exit `0`).


### FINDING_38: `audit-close-priors.md` spacing example mismatches tab-separated `CLOSE_FAILED`/`REASON` output
- **Reviewer(s)**: dyn-kv-contract-output.txt
- **Concern**: Markdown shows spaces between fields, but the script prints a tab delimiter—quick parsers based on docs can miss failures.
- **Suggested revision**: Update the contract example to show a literal tab (or explicitly label TAB-separated fields).


### FINDING_4: `audit-map-runs.sh` swallows `gh pr view` failures in fallback mapping
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Auth/network/user errors during fallback mapping can yield empty `run_id` without an explicit operator-facing error signal, masking integration failures until later steps.
- **Suggested revision**: Emit explicit stderr/KV diagnostics on `gh` mapping failure before continuing; avoid silent “empty mapping” success paths.


### FINDING_8: Trailing-content test disagrees with `audit-scan-run.sh` whitespace semantics
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Concern**: The trailing-content helper/test logic can treat whitespace-only lines after `NO_ISSUES_FOUND` as failing, while the scanner’s “tail + non-whitespace” behavior treats them as non-semantic/pass—risk of false confidence or future incorrect tightening.
- **Suggested revision**: Align the test predicate with production’s non-whitespace tail check **or** explicitly assert both behaviors if both are intended contracts.


