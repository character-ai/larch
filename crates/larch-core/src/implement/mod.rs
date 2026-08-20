//! `/implement` dispatch shared layer (#8610).
//!
//! Recovery-path resolution, porcelain helpers, lean manifest state, and
//! step-checks site mapping for later dispatch cutovers.

mod active_leg;
mod checks_lint_fix;
mod contains_pins;
mod dispatch_manifest;
mod helpers;
mod identity;
mod manifest;
mod recovery;
mod relevant_checks;
mod relevant_checks_digest;
mod self_edit_log;
mod step_checks;

pub use active_leg::{
    ACTIVE_LEG_CALLER, ACTIVE_LEG_IDENTITY_FILE, ACTIVE_LEG_KILL_LOG_FILE,
    ACTIVE_LEG_LEGACY_PGID_FILE, ACTIVE_LEG_REASON, ENV_ACTIVE_LEG_OWNER_TOKEN, REASON_LEGACY_PGID,
    REASON_MALFORMED, REASON_MISSING_TOKEN, record_matches, recorded_identity_from_payload,
    refusal_event, terminate_active_leg_group,
};
pub use checks_lint_fix::{
    CHECKS_FIXER_MAX_ROUNDS, CLAUDE_CI_FIX_MODEL, FIXER_LANE_TIMEOUT_SEC, FixOutcome,
    LINT_FIX_ROLE_ID, NEEDS_USER_SHIP_PR_INTERNAL_LINT_FIX, PRE_SHIP_ALL_TIERS_NO_DELTA_REASON,
    PROC_TIMEOUT_EXIT_CODE, PROMPT_TAIL_BYTES, RepoPathState, checks_fixer_evidence_path,
    classify_attempt_issue, coder_forbidden_paths, codex_lint_fix_prompt_appendix, compose_prompt,
    exhausted_outcome, forbidden_paths_match_count, is_known_site, is_pre_ship_site,
    ledger_phase_for_site, ledger_site_for_lint_site, ledger_step_for_site,
    ledger_trigger_for_lint_site, lint_fix_fast_fail_reason, path_matches_forbidden,
    read_log_file_text, read_log_tail, resolve_checks_log_path, sanitize_log_fence, site_label,
    snapshot_delta_paths, target_cmd_display_valid, tier_ledger_header, tier_ledger_line,
    valid_fixer_site,
};
pub use contains_pins::{ContainsPinsScan, normalize_rel, read_changed_scope, scan_contains_pins};
pub use dispatch_manifest::{
    CompletionRetryInvalid, CompletionRetryState, MANIFEST_STATUSES, PORCELAIN_MIN_PARTS,
    RESUME_CAP, SAFE_CODERS, SUMMARY_BULLETS_MAX, WRAPPER_VALIDATION_RC,
    child_stdout_is_claude_fallback, complete_schema_valid, declared_paths, files_touched_paths,
    json_scalar_string, json_scalar_text, manifest_complete_salvageable, manifest_status,
    model_value_safe, needs_qa_questions_present, oos_materialize_should_bail,
    parse_completion_retry_state, qa_pending_valid, repaired_qa_questions,
    require_architectural_acknowledgment, sanitize_architectural_acknowledgment,
    sanitize_bail_reason, sanitize_manifest_obj, step2_token_mark_eligible, submodule_roots,
    submodule_status_dirty, validate_manifest_paths, warning_bullet,
};
pub use helpers::{
    RecoveryParse, load_digest_map, parse_porcelain_z, rel_under_tmp, resolve_tmpdir_path,
    sha256_file, tmpdir_rel_in_repo, write_bytes_atomic, write_digest_map,
};
pub use identity::{
    BGJOB_RC_KEY, CHECKS_IDENTITY_INTEGRITY_FAILED_ACTION, CHECKS_INPUT_FP_SCHEMA_KEY,
    CHECKS_INPUT_FP_SCHEMA_V1, CHECKS_INPUT_HEAD_SHA_KEY, CHECKS_INPUT_TREE_FP_KEY,
    ChecksIdentityError, ChecksInputIdentity, Classification, WorktreeFacts,
    classify_completed_result, classify_completed_rows, classify_live_seed, compute_identity,
    first_kv_value, identities_match, identity_from_rows, integrity_failure_rows, read_env_rows,
    session_repo_root, validate_repo_root_path,
};
pub use manifest::{
    DispatchState, clear_external_scout_paths, manifest_legacy_fingerprint, path_under_submodule,
};
pub use recovery::{RecoveryPorcelainInputs, compute_recovery_paths};
pub use relevant_checks::{
    ChecksResult, WORKSPACE_INPUTS, coverage_from_markers, is_rust_relevant_path,
    phase_from_markers, scan_checks_log_markers,
};
pub use relevant_checks_digest::build_checks_failure_digest;
pub use self_edit_log::{
    SELF_EDIT_LOG_NAME, SelfEditRecord, digest_paths, file_sha256, normalize_path, read_self_edits,
    record_self_edits, validate_session_tmpdir,
};
pub use step_checks::{
    CHECKS_TERMINAL_ACTIONS, STEP6_CHECKS_STEP, StepChecksSite, checks_step_for_site,
    public_args_for_site, resolve_step_and_budget, resolve_step_name,
};
