### FINDING_1: Cross-cutting audit checks dropped from SKILL vs NDJSON coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Explicit cross-cutting guidance (e.g. self-deploying version gap vs fix version, closed-issue cross-reference) was removed from the skill; remaining NDJSON/`self_deploying_gap` semantics may not substitute, so audits can miss version-vs-fix and issue-closure checks or misread cross-cutting signals.
- **Suggested revision**: Restore equivalent checks in SKILL and/or encode them explicitly in `audit-scan-run` NDJSON with names/fields that match real semantics; align `self_deploying_gap` meaning with behavior or rename it.


### FINDING_11: Preflight tests reimplement helpers instead of running `audit-preflight.sh`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Tests mimic preflight logic rather than executing the script, so real `jq`/`gh`/`git` paths and the KV contract can regress while CI stays green.
- **Suggested revision**: Add `PATH` stub tests that invoke `audit-preflight.sh` for core outcomes.


### FINDING_12: No hermetic automated tests for `audit-close-priors.sh`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: KV emission/ordering bugs in close-priors may only show up in manual audits.
- **Suggested revision**: Add stub-`gh` hermetic tests similar to other audit-runs scripts.


### FINDING_14: `SKILL.md` scan table omits `changelog-rebase-conflicts` row
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Operators relying on the SKILL table can miss a scan that exists in `scans.tsv`.
- **Suggested revision**: Add the missing row to match the registry.


### FINDING_15: Legacy cumulative key `ns_retries_cursor_specialist_launches` not aliased in prior parsing
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Schema/examples move to new keys while `parse_prior` (or equivalent) ignores legacy names, silently zeroing NS retries and producing wrong cumulative totals; external parsers of filed reports may also break on the rename without migration guidance.
- **Suggested revision**: Alias legacy keys (and/or warn on unknown prior keys), and document a one-release dual-key migration for external consumers.


### FINDING_16: Required-file scan path join can escape the run-log subtree via `..` or absolute TSV paths
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Joining `RUN_DIR` with `relative_path` without rejecting `..` segments or absolute paths can turn existence checks into out-of-subtree probing when `RUN_DIR` is relative.
- **Suggested revision**: Reject absolute paths and `..` segments (or enforce canonical-prefix containment after join).


### FINDING_18: `PR_NUM` not validated before JSON/`jq --argjson` emission
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Non-numeric `--pr` can yield invalid NDJSON or a shell/`jq` failure under `set -e` instead of a clean contract error record; downstream aggregation may mis-sum or error intermittently.
- **Suggested revision**: Validate PR as digits-only (or stringify safely) and exit non-zero only after emitting a proper error NDJSON contract if that’s the intended behavior.


### FINDING_19: Repo mismatch diagnostics print the wrong identity pair
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Messages may show `REPO`/expected labels rather than the normalized `GH_REPO` vs parsed `REMOTE_REPO` actually compared, steering operators toward the wrong fix.
- **Suggested revision**: Print the exact compared pair (normalized remote vs `gh` identity) in the error output.


### FINDING_22: Missing run directory yields partial NDJSON then non-zero exit
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: A single NDJSON line plus exit can leave plausible-looking partial scan results and wrong partial counter sums.
- **Suggested revision**: Emit a complete per-scan error set, or mark the results file explicitly incomplete for downstream counters.


### FINDING_24: `audit-close-priors.sh` header comment mis-documents TAB-separated output
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Comment spacing/contract mismatch risks maintainers parsing stdout incorrectly.
- **Suggested revision**: Update the header comment to match the actual TAB-separated `CLOSE_FAILED` contract.


### FINDING_25: Plan fidelity: registry/schema expansion beyond stated plan scope
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Adds `changelog-rebase-conflicts` wiring through `scans.tsv`, `audit-scan-run.sh`, `audit-compute-counters.sh`, and SKILL cumulative counters while shifting frontmatter examples away from `ns_retries_cursor_specialist_launches`—not reflected in the enumerated plan/files scope.
- **Suggested revision**: Split into a follow-up with its own plan/issue, or amend the authoritative plan to explicitly require changelog countering and frontmatter migration.


### FINDING_3: `since-ISO` merged-at filter can match partial date-only prefixes
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: The since-ISO matcher may accept partial prefixes, so merged-at filtering can diverge from intended full instant comparisons against GitHub timestamps.
- **Suggested revision**: Align matching to the documented full ISO grammar and reject/error on partial inputs.


### FINDING_4: Preflight contract text misstates unconditional `git pull`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Concern**: `audit-preflight.md` describes behavior as if `git pull` always happens, while `audit-preflight.sh` branches differently off `main`, misleading operators about maintenance steps.
- **Suggested revision**: Update the markdown contract to match the script’s branching (or change the script if the doc is authoritative).


### FINDING_5: Tests duplicate resolve parsing instead of exercising `audit-resolve-prs.sh`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Concern**: `test-audit-runs.sh` reimplements verbal-description parsing and related regexes alongside the real resolver, so dispatch/regex and `PR_LIST` bugs can drift without failing CI; key since-last/since-iso/pr-ref paths stay thinly covered on the real script.
- **Suggested revision**: Consolidate coverage by stubbing `gh`/fixtures and invoking `audit-resolve-prs.sh` for the core outcomes instead of parallel parsers.


### FINDING_7: `LAST_PR` parsing from YAML is not normalized before `gh pr view`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: `LAST_PR` taken via `awk` may retain quotes/whitespace, causing `gh pr view` failures or an incorrect merged-at cutoff when the YAML value is quoted or padded.
- **Suggested revision**: Strip YAML quoting/whitespace, validate a numeric PR id, and fail fast before `gh` calls.


### FINDING_8: Wrong/missing `scans.tsv` yields misleading first NDJSON scan label
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: When the registry path is wrong, error NDJSON can label the line like a normal required-file-presence scan, misleading automation about what failed.
- **Suggested revision**: Use a distinct scan name or emit an explicit null/invalid scan record with detail that this is registry/path resolution failure.


### FINDING_9: Merged-PR listing can truncate after 100 API pages
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: PR history fetch is capped (e.g. 100 pages), so very large histories can truncate `PR_LIST` for since-last/ISO/last-N modes without a clear fail-closed signal.
- **Suggested revision**: Page until empty or detect truncation and fail closed (or otherwise guarantee completeness).


