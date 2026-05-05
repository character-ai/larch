# Larch Makefile
# Thin wrapper around pre-commit. Linter definitions live in .pre-commit-config.yaml.

.PHONY: lint lint-only test-harnesses test-harnesses-1 test-harnesses-2 test-harnesses-3 test-harnesses-4 test-harnesses-5 shellcheck markdownlint jsonlint actionlint agent-lint agnix gitleaks trufflehog setup test-redact test-validate-research-output test-validate-citations test-validate-citations-budget test-collect-agent-bash32 test-collect-agent-retry test-parse-input test-allocate-candidates test-add-blocked-by test-list-issues test-parse-args test-prepare-description test-parse-prose-blockers test-issue-lifecycle test-fix-issue-bail-detection test-fix-issue-step-order test-find-lock-issue test-umbrella-handler test-finalize-umbrella test-sentinel-write test-sessionstart test-session-entry-gate test-audit-edit-write test-block-submodule test-deny-edit-write test-post-scaffold-hints test-render-skill test-render-lane-status test-verify-skill-called test-check-bump-version test-drop-bump-commit test-ci-wait-exit-trap test-merge-pr test-lint-skill-invocations test-anti-halt test-orchestrator-scope-sync test-alias-target-resolution test-alias-structure test-design-structure test-design-manifest test-implement-rebase-macro test-implement-structure test-implement-anti-polling-rule test-implement-post-design-boundary test-step2-dispatch test-cursor-implementer test-gemini-implementer test-run-external-agent test-run-external-agent-args test-quick-mode-docs-sync test-implement-finalize test-harness-shards-coverage test-references-headers test-render-reviewer-prompt test-render-specialist-prompt test-research-structure test-review-structure test-run-research-planner test-render-findings-batch test-research-banner test-synthesis-subagent test-research-angle-prompts test-subskill-anchors test-tracking-issue-write test-tracking-issue-read-sentinel test-assemble-anchor test-refresh-anchor test-hydrate-anchor test-token-tally test-umbrella-helpers test-umbrella-parse-args test-umbrella-emit-output-contract test-umbrella-render-batch-input test-render-umbrella-body test-check-review-changes test-check-reviewers test-external-tool-registry test-launch-gemini-review test-validate-pieces-json smoke-dialectic eval-research test-eval-set-structure test-eval-research-baseline-flag test-body-file-title test-intra-batch-deps test-blocked-by-issue test-oos-file-conflict-deps

# CI splits `lint` into `lint-only` (pre-commit) and `test-harnesses`
# (regression harnesses). `lint` remains the local-dev convenience target
# that runs both, defined in terms of the two split targets to prevent drift.
lint: test-harnesses lint-only

lint-only:
	pre-commit run --all-files

# Five balanced regression-harness shards. Lists are manually adjusted from
# observed CI timings; see docs/linting.md "Refreshing harness shard balance"
# for the procedure used to regenerate these lists when imbalance grows. The
# test-validate-citations harness remains the dominant wall-clock harness;
# its real-time budget-exhaustion tests live in test-validate-citations-budget
# so their sleeps can be billed to a different shard. IMPORTANT: each
# test-harnesses-N rule below stays on a single physical line (no `\`
# continuations); the drift-detection script
# `scripts/test-harness-shards-coverage.sh` parses these lines literally.
# New harnesses get appended to one shard line.
test-harnesses: test-harnesses-1 test-harnesses-2 test-harnesses-3 test-harnesses-4 test-harnesses-5

test-harnesses-1: test-umbrella-handler test-issue-lifecycle test-finalize-umbrella test-add-blocked-by test-design-manifest test-umbrella-render-batch-input test-run-research-planner test-deny-edit-write test-render-lane-status test-research-structure test-implement-rebase-macro test-alias-structure test-fix-issue-bail-detection test-synthesis-subagent test-find-lock-issue test-render-specialist-prompt

test-harnesses-2: test-research-banner test-post-scaffold-hints test-body-file-title test-cursor-implementer test-gemini-implementer test-drop-bump-commit test-lint-skill-invocations test-ci-wait-exit-trap test-merge-pr test-list-issues test-render-reviewer-prompt test-parse-input test-validate-pieces-json test-step2-dispatch test-subskill-anchors test-render-skill test-quick-mode-docs-sync test-sessionstart test-check-reviewers test-launch-gemini-review test-research-angle-prompts test-implement-anti-polling-rule test-umbrella-emit-output-contract test-validate-citations-budget

test-harnesses-3: test-tracking-issue-write test-allocate-candidates test-block-submodule test-redact test-validate-research-output test-prepare-description test-assemble-anchor test-refresh-anchor test-tracking-issue-read-sentinel test-token-tally test-collect-agent-bash32 test-collect-agent-retry test-sentinel-write test-design-structure test-fix-issue-step-order test-orchestrator-scope-sync test-intra-batch-deps test-blocked-by-issue test-oos-file-conflict-deps test-review-structure test-check-bump-version

test-harnesses-4: test-umbrella-helpers test-render-findings-batch test-verify-skill-called test-check-review-changes test-parse-prose-blockers test-umbrella-parse-args test-render-umbrella-body test-references-headers test-implement-structure test-implement-post-design-boundary test-audit-edit-write test-parse-args test-anti-halt test-alias-target-resolution

# Shard-5 leads with the partition-invariant guard so partition bugs surface.
test-harnesses-5: test-harness-shards-coverage test-validate-citations test-external-tool-registry test-session-entry-gate test-hydrate-anchor test-implement-finalize test-run-external-agent test-run-external-agent-args

test-redact:
	bash scripts/test-redact-secrets.sh

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

test-session-entry-gate:
	bash scripts/test-session-entry-gate.sh

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

test-render-lane-status:
	bash scripts/test-render-lane-status.sh

test-token-tally:
	bash scripts/test-token-tally.sh

test-verify-skill-called:
	bash scripts/test-verify-skill-called.sh

test-check-bump-version:
	bash scripts/test-check-bump-version.sh

test-drop-bump-commit:
	bash scripts/test-drop-bump-commit.sh

test-ci-wait-exit-trap:
	bash scripts/test-ci-wait-exit-trap.sh

test-merge-pr:
	bash scripts/test-merge-pr.sh

test-lint-skill-invocations:
	bash scripts/test-lint-skill-invocations.sh

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

test-implement-rebase-macro:
	bash scripts/test-implement-rebase-macro.sh

test-implement-structure:
	bash scripts/test-implement-structure.sh

test-implement-anti-polling-rule:
	bash scripts/test-implement-anti-polling-rule.sh

test-implement-post-design-boundary:
	bash scripts/test-implement-post-design-boundary.sh

test-step2-dispatch:
	bash skills/implement/scripts/test-step2-dispatch.sh

test-cursor-implementer:
	bash skills/implement/scripts/test-cursor-implementer.sh

test-gemini-implementer:
	bash skills/implement/scripts/test-gemini-implementer.sh

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

test-tracking-issue-read-sentinel:
	bash scripts/test-tracking-issue-read-sentinel.sh

test-assemble-anchor:
	bash scripts/test-assemble-anchor.sh

test-refresh-anchor:
	bash scripts/test-refresh-anchor.sh

test-hydrate-anchor:
	bash scripts/test-hydrate-anchor.sh

test-umbrella-helpers:
	bash skills/umbrella/scripts/test-helpers.sh

test-umbrella-parse-args:
	bash skills/umbrella/scripts/test-umbrella-parse-args.sh

test-umbrella-emit-output-contract:
	bash skills/umbrella/scripts/test-umbrella-emit-output-contract.sh

test-umbrella-render-batch-input:
	bash skills/umbrella/scripts/test-render-batch-input.sh

test-render-umbrella-body:
	bash skills/umbrella/scripts/test-render-umbrella-body.sh

test-check-review-changes:
	bash skills/implement/scripts/test-check-review-changes.sh

test-check-reviewers:
	bash scripts/test-check-reviewers.sh

test-external-tool-registry:
	bash scripts/test-external-tool-registry.sh

test-launch-gemini-review:
	bash scripts/test-launch-gemini-review.sh

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
