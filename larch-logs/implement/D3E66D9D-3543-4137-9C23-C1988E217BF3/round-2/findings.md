### FINDING_1: **Important** `correctness` `scripts/dispatch-code-voters.sh:111` `scripts/test-dispatch-code-voters.sh:354`  
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` `scripts/dispatch-code-voters.sh:111` `scripts/test-dispatch-code-voters.sh:354`      The suppression guard checks only `basename "$REVIEW_TMPDIR"`, but the harness creates one parent tmpdir named `test-dispatch-code-voters.XXXXXX` and then passes child review dirs like `$TMP/env-isolation-review`. In that concrete case, `review_basename=env-isolation-review`, so `should_suppress_parse_rate_issue_append` returns false and line 170 still calls `append-tool-failure.sh`, writing to the explicit `LARCH_EXECUTION_ISSUES_LOG` that regression 1 expects to remain empty. Fix the predicate to recognize harness ancestry from `voter_path` or `REVIEW_TMPDIR` path segments, for example matching `*/test-dispatch-code-voters.*/*` and the sibling harness patterns, while still requiring the voter output to be under the review tmpdir.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] risk-integration: scripts/test-collect-agent-results.sh:11-13
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Sibling harness not modified in branch; already isolates execution-issues env around TMPROOT. Feature text mentioned sibling harnesses; no new gap shown here. None required for this branch review.
- **Suggested revision**: Address the concern above.

### FINDING_3: architecture: scripts/dispatch-code-voters.sh:108-120
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Basename patterns test-collect-* / test-check-* / test-tally-* can suppress production parse-rate issue appends if --review-tmpdir leaf matches. Legitimate tmpdir naming collision drops Warnings from central execution-issues. Narrow patterns or add explicit harness-only sentinel; document tradeoff.
- **Suggested revision**: Address the concern above.

### FINDING_4: architecture: scripts/test-dispatch-code-voters.sh:27-32
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Feature asked for per-case subshell env isolation; implementation uses one global unset. Minor mismatch with written requirement wording only if compliance text matters. Use subshells per test or align requirement doc to global unset.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: .github/workflows/release-tag.yaml (new env block)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] release-tag workflow adds FORCE_JAVASCRIPT_ACTIONS_TO_NODE24 without rationale comment present in ci.yaml. Readers lack the deprecation context available in ci.yaml. Mirror the short explanatory comment from .github/workflows/ci.yaml.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: scripts/dispatch-code-voters.sh:108-120
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Feature (B) asked voter_path pattern match before append; implementation uses REVIEW_TMPDIR basename patterns. Nested review dirs under a harness-shaped /tmp root never suppress parent-log append even when voter_path paths include test-dispatch-code-voters; behavior diverges from written requirement. Align spec and tests with basename(REVIEW_TMPDIR) contract or implement voter_path (or path-prefix) matching from the requirement.
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: scripts/test-dispatch-code-voters.md:14-15
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Coverage bullets say path guard fires for voter_path under test-dispatch-code-voters tmpdir. Doc disagrees with dispatch-code-voters.md:44 (REVIEW_TMPDIR basename rule). Reword bullets to basename(REVIEW_TMPDIR) and in-REVIEW_TMPDIR voter_path prefix.
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: scripts/test-dispatch-code-voters.sh:249-250 scripts/test-dispatch-code-voters.sh:311
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Comments attribute retry-fail behavior to path guard suppressing append-tool-failure. Basename retry-fail does not match guard; without LARCH the issues log is REVIEW_TMPDIR/execution-issues.md per dispatch-code-voters.sh:166-169; comments mislead maintainers. Rewrite comments to describe unset parent env and default _issues_log resolution.
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: scripts/test-dispatch-code-voters.sh:27-32
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Plan asked env-isolated subshells per test case; diff uses one-time unset at harness start. Minor plan/spec drift; subshells would isolate per-test exports if any appear later. Match plan with subshell wrappers or document intentional global unset in plan.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: scripts/dispatch-code-voters.sh:108-120
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Implementation keys suppression off review tmpdir basename; feature text referenced voter_path pattern matching. Parent LARCH_EXECUTION_ISSUES_LOG set, review dir basename review under test-dispatch-code-voters.* parent; voter_path under harness tree; append still writes to parent log. Match voter_path or full REVIEW_TMPDIR path to harness prefixes per spec or update spec to basename rule.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: scripts/dispatch-code-voters.sh:108-120 scripts/test-dispatch-code-voters.sh:344-381
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Path guard uses basename(REVIEW_TMPDIR) but harness uses nested review dirs so suppression never runs; Regression 1/2 expect no append to LARCH_EXECUTION_ISSUES_LOG. Running scripts/test-dispatch-code-voters.sh: append-tool-failure writes to the explicit issues files; [[ -s env_isolation_parent]] / path_guard_issues triggers FAIL. Use --review-tmpdir "$TMP" for guard tests or extend guard (e.g. prefix on voter_path or REVIEW_TMPDIR path).
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: scripts/test-dispatch-code-voters.md:14-15
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Coverage bullets claim path guard fires for paths under test-dispatch tmpdir with LARCH set; implementation uses basename(REVIEW_TMPDIR) only. Doc/contract mismatch with code and broken regressions. Sync bullets with dispatch-code-voters.md after fixing tests.
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: scripts/test-dispatch-code-voters.sh:249-250 scripts/test-dispatch-code-voters.sh:311-312
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Comments attribute retry-fail behavior to path guard; guard does not apply to nested tmpdir basenames. Maintainer drops global unset expecting guard to stop parent writes; nested tmpdir still appends to parent log when LARCH_EXECUTION_ISSUES_LOG is set. Reword: credit unset plus default _issues_log under REVIEW_TMPDIR; describe path guard only when basename matches.
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: scripts/test-dispatch-code-voters.sh:344-381
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Regression 1-2 use --review-tmpdir basenames env-isolation-review and path-guard-review; should_suppress_parse_rate_issue_append only matches basename(REVIEW_TMPDIR) against test-dispatch-code-voters.*|test-collect-*|test-check-*|test-tally-*. With LARCH_EXECUTION_ISSUES_LOG set append-tool-failure still runs; env_isolation_parent and path_guard_issues become non-empty; grep -s assertions fail on scripts/test-dispatch-code-voters.sh. Use --review-tmpdir whose basename matches the guard (e.g. $TMP) or extend guard to voter_path/ancestor paths per spec.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: scripts/dispatch-code-voters.sh:108-118
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Spec (B) says voter_path pattern; impl uses REVIEW_TMPDIR basename Nested harness layout like .../test-dispatch-code-voters.XXX/retry-fail never suppresses parent log even though voter_path contains test-dispatch-code-voters; accidental production basename test-collect-* could suppress wrongly Match voter_path (or full path prefix) as in spec or document and test basename-only contract explicitly
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: scripts/dispatch-code-voters.sh:164-180
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] larch_err ordering moved before append-tool-failure vs previous branch. Minor change in stderr vs issues-log ordering for operators. Accept or restore previous order if contract matters.
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: scripts/test-dispatch-code-voters.sh (Part A vs diff)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Feature asked per-case subshell isolation and sibling harness updates; only global unset in one harness appears. Coverage story does not match stated spec. Follow spec or document deviation in test-dispatch-code-voters.md.
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: scripts/test-dispatch-code-voters.sh:247-250 scripts/test-dispatch-code-voters.sh:309-312
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Comments attribute retry-fail behavior to path guard suppression. Readers may remove unset or mis-fix guard while leak returns or tests rot. Reword to credit unset + default _issues_log under REVIEW_TMPDIR.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: scripts/test-dispatch-code-voters.sh:249-250,311
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Comments attribute no-append behavior to path guard for retry-fail fixtures; guard does not match retry-fail basename; append goes to review-local execution-issues.md when parent log vars unset. Maintainer misdiagnoses parse-rate append behavior or regresses harness unset. Rewrite comments to describe unset-driven log resolution and when basename guard applies.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: scripts/test-dispatch-code-voters.sh:27-32
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Plan asked subshell env isolation; only global unset at startup Lower isolation if later code exports parent vars; minor plan fidelity Use subshells per invocation or document why global unset is sufficient
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: scripts/test-dispatch-code-voters.sh:389-403
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Regression3 does not assert Claude parse-rate tool label string in issues log. Change removes only dispatch-code-voters.sh claude substring check for launcher label; claude label regression could slip. Grep for launch-claude-review.sh (voter parse-rate check) in prod_issues like codex branch.
- **Suggested revision**: Address the concern above.

### FINDING_22: risk-integration: scripts/test-dispatch-code-voters.sh:398-403
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Production-shape Claude assertion only greps site string Missing tool-label assertion allows bad append-tool-failure --tool field for Claude parse-rate warnings Add grep for launch-claude-review.sh (voter parse-rate check) like removed retry_fail checks
- **Suggested revision**: Address the concern above.

### FINDING_23: security: scripts/dispatch-code-voters.sh:108-119
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Basename allowlist can match non-harness review dirs if operators reuse harness-style names. Parse-rate execution-issues append silently skipped for those runs. Tighten detection or document reserved basename patterns.
- **Suggested revision**: Address the concern above.

