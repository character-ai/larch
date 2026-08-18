# Larch Makefile
# Thin wrapper around pre-commit. Linter definitions live in .pre-commit-config.yaml.

PYTHON ?= python3
CARGO_DENY_VERSION ?= 0.20.2
# `timing harness-mark` is Rust-owned (#8083). The dependency-free
# `larch-harness-mark` boundary lets developer and CI harnesses start that timer
# without compiling the released CLI. The separate target directory keeps this
# build out of `target/debug/larch`, which several harnesses probe to decide
# whether their Rust-owned assertions run; wrapping a harness must not change
# which assertions it selects. The standard-library-only sources compile with
# `rustc`, avoiding Cargo workspace setup on the first timer invocation. A
# temporary binary moves into place atomically so local parallel harnesses never
# execute a partial helper. The two values are sampled before that build starts
# so the timer can emit a cold-or-warm bootstrap diagnostic before the child.
HARNESS_MARK ?= sh -c 'timer=target/harness-mark/larch-harness-mark; LARCH_HARNESS_BOOTSTRAP_START_NS="$$($(PYTHON) -c "import time; print(time.time_ns())")"; if test ! -x "$$timer" || test Makefile -nt "$$timer" || test crates/larch-harness-mark/src/main.rs -nt "$$timer" || test crates/larch-harness-mark/src/harness_mark.rs -nt "$$timer"; then LARCH_HARNESS_BOOTSTRAP_KIND=cold; else LARCH_HARNESS_BOOTSTRAP_KIND=warm; fi; export LARCH_HARNESS_BOOTSTRAP_START_NS LARCH_HARNESS_BOOTSTRAP_KIND; if test "$$LARCH_HARNESS_BOOTSTRAP_KIND" = cold; then mkdir -p target/harness-mark || exit 1; build_directory=$$(mktemp -d target/harness-mark/.build.XXXXXX) || exit 1; if ! rustc --edition=2024 --crate-name larch_harness_mark crates/larch-harness-mark/src/main.rs -o "$$build_directory/larch-harness-mark"; then rmdir "$$build_directory" || true; exit 1; fi; if ! mv "$$build_directory/larch-harness-mark" "$$timer"; then rmdir "$$build_directory" || true; exit 1; fi; rmdir "$$build_directory" || true; fi; exec "$$timer" "$$@"' --

.PHONY: py-lint py-typecheck py-test lint lint-only test-harnesses test-harnesses-1 test-harnesses-2 shellcheck markdownlint jsonlint actionlint agent-lint agnix gitleaks trufflehog setup test-pipe-sigpipe-safety test-redact test-scrub-log-secrets test-redact-tmpdir-paths test-append-tool-failure test-append-execution-issue test-render-final-summary-bash32 test-collect-agent-results test-blocker test-anti-improvised-wakeup test-audit-runs test-sessionstart test-cleanup-sessionstart test-check-clean-tree test-check-main-sync test-check-scope-reduction-marker test-plan-review-scope-anchor test-persist-retally-step3-env test-lib-scope-anchor-handoff test-clarify-comment test-clarify-state test-check-stale-plugin test-cache-root-validation test-cache-key-discipline test-finalize-sanity-check test-audit-edit-write test-block-submodule test-deny-edit-write test-verify-skill-called test-hook-anti-read-poll test-extinct-notification-stack test-sessionstart-statusline test-hook-stop-fail-close test-classify-bump test-git-push test-lint-no-raw-stderr-after-quiet-init test-lint-readability-preamble test-anti-halt test-orchestrator-scope-sync test-alias-structure test-design-structure test-decompose-panel-dispatch test-decompose-aggregator test-decompose-file-issues test-design-driver test-design-clarify test-design-publish test-design-postplan-emit test-invoke-plan-validator test-file-design-oos test-emit-plan test-gate-b-dedup-plan test-trailer-helpers test-emit-design-plan-preview test-check-plan-size test-parse-plan-commands test-validate-plan-commands test-step3-review-cap test-run-step3-review test-plan-review-loop test-tally-plan-review test-finalize-plan test-step0b-router-flag-recovery test-brainstorm-prompts test-scout-plan-archetypes-wrapper test-dispatch-plan-review-panel test-render-final-summary test-implement-rebase-macro test-phantom-probe-with-warn test-implement-step2-routing test-implement-structure test-implement-step8-exit3-first-fixer test-oos-disposition-gate test-step-8-oos-checkpoint test-plan-adequacy-audit test-implement-preflight test-implement-positional-issue test-implement-fence-shape test-architectural-guidelines-step test-implement-timing-rehydration test-implement-cleanup-roundtrip test-implement-relevant-checks-anti-halt test-implement-anti-halt test-step2-dispatch test-refresh-run-logs  test-run-negotiation-round test-launch-claude-subprocess test-launch-claude-review test-dispatch-with-waterfall test-run-external-agent test-run-external-agent-args test-quick-mode-docs-sync test-implement-bootstrap test-implement-bootstrap-invoke test-implement-finalize test-flush-execution-issues test-post-tracking-issue test-commit-implementation test-review-and-fix-commit-fixes test-generate-code-flow-diagram test-review-and-fix-write-rejected test-slack-issue-announce test-step-16-17 test-write-final-report write-final-report-py-harness write-final-report-bash-harness test-step-18b-final-report test-token-cost test-render-cost-line test-implement-cleanup-script test-harness-shards-coverage test-references-headers test-research-structure test-review-structure test-gather-context test-gather-branch-context test-review-core test-dispatch-panel-core test-dispatch-panel-core-dynamic test-dispatch-panel-reuse test-dispatch-panel-limits test-scout-dynamic-archetypes test-dispatch-plan-voters test-collect-findings test-aggregate-findings test-prune-nit-findings test-tally-code-votes test-check-reviewer-failure-threshold test-dispatch-code-voters test-emit-tally test-log-phase test-review-and-fix test-review-and-fix-dispatch test-review-and-fix-convergence test-review-and-fix-parsers test-synthesis-subagent test-research-angle-prompts test-subskill-anchors test-tracking-issue-write test-larch-log test-capture-session-transcript test-larch-logs-manifest test-larch-logs-batches test-compose-plan-goals-test test-compose-collector-failure-log test-tracking-issue-summary test-tracking-issue-read-sentinel test-compose-review-findings test-token-tally test-token-ledger test-token-report test-timing-ledger test-token-vendor-scrapers test-token-claude-source test-review-and-fix-check-changes test-check-mid-run-dirty-tree test-check-phantom-dirty test-check-reviewers test-degraded-tools-gate test-external-tool-registry test-agent-model-args test-effort-prose test-launch-review test-lib-design-tmpdir test-get-issue-context eval-research test-wait-for-reviewers test-classify-diff-mode test-analyze test-compute-pr-line-counts test-review-and-fix-step5 test-run-step1-plan-log test-run-step2-dispatch test-prompt-template-invariants test-verify-run-log-completeness test-design-log-publish test-fetch-combinable-issues-filter test-legacy-title-prefix-literals-scope test-pause-skill test-fluff-analysis test-rejected-analysis

.PHONY: test-findings-classification test-review-findings-classification test-review-and-fix-step5-starting-round test-file-bug-structure test-learn-from-bugs-structure
.PHONY: test-prompt-template-invariants
.PHONY: test-larch-log-write-round
.PHONY: test-scout-dynamic-archetypes
.PHONY: test-plan-review test-plan-review-panel
.PHONY: test-git-commit-only
.PHONY: test-promote-release test-release-finish test-release-prepare test-release-set-version
.PHONY: test-auto-fix-plan-commands test-design-step2b-drafter test-gate-b-apply-mode
.PHONY: test-token-report-dedup test-token-cost-per-bucket test-render-cost-line-realism test-render-cost-line-callsites test-token-report-summary-format test-parse-bootstrap-routing-envelope lint-retired-scripts
.PHONY: agent-sync
.PHONY: test-hook-deny-run-in-background test-bgjob
.PHONY: test-step-7a step-7a-bash-harness test-step-8-oos-checkpoint
.PHONY: test-oos-disposition-gate oos-disposition-gate-bash-harness
.PHONY: test-flush-execution-issues flush-execution-issues-bash-harness
.PHONY: test-review-dispatch-panel
.PHONY: test-stall-recovery-report test-stall-recovery-report-1 test-stall-recovery-report-2 test-stall-recovery-report-3 test-step-18b-final-report
.PHONY: test-resolve-upstream-larch-repo test-file-failure-report-cross-repo
.PHONY: test-design-pause-resume
.PHONY: test-design-step1d5 test-design-log-ship
.PHONY: test-review-design-step3-loop
.PHONY: test-read-result-env test-parse-design-argv
.PHONY: test-launch-codex-exec test-launch-drafters test-launch-ci-fixers test-implement-launchers
.PHONY: test-design-multi-round-integration test-lib-design-round-artifacts test-step3-orchestrator-fence test-design-step3-state test-design-step3-mav
.PHONY: test-no-grouped-reuse-guard test-review-and-fix-record-timing test-review-and-fix-step5-loop-timing test-record-plan-review-round-timing test-reviewer-prune test-lib-prune-decision test-fluff-analysis-corpus test-voter-calibration test-difficulty-calibration
# CI splits `lint` into `lint-only` (pre-commit) and `test-harnesses`
# (regression harnesses). `lint` remains the local-dev convenience target
# that runs both, defined in terms of the two split targets to prevent drift.
lint: test-harnesses rust-lint lint-only

py-lint:
	@$(PYTHON) -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' \
		|| (printf '%s\n' "ERROR: make py-lint requires Python 3.11 or newer (PYTHON=$(PYTHON))" >&2; exit 1)
	cd python && ruff check .
	cd python && pyright

py-typecheck:
	@$(PYTHON) -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' \
		|| (printf '%s\n' "ERROR: make py-typecheck requires Python 3.11 or newer (PYTHON=$(PYTHON))" >&2; exit 1)
	cd python && pyright

py-test:
	@$(PYTHON) -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' \
		|| (printf '%s\n' "ERROR: make py-test requires Python 3.11 or newer (PYTHON=$(PYTHON))" >&2; exit 1)
	# --durations=0 emits per-test timing so CI shards (PYTEST_SHARD_ID /
	# PYTEST_SHARD_COUNT, see python/conftest.py) can be rebalanced by wall time.
	cd python && $(PYTHON) -m pytest --durations=0

.PHONY: rust-check rust-fmt rust-clippy rust-build rust-test rust-deny rust-lint

rust-check:
	python3 python/cli.py checks rust-clippy --repo-root "$$(pwd -P)" --changed-from-git

rust-fmt:
	cargo fmt --all -- --check

rust-clippy:
	cargo clippy --workspace --all-targets --all-features --locked -- -D warnings

rust-build:
	cargo build --workspace --all-targets --all-features --locked

rust-test:
	cargo test --workspace --all-features --locked

rust-lint:
	cargo run --quiet --locked --package larch-cli -- lint all

rust-deny:
	@test "$$(cargo deny --version)" = "cargo-deny $(CARGO_DENY_VERSION)" \
		|| (printf '%s\n' "ERROR: make rust-deny requires cargo-deny $(CARGO_DENY_VERSION)" >&2; exit 1)
	cargo deny --locked --all-features check

lint-only:
	pre-commit run --all-files

# Bash regression-harness shards (#1294, #1585, #1911, #2080, #2252, #2262, #2291, #2349, #2366,
# #2386, #5429 — originally 20 shards mixing pytest wrappers with bash scripts; collapsed to 6, then 5
# bash-only shards after pruning 193 pytest-wrapper targets that duplicated the python-tests job; then to two
# measured Bash-only shards after empty cells accumulated).
# Each test-harnesses-N rule below stays on a single physical line (no `\` continuations); the
# drift-detection script `scripts/test-harness-shards-coverage.sh` parses these lines literally.
# Shard members must be direct Bash leaves (recipe-bearing test-* or *-bash-harness
# with no pytest or Cargo invocation). Cargo-focused targets remain available for
# local debugging; rust-full owns their required CI coverage.
# Public aggregates (pytest + smoke) and pytest-only leaves stay out of shard lists; run via
# make py-test or the local developer aggregate targets.
# New bash harnesses get appended to one shard line.
test-harnesses: test-harnesses-1 test-harnesses-2

test-harnesses-1: test-hook-anti-read-poll

test-harnesses-2: test-harness-shards-coverage test-prompt-template-invariants test-file-failure-report-cross-repo test-gate-b-apply-mode test-read-result-env test-sessionstart test-deny-edit-write test-design-step3b-tail test-token-vendor-scrapers test-external-tool-registry test-resolve-upstream-larch-repo test-cache-root-validation test-block-submodule test-cache-key-discipline test-architectural-guidelines-step test-references-headers test-extinct-notification-stack test-pipe-sigpipe-safety test-hook-stop-fail-close test-hook-deny-run-in-background test-quick-mode-docs-sync test-check-stale-plugin oos-disposition-gate-bash-harness test-render-cost-line-callsites test-plan-adequacy-audit write-final-report-bash-harness step-7a-bash-harness test-implement-timing-rehydration test-pause-skill flush-execution-issues-bash-harness test-audit-edit-write test-cleanup-sessionstart test-subskill-anchors test-rejected-analysis test-implement-anti-halt test-sessionstart-statusline test-step-8-oos-checkpoint test-design-clarify test-implement-fence-shape test-legacy-title-prefix-literals-scope test-implement-step2-routing test-triage-structure test-anti-halt test-implement-rebase-macro test-research-angle-prompts test-implement-step8-exit3-first-fixer test-orchestrator-scope-sync test-brainstorm-prompts test-synthesis-subagent test-implement-cleanup-roundtrip test-anti-improvised-wakeup test-implement-relevant-checks-anti-halt test-fluff-analysis-corpus test-implement-positional-issue test-effort-prose

test-pipe-sigpipe-safety:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-pipe-sigpipe-safety.sh

test-redact:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest -q python/tests/core/test_redact.py -k 'not (scrub_log_secrets or tmpdir or operator)'

test-scrub-log-secrets:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest -q python/tests/core/test_redact.py -k scrub_log_secrets

test-redact-tmpdir-paths:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest -q python/tests/core/test_redact.py -k 'tmpdir or operator'

test-reviewer-prune:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test review_commands reviewer_prune

test-lib-prune-decision:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --bin larch review_core_commands
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test review_core_contract

test-append-tool-failure:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest -q python/tests/report/test_run_logs.py -k execution_issues

test-append-execution-issue:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test execution_issues_contract append_

test-collect-agent-results:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test collector_commands

test-analyze:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --bin larch analyze_issues_commands

test-fluff-analysis:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test fluff_analysis_parity

test-rejected-analysis:
	$(HARNESS_MARK) --label $@ -- bash skills/rejected-analysis/scripts/test-rejected-analysis.sh

test-difficulty-calibration:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test difficulty_calibration_parity

test-voter-calibration:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test voter_calibration_parity

test-fluff-analysis-corpus:
	$(HARNESS_MARK) --label $@ -- bash skills/fluff-analysis/scripts/test-fluff-analysis-corpus.sh

test-fetch-combinable-issues-filter:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli combine_issues_commands --bin larch

test-legacy-title-prefix-literals-scope:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-legacy-title-prefix-literals-scope.sh

test-blocker:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-core --lib prose_blockers

test-anti-improvised-wakeup:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-anti-improvised-wakeup.sh

test-audit-runs:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test audit_runs


test-sessionstart:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-sessionstart-health.sh

test-cleanup-sessionstart:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-cleanup-sessionstart.sh

test-check-clean-tree:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test cli clean_tree_reports_clean_and_tracked_or_untracked_dirty_state

test-check-main-sync:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/git/test_check_main_sync.py python/tests/git/test_git.py -q -k 'check_main_sync'



test-check-scope-reduction-marker:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test dirty_tree scope_

test-plan-review:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test plan_review_loop_commands

test-plan-review-panel:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test plan_review_dispatch

test-plan-review-scope-anchor:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test plan_review_loop_commands utility_and_persistence

test-lib-scope-anchor-handoff:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/rendering/test_rendering.py -q

test-clarify-comment:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/design/test_clarify.py -q -k comment

test-clarify-state:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/design/test_clarify.py -q -k 'not comment'

test-check-stale-plugin:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-check-stale-plugin.sh


test-cache-root-validation:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-cache-root-validation.sh

test-cache-key-discipline:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-cache-key-discipline.sh

test-finalize-sanity-check:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/implement/test_finalize.py -q -k cleanup_target_ok


test-audit-edit-write:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-audit-edit-write.sh

test-block-submodule:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-block-submodule-edit.sh


test-deny-edit-write:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-deny-edit-write.sh




test-token-tally:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/report/test_tokens.py -q -k tally

test-token-ledger:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/report/test_tokens.py -q -k ledger

test-token-report:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test token_commands report_

test-token-report-dedup:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/report/test_tokens.py -q -k dedupe

test-token-cost-per-bucket:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/report/test_report_tokens_cost.py -q -k bucket

test-render-cost-line-realism:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/report/test_report_tokens_cost.py -q -k 'not (render_cost_line or token_cost or bucket)'

test-render-cost-line-callsites:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-render-cost-line-callsites.sh

test-token-report-summary-format:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test token_commands report_renders_recorded_json_markdown_and_compact_modes

test-timing-ledger:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/report/test_timing.py -q

test-review-and-fix-record-timing:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test review_and_fix_commands

test-review-and-fix-step5-loop-timing:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test review_and_fix_commands

test-record-plan-review-round-timing:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test plan_review_loop_commands utility_and_persistence



test-token-vendor-scrapers:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-token-vendor-scrapers.sh

test-token-claude-source:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/report/test_tokens.py -q -k claude_source

test-verify-skill-called:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test developer_tooling_commands -- verify_skill_called


test-extinct-notification-stack:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-extinct-notification-stack.sh

test-hook-anti-read-poll:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-hook-anti-read-poll.sh


test-sessionstart-statusline:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-sessionstart-statusline.sh

test-hook-stop-fail-close:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-hook-stop-fail-close.sh


test-hook-deny-run-in-background:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-hook-deny-run-in-background.sh


# These Rust integration-test entry points are standalone aliases, not
# test-harnesses prerequisites; see CARVE_OUTS in
# scripts/test-harness-shards-coverage.sh.
test-bgjob:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test bgjob

test-classify-bump:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test release_prepare

test-release-prepare:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test release_prepare

test-release-set-version:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test release_version

test-release-finish:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --bin larch release_publish::tests
	$(HARNESS_MARK) --label $@-verify-main -- python3 -m pytest python/tests/release/test_release.py -q

# This Rust-only entry point is a standalone alias, not a test-harnesses
# prerequisite; see CARVE_OUTS in scripts/test-harness-shards-coverage.sh.
test-promote-release:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --bin larch release_publish::tests::promotion


test-git-push:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/git/test_push.py -q -k 'branch_push or branch_main or propagates_final_exit'


test-anti-halt:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-anti-halt-banners.sh

test-orchestrator-scope-sync:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-orchestrator-scope-sync.sh


test-alias-structure:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/skills/test_skill_structure.py -k 'alias_structure' -q

test-file-bug-structure:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/skills/test_skill_structure.py -k 'file_bug_structure' -q

test-learn-from-bugs-structure:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/skills/test_skill_structure.py -k 'learn_from_bugs_structure' -q

test-design-structure:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/skills/test_skill_structure.py -k 'design_structure_pin or design_structure_specialized' -q

test-design-pause-resume:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/design/test_design_pause.py

test-pause-skill:
	$(HARNESS_MARK) --label $@ -- bash skills/pause/scripts/test-pause-skill.sh

test-decompose-panel-dispatch:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/design/test_decompose.py -q -k '(panel or degraded) and not aggregate'

test-decompose-aggregator:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/design/test_decompose.py -q -k aggregate

test-decompose-file-issues:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/design/test_decompose.py -q -k 'prepare or annotate or close_original'

test-design-step2b-drafter:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest -q python/tests/design/test_design_lifecycle.py -k 'step2a or step2b or guideline or dialectic_instructions or postplan_decide or postplan_executor'

test-design-driver:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/design/test_design_lifecycle.py -k 'phase_driver or design_read_result_env or design_driver'

test-design-clarify:
	$(HARNESS_MARK) --label $@ -- bash skills/design/scripts/test-design-clarify.sh

test-design-publish:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/design/test_design_publish.py

test-design-postplan-emit:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/design/test_design_postplan.py

test-read-result-env:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-read-result-env.sh

test-parse-design-argv:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/design/test_design_argv.py


test-invoke-plan-validator:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest -q python/tests/design/test_plan_quality.py -k validate_plan

test-file-design-oos:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/design/test_design_oos.py

test-design-log-publish:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/design/test_design_log_publish_flow.py



test-emit-plan:
	$(HARNESS_MARK) --label $@ -- cargo test --quiet --locked --package larch-cli --test plan_review_commands emit_and_rejected_findings_bytes_are_frozen

test-gate-b-dedup-plan:
	$(HARNESS_MARK) --label $@ -- cargo test --quiet --locked --package larch-cli --test plan_review_commands gate_b_lines_and_dedup_wire_are_frozen

test-gate-b-apply-mode:
	$(HARNESS_MARK) --label $@ -- bash skills/design/scripts/test-gate-b-apply-mode.sh

test-trailer-helpers:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest -q python/tests/design/test_plan_quality.py -k optional_trailer

test-emit-design-plan-preview:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test plan_review_loop_commands preview_and_finalize
test-check-plan-size:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest -q python/tests/design/test_plan_quality.py -k check_plan_size

test-auto-fix-plan-commands:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest -q python/tests/design/test_plan_quality.py -k auto_fix


test-parse-plan-commands:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest -q python/tests/design/test_plan_quality.py -k parse_plan_commands


test-validate-plan-commands:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest -q python/tests/design/test_plan_quality.py -k validate_plan

test-tally-plan-review:
	$(HARNESS_MARK) --label $@ -- cargo test --quiet --locked --package larch-cli --test plan_review_commands tally

test-findings-classification:
	@if [ -z "$${LARCH_BINARY:-}" ]; then \
		cargo build --quiet --locked --package larch-cli --bin larch || exit 1; \
		export LARCH_BINARY="$$(pwd -P)/target/debug/larch"; \
	fi; \
	$(HARNESS_MARK) --label $@ -- bash skills/design/scripts/test-findings-classification.sh

test-review-findings-classification:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test review_tally_commands

test-plan-review-loop:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test plan_review_loop_commands loop_transcript

test-lib-design-round-artifacts:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test plan_review_loop_commands utility_and_persistence

test-design-multi-round-integration:
	$(HARNESS_MARK) --label $@-rust -- cargo test --locked --package larch-cli --test plan_review_loop_commands loop_transcript
	$(HARNESS_MARK) --label $@ -- bash scripts/test-design-multi-round-integration.sh

test-step3-review-cap:
	$(HARNESS_MARK) --label $@-rust -- cargo test --locked --package larch-cli --test plan_review_loop_commands loop_transcript
	$(HARNESS_MARK) --label $@ -- bash skills/design/scripts/test-step3-review-cap.sh

test-persist-retally-step3-env:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test plan_review_loop_commands utility_and_persistence

test-run-step3-review:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test plan_review_loop_commands loop_transcript

test-review-design-step3-loop:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test plan_review_loop_commands loop_transcript

test-step3-orchestrator-fence:
	$(HARNESS_MARK) --label $@-rust -- cargo test --locked --package larch-cli --test plan_review_loop_commands normalize
	$(HARNESS_MARK) --label $@ -- bash skills/design/scripts/test-step3-orchestrator-fence.sh

test-design-step3-mav:
	$(HARNESS_MARK) --label $@-rust -- cargo test --locked --package larch-cli --test plan_review_loop_commands utility_and_persistence
	$(HARNESS_MARK) --label $@ -- bash skills/design/scripts/test-design-step3-mav.sh

test-design-step3-state:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test plan_review_loop_commands step3_state
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test plan_review_loop_commands normalize

test-finalize-plan:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test plan_review_loop_commands preview_and_finalize

test-step0b-router-flag-recovery:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/design/test_design_lifecycle.py -k design_route

test-brainstorm-prompts:
	$(HARNESS_MARK) --label $@ -- bash skills/design/scripts/test-brainstorm-prompts.sh

# This Rust-only entry point is a standalone alias, not a test-harnesses
# prerequisite; see CARVE_OUTS in scripts/test-harness-shards-coverage.sh.
test-launch-codex-exec:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test drafter_commands codex_exec

test-scout-plan-archetypes-wrapper:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/design/test_plan_scout.py -q -k plan_wrapper

test-dispatch-plan-review-panel:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test plan_review_dispatch

test-render-final-summary:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/design/test_design_summary.py -k render_final_summary

test-render-final-summary-bash32:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/design/test_design_summary.py -k 'not render_final_summary'

test-implement-rebase-macro:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-implement-rebase-macro.sh

test-phantom-probe-with-warn:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test cli phantom_probe

test-implement-step2-routing:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-implement-step2-routing.sh

test-implement-structure:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/skills/test_skill_structure.py -k 'implement_structure' -q


test-implement-step8-exit3-first-fixer:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-implement-step8-exit3-first-fixer.sh

# Behavioral authority moved to Rust with #8178: the five `oos` verbs are
# covered by `cargo test --package larch-cli --bin larch oos_commands` and
# `cargo test --package larch-core --lib issue::oos`, which the Rust CI job
# already runs. This aggregate keeps the delegation smoke.
test-oos-disposition-gate: oos-disposition-gate-bash-harness

# Delegation smoke for the two disposition wrappers; behavior lives in
# crates/larch-cli/src/oos_commands.rs.
oos-disposition-gate-bash-harness:
	$(HARNESS_MARK) --label $@ -- bash skills/implement/scripts/test-oos-disposition-gate.sh

test-plan-adequacy-audit:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-plan-adequacy-audit.sh

test-implement-preflight:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test implement_admission_migrated_parity

test-implement-positional-issue:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-implement-positional-issue.sh

test-implement-fence-shape:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-implement-fence-shape.sh

test-architectural-guidelines-step:
	$(HARNESS_MARK) --label $@ -- bash skills/implement/scripts/test-architectural-guidelines-step.sh

test-implement-timing-rehydration:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-implement-timing-rehydration.sh

test-implement-cleanup-roundtrip:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-implement-cleanup-roundtrip.sh


test-implement-relevant-checks-anti-halt:
	$(HARNESS_MARK) --label $@ -- bash skills/implement/scripts/test-implement-relevant-checks-anti-halt.sh

test-implement-anti-halt:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-implement-anti-halt.sh


test-run-step2-dispatch:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/implement/test_implement_dispatch.py -q -k 'not (step2_dispatch or codex_launcher or cursor_launcher or commit_main)'

test-step2-dispatch:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/implement/test_implement_dispatch.py -q -k step2_dispatch

# test-stall-recovery-report runs the Rust contract-lint test and focused Rust
# core/adapter suites. The aggregate and Rust aliases are standalone carve-outs;
# see CARVE_OUTS in scripts/test-harness-shards-coverage.sh.
test-stall-recovery-report: test-stall-recovery-report-1 test-stall-recovery-report-2 test-stall-recovery-report-3

test-stall-recovery-report-1:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test session_closeout stall_recovery_lint_uses_the_rust_owned_contract_check

test-stall-recovery-report-2:
	$(HARNESS_MARK) --label $@ -- cargo test --locked -p larch-core stall_recovery

test-stall-recovery-report-3:
	$(HARNESS_MARK) --label $@ -- cargo test --locked -p larch-adapters stall_recovery

test-resolve-upstream-larch-repo:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-resolve-upstream-larch-repo.sh

test-file-failure-report-cross-repo:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-file-failure-report-cross-repo.sh



# This Rust-only entry point is a standalone alias, not a test-harnesses
# prerequisite; see CARVE_OUTS in scripts/test-harness-shards-coverage.sh.
test-step-18b-final-report:
	$(HARNESS_MARK) --label $@ -- cargo test -p larch-cli --bin larch final_report_commands

# This Rust-only entry point is a standalone alias, not a test-harnesses
# prerequisite; see CARVE_OUTS in scripts/test-harness-shards-coverage.sh.
test-implement-launchers:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test implement_launcher_commands


test-git-commit-only:
	$(HARNESS_MARK) --label $@ -- cargo test --locked -p larch-cli --test git_commands nul_pathspec_only_commit_preserves_unrelated_staged_content

# `run-log refresh` is Rust-owned (#8078), so this is a standalone
# Rust integration-test alias, not a test-harnesses prerequisite; see CARVE_OUTS
# in scripts/test-harness-shards-coverage.sh.
test-refresh-run-logs:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test run_log_flush refresh_

# This Rust-only entry point is a standalone alias, not a test-harnesses
# prerequisite; see CARVE_OUTS in scripts/test-harness-shards-coverage.sh.
test-launch-ci-fixers:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test ci_launcher_commands

# This Rust-only entry point is a standalone alias, not a test-harnesses
# prerequisite; see CARVE_OUTS in scripts/test-harness-shards-coverage.sh.
test-launch-drafters:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test drafter_commands drafter

# This Rust-only entry point is a standalone alias, not a test-harnesses
# prerequisite; see CARVE_OUTS in scripts/test-harness-shards-coverage.sh.
test-run-negotiation-round:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test drafter_commands negotiation_round

# This Rust-only entry point is a standalone alias, not a test-harnesses
# prerequisite; see CARVE_OUTS in scripts/test-harness-shards-coverage.sh.
test-run-external-agent-args:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test agent_commands run_external_agent_rejects_invalid_arguments_before_creating_sidecars

test-quick-mode-docs-sync:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-quick-mode-docs-sync.sh
	$(HARNESS_MARK) --label $@ -- bash scripts/test-quick-mode-docs-sync.sh --self-test

test-implement-finalize:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/implement/test_finalize.py -q -k 'not cleanup'

test-implement-bootstrap:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --bin larch implement_bootstrap_continuation::tests
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test parity bootstrap_invoke_clean_install_runs_native_plan_coder_and_tail

test-implement-bootstrap-invoke:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --bin larch bootstrap_commands::tests
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test parity bootstrap_invoke_stdout_is_pinned_for_fresh_and_resume_paths

test-parse-bootstrap-routing-envelope:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --bin larch bootstrap_commands::tests

# Behavioral authority moved to Rust with #8176: the verbs are covered by
# `cargo test --package larch-cli --bin larch execution_issue_commands`, which
# the Rust CI job already runs. This aggregate keeps the delegation smoke.
test-flush-execution-issues: flush-execution-issues-bash-harness

# Delegation smoke for flush-execution-issues.sh; behavior lives in the Rust
# execution_issue_commands unit tests.
flush-execution-issues-bash-harness:
	$(HARNESS_MARK) --label $@ -- bash skills/implement/scripts/test-flush-execution-issues.sh

test-step-7a: step-7a-bash-harness

# Delegation smoke for step-7a.sh; behavior lives in the Rust owner
# crates/larch-cli/src/implement_review_commands.rs.
step-7a-bash-harness:
	$(HARNESS_MARK) --label $@ -- bash skills/implement/scripts/test-step-7a.sh


test-step-8-oos-checkpoint:
	$(HARNESS_MARK) --label $@ -- bash skills/implement/scripts/test-step-8-oos-checkpoint.sh

test-post-tracking-issue:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/git/test_pr_body.py -q -k post_tracking

test-commit-implementation:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/implement/test_implement_dispatch.py -q -k commit_main

test-review-and-fix-commit-fixes:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test review_and_fix_commands self_review_snapshot_commits_only_its_delta

test-generate-code-flow-diagram:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/git/test_pr_body.py -q -k generate_code_flow

test-review-and-fix-write-rejected:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test review_and_fix_commands

test-slack-issue-announce:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/git/test_pr_body.py -q -k slack_issue_announce

test-step-16-17:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/implement/test_closeout.py -q

test-write-final-report: write-final-report-py-harness write-final-report-bash-harness

write-final-report-py-harness:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/git/test_pr_body.py -q -k 'render_run_summary or post_tracking or generate_code_flow'

# Delegation smoke for write-final-report.sh; behavior lives in write-final-report-py-harness.
write-final-report-bash-harness:
	$(HARNESS_MARK) --label $@ -- bash skills/implement/scripts/test-write-final-report.sh

test-token-cost:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test token_commands cost_and_render_cost_line_preserve_cli_contracts

lint-retired-scripts:
	cargo run --quiet --locked --package larch-cli -- lint rule retired-scripts

test-render-cost-line:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test token_commands cost_and_render_cost_line_preserve_cli_contracts

test-implement-cleanup-script:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/implement/test_finalize.py -q -k 'cleanup and not cleanup_target_ok'

test-harness-shards-coverage:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-harness-shards-coverage.sh
	$(HARNESS_MARK) --label $@ -- bash scripts/test-harness-shards-coverage.sh --self-test


test-references-headers:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-references-headers.sh

test-research-structure:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/skills/test_skill_structure.py -k 'research_structure' -q

.PHONY: test-triage-structure
test-triage-structure:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-triage-structure.sh

test-review-structure:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/skills/test_skill_structure.py -k 'review_structure' -q

test-gather-context:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test review_commands gather_context

test-review-core:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --bin larch review_core_commands
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test review_core_contract

test-dispatch-panel-core:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test review_dispatch_panel

test-dispatch-panel-core-dynamic:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test review_dispatch_panel

test-dispatch-panel-reuse:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test review_dispatch_panel

test-dispatch-panel-limits:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test review_dispatch_panel

# Manual direct wrapper for the Rust integration harness. It keeps the shell
# contract independently runnable while rust-full owns its CI execution.
test-review-dispatch-panel:
	cargo build --locked --package larch-cli
	$(HARNESS_MARK) --label $@ -- env LARCH_BINARY=target/debug/larch bash scripts/test-review-dispatch-panel.sh

test-scout-dynamic-archetypes:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/design/test_plan_scout.py -q -k 'not plan_wrapper'

test-dispatch-plan-voters:
	cargo build --locked --package larch-cli
	$(HARNESS_MARK) --label $@ -- env LARCH_BINARY=target/debug/larch bash scripts/test-plan-review-dispatch.sh

build-larch-cli:
	cargo build --locked --package larch-cli

.PHONY: build-larch-cli
test-prompt-template-invariants: build-larch-cli
	$(HARNESS_MARK) --label $@ -- env LARCH_BINARY="$(CURDIR)/target/debug/larch" bash scripts/test-prompt-template-invariants.sh


test-collect-findings:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test review_commands collect_findings

test-aggregate-findings:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test review_commands aggregate_findings

test-prune-nit-findings:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test review_commands prune_nit_findings

test-tally-code-votes:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test review_tally_commands tally_

.PHONY: test-check-reviewer-failure-threshold
test-check-reviewer-failure-threshold:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test review_commands reviewer_failure_threshold

.PHONY: test-dispatch-code-voters
test-dispatch-code-voters:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test voter_dispatch_commands

test-emit-tally:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test review_tally_commands emit_tally

test-log-phase:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test review_tally_commands log_phase

# test-review-and-fix is a local convenience target (not a test-harnesses
# prerequisite — see CARVE_OUTS in scripts/test-harness-shards-coverage.sh).
test-review-and-fix:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test review_and_fix_commands

test-review-and-fix-dispatch:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test review_and_fix_commands

test-review-and-fix-convergence:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test review_and_fix_commands

test-review-and-fix-parsers:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test review_and_fix_commands

test-review-and-fix-step5-starting-round:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test review_and_fix_commands step5_preflight_failure_persists_the_stall_envelope

test-review-and-fix-step5:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test review_and_fix_commands step5_preflight_failure_persists_the_stall_envelope

test-synthesis-subagent:
	$(HARNESS_MARK) --label $@ -- bash skills/research/scripts/test-synthesis-subagent.sh

test-research-angle-prompts:
	$(HARNESS_MARK) --label $@ -- bash skills/research/scripts/test-research-angle-prompts.sh

test-subskill-anchors:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-subskill-anchors.sh

test-larch-log:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest -q python/tests/report/test_run_logs.py -k larch_log_commit

test-larch-log-write-round:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest -q python/tests/report/test_run_logs.py -k 'not (execution_issues or refresh_run_logs or larch_log_commit or capture_transcript or verify_completeness or manifest or batch or batches)'

# `run-log capture-transcript` is Rust-owned (#8078), so this is a
# standalone Rust integration-test alias, not a test-harnesses prerequisite;
# see CARVE_OUTS in scripts/test-harness-shards-coverage.sh.
test-capture-session-transcript:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test run_log_flush capture_

# `run-log verify-completeness` is Rust-owned (#8073), so this is a standalone
# Rust integration-test alias, not a test-harnesses prerequisite; see CARVE_OUTS
# in scripts/test-harness-shards-coverage.sh.
test-verify-run-log-completeness:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test run_log_entry verify_completeness

test-larch-logs-manifest:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest -q python/tests/report/test_run_logs.py -k manifest

test-larch-logs-batches:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest -q python/tests/report/test_run_logs.py -k '(batch or batches) and not execution_issues'

test-compose-plan-goals-test:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest -q python/tests/design/test_plan_quality.py -k compose_plan_goals_test

test-run-step1-plan-log:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/design/test_design_step_log.py

test-compose-collector-failure-log:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test agent_commands compose_collector_failure_log_redacts_and_writes_sections

test-compute-pr-line-counts:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/report/test_tokens.py -q -k compute_pr_line_counts

test-compose-review-findings:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test review_compose_contract







test-review-and-fix-check-changes:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test review_and_fix_commands

test-check-mid-run-dirty-tree:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test dirty_tree

test-check-phantom-dirty:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test cli check_phantom_dirty

# Rust CLI smoke aliases remain standalone; see CARVE_OUTS in
# scripts/test-harness-shards-coverage.sh.
test-check-reviewers:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test reviewer_availability_commands

test-degraded-tools-gate:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test reviewer_availability_commands degraded_tools_gate

test-no-grouped-reuse-guard:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test waterfall_commands grouped_reuse

test-external-tool-registry:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-external-tool-registry.sh

test-launch-review:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/agents/test_launch_review.py


test-launch-claude-subprocess:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test claude_commands -- subprocess_

test-launch-claude-review:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test claude_commands -- review_




test-dispatch-with-waterfall:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test waterfall_commands

test-agent-model-args:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/agents/test_agents.py -q -k model_args

test-effort-prose:
	$(HARNESS_MARK) --label $@ -- bash scripts/test-effort-prose.sh



# Retired stub — kept for installed-plugin compat until checks.py ships without the
# lib-design-tmpdir _DIRECT_TARGET_RULES entry. NOT a test-harnesses prerequisite;
# see CARVE_OUTS in scripts/test-harness-shards-coverage.sh.
test-lib-design-tmpdir:
	@:

# Rust integration aliases remain standalone; see CARVE_OUTS in
# scripts/test-harness-shards-coverage.sh.
test-wait-for-reviewers:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test agent_commands wait_reviewers_preserves_validation_and_completion_rows

test-classify-diff-mode:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test agent_commands classify_diff_covers_modes_mixed_changes_and_bad_manifests

test-gather-branch-context:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test agent_commands gather_branch_context

test-run-external-agent:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test agent_commands run_external_agent
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/agents/test_agents.py -q -k 'not (check_reviewers or health_gate or launch_claude_ci or launch_claude_review or launch_claude_subprocess or launch_codex_ci or launch_cursor_ci or parse_codex_usage or model_args or degraded_tools)'

agent-sync:
	cargo run --quiet --locked --package larch-cli -- generate check
	cargo run --quiet --locked --package larch-cli -- lint rule topology-rule-paths
	cargo run --quiet --locked --package larch-cli -- lint rule focus-area-enum

# Opt-in /research evaluation harness (closes #419 under umbrella #413). NOT a
# lint prerequisite — runs ~20 questions × ~30-60s each, costs real tokens.
# Operator instrumentation for prompt-side iteration on /research. See
# docs/linting.md "/research evaluation harness". Pass flags via ARGS=,
# e.g.: `make eval-research ARGS="--id eval-1 --timeout 4200"`. The Rust owner
# (#8500) runs through the verified bootstrap script.
eval-research:
	scripts/larch.sh eval research $(ARGS)

shellcheck:
	pre-commit run shellcheck --all-files

markdownlint:
	pre-commit run markdownlint --all-files

jsonlint:
	pre-commit run jsonlint --all-files

actionlint:
	pre-commit run actionlint --all-files

agent-lint:
	pre-commit run --hook-stage manual agent-lint --all-files

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

.PHONY: test-design-stage-terminal-state test-design-failure-report test-design-step-final-summary test-design-step3-review test-design-step3b-tail test-design-step3b-entry test-design-step3-entry test-design-small-session-entries test-design-step0-init test-design-step5c test-design-step6 test-design-step-validator-autofix

test-design-stage-terminal-state:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/design/test_design_lifecycle.py -k 'stage_terminal_state or capture_contract or clarify_hard_halt'

test-design-failure-report:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/design/test_design_lifecycle.py -k failure_report

test-design-step-final-summary:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/design/test_design_lifecycle.py -k step_final_summary

test-design-step3-review:
	$(HARNESS_MARK) --label $@-rust -- cargo test --locked --package larch-cli --test plan_review_loop_commands normalize
	$(HARNESS_MARK) --label $@ -- bash skills/design/scripts/test-design-step3-review.sh

test-design-step3b-tail:
	$(HARNESS_MARK) --label $@ -- bash skills/design/scripts/test-design-step3b-tail.sh

test-design-step3b-entry:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/design/test_design_step3b.py

test-design-step3-entry:
	$(HARNESS_MARK) --label $@-rust -- cargo test --locked --package larch-cli --test plan_review_loop_commands normalize_and_session_entry
	$(HARNESS_MARK) --label $@ -- bash skills/design/scripts/test-design-step3-entry.sh

test-design-small-session-entries:
	$(HARNESS_MARK) --label $@ -- cargo test --locked --package larch-cli --test plan_review_loop_commands normalize_and_session_entry

test-design-step0-init:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/design/test_design_lifecycle.py -k 'step0_parse or step0_session or step0_route or step0_init or step0_abort or step0_ap or step0c or step1d7 or step1e or pause_save or bash_quoted or decode_bash_percent_q or degraded_tools or relay_degraded or require_design or resolve_repo or wrapper or core_style_ctx'

test-design-step5c:
	$(HARNESS_MARK) --label $@ -- bash skills/design/scripts/test-design-step5c.sh
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/design/test_design_lifecycle.py -k step5c

test-design-step6:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/design/test_design_lifecycle.py -k step6

test-design-step-validator-autofix:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest -q python/tests/design/test_plan_quality.py -k validator_autofix

test-design-step1d5:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/design/test_design_lifecycle.py -k 'step1d5'

test-design-log-ship:
	$(HARNESS_MARK) --label $@ -- python3 -m pytest python/tests/design/test_design_log_ship.py
