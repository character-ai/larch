```text
### FINDING_1: changelog-rebase-conflicts NDJSON `result` vs `count` mismatch
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: `changelog-rebase-conflicts` NDJSON can report `result=pass` while `count>0`, so consumers that only trust `result` treat heuristic hits as clean while counters still increment (inconsistent with other scans’ semantics).
- **Suggested revision**: Align `result` with non-zero `count` (e.g., fail/neutral) **or** explicitly document counter-only semantics across `audit-scan-run.md` / `SKILL.md` and any downstream parsers.

### FINDING_2: Hermetic tests duplicate/stub shipped script behavior (preflight/resolve/scan paths)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Large parts of `test-audit-runs.sh` validate duplicated snippets/helpers instead of executing `audit-preflight.sh`, `audit-resolve-prs.sh`, and related scripts end-to-end; `resolve-prs` coverage is especially stub-heavy, leaving `gh api` pagination/jq/dispatch regressions undetected.
- **Suggested revision**: Refactor to subprocess the real scripts under a controlled fixture repo and `PATH`-wrapped `gh`/`git` fakes; extend stubs to cover the “five forms,” error paths, and key failure modes with assertions on real stdout (`ERROR=`, `PR_LIST=`, etc.).

### FINDING_3: `audit-pacific-timestamp.sh` manual fallback calendar/DST correctness
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Concern**: When `TZ=America/Los_Angeles` conversion isn’t available, the simplified Pacific/DST heuristic and day arithmetic can be wrong across DST boundaries, UTC midnight rollovers, and month/year boundaries (wrong or invalid wall-clock labels vs true `America/Los_Angeles` time).
- **Suggested revision**: Treat manual output as explicitly best-effort, fail closed unless TZ-based conversion succeeds, or replace with full calendar normalization / safe UTC `Z` fallback; document the chosen contract.

### FINDING_4: `audit-map-runs.sh` swallows `gh pr view` failures in fallback mapping
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Auth/network/user errors during fallback mapping can yield empty `run_id` without an explicit operator-facing error signal, masking integration failures until later steps.
- **Suggested revision**: Emit explicit stderr/KV diagnostics on `gh` mapping failure before continuing; avoid silent “empty mapping” success paths.

### FINDING_5: Repo mismatch messaging may mislabel compared slugs (`REPO` vs `GH_REPO`)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: The operator-facing message can print an “expected” slug that doesn’t correspond to the GitHub-derived comparison side, increasing confusion during mis-clones or mixed remotes.
- **Suggested revision**: Print both sides with clear labels (remote-derived vs `GH_REPO`) so the mismatch is unambiguous.

### FINDING_6: `audit-resolve-prs.sh` repeats expensive merged-PR pagination across branches
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Multiple branches trigger redundant full merged-PR fetches, increasing `gh api` cost on large repos.
- **Suggested revision**: Fetch/cache merged PR JSON once per invocation and reuse across branches.

### FINDING_7: [OUT_OF_SCOPE] Legacy inline parser tests duplicate production regexes
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Older inline parser tests duplicate production regexes, increasing maintenance burden; not uniquely introduced/resolved by this branch alone.
- **Suggested revision**: Refactor tests to call scripts/shared parsers opportunistically the next time this area is touched (policy-level cleanup).

### FINDING_8: Trailing-content test disagrees with `audit-scan-run.sh` whitespace semantics
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Concern**: The trailing-content helper/test logic can treat whitespace-only lines after `NO_ISSUES_FOUND` as failing, while the scanner’s “tail + non-whitespace” behavior treats them as non-semantic/pass—risk of false confidence or future incorrect tightening.
- **Suggested revision**: Align the test predicate with production’s non-whitespace tail check **or** explicitly assert both behaviors if both are intended contracts.

### FINDING_9: `audit-resolve-prs.sh` verbal forms are overly strict (case/punctuation)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Supported verbal intents can be rejected as `ERROR unrecognized` due to case/punctuation differences (e.g., “Since Last Audit” vs exact expected tokenization).
- **Suggested revision**: Normalize input (case folding / punctuation stripping) **or** document strict matching in `SKILL.md` + contract markdown so automation matches reality.

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

### FINDING_18: [OUT_OF_SCOPE] `audit-close-priors.sh` intentionally lacks unit tests (integration-only posture)
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt
- **Concern**: Close-priors behavior is manual/`gh`-integration oriented by contract; not necessarily a regression introduced by this diff’s stated test plan, but it concentrates risk in manual runs.
- **Suggested revision**: Keep as documented policy **or** add opt-in hermetic `gh` stub tests if policy changes.

### FINDING_19: Command injection via unquoted heredoc expanding `PR_LIST` (`audit-map-runs.sh`)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: An unquoted heredoc can expand `PR_LIST` before `read`, allowing command substitution/metacharacters in the list string to execute under the operator’s shell.
- **Suggested revision**: Use `<<'EOF'` (no expansion) and feed tokens safely (e.g., `IFS=',' read -r -a ... <<<"$PR_LIST"`) with strict numeric validation.

### FINDING_20: Shell interpolation of untrusted `--repo` / owner/repo segments into `gh api` URLs (`audit-resolve-prs.sh`)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Constructing API paths via double-quoted strings can execute expansions when repo slugs contain `$(...)` or similar metacharacters.
- **Suggested revision**: Validate GitHub `owner/name` slugs strictly **or** pass owner/repo to `gh` in ways that avoid shell-expanded URL segments.

### FINDING_21: `REPO` expanded in double quotes for `gh --repo` across multiple audit scripts
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Metacharacters/command substitutions in `--repo` can be evaluated by the operator shell before `gh` runs.
- **Suggested revision**: Centralize strict `owner/repo` validation once and reuse before any `gh --repo "$REPO"` construction.

### FINDING_22: `NEW_ISSUE` interpolated inside double-quoted `--body` (`audit-close-priors.sh`)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Non-numeric issue “numbers” like `1$(touch /tmp/x)` can execute while building `gh issue comment` arguments.
- **Suggested revision**: Restrict to `^[0-9]+$` **or** use `gh --body-file` with a safely written temp file.

### FINDING_23: `TIMESTAMP` expanded in double-quoted `printf` args (`audit-title.sh`)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Malicious `--timestamp` values can execute command substitutions during printf formatting.
- **Suggested revision**: Validate timestamp shape (same family of checks as Pacific timestamp regex policy) before any formatted output path.

### FINDING_24: `emit_error` can print multi-line `ERROR=` values (`audit-resolve-prs.sh`)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Crafted descriptions can inject extra stdout lines resembling additional KV pairs.
- **Suggested revision**: Encode errors as strictly single-line (shell-safe quoting), JSON, or base64; reject/control embedded newlines.

### FINDING_25: Symlink / arbitrary-prefix hazards in filesystem walks (`--log-root`, scan-result globs)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: `--log-root` may aim reads/globs outside the intended worktree; NDJSON aggregation may follow symlinks and read attacker-controlled content, skewing counters.
- **Suggested revision**: Resolve `LOG_ROOT` under the git worktree root and reject traversal; skip symlinks / require regular files for NDJSON inputs.

### FINDING_26: `eval` used to read required-arg variables (`audit-scan-run.sh`)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: `eval` is fragile if refactored to non-constant arg names and can become an accidental expansion footgun.
- **Suggested revision**: Replace with explicit per-variable empty checks (bash 3.2-safe).

### FINDING_27: `--pr` not validated as numeric before embedding in NDJSON (`audit-scan-run.sh`)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Non-numeric `--pr` can break NDJSON shape for `jq` consumers and weaken downstream assumptions.
- **Suggested revision**: Validate `^[0-9]+$` at startup (and normalize/strip leading zeros if arithmetic is used elsewhere).

### FINDING_28: `fetch_merged_main_prs_json` pagination cap can omit merged PRs (`audit-resolve-prs.sh`)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Hard caps (e.g., page limits) can omit PRs merged after a cutoff but beyond the fetched window, mis-reporting “none” or incomplete resolution.
- **Suggested revision**: Paginate until empty/error, or use a mergedAt-bounded query strategy with explicit completeness guarantees.

### FINDING_29: `parent-issue` fallback can pick the wrong run when multiple globs match (`audit-map-runs.sh`)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: “First glob match” behavior can be nondeterministic when multiple runs share an `ISSUE_NUMBER`, mapping to the wrong `run_id`.
- **Suggested revision**: Disambiguate by newest `started_at` (normalized), or error on ambiguity.

### FINDING_30: `audit-map-runs.sh` PR list parsing vs Bash 3.2 policy (reviewer disagreement)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-bash-portability-output.txt
- **Concern**: One reviewer claims `read -a` / array parsing is incompatible with macOS Bash 3.2 and fails at parse time; another reviewer asserts the shown `read -r -a` heredoc pattern is Bash 3.2-valid—leaves a portability/policy ambiguity that blocks confident “fix direction.”
- **Suggested revision**: Reconcile against repo `BASH_AUTHORING.md` / supported Bash baseline: either replace tokenization with explicitly approved 3.2-safe parsing **or** document/encode why the current approach is guaranteed safe on supported platforms.

### FINDING_31: Plan traceability: unplanned scan additions + cumulative schema churn vs written plan
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Introducing scans like `changelog-rebase-conflicts` and changing cumulative counter schema without an updated plan issue breaks reviewer traceability of intended vs accidental scope.
- **Suggested revision**: Revert/split scope: keep PR aligned to the written plan **or** file/update the plan issue to explicitly cover new scans/schema.

### FINDING_32: Stale header comment in `audit-title.sh` vs actual behavior/docs
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Header commentary about non-contiguous title branches is misleading relative to `audit-title.md` and implementation.
- **Suggested revision**: Sync the header comment with the real branching rules and documentation.

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

### FINDING_37: `SKILL.md` “Revised Orchestrator Flow” under-documents KV sets vs normative sections
- **Reviewer(s)**: dyn-kv-contract-output.txt
- **Concern**: The condensed flow omits keys documented earlier (`PR_COUNT`, `IMPLICIT_SINCE_LAST_AUDIT`, `ERROR`, `REASON`, etc.), encouraging implementers to follow an incomplete checklist.
- **Suggested revision**: Either list the full per-script KV set in the flow summary **or** explicitly defer to “full KV per contract `.md`” with zero ambiguity.

### FINDING_38: `audit-close-priors.md` spacing example mismatches tab-separated `CLOSE_FAILED`/`REASON` output
- **Reviewer(s)**: dyn-kv-contract-output.txt
- **Concern**: Markdown shows spaces between fields, but the script prints a tab delimiter—quick parsers based on docs can miss failures.
- **Suggested revision**: Update the contract example to show a literal tab (or explicitly label TAB-separated fields).

### FINDING_39: [OUT_OF_SCOPE] Bash 3.2 “advanced construct” checklist: no violations found in new audit-runs scripts/tests
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Concern**: Reviewer reports no `declare -A`, `mapfile`, `${var^^}`, `&>>`, `coproc`, etc., in the touched audit-runs surface (maintenance/verification note).
- **Suggested revision**: None required beyond keeping future edits within `BASH_AUTHORING.md` constraints.

### FINDING_40: [OUT_OF_SCOPE] `audit-pacific-timestamp.sh` manual fallback labeled behavioral approximation (non-Bash issue)
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Concern**: TZ-based conversion path plus `%z` normalization is considered reasonable on macOS/BSD; manual fallback is an intentional approximation rather than a Bash construct incompatibility.
- **Suggested revision**: If behavior changes, document approximation limits; no Bash-only action implied here.

### FINDING_41: [OUT_OF_SCOPE] Tooling/version dependencies (`jq`, `gh`, `sort -V`, `git branch`)
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Concern**: Scripts depend on external tool behaviors/flags outside the Bash construct checklist (environment matrix concern).
- **Suggested revision**: Track under installation/docs/CI image policy rather than bash-only linting.
```
