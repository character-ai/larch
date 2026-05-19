# Larch Makefile
# Thin wrapper around pre-commit. Linter definitions live in .pre-commit-config.yaml.

.PHONY: lint lint-only test-harnesses test-harnesses-1 test-harnesses-2 test-harnesses-3 test-harnesses-4 test-harnesses-5 test-harnesses-6 test-harnesses-7 test-harnesses-8 test-harnesses-9 test-harnesses-10 test-harnesses-11 test-harnesses-12 test-harnesses-13 test-harnesses-14 test-harnesses-15 test-harnesses-16 shellcheck markdownlint jsonlint actionlint agent-lint agnix gitleaks trufflehog setup test-pipe-sigpipe-safety test-redact test-redact-tmpdir-paths test-append-tool-failure test-validate-research-output test-validate-citations test-validate-citations-budget test-collect-agent-bash32 test-collect-agent-retry test-collect-agent-results test-parse-input test-allocate-candidates test-add-blocked-by test-list-issues test-parse-args test-prepare-description test-parse-prose-blockers test-issue-lifecycle test-fix-issue-bail-detection test-anti-improvised-wakeup test-fix-issue-step-order test-find-lock-issue test-umbrella-handler test-finalize-umbrella test-sentinel-write test-sessionstart test-keepalive-sentinel test-check-clean-tree test-preflight-args test-cleanup-tmpdir test-cache-root-validation test-cache-key-discipline test-finalize-sanity-check test-session-entry-gate test-session-setup-presence-defaults test-session-setup-repo-fallback test-session-env-roundtrip test-audit-edit-write test-block-submodule test-deny-edit-write test-post-scaffold-hints test-render-skill test-show-skill test-render-lane-status test-verify-skill-called test-check-bump-version test-run-checks test-relevant-checks-byte-budget test-relevant-checks-validation test-relevant-checks-helper-failure test-hook-block-skill-relevant-checks test-hook-anti-read-poll test-review-relevant-checks-helper test-lint-fix-loop test-drop-bump-commit test-ci-wait-exit-trap test-ci-rerun-failed test-ci-status test-merge-pr test-apply-bump test-git-push test-lint-skill-invocations test-lint-literal-counts test-lint-no-raw-stderr-after-quiet-init test-mermaid-fragments test-anti-halt test-orchestrator-scope-sync test-alias-target-resolution test-alias-structure test-design-structure test-design-manifest test-design-driver test-classify-issue test-emit-plan test-tally-plan-review test-finalize-plan test-write-run-params test-plan-review-prompt test-implement-rebase-macro test-implement-step2-routing test-rebase-push-keep-on-conflict test-rebase-push-force-lease test-rebase-push-fork-mode test-implement-structure test-implement-timing-rehydration test-implement-cleanup-roundtrip test-implement-anti-polling-rule test-implement-relevant-checks-anti-halt test-implement-anti-halt test-post-design-boundary test-implement-post-design-boundary test-implement-review-token-propagation test-step2-dispatch test-cursor-implementer test-codex-implementer test-refresh-run-logs test-ship-pr test-ci-wait test-launch-cursor-ci test-launch-codex-ci test-launch-claude-subprocess test-launch-claude-review test-dispatch-with-waterfall test-run-external-agent test-run-external-agent-args test-quick-mode-docs-sync test-implement-finalize test-flush-execution-issues test-post-tracking-issue test-commit-implementation test-commit-review-fixes test-generate-code-flow-diagram test-refresh-execution-issues test-write-rejected-findings test-slack-issue-announce test-write-final-report test-implement-cleanup-script test-restore-finalize-state test-harness-shards-coverage test-harness-timer test-references-headers test-render-reviewer-prompt test-render-specialist-prompt test-research-structure test-review-structure test-gather-context test-review-core test-dispatch-panel test-scout-dynamic-archetypes test-dispatch-plan-voters test-collect-findings test-tally-code-votes test-check-reviewer-failure-threshold test-lib-vote-tally test-dispatch-code-voters test-emit-tally test-log-phase test-review-and-fix test-scrub-submodule-paths test-ballot-parse test-tally-vote test-scoreboard test-oos-serialize test-run-research-planner test-render-findings-batch test-research-banner test-synthesis-subagent test-research-angle-prompts test-subskill-anchors test-tracking-issue-write test-larch-log test-capture-session-transcript test-local-cleanup test-larch-logs-manifest test-larch-logs-batches test-compose-plan-goals-test test-write-tally test-compose-collector-failure-log test-tracking-issue-summary test-false-positive-keywords test-round-trip-detect test-tracking-issue-read-sentinel test-compose-review-findings test-token-tally test-token-ledger test-token-report test-timing-ledger test-timing-report test-token-vendor-scrapers test-token-claude-source test-umbrella-helpers test-umbrella-parse-args test-umbrella-blocked-by-issue test-umbrella-emit-output-contract test-umbrella-render-batch-input test-render-umbrella-body test-check-review-changes test-check-mid-run-dirty-tree test-check-phantom-dirty test-check-reviewers test-check-generators test-check-topology-rule-paths test-generate-topology-docs test-external-tool-registry test-agent-model-args test-effort-prose test-launch-review test-lib-cursor-auth test-lib-quiet test-github-remote-repo test-implement-fork-env test-get-issue-context test-create-pr test-resolve-repo test-gh-pr-body-update test-validate-pieces-json test-upgrade-larch test-upgrade-larch-prune smoke-dialectic eval-research test-eval-set-structure test-eval-research-baseline-flag test-body-file-title test-intra-batch-deps test-blocked-by-issue test-oos-file-conflict-deps test-oos-issue-cap test-wait-for-reviewers test-set-up-forked-open-source-repo test-analyze test-rate-assertions test-compose-pr-summary test-compose-architecture-sketch test-run-step5-review test-run-step1-plan-log test-run-step2-dispatch test-persist-post-plan-keys
.PHONY: test-check-reviewer-failure-threshold
.PHONY: test-lib-vote-tally
.PHONY: test-dispatch-code-voters
.PHONY: test-larch-log-write-round
.PHONY: test-upgrade-larch
.PHONY: test-scout-dynamic-archetypes
.PHONY: lint-bash32 test-lint-bash32
# CI splits `lint` into `lint-only` (pre-commit) and `test-harnesses`
# (regression harnesses). `lint` remains the local-dev convenience target
# that runs both, defined in terms of the two split targets to prevent drift.
lint: test-harnesses lint-bash32 lint-only

lint-only:
	pre-commit run --all-files

# Balanced regression-harness shards (closes #1294, #1585, #1911, #2080, #2252, #2262, #2291 — rebalance after
# slow harnesses pushed shards 2/3/5 over the 20s target, resharded to 10, then resharded to 11,
# then to 13 after heavy tests pushed shard wall time over the 40s target, then to 16 after
# shards 12/13 exceeded 50s with test-dispatch-code-voters and test-dispatch-panel). Lists
# are manually adjusted from observed CI timings using LPT bin-packing; see
# docs/linting.md "Refreshing harness shard balance" for the procedure used to regenerate these
# lists when imbalance grows. IMPORTANT: each test-harnesses-N rule below stays on a single
# physical line (no `\` continuations); the drift-detection script
# `scripts/test-harness-shards-coverage.sh` parses these lines literally. New harnesses get
# appended to one shard line.
# Shard-12 leads with the partition-invariant guard so partition bugs surface.
test-harnesses: test-harnesses-1 test-harnesses-2 test-harnesses-3 test-harnesses-4 test-harnesses-5 test-harnesses-6 test-harnesses-7 test-harnesses-8 test-harnesses-9 test-harnesses-10 test-harnesses-11 test-harnesses-12 test-harnesses-13 test-harnesses-14 test-harnesses-15 test-harnesses-16

test-harnesses-1: test-ship-pr

test-harnesses-2: test-dispatch-panel

test-harnesses-3: test-launch-review

test-harnesses-4: test-set-up-forked-open-source-repo

test-harnesses-5: test-dispatch-code-voters test-research-banner test-alias-structure

test-harnesses-6: test-implement-finalize test-token-report test-check-phantom-dirty test-refresh-run-logs test-launch-claude-subprocess test-relevant-checks-validation test-run-research-planner test-session-entry-gate test-compose-plan-goals-test test-commit-review-fixes test-agent-model-args test-lib-vote-tally test-research-structure test-tally-vote test-oos-serialize test-body-file-title

test-harnesses-7: test-review-and-fix test-lint-fix-loop test-ci-wait test-collect-agent-bash32 test-block-submodule test-parse-prose-blockers test-run-step5-review test-launch-claude-review test-render-skill test-cache-root-validation test-lint-no-raw-stderr-after-quiet-init test-design-structure test-get-issue-context test-implement-post-design-boundary test-implement-rebase-macro test-keepalive-sentinel test-blocked-by-issue

test-harnesses-8: test-upgrade-larch test-render-specialist-prompt test-validate-citations-budget test-allocate-candidates test-local-cleanup test-rebase-push-keep-on-conflict test-append-tool-failure test-tracking-issue-read-sentinel test-plan-review-prompt test-slack-issue-announce test-alias-target-resolution test-lint-bash32 test-show-skill test-gh-pr-body-update test-implement-anti-halt test-implement-timing-rehydration test-intra-batch-deps test-anti-improvised-wakeup

test-harnesses-9: test-post-design-boundary test-dispatch-with-waterfall test-sessionstart test-apply-bump test-preflight-args test-check-review-changes test-write-tally test-add-blocked-by test-larch-logs-batches test-tracking-issue-summary test-redact-tmpdir-paths test-session-env-roundtrip test-ci-rerun-failed test-relevant-checks-byte-budget test-compose-pr-summary test-umbrella-emit-output-contract test-emit-tally test-research-angle-prompts test-implement-step2-routing

test-harnesses-10: test-find-lock-issue test-review-core test-run-checks test-validate-citations test-token-claude-source test-validate-research-output test-lint-skill-invocations test-run-external-agent test-umbrella-render-batch-input test-validate-pieces-json test-timing-report test-render-lane-status test-references-headers test-commit-implementation test-implement-structure test-lib-cursor-auth test-external-tool-registry test-anti-halt test-implement-anti-polling-rule test-implement-cleanup-roundtrip

test-harnesses-11: test-gather-context test-codex-implementer test-larch-log test-drop-bump-commit test-check-mid-run-dirty-tree test-redact test-mermaid-fragments test-larch-log-write-round test-flush-execution-issues test-run-step1-plan-log test-classify-issue test-post-tracking-issue test-round-trip-detect test-run-step2-dispatch test-log-phase test-larch-logs-manifest test-write-run-params test-orchestrator-scope-sync test-fix-issue-step-order

# Shard-12 leads with the partition-invariant guard so partition bugs surface.
test-harnesses-12: test-harness-shards-coverage test-merge-pr test-collect-findings test-upgrade-larch-prune test-capture-session-transcript test-wait-for-reviewers test-check-generators test-check-reviewer-failure-threshold test-umbrella-parse-args test-scrub-submodule-paths test-list-issues test-restore-finalize-state test-generate-code-flow-diagram test-write-rejected-findings test-cache-key-discipline test-compose-collector-failure-log test-parse-args test-run-external-agent-args test-finalize-plan test-ballot-parse test-effort-prose

test-harnesses-13: test-oos-file-conflict-deps test-umbrella-handler test-umbrella-helpers test-oos-issue-cap test-render-findings-batch test-create-pr test-lint-literal-counts test-verify-skill-called test-implement-review-token-propagation test-token-ledger test-render-umbrella-body test-relevant-checks-helper-failure test-deny-edit-write test-refresh-execution-issues test-sentinel-write test-design-driver test-launch-codex-ci test-scoreboard test-fix-issue-bail-detection

test-harnesses-14: test-dispatch-plan-voters test-timing-ledger test-prepare-description test-finalize-umbrella test-tally-plan-review test-token-vendor-scrapers test-pipe-sigpipe-safety test-check-topology-rule-paths test-analyze test-persist-post-plan-keys test-ci-status test-resolve-repo test-tracking-issue-write test-compose-architecture-sketch test-false-positive-keywords test-launch-cursor-ci test-audit-edit-write test-github-remote-repo test-synthesis-subagent test-implement-relevant-checks-anti-halt

test-harnesses-15: test-collect-agent-retry test-issue-lifecycle test-collect-agent-results test-tally-code-votes test-harness-timer test-generate-topology-docs test-lib-quiet test-render-reviewer-prompt test-design-manifest test-rebase-push-fork-mode test-implement-fork-env test-check-clean-tree test-token-tally test-write-final-report test-implement-cleanup-script test-emit-plan test-review-structure test-post-scaffold-hints test-cleanup-tmpdir

test-harnesses-16: test-cursor-implementer test-step2-dispatch test-hook-block-skill-relevant-checks test-scout-dynamic-archetypes test-check-bump-version test-finalize-sanity-check test-ci-wait-exit-trap test-hook-anti-read-poll test-parse-input test-session-setup-repo-fallback test-compose-review-findings test-git-push test-session-setup-presence-defaults test-subskill-anchors test-rebase-push-force-lease test-quick-mode-docs-sync test-rate-assertions test-check-reviewers test-umbrella-blocked-by-issue test-review-relevant-checks-helper

test-pipe-sigpipe-safety:
	bash scripts/harness-timer.sh $@ bash scripts/test-pipe-sigpipe-safety.sh

test-redact:
	bash scripts/harness-timer.sh $@ bash scripts/test-redact-secrets.sh

test-redact-tmpdir-paths:
	bash scripts/harness-timer.sh $@ bash scripts/test-redact-tmpdir-paths.sh

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

test-rate-assertions:
	bash scripts/harness-timer.sh $@ bash skills/report-tokens/scripts/test-rate-assertions.sh

test-parse-args:
	bash scripts/harness-timer.sh $@ bash scripts/test-parse-args.sh

test-prepare-description:
	bash scripts/harness-timer.sh $@ bash scripts/test-prepare-description.sh

test-parse-prose-blockers:
	bash scripts/harness-timer.sh $@ bash skills/fix-issue/scripts/test-parse-prose-blockers.sh

test-issue-lifecycle:
	bash scripts/harness-timer.sh $@ bash skills/fix-issue/scripts/test-issue-lifecycle.sh

test-fix-issue-bail-detection:
	bash scripts/harness-timer.sh $@ bash skills/fix-issue/scripts/test-fix-issue-bail-detection.sh

test-anti-improvised-wakeup:
	bash scripts/harness-timer.sh $@ bash scripts/test-anti-improvised-wakeup.sh

test-fix-issue-step-order:
	bash scripts/harness-timer.sh $@ bash skills/fix-issue/scripts/test-fix-issue-step-order.sh

test-find-lock-issue:
	bash scripts/harness-timer.sh $@ bash skills/fix-issue/scripts/test-find-lock-issue.sh

test-umbrella-handler:
	bash scripts/harness-timer.sh $@ bash skills/fix-issue/scripts/test-umbrella-handler.sh

test-finalize-umbrella:
	bash scripts/harness-timer.sh $@ bash skills/fix-issue/scripts/test-finalize-umbrella.sh

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

test-cleanup-tmpdir:
	bash scripts/harness-timer.sh $@ bash scripts/test-cleanup-tmpdir.sh

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

test-deny-edit-write:
	bash scripts/harness-timer.sh $@ bash scripts/test-deny-edit-write.sh

test-post-scaffold-hints:
	bash scripts/harness-timer.sh $@ bash scripts/test-post-scaffold-hints.sh

test-render-skill:
	bash scripts/harness-timer.sh $@ bash skills/create-skill/scripts/test-render-skill-md.sh
	bash scripts/harness-timer.sh $@ bash skills/show-skill/scripts/test-show-skill.sh

test-show-skill:
	bash scripts/harness-timer.sh $@ bash skills/show-skill/scripts/test-show-skill.sh

test-render-lane-status:
	bash scripts/harness-timer.sh $@ bash scripts/test-render-lane-status.sh

test-token-tally:
	bash scripts/harness-timer.sh $@ bash scripts/test-token-tally.sh

test-token-ledger:
	bash scripts/harness-timer.sh $@ bash scripts/test-token-ledger.sh

test-token-report:
	bash scripts/harness-timer.sh $@ bash scripts/test-token-report.sh

test-timing-ledger:
	bash scripts/harness-timer.sh $@ bash scripts/test-timing-ledger.sh

test-timing-report:
	bash scripts/harness-timer.sh $@ bash scripts/test-timing-report.sh

test-token-vendor-scrapers:
	bash scripts/harness-timer.sh $@ bash scripts/test-token-vendor-scrapers.sh

test-token-claude-source:
	bash scripts/harness-timer.sh $@ bash scripts/test-token-claude-source.sh

test-verify-skill-called:
	bash scripts/harness-timer.sh $@ bash scripts/test-verify-skill-called.sh

test-check-bump-version:
	bash scripts/harness-timer.sh $@ bash scripts/test-check-bump-version.sh

test-run-checks:
	bash scripts/harness-timer.sh $@ bash .claude/skills/relevant-checks/scripts/test-run-checks.sh

test-relevant-checks-byte-budget:
	bash scripts/harness-timer.sh $@ bash scripts/test-relevant-checks-byte-budget.sh

test-relevant-checks-validation:
	bash scripts/harness-timer.sh $@ bash scripts/test-relevant-checks-validation.sh

test-relevant-checks-helper-failure:
	bash scripts/harness-timer.sh $@ bash scripts/test-relevant-checks-helper-failure.sh

test-hook-block-skill-relevant-checks:
	bash scripts/harness-timer.sh $@ bash scripts/test-hook-block-skill-relevant-checks.sh

test-hook-anti-read-poll:
	bash scripts/harness-timer.sh $@ bash scripts/test-hook-anti-read-poll.sh

test-review-relevant-checks-helper:
	bash scripts/harness-timer.sh $@ bash scripts/test-review-relevant-checks-helper.sh

test-lint-fix-loop:
	bash scripts/harness-timer.sh $@ bash scripts/test-lint-fix-loop.sh

test-drop-bump-commit:
	bash scripts/harness-timer.sh $@ bash scripts/test-drop-bump-commit.sh

test-ci-wait-exit-trap:
	bash scripts/harness-timer.sh $@ bash scripts/test-ci-wait-exit-trap.sh

test-ci-rerun-failed:
	bash scripts/harness-timer.sh $@ bash scripts/test-ci-rerun-failed.sh

test-ci-status:
	bash scripts/harness-timer.sh $@ bash scripts/test-ci-status.sh

test-merge-pr:
	bash scripts/harness-timer.sh $@ bash scripts/test-merge-pr.sh

test-apply-bump:
	bash scripts/harness-timer.sh $@ bash scripts/test-apply-bump.sh

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

test-design-manifest:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-design-manifest.sh

test-design-driver:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-design-driver.sh

test-classify-issue:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-classify-issue.sh

test-emit-plan:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-emit-plan.sh

test-tally-plan-review:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-tally-plan-review.sh

test-finalize-plan:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-finalize-plan.sh

test-write-run-params:
	bash scripts/harness-timer.sh $@ bash scripts/test-write-run-params.sh
test-plan-review-prompt:
	bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-plan-review-prompt.sh

test-implement-rebase-macro:
	bash scripts/harness-timer.sh $@ bash scripts/test-implement-rebase-macro.sh

test-implement-step2-routing:
	bash scripts/harness-timer.sh $@ bash scripts/test-implement-step2-routing.sh

test-rebase-push-keep-on-conflict:
	bash scripts/harness-timer.sh $@ bash scripts/test-rebase-push-keep-on-conflict.sh

test-rebase-push-force-lease:
	bash scripts/harness-timer.sh $@ bash scripts/test-rebase-push-force-lease.sh

test-rebase-push-fork-mode:
	bash scripts/harness-timer.sh $@ bash scripts/test-rebase-push-fork-mode.sh

test-implement-structure:
	bash scripts/harness-timer.sh $@ bash scripts/test-implement-structure.sh

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

test-post-design-boundary:
	bash scripts/harness-timer.sh $@ bash skills/implement/scripts/test-post-design-boundary.sh

test-implement-post-design-boundary: test-post-design-boundary
	bash scripts/harness-timer.sh $@ bash scripts/test-implement-post-design-boundary.sh

test-implement-review-token-propagation:
	bash scripts/harness-timer.sh $@ bash skills/implement/scripts/test-implement-review-token-propagation.sh

test-run-step2-dispatch:
	bash scripts/harness-timer.sh $@ bash skills/implement/scripts/test-run-step2-dispatch.sh

test-step2-dispatch:
	bash scripts/harness-timer.sh $@ bash skills/implement/scripts/test-step2-dispatch.sh

test-cursor-implementer:
	bash scripts/harness-timer.sh $@ bash skills/implement/scripts/test-cursor-implementer.sh

test-codex-implementer:
	bash scripts/harness-timer.sh $@ bash skills/implement/scripts/test-codex-implementer.sh

test-refresh-run-logs:
	bash scripts/harness-timer.sh $@ bash scripts/test-refresh-run-logs.sh

test-ship-pr:
	bash scripts/harness-timer.sh $@ bash scripts/test-ship-pr.sh

test-ci-wait:
	bash scripts/harness-timer.sh $@ bash scripts/test-ci-wait.sh

test-launch-cursor-ci:
	bash scripts/harness-timer.sh $@ bash scripts/test-launch-cursor-ci.sh

test-launch-codex-ci:
	bash scripts/harness-timer.sh $@ bash scripts/test-launch-codex-ci.sh

test-run-external-agent-args:
	bash scripts/harness-timer.sh $@ bash scripts/test-run-external-agent-args.sh

test-quick-mode-docs-sync:
	bash scripts/harness-timer.sh $@ bash scripts/test-quick-mode-docs-sync.sh
	bash scripts/harness-timer.sh $@ bash scripts/test-quick-mode-docs-sync.sh --self-test

test-implement-finalize:
	bash scripts/harness-timer.sh $@ bash scripts/test-implement-finalize.sh

test-flush-execution-issues:
	bash scripts/harness-timer.sh $@ bash skills/implement/scripts/test-flush-execution-issues.sh

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

test-research-structure:
	bash scripts/harness-timer.sh $@ bash scripts/test-research-structure.sh

test-review-structure:
	bash scripts/harness-timer.sh $@ bash scripts/test-review-structure.sh

test-gather-context:
	bash scripts/harness-timer.sh $@ bash skills/review/scripts/test-gather-context.sh

test-review-core:
	bash scripts/harness-timer.sh $@ bash skills/review/scripts/test-review-core.sh

test-dispatch-panel:
	bash scripts/harness-timer.sh $@ bash skills/review/scripts/test-dispatch-panel.sh

test-scout-dynamic-archetypes:
	bash scripts/harness-timer.sh $@ bash scripts/test-scout-dynamic-archetypes.sh

test-dispatch-plan-voters:
	bash scripts/harness-timer.sh $@ bash scripts/test-dispatch-plan-voters.sh

test-collect-findings:
	bash scripts/harness-timer.sh $@ bash skills/review/scripts/test-collect-findings.sh

test-tally-code-votes:
	bash scripts/harness-timer.sh $@ bash skills/review/scripts/test-tally-code-votes.sh

.PHONY: test-check-reviewer-failure-threshold
test-check-reviewer-failure-threshold:
	bash scripts/harness-timer.sh $@ bash skills/review/scripts/test-check-reviewer-failure-threshold.sh

.PHONY: test-lib-vote-tally
test-lib-vote-tally:
	bash scripts/harness-timer.sh $@ bash scripts/test-lib-vote-tally.sh

.PHONY: test-dispatch-code-voters
test-dispatch-code-voters:
	bash scripts/harness-timer.sh $@ bash scripts/test-dispatch-code-voters.sh

test-emit-tally:
	bash scripts/harness-timer.sh $@ bash skills/review/scripts/test-emit-tally.sh

test-log-phase:
	bash scripts/harness-timer.sh $@ bash skills/review/scripts/test-log-phase.sh

test-review-and-fix:
	bash scripts/harness-timer.sh $@ bash skills/review-and-fix/scripts/test-review-and-fix.sh

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

test-persist-post-plan-keys:
	bash scripts/harness-timer.sh $@ bash scripts/test-persist-post-plan-keys.sh

test-write-tally:
	bash scripts/harness-timer.sh $@ bash scripts/test-write-tally.sh

test-compose-collector-failure-log:
	bash scripts/harness-timer.sh $@ bash scripts/test-compose-collector-failure-log.sh

test-compose-pr-summary:
	bash scripts/harness-timer.sh $@ bash scripts/test-compose-pr-summary.sh

test-compose-architecture-sketch:
	bash scripts/harness-timer.sh $@ bash scripts/test-compose-architecture-sketch.sh

test-tracking-issue-summary:
	bash scripts/harness-timer.sh $@ bash scripts/test-tracking-issue-summary.sh

test-false-positive-keywords:
	bash scripts/harness-timer.sh $@ bash scripts/test-false-positive-keywords.sh

test-round-trip-detect:
	bash scripts/harness-timer.sh $@ bash scripts/test-round-trip-detect.sh

test-tracking-issue-read-sentinel:
	bash scripts/harness-timer.sh $@ bash scripts/test-tracking-issue-read-sentinel.sh

test-compose-review-findings:
	bash scripts/harness-timer.sh $@ bash scripts/test-compose-review-findings.sh

test-umbrella-helpers:
	bash scripts/harness-timer.sh $@ bash skills/umbrella/scripts/test-helpers.sh

test-umbrella-parse-args:
	bash scripts/harness-timer.sh $@ bash skills/umbrella/scripts/test-umbrella-parse-args.sh

test-umbrella-blocked-by-issue:
	bash scripts/harness-timer.sh $@ bash skills/umbrella/scripts/test-umbrella-blocked-by-issue.sh

test-umbrella-emit-output-contract:
	bash scripts/harness-timer.sh $@ bash skills/umbrella/scripts/test-umbrella-emit-output-contract.sh

test-umbrella-render-batch-input:
	bash scripts/harness-timer.sh $@ bash skills/umbrella/scripts/test-render-batch-input.sh

test-render-umbrella-body:
	bash scripts/harness-timer.sh $@ bash skills/umbrella/scripts/test-render-umbrella-body.sh

test-check-review-changes:
	bash scripts/harness-timer.sh $@ bash skills/implement/scripts/test-check-review-changes.sh

test-check-mid-run-dirty-tree:
	bash scripts/harness-timer.sh $@ bash scripts/test-check-mid-run-dirty-tree.sh

test-check-phantom-dirty:
	bash scripts/harness-timer.sh $@ bash scripts/test-check-phantom-dirty.sh

test-check-reviewers:
	bash scripts/harness-timer.sh $@ bash scripts/test-check-reviewers.sh

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

test-launch-claude-subprocess:
	bash scripts/harness-timer.sh $@ bash scripts/test-launch-claude-subprocess.sh

test-launch-claude-review:
	bash scripts/harness-timer.sh $@ bash scripts/test-launch-claude-review.sh

test-dispatch-with-waterfall:
	bash scripts/harness-timer.sh $@ bash scripts/test-dispatch-with-waterfall.sh

test-agent-model-args:
	bash scripts/harness-timer.sh $@ bash scripts/test-agent-model-args.sh

test-effort-prose:
	bash scripts/harness-timer.sh $@ bash scripts/test-effort-prose.sh

test-lib-cursor-auth:
	bash scripts/harness-timer.sh $@ bash scripts/test-lib-cursor-auth.sh

test-lib-quiet:
	bash scripts/harness-timer.sh $@ bash scripts/test-lib-quiet.sh

test-github-remote-repo:
	bash scripts/harness-timer.sh $@ bash scripts/test-github-remote-repo.sh

test-implement-fork-env:
	bash scripts/harness-timer.sh $@ bash scripts/test-implement-fork-env.sh

test-get-issue-context:
	bash scripts/harness-timer.sh $@ bash scripts/test-get-issue-context.sh

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

test-validate-pieces-json:
	bash scripts/harness-timer.sh $@ bash skills/umbrella/scripts/test-validate-pieces-json.sh

test-body-file-title:
	bash scripts/harness-timer.sh $@ bash skills/issue/scripts/test-body-file-title.sh

test-upgrade-larch-prune:
	bash scripts/harness-timer.sh $@ bash skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh

test-upgrade-larch:
	bash scripts/harness-timer.sh $@ bash skills/upgrade-larch/scripts/test-upgrade-larch.sh

test-intra-batch-deps:
	bash scripts/harness-timer.sh $@ bash skills/issue/scripts/test-intra-batch-deps.sh

test-oos-file-conflict-deps:
	bash scripts/harness-timer.sh $@ bash skills/implement/scripts/test-oos-file-conflict-deps.sh

test-upgrade-larch:
	bash scripts/harness-timer.sh $@ bash skills/upgrade-larch/scripts/test-upgrade-larch.sh

test-oos-issue-cap:
	bash scripts/harness-timer.sh $@ bash skills/implement/scripts/test-oos-issue-cap.sh

test-blocked-by-issue:
	bash scripts/harness-timer.sh $@ bash skills/issue/scripts/test-blocked-by-issue.sh

smoke-dialectic:
	bash scripts/dialectic-smoke-test.sh

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
