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
    ("checks", "run-relevant"): ("larch.implement.checks", "checks_run_relevant_main", True),
    ("checks", "fixer-evidence"): ("larch.implement.checks", "checks_fixer_evidence_main", True),
    ("checks", "lint-fix"): ("larch.implement.checks", "checks_lint_fix_main", True),
    ("checks", "repair-loop"): ("larch.implement.checks", "checks_repair_loop_main", True),
    ("checks", "contains-pins"): ("larch.implement.checks", "check_contains_pins_main", True),
    ("checks", "rust-clippy"): ("larch.implement.checks", "rust_clippy_main", False),
    ("ci", "distill-log"): ("larch.implement.ci", "distill_log_main", False),
    ("ci", "prepare-rust-integration-artifact"): (
        "larch.implement.rust_policy_candidate",
        "prepare_integration_artifact_main",
        False,
    ),
    ("ci", "stage-rust-policy-candidate"): (
        "larch.implement.rust_policy_candidate",
        "stage_policy_candidate_main",
        False,
    ),
    ("ci", "promote-rust-policy-candidate"): (
        "larch.implement.rust_policy_candidate",
        "promote_policy_candidate_main",
        False,
    ),
    ("ci", "stage-main-cache-candidate"): (
        "larch.implement.main_cache_candidate",
        "stage_main_cache_candidate_main",
        True,
    ),
    ("ci", "verify-main-cache-candidate"): (
        "larch.implement.main_cache_candidate",
        "verify_main_cache_candidate_main",
        True,
    ),
    ("complete-umbrella", "ship-leaf"): (
        "larch.implement.complete_umbrella_ship",
        "main",
        True,
    ),
    ("implement", "step2-dispatch"): ("larch.implement.implement_dispatch", "step2_dispatch_main", False),
    ("implement", "run-dispatch"): ("larch.implement.implement_dispatch", "run_dispatch_main", False),
    ("implement", "commit"): ("larch.implement.implement_dispatch", "commit_main", False),
    ("implement", "commit-route"): ("larch.implement.implement_dispatch", "commit_route_main", True),
    ("implement", "scope-disposition"): ("larch.implement.scope_disposition", "scope_disposition_main", True),
    ("implement", "checks-commit-route"): ("larch.implement.implement_dispatch", "checks_commit_route_main", True),
    ("implement", "kill-active-leg"): ("larch.implement.implement_dispatch", "kill_active_leg_main", False),
    ("implement", "step-2-post-dispatch"): ("larch.implement.implement_dispatch", "step2_post_dispatch_main", False),
    ("implement", "step-8-python-guard"): ("larch.implement.implement_dispatch", "step8_python_guard_main", False),
    ("implement", "step-8-seed-initial"): ("larch.implement.implement_dispatch", "step8_seed_initial_main", False),
    ("implement", "step-8-ship"): ("larch.implement.implement_dispatch", "step8_ship_main", False),
    ("implement", "step-8-oos-checkpoint"): ("larch.implement.implement_dispatch", "step8_oos_checkpoint_main", True),
    ("architectural-guidelines", "read"): ("larch.core.architectural_guidelines", "read_main", True),
    ("architectural-assessment", "materialize"): ("larch.implement.architectural_assessment", "materialize_main", True),
    ("architectural-assessment", "submit"): ("larch.implement.architectural_assessment", "submit_main", True),
    ("architectural-assessment", "final-report-sections"): (
        "larch.implement.architectural_assessment",
        "final_report_sections_main",
        True,
    ),
    ("architectural-assessment", "sanitize-detail"): (
        "larch.implement.architectural_assessment",
        "sanitize_detail_main",
        True,
    ),
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
    ("design", "step3b-entry"): ("larch.design.design_step3b", "step3b_entry_main", True),
    ("plan-review", "step35-settle"): ("larch.design.design_settle", "step35_settle_main", True),
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
    ("design", "read-result-env"): ("larch.design.design_terminal", "read_result_env_main", True),
    ("design", "stage-terminal-state"): ("larch.design.design_terminal", "stage_terminal_state_main", True),
    ("design", "failure-report"): ("larch.design.design_terminal", "failure_report_main", True),
    ("design", "step-final-summary"): ("larch.design.design_terminal", "step_final_summary_main", True),
    ("design", "step2b-drafter"): ("larch.design.design_step2b", "step2b_drafter_main", True),
    ("design", "step2b-postplan"): ("larch.design.design_step2b", "step2b_postplan_main", True),
    ("design", "step35-settle"): ("larch.design.design_settle", "step35_settle_main", True),
    ("design", "prelude"): ("larch.design.design_core", "prelude_main", True),
    ("design", "step3-continuation-entry"): ("larch.design.design_core", "step3_continuation_entry_main", True),
    ("design", "dialectic-gatec"): ("larch.design.design_dialectic", "gatec_main", False),
    ("design", "dialectic-manual"): ("larch.design.design_dialectic", "manual_main", False),
    ("design", "dialectic-write-candidates"): ("larch.design.design_dialectic", "write_candidates_main", False),
    ("design", "dialectic-promote-candidates"): ("larch.design.design_dialectic", "promote_candidates_main", False),
    ("design", "dialectic-validate-candidates"): ("larch.design.design_dialectic", "validate_candidates_main", False),
    ("design", "dialectic-clear-stale"): ("larch.design.design_dialectic", "clear_stale_main", False),
    ("design", "step2b5"): ("larch.design.design_step5c", "step2b5_main", True),
    ("design", "step5b-prepare"): ("larch.design.design_step5b", "step5b_prepare_main", True),
    ("design", "step5b-annotate"): ("larch.design.design_step5b", "step5b_annotate_main", True),
    ("design", "step5c"): ("larch.design.design_step5c", "step5c_main", True),
    ("design", "step6"): ("larch.design.design_step6", "step6_main", True),
    ("design", "step6-prelude"): ("larch.design.design_step6", "step6_prelude_main", True),
    ("design", "step6-cleanup"): ("larch.design.design_step6", "step6_cleanup_main", True),
    ("design", "postplan-emit"): ("larch.design.design_postplan", "postplan_emit_main", True),
    ("design", "publish"): ("larch.design.design_publish", "publish_main", True),
    ("design", "clarify"): ("larch.design.clarify", "design_clarify_main", True),
    ("design", "log-publish"): ("larch.design.design_log_publish_flow", "log_publish_main", True),
    ("design", "pause-save"): ("larch.design.design_pause", "pause_save_main", True),
    ("design", "pause-load"): ("larch.design.design_pause", "pause_load_main", True),
    ("design", "render-gate"): ("larch.design.design_gate_render", "render_gate_main", True),
    ("design", "render-final-summary"): ("larch.design.design_summary", "render_final_summary_main", True),
    ("design", "file-oos-prepare"): ("larch.design.design_oos", "file_oos_prepare_main", True),
    ("design", "file-oos-annotate"): ("larch.design.design_oos", "file_oos_annotate_main", True),
    ("decompose", "prepare"): ("larch.design.decompose", "prepare_main", False),
    ("decompose", "annotate"): ("larch.design.decompose", "annotate_main", False),
    ("decompose", "migrate-deps"): ("larch.design.decompose", "migrate_deps_main", False),
    ("decompose", "close-original"): ("larch.design.decompose", "close_original_main", False),
    ("decompose", "panel-dispatch"): ("larch.design.decompose", "panel_dispatch_main", False),
    ("decompose", "aggregate"): ("larch.design.decompose", "aggregate_main", False),
    ("scout", "dynamic-archetypes"): ("larch.design.plan_scout", "dynamic_archetypes_main", False),
    ("scout", "plan-archetypes"): ("larch.design.plan_scout", "plan_archetypes_main", False),
    ("scout", "filter-manifest"): ("larch.design.plan_scout", "filter_manifest_main", False),
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
    ("ship", "pr"): ("larch.implement.ship", "main", False),
    ("ship", "pre-driver"): ("larch.implement.implement_dispatch", "ship_pre_driver_main", True),
    ("ship", "pre-fix-rebase"): ("larch.implement.implement_dispatch", "ship_pre_fix_rebase_main", True),
    ("ship", "normalize-assessment-handoff"): (
        "larch.implement.implement_dispatch",
        "ship_normalize_assessment_handoff_main",
        True,
    ),
    ("ship", "route-exit"): ("larch.implement.implement_dispatch", "ship_route_exit_main", True),
    ("ship", "reconcile-manual-merge"): ("larch.implement.ship_recovery", "reconcile_manual_merge_main", True),
    ("ship", "seed-initial-state"): ("larch.implement.ship", "seed_initial_state_main", False),
    ("clarify", "state"): ("larch.design.clarify", "clarify_state_main", False),
    ("clarify", "comment-fetch"): ("larch.design.clarify", "clarify_comment_fetch_main", False),
    ("clarify", "comment-post"): ("larch.design.clarify", "clarify_comment_post_main", False),
    ("clarify", "label"): ("larch.design.clarify", "clarify_label_main", False),
    ("token", "check-budget"): ("larch.report.tokens", "token_check_budget_main", False),
    ("token", "compute-pr-line-counts"): ("larch.report.tokens", "compute_pr_line_counts_main", False),
    ("token", "compute-pr-lines"): ("larch.report.tokens", "compute_pr_lines_main", False),
    ("redact", "secrets"): ("larch.core.redact", "main_secrets", False),
    ("redact", "tmpdir-paths"): ("larch.core.redact", "main_tmpdir_paths", False),
    ("redact", "scrub-log-secrets"): ("larch.core.redact", "main_scrub_log_secrets", False),
    ("redact", "scrub-submodule-paths"): ("larch.core.redact", "main_scrub_submodule_paths", False),
    ("implement", "step-16"): ("larch.state.closeout", "step_16_main", True),
    ("implement", "step-17"): ("larch.state.closeout", "step_17_main", True),
    ("implement", "step-16-16a"): ("larch.state.closeout", "step_16_16a_main", True),
    ("implement", "step-16-17"): ("larch.state.closeout", "step_16_17_main", True),
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
    ("ci", "wait"): ("larch.implement.ci", "wait_main", False),
    ("ci", "status"): ("larch.implement.ci", "status_main", False),
    ("ci", "decide"): ("larch.implement.ci", "decide_main", False),
    ("ci", "main-health"): ("larch.implement.ci", "main_health_main", False),
    ("ci", "failed-jobs"): ("larch.implement.ci", "failed_jobs_main", False),
    ("ci", "behind-count"): ("larch.implement.ci", "behind_count_main", False),
    ("ci", "rerun-failed"): ("larch.implement.ci", "rerun_failed_main", False),
}

# Compatibility view: keys whose registry row has machine_stdout=True.
# Derived from _REGISTRY; do not hand-maintain.
_MACHINE_STDOUT_KEYS: frozenset[tuple[str, str]] = frozenset(
    key for key, (_module, _func, machine_stdout) in _REGISTRY.items() if machine_stdout
)

_SHIP_PRE_DRIVER_STALLED_JSON = '{"detail":"Python ship driver requires Python 3.11 or newer","failed_run_id":"","ledger_dispatcher":"","ledger_exit_code":null,"ledger_failure_detail_log":"","ledger_phase":"","ledger_ready":false,"ledger_site":"","ledger_step":"","ledger_trigger":"","merge_result":"","needs_user_reason":"","outcome":"STALLED","pr_number":null,"pr_url":""}'
_MIN_SUBCOMMAND_PARTS = 2


def _version_supported(version_info: object) -> bool:
    return tuple(version_info) >= (3, 11)  # type: ignore[arg-type]


def _unsupported_version_exit(args: list[str]) -> int:
    if len(args) >= _MIN_SUBCOMMAND_PARTS and args[0] == "ship" and args[1] == "pre-driver":
        print("ERROR: Python ship driver requires Python 3.11 or newer", file=sys.stderr)
        print(_SHIP_PRE_DRIVER_STALLED_JSON, file=sys.stderr)
        print("NEXT_ACTION=stall")
        return 4
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
