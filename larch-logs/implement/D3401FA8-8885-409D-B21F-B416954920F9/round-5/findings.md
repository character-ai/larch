Here is the aggregated structured finding list. In-scope items are merged by shared behavioral risk; out-of-scope items are listed after in-scope so `[OUT_OF_SCOPE]` headings stay accurate without merging important in-scope work into tagged headings.

```text
### FINDING_1: scans.tsv registry drift vs hardcoded scan dispatch
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: `scans.tsv` type/pattern columns are not consumed; scans are driven by a hardcoded `case` statement. Operators may add a TSV row without wiring a new branch, causing silent drift or exit-on-unknown at runtime.
- **Suggested revision**: Make the registry truly data-driven (e.g. codegen) or simplify `scans.tsv` to an ordered name list without unused columns.

### FINDING_2: audit-resolve-prs merged-PR pagination cost
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: `fetch_merged_main_prs_json` paginates all closed PRs into a large in-memory JSON array. Large org repos can make resolution slow, memory-heavy, and rate-limit heavy for last-N, since-ISO, or since-last-audit modes.
- **Suggested revision**: Replace with targeted GraphQL/REST filtered by `mergedAt`/base, or document and enforce an explicit hard cap.

### FINDING_3: duplicated fake `gh api` stub heredocs in tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Duplicate heredoc stubs for the fake `gh api` protocol increase maintenance when the stub contract changes.
- **Suggested revision**: Extract one shared stub script or helper sourced by both tests.

### FINDING_4: manual Pacific timestamp fallback is not real Pacific
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: When `TZ=America/Los_Angeles` is unavailable, the manual path uses coarse month bands for DST (not US transition rules), fixed Apr–Oct offsets, and skips civil day/month/year rollover when adjusting from UTC. Late March / early November and UTC-midnight boundaries can yield wrong wall-clock dates/offsets while still exiting 0, mis-dating chain-of-history titles.
- **Suggested revision**: Prefer a real TZ path; otherwise use correct DST/civil-date arithmetic, fail closed, emit an explicit unreliable flag, or fall back to UTC with a clear operator warning—do not present manual output as authoritative Pacific.

### FINDING_5: `normalize_repo` truncates dotted GitHub repo names for `*.git` SSH URLs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Dotted repo segments in SSH URLs like `git@github.com:org/foo.bar.git` can normalize to `org/foo`, disagreeing with `gh`’s `org/foo.bar` and yielding false `PREFLIGHT_OK` repo mismatch.
- **Suggested revision**: Align `.git` URL capture with the non-`.git` pattern so dots are allowed in the repo segment.

### FINDING_6: `parse_prior` awk may match duplicate keys outside intended YAML context
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Substring key matching can pick up duplicate key mentions in free text and corrupt prior counter baselines.
- **Suggested revision**: Parse only under the `cumulative_counters` block or use structured YAML tooling.

### FINDING_7: `audit-scan-run` path validation order and error signaling mismatch
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Missing `--run-dir` can short-circuit before other argument validation, forcing multiple fix cycles; emitting NDJSON then exiting non-zero differs from KV scripts that exit 0, which can interact badly with `set -e` pipelines and partial log capture.
- **Suggested revision**: Validate all path arguments before emitting partial NDJSON or batch errors; standardize error signaling (KV + exit 0 vs NDJSON + non-zero) and document required shell patterns in SKILL/contract markdown.

### FINDING_8: `audit-compute-counters` silent all-zero deltas when no scan NDJSON matches
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Default glob behavior can read zero scan files, producing priors-only output with no warning—wrong `--scan-results-dir` or filename patterns look like a successful empty delta.
- **Suggested revision**: Emit `SCAN_FILES_FOUND=0` (or equivalent) or fail when no matching NDJSON files were read.

### FINDING_9: plan text vs implemented run-dir missing contract shape
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Implementation/plan referenced required-file-presence style signaling while code emits `run-dir-missing` (per `audit-scan-run.md` / tests), confusing plan-only consumers about the error row shape.
- **Suggested revision**: Update plan/issue text or align the scan key with the documented contract.

### FINDING_10: preflight checks reimplemented in tests instead of invoking `audit-preflight.sh`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Concurrency/repo checks duplicated inline can diverge from shipped `jq`/`date`/`gh` behavior while tests still pass; the plan asked to test the real script.
- **Suggested revision**: Stub `gh issue list` + `jq` paths and assert `PREFLIGHT_OK` on the real `audit-preflight.sh`; remove redundant inline duplicates.

### FINDING_11: CI gap—registry scan types not all exercised via real `audit-scan-run.sh`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Hermetic tests do not run `audit-scan-run.sh` for every `scans.tsv` scan type with NDJSON assertions; registry scans can regress without signal despite per-scan NDJSON coverage goals.
- **Suggested revision**: Add minimal fixture runs per missing scan invoking the real script with `jq` checks for pass/fail/skip shapes.

### FINDING_12: verbal-form dispatch logic duplicated vs `audit-resolve-prs.sh`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Test-side dispatch mirrors production rules; divergence can yield green tests while the skill script misroutes descriptions.
- **Suggested revision**: Add per-form integration tests against the real resolver or share one parser implementation.

### FINDING_13: verbal resolution is strict (case/whitespace) vs human-readable phrases
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Exact-match/case-sensitive handling for several forms rejects operator text that looks valid (extra spaces, different case), conflicting with natural-language SKILL prose unless tightened there.
- **Suggested revision**: Normalize case/whitespace for canonical phrases or tighten SKILL to match strict parsing.

### FINDING_14: weak `audit-pacific-timestamp` test assertions
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Tests only check a weak datetime prefix; Pacific offset vs UTC-`Z` fallback contract is untested, letting subtle timestamp bugs slip through.
- **Suggested revision**: Tighten regex for documented offsets and add a controlled fallback test or document CI skip for `Z` output.

### FINDING_15: `audit-preflight` may echo raw `remote.origin.url` on identity parse failure
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: PATs or token-in-URL remotes can leak credentials into stdout transcripts and automation captures when normalization fails or URLs are malformed.
- **Suggested revision**: Strip userinfo from URLs or print only owner/repo; never `printf` raw `remote.origin.url` on failure paths.

### FINDING_16: unanchored operator paths (`--log-root`, scan/counter CLI paths)
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-shell-injection-output.txt
- **Concern**: `--log-root` and other path flags are not confined to the repo workspace; mistaken or hostile paths can bulk-read arbitrary directories or steer NDJSON/prior parsing at sensitive trees, enabling disclosure or misleading aggregates.
- **Suggested revision**: Resolve realpaths and enforce a single anchored workspace prefix (or reject `..`/absolute escapes) before opening files or globbing.

### FINDING_17: machine-unsafe KV lines from free-text fields (`ERROR`, `RESOLVED_ECHO`, related)
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-shell-injection-output.txt
- **Concern**: Embedded newlines/control characters and unescaped `=` in operator-controlled descriptions can append extra stdout lines, spoof keys, or break sed/KV consumers; overlaps newline-safety and injection-shaped stdout parsing hazards.
- **Suggested revision**: Normalize to single-line values (strip/replace controls), length-prefix, JSON-encode a side channel, or build records with `jq -n` and `--arg`/`--argjson` for every field.

### FINDING_18: `jstr()` insufficient escaping breaks hand-built NDJSON in `audit-scan-run.sh`
- **Reviewer(s)**: dyn-shell-injection-output.txt
- **Concern**: Escaping only `\` and `"` lets `\n`/`\r`/`\t`/controls through into concatenated JSON, producing invalid JSON or split NDJSON lines that confuse downstream `jq`.
- **Suggested revision**: Extend `jstr` for common controls or stop hand-building JSON—emit objects with `jq -n` and `--arg` per string field.

### FINDING_19: `audit-title.sh` passes `--timestamp` through to a single-line `TITLE=` record
- **Reviewer(s)**: dyn-shell-injection-output.txt
- **Concern**: Embedded newlines/control characters can break or multi-line `TITLE=` output with KV/log spoofing risk for structural parsers.
- **Suggested revision**: Reject or normalize timestamps (single line, no controls) or emit `TITLE` as one-line JSON via `jq`.

### FINDING_20: `CATEGORY_STATS_PARTIAL` incompletely gates OOS-related cumulative counters
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Partial category-stats inputs can skip some OOS clean/blank deltas while other OOS-related counters still move, yielding YAML that reads fully cumulative despite partial inputs.
- **Suggested revision**: Gate all OOS cumulative fields on `partial_data` or emit separate complete vs partial totals with clear operator instructions.

### FINDING_21: `audit-close-priors` can supersede without closing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Comment success paired with close failure (concurrency/transient `gh` errors) can strand multiple open audit-report issues marked superseded, breaking single-open canonicality.
- **Suggested revision**: Surface hard failure to the orchestrator; document retry; consider close-first/stronger atomicity; optionally exit non-zero on `CLOSE_FAILED`.

### FINDING_22: empty `RUN_ID` combined with SKILL path templates can scan the wrong tree
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Mapping can yield empty `run_id` while SKILL still substitutes `<RUN_ID>` into `audit-scan-run` paths, pointing scans at a parent directory and emitting plausible but wrong NDJSON.
- **Suggested revision**: Require non-empty `run_id` before scanning or make `audit-map-runs.sh` exit non-zero on hard failures; document stderr markers as blocking.

### FINDING_23: `audit-resolve-prs.sh` header contradicts real unknown-argv exit behavior
- **Reviewer(s)**: dyn-kv-contract-output.txt
- **Concern**: Header claims exit `0` always while unknown argv exits `1` with stderr only and no stdout KV, diverging from `audit-resolve-prs.md` and misleading automation.
- **Suggested revision**: Update the script header to match the contract (document non-zero exit and absent stdout KV for unknown argv).

### FINDING_24: `audit-pacific-timestamp` header and `.md` omit unknown-argv failure surface
- **Reviewer(s)**: dyn-kv-contract-output.txt
- **Concern**: Header still implies `0` always while extra args exit `1` stderr-only; contract markdown lacks the explicit “no `PACIFIC_TIMESTAMP=` on stdout” warning pattern used elsewhere (e.g. `audit-preflight.md`).
- **Suggested revision**: Fix header exit-code claims and add a short unknown-argv subsection to `audit-pacific-timestamp.md`.

### FINDING_25: `SKILL.md` orchestrator flow diagram under-specifies `audit-resolve-prs.sh` outputs
- **Reviewer(s)**: dyn-kv-contract-output.txt
- **Concern**: The “Revised Orchestrator Flow” line summarizes only a subset of keys while verbal resolution requires parsing the full set including `ERROR`, `PR_COUNT`, and `IMPLICIT_SINCE_LAST_AUDIT`, risking silent partial-success handling.
- **Suggested revision**: Expand the diagram line to the full key set or add a pointer to `audit-resolve-prs.md`’s authoritative list.

### FINDING_26: [OUT_OF_SCOPE] test harness `bash [[ ]]` vs shipped `sh`-style operator scripts
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Tests use Bash idioms not identical to the shipped audit operator script surface; may be acceptable test-only convention unless repo-wide strict `bash 3.2` parity is required.
- **Suggested revision**: Accept as test-only convention or refactor tests if strict portability is required repo-wide.

### FINDING_27: [OUT_OF_SCOPE] case-sensitive “Since Last Audit” operator input
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Strict casing can surprise operators (e.g. `Since Last Audit` vs expected form).
- **Suggested revision**: Document in SKILL or defer normalized casing to a future change.

### FINDING_28: [OUT_OF_SCOPE] `test-audit-runs.md` contradicts current empty-verbal behavior
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Doc still frames empty verbal description as a usage error while tests/SKILL treat empty as implicit since-last-audit.
- **Suggested revision**: Update the contract bullet in a separate doc-only change.

### FINDING_29: [OUT_OF_SCOPE] tests mirror `audit-resolve-prs` classifiers instead of always shelling out
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Duplicated logic is not mechanically coupled to production parsing.
- **Suggested revision**: Prefer invoking real scripts for dispatch edge cases or share one sourced parser module ( overlaps directionally with FINDING_12 but flagged out-of-scope by source).

### FINDING_30: [OUT_OF_SCOPE] KV vs YAML naming split for changelog counters is intentional
- **Reviewer(s)**: dyn-kv-contract-output.txt
- **Concern**: Uppercase KV names vs snake_case YAML keys is a deliberate split; `parse_prior` targets YAML consistently.
- **Suggested revision**: No change required beyond optional clarifying note if maintainers find it confusing.

### FINDING_31: [OUT_OF_SCOPE] `audit-resolve-prs.sh` emit paths include all six documented keys
- **Reviewer(s)**: dyn-kv-contract-output.txt
- **Concern**: `emit_error` / `emit_ok` appear consistent with `audit-resolve-prs.md`’s six-key contract.
- **Suggested revision**: None (informational confirmation).

### FINDING_32: [OUT_OF_SCOPE] `audit-close-priors.sh` matches `audit-close-priors.md` / SKILL narratives
- **Reviewer(s)**: dyn-kv-contract-output.txt
- **Concern**: Per-issue `CLOSE_FAILED`/`REASON` and `ISSUE_LIST_FAILED` shapes align with documented contracts (includes branch commit references in source).
- **Suggested revision**: None (informational confirmation).

### FINDING_33: [OUT_OF_SCOPE] `last N PRs` verbal parsing robustness (`grep -oE`)
- **Reviewer(s)**: dyn-shell-injection-output.txt
- **Concern**: Digit extraction can behave poorly if multiple digit runs/lines appear; primarily robustness, not a demonstrated injection against `jq`.
- **Suggested revision**: Harden parsing if desired; not prioritized as a security finding by source.

### FINDING_34: [OUT_OF_SCOPE] `normalize_repo` not applied to `--repo` exotic URL shapes
- **Reviewer(s)**: dyn-shell-injection-output.txt
- **Concern**: Identity-check accuracy edge cases for non-canonical `github.com` placement vs focusing on `remote.origin.url`.
- **Suggested revision**: Optional hardening separate from dotted-segment `.git` bug (FINDING_5).

### FINDING_35: [OUT_OF_SCOPE] informational closure on scan-run PR-body digit constraints
- **Reviewer(s)**: dyn-shell-injection-output.txt
- **Concern**: Source asserts certain fields/patterns limit injection surface described elsewhere; no additional in-scope security finding beyond listed items.
- **Suggested revision**: None (informational).
```
