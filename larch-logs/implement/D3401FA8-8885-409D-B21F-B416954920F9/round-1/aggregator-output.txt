Here is the normalized structured finding list (merged by shared behavioral risk; sources listed per finding). In-scope items first, then `[OUT_OF_SCOPE]` items (per your rule, those headings keep the tag).

```text
### FINDING_1: Trailing-content scan matches `NO_ISSUES_FOUND` on any line, not first line / slice
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Concern**: Multi-line first-pass files can fail trailing-content when a later line equals the sentinel even if the first line differs; behavior should follow first-line (or documented first-pass slice) semantics.
- **Suggested revision**: Compare only the first line (or documented slice) before counting additional lines; normalize CRLF/trim if the contract requires it (see also FINDING_17).

### FINDING_2: `CHANGELOG_DELTA` / changelog deltas never accumulated from NDJSON
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Scan NDJSON is not wired into changelog counter aggregation, so reported changelog deltas stay at zero and cumulative changelog signals can be misleading.
- **Suggested revision**: Sum the appropriate NDJSON field from scans, or remove the KV until implemented.

### FINDING_3: Run/manifest selection uses first glob-ordered match, not newest run for a PR
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Duplicate or re-run manifests can map scans to an arbitrary older run directory instead of the latest implement run for that PR.
- **Suggested revision**: Select newest by manifest `started_at` (or stable `run_id` ordering) and document the tie-break.

### FINDING_4: Empty `gh`/jq PR resolution still `emit_ok` for last-N / since-ISO style inputs
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Transient `gh` failures or empty results can yield success with an empty PR list, letting mapping/reporting proceed with no audited PRs when that mode should be an error.
- **Suggested revision**: Treat empty `PR_LIST` as ERROR (non-zero) for forms that require a non-empty audit scope (with explicit carve-out only where “since last audit” legitimately allows empty).

### FINDING_5: `self_deploying_gap` always false; SKILL cross-check guidance removed
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Prior explicit LLM/script guardrails for self-deploying gap and related cross-checks are lost; reporting can silently omit a previously surfaced risk class.
- **Suggested revision**: Recompute `self_deploying_gap` in `audit-scan-run.sh` (or equivalent) and/or restore explicit SKILL-owned steps; align emitted contract with docs.

### FINDING_6: Preflight `git pull --ff-only` may advance current branch, not `main`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: After fetching `main`, operators can still audit with a stale local `main` while preflight passes, confusing scope.
- **Suggested revision**: Fast-forward `main` explicitly (or document branch semantics and enforce the intended ref).

### FINDING_7: Missing run-dir uses “setup” style scan/error instead of planned `required-file-presence` contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Downstream parsers expecting a specific scan key/shape for missing run directories may mis-handle failures (including exit semantics).
- **Suggested revision**: Emit the planned NDJSON/scan id and exit behavior, or update `audit-scan-run.md` + plan so one schema is canonical.

### FINDING_8: Pacific timestamp paths can be wrong, mislabeled, or format-nonconforming under fallback / odd `date` output
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-compat-output.txt
- **Concern**: Manual/UTC-derived “Pacific” can be incorrect near DST/month boundaries; primary `%z` + `sed` normalization may miss required `-HH:MM` shape on unusual `date` outputs; operators can get misleading chain-of-history timestamps versus SKILL “Pacific clock” expectations.
- **Suggested revision**: Validate strict final format and fall back to honest UTC (or real Olson-zone conversion), avoiding `Z`-labeled “Pacific”; broaden offset normalization beyond a single brittle `sed` tail match.

### FINDING_9: Dead `PR_REFS` awk pipeline overwritten immediately
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-compat-output.txt
- **Concern**: Duplicate/dead assignment increases maintenance risk and review noise.
- **Suggested revision**: Remove the unused pipeline; keep a single obvious construction.

### FINDING_10: New tests mostly mirror snippets instead of executing real scripts under fixtures
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Regressions in extracted bash modules can pass while production script bodies drift from intended contracts.
- **Suggested revision**: Add PATH-isolated tests invoking real scripts with stubbed `gh`/`git`/`jq` inputs per plan.

### FINDING_11: Aggregating per-PR category-stats into cumulative semantics may drift from historical meaning
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Summing canonical/blank category-stat slices across PRs may not match how cumulative counters were interpreted in prior audit reports.
- **Suggested revision**: Reconcile definitions with historical reports or change aggregation to match an explicit spec.

### FINDING_12: `audit-title.sh` PR normalization deletes newlines and merges PR tokens (`tr -d '[:space:]'`)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-kv-contract-output.txt, dyn-jq-shell-logic-output.txt
- **Concern**: Comma-separated multi-PR lists collapse into one bogus integer token; contiguous detection, counts, and titles break (also affects spaced forms like `10, 20` → digit merge).
- **Suggested revision**: Split on commas then trim per token without deleting record separators; optionally error on invalid tokens; add a parsed-count assertion in tests.

### FINDING_13: `gh pr list` pagination / default limits can truncate since-* PR sets
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Large merged backlogs after a cutoff can silently omit PRs from the audit scope.
- **Suggested revision**: Paginate until exhaustion or set an explicit high limit with a safety guard / sanity check.

### FINDING_14: Codex-generalist “waste” check uses whole-file equality to `NO_ISSUES_FOUND` (newline prevents match)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Typical files ending with newline skip the intended waste detection.
- **Suggested revision**: Compare first line only or strip trailing newline before equality, consistent with scan intent.

### FINDING_15: Unknown CLI flags are silently ignored across new audit-runs scripts
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt
- **Concern**: Typos silently select defaults, weakening operator safety.
- **Suggested revision**: Strict argv parsing with usage error on unknown flags.

### FINDING_16: `test-audit-runs.sh` uses `wc -l` where newline-terminated semantics skew counts
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: `wc -l` counts newline-terminated lines; missing final newline can make a two-line fixture read as one line, flipping pass/fail expectations.
- **Suggested revision**: Use `NR`-based counting, ensure trailing newline in fixtures, or align assertions with real file semantics.

### FINDING_17: Trailing-content / first-pass matching brittle to CRLF and trailing whitespace
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Exact sentinel equality can misclassify benign-looking files near Windows CRLF or trailing spaces.
- **Suggested revision**: Strip CR and trim the compared first line before classification.

### FINDING_18: Unvalidated `LAST_PR` from prior YAML passed into `gh` under fragile quoting
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Crafted `last:` values can break shell quoting boundaries around `gh` invocation.
- **Suggested revision**: Restrict to digits-only IDs or use `gh api` with validated numeric parameters.

### FINDING_19: User/API timestamps spliced raw into `gh --jq` filter strings
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Malicious or odd since-ISO text can corrupt jq filters and change PR selection behavior.
- **Suggested revision**: Pass values via `jq --arg` / separate jq passes; never embed unescaped external strings into `--jq`.

### FINDING_20: NDJSON / JSON embedding built with string concatenation (`jstr` / setup records)
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Quotes, control characters, or odd paths can yield invalid or misleading JSON for downstream tooling.
- **Suggested revision**: Build JSON with `jq -n` + typed `--arg` fields; validate numeric PR fields.

### FINDING_21: `--log-root` accepted as bare prefix without repo-root containment checks
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Callers can aim mapping at sensitive directories under cwd.
- **Suggested revision**: Resolve under enforced repo root; reject `..` / traversal segments.

### FINDING_22: Required-file TSV relative paths joined to `RUN_DIR` without `..`/abs-path rejection
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Malicious TSV rows could probe outside the intended run log tree.
- **Suggested revision**: Reject `..` and absolute paths before filesystem tests.

### FINDING_23: `pr_number` lookup via substring matching can associate wrong PR (e.g., 2476 vs 24760)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Grepping manifest text for a bare number can bind the wrong run.
- **Suggested revision**: Use `jq` or delimiter-safe regex ensuring the PR token boundary.

### FINDING_24: `audit-close-priors` treats `gh list` failure like “no open issues”
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Auth/network failures can exit success while leaving issues open, masking operational failure.
- **Suggested revision**: Detect `gh` failure; non-zero exit and/or explicit error KV on list failures.

### FINDING_25: Cache-freshness / version-gap scan always passes (stale plugin runs not surfaced)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Manifest `larch_version` vs `--current-version` gap never fails high-severity freshness intent.
- **Suggested revision**: Compare versions and emit fail/warn when behind per contract.

### FINDING_26: Preflight “recent audit” guard can break due to capturing both `jq` stdout and `echo`
- **Reviewer(s)**: dyn-bash-compat-output.txt
- **Concern**: `RECENT` may become multi-line (`true` from jq plus `echo true`), so `[ "$RECENT" = "true" ]` never matches and the overlap guard silently stays open.
- **Suggested revision**: Redirect jq stdout to `/dev/null` and emit a single-line sentinel from exit status, or use an `if …; then RECENT=true; else … fi` pattern.

### FINDING_27: [OUT_OF_SCOPE] `audit-close-priors.md` contract vs broader automated-testing narrative
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Doc claims no unit tests while other materials push harness expansion—documentation-only mismatch.
- **Suggested revision**: Reconcile contract text with intended offline stub strategy (or explicit manual-only waiver).

### FINDING_28: [OUT_OF_SCOPE] `SKILL.md` vs `audit-title.md` / `audit-title.sh` disagree on non-contiguous title rules
- **Reviewer(s)**: dyn-bash-compat-output.txt
- **Concern**: Orchestrator-facing SKILL prose diverges from script contract (≤4 vs explicit list for all gaps).
- **Suggested revision**: Align SKILL + companion `.md` + script behavior under one documented rule.

### FINDING_29: [OUT_OF_SCOPE] Bash 3.2 portability spot-check (audit-runs scripts)
- **Reviewer(s)**: dyn-bash-compat-output.txt
- **Concern**: Reviewer reports no disallowed Bash 4+ features in `.claude/skills/audit-runs/scripts/*.sh` per `BASH_AUTHORING.md` guidance (informational).
- **Suggested revision**: Keep future edits within the same portability constraints.

### FINDING_30: [OUT_OF_SCOPE] Branch/commit context note (read-only)
- **Reviewer(s)**: dyn-bash-compat-output.txt
- **Concern**: Review anchored to branch commit `620377c2` / PR #2495 extraction work (metadata only).
- **Suggested revision**: None (tracking/context for readers).

### FINDING_31: `audit-compute-counters.md` wire shape vs emitted `KEY=value` lines
- **Reviewer(s)**: dyn-kv-contract-output.txt
- **Concern**: Doc shows multiple pairs per physical line while the script prints one assignment per line—consumer/parser drift risk.
- **Suggested revision**: Pick one canonical wire format and align `.md`, SKILL, and script.

### FINDING_32: `SKILL.md` snippet uses `PACIFIC_OUT` then passes undefined `PACIFIC_TIMESTAMP` to `audit-title.sh`
- **Reviewer(s)**: dyn-kv-contract-output.txt
- **Concern**: Documented orchestration is not self-consistent for KV handoff.
- **Suggested revision**: Show explicit extraction from `PACIFIC_OUT` or use one variable end-to-end.

### FINDING_33: `SKILL.md` “Revised Orchestrator Flow” references `counters.env` but counters come from `COUNTERS_OUT`
- **Reviewer(s)**: dyn-kv-contract-output.txt
- **Concern**: Flow diagram names an artifact that is not defined/produced alongside the counter script stdout capture.
- **Suggested revision**: Drop `counters.env` or define it as a file write of `COUNTERS_OUT` when needed.

### FINDING_34: `audit-compute-counters.sh` uses `jq ... | head -1` per scan, dropping duplicate NDJSON lines
- **Reviewer(s)**: dyn-jq-shell-logic-output.txt
- **Concern**: Multiple matching objects for the same scan would be undercounted.
- **Suggested revision**: Aggregate in `jq` (`jq -s` + `add`) or sum all matches without `head -1`.

### FINDING_35: `audit-scan-run.sh` pipelines use `wc -l` on jq streams without guaranteed final newline
- **Reviewer(s)**: dyn-jq-shell-logic-output.txt
- **Concern**: Last line lacking newline can make `wc -l` undercount by one, skewing category-related counters.
- **Suggested revision**: Prefer `jq -s 'map(select(...)) | length'`, append newline before `wc -l`, or otherwise count records robustly.

### FINDING_36: Canonical-category `jq test` applied before null-safe narrowing
- **Reviewer(s)**: dyn-jq-shell-logic-output.txt
- **Concern**: `test` on JSON `null` can error; stderr suppression + pipeline behavior can distort counts depending on `pipefail`.
- **Suggested revision**: Narrow to string categories first, or use null-safe selectors before `test`.

### FINDING_37: `select(.category != "Warnings")` counts null/absent category as non-Warnings
- **Reviewer(s)**: dyn-jq-shell-logic-output.txt
- **Concern**: Unintended pass/fail flips vs “real non-Warnings entries” intent.
- **Suggested revision**: Count only rows with string categories not equal to `Warnings`.

### FINDING_38: [OUT_OF_SCOPE] Spot checks: `emit_error`/`emit_ok` printf format strings; parent-issue grep format; empty-string category semantics; `parse_prior` duplicate-key ambiguity
- **Reviewer(s)**: dyn-kv-contract-output.txt, dyn-jq-shell-logic-output.txt
- **Concern**: Reviewers flag these as likely acceptable / low likelihood / intentional behavior as written (informational cross-checks, not actionable defects).
- **Suggested revision**: None unless product intent changes; optionally document edge-case interpretations explicitly.
```
