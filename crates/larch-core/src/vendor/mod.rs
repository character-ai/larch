//! Typed vendor descriptors, exact argv builders, and Claude envelope parsing.
//!
//! Adapter parity for issue #8103. No command cutover and no launch lifecycle.

mod argv;
mod auth;
mod check_reviewers;
mod degraded_tools;
mod envelope;
mod external_agent;
mod lifecycle;
mod model_pins;
mod probe_cache;
mod registry;
mod review;
mod session;
mod types;

pub use argv::{
    CodexEnvAuth, VendorArgv, VendorArgvError, VendorArgvErrorKind, build_claude_argv,
    build_codex_argv, build_codex_resume_argv, build_codex_session_argv, build_cursor_argv,
    build_cursor_create_chat_argv, build_cursor_resume_argv, codex_auth_args,
    codex_env_auth_from_key, extract_model_from_argv, trust_config_arg,
};
pub use auth::{
    CURSOR_AUTH_MAX_ATTEMPTS, CURSOR_AUTH_RETRY_DELAY, CURSOR_KEYCHAIN_ACCOUNT,
    CURSOR_KEYCHAIN_SERVICE, CURSOR_PREFLIGHT_AUTH_RC, CursorCredential, HostPlatform,
    NO_OPEN_BROWSER_ON, cursor_child_environment, cursor_keychain_arguments,
    cursor_preflight_failure_message, cursor_preflight_refusal, keychain_credential,
};
pub use check_reviewers::{
    CheckReviewersConfig, CheckReviewersResult, PROBE_TIMEOUT_EXIT_CODE, binary_on_path,
    external_auth_verdict, probe_attempt_rc, resolve_probe_workdir,
};
pub use degraded_tools::{
    CodexGateMessage, DegradedToolsResult, EXTERNAL_TOOL_NAMES, norm_bool, norm_tristate,
    state_phrase, tool_state,
};
pub use envelope::{ClaudeEnvelopeStatus, parse_claude_envelope};
pub use external_agent::{
    CODEX_POLICY_REJECTION_EXCERPT_BYTES, CODEX_POLICY_REJECTION_TAIL_BYTES,
    CodexSessionParseError, ExternalAuthVerdict, codex_policy_rejection_excerpt,
    external_auth_verdict, parse_codex_session_id, sanitize_tool_label, strip_codex_config,
};
pub use lifecycle::{
    CursorStallRecord, LaunchTimingRecord, TimeoutStallRecord, TimingTaskKind, TimingTaskKindError,
    VendorConfigurationGuard, VendorHookFuture, VendorLaunchContext, VendorLaunchError,
    VendorLifecycleHooks, VendorPostHook, VendorRetryClassification, VendorRetryPolicy,
    build_check_budget_argv, build_record_launch_timing_argv, check_token_budget_cap,
    elapsed_minute_message, render_cursor_stall_json, render_timeout_stall_json, run_vendor_launch,
    run_with_vendor_retries,
};
pub use model_pins::{
    CURSOR_MODEL_LIST_ARGV, CURSOR_MODEL_LIST_HEADER, CursorModelListOutcome,
    EXTERNAL_HEALTH_CHECK_TIMEOUT_DEFAULT_SEC, MODEL_PINS_STATUS_LIST_FAILED, MODEL_PINS_STATUS_OK,
    MODEL_PINS_STATUS_SKIPPED, MODEL_PINS_STATUS_UNKNOWN_ID, MODEL_PINS_STATUS_UNPARSEABLE,
    MODEL_PINS_STATUS_UNVERIFIABLE, ModelPinsReport, PinnedModel, VendorModelPinResult,
    codex_pinned_model_declarations, codex_pinned_models, cursor_pinned_model_declarations,
    cursor_pinned_models, list_failed_detail, model_list_timeout_seconds, parse_cursor_model_list,
    resolve_codex_model_pins, resolve_cursor_model_pins_from_list, resolve_model_pins,
};
pub use probe_cache::{
    CODEX_PROBE_GATE_IMMEDIATE_TTL, CodexProbeAttempt, CodexProbeLoop, CursorProbeLoop,
    PROBE_AUTH_RETRY_RC, PROBE_NO_RETRY_RC, PROBE_TRANSIENT_RC, ProbeConclusion, ProbeRetryLimits,
    ProbeStep, ProbeTtl, codex_gate_detail_file_name, codex_probe_identity,
    codex_probe_update_lock_file_name, fresh_probe_verdict, parse_codex_gate_detail,
    probe_cache_user, probe_stamp_contents, probe_stamp_file_name, render_codex_gate_detail,
    transient_probe_retries,
};
pub use registry::{
    CLAUDE_DESCRIPTOR, CODEX_DESCRIPTOR, CURSOR_DESCRIPTOR, REQUIRED_CAPABILITIES,
    VENDOR_DESCRIPTORS, VendorDescriptorError, VendorDescriptorErrorKind, build_vendor_registry,
};
pub use review::{
    COLLECTOR_NS_STRONG_HEADER, CURSOR_DEGRADED_OUTPUT_TOKEN_FLOOR, CURSOR_DEGRADED_RESPONSE,
    CURSOR_DEGRADED_RESULT_BYTES_CEILING, CURSOR_EMPTY_RESPONSE, CURSOR_NO_ISSUES_JSON,
    CURSOR_NO_WORK_INPUT_TOKEN_FLOOR, CURSOR_PREREAD_FAIL_MSG, CURSOR_PREREAD_FAIL_RC,
    CapHitArtifacts, CodexPromptSentinelRead, CodexPromptSidecarArgs, CodexReviewAuthPort,
    CursorPreflightFailure, CursorResultWrite, CursorReviewAuthPort,
    DEFAULT_CURSOR_LAUNCH_JITTER_MS, DirtyBaselineCapturePlan, DirtyTreeBaselinePort,
    ENV_CURSOR_LAUNCH_JITTER_MS, ENV_CURSOR_RETRY_EMPTY_RESULT, ENV_TOKEN_BUDGET_CAP_REVIEW,
    ENV_TRANSIENT_RETRY_DELAY, REVIEW_MAX_TRANSIENT_RETRIES, ResearchOutputValidator,
    RetryArtifactResetPlan, ReviewAuthVerdict, ReviewPreflightRefusal, SpecialistRenderPort,
    StreamResetPlan, codex_compact_sentinel_offset, cursor_has_structured_findings,
    cursor_input_work_tokens, cursor_launch_jitter_ms, cursor_line_no_issues,
    cursor_normalize_no_issues, cursor_output_tokens, cursor_result_is_no_issues,
    effective_review_token_cap, is_cursor_empty_result, plan_capture_cursor_dirty_baseline,
    plan_cursor_result_write, plan_retry_artifact_reset, plan_stream_reset,
    read_codex_prompt_sentinel, render_cap_hit_artifacts, render_clean_readonly_dirty_tree,
    render_codex_prompt_sidecar, render_cursor_degraded_diag, render_cursor_empty_response,
    render_cursor_no_work_diag, render_preflight_bundle, render_unknown_dirty_tree,
    resolve_codex_review_model, review_retry_delay_secs, run_codex_review_preflight,
    run_cursor_review_preflight, write_cursor_dirty_tree_from_baseline,
};
pub use session::{
    VendorSessionError, VendorSessionErrorKind, VendorSessionHandle, VendorSessionVendor,
};
pub use types::{
    CAP_HIT_PAYLOAD, VendorCapCheckResult, VendorDescriptor, VendorFamilyHooks,
    VendorLaunchOutcome, VendorLaunchRequest, VendorLaunchStatus, VendorParsedResult,
    VendorProcessResult,
};
