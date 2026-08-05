# Git operation inventory

This matrix records every production source that reads local Git state or can
execute installed Git. The `gix-read` owner means the typed `RepositoryRead`
port implemented only by `crates/larch-adapters/src/git/repository.rs`.
The `git-cli` owner means a closed method on `GitCli`; it never means arbitrary
Git arguments. `later-domain` rows remain Python-owned until the named Rust
migration issue atomically switches their command consumers and removes the
Python implementation.

The rule `git-ownership` compares this block with live production Rust, Python,
skill, agent, hook, script, Makefile, and workflow surfaces. It also rejects
direct installed-Git construction through aliases, qualified constructors, or
constant and variable executable values. It pins the adapter's public methods
to the closed typed request families and rejects generic argv forwarding.
Keep the block tab-separated and sort each row's operation names.

<!-- markdownlint-disable MD010 -->
<!-- git-ownership-matrix:start -->
```text
surface	owner	issue	operations
.claude/skills/agnix-fix/SKILL.md	later-domain	#7685	remote
.claude/skills/audit-runs/SKILL.md	later-domain	#7684	log,show
.claude/skills/larch-size/scripts/larch_size.py	later-domain	#7685	ls-files,rev-parse
.claude/skills/rebalance-tests/scripts/rebalance.py	later-domain	#7685	checkout
.claude/skills/release/SKILL.md	later-domain	#7674	add,checkout,commit,fetch,merge,merge-base,rev-parse
.github/workflows/ci.yaml	later-domain	#7685	diff,merge-base,rev-parse
.github/workflows/rust-release-assets.yaml	later-domain	#7685	rev-parse
.pre-commit-config.yaml	later-domain	#7686	rev-parse
agents/_implementer-base.md	later-domain	#7678	commit
agents/claude-self-reviewer.md	later-domain	#7678	merge-base
skills/implement/prompts/codex-implementer.md	later-domain	#7681	commit
skills/implement/prompts/cursor-implementer.md	later-domain	#7681	commit
crates/larch-adapters/src/git/mod.rs	git-cli	#7671	closed-cli-owner
crates/larch-adapters/src/git/repository.rs	gix-read	#7671	concrete-gix-owner
crates/larch-cli/src/admission_commands.rs	git-cli	#7671	typed-cli,typed-read
crates/larch-cli/src/dirty_tree_commands.rs	gix-read	#7671	typed-read
crates/larch-cli/src/git_commands.rs	git-cli	#7671	typed-cli,typed-read
crates/larch-cli/src/github_repository_resolution.rs	gix-read	#7671	typed-read
crates/larch-cli/src/main.rs	git-cli	#7671	typed-cli,typed-read
crates/larch-cli/src/push_network.rs	git-cli	#7671	typed-cli,typed-read
crates/larch-cli/src/push_rebase.rs	git-cli	#7671	typed-cli,typed-read
crates/larch-cli/src/release_common.rs	git-cli	#7671	typed-cli,typed-read
crates/larch-cli/src/release_plugin_runtime.rs	gix-read	#7671	typed-read
crates/larch-cli/src/release_prepare.rs	gix-read	#7671	typed-read
crates/larch-cli/src/release_publish.rs	gix-read	#7671	typed-read
crates/larch-cli/src/release_stage.rs	gix-read	#7671	typed-read
crates/larch-cli/src/run_log_commands.rs	gix-read	#7671	typed-read
crates/larch-lint/src/repository.rs	bootstrap	#7736	repository-discovery,tracked-paths
python/larch/agents/_drafter.py	later-domain	#7678	dynamic
python/larch/agents/_run_external.py	later-domain	#7678	dynamic
crates/larch-cli/src/agent_commands.rs	git-cli	#7671	typed-cli,typed-read
python/larch/core/architectural_guidelines.py	later-domain	#7686	diff,merge-base,rev-parse
python/larch/core/coder_delta_guards.py	later-domain	#7686	config,diff,ls-files,submodule
python/larch/core/forked_repo.py	later-domain	#7682	config,ls-remote,merge-base,remote,rev-parse,show-ref,status,submodule,worktree
python/larch/core/redact.py	later-domain	#7686	submodule
python/larch/core/residual_bash.py	later-domain	#7686	dynamic
python/larch/core/verify_main.py	later-domain	#7686	log
python/larch/design/design_log_publish_flow.py	later-domain	#7680	dynamic
python/larch/design/design_step2b.py	later-domain	#7680	dynamic
python/larch/design/plan_quality.py	later-domain	#7680	apply
python/larch/git/gh.py	later-domain	#7676	remote
python/larch/git/git.py	later-domain	#7681	add,branch,checkout,commit,diff,diff-tree,fetch,log,ls-files,ls-remote,merge-base,push,rebase,reset,restore,rev-list,rev-parse,rm,show,show-ref,status,symbolic-ref
python/larch/git/merge.py	later-domain	#7681	fetch,log,show
python/larch/git/pr.py	later-domain	#7681	branch,checkout,config,push
python/larch/git/pr_body.py	later-domain	#7681	diff,merge-base,rev-parse
python/larch/git/rebase.py	later-domain	#7681	checkout
python/larch/implement/checks_lint_fix.py	later-domain	#7681	checkout,diff,merge-base,reset,rev-parse
python/larch/implement/checks_result_identity.py	later-domain	#7681	dynamic
python/larch/implement/rust_clippy.py	later-domain	#7681	diff,ls-files,rev-parse
python/larch/implement/ci_monitor.py	later-domain	#7681	ls-remote,rev-list,symbolic-ref
python/larch/implement/dispatch_helpers.py	later-domain	#7681	dynamic
python/larch/implement/dispatch_recovery.py	later-domain	#7681	rev-parse
python/larch/implement/dispatch_step2.py	later-domain	#7681	rev-parse
python/larch/implement/scope_disposition.py	later-domain	#7681	dynamic
python/larch/implement/step_7a.py	later-domain	#7681	diff,merge-base
python/larch/issue/analyze_bugs.py	later-domain	#7682	cat-file,diff,diff-tree,fetch,grep,log,merge-base,rev-parse,show
python/larch/issue/audit_runs.py	later-domain	#7682	branch,config,fetch,pull,rev-parse,status
python/larch/issue/file_oos.py	later-domain	#7682	log,merge-base,rev-list,rev-parse
python/larch/issue/learn_from_bugs.py	later-domain	#7682	dynamic
python/larch/issue/migration_governance.py	later-domain	#7682	ls-tree
python/larch/issue/rejected_analysis.py	later-domain	#7682	dynamic
python/larch/issue/triage.py	later-domain	#7682	--version
python/larch/lint/timing_task_kind_allowlist.py	later-domain	#7685	dynamic
python/larch/rendering/_rendering_generators.py	later-domain	#7683	commit,diff,ls-files
python/larch/rendering/rendering.py	later-domain	#7683	merge-base
python/larch/report/final_report.py	later-domain	#7683	rev-parse
python/larch/report/run_log_commit.py	later-domain	#7683	add,clean,commit,diff,reset,restore,rev-parse,status,symbolic-ref
python/larch/report/run_log_flush.py	later-domain	#7683	diff
python/larch/report/storage_config.py	later-domain	#7683	dynamic
python/larch/report/tokens.py	later-domain	#7683	dynamic
python/larch/research/research_eval.py	later-domain	#7684	dynamic
python/larch/review/_raf_util.py	later-domain	#7679	status
python/larch/review/coder_runner.py	later-domain	#7679	checkout
python/larch/review/review_and_fix.py	later-domain	#7679	diff,ls-files,rev-parse,status
python/larch/review/review_gather.py	later-domain	#7679	ls-files
python/larch/review/snapshot.py	later-domain	#7679	apply,cat-file,checkout,diff,ls-files,restore
python/larch/state/bootstrap.py	later-domain	#7677	status
python/larch/state/finalize.py	later-domain	#7677	branch,check-ref-format,checkout,ls-remote,pull,rev-list,rev-parse,show-ref,stash,symbolic-ref
python/larch/state/session_env.py	later-domain	#7677	branch,checkout,fetch,pull,rev-list,show-ref,symbolic-ref
scripts/block-submodule-edit.sh	later-domain	#7677	rev-parse
scripts/check-stale-plugin.sh	later-domain	#7674	rev-parse
scripts/sessionstart-health.sh	later-domain	#7677	branch,rev-parse,sparse-checkout,stash,status
skills/implement/references/checks-repair-loop.md	later-domain	#7681	rev-parse
skills/implement/references/codex-manifest-schema.md	later-domain	#7681	commit
skills/implement/references/step2-dispatch.md	later-domain	#7681	commit
skills/implement/scripts/generate-code-flow-diagram.sh	later-domain	#7681	diff,merge-base,rev-parse
skills/implement/scripts/oos-disposition-gate.md	later-domain	#7681	merge-base
skills/implement/scripts/step-architectural-guidelines-write-staged.sh	later-domain	#7681	rev-parse
skills/voter-calibration/scripts/voter-calibration.py	later-domain	#7684	dynamic
```
<!-- git-ownership-matrix:end -->
<!-- markdownlint-enable MD010 -->

Tests and repository-only bootstrap code are not production exceptions.
`#[cfg(test)]` fixture setup and `larch-test-support` may execute Git as an
independent oracle. The lint bootstrap row above is confined to repository
discovery and tracked-path enumeration because `larch-lint` cannot depend on
product crates while it validates them. Production suppression cannot widen
either exception. The rule also re-runs the command registry's syntax-aware
Python retirement proof for every #7675 command and rejects the retired
`push rebase` state-machine symbols.
