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
    ("status", "check"): ("larch.agents.agents", "status_check_main", False),
    ("calibration-replay", "rebuild-ballot"): ("larch.calibration.calibration_replay", "rebuild_ballot_main", False),
    ("calibration-replay", "run-replay"): ("larch.calibration.calibration_replay", "run_replay_main", False),
    ("calibration-replay", "validate-manifest"): (
        "larch.calibration.calibration_replay",
        "validate_manifest_main",
        False,
    ),
    ("difficulty", "validate-rating"): ("larch.calibration.difficulty", "validate_rating_main", True),
    ("difficulty", "extract-plan-metadata"): ("larch.calibration.difficulty", "extract_plan_metadata_main", True),
    ("difficulty", "write-record"): ("larch.calibration.difficulty", "write_record_main", True),
    ("difficulty", "render-rubric"): ("larch.calibration.difficulty", "render_rubric_main", False),
    ("difficulty", "render-line"): ("larch.calibration.difficulty", "render_line_main", True),
    ("difficulty", "resolve-panel"): ("larch.calibration.difficulty", "resolve_panel_main", True),
    ("difficulty", "sync-labels"): ("larch.calibration.difficulty", "sync_labels_main", True),
    ("debate", "abort"): ("larch.debate.orchestrator", "abort_main", True),
    ("debate", "adjudicate"): ("larch.debate.orchestrator", "adjudicate_main", True),
    ("debate", "adjudication-preview"): ("larch.debate.orchestrator", "adjudication_preview_main", True),
    ("debate", "comment-verify"): ("larch.debate.publication", "comment_verify_main", True),
    ("debate", "init"): ("larch.debate.orchestrator", "init_main", True),
    ("debate", "issue-prepare"): ("larch.debate.publication", "issue_prepare_main", True),
    ("debate", "proposal-link"): ("larch.debate.publication", "proposal_link_main", True),
    ("debate", "publish-prepare"): ("larch.debate.orchestrator", "publish_prepare_main", True),
    ("debate", "record-turn"): ("larch.debate.orchestrator", "record_turn_main", True),
    ("debate", "round-prep"): ("larch.debate.orchestrator", "round_prep_main", True),
    ("debate", "synthesize"): ("larch.debate.orchestrator", "synthesize_main", True),
    ("debate", "title-transition"): ("larch.debate.publication", "title_transition_main", True),
    ("checks", "run-relevant"): ("larch.implement.checks", "checks_run_relevant_main", True),
    ("checks", "fixer-evidence"): ("larch.implement.checks", "checks_fixer_evidence_main", True),
    ("hook", "anti-read-poll"): ("larch.core.hook_anti_read_poll", "anti_read_poll_main", True),
    ("checks", "lint-fix"): ("larch.implement.checks", "checks_lint_fix_main", True),
    ("checks", "repair-loop"): ("larch.implement.checks", "checks_repair_loop_main", True),
    ("checks", "contains-pins"): ("larch.implement.checks", "check_contains_pins_main", True),
    ("checks", "rust-clippy"): ("larch.implement.checks", "rust_clippy_main", False),
    ("checks", "self-edit-log"): ("larch.implement.checks", "checks_self_edit_log_main", True),
    ("ci", "distill-log"): ("larch.implement.ci", "distill_log_main", False),
    ("ci", "rust-select"): ("larch.implement.rust_ci_selection", "rust_select_main", True),
    ("ci", "rust-select-summary"): (
        "larch.implement.rust_ci_selection",
        "rust_select_summary_main",
        True,
    ),
    ("bootstrap", "invoke"): ("larch.state.bootstrap", "invoke_main", True),
    ("bootstrap", "parse-routing"): ("larch.state.bootstrap", "parse_routing_main", True),
    ("bootstrap", "resolve-non-interactive"): ("larch.state.bootstrap", "resolve_non_interactive_main", False),
    ("residual-bash", "paths"): ("larch.core.residual_bash", "paths_main", True),
    ("verify", "main"): ("larch.core.verify_main", "main", False),
    ("audit-runs", "preflight"): ("larch.issue.audit_runs", "preflight_main", False),
    ("audit-runs", "resolve-prs"): ("larch.issue.audit_runs", "resolve_prs_main", False),
    ("audit-runs", "map-runs"): ("larch.issue.audit_runs", "map_runs_main", False),
    ("audit-runs", "scan-run"): ("larch.issue.audit_runs", "scan_run_main", False),
    ("audit-runs", "compute-counters"): ("larch.issue.audit_runs", "compute_counters_main", False),
    ("audit-runs", "title"): ("larch.issue.audit_runs", "title_main", False),
    ("audit-runs", "title-match"): ("larch.issue.audit_runs", "title_match_main", False),
    ("audit-runs", "pacific-timestamp"): ("larch.issue.audit_runs", "pacific_timestamp_main", False),
    ("audit-runs", "bugs-backlog-nudge"): ("larch.issue.audit_runs", "bugs_backlog_nudge_main", False),
    ("audit-runs", "close-priors"): ("larch.issue.audit_runs", "close_priors_main", False),
    ("complete-umbrella", "ship-leaf"): (
        "larch.implement.complete_umbrella_ship",
        "main",
        True,
    ),
    ("analyze-issues", "fetch"): ("larch.issue.analyze_issues", "fetch_main", False),
    ("analyze-issues", "run"): ("larch.issue.analyze_issues", "run_main", False),
    ("analyze-issues", "analyze"): ("larch.issue.analyze_issues", "analyze_main", False),
    ("analyze-bugs", "prefetch"): ("larch.issue.analyze_bugs", "prefetch_main", False),
    ("analyze-bugs", "ledger"): ("larch.issue.analyze_bugs", "ledger_main", False),
    ("analyze-bugs", "runtime"): ("larch.issue.analyze_bugs", "runtime_main", False),
    ("analyze-bugs", "report"): ("larch.issue.analyze_bugs", "report_main", False),
    ("validate-merged", "prepare"): ("larch.issue.validate_merged", "prepare_main", False),
    ("validate-merged", "ingest-finder"): ("larch.issue.validate_merged", "ingest_finder_main", False),
    ("validate-merged", "ingest-refuter"): ("larch.issue.validate_merged", "ingest_refuter_main", False),
    ("validate-merged", "report"): ("larch.issue.validate_merged", "report_main", False),
    ("validate-merged", "write-state"): ("larch.issue.validate_merged", "write_state_main", False),
    ("learn-from-bugs", "prepare"): ("larch.issue.learn_from_bugs", "prepare_main", True),
    ("learn-from-bugs", "coverage-index"): ("larch.issue.learn_from_bugs", "coverage_index_main", False),
    ("learn-from-bugs", "read-state"): ("larch.issue.learn_from_bugs", "read_state_main", True),
    ("learn-from-bugs", "check-proposals"): ("larch.issue.learn_from_bugs", "check_proposals_main", True),
    ("learn-from-bugs", "write-state"): ("larch.issue.learn_from_bugs", "write_state_main", True),
    ("learn-from-bugs", "verify-origin"): ("larch.issue.learn_from_bugs", "verify_origin_main", True),
    ("learn-from-bugs", "state-publish"): ("larch.issue.learn_from_bugs", "state_publish_main", True),
    ("learn-from-bugs", "resolve-zones"): ("larch.issue.learn_from_bugs", "resolve_zones_main", False),
    ("learn-from-bugs", "validate-report"): ("larch.issue.learn_from_bugs", "validate_report_main", False),
    ("learn-from-bugs", "filing-deps"): ("larch.issue.learn_from_bugs", "filing_deps_main", False),
    ("rejected-analysis", "prepare"): ("larch.issue.rejected_analysis", "prepare_main", False),
    ("rejected-analysis", "ingest-verdict"): ("larch.issue.rejected_analysis", "ingest_verdict_main", False),
    ("rejected-analysis", "finalize"): ("larch.issue.rejected_analysis", "finalize_main", False),
    ("rejected-analysis", "record"): ("larch.issue.rejected_analysis", "record_main", False),
    ("implement", "step2-dispatch"): ("larch.implement.implement_dispatch", "step2_dispatch_main", False),
    ("implement", "run-dispatch"): ("larch.implement.implement_dispatch", "run_dispatch_main", False),
    ("implement", "recovery-paths"): ("larch.implement.implement_dispatch", "recovery_paths_main", False),
    ("implement", "commit"): ("larch.implement.implement_dispatch", "commit_main", False),
    ("implement", "commit-route"): ("larch.implement.implement_dispatch", "commit_route_main", True),
    ("implement", "scope-disposition"): ("larch.implement.scope_disposition", "scope_disposition_main", True),
    ("implement", "checks-commit-route"): ("larch.implement.implement_dispatch", "checks_commit_route_main", True),
    ("implement", "checks-step5-resume"): ("larch.implement.implement_dispatch", "checks_step5_resume_main", True),
    ("implement", "clone-tag"): ("larch.implement.implement_dispatch", "clone_tag_main", False),
    ("implement", "kill-active-leg"): ("larch.implement.implement_dispatch", "kill_active_leg_main", False),
    ("implement", "normalize-coder-scout"): ("larch.implement.implement_dispatch", "normalize_coder_scout_main", False),
    ("implement", "step-0-bootstrap"): ("larch.implement.implement_dispatch", "step0_bootstrap_main", False),
    ("implement", "step-0-degraded-gate"): ("larch.implement.implement_dispatch", "step0_degraded_gate_main", False),
    ("implement", "step-2-post-dispatch"): ("larch.implement.implement_dispatch", "step2_post_dispatch_main", False),
    ("implement", "step-5-review"): ("larch.implement.implement_dispatch", "step5_review_main", False),
    ("implement", "step-5-resume"): ("larch.implement.implement_dispatch", "step5_resume_main", False),
    ("implement", "step-6-entry"): ("larch.implement.implement_dispatch", "step6_entry_main", True),
    ("implement", "step-8-python-guard"): ("larch.implement.implement_dispatch", "step8_python_guard_main", False),
    ("implement", "step-8-seed-initial"): ("larch.implement.implement_dispatch", "step8_seed_initial_main", False),
    ("implement", "step-8-ship"): ("larch.implement.implement_dispatch", "step8_ship_main", False),
    ("implement", "step-8-oos-checkpoint"): ("larch.implement.implement_dispatch", "step8_oos_checkpoint_main", True),
    ("implement", "step-18"): ("larch.implement.implement_dispatch", "step_18_main", True),
    ("implement", "step-18-gate-logs-flush"): ("larch.implement.implement_dispatch", "step_18_gate_logs_flush_main", True),
    ("implement", "step-19"): ("larch.implement.implement_dispatch", "step_19_main", True),
    ("implement", "run-step-checks"): ("larch.implement.implement_dispatch", "run_step_checks_main", False),
    ("implement", "checks-result-identity"): (
        "larch.implement.checks_result_identity",
        "checks_result_identity_main",
        False,
    ),
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
    ("plan", "parse-commands"): ("larch.design.plan_quality", "parse_plan_commands_main", False),
    ("plan", "validate-commands"): ("larch.design.plan_quality", "validate_plan_commands_main", True),
    ("plan", "validate"): ("larch.design.plan_quality", "validate_plan_main", True),
    ("plan", "check-size"): ("larch.design.plan_quality", "check_plan_size_main", True),
    ("plan", "set-oversize-override"): ("larch.design.plan_quality", "set_oversize_override_main", True),
    ("plan", "revise-waterfall"): ("larch.design.plan_quality", "revise_plan_with_waterfall_main", True),
    ("plan", "auto-fix-commands"): ("larch.design.plan_quality", "auto_fix_plan_commands_main", True),
    ("plan", "validator-autofix"): ("larch.design.plan_quality", "validator_autofix_main", True),
    ("plan", "optional-trailers"): ("larch.design.plan_quality", "optional_trailers_main", True),
    ("plan", "compose-goals-test"): ("larch.design.plan_quality", "compose_plan_goals_test_main", True),
    ("plan", "step1-log"): ("larch.design.design_step_log", "step1_log_main", True),
    ("plan-review", "run"): ("larch.review.plan_review", "run_main", True),
    ("plan-review", "write-loop-identity"): ("larch.core.process_identity", "write_loop_identity_main", False),
    ("plan-review", "await-loop-identity"): ("larch.core.process_identity", "await_loop_identity_main", False),
    ("plan-review", "teardown-loop-identity"): ("larch.core.process_identity", "teardown_loop_identity_main", False),
    ("plan-review", "normalize-status"): ("larch.review.plan_review", "normalize_step3_status_main", True),
    ("plan-review", "panel-dispatch"): ("larch.review.plan_review_panel", "dispatch_panel_main", True),
    ("plan-review", "voter-dispatch"): ("larch.review.plan_review_panel", "dispatch_voters_main", True),
    ("plan-review", "tally"): ("larch.review.plan_review", "tally_main", True),
    ("plan-review", "emit"): ("larch.review.plan_review", "emit_main", True),
    ("plan-review", "finalize"): ("larch.review.plan_review", "finalize_main", True),
    ("plan-review", "preview"): ("larch.review.plan_review", "preview_main", True),
    ("plan-review", "snapshot-pre-review"): (
        "larch.review.plan_review_accepted_audit",
        "snapshot_pre_review_main",
        False,
    ),
    ("plan-review", "filter-gate-b-skipped"): ("larch.review.plan_review_accepted_audit", "filter_gate_b_skipped_main", True),
    ("plan-review", "persist-accepted-audit"): ("larch.review.plan_review_accepted_audit", "persist_accepted_audit_main", True),
    ("plan-review", "gate-b-counts"): ("larch.review.plan_review", "gate_b_counts_main", True),
    ("plan-review", "gate-b-finding-line"): ("larch.review.plan_review", "gate_b_finding_line_main", True),
    ("plan-review", "gate-b-dedup"): ("larch.review.plan_review", "gate_b_dedup_main", True),
    ("plan-review", "persist-retally-env"): ("larch.review.plan_review", "persist_retally_env_main", True),
    ("plan-review", "persist-round-start-s"): ("larch.review.plan_review", "persist_round_start_s_main", True),
    ("plan-review", "step3-state"): ("larch.review.plan_review", "step3_state_main", True),
    ("plan-review", "record-round-timing"): ("larch.review.plan_review", "record_round_timing_main", True),
    ("plan-review", "continuation"): ("larch.review.plan_review", "continuation_main", True),
    ("plan-review", "prelaunch-failure"): ("larch.review.plan_review", "prelaunch_failure_main", True),
    ("plan-review", "step3-entry"): ("larch.review.plan_review", "step3_entry_main", True),
    ("plan-review", "step3-entry-preview"): ("larch.review.plan_review", "step3_entry_preview_main", True),
    ("plan-review", "step3-entry-state"): ("larch.review.plan_review", "step3_entry_state_main", True),
    ("plan-review", "step3-gate-b-bypass"): ("larch.review.plan_review", "step3_gate_b_bypass_main", True),
    ("plan-review", "step3-mav"): ("larch.review.plan_review", "step3_mav_main", True),
    ("design", "step3b-entry"): ("larch.design.design_step3b", "step3b_entry_main", True),
    ("plan-review", "step3b-tail"): ("larch.review.plan_review", "step3b_tail_main", True),
    ("plan-review", "emit-rejected"): ("larch.review.plan_review", "emit_rejected_main", True),
    ("plan-review", "step35"): ("larch.review.plan_review", "step35_main", True),
    ("plan-review", "step35-settle"): ("larch.design.design_settle", "step35_settle_main", True),
    ("plan-review", "json-get-bool"): ("larch.review.plan_review", "json_get_bool_main", True),
    ("plan-review", "round-artifact-included"): ("larch.review.plan_review", "round_artifact_included_main", False),
    ("plan-review", "round-revise-artifact-included"): (
        "larch.review.plan_review",
        "round_revise_artifact_included_main",
        False,
    ),
    ("plan-review", "round-revise-artifact-excluded"): (
        "larch.review.plan_review",
        "round_revise_artifact_excluded_main",
        False,
    ),
    ("plan-review", "drift-baseline"): ("larch.review.plan_review", "drift_baseline_main", False),
    ("issue", "migration-audit"): (
        "larch.issue.migration_governance",
        "migration_audit_main",
        True,
    ),
    ("alias", "generate"): ("larch.core.alias_skill", "generate_main", False),
    ("alias", "resolve-target"): ("larch.core.alias_skill", "resolve_target_main", False),
    ("cleanup", "run"): ("larch.core.cleanup_skill", "run_main", False),
    ("forked-repo", "setup"): ("larch.core.forked_repo", "setup_main", False),
    ("design", "parse-flags"): ("larch.design.design_argv", "parse_flags_main", True),
    ("design", "step0-parse"): ("larch.design.design_step0_env", "step0_parse_main", True),
    ("design", "step0-session"): ("larch.design.design_step0", "step0_session_entry_main", True),
    ("design", "step0-route"): ("larch.design.design_step0", "step0_route_main", True),
    ("design", "step0-clarify-hard-halt"): ("larch.design.design_step0", "step0_clarify_hard_halt_main", True),
    ("design", "step0-init"): ("larch.design.design_step0", "step0_init_main", True),
    ("design", "step0-abort-cleanup"): ("larch.design.design_step0", "step0_abort_cleanup_main", True),
    ("design", "step0-ap-continue"): ("larch.design.design_step0", "step0_ap_continue_main", True),
    ("design", "step0c"): ("larch.design.design_step0", "step0c_main", True),
    ("design", "step1d5"): ("larch.design.design_step1", "step1d5_main", True),
    ("design", "step1d7"): ("larch.design.design_step1", "step1d7_main", True),
    ("design", "step1e-reentry"): ("larch.design.design_step1", "step1e_reentry_main", True),
    ("design", "route"): ("larch.design.design_router", "route_main", True),
    ("design", "init-runparams"): ("larch.design.design_router", "init_runparams_main", True),
    ("design", "driver"): ("larch.design.design_step1", "driver_main", True),
    ("design", "read-result-env"): ("larch.design.design_terminal", "read_result_env_main", True),
    ("design", "stage-terminal-state"): ("larch.design.design_terminal", "stage_terminal_state_main", True),
    ("design", "failure-report"): ("larch.design.design_terminal", "failure_report_main", True),
    ("design", "step-final-summary"): ("larch.design.design_terminal", "step_final_summary_main", True),
    ("design", "step2b-drafter"): ("larch.design.design_step2b", "step2b_drafter_main", True),
    ("design", "step2b-postplan"): ("larch.design.design_step2b", "step2b_postplan_main", True),
    ("design", "settle-next-action"): ("larch.design.design_session", "settle_next_action_main", True),
    ("design", "step35-settle"): ("larch.design.design_settle", "step35_settle_main", True),
    ("design", "prelude"): ("larch.design.design_session", "prelude_main", True),
    ("design", "step3-continuation-entry"): ("larch.design.design_session", "step3_continuation_entry_main", True),
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
    ("research", "validate-citations"): ("larch.research.research", "validate_citations_main", False),
    ("research", "render-findings-batch"): ("larch.research.research", "render_findings_batch_main", False),
    ("research", "run-planner"): ("larch.research.research", "run_research_planner_main", False),
    ("research", "banner"): ("larch.research.research", "compute_research_banner_main", False),
    ("eval", "validate-research-output"): ("larch.research.research_eval", "validate_research_output_main", False),
    ("eval", "research"): ("larch.research.research_eval", "eval_research_main", False),
    ("render", "specialist"): ("larch.rendering.rendering", "render_specialist_main", False),
    ("render", "reviewer"): ("larch.rendering.rendering", "render_reviewer_main", False),
    ("render", "lane-status"): ("larch.rendering.rendering", "render_lane_status_main", False),
    ("render", "voter"): ("larch.rendering.rendering", "render_voter_main", False),
    ("render", "plan-review"): ("larch.rendering.rendering", "render_plan_review_main", False),
    ("render", "scope-anchor"): ("larch.rendering.rendering", "render_scope_anchor_main", False),
    ("render", "findings-view"): ("larch.rendering.rendering", "render_findings_view_main", False),
    ("voter-calibration", "snapshot"): ("larch.review.voting", "voter_calibration_snapshot_main", False),
    ("difficulty-calibration", "analyze"): ("larch.calibration.difficulty_calibration", "analyze_main", False),
    ("scope-anchor", "relay-allowed"): ("larch.rendering.rendering", "scope_anchor_relay_allowed_main", False),
    ("scope-anchor", "validate"): ("larch.rendering.rendering", "scope_anchor_validate_main", False),
    ("scope-anchor", "retally-handoff"): ("larch.rendering.rendering", "scope_anchor_retally_handoff_main", False),
    ("scope-anchor", "design-handoff"): ("larch.rendering.rendering", "scope_anchor_design_handoff_main", False),
    ("review", "gather-context"): ("larch.review.review_gather", "gather_context_main", True),
    ("review", "dispatch-panel"): ("larch.review.review_dispatch_panel", "dispatch_panel_main", True),
    ("review", "collect-findings"): ("larch.review.review_collect", "collect_findings_main", True),
    ("review", "check-reviewer-failure-threshold"): (
        "larch.review.review_threshold",
        "check_reviewer_failure_threshold_main",
        True,
    ),
    ("review", "aggregate-findings"): ("larch.review.review_aggregate", "aggregate_findings_main", True),
    ("review", "prune-nit-findings"): ("larch.review.review_aggregate", "prune_nit_findings_main", True),
    ("review", "tally-code-votes"): ("larch.review.review_tally", "tally_code_votes_main", True),
    ("review", "emit-tally"): ("larch.review.review_tally", "emit_tally_main", True),
    ("review", "log-phase"): ("larch.review.review_tally", "log_phase_main", True),
    ("review", "core"): ("larch.review.review_core_body", "review_core_main", True),
    ("review", "reviewer-prune"): ("larch.review.review_prune", "reviewer_prune_main", False),
    ("review", "compose-findings"): ("larch.review.compose_review", "compose_findings_main", True),
    ("review-and-fix", "apply-findings"): ("larch.review.review_and_fix", "apply_findings", True),
    ("review-and-fix", "step5"): ("larch.review.review_and_fix", "step5", True),
    ("review-and-fix", "write-loop-identity"): ("larch.core.process_identity", "write_step5_loop_identity_main", False),
    ("review-and-fix", "await-loop-identity"): ("larch.core.process_identity", "await_step5_loop_identity_main", False),
    ("review-and-fix", "teardown-loop-identity"): (
        "larch.core.process_identity",
        "teardown_step5_loop_identity_main",
        False,
    ),
    ("review-and-fix", "normalize-status"): ("larch.review.review_and_fix", "normalize_status", True),
    ("review-and-fix", "check-changes"): ("larch.review.review_and_fix", "check_changes", True),
    ("review-and-fix", "commit-fixes"): ("larch.review.review_and_fix", "commit_fixes", True),
    ("review-and-fix", "write-rejected"): ("larch.review.review_and_fix", "write_rejected", True),
    ("review-and-fix", "record-round-timing"): ("larch.review.review_and_fix", "record_round_timing", True),
    ("review-and-fix", "write-self-review-tally"): ("larch.review.review_and_fix", "write_self_review_tally", True),
    ("review-and-fix", "write-pre-self-review-snapshot"): (
        "larch.review.review_and_fix",
        "write_pre_self_review_snapshot",
        True,
    ),
    ("mermaid", "sanitize"): ("larch.rendering.rendering", "mermaid_sanitize_main", False),
    ("diagrams", "upsert"): ("larch.rendering.rendering", "diagrams_upsert_main", False),
    ("generate", "code-reviewer-agent"): ("larch.rendering.rendering", "generate_code_reviewer_agent_main", False),
    ("generate", "reviewer-plan-fidelity-agent"): (
        "larch.rendering.rendering",
        "generate_reviewer_plan_fidelity_agent_main",
        False,
    ),
    ("generate", "reviewer-code-robustness-agent"): (
        "larch.rendering.rendering",
        "generate_reviewer_code_robustness_agent_main",
        False,
    ),
    ("generate", "reviewer-security-structure-tests-agent"): (
        "larch.rendering.rendering",
        "generate_reviewer_security_structure_tests_agent_main",
        False,
    ),
    ("generate", "reviewer-structure-agent"): ("larch.rendering.rendering", "generate_reviewer_structure_agent_main", False),
    ("generate", "reviewer-correctness-agent"): ("larch.rendering.rendering", "generate_reviewer_correctness_agent_main", False),
    ("generate", "reviewer-testing-agent"): ("larch.rendering.rendering", "generate_reviewer_testing_agent_main", False),
    ("generate", "reviewer-security-agent"): ("larch.rendering.rendering", "generate_reviewer_security_agent_main", False),
    ("generate", "reviewer-edge-cases-agent"): ("larch.rendering.rendering", "generate_reviewer_edge_cases_agent_main", False),
    ("generate", "pre-rendered-reviewer-prompts"): (
        "larch.rendering.rendering",
        "generate_pre_rendered_reviewer_prompts_main",
        False,
    ),
    ("generate", "codex-implementer"): ("larch.rendering.rendering", "generate_codex_implementer_main", False),
    ("generate", "cursor-implementer"): ("larch.rendering.rendering", "generate_cursor_implementer_main", False),
    ("generate", "topology-docs"): ("larch.rendering.rendering", "generate_topology_docs_main", False),
    ("generate", "check"): ("larch.rendering.rendering", "generate_check_main", False),
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
    ("token", "mark"): ("larch.report.tokens", "token_mark_main", False),
    ("token", "record-vendor"): ("larch.report.tokens", "token_record_vendor_main", False),
    ("token", "dump"): ("larch.report.tokens", "token_dump_main", False),
    ("token", "report"): ("larch.report.tokens", "token_report_main", False),
    ("token", "check-budget"): ("larch.report.tokens", "token_check_budget_main", False),
    ("token", "claude-source"): ("larch.report.tokens", "token_claude_source_main", False),
    ("token", "lane-write"): ("larch.report.tokens", "token_lane_write_main", False),
    ("token", "lane-report"): ("larch.report.tokens", "token_lane_report_main", False),
    ("token", "append-record"): ("larch.report.tokens", "token_append_record_main", False),
    ("token", "record-vendor-sidecar"): ("larch.report.tokens", "token_record_vendor_sidecar_main", False),
    ("token", "cost"): ("larch.report.tokens", "token_cost_main", False),
    ("token", "render-cost-line"): ("larch.report.tokens", "token_render_cost_line_main", False),
    ("token", "compute-pr-line-counts"): ("larch.report.tokens", "compute_pr_line_counts_main", False),
    ("token", "compute-pr-lines"): ("larch.report.tokens", "compute_pr_lines_main", False),
    ("token", "measure-md-cost"): ("larch.report.tokens", "measure_md_cost_main", False),
    ("token", "measure-cache-efficiency"): ("larch.report.tokens", "measure_cache_efficiency_main", False),
    ("token", "measure-ngram-duplication"): ("larch.report.tokens", "measure_ngram_duplication_main", False),
    ("token", "measure-references-heatmap"): ("larch.report.tokens", "measure_references_heatmap_main", False),
    ("token", "measure-realized-cost"): ("larch.report.tokens", "measure_realized_cost_main", False),
    ("token", "measure-panel-cost"): ("larch.report.tokens", "measure_panel_cost_main", False),
    ("token", "measure-checks-digest-savings"): ("larch.report.tokens", "measure_checks_digest_savings_main", False),
    ("voting", "findings-classification-header"): ("larch.review.voting", "findings_classification_header_main", False),
    ("voting", "code-review-classification-header"): (
        "larch.review.voting",
        "code_review_classification_header_main",
        False,
    ),
    ("voting", "vote-for-id"): ("larch.review.voting", "vote_for_id_main", False),
    ("voting", "reviewer-for-block"): ("larch.review.voting", "reviewer_for_block_main", False),
    ("voting", "is-security-block"): ("larch.review.voting", "is_security_block_main", False),
    ("voting", "accept-finding"): ("larch.review.voting", "accept_finding_main", False),
    ("voting", "classify-result"): ("larch.review.voting", "classify_result_main", False),
    ("voting", "panel-tier"): ("larch.review.voting", "panel_tier_main", False),
    ("voting", "split-ballot"): ("larch.review.voting", "split_ballot_main", False),
    ("voting", "parse-judge-vote"): ("larch.review.voting", "parse_judge_vote_main", False),
    ("voting", "parse-rate-check"): ("larch.review.voting", "parse_rate_check_main", False),
    ("voting", "parse-rate-retry"): ("larch.review.voting", "parse_rate_retry_main", False),
    ("voting", "parse-rate-diag-matches"): ("larch.review.voting", "parse_rate_diag_matches_main", False),
    ("voting", "effective-judges"): ("larch.review.voting", "effective_judges_main", False),
    ("voting", "degraded-warning"): ("larch.review.voting", "degraded_warning_main", False),
    ("voting", "voter-status-block"): ("larch.review.voting", "voter_status_block_main", False),
    ("voting", "write-tally"): ("larch.review.voting", "write_tally_main", False),
    ("voting", "compose-tally-record"): ("larch.review.voting", "compose_tally_record_main", False),
    ("voting", "false-positive-match"): ("larch.review.voting", "false_positive_match_main", False),
    ("voting", "file-line-regex"): ("larch.review.voting", "file_line_regex_main", False),
    ("voting", "ballot-parse"): ("larch.review.voting", "ballot_parse_main", False),
    ("voting", "tally-vote"): ("larch.review.voting", "tally_vote_main", False),
    ("voting", "scoreboard"): ("larch.review.voting", "scoreboard_main", False),
    ("redact", "secrets"): ("larch.core.redact", "main_secrets", False),
    ("redact", "tmpdir-paths"): ("larch.core.redact", "main_tmpdir_paths", False),
    ("redact", "scrub-log-secrets"): ("larch.core.redact", "main_scrub_log_secrets", False),
    ("redact", "scrub-submodule-paths"): ("larch.core.redact", "main_scrub_submodule_paths", False),
    ("verify", "skill-called"): ("larch.core.verify_skill", "main", False),
    ("stall-recovery", "lint"): ("larch.state.stall_recovery", "lint_main", True),
    ("implement", "step-7a"): ("larch.implement.step_7a", "main", True),
    ("implement", "preflight"): ("larch.implement.preflight", "preflight_main", True),
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
    ("ci", "wait"): ("larch.implement.ci", "wait_main", False),
    ("ci", "status"): ("larch.implement.ci", "status_main", False),
    ("ci", "decide"): ("larch.implement.ci", "decide_main", False),
    ("ci", "main-health"): ("larch.implement.ci", "main_health_main", False),
    ("ci", "failed-jobs"): ("larch.implement.ci", "failed_jobs_main", False),
    ("ci", "behind-count"): ("larch.implement.ci", "behind_count_main", False),
    ("ci", "rerun-failed"): ("larch.implement.ci", "rerun_failed_main", False),
    ("session", "setup"): ("larch.state.session_env", "setup_main", False),
    ("session", "local-cleanup"): ("larch.state.session_env", "local_cleanup_main", False),
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

    try:
        return int(target_main(rest_argv))
    except RuntimeError as exc:
        plan_review_mod = sys.modules.get("larch.review.plan_review")
        if plan_review_mod is not None:
            plan_review_error = getattr(plan_review_mod, "PlanReviewError", None)
            if plan_review_error is not None and isinstance(exc, plan_review_error):
                print(f"ERROR: plan-review: {exc}", file=sys.stderr)
                return 1
        raise


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
