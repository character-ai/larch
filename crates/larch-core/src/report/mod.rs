//! Shared report Markdown block, issue-detail, run-log corpus, and rendering
//! helpers.
//!
//! Library parity for Python `larch.report.markdown_block` and
//! `larch.report.exec_issue_detail`, plus read-only parity for
//! `larch.report.run_log_batch` and `larch.report.run_log_corpus`. The
//! [`gantt`], [`growth_chart`], [`cost_plot`], and [`diagram_log`] modules own
//! the migrated renderers and the bounded diagram failure log.

pub mod cost_plot;
mod diagram_log;
mod exec_issue_detail;
mod final_report;
pub mod gantt;
pub mod growth_chart;
mod markdown_block;
mod path_warning;
mod raster;
mod run_log_corpus;
mod run_summary;
mod session_transcript;
pub mod timing;
mod token_cost;
mod token_ledger;
mod token_measurements;
mod token_report;
mod token_scan;

pub use diagram_log::{
    bounded_diagram_warning_body, sanitize_diagram_capture, strip_diagram_sections,
    write_bounded_diagram_failure_log,
};
pub use exec_issue_detail::{
    ASSESSMENT_TIMEOUT_SECONDS, DEFAULT_ASSESSMENT_MODEL, EMPTY_GROUPS,
    ENV_EXEC_ISSUE_ASSESSMENT_MODEL, IssueDetail, IssueDetailGroups, IssueEvent, LoadResult,
    MAX_ASSESSMENT_LEN, MAX_DEDUPE_KEY_LEN, MAX_DISPLAY_LEN, WARN_CATEGORY, assessment_prompt_text,
    assessment_sentence, build_issue_detail_section, count_issue_groups, count_load_result,
    execution_issue_identity, load_issue_detail_groups, normalize_body_for_hash,
    parse_markdown_execution_issues, render_issue_detail_block, structured_body_dedupe_keys,
};
pub use final_report::{
    DIFFICULTY_RECORD_BASENAME, LINE_COUNT_STATE_KEYS, MANIFEST_STATUS_DONE,
    MANIFEST_STATUS_IN_PROGRESS, MERGE_COMPLETED_OUTCOMES, NORMALIZED_OUTCOMES,
    architectural_section, count_code_review_findings, derive_oos_fields, derive_review_line,
    difficulty_line, difficulty_summary_line, dynamic_archetypes_line, final_report_duration,
    join_prefixed_summary, json_object, latest_token_ledger, manifest_only_recovered_outcome,
    merged_line_count_state, needs_user_execution_entry, outcome_with_manifest_only_backstop,
    read_state_kv, reconciled_stalled_summary, stalled_summary_manifest_reconciliation_needed,
    state_file_has_rows, summary_heading_is_stalled, token_argv_from_report,
};
pub use markdown_block::{
    BlockMarkers, BlockMarkersError, BlockMarkersErrorKind, replace_markdown_block,
    replace_markdown_block_with_warn,
};
pub use path_warning::PathWarning;
pub use run_log_corpus::{
    RunLogBatchArtifact, RunLogBatchMode, RunLogBatchSanitizer, RunLogBatchSpec, RunLogCorpus,
    RunLogCorpusEvent, RunLogCorpusIter, RunLogCorpusWarning, RunLogCorpusWarningKind,
    RunLogFileIter, RunLogManifest, RunLogRoundSort, RunLogRun, RunLogSelection, RunLogTimeWindow,
    RunLogTimeWindowError, parse_preterminal_outcome_label, round_number_from_path,
    run_log_batch_spec, run_log_batch_specs, run_started_at_without_manifest,
};
pub use run_summary::{
    GLM_TOKEN_TO_PLAN_DIVISOR, RunSummaryCost, RunSummaryFields, RunSummaryIdentity,
    map_outcome_display, render_run_summary,
};
pub use session_transcript::{
    MAX_INPUT_BYTES as MAX_TRANSCRIPT_INPUT_BYTES, MAX_RECORD_BYTES as MAX_TRANSCRIPT_RECORD_BYTES,
    RenderedTranscript, SCHEMA_VERSION as TRANSCRIPT_SCHEMA_VERSION, TRANSCRIPT_POLICY,
    TranscriptError, TranscriptWarnings, render_session_transcript,
};
pub use token_cost::{
    BLENDED_FALLBACK_WARNING, CODEX_MINI_MODELS, CURSOR_COMPOSER_BASE_RATES, CURSOR_GROK_MODELS,
    CURSOR_TEAMS_TOKEN_RATE_SURCHARGE_PER_M, ClaudeCounts, CodexCounts, CursorCounts, RATE_TABLE,
    RateRow, RunCost, TokenCostError, TokenCostValues, TokenCounts, TokenRates,
    aggregate_vendor_tokens, cursor_buckets_are_detailed, display_rates, exact_rate_row,
    fallback_cost, format_money, price_counts, price_run, python_round, rate_row, render_cost_kv,
    render_cost_line,
};
pub use token_ledger::{
    TokenSidecarPayload, active_ledger_vendor, contains_dotdot, default_ledger_basename,
    lane_sidecar_body, lane_sidecar_name, mark_line, parse_token_record_sidecar,
    render_lane_report, resolve_under_roots, safe_lane_slug, sha256_hex, sidecar_ndjson_line,
    validate_lane_phase, validate_total_tokens, vendor_line,
};
pub use token_measurements::{
    checks_digest_savings, markdown_cost, ngram_duplication, panel_cost, realized_cost,
    reference_heatmap, token_cache_efficiency, token_cache_efficiency_with_diagnostics,
};
pub use token_report::{
    ALL_RUNS, CACHE_BASENAME, EMPTY_REPORT_BODY, IssueBodyError, PricedRun, REPORT_HEADING,
    RenderedReport, ReportSection, SectionPriority, assemble_issue_body, cache_ndjson, daily_costs,
    render_report, title_for_skill,
};
pub use token_scan::{
    CODEX_IMPLEMENT_RAW_LABEL, CURSOR_IMPLEMENT_RAW_LABEL, IMPLEMENT_STEP2_LABEL,
    IMPLEMENT_STEP2_PREFIX, TOKEN_VENDORS, TokenCorpusScan, TokenObservation, TokenObservationKind,
    TokenObservations, TokenPhaseRow, TokenReportError, TokenReportInputs, TokenRunRecord,
    TokenScanEvent, TokenScanWarning, TokenScanWarningKind, TokenStepMark, TokenUsageRow,
    TokenVendor, VendorTotals, build_report_from_ledgers, claude_effective_cache_create,
    claude_usage_rows, effective_vendor_total, full_report, full_report_with_observations,
    ledger_step_marks, ledger_vendor_rows, parse_epoch, read_ledger, read_report_inputs,
    report_has_numeric_tokens, resolve_run_report, run_log_ledger_path, run_record, safe_int,
    summary_report, token_phase_rows, token_report_basename, transcript_sources,
    vendor_totals_from_report,
};
