# Larch Makefile
# Thin wrapper around pre-commit. Linter definitions live in .pre-commit-config.yaml.

.PHONY: lint lint-only test-harnesses test-harnesses-1 test-harnesses-2 test-harnesses-3 test-harnesses-4 test-harnesses-5 test-harnesses-6 test-harnesses-7 shellcheck markdownlint jsonlint actionlint agent-lint agnix gitleaks trufflehog setup test-pipe-sigpipe-safety test-redact test-redact-tmpdir-paths test-validate-research-output test-validate-citations test-validate-citations-budget test-collect-agent-bash32 test-collect-agent-retry test-parse-input test-allocate-candidates test-add-blocked-by test-list-issues test-parse-args test-prepare-description test-parse-prose-blockers test-issue-lifecycle test-fix-issue-bail-detection test-anti-improvised-wakeup test-fix-issue-step-order test-find-lock-issue test-umbrella-handler test-finalize-umbrella test-sentinel-write test-sessionstart test-keepalive-sentinel test-check-clean-tree test-preflight-args test-cleanup-tmpdir test-cache-root-validation test-finalize-sanity-check test-session-entry-gate test-session-setup-health-defaults test-session-setup-repo-fallback test-session-env-roundtrip test-audit-edit-write test-block-submodule test-deny-edit-write test-post-scaffold-hints test-render-skill test-show-skill test-render-lane-status test-verify-skill-called test-check-bump-version test-run-checks test-relevant-checks-byte-budget test-relevant-checks-validation test-relevant-checks-helper-failure test-hook-block-skill-relevant-checks test-review-relevant-checks-helper test-drop-bump-commit test-ci-wait-exit-trap test-ci-status test-merge-pr test-apply-bump test-lint-skill-invocations test-lint-literal-counts test-mermaid-fragments test-anti-halt test-orchestrator-scope-sync test-alias-target-resolution test-alias-structure test-design-structure test-design-manifest test-write-run-params test-implement-rebase-macro test-rebase-push-keep-on-conflict test-implement-structure test-implement-cleanup-roundtrip test-implement-anti-polling-rule test-implement-relevant-checks-anti-halt test-implement-anti-halt test-post-design-boundary test-implement-post-design-boundary test-implement-review-token-propagation test-step2-dispatch test-cursor-implementer test-gemini-implementer test-codex-implementer test-run-external-agent test-run-external-agent-args test-quick-mode-docs-sync test-implement-finalize test-harness-shards-coverage test-references-headers test-render-reviewer-prompt test-render-specialist-prompt test-research-structure test-review-structure test-run-research-planner test-render-findings-batch test-research-banner test-synthesis-subagent test-research-angle-prompts test-subskill-anchors test-tracking-issue-write test-false-positive-keywords test-round-trip-detect test-tracking-issue-read-sentinel test-assemble-anchor test-refresh-anchor test-hydrate-anchor test-compose-review-findings test-token-tally test-token-ledger test-token-report test-timing-ledger test-timing-report test-token-vendor-scrapers test-token-claude-source test-umbrella-helpers test-umbrella-parse-args test-umbrella-blocked-by-issue test-umbrella-emit-output-contract test-umbrella-render-batch-input test-render-umbrella-body test-check-review-changes test-check-mid-run-dirty-tree test-check-phantom-dirty test-check-reviewers test-check-generators test-check-topology-rule-paths test-generate-topology-docs test-external-tool-registry test-agent-model-args test-effort-prose test-launch-review test-lib-cursor-auth test-github-remote-repo test-implement-fork-env test-get-issue-context test-create-pr test-resolve-repo test-gh-pr-body-update test-validate-pieces-json smoke-dialectic eval-research test-eval-set-structure test-eval-research-baseline-flag test-body-file-title test-intra-batch-deps test-blocked-by-issue test-oos-file-conflict-deps test-oos-issue-cap test-wait-for-reviewers test-set-up-forked-open-source-repo test-analyze
.PHONY: lint lint-only test-harnesses test-harnesses-1 test-harnesses-2 test-harnesses-3 test-harnesses-4 test-harnesses-5 test-harnesses-6 test-harnesses-7 shellcheck markdownlint jsonlint actionlint agent-lint agnix gitleaks trufflehog setup test-pipe-sigpipe-safety test-redact test-redact-tmpdir-paths test-validate-research-output test-validate-citations test-validate-citations-budget test-collect-agent-bash32 test-collect-agent-retry test-parse-input test-allocate-candidates test-add-blocked-by test-list-issues test-parse-args test-prepare-description test-parse-prose-blockers test-issue-lifecycle test-fix-issue-bail-detection test-anti-improvised-wakeup test-fix-issue-step-order test-find-lock-issue test-umbrella-handler test-finalize-umbrella test-sentinel-write test-sessionstart test-keepalive-sentinel test-check-clean-tree test-preflight-args test-cleanup-tmpdir test-cache-root-validation test-finalize-sanity-check test-session-entry-gate test-session-setup-health-defaults test-session-setup-repo-fallback test-session-env-roundtrip test-audit-edit-write test-block-submodule test-deny-edit-write test-post-scaffold-hints test-render-skill test-show-skill test-render-lane-status test-verify-skill-called test-check-bump-version test-run-checks test-relevant-checks-byte-budget test-relevant-checks-validation test-relevant-checks-helper-failure test-hook-block-skill-relevant-checks test-review-relevant-checks-helper test-drop-bump-commit test-ci-wait-exit-trap test-ci-status test-merge-pr test-apply-bump test-lint-skill-invocations test-lint-literal-counts test-mermaid-fragments test-anti-halt test-orchestrator-scope-sync test-alias-target-resolution test-alias-structure test-design-structure test-design-manifest test-plan-review-prompt test-implement-rebase-macro test-rebase-push-keep-on-conflict test-implement-structure test-implement-cleanup-roundtrip test-implement-anti-polling-rule test-implement-relevant-checks-anti-halt test-implement-anti-halt test-post-design-boundary test-implement-post-design-boundary test-implement-review-token-propagation test-step2-dispatch test-cursor-implementer test-gemini-implementer test-codex-implementer test-run-external-agent test-run-external-agent-args test-quick-mode-docs-sync test-implement-finalize test-harness-shards-coverage test-references-headers test-render-reviewer-prompt test-render-specialist-prompt test-research-structure test-review-structure test-run-research-planner test-render-findings-batch test-research-banner test-synthesis-subagent test-research-angle-prompts test-subskill-anchors test-tracking-issue-write test-false-positive-keywords test-round-trip-detect test-tracking-issue-read-sentinel test-assemble-anchor test-refresh-anchor test-hydrate-anchor test-compose-review-findings test-token-tally test-token-ledger test-token-report test-timing-ledger test-timing-report test-token-vendor-scrapers test-token-claude-source test-umbrella-helpers test-umbrella-parse-args test-umbrella-blocked-by-issue test-umbrella-emit-output-contract test-umbrella-render-batch-input test-render-umbrella-body test-check-review-changes test-check-mid-run-dirty-tree test-check-phantom-dirty test-check-reviewers test-check-generators test-check-topology-rule-paths test-generate-topology-docs test-external-tool-registry test-agent-model-args test-effort-prose test-launch-review test-lib-cursor-auth test-github-remote-repo test-implement-fork-env test-get-issue-context test-create-pr test-resolve-repo test-gh-pr-body-update test-validate-pieces-json smoke-dialectic eval-research test-eval-set-structure test-eval-research-baseline-flag test-body-file-title test-intra-batch-deps test-blocked-by-issue test-oos-file-conflict-deps test-oos-issue-cap test-wait-for-reviewers test-set-up-forked-open-source-repo test-analyze

# CI splits `lint` into `lint-only` (pre-commit) and `test-harnesses`
# (regression harnesses). `lint` remains the local-dev convenience target
# that runs both, defined in terms of the two split targets to prevent drift.
lint: test-harnesses lint-only

lint-only:
	pre-commit run --all-files

# Balanced regression-harness shards (closes #1294, #1585 — rebalance after
# slow harnesses pushed shards 2/3/5 over the 20s target). Lists are manually
# adjusted from observed CI timings; see docs/linting.md "Refreshing harness
# shard balance" for the procedure used to regenerate these lists when
# imbalance grows. The test-validate-citations harness remains the dominant
# wall-clock harness; its real-time budget-exhaustion tests live in
# test-validate-citations-budget so their sleeps can be billed to a different
# shard. IMPORTANT: each test-harnesses-N rule below stays on a single physical
# line (no `\` continuations); the drift-detection script
# `scripts/test-harness-shards-coverage.sh` parses these lines literally.
# New harnesses get appended to one shard line.
test-harnesses: test-harnesses-1 test-harnesses-2 test-harnesses-3 test-harnesses-4 test-harnesses-5 test-harnesses-6 test-harnesses-7

test-harnesses-1: test-oos-file-conflict-deps test-preflight-args test-collect-agent-retry test-ci-wait-exit-trap test-parse-prose-blockers test-step2-dispatch test-design-manifest test-write-run-params test-render-umbrella-body test-render-lane-status test-hydrate-anchor test-design-structure test-run-external-agent-args test-post-scaffold-hints test-implement-anti-polling-rule test-implement-anti-halt test-generate-topology-docs test-anti-improvised-wakeup test-session-env-roundtrip
test-harnesses-1: test-oos-file-conflict-deps test-preflight-args test-collect-agent-retry test-ci-wait-exit-trap test-parse-prose-blockers test-step2-dispatch test-design-manifest test-plan-review-prompt test-render-umbrella-body test-render-lane-status test-hydrate-anchor test-design-structure test-run-external-agent-args test-post-scaffold-hints test-implement-anti-polling-rule test-implement-anti-halt test-generate-topology-docs test-anti-improvised-wakeup test-session-env-roundtrip

test-harnesses-2: test-check-reviewers test-oos-issue-cap test-finalize-umbrella test-block-submodule test-refresh-anchor test-gemini-implementer test-launch-review test-agent-model-args test-effort-prose test-lib-cursor-auth test-list-issues test-run-research-planner test-false-positive-keywords test-quick-mode-docs-sync test-external-tool-registry test-research-banner test-anti-halt test-intra-batch-deps test-apply-bump

test-harnesses-3: test-implement-finalize test-validate-citations test-drop-bump-commit test-sessionstart test-check-clean-tree test-check-review-changes test-check-mid-run-dirty-tree test-check-phantom-dirty test-add-blocked-by test-codex-implementer test-umbrella-render-batch-input test-validate-pieces-json test-deny-edit-write test-umbrella-emit-output-contract test-render-skill test-show-skill test-audit-edit-write test-parse-args test-fix-issue-step-order test-body-file-title test-round-trip-detect test-compose-review-findings

test-harnesses-4: test-umbrella-helpers test-tracking-issue-write test-validate-citations-budget test-check-generators test-check-topology-rule-paths test-merge-pr test-redact test-umbrella-parse-args test-prepare-description test-references-headers test-tracking-issue-read-sentinel test-token-tally test-token-ledger test-token-report test-timing-ledger test-timing-report test-token-vendor-scrapers test-token-claude-source test-sentinel-write test-review-structure test-fix-issue-bail-detection test-blocked-by-issue test-lint-skill-invocations

test-harnesses-5: test-find-lock-issue test-issue-lifecycle test-render-findings-batch test-lint-literal-counts test-verify-skill-called test-validate-research-output test-parse-input test-render-reviewer-prompt test-run-external-agent test-render-specialist-prompt test-subskill-anchors test-analyze test-post-design-boundary test-implement-post-design-boundary test-implement-rebase-macro test-orchestrator-scope-sync test-synthesis-subagent

test-harnesses-6: test-umbrella-handler test-run-checks test-relevant-checks-byte-budget test-relevant-checks-validation test-relevant-checks-helper-failure test-hook-block-skill-relevant-checks test-review-relevant-checks-helper test-check-bump-version test-allocate-candidates test-rebase-push-keep-on-conflict test-cursor-implementer test-collect-agent-bash32 test-assemble-anchor test-mermaid-fragments test-implement-structure test-implement-cleanup-roundtrip test-implement-review-token-propagation test-implement-relevant-checks-anti-halt test-wait-for-reviewers test-alias-target-resolution

# Shard-7 leads with the partition-invariant guard so partition bugs surface.
test-harnesses-7: test-harness-shards-coverage test-session-entry-gate test-research-structure test-research-angle-prompts test-alias-structure test-umbrella-blocked-by-issue test-cleanup-tmpdir test-session-setup-health-defaults test-session-setup-repo-fallback test-redact-tmpdir-paths test-keepalive-sentinel test-cache-root-validation test-finalize-sanity-check test-ci-status test-github-remote-repo test-implement-fork-env test-get-issue-context test-create-pr test-resolve-repo test-gh-pr-body-update test-set-up-forked-open-source-repo test-pipe-sigpipe-safety

test-pipe-sigpipe-safety:
	bash scripts/test-pipe-sigpipe-safety.sh

test-redact:
	bash scripts/test-redact-secrets.sh

test-redact-tmpdir-paths:
	bash scripts/test-redact-tmpdir-paths.sh

test-validate-research-output:
	bash scripts/test-validate-research-output.sh

test-validate-citations:
	bash skills/research/scripts/test-validate-citations.sh

test-validate-citations-budget:
	bash skills/research/scripts/test-validate-citations-budget.sh

test-collect-agent-bash32:
	bash scripts/test-collect-agent-bash32.sh

test-collect-agent-retry:
	bash scripts/test-collect-agent-retry.sh

test-parse-input:
	bash skills/issue/scripts/test-parse-input.sh

test-allocate-candidates:
	bash skills/issue/scripts/test-allocate-candidates.sh

test-add-blocked-by:
	bash skills/issue/scripts/test-add-blocked-by.sh

test-list-issues:
	bash skills/issue/scripts/test-list-issues.sh

test-analyze:
	bash .claude/skills/analyze-issues/scripts/test-analyze.sh

test-parse-args:
	bash scripts/test-parse-args.sh

test-prepare-description:
	bash scripts/test-prepare-description.sh

test-parse-prose-blockers:
	bash skills/fix-issue/scripts/test-parse-prose-blockers.sh

test-issue-lifecycle:
	bash skills/fix-issue/scripts/test-issue-lifecycle.sh

test-fix-issue-bail-detection:
	bash skills/fix-issue/scripts/test-fix-issue-bail-detection.sh

test-anti-improvised-wakeup:
	bash scripts/test-anti-improvised-wakeup.sh

test-fix-issue-step-order:
	bash skills/fix-issue/scripts/test-fix-issue-step-order.sh

test-find-lock-issue:
	bash skills/fix-issue/scripts/test-find-lock-issue.sh

test-umbrella-handler:
	bash skills/fix-issue/scripts/test-umbrella-handler.sh

test-finalize-umbrella:
	bash skills/fix-issue/scripts/test-finalize-umbrella.sh

test-sentinel-write:
	bash skills/issue/scripts/test-sentinel-write.sh

test-sessionstart:
	bash scripts/test-sessionstart-health.sh

test-keepalive-sentinel:
	bash scripts/test-keepalive-sentinel.sh

test-preflight-args:
	bash scripts/test-preflight-args.sh

test-check-clean-tree:
	bash scripts/test-check-clean-tree.sh

test-cleanup-tmpdir:
	bash scripts/test-cleanup-tmpdir.sh

test-cache-root-validation:
	bash scripts/test-cache-root-validation.sh

test-finalize-sanity-check:
	bash scripts/test-finalize-sanity-check.sh

test-set-up-forked-open-source-repo:
	bash skills/set-up-forked-open-source-repo/scripts/test-setup-forked-open-source-repo.sh

test-session-entry-gate:
	bash scripts/test-session-entry-gate.sh

test-session-setup-health-defaults:
	bash scripts/test-session-setup-health-defaults.sh

test-session-setup-repo-fallback:
	bash scripts/test-session-setup-repo-fallback.sh

test-session-env-roundtrip:
	bash scripts/test-session-env-roundtrip.sh

test-audit-edit-write:
	bash scripts/test-audit-edit-write.sh

test-block-submodule:
	bash scripts/test-block-submodule-edit.sh

test-deny-edit-write:
	bash scripts/test-deny-edit-write.sh

test-post-scaffold-hints:
	bash scripts/test-post-scaffold-hints.sh

test-render-skill:
	bash skills/create-skill/scripts/test-render-skill-md.sh
	bash skills/show-skill/scripts/test-show-skill.sh

test-show-skill:
	bash skills/show-skill/scripts/test-show-skill.sh

test-render-lane-status:
	bash scripts/test-render-lane-status.sh

test-token-tally:
	bash scripts/test-token-tally.sh

test-token-ledger:
	bash scripts/test-token-ledger.sh

test-token-report:
	bash scripts/test-token-report.sh

test-timing-ledger:
	bash scripts/test-timing-ledger.sh

test-timing-report:
	bash scripts/test-timing-report.sh

test-token-vendor-scrapers:
	bash scripts/test-token-vendor-scrapers.sh

test-token-claude-source:
	bash scripts/test-token-claude-source.sh

test-verify-skill-called:
	bash scripts/test-verify-skill-called.sh

test-check-bump-version:
	bash scripts/test-check-bump-version.sh

test-run-checks:
	bash .claude/skills/relevant-checks/scripts/test-run-checks.sh

test-relevant-checks-byte-budget:
	bash scripts/test-relevant-checks-byte-budget.sh

test-relevant-checks-validation:
	bash scripts/test-relevant-checks-validation.sh

test-relevant-checks-helper-failure:
	bash scripts/test-relevant-checks-helper-failure.sh

test-hook-block-skill-relevant-checks:
	bash scripts/test-hook-block-skill-relevant-checks.sh

test-review-relevant-checks-helper:
	bash scripts/test-review-relevant-checks-helper.sh

test-drop-bump-commit:
	bash scripts/test-drop-bump-commit.sh

test-ci-wait-exit-trap:
	bash scripts/test-ci-wait-exit-trap.sh

test-ci-status:
	bash scripts/test-ci-status.sh

test-merge-pr:
	bash scripts/test-merge-pr.sh

test-apply-bump:
	bash scripts/test-apply-bump.sh

test-lint-skill-invocations:
	bash scripts/test-lint-skill-invocations.sh

test-lint-literal-counts:
	bash scripts/test-lint-literal-counts.sh

test-mermaid-fragments:
	bash scripts/test-mermaid-fragments.sh

test-anti-halt:
	bash scripts/test-anti-halt-banners.sh

test-orchestrator-scope-sync:
	bash scripts/test-orchestrator-scope-sync.sh

test-alias-target-resolution:
	bash scripts/test-alias-target-resolution.sh

test-alias-structure:
	bash scripts/test-alias-structure.sh

test-design-structure:
	bash scripts/test-design-structure.sh

test-design-manifest:
	bash skills/design/scripts/test-design-manifest.sh

test-write-run-params:
	bash scripts/test-write-run-params.sh
test-plan-review-prompt:
	bash skills/design/scripts/test-plan-review-prompt.sh

test-implement-rebase-macro:
	bash scripts/test-implement-rebase-macro.sh

test-rebase-push-keep-on-conflict:
	bash scripts/test-rebase-push-keep-on-conflict.sh

test-implement-structure:
	bash scripts/test-implement-structure.sh

test-implement-cleanup-roundtrip:
	bash scripts/test-implement-cleanup-roundtrip.sh

test-implement-anti-polling-rule:
	bash scripts/test-implement-anti-polling-rule.sh

test-implement-relevant-checks-anti-halt:
	bash skills/implement/scripts/test-implement-relevant-checks-anti-halt.sh

test-implement-anti-halt:
	bash scripts/test-implement-anti-halt.sh

test-post-design-boundary:
	bash skills/implement/scripts/test-post-design-boundary.sh

test-implement-post-design-boundary: test-post-design-boundary
	bash scripts/test-implement-post-design-boundary.sh

test-implement-review-token-propagation:
	bash skills/implement/scripts/test-implement-review-token-propagation.sh

test-step2-dispatch:
	bash skills/implement/scripts/test-step2-dispatch.sh

test-cursor-implementer:
	bash skills/implement/scripts/test-cursor-implementer.sh

test-gemini-implementer:
	bash skills/implement/scripts/test-gemini-implementer.sh

test-codex-implementer:
	bash skills/implement/scripts/test-codex-implementer.sh

test-run-external-agent-args:
	bash scripts/test-run-external-agent-args.sh

test-quick-mode-docs-sync:
	bash scripts/test-quick-mode-docs-sync.sh
	bash scripts/test-quick-mode-docs-sync.sh --self-test

test-implement-finalize:
	bash scripts/test-implement-finalize.sh

test-harness-shards-coverage:
	bash scripts/test-harness-shards-coverage.sh
	bash scripts/test-harness-shards-coverage.sh --self-test

test-references-headers:
	bash scripts/test-references-headers.sh

test-render-reviewer-prompt:
	bash scripts/test-render-reviewer-prompt.sh

test-render-specialist-prompt:
	bash scripts/test-render-specialist-prompt.sh

test-research-structure:
	bash scripts/test-research-structure.sh

test-review-structure:
	bash scripts/test-review-structure.sh

test-run-research-planner:
	bash skills/research/scripts/test-run-research-planner.sh

test-render-findings-batch:
	bash skills/research/scripts/test-render-findings-batch.sh

test-research-banner:
	bash skills/research/scripts/test-research-banner.sh

test-synthesis-subagent:
	bash skills/research/scripts/test-synthesis-subagent.sh

test-research-angle-prompts:
	bash skills/research/scripts/test-research-angle-prompts.sh

test-subskill-anchors:
	bash scripts/test-subskill-anchors.sh

test-tracking-issue-write:
	bash scripts/test-tracking-issue-write.sh

test-false-positive-keywords:
	bash scripts/test-false-positive-keywords.sh

test-round-trip-detect:
	bash scripts/test-round-trip-detect.sh

test-tracking-issue-read-sentinel:
	bash scripts/test-tracking-issue-read-sentinel.sh

test-assemble-anchor:
	bash scripts/test-assemble-anchor.sh

test-refresh-anchor:
	bash scripts/test-refresh-anchor.sh

test-hydrate-anchor:
	bash scripts/test-hydrate-anchor.sh

test-compose-review-findings:
	bash scripts/test-compose-review-findings.sh

test-umbrella-helpers:
	bash skills/umbrella/scripts/test-helpers.sh

test-umbrella-parse-args:
	bash skills/umbrella/scripts/test-umbrella-parse-args.sh

test-umbrella-blocked-by-issue:
	bash skills/umbrella/scripts/test-umbrella-blocked-by-issue.sh

test-umbrella-emit-output-contract:
	bash skills/umbrella/scripts/test-umbrella-emit-output-contract.sh

test-umbrella-render-batch-input:
	bash skills/umbrella/scripts/test-render-batch-input.sh

test-render-umbrella-body:
	bash skills/umbrella/scripts/test-render-umbrella-body.sh

test-check-review-changes:
	bash skills/implement/scripts/test-check-review-changes.sh

test-check-mid-run-dirty-tree:
	bash scripts/test-check-mid-run-dirty-tree.sh

test-check-phantom-dirty:
	bash scripts/test-check-phantom-dirty.sh

test-check-reviewers:
	bash scripts/test-check-reviewers.sh

test-check-generators:
	bash scripts/test-check-generators.sh

test-check-topology-rule-paths:
	bash scripts/test-check-topology-rule-paths.sh

test-generate-topology-docs:
	bash scripts/test-generate-topology-docs.sh

test-external-tool-registry:
	bash scripts/test-external-tool-registry.sh

test-launch-review:
	bash scripts/test-launch-review.sh

test-agent-model-args:
	bash scripts/test-agent-model-args.sh

test-effort-prose:
	bash scripts/test-effort-prose.sh

test-lib-cursor-auth:
	bash scripts/test-lib-cursor-auth.sh

test-github-remote-repo:
	bash scripts/test-github-remote-repo.sh

test-implement-fork-env:
	bash scripts/test-implement-fork-env.sh

test-get-issue-context:
	bash scripts/test-get-issue-context.sh

test-create-pr:
	bash scripts/test-create-pr.sh

test-resolve-repo:
	bash scripts/test-resolve-repo.sh

test-gh-pr-body-update:
	bash scripts/test-gh-pr-body-update.sh

test-wait-for-reviewers:
	bash scripts/test-wait-for-reviewers.sh

test-run-external-agent:
	bash scripts/test-run-external-agent.sh

test-validate-pieces-json:
	bash skills/umbrella/scripts/test-validate-pieces-json.sh

test-body-file-title:
	bash skills/issue/scripts/test-body-file-title.sh

test-intra-batch-deps:
	bash skills/issue/scripts/test-intra-batch-deps.sh

test-oos-file-conflict-deps:
	bash skills/implement/scripts/test-oos-file-conflict-deps.sh

test-oos-issue-cap:
	bash skills/implement/scripts/test-oos-issue-cap.sh

test-blocked-by-issue:
	bash skills/issue/scripts/test-blocked-by-issue.sh

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
	bash scripts/test-eval-set-structure.sh

# Standalone offline regression harness for the `--baseline` flag handling
# in scripts/eval-research.sh (closes #441). NOT a `test-harnesses`
# prerequisite — the eval-research surface is opt-in operator
# instrumentation explicitly carved out from CI by repo contract
# (see the `test-eval-set-structure` target above, docs/linting.md,
# scripts/eval-research.md). Runs offline by PATH-stubbing claude + jq
# so it works on machines without the real binaries.
# See scripts/test-eval-research-baseline-flag.md.
test-eval-research-baseline-flag:
	bash scripts/test-eval-research-baseline-flag.sh

shellcheck:
	pre-commit run shellcheck --all-files

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
