//! Typed vendor descriptors, exact argv builders, and Claude envelope parsing.
//!
//! Adapter parity for issue #8103. No command cutover and no launch lifecycle.

mod argv;
mod envelope;
mod lifecycle;
mod registry;
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
pub use session::{
    VendorSessionError, VendorSessionErrorKind, VendorSessionHandle, VendorSessionVendor,
};
pub use types::{
    CAP_HIT_PAYLOAD, VendorCapCheckResult, VendorDescriptor, VendorFamilyHooks,
    VendorLaunchOutcome, VendorLaunchRequest, VendorLaunchStatus, VendorParsedResult,
    VendorProcessResult,
};
