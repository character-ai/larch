//! Typed vendor descriptors, exact argv builders, and Claude envelope parsing.
//!
//! Adapter parity for issue #8103. No command cutover and no launch lifecycle.

mod argv;
mod envelope;
mod lifecycle;
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
pub use envelope::{ClaudeEnvelopeStatus, parse_claude_envelope};
pub use lifecycle::{
    CursorStallRecord, LaunchTimingRecord, TimeoutStallRecord, TimingTaskKind, TimingTaskKindError,
    VendorConfigurationGuard, VendorHookFuture, VendorLaunchContext, VendorLaunchError,
    VendorLifecycleHooks, VendorPostHook, VendorRetryClassification, VendorRetryPolicy,
    build_check_budget_argv, build_record_launch_timing_argv, check_token_budget_cap,
    elapsed_minute_message, render_cursor_stall_json, render_timeout_stall_json, run_vendor_launch,
    run_with_vendor_retries,
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
