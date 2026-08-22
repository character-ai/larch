"""Argparse-based subcommand dispatcher for larch Python runtime.

Canonical location; python/cli.py is the entry-point shim.
Direct-call convention: consumers invoke
    python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" <domain> <verb> [args...]
No .sh shim files, ever. See docs/python-migration.md for the migration playbook.
"""

from __future__ import annotations

import argparse
import importlib
import os
import sys

_REGISTRY: dict[tuple[str, str], tuple[str, str, bool]] = {
    ("architectural-guidelines", "read"): ("larch.core.architectural_guidelines", "read_main", True),
    ("architectural-invariants", "read"): ("larch.core.architectural_guidelines", "invariants_read_main", True),
    ("architectural-guidelines", "present-note"): ("larch.core.architectural_guidelines", "present_note_main", True),
    ("architectural-invariants", "present-note"): (
        "larch.core.architectural_guidelines",
        "invariants_present_note_main",
        True,
    ),
    ("architectural-guidelines", "materialize-diff"): (
        "larch.core.architectural_guidelines",
        "materialize_diff_main",
        True,
    ),
    ("architectural-invariants", "materialize-diff"): (
        "larch.core.architectural_guidelines",
        "invariants_materialize_diff_main",
        True,
    ),
    ("architectural-guidelines", "prepare"): ("larch.core.architectural_guidelines", "prepare_main", True),
    ("architectural-invariants", "prepare"): ("larch.core.architectural_guidelines", "invariants_prepare_main", True),
    ("architectural-guidelines", "prepare-compose"): (
        "larch.core.architectural_guidelines",
        "prepare_compose_main",
        True,
    ),
    ("architectural-invariants", "prepare-compose"): (
        "larch.core.architectural_guidelines",
        "invariants_prepare_compose_main",
        True,
    ),
    ("architectural-guidelines", "write-compose-assessment"): (
        "larch.core.architectural_guidelines",
        "write_compose_assessment_main",
        True,
    ),
    ("architectural-invariants", "write-compose-assessment"): (
        "larch.core.architectural_guidelines",
        "invariants_write_compose_assessment_main",
        True,
    ),
    ("architectural-guidelines", "append-deviation-note"): (
        "larch.core.architectural_guidelines",
        "append_deviation_note_main",
        True,
    ),
    ("architectural-invariants", "append-deviation-note"): (
        "larch.core.architectural_guidelines",
        "invariants_append_deviation_note_main",
        True,
    ),
    ("architectural-guidelines", "write-staged-assessment"): (
        "larch.core.architectural_guidelines",
        "write_staged_assessment_main",
        True,
    ),
    ("architectural-invariants", "write-staged-assessment"): (
        "larch.core.architectural_guidelines",
        "invariants_write_staged_assessment_main",
        True,
    ),
    ("architectural-guidelines", "pin-note-from-staged"): (
        "larch.core.architectural_guidelines",
        "pin_note_from_staged_main",
        True,
    ),
    ("architectural-invariants", "pin-note-from-staged"): (
        "larch.core.architectural_guidelines",
        "invariants_pin_note_from_staged_main",
        True,
    ),
    ("architectural-guidelines", "invalidate"): ("larch.core.architectural_guidelines", "invalidate_main", True),
    ("architectural-invariants", "invalidate"): (
        "larch.core.architectural_guidelines",
        "invariants_invalidate_main",
        True,
    ),
    ("architectural-guidelines", "persist-design-assessment"): (
        "larch.core.architectural_guidelines",
        "persist_design_assessment_main",
        True,
    ),
    ("architectural-invariants", "persist-design-assessment"): (
        "larch.core.architectural_guidelines",
        "invariants_persist_design_assessment_main",
        True,
    ),
    ("plan-review", "write-loop-identity"): ("larch.core.process_identity", "write_loop_identity_main", False),
    ("plan-review", "await-loop-identity"): ("larch.core.process_identity", "await_loop_identity_main", False),
    ("plan-review", "teardown-loop-identity"): ("larch.core.process_identity", "teardown_loop_identity_main", False),
    ("issue", "governance-gate"): (
        "larch.issue.migration_governance",
        "governance_gate_main",
        True,
    ),
    ("plan-receipt", "refresh"): (
        "larch.issue.migration_governance",
        "plan_receipt_refresh_main",
        True,
    ),
    ("forked-repo", "setup"): ("larch.core.forked_repo", "setup_main", False),
    ("render", "specialist"): ("larch.rendering.rendering", "render_specialist_main", False),
    ("render", "voter"): ("larch.rendering.rendering", "render_voter_main", False),
    ("render", "plan-review"): ("larch.rendering.rendering", "render_plan_review_main", False),
    ("render", "scope-anchor"): ("larch.rendering.rendering", "render_scope_anchor_main", False),
    ("scope-anchor", "relay-allowed"): ("larch.rendering.rendering", "scope_anchor_relay_allowed_main", False),
    ("scope-anchor", "validate"): ("larch.rendering.rendering", "scope_anchor_validate_main", False),
    ("scope-anchor", "retally-handoff"): ("larch.rendering.rendering", "scope_anchor_retally_handoff_main", False),
    ("scope-anchor", "design-handoff"): ("larch.rendering.rendering", "scope_anchor_design_handoff_main", False),
    ("review-and-fix", "write-loop-identity"): ("larch.core.process_identity", "write_step5_loop_identity_main", False),
    ("review-and-fix", "await-loop-identity"): ("larch.core.process_identity", "await_step5_loop_identity_main", False),
    ("review-and-fix", "teardown-loop-identity"): (
        "larch.core.process_identity",
        "teardown_step5_loop_identity_main",
        False,
    ),
    ("mermaid", "sanitize"): ("larch.rendering.rendering", "mermaid_sanitize_main", False),
    ("diagrams", "upsert"): ("larch.rendering.rendering", "diagrams_upsert_main", False),
    ("token", "check-budget"): ("larch.report.tokens", "token_check_budget_main", False),
    ("token", "compute-pr-line-counts"): ("larch.report.tokens", "compute_pr_line_counts_main", False),
    ("token", "compute-pr-lines"): ("larch.report.tokens", "compute_pr_lines_main", False),
    ("redact", "secrets"): ("larch.core.redact", "main_secrets", False),
    ("redact", "tmpdir-paths"): ("larch.core.redact", "main_tmpdir_paths", False),
    ("redact", "scrub-log-secrets"): ("larch.core.redact", "main_scrub_log_secrets", False),
    ("redact", "scrub-submodule-paths"): ("larch.core.redact", "main_scrub_submodule_paths", False),
    ("implement", "cleanup"): ("larch.state.finalize", "cleanup_main", True),
    ("implement-finalize", "postbump"): ("larch.state.finalize", "implement_finalize_postbump_main", True),
    ("implement-finalize", "postmerge"): ("larch.state.finalize", "implement_finalize_postmerge_main", True),
    ("implement-finalize", "teardown"): ("larch.state.finalize", "implement_finalize_teardown_main", True),
    ("tracking", "post-issue"): ("larch.git.pr_body", "post_tracking_issue_main", True),
    ("diagram", "code-flow"): ("larch.git.pr_body", "generate_code_flow_diagram_main", True),
    ("render", "run-summary"): ("larch.git.pr_body", "render_run_summary_main", True),
    ("pr", "compose-summary"): ("larch.git.pr_body", "compose_pr_summary_main", True),
    ("oos", "serialize"): ("larch.issue.oos", "oos_serialize_main", False),
    ("oos", "normalize-header"): ("larch.issue.oos", "oos_normalize_header_main", False),
    ("pr", "create-branch"): ("larch.git.pr", "create_branch_main", False),
    ("pr", "create"): ("larch.git.pr", "create_main", False),
    ("pr", "body-update"): ("larch.git.pr", "body_update_main", False),
    ("pr", "checks"): ("larch.git.pr", "checks_main", False),
    ("pr", "closes-issue"): ("larch.git.pr", "closes_issue_main", False),
    ("merge", "pr"): ("larch.git.merge", "pr_main", False),
    ("merge", "wait"): ("larch.git.merge", "wait_main", False),
}

# Compatibility view: keys whose registry row has machine_stdout=True.
# Derived from _REGISTRY; do not hand-maintain.
_MACHINE_STDOUT_KEYS: frozenset[tuple[str, str]] = frozenset(
    key for key, (_module, _func, machine_stdout) in _REGISTRY.items() if machine_stdout
)

def _version_supported(version_info: object) -> bool:
    return tuple(version_info) >= (3, 11)  # type: ignore[arg-type]


def _unsupported_version_exit(args: list[str]) -> int:
    _ = args
    print(
        "ERROR: larch cli.py requires Python 3.11 or newer",
        file=sys.stderr,
    )
    return 2


def _build_help_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cli.py",
        description="larch Python runtime dispatcher",
        add_help=True,
        formatter_class=argparse.RawDescriptionHelpFormatter,
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


def _run_subcommand(module_name: str, func_name: str, rest_argv: list[str]) -> int:
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


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]

    if not _version_supported(sys.version_info):
        return _unsupported_version_exit(args)

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

    module_name, func_name, machine_stdout = _REGISTRY[key]
    rest_argv = args[2:]
    if machine_stdout:
        os.environ["LARCH_QUIET_DISABLE"] = "1"

    return _run_subcommand(module_name, func_name, rest_argv)
