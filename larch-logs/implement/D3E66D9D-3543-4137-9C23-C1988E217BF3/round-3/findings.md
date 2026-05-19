### FINDING_1: [OUT_OF_SCOPE] architecture: repo-wide (other test-*.sh harnesses)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] No other harness calls dispatch-code-voters.sh. N/A for this PR’s sibling-harness requirement. N/A
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] risk-integration: Makefile:511-516
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Parse-retry and regression tail runs for both happy and edge harness shards (duplicate work) Extra CI time; not caused by the new regression block alone Refactor sections if you want to dedupe (future change)
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] risk-integration: repo-wide harness inventory
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Implementation plan mentioned sibling harnesses unsetting env; no other harness calls dispatch-code-voters today None unless new harnesses invoke dispatch without copying this unset pattern Document or extend unset if a new caller appears
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] risk-integration: scripts/dispatch-code-voters.sh (append-tool-failure invocations)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] append-tool-failure errors swallowed via || true. Silent failure to record warnings pre-exists. Leave unless changing error policy repo-wide.
- **Suggested revision**: Address the concern above.

### FINDING_5: architecture: scripts/dispatch-code-voters.sh:296-335
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Voter1 failure append path has no harness suppression while parse-rate path does. Caller sets LARCH_EXECUTION_ISSUES_LOG to parent implement log and uses harness-shaped REVIEW_TMPDIR; voter1 empty/failure still appends to parent; parse-rate does not. Share suppression helper with voter1 failure branch or document intentional asymmetry.
- **Suggested revision**: Address the concern above.

### FINDING_6: architecture: scripts/test-dispatch-code-voters.sh:26-32
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Feature description Part (A) asks for per-case env-isolated subshells; harness uses one global unset at startup (matches written implementation plan, not the feature’s subshell wording). A future test exports SESSION_ENV_PATH or IMPLEMENT_TMPDIR into the harness shell; later cases inherit it unless they override. Add per-section subshells or repeat unset before each independent scenario block.
- **Suggested revision**: Address the concern above.

### FINDING_7: architecture: scripts/test-dispatch-code-voters.sh:315-320
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Startup unset replaces per-case subshell env isolation described in the plan. Future edits that export parent env vars after harness start could reintroduce leakage without subshell isolation at each invocation. Use per-invocation subshells or align documentation with the chosen isolation model.
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: scripts/test-dispatch-code-voters.sh:17-20 (diff context)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Plan Part A asked for env-isolated subshells per test; harness uses one-time unset at startup instead. Reviewers comparing the branch to the written implementation_plan see a structural mismatch though behavior likely still fixes the leak. Update the plan wording after merge or add subshells only around blocks that export parent env vars if strict plan parity matters.
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: scripts/test-dispatch-code-voters.sh:249-252 scripts/test-dispatch-code-voters.sh:311-314
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Comments attribute absence of parent log writes to issues-log fallback under REVIEW_TMPDIR; suppression actually skips append-tool-failure for harness parse-rate Maintainer expects review-local execution-issues.md to receive structured parse-rate warnings during harness runs; it does not Reword comments to mention should_suppress_parse_rate_issue_append plus env unset
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: scripts/test-dispatch-code-voters.sh:249-312
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Comments claim review-local fallback prevents parent writes. Guard suppresses all appends for harness trees; comment misleads maintainers. Rewrite comments to state suppression and unset env behavior accurately.
- **Suggested revision**: Address the concern above.

### FINDING_11: code-quality: scripts/test-dispatch-code-voters.sh:27-31
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Global unset vs spec subshell-per-test. Future test exports parent env: startup unset alone may not isolate. Use env -u per invocation or align spec to harness-wide unset.
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: scripts/dispatch-code-voters.md:44 and scripts/dispatch-code-voters.sh:171-187
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Doc says parse-rate guard suppresses append-tool-failure for the parent-run log only, but the code skips append-tool-failure for every resolved _issues_log when suppressed, including review-local $REVIEW_TMPDIR/execution-issues.md. Harness-shaped REVIEW_TMPDIR with no parent env vars: parse-rate NOT_SUBSTANTIVE still produces diag and stderr but never appends to review-local execution-issues.md; doc and feature text imply only parent leakage is suppressed. Narrow suppression to parent-resolved logs only, or update docs and issue spec to say all parse-rate append-tool-failure targets are suppressed in harness paths.
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: scripts/dispatch-code-voters.sh:108-127
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Harness path globs suppress parse-rate append-tool-failure for any REVIEW_TMPDIR under a segment matching test-collect-/test-check-/test-tally-/test-dispatch-code-voters.* Non-harness review with --review-tmpdir under e.g. .../test-collect-summary/review and real NOT_SUBSTANTIVE parse-rate: durable execution-issues Warnings entry is skipped while stderr still warns Narrow detection (explicit harness env, tighter path contract) or document forbidden production directory names
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: scripts/dispatch-code-voters.sh:108-127
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] is_harness_review_path matches test-collect- test-check- test-tally- segments anywhere in the tested path Future nested voter paths under REVIEW_TMPDIR could suppress parse-rate issues append in non-test reviews Narrow patterns to tmp harness roots or basename-only rules
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: scripts/dispatch-code-voters.sh:158-177
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Harness path globs (test-collect-/test-check-/test-tally-) can match legitimate REVIEW_TMPDIR layouts. Production review tmpdir under e.g. .../test-collect-foo/review suppresses parse-rate append-tool-failure writes; stderr warning still fires but execution-issues.md misses the warning. Tighten guard to explicit harness tmp prefix or env sentinel; avoid broad path-component globs.
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: scripts/dispatch-code-voters.sh:171-177
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] larch_err now precedes issues-log resolution and append-tool-failure. Any tooling that assumed append-tool-failure ran before the stderr line may see reversed ordering. Restore prior ordering for non-suppressed runs if log scrapers depend on it; otherwise document the new order.
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: scripts/test-dispatch-code-voters.sh:249-312 (diff context)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Comments say omitting LARCH_EXECUTION_ISSUES_LOG makes review-local execution-issues the sink and implies that avoids parent leakage. Harness paths suppress all append-tool-failure calls for parse-rate; no review-local issues append occurs, which the comment does not state. Reword to say the harness guard skips parse-rate append-tool-failure entirely for these tmpdirs, not that logs fall back under REVIEW_TMPDIR.
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: scripts/test-dispatch-code-voters.sh:27-32
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Feature text asked per-test subshell env isolation; code uses one global unset (matches written plan) Literal requirement/spec mismatch without observed leak in this harness Align spec to implementation or add subshell wrappers
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: .github/workflows/ci.yaml:26-34 and .github/workflows/release-tag.yaml:71-74
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Workflow-level FORCE_JAVASCRIPT_ACTIONS_TO_NODE24. Single incompatible action breaks every job in the workflow. Accept or narrow env to specific jobs if supported.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: scripts/dispatch-code-voters.sh:108-127
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Harness-shaped path segments suppress append-tool-failure for parse-rate warnings when voter output lives under REVIEW_TMPDIR. A legitimate review using a tmpdir whose path contains a segment like test-collect-* or test-check-* would match is_harness_review_path and skip writing the Warning to execution-issues.md while stderr still warns, weakening the persistent audit trail for that run. Tighten detection with realpath plus an explicit harness-only env flag or stricter prefix allowlist so production paths cannot collide with harness templates.
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: scripts/dispatch-code-voters.sh:108-127
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Parse-rate issue suppression uses broad path substring globs on REVIEW_TMPDIR or voter_path. A production review tree stored under a path containing e.g. test-check-foo would skip execution-issues warnings for NOT_SUBSTANTIVE parse-rate while still emitting stderr. Narrow the guard (explicit env flag from harnesses, or anchor to known tmp roots) if collision risk matters.
- **Suggested revision**: Address the concern above.

### FINDING_22: risk-integration: scripts/test-dispatch-code-voters.sh:247-325
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Retry-fail fixtures no longer assert append-tool-failure / issues-log content. append-tool-failure broken or skipped: retry-fail tests can still pass via diag-only checks. Add stub invocation counter or keep one explicit issues-log assertion on a non-suppressed path.
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: scripts/test-dispatch-code-voters.sh:247-325
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] retry-fail fixtures dropped execution-issues assertions for parse-rate NOT_SUBSTANTIVE; only diag and KV are checked Regression in append-tool-failure wiring for the unset-LARCH harness-tmp branch might only surface in prod-shape regression3 with weaker localization Add stub append argv logging or one explicit non-harness REVIEW_TMPDIR case asserting issues-log lines for retry-fail
- **Suggested revision**: Address the concern above.

### FINDING_24: risk-integration: scripts/test-dispatch-code-voters.sh:249-312
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Comments claim LARCH unset falls back to review-local execution-issues and implies parent safety via fallback Readers may expect review-local execution-issues.md to be populated under harness tmp after parse-rate fail; append is suppressed so file often stays empty Reword to state suppress skips append-tool-failure for harness paths while diag and stderr remain
- **Suggested revision**: Address the concern above.

### FINDING_25: risk-integration: scripts/test-dispatch-code-voters.sh:315-319
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Plan asked for per-test subshell env isolation; implementation uses global unset at harness start Minor plan fidelity mismatch though child env assignments do not leak into parent Accept as doc-only or add explicit subshells if strict alignment matters
- **Suggested revision**: Address the concern above.

