# pyright: reportUnusedCallResult=false, reportUnusedFunction=false, reportPrivateUsage=false, reportUnusedImport=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalIterable=false, reportArgumentType=false
# ruff: noqa: F401
# pylint: disable=unused-import
"""Native review pipeline CLI entry points.

review panel_hard topology authority: specialists per vendor, Cursor + Codex.

This module is a thin compatibility shim. Implementation lives in:
- review_pipeline_shared.py  — shared utilities and data types
- review_gather.py           — gather-context
- review_prune.py            — reviewer-prune
- review_dispatch_panel.py   — dispatch-panel and dynamic archetypes
- review_collect.py          — collect-findings
- review_threshold.py        — check-reviewer-failure-threshold
- review_core_body.py        — review-core pipeline orchestration
"""

from __future__ import annotations

# Keep module-level attributes that external code monkeypatches or accesses directly.
from larch.core import external_defaults
from larch.core import logging_util
from larch.review.review_pipeline_shared import (
    FOCUS_AREAS,
    PER_REVIEWER_OOS_PROPOSAL_CAP,
    REVIEWER_PRUNE_ACCEPTANCE_FLOOR_DENOMINATOR,
    REVIEWER_PRUNE_ACCEPTANCE_FLOOR_NUMERATOR,
    STATIC_REVIEWERS,
    PreVoteGateError,
    PreVoteOosGateResult,
    ReviewCommands,
    ReviewCoreBranchContext,
    ReviewCoreResult,
    _append_text,
    _atomic_write,
    _bool_string,
    _call_maybe_override,
    _call_review_command,
    _collector_records,
    _diag,
    _emit_kv,
    _emit_result,
    _env_with_plugin,
    _get,
    _get_list,
    _is_nonneg_int,
    _kv_get_file,
    _kv_parse,
    _manifest_rows,
    _normalize_output_base,
    _parse_args,
    _parse_pos_int,
    _run_capture,
    _run_command_string,
    _run_python_cli,
    _runner,
    _usage,
    _write_text,
)
from larch.review.review_types import ReviewCoreStatus

# gather-context
from larch.review.review_gather import (
    _valid_rel_file,
    gather_context,
    gather_context_main,
)

# reviewer-prune
from larch.review.review_prune import (
    PruneFilterResult,
    PruneRoundCounts,
    _ledger_history,
    _legacy_prune_ledger_header,
    _manifest_combo,
    _normalize_code_label,
    _output_label,
    _prune_ledger_header,
    _prune_nonneg_int,
    _read_classification_counts,
    _read_label_map,
    _rewrite_prune_ledger,
    _tokenize_plan_finding_reviewers,
    _well_formed_prune_ledger_row,
    derive_prune_status,
    ensure_reviewer_prune_ledger,
    normalize_prune_eligible,
    prune_window_evaluated,
    reviewer_prune,
    reviewer_prune_filter,
    reviewer_prune_main,
    reviewer_prune_record,
    write_prune_decision_env,
)

# dispatch-panel
from larch.review.review_dispatch_panel import (
    _append_generic_codex_row,
    _append_manifest_row,
    _append_producer_scout_warning_once,
    _append_round_generic_codex_row,
    _append_static_specialist_rows,
    _carry_forward_eligible,
    _degraded_retry_carry_forward,
    _dynamic_agent_body,
    _generic_codex_enabled,
    _implement_scout_status,
    _normalize_scout_manifest,
    _raw_archetype_count,
    _recount_manifest,
    _scout_archetypes,
    _scout_manifest_valid,
    _synthesize_dynamic_slots,
    _valid_dynamic_archetype,
    _write_empty_scout_manifest,
    _write_scout_status,
    dispatch_panel,
    dispatch_panel_main,
)

# collect-findings
from larch.review.review_collect import (
    _clean_oos_focus_title,
    _collector_ok,
    _file_has_no_findings_sentinel,
    _normalize_reviewer_label,
    _parse_output,
    _parse_output_tsv,
    _record_claude_collector_result,
    _record_claude_non_substantive,
    _record_claude_substantive,
    _retain_oos_for_label,
    _valid_reviewer_output_label,
    collect_findings,
    collect_findings_main,
)

# threshold
from larch.review.review_threshold import (
    _dropped_reviewer_output_base,
    _dropped_slot_fields,
    _dynamic_drop_output_base,
    _is_dynamic_reviewer_basename,
    _is_reviewer_output_basename,
    _is_static_reviewer_basename,
    _manifest_rows_by_slot_tool,
    _manifest_slot_tool_by_output,
    _output_file_success,
    _slot_tool_from_reviewer_basename,
    _synthetic_dynamic_drop_key,
    check_reviewer_failure_threshold,
    check_reviewer_failure_threshold_main,
)

# review-core
from larch.review.review_core_body import (
    _apply_pre_vote_oos_gate,
    _append_threshold_dispatch_metadata,
    _collector_success_count,
    _copy_gate_audit_to_parent,
    _copy_to_parent,
    _core_common_rows,
    _emit_core_common,
    _emit_review_core_result,
    _emit_tally,
    _ensure_prune_sidecars,
    _finalize_dropped_reviewer_round,
    _flush_round_log,
    _handle_empty_merge_after_gate,
    _handle_validation_exhausted_after_gate,
    _is_oos_ballot_block,
    _log_pre_vote_gate_issue,
    _oos_title_from_finding_heading,
    _parse_nonnegative_int,
    _parent_dir,
    _post_gate_panel_failed_exit,
    _post_gate_panel_failed_exit_from_context,
    _post_gate_panel_failed_with_audit,
    _post_gate_panel_failed_with_audit_from_context,
    _pre_vote_gate_env_text,
    _pre_vote_gate_rows,
    _promote_gated_ballot_to_findings,
    _prune_nit_then_pre_vote_gate,
    _record_classification,
    _record_prune_round,
    _renumber_finding_blocks,
    _renumber_oos_audit_blocks,
    _restore_oos,
    _review_commands,
    _review_core_body,
    _run_normal_pre_vote_gate,
    _snapshot_oos,
    _static_coverage_reason,
    _static_slug_for_file,
    _write_proposer_sidecar_and_neutralize,
    _zero_findings_branch,
    _zero_findings_from_context,
    review_core,
    review_core_main,
)
