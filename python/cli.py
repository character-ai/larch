"""Argparse-based subcommand dispatcher for larch Python runtime.

Direct-call convention: consumers invoke
    python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" <domain> <verb> [args...]
No .sh shim files, ever. See docs/python-migration.md for the migration playbook.
"""

from __future__ import annotations

import argparse
import importlib
import sys

_REGISTRY: dict[tuple[str, str], tuple[str, str]] = {
    ("issue", "parse-input"): ("issue_create", "parse_input_main"),
    ("issue", "create-one"): ("issue_create", "create_one_main"),
    ("issue", "allocate-candidates"): ("issue_create", "allocate_candidates_main"),
    ("issue", "add-blocked-by"): ("issue_create", "add_blocked_by_main"),
    ("issue", "fetch-issue-details"): ("issue_create", "fetch_issue_details_main"),
    ("issue", "list-issues"): ("issue_create", "list_issues_main"),
    ("issue", "write-sentinel"): ("issue_create", "write_sentinel_main"),
    ("issue", "cleanup-failed"): ("issue_create", "cleanup_failed_main"),
    ("block-issue", "add-blocked-by"): ("issue_block", "add_blocked_by_main"),
    ("alias", "generate"): ("alias_skill", "generate_main"),
    ("alias", "resolve-target"): ("alias_skill", "resolve_target_main"),
    ("cleanup", "run"): ("cleanup_skill", "run_main"),
    ("upgrade-larch", "run"): ("upgrade_larch", "run_main"),
    ("upgrade-larch", "release-step7-root"): ("upgrade_larch", "release_step7_root_main"),
    ("forked-repo", "setup"): ("forked_repo", "setup_main"),
    ("render", "specialist"): ("rendering", "render_specialist_main"),
    ("render", "reviewer"): ("rendering", "render_reviewer_main"),
    ("render", "debate-retry"): ("rendering", "render_debate_retry_main"),
    ("render", "lane-status"): ("rendering", "render_lane_status_main"),
    ("render", "voter"): ("rendering", "render_voter_main"),
    ("render", "plan-review"): ("rendering", "render_plan_review_main"),
    ("mermaid", "sanitize"): ("rendering", "mermaid_sanitize_main"),
    ("diagrams", "upsert"): ("rendering", "diagrams_upsert_main"),
    ("generate", "code-reviewer-agent"): ("rendering", "generate_code_reviewer_agent_main"),
    ("generate", "reviewer-plan-fidelity-agent"): ("rendering", "generate_reviewer_plan_fidelity_agent_main"),
    ("generate", "reviewer-code-robustness-agent"): ("rendering", "generate_reviewer_code_robustness_agent_main"),
    ("generate", "reviewer-security-structure-tests-agent"): ("rendering", "generate_reviewer_security_structure_tests_agent_main"),
    ("generate", "pre-rendered-reviewer-prompts"): ("rendering", "generate_pre_rendered_reviewer_prompts_main"),
    ("generate", "codex-implementer"): ("rendering", "generate_codex_implementer_main"),
    ("generate", "cursor-implementer"): ("rendering", "generate_cursor_implementer_main"),
    ("generate", "topology-docs"): ("rendering", "generate_topology_docs_main"),
    ("generate", "check"): ("rendering", "generate_check_main"),
    ("ship", "design-log"): ("design_log_ship", "main"),
    ("ship", "pr"): ("ship", "main"),
    ("clarify", "state"): ("clarify", "clarify_state_main"),
    ("clarify", "comment-post"): ("clarify", "clarify_comment_post_main"),
    ("clarify", "label"): ("clarify", "clarify_label_main"),
    ("progress", "report"): ("progress_report", "report_main"),
    ("report-tokens", "analyze"): ("report_tokens_cli", "main"),
    ("token", "mark"): ("tokens", "token_mark_main"),
    ("token", "record-vendor"): ("tokens", "token_record_vendor_main"),
    ("token", "dump"): ("tokens", "token_dump_main"),
    ("token", "report"): ("tokens", "token_report_main"),
    ("token", "check-budget"): ("tokens", "token_check_budget_main"),
    ("token", "claude-source"): ("tokens", "token_claude_source_main"),
    ("token", "lane-write"): ("tokens", "token_lane_write_main"),
    ("token", "lane-report"): ("tokens", "token_lane_report_main"),
    ("token", "append-record"): ("tokens", "token_append_record_main"),
    ("token", "cost"): ("tokens", "token_cost_main"),
    ("token", "render-cost-line"): ("tokens", "token_render_cost_line_main"),
    ("token", "compute-pr-line-counts"): ("tokens", "compute_pr_line_counts_main"),
    ("token", "measure-md-cost"): ("tokens", "measure_md_cost_main"),
    ("token", "measure-ngram-duplication"): ("tokens", "measure_ngram_duplication_main"),
    ("token", "measure-references-heatmap"): ("tokens", "measure_references_heatmap_main"),
    ("token", "measure-realized-cost"): ("tokens", "measure_realized_cost_main"),
    ("timing", "mark"): ("timing", "timing_mark_main"),
    ("timing", "record-vendor-task"): ("timing", "timing_record_vendor_task_main"),
    ("timing", "record-round"): ("timing", "timing_record_round_main"),
    ("timing", "dump"): ("timing", "timing_dump_main"),
    ("timing", "report"): ("timing", "timing_report_main"),
    ("timing", "harness-mark"): ("timing", "timing_harness_mark_main"),
    ("timing", "telemetry-mark"): ("timing", "timing_telemetry_mark_main"),
    ("timing", "task-kinds"): ("timing", "timing_task_kinds_main"),
    ("lint", "retired-scripts"): ("migration_lint", "main"),
    ("lint", "mermaid-fences"): ("lint_mermaid_fences", "main"),
    ("lint", "skill-md-flag-signature"): ("lint_skill_md_flag_signature", "main"),
    ("lint", "readability-preamble"): ("lint_readability_preamble", "main"),
    ("lint", "gh-body-inline"): ("lint_gh_body_inline", "main"),
    ("lint", "codex-exec-auth"): ("lint_codex_exec_auth", "main"),
    ("lint", "skill-invocations"): ("lint_skill_invocations", "main"),
    ("voting", "vote-for-id"): ("voting", "vote_for_id_main"),
    ("voting", "reviewer-for-block"): ("voting", "reviewer_for_block_main"),
    ("voting", "is-security-block"): ("voting", "is_security_block_main"),
    ("voting", "accept-finding"): ("voting", "accept_finding_main"),
    ("voting", "classify-result"): ("voting", "classify_result_main"),
    ("voting", "panel-tier"): ("voting", "panel_tier_main"),
    ("voting", "split-ballot"): ("voting", "split_ballot_main"),
    ("voting", "parse-judge-vote"): ("voting", "parse_judge_vote_main"),
    ("voting", "parse-rate-check"): ("voting", "parse_rate_check_main"),
    ("voting", "parse-rate-retry"): ("voting", "parse_rate_retry_main"),
    ("voting", "parse-rate-diag-matches"): ("voting", "parse_rate_diag_matches_main"),
    ("voting", "effective-judges"): ("voting", "effective_judges_main"),
    ("voting", "degraded-warning"): ("voting", "degraded_warning_main"),
    ("voting", "voter-status-block"): ("voting", "voter_status_block_main"),
    ("voting", "write-tally"): ("voting", "write_tally_main"),
    ("voting", "compose-tally-record"): ("voting", "compose_tally_record_main"),
    ("voting", "false-positive-match"): ("voting", "false_positive_match_main"),
    ("voting", "file-line-regex"): ("voting", "file_line_regex_main"),
    ("voting", "ballot-parse"): ("voting", "ballot_parse_main"),
    ("voting", "tally-vote"): ("voting", "tally_vote_main"),
    ("voting", "scoreboard"): ("voting", "scoreboard_main"),
    ("lint", "focus-area-enum"): ("voting", "lint_focus_area_enum_main"),
    ("oos", "serialize"): ("oos", "oos_serialize_main"),
    ("oos", "normalize-header"): ("oos", "oos_normalize_header_main"),
    ("git", "commit"): ("git", "commit_main"),
    ("git", "stage"): ("git", "stage_main"),
    ("git", "amend-add"): ("git", "amend_add_main"),
    ("git", "current-branch"): ("git", "current_branch_main"),
    ("git", "branch-info"): ("git", "branch_info_main"),
    ("git", "conflict-files"): ("git", "conflict_files_main"),
    ("git", "rebase-abort"): ("git", "rebase_abort_main"),
    ("git", "rebase-skip"): ("git", "rebase_skip_main"),
    ("git", "checkout-ours"): ("git", "checkout_ours_main"),
    ("git", "show-stage"): ("git", "show_stage_main"),
    ("git", "sync-local-main"): ("git", "sync_local_main_main"),
    ("git", "clean-tree"): ("git", "clean_tree_main"),
    ("git", "snapshot-untracked"): ("git", "snapshot_untracked_main"),
    ("git", "count-commits"): ("git", "count_commits_main"),
    ("git", "check-main-sync"): ("git", "check_main_sync_main"),
    ("git", "check-remote-branch"): ("git", "check_remote_branch_main"),
    ("git", "check-phantom-dirty"): ("git", "check_phantom_dirty_main"),
    ("git", "phantom-probe"): ("git", "phantom_probe_main"),
    ("push", "branch"): ("push", "branch_main"),
    ("push", "force"): ("push", "force_main"),
    ("push", "rebase"): ("push", "rebase_main"),
    ("push", "checkpoint-probe"): ("push", "checkpoint_probe_main"),
    ("pr", "create-branch"): ("pr", "create_branch_main"),
    ("pr", "create"): ("pr", "create_main"),
    ("pr", "body-update"): ("pr", "body_update_main"),
    ("pr", "checks"): ("pr", "checks_main"),
    ("pr", "closes-issue"): ("pr", "closes_issue_main"),
    ("merge", "pr"): ("merge", "pr_main"),
    ("gh", "resolve-repo"): ("gh", "resolve_repo_main"),
    ("gh", "remote-repo"): ("gh", "remote_repo_main"),
    ("gh", "run-logs"): ("gh", "run_logs_main"),
    ("gh", "workflow-path"): ("gh", "workflow_path_main"),
    ("ci", "wait"): ("ci", "wait_main"),
    ("ci", "status"): ("ci", "status_main"),
    ("ci", "decide"): ("ci", "decide_main"),
    ("ci", "failed-jobs"): ("ci", "failed_jobs_main"),
    ("ci", "behind-count"): ("ci", "behind_count_main"),
    ("ci", "rerun-failed"): ("ci", "rerun_failed_main"),
    ("session", "setup"): ("session_env", "setup_main"),
    ("session", "write-env"): ("session_env", "write_env_main"),
    ("session", "read-key"): ("session_env", "read_key_main"),
    ("session", "write-design-env"): ("session_env", "write_design_env_main"),
    ("session", "write-implement-env"): ("session_env", "write_implement_env_main"),
    ("session", "clear-implement-pointer"): ("session_env", "clear_implement_pointer_main"),
    ("session", "write-run-params"): ("session_env", "write_run_params_main"),
    ("session", "read-classification"): ("session_env", "read_classification_main"),
    ("session", "write-id"): ("session_env", "write_id_main"),
    ("session", "persist-run-flags"): ("session_env", "persist_run_flags_main"),
    ("session", "restore-finalize-state"): ("session_env", "restore_finalize_state_main"),
    ("session", "cleanup-tmpdir"): ("session_env", "cleanup_tmpdir_main"),
    ("session", "local-cleanup"): ("session_env", "local_cleanup_main"),
    ("session", "entry-gate"): ("session_env", "entry_gate_main"),
}


def _version_supported(version_info: object) -> bool:
    return tuple(version_info) >= (3, 11)  # type: ignore[arg-type]


def _build_help_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cli.py",
        description="larch Python runtime dispatcher",
        add_help=True,
    )
    domains: dict[str, list[str]] = {}
    for domain, verb in _REGISTRY:
        domains.setdefault(domain, []).append(verb)
    lines = ["Available subcommands:"]
    lines.extend(
        f"  {domain} {verb}" for domain in sorted(domains) for verb in sorted(domains[domain])
    )
    parser.epilog = "\n".join(lines)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]

    if not _version_supported(sys.version_info):
        print(
            "ERROR: larch cli.py requires Python 3.11 or newer",
            file=sys.stderr,
        )
        return 2

    if not args or args[0] in {"-h", "--help"}:
        _build_help_parser().print_help()
        return 0

    domain = args[0]
    if len(args) < 2 or args[1].startswith("-"):  # noqa: PLR2004
        print(
            f"ERROR: missing verb for domain {domain!r}. "
            f"Usage: cli.py <domain> <verb> [args...]",
            file=sys.stderr,
        )
        return 2

    verb = args[1]
    key = (domain, verb)
    if key not in _REGISTRY:
        known = ", ".join(f"{d} {v}" for d, v in sorted(_REGISTRY))
        print(
            f"ERROR: unknown subcommand {domain!r} {verb!r}. "
            f"Known: {known}",
            file=sys.stderr,
        )
        return 2

    module_name, func_name = _REGISTRY[key]
    rest_argv = args[2:]

    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        print(f"ERROR: failed to import module {module_name!r}: {exc}", file=sys.stderr)
        return 2

    target_main = getattr(module, func_name, None)
    if target_main is None:
        print(
            f"ERROR: module {module_name!r} has no function {func_name!r}",
            file=sys.stderr,
        )
        return 2

    return int(target_main(rest_argv))


if __name__ == "__main__":
    raise SystemExit(main())
