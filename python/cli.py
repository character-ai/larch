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
    ("ship", "pr"): ("ship", "main"),
    ("report-tokens", "analyze"): ("report_tokens_cli", "main"),
    ("lint", "retired-scripts"): ("migration_lint", "main"),
    ("lint", "mermaid-fences"): ("lint_mermaid_fences", "main"),
    ("lint", "skill-md-flag-signature"): ("lint_skill_md_flag_signature", "main"),
    ("lint", "readability-preamble"): ("lint_readability_preamble", "main"),
    ("lint", "gh-body-inline"): ("lint_gh_body_inline", "main"),
    ("lint", "codex-exec-auth"): ("lint_codex_exec_auth", "main"),
    ("lint", "skill-invocations"): ("lint_skill_invocations", "main"),
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
