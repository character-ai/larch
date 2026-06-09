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
    ("git", "commit"): ("git_cli", "commit_main"),
    ("git", "stage"): ("git_cli", "stage_main"),
    ("git", "amend-add"): ("git_cli", "amend_add_main"),
    ("git", "current-branch"): ("git_cli", "current_branch_main"),
    ("git", "branch-info"): ("git_cli", "branch_info_main"),
    ("git", "conflict-files"): ("git_cli", "conflict_files_main"),
    ("git", "rebase-abort"): ("git_cli", "rebase_abort_main"),
    ("git", "rebase-skip"): ("git_cli", "rebase_skip_main"),
    ("git", "checkout-ours"): ("git_cli", "checkout_ours_main"),
    ("git", "show-stage"): ("git_cli", "show_stage_main"),
    ("git", "sync-local-main"): ("git_cli", "sync_local_main_main"),
    ("git", "clean-tree"): ("git_cli", "clean_tree_main"),
    ("git", "snapshot-untracked"): ("git_cli", "snapshot_untracked_main"),
    ("git", "count-commits"): ("git_cli", "count_commits_main"),
    ("git", "check-main-sync"): ("git_cli", "check_main_sync_main"),
    ("git", "check-remote-branch"): ("git_cli", "check_remote_branch_main"),
    ("git", "check-phantom-dirty"): ("git_cli", "check_phantom_dirty_main"),
    ("git", "phantom-probe"): ("git_cli", "phantom_probe_main"),
    ("push", "branch"): ("push_cli", "branch_main"),
    ("push", "force"): ("push_cli", "force_main"),
    ("push", "rebase"): ("push_cli", "rebase_main"),
    ("push", "checkpoint-probe"): ("push_cli", "checkpoint_probe_main"),
    ("pr", "create-branch"): ("pr_cli", "create_branch_main"),
    ("pr", "create"): ("pr_cli", "create_main"),
    ("pr", "body-update"): ("pr_cli", "body_update_main"),
    ("pr", "checks"): ("pr_cli", "checks_main"),
    ("pr", "closes-issue"): ("pr_cli", "closes_issue_main"),
    ("merge", "pr"): ("merge_cli", "pr_main"),
    ("gh", "resolve-repo"): ("gh_cli", "resolve_repo_main"),
    ("gh", "remote-repo"): ("gh_cli", "remote_repo_main"),
    ("gh", "run-logs"): ("gh_cli", "run_logs_main"),
    ("gh", "workflow-path"): ("gh_cli", "workflow_path_main"),
    ("ci", "wait"): ("ci_cli", "wait_main"),
    ("ci", "status"): ("ci_cli", "status_main"),
    ("ci", "decide"): ("ci_cli", "decide_main"),
    ("ci", "failed-jobs"): ("ci_cli", "failed_jobs_main"),
    ("ci", "behind-count"): ("ci_cli", "behind_count_main"),
    ("ci", "rerun-failed"): ("ci_cli", "rerun_failed_main"),
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
