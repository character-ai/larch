# Larch Makefile
# Thin wrapper around pre-commit. Linter definitions live in .pre-commit-config.yaml.

PYTHON ?= python3
PYLINT_JOBS ?= $(shell $(PYTHON) -c 'import os; print(0 if os.sysconf("SC_SEM_NSEMS_MAX") >= 0 else 1)' 2>/dev/null || printf '1')

.PHONY: py-lint py-lint-main py-lint-checks-fast py-lint-shard py-typecheck py-lint-duplicate-code py-test lint lint-only test-harnesses test-harnesses-1 test-harnesses-2 test-harnesses-3 test-harnesses-4 test-harnesses-5 shellcheck markdownlint jsonlint actionlint agent-lint agnix gitleaks trufflehog setup test-pipe-sigpipe-safety test-redact test-scrub-log-secrets test-redact-tmpdir-paths test-append-tool-failure test-flush-vendor-failure-diagnostics test-append-execution-issue test-validate-research-output test-render-final-summary-bash32 test-collect-agent-results test-blocker test-issue-query test-anti-improvised-wakeup test-audit-runs test-sessionstart test-sweep-design-logs test-check-clean-tree test-check-main-sync test-check-scope-reduction-marker test-plan-review-scope-anchor test-persist-retally-step3-env test-lib-scope-anchor-handoff test-clarify-comment test-clarify-state test-check-stale-plugin test-preflight-args test-cache-root-validation test-cache-key-discipline test-finalize-sanity-check test-audit-edit-write test-block-submodule test-deny-edit-write test-verify-skill-called test-hook-anti-read-poll test-hook-bg-poll-guard test-hook-progress-report test-hook-stop-fail-close test-hook-no-progress-guard test-classify-bump test-git-push test-lint-skill-invocations test-lint-skill-md-flag-signature test-lint-codex-exec-auth test-lint-literal-counts test-lint-no-raw-stderr-after-quiet-init test-lint-readability-preamble test-lint-bare-grep-probe test-anti-halt test-orchestrator-scope-sync test-alias-structure test-design-structure test-decompose-panel-dispatch test-decompose-aggregator test-decompose-file-issues test-design-driver test-design-clarify test-design-publish test-design-postplan-emit test-invoke-plan-validator test-file-design-oos test-emit-plan test-gate-b-dedup-plan test-trailer-helpers test-emit-design-plan-preview test-check-plan-size test-parse-plan-commands test-validate-plan-commands test-step3-review-cap test-run-step3-review test-plan-review-loop test-tally-plan-review test-finalize-plan test-step0b-router-flag-recovery test-brainstorm-prompts test-scout-plan-archetypes-wrapper test-dispatch-plan-review-panel test-render-final-summary test-implement-rebase-macro test-phantom-probe-with-warn test-implement-step2-routing test-implement-structure test-implement-step8-exit3-first-fixer test-oos-disposition-gate test-step-8-oos-checkpoint test-plan-adequacy-audit test-implement-preflight test-implement-positional-issue test-implement-fence-shape test-architectural-guidelines-step test-implement-timing-rehydration test-implement-cleanup-roundtrip test-implement-anti-polling-rule test-implement-relevant-checks-anti-halt test-implement-anti-halt test-implement-review-token-propagation test-step2-dispatch test-cursor-implementer test-codex-implementer test-refresh-run-logs test-launch-cursor-ci test-launch-claude-ci test-launch-codex-ci test-run-negotiation-round test-launch-claude-subprocess test-launch-claude-review test-dispatch-with-waterfall test-revise-plan-with-waterfall test-run-external-agent test-run-external-agent-args test-quick-mode-docs-sync test-implement-bootstrap test-implement-bootstrap-invoke test-implement-finalize test-flush-execution-issues test-post-tracking-issue test-commit-implementation test-review-and-fix-commit-fixes test-generate-code-flow-diagram test-refresh-execution-issues test-review-and-fix-write-rejected test-slack-issue-announce test-step-16-17 test-write-final-report test-step-18 test-step-18b-final-report test-token-cost test-render-cost-line test-implement-cleanup-script test-harness-shards-coverage test-harness-timer test-references-headers test-research-structure test-review-structure test-gather-context test-gather-branch-context test-review-core test-dispatch-panel-core test-dispatch-panel-core-dynamic test-dispatch-panel-reuse test-dispatch-panel-limits test-scout-dynamic-archetypes test-dispatch-plan-voters test-collect-findings test-aggregate-findings test-prune-nit-findings test-tally-code-votes test-check-reviewer-failure-threshold test-dispatch-code-voters-happy test-dispatch-code-voters-edge-and-r3-claude test-dispatch-code-voters-regressions-r1-r2 test-dispatch-code-voters-regressions-r3-codex test-emit-tally test-log-phase test-review-and-fix test-review-and-fix-dispatch test-review-and-fix-convergence test-review-and-fix-parsers test-render-findings-batch test-synthesis-subagent test-research-angle-prompts test-subskill-anchors test-tracking-issue-write test-larch-log test-capture-session-transcript test-larch-logs-manifest test-larch-logs-batches test-compose-plan-goals-test test-compose-collector-failure-log test-tracking-issue-summary test-tracking-issue-read-sentinel test-compose-review-findings test-token-tally test-token-ledger test-token-report test-timing-ledger test-timing-report test-parse-codex-usage test-token-vendor-scrapers test-token-claude-source test-review-and-fix-check-changes test-check-mid-run-dirty-tree test-check-phantom-dirty test-check-reviewers test-degraded-tools-gate test-check-topology-rule-paths test-external-tool-registry test-agent-model-args test-effort-prose test-launch-review test-lib-design-tmpdir test-implement-fork-env test-get-issue-context eval-research test-eval-set-structure test-eval-research-baseline-flag test-oos-file-conflict-deps test-oos-issue-cap test-wait-for-reviewers test-classify-diff-mode test-analyze test-compute-pr-line-counts test-review-and-fix-step5 test-run-step1-plan-log test-run-step2-dispatch test-prompt-template-invariants test-verify-run-log-completeness test-design-log-publish test-fetch-combinable-issues-filter test-legacy-title-prefix-literals-scope test-implement-admission test-pause-skill test-fluff-analysis test-rejected-analysis

.PHONY: test-findings-classification test-review-findings-classification test-review-and-fix-step5-starting-round test-bug-structure
.PHONY: test-prompt-template-invariants
.PHONY: test-larch-log-write-round
.PHONY: test-scout-dynamic-archetypes
.PHONY: test-plan-review test-plan-review-panel
.PHONY: test-git-commit-only
.PHONY: test-promote-release test-release-finish test-release-prepare test-release-set-version
.PHONY: test-auto-fix-plan-commands test-design-step2b-drafter test-gate-b-apply-mode
.PHONY: test-token-report-dedup test-token-cost-per-bucket test-render-cost-line-realism test-render-cost-line-callsites test-token-report-summary-format test-parse-bootstrap-routing-envelope test-step-telemetry-mark lint-retired-scripts skill-closure-size lint-skill-closure-growth regen-skill-closure-baseline test-lint-skill-closure-growth
.PHONY: lint-bash32 test-lint-bash32 lint-gh-body-inline lint-mermaid agent-sync
.PHONY: lint-bg-wait-coverage test-lint-bg-wait-coverage
.PHONY: test-step-7a test-step-8-ship test-step-8-oos-checkpoint
.PHONY: test-stall-recovery-report test-stall-recovery-report-1 test-stall-recovery-report-2 test-stall-recovery-report-3 test-step-18 test-step-18b-final-report
.PHONY: test-resolve-upstream-larch-repo test-file-failure-report-cross-repo
.PHONY: test-design-pause-resume
.PHONY: test-design-step1d5 test-design-log-ship
.PHONY: test-review-design-step3-loop
.PHONY: test-read-result-env test-parse-design-argv
.PHONY: lint-readability-preamble test-lint-readability-preamble
.PHONY: lint-renderer-substitution-safety lint-skill-md-flag-signature lint-skill-description-length test-lint-renderer-substitution-safety test-lint-skill-md-flag-signature test-lint-skill-description-length
.PHONY: lint-bare-grep-probe test-lint-bare-grep-probe lint-codex-exec-auth test-lint-codex-exec-auth lint-consecutive-bash test-lint-consecutive-bash test-launch-codex-exec lint-awk-multibyte-regex test-lint-awk-multibyte-regex
.PHONY: lint-tier1a-size test-lint-tier1a-size
.PHONY: test-design-multi-round-integration test-lib-design-round-artifacts test-step3-orchestrator-fence test-design-step3-state test-design-step3-mav
.PHONY: test-no-grouped-reuse-guard test-review-and-fix-record-timing test-review-and-fix-step5-loop-timing test-record-plan-review-round-timing test-reviewer-prune test-lib-prune-decision test-fluff-analysis-corpus test-voter-calibration
# CI splits `lint` into `lint-only` (pre-commit) and `test-harnesses`
# (regression harnesses). `lint` remains the local-dev convenience target
# that runs both, defined in terms of the two split targets to prevent drift.
lint: test-harnesses lint-bash32 lint-readability-preamble lint-renderer-substitution-safety lint-skill-md-flag-signature lint-skill-description-length lint-bare-grep-probe lint-codex-exec-auth lint-consecutive-bash lint-bg-wait-coverage lint-awk-multibyte-regex lint-tier1a-size lint-retired-scripts lint-skill-closure-growth lint-only

py-lint: py-lint-main py-typecheck

# Fast Python lints (ruff + custom AST ratchets): a few seconds total. Shared by
# the local full lint (py-lint-main) and CI shard 1 (py-lint-shard) so the check
# set is defined once.
py-lint-checks-fast:
	@$(PYTHON) -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' \
		|| (printf '%s\n' "ERROR: make py-lint-checks-fast requires Python 3.11 or newer (PYTHON=$(PYTHON))" >&2; exit 1)
	cd python && ruff check .
	$(PYTHON) python/cli.py lint complexity-baseline
	$(PYTHON) python/cli.py lint keyword-only
	$(PYTHON) python/cli.py lint subprocess-via-runner
	$(PYTHON) python/cli.py lint env-via-config-constant
	$(PYTHON) python/cli.py lint layering

# Local full Python lint: fast checks + pylint over the whole tree. pylint runs
# with all cores when the host supports the required process-pool semaphore
# query. Some restricted local sandboxes deny that query, so they fall back to a
# single worker. duplicate-code is disabled here (.pylintrc) and runs in the
# dedicated py-lint-duplicate-code target.
py-lint-main: py-lint-checks-fast
	cd python && pylint -j $(PYLINT_JOBS) .

# CI per-shard Python lint (matrix PYLINT_SHARD_ID of PYLINT_SHARD_COUNT). The
# ruff + AST ratchet fast checks (~10s on CI) run once, on shard 1; pylint runs
# on this shard's basename subset (python/pylint_sharding.py). Shard 1 holds the
# a..o source, the lightest pylint shard on CI, so it absorbs the fast-check lump
# with the least imbalance. A python-lint-gate job aggregates the matrix so the
# required status check name stays stable across resharding.
py-lint-shard:
	@$(PYTHON) -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' \
		|| (printf '%s\n' "ERROR: make py-lint-shard requires Python 3.11 or newer (PYTHON=$(PYTHON))" >&2; exit 1)
	@if [ "$(PYLINT_SHARD_ID)" = "1" ]; then $(MAKE) py-lint-checks-fast; fi
	cd python && $(PYTHON) cli.py lint pylint-shard --shard-id $(PYLINT_SHARD_ID) --shard-count $(PYLINT_SHARD_COUNT) --jobs $(PYLINT_JOBS)

.PHONY: regen-complexity-baseline regen-keyword-only-baseline regen-subprocess-via-runner-baseline regen-env-via-config-constant-baseline regen-layering-baseline regen-skill-closure-baseline
regen-complexity-baseline:
	# Mechanically regenerate python/complexity-baseline.json from live ruff
	# output so the ratchet baseline is generated, not hand-edited (issue #5041).
	$(PYTHON) python/cli.py lint complexity-baseline --write

regen-keyword-only-baseline:
	# Regenerate python/keyword-only-baseline.json from live AST scan.
	$(PYTHON) python/cli.py lint keyword-only --write

regen-subprocess-via-runner-baseline:
	# Regenerate python/subprocess-via-runner-baseline.json from live AST scan.
	# Routine regen preserves matching per-record reasons; the bootstrap reason
	# is used only when the baseline file is absent.
	@if [ -f python/subprocess-via-runner-baseline.json ]; then \
		$(PYTHON) python/cli.py lint subprocess-via-runner --write; \
	else \
		$(PYTHON) python/cli.py lint subprocess-via-runner --write --initial-reason 'grandfathered direct subprocess usage pre-G-Py-9 ratchet'; \
	fi

regen-env-via-config-constant-baseline:
	# Regenerate python/env-via-config-constant-baseline.json from live AST scan.
	# Routine regen preserves matching per-record reasons; the bootstrap reason
	# is used only when the baseline file is absent.
	@if [ -f python/env-via-config-constant-baseline.json ]; then \
		$(PYTHON) python/cli.py lint env-via-config-constant --write; \
	else \
		$(PYTHON) python/cli.py lint env-via-config-constant --write --initial-reason 'grandfathered bare env literal pre-G-Cfg-2 ratchet'; \
	fi

regen-layering-baseline:
	# Regenerate python/layering-baseline.json from live AST scan.
	# Routine regen preserves matching per-record reasons; the bootstrap reason
	# is used only when the baseline file is absent.
	@if [ -f python/layering-baseline.json ]; then \
		$(PYTHON) python/cli.py lint layering --write; \
	else \
		$(PYTHON) python/cli.py lint layering --write --initial-reason 'grandfathered upward import pre-layering-ratchet'; \
	fi

regen-skill-closure-baseline:
	# Regenerate python/skill-closure-baseline.json from live /design and /implement markdown closure size.
	$(PYTHON) python/cli.py lint skill-closure-growth --write

skill-closure-size:
	$(PYTHON) python/cli.py skill-closure report

lint-skill-closure-growth:
	$(PYTHON) python/cli.py lint skill-closure-growth

py-typecheck:
	@$(PYTHON) -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' \
		|| (printf '%s\n' "ERROR: make py-typecheck requires Python 3.11 or newer (PYTHON=$(PYTHON))" >&2; exit 1)
	cd python && pyright

py-lint-duplicate-code:
	@$(PYTHON) -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' \
		|| (printf '%s\n' "ERROR: make py-lint-duplicate-code requires Python 3.11 or newer (PYTHON=$(PYTHON))" >&2; exit 1)
	# Duplicate-code (R0801) runs through the larch runner. It uses Pylint
	# 4.0.5's symilar engine via PyLinter plus SimilaritiesChecker.process_module
	# ingestion with astroid Module nodes, then parallelizes pair comparisons by
	# explicit combinations indices on the configured checker-owned Symilar
	# instance. It does not shard file slices or pre-scan through _iter_sims. Kept
	# out of `py-lint` (which disables duplicate-code via .pylintrc) so the main
	# lint pass parallelizes; this is the CI `python-lint-duplicate-code` job. See
	# issue #4480.
	$(PYTHON) python/cli.py lint duplicate-code --root python --rcfile python/.pylintrc

py-test:
	@$(PYTHON) -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' \
		|| (printf '%s\n' "ERROR: make py-test requires Python 3.11 or newer (PYTHON=$(PYTHON))" >&2; exit 1)
	# --durations=0 emits per-test timing so CI shards (PYTEST_SHARD_ID /
	# PYTEST_SHARD_COUNT, see python/conftest.py) can be rebalanced by wall time.
	cd python && $(PYTHON) -m pytest --durations=0

lint-only:
	pre-commit run --all-files

lint-tier1a-size:
	python3 python/cli.py lint tier1a-size

test-lint-tier1a-size:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_lint_tier1a.py -q

lint-readability-preamble:
	python3 python/cli.py lint readability-preamble

lint-renderer-substitution-safety:
	bash scripts/lint-renderer-substitution-safety.sh

lint-skill-md-flag-signature:
	python3 python/cli.py lint skill-md-flag-signature

lint-skill-description-length:
	python3 python/cli.py lint skill-description-length

lint-bare-grep-probe:
	bash scripts/lint-bare-grep-probe.sh

lint-codex-exec-auth:
	python3 python/cli.py lint codex-exec-auth

lint-consecutive-bash:
	python3 python/cli.py lint consecutive-bash

test-lint-consecutive-bash:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/lint/test_lint_consecutive_bash.py -q

lint-bg-wait-coverage:
	python3 python/cli.py lint bg-wait-coverage

test-lint-bg-wait-coverage:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_lint_bg_wait_coverage.py -q

lint-awk-multibyte-regex:
	bash scripts/lint-awk-multibyte-regex.sh

# Bash regression-harness shards (#1294, #1585, #1911, #2080, #2252, #2262, #2291, #2349, #2366,
# #2386, #5429 — originally 20 shards mixing pytest wrappers with bash scripts; collapsed to 6, then 5
# bash-only shards after pruning 193 pytest-wrapper targets that duplicated the python-tests job).
# Each test-harnesses-N rule below stays on a single physical line (no `\` continuations); the
# drift-detection script `scripts/test-harness-shards-coverage.sh` parses these lines literally.
# New bash harnesses get appended to one shard line.
test-harnesses: test-harnesses-1 test-harnesses-2 test-harnesses-3 test-harnesses-4 test-harnesses-5

test-harnesses-1: test-fluff-analysis-corpus test-token-vendor-scrapers test-fluff-analysis test-cache-root-validation test-step-8-ship test-pipe-sigpipe-safety test-references-headers test-architectural-guidelines-step test-check-stale-plugin test-quick-mode-docs-sync test-implement-step2-routing test-legacy-title-prefix-literals-scope test-synthesis-subagent test-anti-improvised-wakeup

test-harnesses-2: test-design-step3-review test-hook-anti-read-poll test-file-failure-report-cross-repo test-lint-literal-counts test-lint-awk-multibyte-regex test-resolve-upstream-larch-repo test-lint-bare-grep-probe test-lint-no-raw-stderr-after-quiet-init test-render-cost-line-callsites test-lint-renderer-substitution-safety test-audit-edit-write test-rejected-analysis test-implement-step8-exit3-first-fixer test-orchestrator-scope-sync test-implement-relevant-checks-anti-halt

test-harnesses-3: test-design-step3-mav test-hook-bg-poll-guard test-prompt-template-invariants test-design-multi-round-integration test-hook-stop-fail-close test-hook-no-progress-guard test-design-structure test-voter-calibration test-research-structure test-cache-key-discipline test-plan-adequacy-audit test-implement-structure test-design-clarify test-alias-structure test-anti-halt test-bug-structure test-effort-prose

test-harnesses-4: test-harness-shards-coverage test-step3-orchestrator-fence test-gate-b-apply-mode test-read-result-env test-sessionstart test-check-topology-rule-paths test-block-submodule test-lint-bash32 test-deny-edit-write test-pause-skill test-implement-timing-rehydration test-subskill-anchors test-research-angle-prompts test-brainstorm-prompts test-implement-cleanup-roundtrip

test-harnesses-5: test-findings-classification test-step3-review-cap test-step-18 test-implement-review-token-propagation test-design-step3-entry test-sweep-design-logs test-external-tool-registry test-flush-vendor-failure-diagnostics test-review-structure test-implement-anti-polling-rule test-implement-fence-shape test-hook-progress-report test-implement-anti-halt test-step-8-oos-checkpoint test-implement-rebase-macro test-implement-positional-issue

test-pipe-sigpipe-safety:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-pipe-sigpipe-safety.sh

test-redact:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/core/test_redact.py -k 'not (scrub_log_secrets or tmpdir or operator)'

test-scrub-log-secrets:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/core/test_redact.py -k scrub_log_secrets

test-redact-tmpdir-paths:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/core/test_redact.py -k 'tmpdir or operator'

test-reviewer-prune:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/review/test_review_pipeline.py -k reviewer_prune

test-lib-prune-decision:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/review/test_review_pipeline.py -k 'prune and not reviewer_prune'

test-append-tool-failure:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/report/test_run_logs.py -k execution_issues

test-append-execution-issue:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/issue/test_execution_issues.py -k 'not (flush or refresh)'

test-validate-research-output:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/research/test_research_eval.py



test-collect-agent-results:
	python3 python/cli.py timing harness-mark --label $@ -- sh -c 'cd python && $(PYTHON) -m pytest -q test_collect_results.py'


test-flush-vendor-failure-diagnostics:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-flush-vendor-failure-diagnostics.sh






test-analyze:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/issue/test_analyze_issues.py -q

test-fluff-analysis:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/fluff-analysis/scripts/test-fluff-analysis.sh

test-rejected-analysis:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/rejected-analysis/scripts/test-rejected-analysis.sh

test-voter-calibration:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/voter-calibration/scripts/test-voter-calibration.sh

test-fluff-analysis-corpus:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/fluff-analysis/scripts/test-fluff-analysis-corpus.sh

test-fetch-combinable-issues-filter:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/issue/test_combine_issues.py -q

test-legacy-title-prefix-literals-scope:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-legacy-title-prefix-literals-scope.sh

test-blocker:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/issue/test_blocker.py -x -q

test-issue-query:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/issue/test_issue_query.py -x -q

test-implement-admission:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/state/test_admission.py -x -q -k 'not (preflight or fork_env)'

test-anti-improvised-wakeup:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-anti-improvised-wakeup.sh

test-audit-runs:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/issue/test_audit_runs.py -q


test-sessionstart:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-sessionstart-health.sh

test-sweep-design-logs:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-sweep-design-logs.sh

test-preflight-args:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/state/test_admission.py -x -q -k 'preflight'

test-check-clean-tree:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/git/test_git.py -q -k 'clean_tree'

test-check-main-sync:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/git/test_check_main_sync.py python/tests/git/test_git.py -q -k 'check_main_sync'



test-check-scope-reduction-marker:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/state/test_dirty_tree.py -x -q -k 'scope_check or scope_marker'

test-plan-review:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/review/test_plan_review.py -q -k '(drift_baseline and not round_artifact) or compose_attributed_ballot or ballot_neutralization or aggregation_ok or aggregator_status or write_atomic'

test-plan-review-panel:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/review/test_plan_review_panel.py -q -k 'not ((panel_dispatch and not usage) or (voter_dispatch and not usage))'

test-plan-review-scope-anchor:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/review/test_plan_review.py -q -k 'scope_anchor and not persist_retally'

test-lib-scope-anchor-handoff:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/rendering/test_rendering.py -q

test-clarify-comment:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/design/test_clarify.py -q -k comment

test-clarify-state:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/design/test_clarify.py -q -k 'not comment'

test-check-stale-plugin:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-check-stale-plugin.sh


test-cache-root-validation:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-cache-root-validation.sh

test-cache-key-discipline:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-cache-key-discipline.sh

test-finalize-sanity-check:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/state/test_finalize.py -q -k cleanup_target_ok


test-audit-edit-write:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-audit-edit-write.sh

test-block-submodule:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-block-submodule-edit.sh


test-deny-edit-write:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-deny-edit-write.sh




test-token-tally:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/report/test_tokens.py -q -k tally

test-token-ledger:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/report/test_tokens.py -q -k ledger

test-token-report:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/report/test_tokens.py -q -k token_report

test-token-report-dedup:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/report/test_tokens.py -q -k dedupe

test-token-cost-per-bucket:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/report/test_report_tokens_cost.py -q -k bucket

test-render-cost-line-realism:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/report/test_report_tokens_cost.py -q -k 'not (render_cost_line or token_cost or bucket)'

test-render-cost-line-callsites:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-render-cost-line-callsites.sh

test-token-report-summary-format:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/report/test_tokens.py -q -k 'not (compute_pr_line_counts or claude_source or ledger or tally or dedupe or token_report)'

test-timing-ledger:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/report/test_timing.py -q -k 'not harness_mark and not telemetry_mark and not report'

test-review-and-fix-record-timing:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/review/test_review_and_fix.py -q -k record_timing

test-review-and-fix-step5-loop-timing:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/review/test_review_and_fix.py -q -k loop_timing

test-record-plan-review-round-timing:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/review/test_plan_review.py -q -k 'record_round_timing or persist_round_start_s'

test-step-telemetry-mark:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/report/test_timing.py -q -k telemetry_mark

test-timing-report:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/report/test_timing.py -q -k report

test-token-vendor-scrapers:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-token-vendor-scrapers.sh

test-parse-codex-usage:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/agents/test_agents.py -q -k parse_codex_usage

test-token-claude-source:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/report/test_tokens.py -q -k claude_source

test-verify-skill-called:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/core/test_verify_skill.py


test-hook-anti-read-poll:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-hook-anti-read-poll.sh

test-hook-bg-poll-guard:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-hook-bg-poll-guard.sh

test-hook-progress-report:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-hook-progress-report.sh

test-hook-stop-fail-close:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-hook-stop-fail-close.sh

test-hook-no-progress-guard:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-hook-no-progress-guard.sh

test-classify-bump:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/release/test_version_bump.py -q

test-release-prepare:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/release/test_release.py -q -k release_prepare

test-release-set-version:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/release/test_release.py -q -k 'set_version or read_plugin_version or plugin_read_version'

test-release-finish:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/release/test_release.py -q -k 'release_finish or verify_main'

test-promote-release:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/release/test_release.py -q -k 'promote and not release_finish'


test-git-push:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/git/test_push.py -q -k 'branch_push or branch_main or propagates_final_exit'


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

test-bug-structure:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-bug-structure.sh

test-design-structure:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-design-structure.sh

test-design-pause-resume:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/design/test_design_pause.py

test-pause-skill:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/pause/scripts/test-pause-skill.sh

test-decompose-panel-dispatch:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/design/test_decompose.py -q -k '(panel or degraded) and not aggregate'

test-decompose-aggregator:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/design/test_decompose.py -q -k aggregate

test-decompose-file-issues:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/design/test_decompose.py -q -k 'prepare or annotate or close_original'

test-design-step2b-drafter:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/design/test_design_lifecycle.py -k 'step2a or step2b or guideline or dialectic_instructions or postplan_decide or postplan_executor'

test-design-driver:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/design/test_design_lifecycle.py -k 'phase_driver or design_read_result_env or design_driver'

test-design-clarify:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/design/scripts/test-design-clarify.sh

test-design-publish:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/design/test_design_publish.py

test-design-postplan-emit:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/design/test_design_postplan.py

test-read-result-env:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-read-result-env.sh

test-parse-design-argv:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/design/test_design_argv.py


test-invoke-plan-validator:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/design/test_plan_quality.py -k validate_plan

test-file-design-oos:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/design/test_design_oos.py

test-design-log-publish:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/design/test_design_log_publish_flow.py



test-emit-plan:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/review/test_plan_review.py -q -k emit_plan

test-gate-b-dedup-plan:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/review/test_plan_review.py -q -k gate_b_dedup

test-gate-b-apply-mode:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/design/scripts/test-gate-b-apply-mode.sh

test-trailer-helpers:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/design/test_plan_quality.py -k optional_trailer

test-emit-design-plan-preview:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/review/test_plan_review.py -q -k preview
test-check-plan-size:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/design/test_plan_quality.py -k check_plan_size

test-auto-fix-plan-commands:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/design/test_plan_quality.py -k auto_fix


test-parse-plan-commands:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/design/test_plan_quality.py -k parse_plan_commands


test-validate-plan-commands:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/design/test_plan_quality.py -k validate_plan

test-tally-plan-review:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/review/test_plan_review.py -q -k 'tally_plan_review or tally_error_rollback or degraded_empty or cap_reached'

test-findings-classification:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/design/scripts/test-findings-classification.sh

test-review-findings-classification:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/review/test_review_tally.py -k findings_classification

test-plan-review-loop:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/review/test_plan_review.py -q -k 'loop_dedup or migrated_collector or not_substantive_count or round_meta or emit_rejected or run_round_body_subprocess or run_round_body_in_process or (continuation and not step3_state)'

test-lib-design-round-artifacts:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/review/test_plan_review.py -q -k round_artifact

test-design-multi-round-integration:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-design-multi-round-integration.sh

test-step3-review-cap:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/design/scripts/test-step3-review-cap.sh

test-persist-retally-step3-env:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/review/test_plan_review.py -q -k persist_retally

test-run-step3-review:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/review/test_plan_review.py -q -k record_report_evidence

test-review-design-step3-loop:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/review/test_plan_review.py -q -k 'legacy_assets_removed or phase_driver_write_result_env_refuses_symlink or step3_loop_persist_envelope or postplan_validator or emits_round_provenance or zero_findings_degraded_stop'

test-step3-orchestrator-fence:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/design/scripts/test-step3-orchestrator-fence.sh

test-design-step3-mav:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/design/scripts/test-design-step3-mav.sh

test-design-step3-state:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/review/test_plan_review.py -q -k 'step3_state or step3_normalize or step3_read_result_env'

test-finalize-plan:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/review/test_plan_review.py -q -k finalize

test-step0b-router-flag-recovery:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/design/test_design_lifecycle.py -k design_route

test-brainstorm-prompts:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/design/scripts/test-brainstorm-prompts.sh

test-lint-readability-preamble:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/lint/test_lint_readability_preamble.py -q

test-lint-skill-md-flag-signature:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/lint/test_lint_skill_md_flag_signature.py -q

test-lint-skill-description-length:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_lint_skill_description_length.py -q

test-lint-codex-exec-auth:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/lint/test_lint_codex_exec_auth.py -q

test-lint-skill-closure-growth:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/lint/test_lint_skill_closure_growth.py -q

test-lint-skill-invocations:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/lint/test_lint_skill_invocations.py -q

test-lint-renderer-substitution-safety:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-lint-renderer-substitution-safety.sh


test-lint-bare-grep-probe:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-lint-bare-grep-probe.sh


test-launch-codex-exec:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/agents/test_agents.py -q -k launch_codex_exec

test-lint-awk-multibyte-regex:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-lint-awk-multibyte-regex.sh

test-scout-plan-archetypes-wrapper:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/design/test_plan_scout.py -q -k plan_wrapper

test-dispatch-plan-review-panel:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/review/test_plan_review_panel.py -q -k 'panel_dispatch and not usage'

test-render-final-summary:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/design/test_design_summary.py -k render_final_summary

test-render-final-summary-bash32:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/design/test_design_summary.py -k 'not render_final_summary'

test-implement-rebase-macro:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-implement-rebase-macro.sh

test-phantom-probe-with-warn:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/implement/test_phantom.py -q -k 'probe'

test-implement-step2-routing:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-implement-step2-routing.sh

test-implement-structure:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-implement-structure.sh

test-implement-step8-exit3-first-fixer:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-implement-step8-exit3-first-fixer.sh

test-oos-disposition-gate:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/issue/test_file_oos.py -q -k 'disposition_gate'

test-oos-file-conflict-deps:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/issue/test_file_oos.py -q -k 'file_conflict_deps'

test-oos-issue-cap:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/issue/test_file_oos.py -q -k 'issue_cap'

test-plan-adequacy-audit:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-plan-adequacy-audit.sh

test-implement-preflight:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/implement/test_preflight.py -q

test-implement-positional-issue:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-implement-positional-issue.sh

test-implement-fence-shape:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-implement-fence-shape.sh

test-architectural-guidelines-step:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/implement/scripts/test-architectural-guidelines-step.sh

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
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/implement/test_implement_dispatch.py -q -k 'not (step2_dispatch or codex_launcher or cursor_launcher or commit_main)'

test-step2-dispatch:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/implement/test_implement_dispatch.py -q -k step2_dispatch

# test-stall-recovery-report runs all split sections sequentially (local-dev convenience,
# NOT a test-harnesses prerequisite, see CARVE_OUTS in scripts/test-harness-shards-coverage.sh).
# CI shards use the three section targets below directly.
test-stall-recovery-report: test-stall-recovery-report-1 test-stall-recovery-report-2 test-stall-recovery-report-3

test-stall-recovery-report-1:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/state/test_stall_recovery.py -q -k 'retry_policy or normalize_issue_env or normalize_outcome or classify or record_attempt or init_attempts or main_accepts or global_flags'

test-stall-recovery-report-2:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/state/test_stall_recovery.py -q -k 'record_escalation or dedup_tier or compose_report or lint_subcommand or clear_stall or seed_terminal or sensitive_corpus or redact_text or report_dedup'

test-stall-recovery-report-3:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/state/test_stall_recovery.py -q -k 'validate_token or validate_terminal or validate_tier_b'

test-resolve-upstream-larch-repo:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-resolve-upstream-larch-repo.sh

test-file-failure-report-cross-repo:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-file-failure-report-cross-repo.sh


test-step-18:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/implement/scripts/test-step-18.sh

test-step-18b-final-report:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/report/test_final_report.py python/tests/git/test_pr_body.py -q -k step18b

test-cursor-implementer:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/implement/test_implement_dispatch.py -q -k cursor_launcher

test-codex-implementer:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/implement/test_implement_dispatch.py -q -k codex_launcher


test-git-commit-only:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/git/test_git.py -q -k 'commit_pathspec_file_nul_only'

test-refresh-run-logs:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/report/test_run_logs.py -k refresh_run_logs

test-launch-cursor-ci:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/agents/test_agents.py -q -k launch_cursor_ci

test-launch-claude-ci:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/agents/test_agents.py -q -k launch_claude_ci

test-launch-codex-ci:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/agents/test_agents.py -q -k launch_codex_ci

test-run-negotiation-round:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/agents/test_agents.py -q -k negotiation_round

test-run-external-agent-args:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/agents/test_agents.py -q -k run_external_agent_args

test-quick-mode-docs-sync:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-quick-mode-docs-sync.sh
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-quick-mode-docs-sync.sh --self-test

test-implement-finalize:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/state/test_finalize.py -q -k 'not cleanup'

test-implement-bootstrap:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/state/test_bootstrap.py -x -q -k 'write_base_session_env or tracking or emergency_bypass or resume_plan_tail or forked_plan or run_bootstrap or phase_coder'

test-implement-bootstrap-invoke:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/state/test_bootstrap.py -x -q -k 'invoke or cli_bootstrap or step0_wrapper or absorbed_degraded or absorbed_1r or degraded_prompt_required or phantom_stdout'

test-parse-bootstrap-routing-envelope:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/state/test_bootstrap.py -x -q -k 'filtered_envelope or parse_routing or routing_parser or degraded_prompt_required or phantom_stdout or absorbed_'

test-flush-execution-issues:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/issue/test_execution_issues.py -q -k flush

test-step-7a:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/implement/test_step_7a.py -q

test-step-8-ship:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/implement/scripts/test-step-8-ship.sh

test-step-8-oos-checkpoint:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/implement/scripts/test-step-8-oos-checkpoint.sh

test-post-tracking-issue:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/git/test_pr_body.py -q -k post_tracking

test-commit-implementation:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/implement/test_implement_dispatch.py -q -k commit_main

test-review-and-fix-commit-fixes:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/review/test_review_and_fix.py -q -k commit_fixes

test-generate-code-flow-diagram:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/git/test_pr_body.py -q -k generate_code_flow

test-refresh-execution-issues:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/issue/test_execution_issues.py -q -k refresh

test-review-and-fix-write-rejected:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/review/test_review_and_fix.py -q -k write_rejected

test-slack-issue-announce:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/git/test_pr_body.py -q -k slack_issue_announce

test-step-16-17:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/state/test_closeout.py -q

test-write-final-report:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/report/test_final_report.py python/tests/git/test_pr_body.py -q -k 'write_final_report or step18b or render_run_summary or post_tracking or generate_code_flow'

test-token-cost:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/report/test_report_tokens_cost.py -q -k token_cost

lint-retired-scripts:
	@$(PYTHON) -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' \
		|| (printf '%s\n' "ERROR: make lint-retired-scripts requires Python 3.11 or newer (PYTHON=$(PYTHON))" >&2; exit 1)
	$(PYTHON) python/cli.py lint retired-scripts

test-render-cost-line:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/report/test_report_tokens_cost.py -q -k render_cost_line

test-implement-cleanup-script:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/state/test_finalize.py -q -k 'cleanup and not cleanup_target_ok'

test-harness-shards-coverage:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-harness-shards-coverage.sh
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-harness-shards-coverage.sh --self-test

test-harness-timer:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/report/test_timing.py -q -k harness_mark

test-references-headers:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-references-headers.sh

test-research-structure:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-research-structure.sh

test-review-structure:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-review-structure.sh

test-gather-context:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/review/test_review_pipeline.py -k gather_context

test-review-core:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/review/test_review_pipeline.py -k '(review_core or write_proposer_sidecar) and not prune'

test-dispatch-panel-core:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/review/test_review_pipeline.py -k 'dispatch_panel_core or generic_codex_static_row'

test-dispatch-panel-core-dynamic:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/review/test_review_pipeline.py -k 'dispatch_panel_dynamic or pre_scouted_valid_dynamic or pre_scouted_empty_ok_static_only or pre_scouted_filtered_to_zero or implement_missing_producer or review_default_ignores_ambient_implement_tmpdir or producer_scout_warning or synthesize_dynamic_slots or generic_codex_static_row'

test-dispatch-panel-reuse:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/review/test_review_pipeline.py -k dispatch_panel_reuse

test-dispatch-panel-limits:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/review/test_review_pipeline.py -k dispatch_panel_limits

test-scout-dynamic-archetypes:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/design/test_plan_scout.py -q -k 'not plan_wrapper'

test-dispatch-plan-voters:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/review/test_plan_review_panel.py -q -k 'voter_dispatch and not usage'

test-prompt-template-invariants:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-prompt-template-invariants.sh


test-collect-findings:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/review/test_review_pipeline.py -k collect_findings

test-aggregate-findings:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/review/test_review_aggregate.py

test-prune-nit-findings:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/review/test_review_aggregate.py -k 'prune_nit'

test-tally-code-votes:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/review/test_review_tally.py -k '(tally_ or attributed_ballot or neutralized_ballot or ledger_reason) and not emit_tally'

.PHONY: test-check-reviewer-failure-threshold
test-check-reviewer-failure-threshold:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/review/test_review_pipeline.py -k 'check_reviewer_failure_threshold or python_surface_does_not_import_agents_waterfall or static_coverage_reason'

.PHONY: test-dispatch-code-voters-happy test-dispatch-code-voters-edge-and-r3-claude test-dispatch-code-voters-parse-rate-claude test-dispatch-code-voters-retry-codex-success test-dispatch-code-voters-retry-cursor test-dispatch-code-voters-retry-codex-fail-and-fallback test-dispatch-code-voters-regressions-r1-r2 test-dispatch-code-voters-regressions-r3-codex
test-dispatch-code-voters-happy:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/agents/test_agent_voters.py -k voter_happy

test-dispatch-code-voters-edge-and-r3-claude:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/agents/test_agent_voters.py -k voter_edge_and_r3_claude

test-dispatch-code-voters-regressions-r1-r2:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/agents/test_agent_voters.py -k voter_regressions_r1_r2

test-dispatch-code-voters-regressions-r3-codex:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/agents/test_agent_voters.py -k voter_regressions_r3_codex

test-dispatch-code-voters-parse-rate-claude:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/agents/test_agent_voters.py -k voter_retry_claude

test-dispatch-code-voters-retry-codex-success:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/agents/test_agent_voters.py -k voter_retry_codex_success

test-dispatch-code-voters-retry-cursor:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/agents/test_agent_voters.py -k voter_retry_cursor

test-dispatch-code-voters-retry-codex-fail-and-fallback:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/agents/test_agent_voters.py -k voter_retry_codex_fail_and_fallback

test-emit-tally:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/review/test_review_tally.py -k emit_tally

test-log-phase:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/review/test_review_tally.py -k log_phase

# test-review-and-fix runs all sections sequentially (local-dev convenience, NOT a test-harnesses
# prerequisite — see CARVE_OUTS in scripts/test-harness-shards-coverage.sh). CI uses the four
# section targets below instead: dispatch, convergence, parsers, and step5-starting-round.
test-review-and-fix:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/review/test_review_and_fix.py -q

test-review-and-fix-dispatch:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/review/test_review_and_fix.py -q -k dispatch

test-review-and-fix-convergence:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/review/test_review_and_fix.py -q -k convergence

test-review-and-fix-parsers:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/review/test_review_and_fix.py -q -k parsers

test-review-and-fix-step5-starting-round:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/review/test_review_and_fix.py -q -k starting_round

test-review-and-fix-step5:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/review/test_review_and_fix.py -q -k step5

test-render-findings-batch:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/research/test_research.py

test-synthesis-subagent:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/research/scripts/test-synthesis-subagent.sh

test-research-angle-prompts:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/research/scripts/test-research-angle-prompts.sh

test-subskill-anchors:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-subskill-anchors.sh

test-larch-log:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/report/test_run_logs.py -k larch_log_commit

test-larch-log-write-round:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/report/test_run_logs.py -k 'not (execution_issues or refresh_run_logs or larch_log_commit or capture_transcript or verify_completeness or manifest or batch or batches)'

test-capture-session-transcript:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/report/test_run_logs.py -k capture_transcript

test-verify-run-log-completeness:
	env -u LARCH_VERIFY_MANIFEST python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/report/test_run_logs.py -k verify_completeness

test-larch-logs-manifest:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/report/test_run_logs.py -k manifest

test-larch-logs-batches:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/report/test_run_logs.py -k '(batch or batches) and not execution_issues'

test-compose-plan-goals-test:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/design/test_plan_quality.py -k compose_plan_goals_test

test-run-step1-plan-log:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/design/test_design_step_log.py

test-compose-collector-failure-log:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/agents/test_review_dispatch.py -k compose_collector_failure_log

test-compute-pr-line-counts:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/report/test_tokens.py -q -k compute_pr_line_counts

test-compose-review-findings:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/review/test_compose_review.py







test-review-and-fix-check-changes:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/review/test_review_and_fix.py -q -k check_changes

test-check-mid-run-dirty-tree:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/state/test_dirty_tree.py -x -q -k 'not (scope_check or scope_marker)'

test-check-phantom-dirty:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/implement/test_phantom.py python/tests/git/test_git.py -q -k 'check_phantom_dirty'

test-check-reviewers:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/agents/test_agents.py -q -k 'check_reviewers or health_gate'

test-degraded-tools-gate:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/agents/test_agents.py -q -k degraded_tools

test-no-grouped-reuse-guard:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/agents/test_agent_waterfall.py -k grouped_reuse_guard

test-check-topology-rule-paths:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-check-topology-rule-paths.sh

test-external-tool-registry:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-external-tool-registry.sh

test-launch-review:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/agents/test_launch_review.py


test-launch-claude-subprocess:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/agents/test_agents.py -q -k launch_claude_subprocess

test-launch-claude-review:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/agents/test_agents.py -q -k launch_claude_review




test-dispatch-with-waterfall:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/agents/test_agent_waterfall.py

test-revise-plan-with-waterfall:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/design/test_plan_quality.py -k revise_waterfall

test-agent-model-args:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/agents/test_agents.py -q -k 'model_args and not launch_codex_exec'

test-effort-prose:
	python3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-effort-prose.sh



# Retired stub — kept for installed-plugin compat until checks.py ships without the
# lib-design-tmpdir _DIRECT_TARGET_RULES entry. NOT a test-harnesses prerequisite;
# see CARVE_OUTS in scripts/test-harness-shards-coverage.sh.
test-lib-design-tmpdir:
	@:

test-implement-fork-env:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/state/test_admission.py -x -q -k 'fork_env'

test-wait-for-reviewers:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/agents/test_review_dispatch.py -k wait

test-classify-diff-mode:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/agents/test_review_dispatch.py -k classify_diff

test-gather-branch-context:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/agents/test_review_dispatch.py -k gather_branch_context

test-run-external-agent:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/agents/test_agents.py -q -k 'not (negotiation_round or check_reviewers or health_gate or launch_claude_ci or launch_claude_review or launch_claude_subprocess or launch_codex_ci or launch_codex_exec or launch_cursor_ci or parse_codex_usage or run_external_agent_args or model_args or degraded_tools)'

lint-mermaid:
	if [ ! -f mermaid-lint/node_modules/.package-lock.json ]; then (cd mermaid-lint && npm ci); fi
	python3 python/cli.py lint mermaid-fences --changed-only
	bash scripts/test-pipe-sigpipe-safety.sh

agent-sync:
	python3 python/cli.py generate check
	python3 python/cli.py lint topology-rule-paths
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
# standalone for symmetry. See python/tests/research/test_research_eval.py.
test-eval-set-structure:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/research/test_research_eval.py

# Standalone offline regression harness for the `--baseline` flag handling
# in python/cli.py eval research (closes #441). NOT a `test-harnesses`
# prerequisite — the eval-research surface is opt-in operator
# instrumentation explicitly carved out from CI by repo contract
# (see the `test-eval-set-structure` target above, docs/linting.md,
# python/research_eval.py). Runs offline by PATH-stubbing claude
# so it works on machines without the real binaries.
# See python/tests/research/test_research_eval.py.
test-eval-research-baseline-flag:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/research/test_research_eval.py

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

.PHONY: test-design-stage-terminal-state test-design-failure-report test-design-step-final-summary test-design-step3-review test-design-step3-entry test-design-step0-init test-design-step5c test-design-step6 test-design-step-validator-autofix

test-design-stage-terminal-state:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/design/test_design_lifecycle.py -k 'stage_terminal_state or capture_contract or clarify_hard_halt'

test-design-failure-report:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/design/test_design_lifecycle.py -k failure_report

test-design-step-final-summary:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/design/test_design_lifecycle.py -k step_final_summary

test-design-step3-review:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/design/scripts/test-design-step3-review.sh

test-design-step3-entry:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/design/scripts/test-design-step3-entry.sh

test-design-step0-init:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/design/test_design_lifecycle.py -k 'step0_parse or step0_session or step0_route or step0_init or step0_abort or step0_ap or step0c or step1d7 or step1e or pause_save or bash_quoted or decode_bash_percent_q or degraded_tools or relay_degraded or require_design or resolve_repo or wrapper or core_style_ctx'

test-design-step5c:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/design/scripts/test-design-step5c.sh
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/design/test_design_lifecycle.py -k step5c

test-design-step6:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/design/test_design_lifecycle.py -k step6

test-design-step-validator-autofix:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest -q python/tests/design/test_plan_quality.py -k validator_autofix

test-design-step1d5:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/design/test_design_lifecycle.py -k 'step1d5'

test-design-log-ship:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/design/test_design_log_ship.py
