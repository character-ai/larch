# Larch Makefile
# Thin wrapper around pre-commit. Linter definitions live in .pre-commit-config.yaml.

.PHONY: py-lint py-test lint lint-only test-harnesses test-harnesses-1 test-harnesses-2 test-harnesses-3 test-harnesses-4 test-harnesses-5 test-harnesses-6 test-harnesses-7 test-harnesses-8 test-harnesses-9 test-harnesses-10 test-harnesses-11 test-harnesses-12 test-harnesses-13 test-harnesses-14 test-harnesses-15 test-harnesses-16 test-harnesses-17 test-harnesses-18 test-harnesses-19 test-harnesses-20 shellcheck markdownlint jsonlint actionlint agent-lint agnix gitleaks trufflehog setup test-pipe-sigpipe-safety test-redact test-scrub-log-secrets test-redact-tmpdir-paths test-append-tool-failure test-validate-research-output test-validate-citations test-validate-citations-budget test-collect-agent-bash32 test-render-final-summary-bash32 test-collect-agent-retry test-collect-agent-results test-parse-input test-allocate-candidates test-add-blocked-by test-list-issues test-parse-prose-blockers test-anti-improvised-wakeup test-audit-runs test-sentinel-write test-sessionstart test-keepalive-sentinel test-resolve-implement-tmpdir test-check-clean-tree test-check-main-sync test-plan-block test-clarify-comment test-clarify-state test-check-stale-plugin test-preflight-args test-cleanup test-cleanup-tmpdir test-cache-root-validation test-cache-key-discipline test-finalize-sanity-check test-session-entry-gate test-session-setup-presence-defaults test-session-setup-repo-fallback test-session-env-roundtrip test-audit-edit-write test-block-submodule test-lib-implement-round-cap test-deny-edit-write test-render-lane-status test-verify-skill-called test-relevant-checks test-relevant-checks-byte-budget test-relevant-checks-validation test-relevant-checks-helper-failure test-hook-anti-read-poll test-review-relevant-checks-helper test-lint-fix-loop test-classify-bump test-ci-wait-exit-trap test-ci-rerun-failed test-ci-status test-merge-pr test-git-push test-lint-skill-invocations test-lint-literal-counts test-lint-no-raw-stderr-after-quiet-init test-lint-readability-preamble test-lint-bare-grep-probe test-mermaid-fragments test-anti-halt test-orchestrator-scope-sync test-alias-target-resolution test-alias-structure test-design-structure test-decompose-panel-dispatch test-decompose-aggregator test-decompose-file-issues test-design-driver test-design-publish test-design-postplan-emit test-upgrade-larch-retention test-invoke-plan-validator test-file-design-oos test-emit-plan test-gate-b-dedup-plan test-trailer-helpers test-emit-design-plan-preview test-check-plan-size test-parse-plan-commands test-validate-plan-commands test-step3-review-cap test-run-step3-review test-lib-phase-driver test-plan-review-loop test-tally-plan-review test-finalize-plan test-write-run-params test-step0b-router-flag-recovery test-write-design-current-env test-plan-review-prompt test-brainstorm-prompts test-scout-plan-archetypes-wrapper test-dispatch-plan-review-panel test-render-final-summary test-implement-rebase-macro test-ship-pr-rebase test-rebase-checkpoint-probe test-phantom-probe-with-warn test-implement-step2-routing test-rebase-push-keep-on-conflict test-rebase-push-force-lease test-rebase-push-fork-mode test-rebase-push-no-push-fetch-retry test-implement-structure test-implement-step8-exit3-first-fixer test-oos-disposition-gate test-plan-adequacy-audit test-implement-positional-issue test-implement-timing-rehydration test-implement-cleanup-roundtrip test-implement-anti-polling-rule test-implement-relevant-checks-anti-halt test-implement-anti-halt test-implement-review-token-propagation test-step2-dispatch test-cursor-implementer test-codex-implementer test-gh-run-logs test-refresh-run-logs test-ci-wait test-launch-cursor-ci test-launch-claude-ci test-launch-codex-ci test-run-negotiation-round test-launch-claude-subprocess test-launch-claude-review test-dispatch-with-waterfall test-revise-plan-with-waterfall test-run-external-agent test-run-external-agent-args test-quick-mode-docs-sync test-implement-bootstrap test-implement-bootstrap-invoke test-implement-finalize test-flush-execution-issues test-post-tracking-issue test-commit-implementation test-commit-review-fixes test-generate-code-flow-diagram test-refresh-execution-issues test-write-rejected-findings test-slack-issue-announce test-write-final-report test-step-18b-final-report test-render-run-summary test-token-cost test-render-cost-line test-implement-cleanup-script test-restore-finalize-state test-harness-shards-coverage test-harness-timer test-references-headers test-render-reviewer-prompt test-render-debate-retry-prompt test-render-specialist-prompt test-research-structure test-review-structure test-gather-context test-gather-branch-context test-review-core test-dispatch-panel-core test-dispatch-panel-reuse test-dispatch-panel-limits test-scout-dynamic-archetypes test-dispatch-plan-voters test-render-voter-prompt test-collect-findings test-aggregate-findings test-tally-code-votes test-check-reviewer-failure-threshold test-lib-vote-tally test-dispatch-code-voters-happy test-dispatch-code-voters-edge-and-r3-claude test-dispatch-code-voters-regressions-r1-r2 test-dispatch-code-voters-regressions-r3-codex test-emit-tally test-log-phase test-review-and-fix test-review-and-fix-dispatch test-review-and-fix-convergence test-review-and-fix-parsers test-scrub-submodule-paths test-ballot-parse test-tally-vote test-scoreboard test-oos-serialize test-run-research-planner test-render-findings-batch test-research-banner test-synthesis-subagent test-research-angle-prompts test-subskill-anchors test-tracking-issue-write test-larch-log test-capture-session-transcript test-local-cleanup test-larch-logs-manifest test-larch-logs-batches test-compose-plan-goals-test test-write-tally test-compose-collector-failure-log test-tracking-issue-summary test-false-positive-keywords test-tracking-issue-read-sentinel test-compose-review-findings test-token-tally test-token-ledger test-token-report test-timing-ledger test-step-telemetry-mark test-timing-report test-parse-codex-usage test-token-vendor-scrapers test-token-claude-source test-check-review-changes test-check-mid-run-dirty-tree test-check-phantom-dirty test-check-reviewers test-degraded-tools-gate test-check-generators test-check-contains-pins test-check-topology-rule-paths test-generate-topology-docs test-external-tool-registry test-agent-model-args test-effort-prose test-launch-review test-lib-external-launcher-common test-lib-cursor-auth test-lib-design-tmpdir test-lib-quiet test-github-remote-repo test-implement-fork-env test-get-issue-context test-get-issue-state test-create-pr test-resolve-repo test-gh-pr-body-update smoke-dialectic eval-research test-eval-set-structure test-eval-research-baseline-flag test-body-file-title test-intra-batch-deps test-blocked-by-issue test-oos-file-conflict-deps test-oos-issue-cap test-materialize-manifest-oos test-wait-for-reviewers test-set-up-forked-open-source-repo test-analyze test-compose-pr-summary test-upsert-diagrams-comment test-run-step5-review test-run-step1-plan-log test-run-step2-dispatch test-prompt-template-invariants test-lib-submodule-prohibition test-verify-run-log-completeness test-design-log-publish test-fetch-combinable-issues-filter test-legacy-title-prefix-literals-scope test-implement-admission test-pause-skill
.PHONY: test-lib-vote-tally test-findings-classification test-review-findings-classification test-review-and-fix-step5-starting-round test-lib-failed-agent-stderr-tail test-lib-net
.PHONY: test-prompt-template-invariants test-render-voter-prompt test-lib-submodule-prohibition
.PHONY: test-larch-log-write-round test-lib-title-eligibility test-lib-title-markers test-read-design-classification
.PHONY: test-scout-dynamic-archetypes
.PHONY: test-extract-plan-scope-paths test-git-commit-only
.PHONY: test-design-reentry-guard
.PHONY: test-promote-release test-release-finish test-release-prepare test-release-set-version
.PHONY: test-snapshot-plan-round test-dispatch-plan-assessors test-render-assessor-prompt test-tally-plan-assessor test-assess-plan-round test-design-plan-quality-assessor
.PHONY: test-token-report-dedup test-token-cost-per-bucket test-render-cost-line-realism test-render-cost-line-callsites test-render-run-summary-callsites test-render-run-summary-format test-token-report-summary-format test-run-analysis-quiet
.PHONY: lint-bash32 test-lint-bash32 lint-gh-body-inline test-lint-gh-body-inline lint-mermaid agent-sync test-ci-failed-jobs test-ci-behind-count
.PHONY: test-step-7a
.PHONY: test-stall-recovery-report test-step-18b-final-report
.PHONY: test-design-pause-resume
.PHONY: test-parse-design-argv
.PHONY: lint-readability-preamble test-lint-readability-preamble
.PHONY: lint-renderer-substitution-safety lint-skill-md-flag-signature test-lint-renderer-substitution-safety test-lint-skill-md-flag-signature
.PHONY: test-persist-implement-run-flags
.PHONY: lint-bare-grep-probe test-lint-bare-grep-probe lint-awk-multibyte-regex test-lint-awk-multibyte-regex
.PHONY: test-design-multi-round-integration test-lib-design-round-artifacts test-step3-orchestrator-fence
.PHONY: test-no-grouped-reuse-guard
# CI splits `lint` into `lint-only` (pre-commit) and `test-harnesses`
# (regression harnesses). `lint` remains the local-dev convenience target
# that runs both, defined in terms of the two split targets to prevent drift.
lint: test-harnesses lint-bash32 lint-readability-preamble lint-renderer-substitution-safety lint-skill-md-flag-signature lint-bare-grep-probe lint-awk-multibyte-regex lint-only

py-lint:
	cd python && ruff check . && pylint . && pyright

py-test:
	cd python && pytest

lint-only:
	pre-commit run --all-files

lint-readability-preamble:
	bash scripts/lint-readability-preamble.sh

lint-renderer-substitution-safety:
	bash scripts/lint-renderer-substitution-safety.sh

lint-skill-md-flag-signature:
	bash scripts/lint-skill-md-flag-signature.sh

lint-bare-grep-probe:
	bash scripts/lint-bare-grep-probe.sh

lint-awk-multibyte-regex:
	bash scripts/lint-awk-multibyte-regex.sh

# Balanced regression-harness shards (closes #1294, #1585, #1911, #2080, #2252, #2262, #2291, #2349, #2366, #2386 — rebalance after
# slow harnesses pushed shards 2/3/5 over the 20s target, resharded to 10, then resharded to 11,
# then to 13 after heavy tests pushed shard wall time over the 40s target, then to 16 after
# shards 12/13 exceeded 50s with test-dispatch-code-voters and test-dispatch-panel, then to 14
# after splitting test-ship-pr/-dispatch-code-voters/-dispatch-panel into sections and stubbing
# ship-pr.sh sleep brought the ceiling under 22s, then to 18 after isolating the four
# retry-only dispatch-code-voters harness sections into dedicated shard rows, and now to 20
# after gating the three previously-ungated Regression 1/2/3 blocks in
# test-dispatch-code-voters.sh into two new sections (regressions-r1-r2, regressions-r3-codex),
# folding Regression 3's claude case into the edge shard as edge-and-r3-claude, and splitting
# test-review-and-fix into dispatch/convergence sections (plus a parsers slice for Step 5 KV parsing) to shrink shard 13). Rebalanced 2026-05-31: fourth-pass LPT dropped test-ship-pr from CI shards;
# that harness was then removed entirely in #3335 as the ship-pr.sh bash path is retired in favor of python/.
# Suite total 1001s; anchors: shard 1 (test-plan-review-loop 61s), shard 2
# (test-launch-review 52s); shards 3-20 target ~49s each. When
# imbalance returns, see docs/linting.md "Refreshing harness shard balance" for the regeneration
# procedure. IMPORTANT: each test-harnesses-N rule below stays on a single
# physical line (no `\` continuations); the drift-detection script
# `scripts/test-harness-shards-coverage.sh` parses these lines literally. New harnesses get
# appended to one shard line.
test-harnesses: test-harnesses-1 test-harnesses-2 test-harnesses-3 test-harnesses-4 test-harnesses-5 test-harnesses-6 test-harnesses-7 test-harnesses-8 test-harnesses-9 test-harnesses-10 test-harnesses-11 test-harnesses-12 test-harnesses-13 test-harnesses-14 test-harnesses-15 test-harnesses-16 test-harnesses-17 test-harnesses-18 test-harnesses-19 test-harnesses-20

test-harnesses-1: test-plan-review-loop

test-harnesses-2: test-launch-review

test-harnesses-3: test-launch-cursor-ci

test-harnesses-4: test-check-reviewers test-implement-admission test-token-ledger test-check-review-changes test-render-debate-retry-prompt test-degraded-tools-gate test-rebase-push-no-push-fetch-retry test-check-stale-plugin test-compose-pr-summary test-ci-status test-lib-implement-round-cap test-implement-anti-halt test-implement-cleanup-roundtrip test-implement-positional-issue

test-harnesses-5: test-harness-shards-coverage test-review-and-fix-dispatch test-gh-pr-body-update test-merge-pr test-plan-review-prompt test-launch-claude-subprocess test-oos-disposition-gate test-session-env-roundtrip test-gate-b-dedup-plan test-lib-quiet test-check-clean-tree test-lint-renderer-substitution-safety test-commit-review-fixes test-refresh-execution-issues test-blocked-by-issue test-implement-step8-exit3-first-fixer

test-harnesses-6: test-run-external-agent test-findings-classification test-stall-recovery-report test-step-18b-final-report test-render-final-summary test-review-findings-classification test-session-setup-presence-defaults test-check-topology-rule-paths test-preflight-args test-decompose-file-issues test-flush-execution-issues test-run-research-planner test-render-reviewer-prompt test-references-headers test-alias-target-resolution test-write-rejected-findings test-extract-plan-scope-paths test-keepalive-sentinel test-token-report-dedup test-body-file-title test-effort-prose

test-harnesses-7: test-step2-dispatch test-aggregate-findings test-refresh-run-logs test-check-contains-pins test-oos-issue-cap test-file-design-oos test-ci-wait test-ci-wait-exit-trap test-plan-block test-redact-tmpdir-paths test-relevant-checks-validation test-snapshot-plan-round test-implement-fork-env test-research-structure test-rebase-push-force-lease test-research-banner test-review-relevant-checks-helper test-step3-orchestrator-fence

test-harnesses-8: test-review-and-fix-convergence test-collect-agent-bash32 test-dispatch-code-voters-edge-and-r3-claude test-design-pause-resume test-audit-runs test-create-pr test-run-step3-review test-finalize-sanity-check test-parse-codex-usage test-token-tally test-sentinel-write test-render-cost-line test-review-structure test-lib-external-launcher-common test-render-run-summary-format test-render-voter-prompt test-intra-batch-deps test-brainstorm-prompts

test-harnesses-9: test-dispatch-panel-core test-larch-logs-manifest test-timing-report test-redact test-scrub-log-secrets test-add-blocked-by test-session-entry-gate test-run-negotiation-round test-lib-vote-tally test-emit-plan test-ci-rerun-failed test-implement-cleanup-script test-oos-serialize test-render-run-summary-callsites

test-harnesses-10: test-design-log-publish test-clarify-comment test-tally-plan-review test-codex-implementer test-token-vendor-scrapers test-validate-plan-commands test-lint-literal-counts test-parse-prose-blockers test-trailer-helpers test-session-setup-repo-fallback test-cache-root-validation test-rebase-push-fork-mode test-post-tracking-issue test-emit-tally test-slack-issue-announce test-tally-vote test-fetch-combinable-issues-filter

test-harnesses-11: test-set-up-forked-open-source-repo test-design-multi-round-integration test-tracking-issue-summary test-scout-dynamic-archetypes test-dispatch-code-voters-regressions-r1-r2 test-token-report test-render-specialist-prompt test-sessionstart test-check-mid-run-dirty-tree test-block-submodule test-launch-claude-ci test-review-and-fix-parsers test-review-and-fix-step5-starting-round test-list-issues test-generate-code-flow-diagram test-relevant-checks-byte-budget test-commit-implementation test-no-grouped-reuse-guard test-cleanup-tmpdir test-legacy-title-prefix-literals-scope

test-harnesses-12: test-dispatch-panel-reuse test-dispatch-panel-limits test-oos-file-conflict-deps test-materialize-manifest-oos test-cursor-implementer test-dispatch-code-voters-retry-codex-fail-and-fallback test-prompt-template-invariants test-launch-claude-review test-larch-log-write-round test-render-run-summary test-write-design-current-env test-scrub-submodule-paths test-cache-key-discipline test-deny-edit-write test-false-positive-keywords test-finalize-plan test-audit-edit-write test-gather-context test-orchestrator-scope-sync test-render-final-summary-bash32
test-harnesses-13: test-launch-codex-ci test-dispatch-code-voters-retry-cursor test-allocate-candidates test-design-structure test-mermaid-fragments test-local-cleanup test-lint-bash32 test-parse-plan-commands test-step0b-router-flag-recovery test-lib-cursor-auth test-implement-rebase-macro test-ship-pr-rebase test-git-commit-only test-lib-submodule-prohibition test-anti-improvised-wakeup

test-harnesses-14: test-dispatch-plan-review-panel test-step-7a test-wait-for-reviewers test-dispatch-code-voters-regressions-r3-codex test-tally-plan-assessor test-lint-awk-multibyte-regex test-append-tool-failure test-lint-bare-grep-probe test-relevant-checks-helper-failure test-lint-skill-md-flag-signature test-lint-no-raw-stderr-after-quiet-init test-lib-net test-lib-design-tmpdir test-token-report-summary-format test-research-angle-prompts test-implement-relevant-checks-anti-halt

test-harnesses-15: test-implement-bootstrap test-implement-bootstrap-invoke test-validate-citations-budget test-lint-fix-loop test-validate-research-output test-render-findings-batch test-generate-topology-docs test-step3-review-cap test-clarify-state test-lint-gh-body-inline test-compose-collector-failure-log test-render-cost-line-realism test-render-cost-line-callsites test-resolve-repo test-run-step2-dispatch test-persist-implement-run-flags test-implement-anti-polling-rule

test-harnesses-16: test-dispatch-code-voters-happy test-timing-ledger test-step-telemetry-mark test-collect-agent-retry test-review-core test-validate-citations test-lint-skill-invocations test-verify-skill-called test-implement-structure test-run-step5-review test-design-driver test-design-publish test-design-postplan-emit test-parse-design-argv test-upgrade-larch-retention test-render-lane-status test-agent-model-args test-git-push test-pause-skill test-lib-phase-driver test-implement-step2-routing test-ballot-parse

test-harnesses-17: test-dispatch-plan-voters test-tally-code-votes test-larch-log test-hook-anti-read-poll test-dispatch-code-voters-retry-claude test-token-claude-source test-dispatch-code-voters-retry-codex-success test-parse-input test-tracking-issue-read-sentinel test-scout-plan-archetypes-wrapper test-write-run-params test-lib-failed-agent-stderr-tail test-ci-failed-jobs test-run-step1-plan-log test-decompose-aggregator test-invoke-plan-validator test-render-assessor-prompt test-plan-adequacy-audit test-lib-design-round-artifacts

test-harnesses-18: test-implement-finalize test-tracking-issue-write test-revise-plan-with-waterfall test-harness-timer test-pipe-sigpipe-safety test-check-plan-size test-assess-plan-round test-design-plan-quality-assessor test-dispatch-plan-assessors test-check-phantom-dirty test-log-phase test-ci-behind-count test-compose-plan-goals-test test-token-cost-per-bucket test-design-reentry-guard test-gh-run-logs test-github-remote-repo test-scoreboard test-synthesis-subagent

test-harnesses-19: test-dispatch-with-waterfall test-verify-run-log-completeness test-cleanup test-write-final-report test-upsert-diagrams-comment test-capture-session-transcript test-analyze test-lint-readability-preamble test-larch-logs-batches test-restore-finalize-state test-check-reviewer-failure-threshold test-rebase-push-keep-on-conflict test-get-issue-state test-quick-mode-docs-sync test-read-design-classification test-lib-title-eligibility test-subskill-anchors test-alias-structure test-lib-title-markers test-phantom-probe-with-warn test-rebase-checkpoint-probe

test-harnesses-20: test-collect-agent-results test-collect-findings test-decompose-panel-dispatch test-compose-review-findings test-relevant-checks test-write-tally test-check-generators test-check-main-sync test-classify-bump test-release-prepare test-release-set-version test-release-finish test-promote-release test-implement-review-token-propagation test-emit-design-plan-preview test-token-cost test-get-issue-context test-run-external-agent-args test-external-tool-registry test-implement-timing-rehydration test-anti-halt test-run-analysis-quiet
test-pipe-sigpipe-safety:
	bash scripts/harness-timer.sh $@ bash scripts/test-pipe-sigpipe-safety.sh

test-redact:
	bash scripts/harness-timer.sh $@ bash scripts/test-redact-secrets.sh

test-scrub-log-secrets:
	bash scripts/harness-timer.sh $@ bash scripts/test-scrub-log-secrets.sh

test-redact-tmpdir-paths:
	bash scripts/harness-timer.sh $@ bash scripts/test-redact-tmpdir-paths.sh

test-read-design-classification:
	bash scripts/harness-timer.sh $@ bash scripts/test-read-design-classification.sh

test-append-tool-failure:
	bash scripts/harness-timer.sh $@ bash scripts/test-append-tool-failure.sh

test-validate-research-output:
	bash scripts/harness-timer.sh $@ bash scripts/test-validate-research-output.sh

test-validate-citations:
	bash scripts/harness-timer.sh $@ bash skills/research/scripts/test-validate-citations.sh

test-validate-citations-budget:
	bash scripts/harness-timer.sh $@ bash skills/research/scripts/test-validate-citations-budget.sh

test-collect-agent-bash32:
	bash scripts/harness-timer.sh $@ bash scripts/test-collect-agent-bash32.sh

test-collect-agent-retry:
	bash scripts/harness-timer.sh $@ bash scripts/test-collect-agent-retry.sh

test-collect-agent-results:
	bash scripts/harness-timer.sh $@ bash scripts/test-collect-agent-results.sh

test-lib-failed-agent-stderr-tail:
	bash scripts/harness-timer.sh $@ bash scripts/test-lib-failed-agent-stderr-tail.sh

test-lib-net:
	bash scripts/harness-timer.sh $@ bash scripts/test-lib-net.sh

test-parse-input:
	bash scripts/harness-timer.sh $@ bash skills/issue/scripts/test-parse-input.sh

test-allocate-candidates:
	bash scripts/harness-timer.sh $@ bash skills/issue/scripts/test-allocate-candidates.sh

test-add-blocked-by:
	bash scripts/harness-timer.sh $@ bash skills/issue/scripts/test-add-blocked-by.sh

test-list-issues:
	bash scripts/harness-timer.sh $@ bash skills/issue/scripts/test-list-issues.sh

test-analyze:
	bash scripts/harness-timer.sh $@ bash .claude/skills/analyze-issues/scripts/test-analyze.sh

test-parse-prose-blockers:
	bash scripts/harness-timer.sh $@ bash scripts/test-parse-prose-blockers.sh

test-fetch-combinable-issues-filter:
	bash scripts/harness-timer.sh $@ bash scripts/test-fetch-combinable-issues-filter.sh

test-legacy-title-prefix-literals-scope:
	bash scripts/harness-timer.sh $@ bash scripts/test-legacy-title-prefix-literals-scope.sh

test-implement-admission:
	bash scripts/harness-timer.sh $@ bash scripts/test-implement-admission.sh

test-anti-improvised-wakeup:
	bash scripts/harness-timer.sh $@ bash scripts/test-anti-improvised-wakeup.sh

test-audit-runs:
	bash scripts/harness-timer.sh $@ bash .claude/skills/audit-runs/scripts/test-audit-runs.sh

test-sentinel-write:
	bash scripts/harness-timer.sh $@ bash skills/issue/scripts/test-sentinel-write.sh

test-sessionstart:
	bash scripts/harness-timer.sh $@ bash scripts/test-sessionstart-health.sh

test-keepalive-sentinel:
	bash scripts/harness-timer.sh $@ bash scripts/test-keepalive-sentinel.sh

test-preflight-args:
	bash scripts/harness-timer.sh $@ bash scripts/test-preflight-args.sh

test-check-clean-tree:
	bash scripts/harness-timer.sh $@ bash scripts/test-check-clean-tree.sh

test-check-main-sync:
	bash scripts/harness-timer.sh $@ bash scripts/test-check-main-sync.sh

test-plan-block:
	bash scripts/harness-timer.sh $@ bash scripts/test-plan-block.sh

test-clarify-comment:
	bash scripts/harness-timer.sh $@ bash scripts/test-clarify-comment.sh

test-clarify-state:
	bash scripts/harness-timer.sh $@ bash scripts/test-clarify-state.sh

test-check-stale-plugin:
	bash scripts/harness-timer.sh $@ bash scripts/test-check-stale-plugin.sh

test-cleanup-tmpdir:
	bash scripts/harness-timer.sh $@ bash scripts/test-cleanup-tmpdir.sh

test-cleanup:
	bash scripts/harness-timer.sh $@ bash skills/cleanup/scripts/test-cleanup.sh

test-cache-root-validation:
	bash scripts/harness-timer.sh $@ bash scripts/test-cache-root-validation.sh

test-cache-key-discipline:
	bash scripts/harness-timer.sh $@ bash scripts/test-cache-key-discipline.sh

test-finalize-sanity-check:
	bash scripts/harness-timer.sh $@ bash scripts/test-finalize-sanity-check.sh

test-set-up-forked-open-source-repo:
	bash scripts/harness-timer.sh $@ bash skills/set-up-forked-open-source-repo/scripts/test-setup-forked-open-source-repo.sh

test-session-entry-gate:
	bash scripts/harness-timer.sh $@ bash scripts/test-session-entry-gate.sh

test-session-setup-presence-defaults:
	bash scripts/harness-timer.sh $@ bash scripts/test-session-setup-presence-defaults.sh

test-session-setup-repo-fallback:
	bash scripts/harness-timer.sh $@ bash scripts/test-session-setup-repo-fallback.sh

test-session-env-roundtrip:
	bash scripts/harness-timer.sh $@ bash scripts/test-session-env-roundtrip.sh

test-audit-edit-write:
	bash scripts/harness-timer.sh $@ bash scripts/test-audit-edit-write.sh

test-block-submodule:
	bash scripts/harness-timer.sh $@ bash scripts/test-block-submodule-edit.sh

test-lib-implement-round-cap:
	bash scripts/harness-timer.sh $@ bash scripts/test-lib-implement-round-cap.sh

test-deny-edit-write:
	bash scripts/harness-timer.sh $@ bash scripts/test-deny-edit-write.sh




test-render-lane-status:
	bash scripts/harness-timer.sh $@ bash scripts/test-render-lane-status.sh

test-token-tally:
	bash scripts/harness-timer.sh $@ bash scripts/test-token-tally.sh

test-token-ledger:
	bash scripts/harness-timer.sh $@ bash scripts/test-token-ledger.sh

test-token-report:
	bash scripts/harness-timer.sh $@ bash scripts/test-token-report.sh

test-token-report-dedup:
	bash scripts/harness-timer.sh $@ bash scripts/test-token-report-dedup.sh

test-token-cost-per-bucket:
	bash scripts/harness-timer.sh $@ bash scripts/test-token-cost-per-bucket.sh

test-render-cost-line-realism:
	bash scripts/harness-timer.sh $@ bash scripts/test-render-cost-line-realism.sh

test-render-cost-line-callsites:
	bash scripts/harness-timer.sh $@ bash scripts/test-render-cost-line-callsites.sh

test-render-run-summary-callsites:
	bash scripts/harness-timer.sh $@ bash scripts/test-render-run-summary-callsites.sh

test-render-run-summary-format:
	bash scripts/harness-timer.sh $@ bash scripts/test-render-run-summary-format.sh

test-token-report-summary-format:
	bash scripts/harness-timer.sh $@ bash scripts/test-token-report-summary-format.sh

test-timing-ledger:
	bash scripts/harness-timer.sh $@ bash scripts/test-timing-ledger.sh

test-step-telemetry-mark:
	bash scripts/harness-timer.sh $@ bash scripts/test-step-telemetry-mark.sh

test-timing-report:
	bash scripts/harness-timer.sh $@ bash scripts/test-timing-report.sh

test-token-vendor-scrapers:
	bash scripts/harness-timer.sh $@ bash scripts/test-token-vendor-scrapers.sh

test-parse-codex-usage:
	bash scripts/harness-timer.sh $@ bash scripts/test-parse-codex-usage.sh

test-token-claude-source:
	bash scripts/harness-timer.sh $@ bash scripts/test-token-claude-source.sh

test-verify-skill-called:
	bash scripts/harness-timer.sh $@ bash scripts/test-verify-skill-called.sh


test-relevant-checks:
	bash scripts/harness-timer.sh $@ bash scripts/test-relevant-checks.sh

test-relevant-checks-byte-budget:
	bash scripts/harness-timer.sh $@ bash scripts/test-relevant-checks-byte-budget.sh

test-relevant-checks-validation:
	bash scripts/harness-timer.sh $@ bash scripts/test-relevant-checks-validation.sh

test-relevant-checks-helper-failure:
	bash scripts/harness-timer.sh $@ bash scripts/test-relevant-checks-helper-failure.sh

test-hook-anti-read-poll:
	bash scripts/harness-timer.sh $@ bash scripts/test-hook-anti-read-poll.sh

test-review-relevant-checks-helper:
	bash scripts/harness-timer.sh $@ bash scripts/test-review-relevant-checks-helper.sh

test-lint-fix-loop:
	bash scripts/harness-timer.sh $@ bash scripts/test-lint-fix-loop.sh



test-classify-bump:
	bash scripts/harness-timer.sh $@ bash .claude/skills/release/scripts/test-classify-bump.sh

test-release-prepare:
	bash scripts/harness-timer.sh $@ bash .claude/skills/release/scripts/test-release-prepare.sh

test-release-set-version:
	bash scripts/harness-timer.sh $@ bash .claude/skills/release/scripts/test-release-set-version.sh

test-release-finish:
	bash scripts/harness-timer.sh $@ bash .claude/skills/release/scripts/test-release-finish.sh

test-promote-release:
	bash scripts/harness-timer.sh $@ bash scripts/test-promote-release.sh


test-ci-wait-exit-trap:
	bash scripts/harness-timer.sh $@ bash scripts/test-ci-wait-exit-trap.sh

test-ci-rerun-failed:
	bash scripts/harness-timer.sh $@ bash scripts/test-ci-rerun-failed.sh

test-ci-status:
	bash scripts/harness-timer.sh $@ bash scripts/test-ci-status.sh

test-ci-behind-count:
	bash scripts/harness-timer.sh $@ bash scripts/test-ci-behind-count.sh

test-merge-pr:
	bash scripts/harness-timer.sh $@ bash scripts/test-merge-pr.sh

test-git-push:
	bash scripts/harness-timer.sh $@ bash scripts/test-git-push.sh

test-lint-skill-invocations:
	bash scripts/harness-timer.sh $@ bash scripts/test-lint-skill-invocations.sh

test-lint-literal-counts:
	bash scripts/harness-timer.sh $@ bash scripts/test-lint-literal-counts.sh

test-lint-no-raw-stderr-after-quiet-init:
	bash scripts/harness-timer.sh $@ bash scripts/test-lint-no-raw-stderr-after-quiet-init.sh

test-lint-bash32:
	bash scripts/harness-timer.sh $@ bash scripts/test-lint-bash32.sh

test-lint-gh-body-inline:
	bash scripts/harness-timer.sh $@ bash scripts/test-lint-gh-body-inline.sh

test-mermaid-fragments:
	bash scripts/harness-timer.sh $@ bash scripts/test-mermaid-fragments.sh

test-anti-halt:
	bash scripts/harness-timer.sh $@ bash scripts/test-anti-halt-banners.sh

test-orchestrator-scope-sync:
	bash scripts/harness-timer.sh $@ bash scripts/test-orchestrator-scope-sync.sh

test-alias-target-resolution:
	bash scripts/harness-timer.sh $@ bash scripts/test-alias-target-resolution.sh

test-alias-structure:
	bash scripts/harness-timer.sh $@ bash scripts/test-alias-structure.sh

test-design-structure:
	bash scripts/harness-timer.sh $@ bash scripts/test-design-structure.sh

test-design-reentry-guard:
	bash scripts/harness-timer.sh $@ bash scripts/test-design-reentry-guard.sh

test-design-pause-resume:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-design-pause-resume.sh

test-pause-skill:
	bash scripts/harness-timer.sh $@ bash skills/pause/scripts/test-pause-skill.sh

test-decompose-panel-dispatch:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-decompose-panel-dispatch.sh

test-decompose-aggregator:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-decompose-aggregator.sh

test-decompose-file-issues:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-decompose-file-issues.sh

test-design-driver:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-design-driver.sh

test-design-publish:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-design-publish.sh

test-design-postplan-emit:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-design-postplan-emit.sh

test-parse-design-argv:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-parse-design-argv.sh

test-upgrade-larch-retention:
	bash scripts/harness-timer.sh $@ bash skills/upgrade-larch/scripts/test-upgrade-larch-retention.sh

test-invoke-plan-validator:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-invoke-plan-validator.sh

test-file-design-oos:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-file-design-oos.sh

test-design-log-publish:
	bash scripts/harness-timer.sh $@ bash scripts/test-design-log-publish.sh

test-lib-title-eligibility:
	bash scripts/harness-timer.sh $@ bash scripts/test-lib-title-eligibility.sh

test-lib-title-markers:
	bash scripts/harness-timer.sh $@ bash scripts/test-lib-title-markers.sh

test-emit-plan:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-emit-plan.sh

test-gate-b-dedup-plan:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-gate-b-dedup-plan.sh

test-trailer-helpers:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-trailer-helpers.sh

test-emit-design-plan-preview:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-emit-design-plan-preview.sh
test-check-plan-size:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-check-plan-size.sh

test-snapshot-plan-round:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-snapshot-plan-round.sh

test-dispatch-plan-assessors:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-dispatch-plan-assessors.sh

test-render-assessor-prompt:
	bash scripts/harness-timer.sh $@ bash skills/shared/scripts/test-render-assessor-prompt.sh

test-tally-plan-assessor:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-tally-plan-assessor.sh

test-assess-plan-round:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-assess-plan-round.sh

test-design-plan-quality-assessor:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-design-plan-quality-assessor.sh

test-parse-plan-commands:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-parse-plan-commands.sh


test-validate-plan-commands:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-validate-plan-commands.sh

test-tally-plan-review:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-tally-plan-review.sh

test-findings-classification:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-findings-classification.sh

test-review-findings-classification:
	bash scripts/harness-timer.sh $@ bash skills/review/scripts/test-findings-classification.sh

test-plan-review-loop:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-plan-review-loop.sh

test-lib-design-round-artifacts:
	bash scripts/harness-timer.sh $@ bash scripts/test-lib-design-round-artifacts.sh

test-design-multi-round-integration:
	bash scripts/harness-timer.sh $@ bash scripts/test-design-multi-round-integration.sh

test-step3-review-cap:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-step3-review-cap.sh

test-run-step3-review:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-run-step3-review.sh

test-step3-orchestrator-fence:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-step3-orchestrator-fence.sh

test-lib-phase-driver:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-lib-phase-driver.sh

test-finalize-plan:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-finalize-plan.sh

test-write-run-params:
	bash scripts/harness-timer.sh $@ bash scripts/test-write-run-params.sh

test-step0b-router-flag-recovery:
	bash scripts/harness-timer.sh $@ bash scripts/test-step0b-router-flag-recovery.sh

test-write-design-current-env:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-write-design-current-env.sh

test-plan-review-prompt:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-plan-review-prompt.sh

test-brainstorm-prompts:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-brainstorm-prompts.sh

test-lint-readability-preamble:
	bash scripts/harness-timer.sh $@ bash scripts/test-lint-readability-preamble.sh

test-lint-renderer-substitution-safety:
	bash scripts/harness-timer.sh $@ bash scripts/test-lint-renderer-substitution-safety.sh

test-lint-skill-md-flag-signature:
	bash scripts/harness-timer.sh $@ bash scripts/test-lint-skill-md-flag-signature.sh

test-lint-bare-grep-probe:
	bash scripts/harness-timer.sh $@ bash scripts/test-lint-bare-grep-probe.sh

test-lint-awk-multibyte-regex:
	bash scripts/harness-timer.sh $@ bash scripts/test-lint-awk-multibyte-regex.sh

test-scout-plan-archetypes-wrapper:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-scout-plan-archetypes-wrapper.sh

test-dispatch-plan-review-panel:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-dispatch-plan-review-panel.sh

test-render-final-summary:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-render-final-summary.sh

test-render-final-summary-bash32:
	bash scripts/harness-timer.sh $@ bash scripts/test-render-final-summary-bash32.sh

test-implement-rebase-macro:
	bash scripts/harness-timer.sh $@ bash scripts/test-implement-rebase-macro.sh

test-ship-pr-rebase:
	bash scripts/harness-timer.sh $@ bash scripts/test-ship-pr-rebase.sh

test-rebase-checkpoint-probe:
	bash scripts/test-rebase-checkpoint-probe.sh

test-phantom-probe-with-warn:
	bash scripts/test-phantom-probe-with-warn.sh

test-implement-step2-routing:
	bash scripts/harness-timer.sh $@ bash scripts/test-implement-step2-routing.sh

test-rebase-push-keep-on-conflict:
	bash scripts/harness-timer.sh $@ bash scripts/test-rebase-push-keep-on-conflict.sh


test-rebase-push-force-lease:
	bash scripts/harness-timer.sh $@ bash scripts/test-rebase-push-force-lease.sh

test-rebase-push-fork-mode:
	bash scripts/harness-timer.sh $@ bash scripts/test-rebase-push-fork-mode.sh

test-rebase-push-no-push-fetch-retry:
	bash scripts/harness-timer.sh $@ bash scripts/test-rebase-push-no-push-fetch-retry.sh

test-implement-structure:
	bash scripts/harness-timer.sh $@ bash scripts/test-implement-structure.sh

test-implement-step8-exit3-first-fixer:
	bash scripts/harness-timer.sh $@ bash scripts/test-implement-step8-exit3-first-fixer.sh

test-oos-disposition-gate:
	bash scripts/harness-timer.sh $@ bash skills/implement/scripts/test-oos-disposition-gate.sh

test-plan-adequacy-audit:
	bash scripts/harness-timer.sh $@ bash scripts/test-plan-adequacy-audit.sh

test-implement-positional-issue:
	bash scripts/harness-timer.sh $@ bash scripts/test-implement-positional-issue.sh

test-implement-timing-rehydration:
	bash scripts/harness-timer.sh $@ bash scripts/test-implement-timing-rehydration.sh

test-implement-cleanup-roundtrip:
	bash scripts/harness-timer.sh $@ bash scripts/test-implement-cleanup-roundtrip.sh

test-implement-anti-polling-rule:
	bash scripts/harness-timer.sh $@ bash scripts/test-implement-anti-polling-rule.sh

test-implement-relevant-checks-anti-halt:
	bash scripts/harness-timer.sh $@ bash skills/implement/scripts/test-implement-relevant-checks-anti-halt.sh

test-implement-anti-halt:
	bash scripts/harness-timer.sh $@ bash scripts/test-implement-anti-halt.sh

test-implement-review-token-propagation:
	bash scripts/harness-timer.sh $@ bash skills/implement/scripts/test-implement-review-token-propagation.sh

test-run-step2-dispatch:
	bash scripts/harness-timer.sh $@ bash skills/implement/scripts/test-run-step2-dispatch.sh

test-step2-dispatch:
	bash scripts/harness-timer.sh $@ bash skills/implement/scripts/test-step2-dispatch.sh

test-stall-recovery-report:
	bash scripts/harness-timer.sh $@ bash skills/implement/scripts/test-stall-recovery-report.sh

test-step-18b-final-report:
	bash scripts/harness-timer.sh $@ bash skills/implement/scripts/test-step-18b-final-report.sh

test-cursor-implementer:
	bash scripts/harness-timer.sh $@ bash skills/implement/scripts/test-cursor-implementer.sh

test-codex-implementer:
	bash scripts/harness-timer.sh $@ bash skills/implement/scripts/test-codex-implementer.sh

test-extract-plan-scope-paths:
	bash scripts/harness-timer.sh $@ bash scripts/test-extract-plan-scope-paths.sh

test-git-commit-only:
	bash scripts/harness-timer.sh $@ bash scripts/test-git-commit-only.sh

test-refresh-run-logs:
	bash scripts/harness-timer.sh $@ bash scripts/test-refresh-run-logs.sh

test-gh-run-logs:
	bash scripts/harness-timer.sh $@ bash scripts/test-gh-run-logs.sh

test-ci-failed-jobs:
	bash scripts/harness-timer.sh $@ bash scripts/test-ci-failed-jobs.sh

test-ci-wait:
	bash scripts/harness-timer.sh $@ bash scripts/test-ci-wait.sh

test-launch-cursor-ci:
	bash scripts/harness-timer.sh $@ bash scripts/test-launch-cursor-ci.sh

test-launch-claude-ci:
	bash scripts/harness-timer.sh $@ bash scripts/test-launch-claude-ci.sh

test-launch-codex-ci:
	bash scripts/harness-timer.sh $@ bash scripts/test-launch-codex-ci.sh

test-run-negotiation-round:
	bash scripts/harness-timer.sh $@ bash scripts/test-run-negotiation-round.sh

test-run-external-agent-args:
	bash scripts/harness-timer.sh $@ bash scripts/test-run-external-agent-args.sh

test-quick-mode-docs-sync:
	bash scripts/harness-timer.sh $@ bash scripts/test-quick-mode-docs-sync.sh
	bash scripts/harness-timer.sh $@ bash scripts/test-quick-mode-docs-sync.sh --self-test

test-implement-finalize:
	bash scripts/harness-timer.sh $@ bash scripts/test-implement-finalize.sh

test-implement-bootstrap:
	bash scripts/harness-timer.sh $@ bash skills/implement/scripts/test-implement-bootstrap.sh

test-implement-bootstrap-invoke:
	bash scripts/harness-timer.sh $@ bash skills/implement/scripts/test-implement-bootstrap-invoke.sh

test-persist-implement-run-flags:
	bash scripts/harness-timer.sh $@ bash scripts/test-persist-implement-run-flags.sh


test-flush-execution-issues:
	bash scripts/harness-timer.sh $@ bash skills/implement/scripts/test-flush-execution-issues.sh

test-step-7a:
	bash scripts/harness-timer.sh $@ bash skills/implement/scripts/test-step-7a.sh

test-post-tracking-issue:
	bash scripts/harness-timer.sh $@ bash skills/implement/scripts/test-post-tracking-issue.sh

test-commit-implementation:
	bash scripts/harness-timer.sh $@ bash skills/implement/scripts/test-commit-implementation.sh

test-commit-review-fixes:
	bash scripts/harness-timer.sh $@ bash skills/implement/scripts/test-commit-review-fixes.sh

test-generate-code-flow-diagram:
	bash scripts/harness-timer.sh $@ bash skills/implement/scripts/test-generate-code-flow-diagram.sh

test-refresh-execution-issues:
	bash scripts/harness-timer.sh $@ bash skills/implement/scripts/test-refresh-execution-issues.sh

test-write-rejected-findings:
	bash scripts/harness-timer.sh $@ bash skills/implement/scripts/test-write-rejected-findings.sh

test-slack-issue-announce:
	bash scripts/harness-timer.sh $@ bash skills/implement/scripts/test-slack-issue-announce.sh

test-write-final-report:
	bash scripts/harness-timer.sh $@ bash skills/implement/scripts/test-write-final-report.sh

test-render-run-summary:
	bash scripts/harness-timer.sh $@ bash scripts/test-render-run-summary.sh

test-token-cost:
	bash scripts/harness-timer.sh $@ bash scripts/test-token-cost.sh

test-run-analysis-quiet:
	bash scripts/harness-timer.sh $@ bash skills/report-tokens/scripts/test-run-analysis-quiet.sh

test-render-cost-line:
	bash scripts/harness-timer.sh $@ bash scripts/test-render-cost-line.sh

test-implement-cleanup-script:
	bash scripts/harness-timer.sh $@ bash skills/implement/scripts/test-cleanup.sh

test-restore-finalize-state:
	bash scripts/harness-timer.sh $@ bash scripts/test-restore-finalize-state.sh

test-harness-shards-coverage:
	bash scripts/harness-timer.sh $@ bash scripts/test-harness-shards-coverage.sh
	bash scripts/harness-timer.sh $@ bash scripts/test-harness-shards-coverage.sh --self-test

test-harness-timer:
	bash scripts/harness-timer.sh $@ bash scripts/test-harness-timer.sh

test-references-headers:
	bash scripts/harness-timer.sh $@ bash scripts/test-references-headers.sh

test-render-reviewer-prompt:
	bash scripts/harness-timer.sh $@ bash scripts/test-render-reviewer-prompt.sh

test-render-specialist-prompt:
	bash scripts/harness-timer.sh $@ bash scripts/test-render-specialist-prompt.sh

test-render-debate-retry-prompt:
	bash scripts/harness-timer.sh $@ bash scripts/test-render-debate-retry-prompt.sh

test-research-structure:
	bash scripts/harness-timer.sh $@ bash scripts/test-research-structure.sh

test-review-structure:
	bash scripts/harness-timer.sh $@ bash scripts/test-review-structure.sh

test-gather-context:
	bash scripts/harness-timer.sh $@ bash skills/review/scripts/test-gather-context.sh

test-review-core:
	bash scripts/harness-timer.sh $@ bash skills/review/scripts/test-review-core.sh

test-dispatch-panel-core:
	bash scripts/harness-timer.sh $@ bash skills/review/scripts/test-dispatch-panel.sh --section core

test-dispatch-panel-reuse:
	bash scripts/harness-timer.sh $@ bash skills/review/scripts/test-dispatch-panel.sh --section reuse

test-dispatch-panel-limits:
	bash scripts/harness-timer.sh $@ bash skills/review/scripts/test-dispatch-panel.sh --section limits

test-scout-dynamic-archetypes:
	bash scripts/harness-timer.sh $@ bash scripts/test-scout-dynamic-archetypes.sh

test-dispatch-plan-voters:
	bash scripts/harness-timer.sh $@ bash scripts/test-dispatch-plan-voters.sh

test-render-voter-prompt:
	bash scripts/harness-timer.sh $@ bash scripts/test-render-voter-prompt.sh

test-prompt-template-invariants:
	bash scripts/harness-timer.sh $@ bash scripts/test-prompt-template-invariants.sh

test-lib-submodule-prohibition:
	bash scripts/harness-timer.sh $@ bash scripts/test-lib-submodule-prohibition.sh

test-collect-findings:
	bash scripts/harness-timer.sh $@ bash skills/review/scripts/test-collect-findings.sh

test-aggregate-findings:
	bash scripts/harness-timer.sh $@ bash skills/review/scripts/test-aggregate-findings.sh

test-tally-code-votes:
	bash scripts/harness-timer.sh $@ bash skills/review/scripts/test-tally-code-votes.sh

.PHONY: test-check-reviewer-failure-threshold
test-check-reviewer-failure-threshold:
	bash scripts/harness-timer.sh $@ bash skills/review/scripts/test-check-reviewer-failure-threshold.sh

.PHONY: test-lib-vote-tally
test-lib-vote-tally:
	bash scripts/harness-timer.sh $@ bash scripts/test-lib-vote-tally.sh

.PHONY: test-dispatch-code-voters-happy test-dispatch-code-voters-edge-and-r3-claude test-dispatch-code-voters-retry-claude test-dispatch-code-voters-retry-codex-success test-dispatch-code-voters-retry-cursor test-dispatch-code-voters-retry-codex-fail-and-fallback test-dispatch-code-voters-regressions-r1-r2 test-dispatch-code-voters-regressions-r3-codex
test-dispatch-code-voters-happy:
	bash scripts/harness-timer.sh $@ bash scripts/test-dispatch-code-voters.sh --section happy

test-dispatch-code-voters-edge-and-r3-claude:
	bash scripts/harness-timer.sh $@ bash scripts/test-dispatch-code-voters.sh --section edge-and-r3-claude

test-dispatch-code-voters-regressions-r1-r2:
	bash scripts/harness-timer.sh $@ bash scripts/test-dispatch-code-voters.sh --section regressions-r1-r2

test-dispatch-code-voters-regressions-r3-codex:
	bash scripts/harness-timer.sh $@ bash scripts/test-dispatch-code-voters.sh --section regressions-r3-codex

test-dispatch-code-voters-retry-claude:
	bash scripts/harness-timer.sh $@ bash scripts/test-dispatch-code-voters.sh --section retry-claude

test-dispatch-code-voters-retry-codex-success:
	bash scripts/harness-timer.sh $@ bash scripts/test-dispatch-code-voters.sh --section retry-codex-success

test-dispatch-code-voters-retry-cursor:
	bash scripts/harness-timer.sh $@ bash scripts/test-dispatch-code-voters.sh --section retry-cursor

test-dispatch-code-voters-retry-codex-fail-and-fallback:
	bash scripts/harness-timer.sh $@ bash scripts/test-dispatch-code-voters.sh --section retry-codex-fail-and-fallback

test-emit-tally:
	bash scripts/harness-timer.sh $@ bash skills/review/scripts/test-emit-tally.sh

test-log-phase:
	bash scripts/harness-timer.sh $@ bash skills/review/scripts/test-log-phase.sh

# test-review-and-fix runs all sections sequentially (local-dev convenience, NOT a test-harnesses
# prerequisite — see CARVE_OUTS in scripts/test-harness-shards-coverage.sh). CI uses the four
# section targets below instead: dispatch, convergence, parsers, and step5-starting-round.
test-review-and-fix:
	bash scripts/harness-timer.sh $@ bash skills/review-and-fix/scripts/test-review-and-fix.sh

test-review-and-fix-dispatch:
	bash scripts/harness-timer.sh $@ bash skills/review-and-fix/scripts/test-review-and-fix.sh --section dispatch

test-review-and-fix-convergence:
	bash scripts/harness-timer.sh $@ bash skills/review-and-fix/scripts/test-review-and-fix.sh --section convergence

test-review-and-fix-parsers:
	bash scripts/harness-timer.sh $@ bash skills/review-and-fix/scripts/test-review-and-fix.sh --section parsers

test-review-and-fix-step5-starting-round:
	bash scripts/harness-timer.sh $@ bash skills/review-and-fix/scripts/test-review-and-fix.sh --section step5-starting-round

test-run-step5-review:
	bash scripts/harness-timer.sh $@ bash scripts/test-run-step5-review.sh

test-scrub-submodule-paths:
	bash scripts/harness-timer.sh $@ bash scripts/test-scrub-submodule-paths.sh

test-ballot-parse:
	bash scripts/harness-timer.sh $@ bash skills/shared/scripts/test-ballot-parse.sh

test-tally-vote:
	bash scripts/harness-timer.sh $@ bash skills/shared/scripts/test-tally-vote.sh

test-scoreboard:
	bash scripts/harness-timer.sh $@ bash skills/shared/scripts/test-scoreboard.sh

test-oos-serialize:
	bash scripts/harness-timer.sh $@ bash skills/shared/scripts/test-oos-serialize.sh

test-run-research-planner:
	bash scripts/harness-timer.sh $@ bash skills/research/scripts/test-run-research-planner.sh

test-render-findings-batch:
	bash scripts/harness-timer.sh $@ bash skills/research/scripts/test-render-findings-batch.sh

test-research-banner:
	bash scripts/harness-timer.sh $@ bash skills/research/scripts/test-research-banner.sh

test-synthesis-subagent:
	bash scripts/harness-timer.sh $@ bash skills/research/scripts/test-synthesis-subagent.sh

test-research-angle-prompts:
	bash scripts/harness-timer.sh $@ bash skills/research/scripts/test-research-angle-prompts.sh

test-subskill-anchors:
	bash scripts/harness-timer.sh $@ bash scripts/test-subskill-anchors.sh

test-tracking-issue-write:
	bash scripts/harness-timer.sh $@ bash scripts/test-tracking-issue-write.sh

test-larch-log:
	bash scripts/harness-timer.sh $@ bash scripts/test-larch-log.sh

test-larch-log-write-round:
	bash scripts/harness-timer.sh $@ bash scripts/test-larch-log-write-round.sh

test-capture-session-transcript:
	bash scripts/harness-timer.sh $@ bash scripts/test-capture-session-transcript.sh

test-verify-run-log-completeness:
	env -u LARCH_VERIFY_MANIFEST bash scripts/harness-timer.sh $@ bash scripts/test-verify-run-log-completeness.sh

test-local-cleanup:
	bash scripts/harness-timer.sh $@ bash scripts/test-local-cleanup.sh

test-larch-logs-manifest:
	bash scripts/harness-timer.sh $@ bash scripts/test-larch-logs-manifest.sh

test-larch-logs-batches:
	bash scripts/harness-timer.sh $@ bash scripts/test-larch-logs-batches.sh

test-compose-plan-goals-test:
	bash scripts/harness-timer.sh $@ bash scripts/test-compose-plan-goals-test.sh

test-run-step1-plan-log:
	bash scripts/harness-timer.sh $@ bash scripts/test-run-step1-plan-log.sh

test-write-tally:
	bash scripts/harness-timer.sh $@ bash scripts/test-write-tally.sh

test-compose-collector-failure-log:
	bash scripts/harness-timer.sh $@ bash scripts/test-compose-collector-failure-log.sh

test-compose-pr-summary:
	bash scripts/harness-timer.sh $@ bash scripts/test-compose-pr-summary.sh

test-upsert-diagrams-comment:
	bash scripts/harness-timer.sh $@ bash scripts/test-upsert-diagrams-comment.sh

test-tracking-issue-summary:
	bash scripts/harness-timer.sh $@ bash scripts/test-tracking-issue-summary.sh

test-false-positive-keywords:
	bash scripts/harness-timer.sh $@ bash scripts/test-false-positive-keywords.sh

test-tracking-issue-read-sentinel:
	bash scripts/harness-timer.sh $@ bash scripts/test-tracking-issue-read-sentinel.sh

test-compose-review-findings:
	bash scripts/harness-timer.sh $@ bash scripts/test-compose-review-findings.sh







test-check-review-changes:
	bash scripts/harness-timer.sh $@ bash skills/implement/scripts/test-check-review-changes.sh

test-check-mid-run-dirty-tree:
	bash scripts/harness-timer.sh $@ bash scripts/test-check-mid-run-dirty-tree.sh

test-check-phantom-dirty:
	bash scripts/harness-timer.sh $@ bash scripts/test-check-phantom-dirty.sh

test-check-reviewers:
	bash scripts/harness-timer.sh $@ bash scripts/test-check-reviewers.sh

test-degraded-tools-gate:
	bash scripts/harness-timer.sh $@ bash scripts/test-degraded-tools-gate.sh

test-no-grouped-reuse-guard:
	bash scripts/harness-timer.sh $@ bash scripts/test-no-grouped-reuse-guard.sh

test-check-generators:
	bash scripts/harness-timer.sh $@ bash scripts/test-check-generators.sh

test-check-topology-rule-paths:
	bash scripts/harness-timer.sh $@ bash scripts/test-check-topology-rule-paths.sh

test-generate-topology-docs:
	bash scripts/harness-timer.sh $@ bash scripts/test-generate-topology-docs.sh

test-external-tool-registry:
	bash scripts/harness-timer.sh $@ bash scripts/test-external-tool-registry.sh

test-launch-review:
	bash scripts/harness-timer.sh $@ bash scripts/test-launch-review.sh

test-lib-external-launcher-common:
	bash scripts/harness-timer.sh $@ bash scripts/test-lib-external-launcher-common.sh

test-launch-claude-subprocess:
	bash scripts/harness-timer.sh $@ bash scripts/test-launch-claude-subprocess.sh

test-launch-claude-review:
	bash scripts/harness-timer.sh $@ bash scripts/test-launch-claude-review.sh

test-dispatch-with-waterfall:
	bash scripts/harness-timer.sh $@ bash scripts/test-dispatch-with-waterfall.sh

test-revise-plan-with-waterfall:
	bash scripts/harness-timer.sh $@ bash scripts/test-revise-plan-with-waterfall.sh

test-agent-model-args:
	bash scripts/harness-timer.sh $@ bash scripts/test-agent-model-args.sh

test-effort-prose:
	bash scripts/harness-timer.sh $@ bash scripts/test-effort-prose.sh

test-lib-cursor-auth:
	bash scripts/harness-timer.sh $@ bash scripts/test-lib-cursor-auth.sh

test-lib-quiet:
	bash scripts/harness-timer.sh $@ bash scripts/test-lib-quiet.sh

test-lib-design-tmpdir:
	bash scripts/harness-timer.sh $@ bash scripts/test-lib-design-tmpdir.sh

test-github-remote-repo:
	bash scripts/harness-timer.sh $@ bash scripts/test-github-remote-repo.sh

test-implement-fork-env:
	bash scripts/harness-timer.sh $@ bash scripts/test-implement-fork-env.sh

test-get-issue-context:
	bash scripts/harness-timer.sh $@ bash scripts/test-get-issue-context.sh

test-get-issue-state:
	bash scripts/harness-timer.sh $@ bash scripts/test-get-issue-state.sh

test-create-pr:
	bash scripts/harness-timer.sh $@ bash scripts/test-create-pr.sh

test-resolve-repo:
	bash scripts/harness-timer.sh $@ bash scripts/test-resolve-repo.sh

test-gh-pr-body-update:
	bash scripts/harness-timer.sh $@ bash scripts/test-gh-pr-body-update.sh

test-wait-for-reviewers:
	bash scripts/harness-timer.sh $@ bash scripts/test-wait-for-reviewers.sh

test-run-external-agent:
	bash scripts/harness-timer.sh $@ bash scripts/test-run-external-agent.sh


test-body-file-title:
	bash scripts/harness-timer.sh $@ bash skills/issue/scripts/test-body-file-title.sh

test-intra-batch-deps:
	bash scripts/harness-timer.sh $@ bash skills/issue/scripts/test-intra-batch-deps.sh

test-oos-file-conflict-deps:
	bash scripts/harness-timer.sh $@ bash skills/implement/scripts/test-oos-file-conflict-deps.sh

test-oos-issue-cap:
	bash scripts/harness-timer.sh $@ bash skills/implement/scripts/test-oos-issue-cap.sh

test-materialize-manifest-oos:
	bash scripts/harness-timer.sh $@ bash skills/implement/scripts/test-materialize-manifest-oos.sh

test-blocked-by-issue:
	bash scripts/harness-timer.sh $@ bash skills/issue/scripts/test-blocked-by-issue.sh

smoke-dialectic:
	bash scripts/dialectic-smoke-test.sh

lint-mermaid:
	if [ ! -f mermaid-lint/node_modules/.package-lock.json ]; then (cd mermaid-lint && npm ci); fi
	scripts/lint-mermaid-fences.sh --changed-only
	bash scripts/test-pipe-sigpipe-safety.sh

agent-sync:
	bash scripts/check-generators.sh
	python3 scripts/check-topology-rule-paths.py
	bash scripts/check-focus-area-enum.sh

# Opt-in /research evaluation harness (closes #419 under umbrella #413). NOT a
# lint prerequisite — runs ~20 questions × ~30-60s each, costs real tokens.
# Operator instrumentation for prompt-side iteration on /research. See
# docs/linting.md "/research evaluation harness". Pass flags via ARGS=,
# e.g.: `make eval-research ARGS="--id eval-1 --timeout 4200"`. Direct
# `bash scripts/eval-research.sh ...` is the documented primary path.
eval-research:
	bash scripts/eval-research.sh $(ARGS)

# Standalone offline structural test for the /research eval set + harness
# (closes #419). NOT a `test-harnesses` prerequisite by design — the runtime
# harness it tests is opt-in operator instrumentation explicitly carved out
# from CI. The structural test is itself cheap (no API cost) but kept
# standalone for symmetry. See scripts/test-eval-set-structure.md.
test-eval-set-structure:
	bash scripts/harness-timer.sh $@ bash scripts/test-eval-set-structure.sh

# Standalone offline regression harness for the `--baseline` flag handling
# in scripts/eval-research.sh (closes #441). NOT a `test-harnesses`
# prerequisite — the eval-research surface is opt-in operator
# instrumentation explicitly carved out from CI by repo contract
# (see the `test-eval-set-structure` target above, docs/linting.md,
# scripts/eval-research.md). Runs offline by PATH-stubbing claude + jq
# so it works on machines without the real binaries.
# See scripts/test-eval-research-baseline-flag.md.
test-eval-research-baseline-flag:
	bash scripts/harness-timer.sh $@ bash scripts/test-eval-research-baseline-flag.sh

shellcheck:
	pre-commit run shellcheck --all-files

lint-bash32:
	bash scripts/lint-bash32.sh

lint-gh-body-inline:
	bash scripts/lint-gh-body-inline.sh

markdownlint:
	pre-commit run markdownlint --all-files

jsonlint:
	pre-commit run jsonlint --all-files

actionlint:
	pre-commit run actionlint --all-files

agent-lint:
	pre-commit run agent-lint --all-files

agnix:
	pre-commit run agnix --all-files

gitleaks:
	pre-commit run gitleaks --all-files

# Trufflehog is CI-only (not a pre-commit hook). This target runs the same
# pinned Docker image as CI but in `filesystem` mode over the working tree;
# CI's `trufflehog` job uses the upstream action's default `git` mode over
# the PR range (different subcommand and scan scope). Image/tag and
# `--only-verified` are identical between the two — the rest is not.
trufflehog:
	docker run --rm -v "$(PWD):/repo" ghcr.io/trufflesecurity/trufflehog:3.82.13 \
		filesystem /repo --only-verified

setup:
	pre-commit install

test-check-contains-pins:
	bash scripts/harness-timer.sh $@ bash scripts/test-check-contains-pins.sh
