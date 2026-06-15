# Larch Makefile
# Thin wrapper around pre-commit. Linter definitions live in .pre-commit-config.yaml.

PYTHON ?= python3

.PHONY: py-lint py-test lint lint-only test-harnesses test-harnesses-1 test-harnesses-2 test-harnesses-3 test-harnesses-4 test-harnesses-5 test-harnesses-6 test-harnesses-7 test-harnesses-8 test-harnesses-9 test-harnesses-10 test-harnesses-11 test-harnesses-12 test-harnesses-13 test-harnesses-14 test-harnesses-15 test-harnesses-16 test-harnesses-17 test-harnesses-18 test-harnesses-19 test-harnesses-20 shellcheck markdownlint jsonlint actionlint agent-lint agnix gitleaks trufflehog setup test-pipe-sigpipe-safety test-redact test-scrub-log-secrets test-redact-tmpdir-paths test-append-tool-failure test-flush-vendor-failure-diagnostics test-append-execution-issue test-validate-research-output test-validate-citations test-validate-citations-budget test-render-final-summary-bash32 test-collect-agent-results test-blocker test-issue-query test-anti-improvised-wakeup test-audit-runs test-sessionstart test-resolve-implement-tmpdir test-check-clean-tree test-check-main-sync test-check-scope-reduction-marker test-plan-review-scope-anchor test-persist-retally-step3-env test-lib-scope-anchor-handoff test-clarify-comment test-clarify-state test-check-stale-plugin test-preflight-args test-cache-root-validation test-cache-key-discipline test-finalize-sanity-check test-audit-edit-write test-block-submodule test-deny-edit-write test-verify-skill-called test-hook-anti-read-poll test-hook-bg-poll-guard test-hook-progress-report test-classify-bump test-ci-wait-exit-trap test-ci-rerun-failed test-ci-status test-merge-pr test-git-push test-lint-skill-invocations test-lint-skill-md-flag-signature test-lint-codex-exec-auth test-lint-literal-counts test-lint-no-raw-stderr-after-quiet-init test-lint-readability-preamble test-lint-bare-grep-probe test-anti-halt test-orchestrator-scope-sync test-alias-structure test-design-structure test-decompose-panel-dispatch test-decompose-aggregator test-decompose-file-issues test-design-driver test-design-clarify test-design-publish test-design-postplan-emit test-invoke-plan-validator test-file-design-oos test-emit-plan test-gate-b-dedup-plan test-trailer-helpers test-emit-design-plan-preview test-check-plan-size test-parse-plan-commands test-validate-plan-commands test-step3-review-cap test-run-step3-review test-lib-phase-driver test-plan-review-loop test-tally-plan-review test-finalize-plan test-step0b-router-flag-recovery test-brainstorm-prompts test-scout-plan-archetypes-wrapper test-dispatch-plan-review-panel test-render-final-summary test-implement-rebase-macro test-rebase-checkpoint-probe test-phantom-probe-with-warn test-implement-step2-routing test-rebase-push-keep-on-conflict test-rebase-push-force-lease test-rebase-push-fork-mode test-rebase-push-no-push-fetch-retry test-implement-structure test-implement-step8-exit3-first-fixer test-oos-disposition-gate test-plan-adequacy-audit test-implement-preflight test-implement-positional-issue test-implement-fence-shape test-implement-timing-rehydration test-implement-cleanup-roundtrip test-implement-anti-polling-rule test-implement-relevant-checks-anti-halt test-implement-anti-halt test-implement-review-token-propagation test-step2-dispatch test-cursor-implementer test-codex-implementer test-gh-run-logs test-refresh-run-logs test-ci-wait test-launch-cursor-ci test-launch-claude-ci test-launch-codex-ci test-run-negotiation-round test-launch-claude-subprocess test-launch-claude-review test-launch-claude-drafter test-launch-codex-drafter test-parse-drafter-output test-dispatch-with-waterfall test-revise-plan-with-waterfall test-run-external-agent test-run-external-agent-args test-quick-mode-docs-sync test-implement-bootstrap test-implement-bootstrap-invoke test-implement-finalize test-flush-execution-issues test-post-tracking-issue test-commit-implementation test-review-and-fix-commit-fixes test-generate-code-flow-diagram test-refresh-execution-issues test-review-and-fix-write-rejected test-slack-issue-announce test-write-final-report test-step-18b-final-report test-render-run-summary test-render-review-phase-detail test-token-cost test-render-cost-line test-implement-cleanup-script test-harness-shards-coverage test-harness-timer test-references-headers test-research-structure test-review-structure test-gather-context test-gather-branch-context test-review-core test-dispatch-panel-core test-dispatch-panel-core-dynamic test-dispatch-panel-reuse test-dispatch-panel-limits test-scout-dynamic-archetypes test-dispatch-plan-voters test-collect-findings test-aggregate-findings test-prune-nit-findings test-tally-code-votes test-check-reviewer-failure-threshold test-dispatch-code-voters-happy test-dispatch-code-voters-edge-and-r3-claude test-dispatch-code-voters-regressions-r1-r2 test-dispatch-code-voters-regressions-r3-codex test-emit-tally test-log-phase test-review-and-fix test-review-and-fix-dispatch test-review-and-fix-convergence test-review-and-fix-parsers test-scrub-submodule-paths test-run-research-planner test-render-findings-batch test-research-banner test-synthesis-subagent test-research-angle-prompts test-subskill-anchors test-tracking-issue-write test-larch-log test-capture-session-transcript test-larch-logs-manifest test-larch-logs-batches test-compose-plan-goals-test test-compose-collector-failure-log test-tracking-issue-summary test-tracking-issue-read-sentinel test-compose-review-findings test-token-tally test-token-ledger test-token-report test-timing-ledger test-timing-report test-parse-codex-usage test-token-vendor-scrapers test-token-claude-source test-review-and-fix-check-changes test-check-mid-run-dirty-tree test-check-phantom-dirty test-check-reviewers test-degraded-tools-gate test-check-topology-rule-paths test-external-tool-registry test-agent-model-args test-effort-prose test-launch-review test-lib-external-launcher-common test-lib-cursor-auth test-lib-design-tmpdir test-lib-quiet test-github-remote-repo test-implement-fork-env test-get-issue-context test-create-pr test-resolve-repo test-gh-pr-body-update eval-research test-eval-set-structure test-eval-research-baseline-flag test-oos-file-conflict-deps test-oos-issue-cap test-materialize-manifest-oos test-wait-for-reviewers test-classify-diff-mode test-analyze test-compose-pr-summary test-compute-pr-line-counts test-review-and-fix-step5 test-run-step1-plan-log test-run-step2-dispatch test-prompt-template-invariants test-lib-submodule-prohibition test-verify-run-log-completeness test-design-log-publish test-fetch-combinable-issues-filter test-legacy-title-prefix-literals-scope test-implement-admission test-pause-skill test-fluff-analysis

.PHONY: test-findings-classification test-review-findings-classification test-review-and-fix-step5-starting-round test-lib-failed-agent-stderr-tail test-lib-net
.PHONY: test-prompt-template-invariants test-lib-submodule-prohibition
.PHONY: test-larch-log-write-round
.PHONY: test-scout-dynamic-archetypes
.PHONY: test-plan-review test-plan-review-panel
.PHONY: test-git-commit-only
.PHONY: test-design-reentry-guard
.PHONY: test-promote-release test-release-finish test-release-prepare test-release-set-version
.PHONY: test-auto-fix-plan-commands test-design-step2b-drafter test-gate-b-apply-mode
.PHONY: test-token-report-dedup test-token-cost-per-bucket test-render-cost-line-realism test-render-cost-line-callsites test-render-run-summary-callsites test-render-run-summary-format test-token-report-summary-format test-parse-bootstrap-routing-envelope test-step-telemetry-mark lint-retired-scripts
.PHONY: lint-bash32 test-lint-bash32 lint-gh-body-inline lint-mermaid agent-sync test-ci-failed-jobs test-ci-behind-count test-ci-decide
.PHONY: test-step-7a test-step-8-ship
.PHONY: test-stall-recovery-report test-stall-recovery-report-1 test-stall-recovery-report-2 test-stall-recovery-report-3 test-step-18b-final-report
.PHONY: test-resolve-upstream-larch-repo test-file-failure-report-cross-repo
.PHONY: test-design-pause-resume
.PHONY: test-review-design-step3-loop
.PHONY: test-read-result-env test-parse-design-argv
.PHONY: lint-readability-preamble test-lint-readability-preamble
.PHONY: lint-renderer-substitution-safety lint-skill-md-flag-signature test-lint-renderer-substitution-safety test-lint-skill-md-flag-signature
.PHONY: lint-bare-grep-probe test-lint-bare-grep-probe lint-codex-exec-auth test-lint-codex-exec-auth test-launch-codex-exec lint-awk-multibyte-regex test-lint-awk-multibyte-regex
.PHONY: test-design-multi-round-integration test-lib-design-round-artifacts test-step3-orchestrator-fence test-design-step3-state test-design-step3-mav
.PHONY: test-no-grouped-reuse-guard test-review-and-fix-record-timing test-review-and-fix-step5-loop-timing test-record-plan-review-round-timing test-reviewer-prune test-lib-prune-decision test-fluff-analysis-corpus
# CI splits `lint` into `lint-only` (pre-commit) and `test-harnesses`
# (regression harnesses). `lint` remains the local-dev convenience target
# that runs both, defined in terms of the two split targets to prevent drift.
lint: test-harnesses lint-bash32 lint-readability-preamble lint-renderer-substitution-safety lint-skill-md-flag-signature lint-bare-grep-probe lint-codex-exec-auth lint-awk-multibyte-regex lint-retired-scripts lint-only

py-lint:
	@$(PYTHON) -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' \
		|| (printf '%s\n' "ERROR: make py-lint requires Python 3.11 or newer (PYTHON=$(PYTHON))" >&2; exit 1)
	cd python && ruff check . && pylint . && pyright

py-test:
	@$(PYTHON) -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' \
		|| (printf '%s\n' "ERROR: make py-test requires Python 3.11 or newer (PYTHON=$(PYTHON))" >&2; exit 1)
	cd python && $(PYTHON) -m pytest

lint-only:
	pre-commit run --all-files

lint-readability-preamble:
	python3 python/cli.py lint readability-preamble

lint-renderer-substitution-safety:
	bash scripts/lint-renderer-substitution-safety.sh

lint-skill-md-flag-signature:
	python3 python/cli.py lint skill-md-flag-signature

lint-bare-grep-probe:
	bash scripts/lint-bare-grep-probe.sh

lint-codex-exec-auth:
	python3 python/cli.py lint codex-exec-auth

lint-awk-multibyte-regex:
	bash scripts/lint-awk-multibyte-regex.sh

# Balanced regression-harness shards (closes #1294, #1585, #1911, #2080, #2252, #2262, #2291, #2349, #2366, #2386 — rebalance after
# slow harnesses pushed shards 2/3/5 over the 20s target, resharded to 10, then resharded to 11,
# then to 13 after heavy tests pushed shard wall time over the 40s target, then to 16 after
# shards 12/13 exceeded 50s with test-dispatch-code-voters and test-dispatch-panel, then to 14
# after splitting test-ship-pr/-dispatch-code-voters/-dispatch-panel into sections and stubbing
# after stubbing long ship-driver sleeps brought the ceiling under 22s, then to 18 after isolating the four
# retry-only dispatch-code-voters harness sections into dedicated shard rows, and now to 20
# after gating the three previously-ungated Regression 1/2/3 blocks in
# test-dispatch-code-voters.sh into two new sections (regressions-r1-r2, regressions-r3-codex),
# folding Regression 3's claude case into the edge shard as edge-and-r3-claude, and splitting
# test-review-and-fix into dispatch/convergence sections (plus a parsers slice for Step 5 KV parsing) to shrink shard 13). Rebalanced 2026-05-31: fourth-pass LPT dropped test-ship-pr from CI shards;
# the Python ship driver is the shipped default after the sh-to-py cutover.
# Suite total 1001s; anchors: shard 1 (test-plan-review-loop 61s), shard 2
# (test-launch-review pytest); shards 3-20 target ~49s each. When
# imbalance returns, see docs/linting.md "Refreshing harness shard balance" for the regeneration
# procedure. IMPORTANT: each test-harnesses-N rule below stays on a single
# physical line (no `\` continuations); the drift-detection script
# `scripts/test-harness-shards-coverage.sh` parses these lines literally. New harnesses get
# appended to one shard line.
test-harnesses: test-harnesses-1 test-harnesses-2 test-harnesses-3 test-harnesses-4 test-harnesses-5 test-harnesses-6 test-harnesses-7 test-harnesses-8 test-harnesses-9 test-harnesses-10 test-harnesses-11 test-harnesses-12 test-harnesses-13 test-harnesses-14 test-harnesses-15 test-harnesses-16 test-harnesses-17 test-harnesses-18 test-harnesses-19 test-harnesses-20

test-harnesses-1: test-findings-classification

test-harnesses-2: test-fluff-analysis-corpus test-design-multi-round-integration test-invoke-plan-validator test-lib-scope-anchor-handoff test-stall-recovery-report-2 test-external-tool-registry test-run-step1-plan-log test-deny-edit-write test-ci-rerun-failed test-rebase-push-force-lease test-brainstorm-prompts

test-harnesses-3: test-design-failure-report test-run-step2-dispatch test-review-core test-launch-claude-drafter test-lint-literal-counts test-scout-dynamic-archetypes test-stall-recovery-report-3 test-dispatch-panel-core test-research-structure test-post-tracking-issue test-scrub-log-secrets test-plan-adequacy-audit test-github-remote-repo test-implement-positional-issue

test-harnesses-4: test-dispatch-with-waterfall test-run-research-planner test-merge-pr test-design-step-validator-autofix test-file-failure-report-cross-repo test-larch-log test-check-phantom-dirty test-check-main-sync test-promote-release test-rebase-push-keep-on-conflict test-oos-issue-cap test-lint-no-raw-stderr-after-quiet-init test-rebase-push-fork-mode

test-harnesses-5: test-dispatch-code-voters-happy test-render-findings-batch test-ci-decide test-auto-fix-plan-commands test-implement-review-token-propagation test-hook-bg-poll-guard test-larch-logs-batches test-compose-plan-goals-test test-fetch-combinable-issues-filter test-oos-file-conflict-deps test-compose-collector-failure-log test-generate-code-flow-diagram test-gh-run-logs test-slack-issue-announce test-render-run-summary-callsites

test-harnesses-6: test-harness-shards-coverage test-plan-review-loop test-validate-citations-budget test-step3-review-cap test-prompt-template-invariants test-token-vendor-scrapers test-decompose-aggregator test-read-result-env test-refresh-run-logs test-ci-behind-count test-check-clean-tree test-rebase-push-no-push-fetch-retry test-git-push test-implement-step2-routing test-implement-cleanup-roundtrip

test-harnesses-7: test-tally-plan-review test-validate-citations test-plan-review-panel test-review-and-fix-step5 test-collect-agent-results test-compose-review-findings test-parse-bootstrap-routing-envelope test-step-7a test-implement-bootstrap test-lint-bash32 test-classify-diff-mode test-redact test-design-step6 test-orchestrator-scope-sync test-launch-claude-ci test-lint-skill-md-flag-signature test-lint-skill-invocations test-step-telemetry-mark test-clarify-state test-lint-codex-exec-auth test-clarify-comment test-phantom-probe-with-warn test-rebase-checkpoint-probe test-lint-readability-preamble test-run-external-agent-args test-launch-claude-review test-launch-cursor-ci test-launch-claude-subprocess test-agent-model-args test-degraded-tools-gate test-render-cost-line-realism test-compute-pr-line-counts test-timing-ledger test-token-claude-source test-timing-report test-launch-codex-exec test-parse-codex-usage test-token-report-dedup test-run-external-agent test-token-tally test-token-cost-per-bucket test-harness-timer test-render-cost-line test-token-ledger test-launch-codex-ci test-token-cost test-token-report test-token-report-summary-format

test-harnesses-8: test-lib-design-round-artifacts test-dispatch-plan-voters test-gh-pr-body-update test-implement-bootstrap-invoke test-revise-plan-with-waterfall test-check-topology-rule-paths test-step0b-router-flag-recovery test-write-final-report test-release-finish test-resolve-repo test-implement-admission test-verify-skill-called test-hook-progress-report test-no-grouped-reuse-guard

test-harnesses-9: test-emit-design-plan-preview test-check-reviewers test-codex-implementer test-launch-codex-drafter test-dispatch-code-voters-retry-codex-success test-design-step3-entry test-pipe-sigpipe-safety test-parse-design-argv test-design-publish test-lint-bare-grep-probe test-implement-fork-env test-references-headers test-render-run-summary-format test-synthesis-subagent

test-harnesses-10: test-gate-b-dedup-plan test-step2-dispatch test-dispatch-plan-review-panel test-dispatch-code-voters-regressions-r1-r2 test-dispatch-code-voters-regressions-r3-codex test-review-and-fix-parsers test-validate-plan-commands test-oos-disposition-gate test-block-submodule test-dispatch-panel-limits test-preflight-args test-analyze test-pause-skill test-implement-anti-halt test-legacy-title-prefix-literals-scope

test-harnesses-11: test-record-plan-review-round-timing test-design-stage-terminal-state test-research-banner test-create-pr test-lib-external-launcher-common test-validate-research-output test-cache-root-validation test-ci-wait-exit-trap test-lib-design-tmpdir test-implement-cleanup-script test-parse-plan-commands test-check-mid-run-dirty-tree test-lib-net test-research-angle-prompts test-lib-submodule-prohibition

test-harnesses-12: test-plan-review-scope-anchor test-collect-findings test-commit-implementation test-dispatch-code-voters-retry-claude test-trailer-helpers test-decompose-file-issues test-review-and-fix-convergence test-issue-query test-prune-nit-findings test-design-postplan-emit test-design-clarify test-render-run-summary test-quick-mode-docs-sync test-subskill-anchors

test-harnesses-13: test-finalize-plan test-design-step2b-drafter test-hook-anti-read-poll test-ci-wait test-dispatch-panel-reuse test-review-and-fix-step5-starting-round test-larch-logs-manifest test-classify-bump test-release-set-version test-review-and-fix-commit-fixes test-review-structure test-refresh-execution-issues test-lint-renderer-substitution-safety test-implement-anti-polling-rule

test-harnesses-14: test-emit-plan test-dispatch-code-voters-edge-and-r3-claude test-step3-orchestrator-fence test-gate-b-apply-mode test-review-and-fix-step5-loop-timing test-sessionstart test-verify-run-log-completeness test-flush-execution-issues test-release-prepare test-ci-failed-jobs test-compose-pr-summary test-file-design-oos test-render-cost-line-callsites test-implement-rebase-macro

test-harnesses-15: test-review-design-step3-loop test-launch-review test-cursor-implementer test-dispatch-code-voters-retry-cursor test-decompose-panel-dispatch test-lib-phase-driver test-scout-plan-archetypes-wrapper test-review-and-fix-check-changes test-review-and-fix-write-rejected test-flush-vendor-failure-diagnostics test-ci-status test-check-stale-plugin

test-harnesses-16: test-run-step3-review test-design-step3-mav test-dispatch-panel-core-dynamic test-implement-preflight test-wait-for-reviewers test-design-driver test-lint-awk-multibyte-regex test-design-pause-resume test-blocker test-gather-branch-context test-append-execution-issue test-implement-fence-shape test-implement-relevant-checks-anti-halt

test-harnesses-17: test-design-step3-state test-emit-tally test-aggregate-findings test-check-plan-size test-lib-failed-agent-stderr-tail test-append-tool-failure test-stall-recovery-report-1 test-audit-runs test-fluff-analysis test-render-final-summary test-redact-tmpdir-paths test-implement-timing-rehydration test-lib-prune-decision test-anti-improvised-wakeup

test-harnesses-18: test-persist-retally-step3-env test-log-phase test-lib-cursor-auth test-finalize-sanity-check test-implement-finalize test-larch-log-write-round test-gather-context test-run-negotiation-round test-step-8-ship test-cache-key-discipline test-check-scope-reduction-marker test-implement-structure test-git-commit-only test-effort-prose

test-harnesses-19: test-plan-review test-review-findings-classification test-dispatch-code-voters-retry-codex-fail-and-fallback test-design-log-publish test-review-and-fix-dispatch test-capture-session-transcript test-resolve-upstream-larch-repo test-design-step0-init test-design-step5c test-materialize-manifest-oos test-render-final-summary-bash32 test-parse-drafter-output test-implement-step8-exit3-first-fixer

test-harnesses-20: test-check-reviewer-failure-threshold test-tally-code-votes test-design-step3-review test-render-review-phase-detail test-design-structure test-design-reentry-guard test-reviewer-prune test-lib-quiet test-review-and-fix-record-timing test-step-18b-final-report test-scrub-submodule-paths test-audit-edit-write test-alias-structure test-anti-halt

test-pipe-sigpipe-safety:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-pipe-sigpipe-safety.sh

test-redact:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_redact.py

test-scrub-log-secrets:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_redact.py

test-redact-tmpdir-paths:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_redact.py

test-reviewer-prune:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-reviewer-prune.sh

test-lib-prune-decision:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-lib-prune-decision.sh

test-append-tool-failure:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_run_logs.py

test-append-execution-issue:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_execution_issues.py -k append_execution_issue

test-validate-research-output:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_research_eval.py

test-validate-citations:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_research.py

test-validate-citations-budget:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_research.py



test-collect-agent-results:
	python3 python/cli.py timing harness-mark --label $@ -- sh -c 'cd python && $(PYTHON) -m pytest -q test_collect_results.py'

test-lib-failed-agent-stderr-tail:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-lib-failed-agent-stderr-tail.sh

test-flush-vendor-failure-diagnostics:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-flush-vendor-failure-diagnostics.sh

test-lib-net:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-lib-net.sh





test-analyze:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_analyze_issues.py -q

test-fluff-analysis:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/fluff-analysis/scripts/test-fluff-analysis.sh

test-fluff-analysis-corpus:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/fluff-analysis/scripts/test-fluff-analysis-corpus.sh

test-fetch-combinable-issues-filter:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_combine_issues.py -q

test-legacy-title-prefix-literals-scope:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-legacy-title-prefix-literals-scope.sh

test-blocker:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_blocker.py -x -q

test-issue-query:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_issue_query.py -x -q

test-implement-admission:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_admission.py -x -q -k 'gate'

test-anti-improvised-wakeup:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-anti-improvised-wakeup.sh

test-audit-runs:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_audit_runs.py -q


test-sessionstart:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-sessionstart-health.sh

test-preflight-args:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_admission.py -x -q -k 'preflight'

test-check-clean-tree:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-check-clean-tree.sh

test-check-main-sync:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-check-main-sync.sh



test-check-scope-reduction-marker:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_dirty_tree.py -x -q -k 'scope_check or scope_marker'

test-plan-review:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_plan_review.py -q

test-plan-review-panel:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_plan_review_panel.py -q

test-plan-review-scope-anchor:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_plan_review.py -q

test-lib-scope-anchor-handoff:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_rendering.py -q

test-clarify-comment:
	cd python && $(PYTHON) -m pytest test_clarify.py

test-clarify-state:
	cd python && $(PYTHON) -m pytest test_clarify.py

test-check-stale-plugin:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-check-stale-plugin.sh


test-cache-root-validation:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-cache-root-validation.sh

test-cache-key-discipline:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-cache-key-discipline.sh

test-finalize-sanity-check:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-finalize-sanity-check.sh


test-audit-edit-write:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-audit-edit-write.sh

test-block-submodule:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-block-submodule-edit.sh


test-deny-edit-write:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-deny-edit-write.sh




test-token-tally:
	cd python && $(PYTHON) -m pytest test_tokens.py -q

test-token-ledger:
	cd python && $(PYTHON) -m pytest test_tokens.py -q

test-token-report:
	cd python && $(PYTHON) -m pytest test_tokens.py -q

test-token-report-dedup:
	cd python && $(PYTHON) -m pytest test_tokens.py -q

test-token-cost-per-bucket:
	cd python && $(PYTHON) -m pytest test_report_tokens_cost.py -q

test-render-cost-line-realism:
	cd python && $(PYTHON) -m pytest test_report_tokens_cost.py -q

test-render-cost-line-callsites:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-render-cost-line-callsites.sh

test-render-run-summary-callsites:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-render-run-summary-callsites.sh

test-render-run-summary-format:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-render-run-summary-format.sh

test-token-report-summary-format:
	cd python && $(PYTHON) -m pytest test_tokens.py -q

test-timing-ledger:
	cd python && $(PYTHON) -m pytest test_timing.py -q

test-review-and-fix-record-timing:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_review_and_fix.py -q -k record_timing

test-review-and-fix-step5-loop-timing:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_review_and_fix.py -q -k loop_timing

test-record-plan-review-round-timing:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_plan_review.py -q

test-step-telemetry-mark:
	cd python && $(PYTHON) -m pytest test_timing.py -q

test-timing-report:
	cd python && $(PYTHON) -m pytest test_timing.py -q

test-token-vendor-scrapers:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-token-vendor-scrapers.sh

test-parse-codex-usage:
	cd python && $(PYTHON) -m pytest test_agents.py -q

test-token-claude-source:
	cd python && $(PYTHON) -m pytest test_tokens.py -q

test-verify-skill-called:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_verify_skill.py


test-hook-anti-read-poll:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-hook-anti-read-poll.sh

test-hook-bg-poll-guard:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-hook-bg-poll-guard.sh

test-hook-progress-report:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-hook-progress-report.sh

test-classify-bump:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_version_bump.py python/test_release.py -q

test-release-prepare:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_release.py -q

test-release-set-version:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_release.py -q

test-release-finish:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_release.py -q

test-promote-release:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_release.py -q


test-ci-wait-exit-trap:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-ci-wait-exit-trap.sh

test-ci-rerun-failed:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-ci-rerun-failed.sh

test-ci-status:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-ci-status.sh

test-ci-behind-count:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-ci-behind-count.sh

test-ci-decide:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-ci-decide.sh

test-merge-pr:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-merge-pr.sh

test-git-push:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-git-push.sh


test-lint-literal-counts:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-lint-literal-counts.sh

test-lint-no-raw-stderr-after-quiet-init:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-lint-no-raw-stderr-after-quiet-init.sh

test-lint-bash32:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-lint-bash32.sh


test-anti-halt:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-anti-halt-banners.sh

test-orchestrator-scope-sync:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-orchestrator-scope-sync.sh


test-alias-structure:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-alias-structure.sh

test-design-structure:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-design-structure.sh

test-design-reentry-guard:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_design_lifecycle.py

test-design-pause-resume:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_design_pause.py

test-pause-skill:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/pause/scripts/test-pause-skill.sh

test-decompose-panel-dispatch:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_decompose.py -q

test-decompose-aggregator:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_decompose.py -q

test-decompose-file-issues:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_decompose.py -q

test-design-step2b-drafter:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/design/scripts/test-design-step2b-drafter.sh

test-design-driver:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_design_lifecycle.py

test-design-clarify:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/design/scripts/test-design-clarify.sh

test-design-publish:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_design_publish.py

test-design-postplan-emit:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_design_postplan.py

test-read-result-env:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-read-result-env.sh

test-parse-design-argv:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_design_argv.py


test-invoke-plan-validator:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_plan_quality.py -k validate_plan

test-file-design-oos:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_design_oos.py

test-design-log-publish:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_design_log_publish_flow.py



test-emit-plan:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_plan_review.py -q

test-gate-b-dedup-plan:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_plan_review.py -q

test-gate-b-apply-mode:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/design/scripts/test-gate-b-apply-mode.sh

test-trailer-helpers:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_plan_quality.py -k optional_trailer

test-emit-design-plan-preview:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_plan_review.py -q
test-check-plan-size:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_plan_quality.py -k check_plan_size

test-auto-fix-plan-commands:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_plan_quality.py -k auto_fix


test-parse-plan-commands:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_plan_quality.py -k parse_plan_commands


test-validate-plan-commands:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_plan_quality.py -k validate_plan

test-tally-plan-review:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_plan_review.py -q

test-findings-classification:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/design/scripts/test-findings-classification.sh

test-review-findings-classification:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_review_tally.py

test-plan-review-loop:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_plan_review.py -q

test-lib-design-round-artifacts:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_plan_review.py -q

test-design-multi-round-integration:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-design-multi-round-integration.sh

test-step3-review-cap:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/design/scripts/test-step3-review-cap.sh

test-persist-retally-step3-env:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_plan_review.py -q

test-run-step3-review:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_plan_review.py -q

test-review-design-step3-loop:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_plan_review.py -q

test-step3-orchestrator-fence:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/design/scripts/test-step3-orchestrator-fence.sh

test-design-step3-mav:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/design/scripts/test-design-step3-mav.sh

test-design-step3-state:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_plan_review.py -q

test-lib-phase-driver:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_design_lifecycle.py

test-finalize-plan:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_plan_review.py -q

test-step0b-router-flag-recovery:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_design_lifecycle.py

test-brainstorm-prompts:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/design/scripts/test-brainstorm-prompts.sh

test-lint-readability-preamble:
	cd python && $(PYTHON) -m pytest test_lint_readability_preamble.py

test-lint-skill-md-flag-signature:
	cd python && $(PYTHON) -m pytest test_lint_skill_md_flag_signature.py

test-lint-codex-exec-auth:
	cd python && $(PYTHON) -m pytest test_lint_codex_exec_auth.py

test-lint-skill-invocations:
	cd python && $(PYTHON) -m pytest test_lint_skill_invocations.py

test-lint-renderer-substitution-safety:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-lint-renderer-substitution-safety.sh


test-lint-bare-grep-probe:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-lint-bare-grep-probe.sh


test-launch-codex-exec:
	cd python && $(PYTHON) -m pytest test_agents.py -q

test-lint-awk-multibyte-regex:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-lint-awk-multibyte-regex.sh

test-scout-plan-archetypes-wrapper:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_plan_scout.py -q

test-dispatch-plan-review-panel:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_plan_review_panel.py -q

test-render-final-summary:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_design_summary.py

test-render-final-summary-bash32:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_design_summary.py

test-implement-rebase-macro:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-implement-rebase-macro.sh

test-rebase-checkpoint-probe:
	bash scripts/test-rebase-checkpoint-probe.sh

test-phantom-probe-with-warn:
	bash scripts/test-phantom-probe-with-warn.sh

test-implement-step2-routing:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-implement-step2-routing.sh

test-rebase-push-keep-on-conflict:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-rebase-push-keep-on-conflict.sh


test-rebase-push-force-lease:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-rebase-push-force-lease.sh

test-rebase-push-fork-mode:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-rebase-push-fork-mode.sh

test-rebase-push-no-push-fetch-retry:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-rebase-push-no-push-fetch-retry.sh

test-implement-structure:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-implement-structure.sh

test-implement-step8-exit3-first-fixer:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-implement-step8-exit3-first-fixer.sh

test-oos-disposition-gate:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_file_oos.py -q -k 'disposition_gate'

test-oos-file-conflict-deps:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_file_oos.py -q -k 'file_conflict_deps'

test-oos-issue-cap:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_file_oos.py -q -k 'issue_cap'

test-plan-adequacy-audit:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-plan-adequacy-audit.sh

test-implement-preflight:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-implement-preflight.sh

test-implement-positional-issue:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-implement-positional-issue.sh

test-implement-fence-shape:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-implement-fence-shape.sh

test-implement-timing-rehydration:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-implement-timing-rehydration.sh

test-implement-cleanup-roundtrip:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-implement-cleanup-roundtrip.sh

test-implement-anti-polling-rule:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-implement-anti-polling-rule.sh

test-implement-relevant-checks-anti-halt:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/implement/scripts/test-implement-relevant-checks-anti-halt.sh

test-implement-anti-halt:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-implement-anti-halt.sh

test-implement-review-token-propagation:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/implement/scripts/test-implement-review-token-propagation.sh

test-run-step2-dispatch:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_implement_dispatch.py -q

test-step2-dispatch:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_implement_dispatch.py -q

# test-stall-recovery-report runs all split sections sequentially (local-dev convenience,
# NOT a test-harnesses prerequisite, see CARVE_OUTS in scripts/test-harness-shards-coverage.sh).
# CI shards use the three section targets below directly.
test-stall-recovery-report: test-stall-recovery-report-1 test-stall-recovery-report-2 test-stall-recovery-report-3

test-stall-recovery-report-1:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_stall_recovery.py -q -k 'retry_policy or normalize_issue or classify or record_attempt'

test-stall-recovery-report-2:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_stall_recovery.py -q -k 'record_escalation or dedup or compose_report or lint or clear_stall or seed_terminal'

test-stall-recovery-report-3:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_stall_recovery.py -q -k 'validate_token or validate_terminal or validate_tier_b'

test-resolve-upstream-larch-repo:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-resolve-upstream-larch-repo.sh

test-file-failure-report-cross-repo:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-file-failure-report-cross-repo.sh

test-step-18b-final-report:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_pr_body.py -q -k step18b

test-cursor-implementer:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_implement_dispatch.py -q

test-codex-implementer:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_implement_dispatch.py -q


test-git-commit-only:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-git-commit-only.sh

test-refresh-run-logs:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_run_logs.py

test-gh-run-logs:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-gh-run-logs.sh

test-ci-failed-jobs:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-ci-failed-jobs.sh

test-ci-wait:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-ci-wait.sh

test-launch-cursor-ci:
	cd python && $(PYTHON) -m pytest test_agents.py -q

test-launch-claude-ci:
	cd python && $(PYTHON) -m pytest test_agents.py -q

test-launch-codex-ci:
	cd python && $(PYTHON) -m pytest test_agents.py -q

test-run-negotiation-round:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_agents.py -q -k negotiation_round

test-run-external-agent-args:
	cd python && $(PYTHON) -m pytest test_agents.py -q

test-quick-mode-docs-sync:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-quick-mode-docs-sync.sh
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-quick-mode-docs-sync.sh --self-test

test-implement-finalize:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_finalize.py -q -k 'teardown or finalize or write_finalize'

test-implement-bootstrap:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_bootstrap.py -x -q -k 'write_base_session_env or tracking or emergency_bypass or resume_plan_tail or forked_plan or run_bootstrap or phase_coder'

test-implement-bootstrap-invoke:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_bootstrap.py -x -q -k 'invoke or cli_bootstrap or step0_wrapper or absorbed_degraded or absorbed_1r or degraded_prompt_required or phantom_stdout'

test-parse-bootstrap-routing-envelope:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_bootstrap.py -x -q -k 'filtered_envelope or parse_routing or routing_parser or degraded_prompt_required or phantom_stdout or absorbed_'

test-flush-execution-issues:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_execution_issues.py -q -k flush

test-step-7a:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_step_7a.py -q

test-step-8-ship:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/implement/scripts/test-step-8-ship.sh

test-post-tracking-issue:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_pr_body.py -q -k post_tracking

test-commit-implementation:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_implement_dispatch.py -q

test-review-and-fix-commit-fixes:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_review_and_fix.py -q -k commit_fixes

test-generate-code-flow-diagram:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_pr_body.py -q -k generate_code_flow

test-refresh-execution-issues:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_execution_issues.py -q -k refresh

test-review-and-fix-write-rejected:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_review_and_fix.py -q -k write_rejected

test-slack-issue-announce:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/implement/scripts/test-slack-issue-announce.sh

test-write-final-report:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_pr_body.py -q -k 'write_final_report or step18b or render_run_summary or post_tracking or generate_code_flow'

test-render-run-summary:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_pr_body.py -q -k 'render_run_summary'

test-render-review-phase-detail:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-render-review-phase-detail.sh

test-token-cost:
	cd python && $(PYTHON) -m pytest test_report_tokens_cost.py -q

lint-retired-scripts:
	@$(PYTHON) -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' \
		|| (printf '%s\n' "ERROR: make lint-retired-scripts requires Python 3.11 or newer (PYTHON=$(PYTHON))" >&2; exit 1)
	$(PYTHON) python/cli.py lint retired-scripts

test-render-cost-line:
	cd python && $(PYTHON) -m pytest test_report_tokens_cost.py -q

test-implement-cleanup-script:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_finalize.py -q -k cleanup

test-harness-shards-coverage:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-harness-shards-coverage.sh
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-harness-shards-coverage.sh --self-test

test-harness-timer:
	cd python && $(PYTHON) -m pytest test_timing.py -q

test-references-headers:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-references-headers.sh

test-research-structure:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-research-structure.sh

test-review-structure:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-review-structure.sh

test-gather-context:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_review_pipeline.py -k gather_context

test-review-core:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_review_pipeline.py -k review_core

test-dispatch-panel-core:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_review_pipeline.py -k dispatch_panel_core

test-dispatch-panel-core-dynamic:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_review_pipeline.py -k 'dispatch_panel_dynamic or pre_scouted_valid_dynamic'

test-dispatch-panel-reuse:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_review_pipeline.py -k dispatch_panel_reuse

test-dispatch-panel-limits:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_review_pipeline.py -k dispatch_panel_limits

test-scout-dynamic-archetypes:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_plan_scout.py -q

test-dispatch-plan-voters:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_plan_review_panel.py -q

test-prompt-template-invariants:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-prompt-template-invariants.sh

test-lib-submodule-prohibition:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-lib-submodule-prohibition.sh

test-collect-findings:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_review_pipeline.py -k collect_findings

test-aggregate-findings:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_review_aggregate.py

test-prune-nit-findings:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/review/scripts/test-prune-nit-findings.sh

test-tally-code-votes:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_review_tally.py

.PHONY: test-check-reviewer-failure-threshold
test-check-reviewer-failure-threshold:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_review_pipeline.py

.PHONY: test-dispatch-code-voters-happy test-dispatch-code-voters-edge-and-r3-claude test-dispatch-code-voters-retry-claude test-dispatch-code-voters-retry-codex-success test-dispatch-code-voters-retry-cursor test-dispatch-code-voters-retry-codex-fail-and-fallback test-dispatch-code-voters-regressions-r1-r2 test-dispatch-code-voters-regressions-r3-codex
test-dispatch-code-voters-happy:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-dispatch-code-voters.sh --section happy

test-dispatch-code-voters-edge-and-r3-claude:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-dispatch-code-voters.sh --section edge-and-r3-claude

test-dispatch-code-voters-regressions-r1-r2:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-dispatch-code-voters.sh --section regressions-r1-r2

test-dispatch-code-voters-regressions-r3-codex:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-dispatch-code-voters.sh --section regressions-r3-codex

test-dispatch-code-voters-retry-claude:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-dispatch-code-voters.sh --section retry-claude

test-dispatch-code-voters-retry-codex-success:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-dispatch-code-voters.sh --section retry-codex-success

test-dispatch-code-voters-retry-cursor:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-dispatch-code-voters.sh --section retry-cursor

test-dispatch-code-voters-retry-codex-fail-and-fallback:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-dispatch-code-voters.sh --section retry-codex-fail-and-fallback

test-emit-tally:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_review_tally.py

test-log-phase:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_review_tally.py

# test-review-and-fix runs all sections sequentially (local-dev convenience, NOT a test-harnesses
# prerequisite — see CARVE_OUTS in scripts/test-harness-shards-coverage.sh). CI uses the four
# section targets below instead: dispatch, convergence, parsers, and step5-starting-round.
test-review-and-fix:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_review_and_fix.py -q

test-review-and-fix-dispatch:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_review_and_fix.py -q -k dispatch

test-review-and-fix-convergence:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_review_and_fix.py -q -k convergence

test-review-and-fix-parsers:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_review_and_fix.py -q -k parsers

test-review-and-fix-step5-starting-round:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_review_and_fix.py -q -k starting_round

test-review-and-fix-step5:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_review_and_fix.py -q -k step5

test-scrub-submodule-paths:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_redact.py


test-run-research-planner:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_research.py

test-render-findings-batch:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_research.py

test-research-banner:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_research.py

test-synthesis-subagent:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/research/scripts/test-synthesis-subagent.sh

test-research-angle-prompts:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/research/scripts/test-research-angle-prompts.sh

test-subskill-anchors:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-subskill-anchors.sh

test-larch-log:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_run_logs.py

test-larch-log-write-round:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_run_logs.py

test-capture-session-transcript:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_run_logs.py

test-verify-run-log-completeness:
	env -u LARCH_VERIFY_MANIFEST python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_run_logs.py

test-larch-logs-manifest:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_run_logs.py

test-larch-logs-batches:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_run_logs.py

test-compose-plan-goals-test:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_plan_quality.py -k compose_plan_goals_test

test-run-step1-plan-log:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_design_step_log.py

test-compose-collector-failure-log:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_review_dispatch.py -k compose_collector_failure_log

test-compose-pr-summary:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_pr_body.py -q -k 'compose_summary'

test-compute-pr-line-counts:
	cd python && $(PYTHON) -m pytest test_tokens.py -q

test-compose-review-findings:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_compose_review.py







test-review-and-fix-check-changes:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_review_and_fix.py -q -k check_changes

test-check-mid-run-dirty-tree:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_dirty_tree.py -x -q -k 'baseline or checkpoint'

test-check-phantom-dirty:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-check-phantom-dirty.sh

test-check-reviewers:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_agents.py -q -k 'check_reviewers or health_gate'

test-degraded-tools-gate:
	cd python && $(PYTHON) -m pytest test_agents.py -q

test-no-grouped-reuse-guard:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-no-grouped-reuse-guard.sh

test-check-topology-rule-paths:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-check-topology-rule-paths.sh

test-external-tool-registry:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-external-tool-registry.sh

test-launch-review:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_launch_review.py

test-lib-external-launcher-common:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-lib-external-launcher-common.sh

test-launch-claude-subprocess:
	cd python && $(PYTHON) -m pytest test_agents.py -q

test-launch-claude-review:
	cd python && $(PYTHON) -m pytest test_agents.py -q

test-launch-claude-drafter:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-launch-claude-drafter.sh

test-launch-codex-drafter:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-launch-codex-drafter.sh

test-parse-drafter-output:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-parse-drafter-output.sh

test-dispatch-with-waterfall:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-dispatch-with-waterfall.sh

test-revise-plan-with-waterfall:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_plan_quality.py -k revise_waterfall

test-agent-model-args:
	cd python && $(PYTHON) -m pytest test_agents.py -q

test-effort-prose:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-effort-prose.sh

test-lib-cursor-auth:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-lib-cursor-auth.sh

test-lib-quiet:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-lib-quiet.sh

test-lib-design-tmpdir:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-lib-design-tmpdir.sh

test-github-remote-repo:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-github-remote-repo.sh

test-implement-fork-env:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_admission.py -x -q -k 'fork_env'

test-create-pr:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-create-pr.sh

test-resolve-repo:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-resolve-repo.sh

test-gh-pr-body-update:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-gh-pr-body-update.sh

test-wait-for-reviewers:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_review_dispatch.py -k wait

test-classify-diff-mode:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_review_dispatch.py -k classify_diff

test-gather-branch-context:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_review_dispatch.py -k gather_branch_context

test-run-external-agent:
	cd python && $(PYTHON) -m pytest test_agents.py -q




test-materialize-manifest-oos:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_file_oos.py -q -k 'materialize_manifest_oos'

lint-mermaid:
	if [ ! -f mermaid-lint/node_modules/.package-lock.json ]; then (cd mermaid-lint && npm ci); fi
	python3 python/cli.py lint mermaid-fences --changed-only
	bash scripts/test-pipe-sigpipe-safety.sh

agent-sync:
	python3 python/cli.py generate check
	python3 scripts/check-topology-rule-paths.py
	python3 python/cli.py lint focus-area-enum

# Opt-in /research evaluation harness (closes #419 under umbrella #413). NOT a
# lint prerequisite — runs ~20 questions × ~30-60s each, costs real tokens.
# Operator instrumentation for prompt-side iteration on /research. See
# docs/linting.md "/research evaluation harness". Pass flags via ARGS=,
# e.g.: `make eval-research ARGS="--id eval-1 --timeout 4200"`. Direct
# `python3 python/cli.py eval research ...` is the documented primary path.
eval-research:
	python3 python/cli.py eval research $(ARGS)

# Standalone offline structural test for the /research eval set + harness
# (closes #419). NOT a `test-harnesses` prerequisite by design — the runtime
# harness it tests is opt-in operator instrumentation explicitly carved out
# from CI. The structural test is itself cheap (no API cost) but kept
# standalone for symmetry. See python/test_research_eval.py.
test-eval-set-structure:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_research_eval.py

# Standalone offline regression harness for the `--baseline` flag handling
# in python/cli.py eval research (closes #441). NOT a `test-harnesses`
# prerequisite — the eval-research surface is opt-in operator
# instrumentation explicitly carved out from CI by repo contract
# (see the `test-eval-set-structure` target above, docs/linting.md,
# python/research_eval.py). Runs offline by PATH-stubbing claude
# so it works on machines without the real binaries.
# See python/test_research_eval.py.
test-eval-research-baseline-flag:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/test_research_eval.py

shellcheck:
	pre-commit run shellcheck --all-files

lint-bash32:
	bash scripts/lint-bash32.sh

lint-gh-body-inline:
	python3 python/cli.py lint gh-body-inline

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

.PHONY: test-design-stage-terminal-state test-design-failure-report test-design-step3-review test-design-step3-entry test-design-step0-init test-design-step5c test-design-step6 test-design-step-validator-autofix

test-design-stage-terminal-state:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/design/scripts/test-design-stage-terminal-state.sh

test-design-failure-report:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/design/scripts/test-design-failure-report.sh

test-design-step3-review:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/design/scripts/test-design-step3-review.sh

test-design-step3-entry:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/design/scripts/test-design-step3-entry.sh

test-design-step0-init:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/design/scripts/test-design-step0-init.sh

test-design-step5c:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/design/scripts/test-design-step5c.sh

test-design-step6:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/design/scripts/test-design-step6.sh

test-design-step-validator-autofix:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/design/scripts/test-design-step-validator-autofix.sh
