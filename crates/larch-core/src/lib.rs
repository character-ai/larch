//! Domain types, use cases, and effect-free service ports for larch.

mod attestation;
mod bgjob;
mod ci_timing;
mod config;
mod context;
mod env_file;
mod error;
mod git;
mod github;
mod github_actions;
mod github_auth;
mod logging_util;
mod object_store;
mod outcome;
mod process;
mod process_identity;
mod progress;
mod redaction;
mod report;
mod retry;
mod review_dispatch;
mod run_log;
mod session_env;
mod session_state;
mod storage;
mod telemetry;
mod test_shards;
mod text;
mod time;
mod upgrade_larch;
mod vendor;
mod vendor_diagnostics;
mod vendor_failure;
mod vendor_usage;

pub use attestation::{
    ArtifactAttestationRequest, AttestationInputError, AttestationInputErrorKind,
    ImmutableReleaseAttestationRequest, ReleaseAssetSubject, ReleaseSourceCommit, ReleaseTag,
    VerifiedArtifactAttestation, VerifiedReleaseAttestation,
};
pub use bgjob::{
    BGJOB_ELAPSED_KEY, BGJOB_INPUT_FP_SUFFIX, BGJOB_RC_KEY, BGJOB_REGISTRY_DIRNAME,
    BGJOB_RESULT_ENV_SUFFIX, BGJOB_STARTUP_ENV_SUFFIX, BGJOB_STATUS_DONE, BGJOB_STATUS_KEY,
    BGJOB_STATUS_STARTED, BGJOB_TMP_SUBDIR, BgjobError, ENV_BGJOB_REGISTRY_ROOT, JobSpec,
    LivenessVerdict, OwnerIdentity, RegistryEntry, ResultEnvRows, WaitResult, bgjob_dir,
    checked_dir, child_liveness, daemon_liveness, default_run_id, ensure_under, entry_expired,
    has_live_entry, iter_entries, log_paths, private_atomic_write, read_entry, read_for,
    registry_path, registry_root, reject_line_value, result_env_path, startup_env_path,
    unlink_entry, validate_initial_merge_rows, validate_merge_result_env, validate_run_id,
    validate_slug, write_entry, write_entry_at,
};
pub use ci_timing::{
    CiTimingRunSelection, HarnessTimingReport, HarnessTimingRow, JobTimingReport, JobTimingRow,
    MAX_CI_TIMING_REQUIRED_TARGETS, MAX_CI_TIMING_RUNS, NodeidTiming, PytestTimingReport,
    PytestTimingRow, ShardTiming, TargetTiming, collect_harness_timing, collect_job_timing,
    collect_pytest_timing,
};
pub use config::{GIT_COMMIT_CO_AUTHORED_BY_TRAILER, env};
pub use context::{RunId, RunIdError, RunIdErrorKind, RuntimeContext};
pub use env_file::{
    CommentPolicy, CrStrip, DuplicateInputPolicy, DuplicatePolicy, EmptyKeyPolicy, EnvFile,
    KeyPolicy, KvDocument, KvError, KvErrorKind, KvRow, MalformedLinePolicy, ParseOptions,
    RenderOptions, WhitespacePolicy, kv_text, parse_allowlisted_env_line, select_kv_bytes,
};
pub use error::{
    EnvironmentalFailure, ErrorCategory, FailureKind, InternalDefect, LarchError, OperatorError,
};
pub use git::{
    Change, ChangeKind, ChangeSet, Commit, ConfigKey, ConfigScope, ConfigValue, ConflictKind,
    ConflictStage, GitMode, GitPath, Head, IgnoreKind, IgnoredEntry, IndexFlags, Object,
    ObjectHash, ObjectId, ObjectKind, RefFormat, RefName, Reference, ReferenceKind,
    ReferenceTarget, Remote, RepositoryError, RepositoryErrorKind, RepositoryLocation,
    RepositoryRead, RepositoryStatus, Revision, StatusOptions, TrackedEntry, UnmergedEntry,
    Upstream, Worktree,
};
pub use github::{
    ASSET_MEDIA_TYPE, AssetDigest, AssetStreamGuard, CheckBucket, CheckRun, GitHubActionsError,
    GitHubActionsErrorKind, GitHubActionsFuture, GitHubActionsService, GitHubCloseReason,
    GitHubComment, GitHubFailureInput, GitHubFuture, GitHubIssue, GitHubIssueCreate,
    GitHubIssueEdit, GitHubIssueList, GitHubIssueSearch, GitHubIssueState, GitHubLabel,
    GitHubLabelCreate, GitHubMutationOutcome, GitHubOperationError, GitHubOperationErrorKind,
    GitHubRateLimitInputs, GitHubRepository, GitHubRepositoryRef, GitHubRequestKind,
    GitHubResponseLimits, GitHubRetryAction, GitHubService, GitHubTransportPolicy,
    ReconciledMutation, ReleaseDataError, ReleaseDataErrorKind, ReleaseState, RemoteAsset,
    TagObjectId, WorkflowDispatchRequest, WorkflowJob, WorkflowLogArchive, WorkflowRun,
    WorkflowRunFilters, classify_github_retry, reconcile_mutation, require_asset_content_type,
    resolve_tag_object_id, select_release_for_staging, select_release_for_tag,
};
pub use github_actions::{RunLogsOutput, run_logs, run_logs_setup_failure, workflow_path};
pub use github_auth::{GitHubToken, GitHubTokenError, GitHubTokenErrorKind, acquire_github_token};
pub use logging_util::emit_kv;
pub use object_store::{
    ObjectPage, ObjectStore, ObjectStoreError, ObjectStoreFuture, RemoteObject,
};
pub use outcome::{ExitCode, WorkflowOutcome};
pub use process::{
    ChildEnvironment, ExternalProcessRunner, ExternalProgram, GitCliOperation, GitHubCliOperation,
    HostUtilityProgram, LarchProgram, ProcessCancellation, ProcessError, ProcessErrorKind,
    ProcessEvent, ProcessEventKind, ProcessFuture, ProcessObserver, ProcessOutput, ProcessRequest,
    ProcessRequestError, ProcessRequestErrorKind, ProcessStatus, PythonVerbProgram, ScannerProgram,
    VendorProgram,
};
pub use process_identity::{
    COMMAND_LOG_LIMIT, DESIGN_STEP3_KILL_LOG_FILE, DESIGN_STEP3_LOOP_IDENTITY_FILE,
    DESIGN_STEP3_MISSING_PID_GRACE, DESIGN_STEP3_WRAPPER_DETACHED_FILE, FINALIZE_KILL_LOG_FILE,
    IMPLEMENT_STEP5_KILL_LOG_FILE, IMPLEMENT_STEP5_LOOP_IDENTITY_FILE,
    IMPLEMENT_STEP5_WRAPPER_DETACHED_FILE, IdentityProbeOutput, KillLogEvent, KillTargetSnapshot,
    PROCESS_IDENTITY_CAPTURE_ATTEMPTS, PROCESS_IDENTITY_CAPTURE_SLEEP, PROCESS_IDENTITY_PS_TIMEOUT,
    PS_LSTART_FIELD_COUNT, ProcessIdentityHost, ProcessIdentityProbeResult,
    RecordedProcessIdentity, TERMINATE_ESCALATION_SLEEP, TerminateSignal, ValidationResult,
    append_kill_log, await_loop_identity, await_loop_poll, bounded_command, collect_descendants,
    collect_process_group_members, identity_to_json, kill_session_background_processes,
    normalize_command_signature, parse_ps_identity, probe_process_identity, read_identity_record,
    read_process_identity, read_stable_process_identity, result_env_has_step3_status,
    teardown_loop_identity, terminate_validated_process_group, validate_process_identity,
    write_identity_record, write_loop_identity, write_step5_loop_identity,
};
pub use progress::{
    CURRENT_RUN_FILENAME, CURRENT_RUN_LOCK_FILENAME, DEFAULT_HIDE_AFTER_S, DEFAULT_STALE_AFTER_S,
    MAX_STATUSLINE_LINES, PROGRESS_DIRNAME, RESET_SESSION_SOURCES, RUN_BREADCRUMB_FILENAME,
    STATUSLINE_COMMAND_MARKER, STATUSLINE_DISABLE_ENV, STATUSLINE_LOCAL_SETTINGS,
    STATUSLINE_VERB_MARKER, StalenessDecision, apply_statusline, breadcrumb_line,
    chained_user_command, classify_staleness, install_payload_directory, is_breadcrumb_row,
    is_larch_statusline_command, positive_int, progress_clone_digest, progress_run_id_error,
    render_statusline_body, resets_active_run, settings_statusline_command, shell_quote,
    stale_suffix, statusline_launcher_text, statusline_payload_directory, truncate_columns,
    validate_progress_run_id,
};
pub use redaction::{RedactionResult, RuntimeRedactor, SafeText, redact, redact_sensitive_paths};
pub use report::{
    BlockMarkers, BlockMarkersError, BlockMarkersErrorKind, EMPTY_GROUPS, IssueDetail,
    IssueDetailGroups, IssueEvent, LoadResult, MAX_DEDUPE_KEY_LEN, MAX_DISPLAY_LEN,
    RunLogBatchArtifact, RunLogBatchMode, RunLogBatchSanitizer, RunLogBatchSpec, RunLogCorpus,
    RunLogCorpusEvent, RunLogCorpusIter, RunLogCorpusWarning, RunLogCorpusWarningKind,
    RunLogFileIter, RunLogManifest, RunLogRoundSort, RunLogRun, RunLogSelection, RunLogTimeWindow,
    RunLogTimeWindowError, WARN_CATEGORY, build_issue_detail_section, count_issue_groups,
    count_load_result, execution_issue_identity, load_issue_detail_groups,
    parse_markdown_execution_issues, parse_preterminal_outcome_label, render_issue_detail_block,
    replace_markdown_block, replace_markdown_block_with_warn, round_number_from_path,
    run_log_batch_spec, run_log_batch_specs, structured_body_dedupe_keys,
};
pub use retry::{
    AttemptOutcome, DeterministicJitter, Jitter, RetryClass, RetryDecision, RetryObservation,
    RetryPolicy, RetryPolicyError, StopReason,
};
pub use review_dispatch::{
    DiffMode, GENERATORS_TSV_COLUMNS, GeneratorsTsvError, ReviewerWaitConfig, ReviewerWaitHost,
    ReviewerWaitResult, ReviewerWaitRow, SUSPEND_REFUND_SECONDS,
    WAIT_DEFAULT_POLL_INTERVAL_SECONDS, WAIT_DEFAULT_TIMEOUT_SECONDS, classify_diff,
    parse_generated_paths, wait_for_reviewers, wait_max_polls,
};
pub use run_log::{
    BatchName, ExecutionIssueEntry, ExecutionIssueFormat, ExecutionIssueLedger,
    ExecutionIssueReadError, ExecutionIssueReadErrorKind, ManifestDocument, ManifestFormatVersion,
    ManifestReadError, ManifestReadErrorKind, ManifestRecord, ManifestUpdate, ManifestV2Seed,
    ManifestWriteError, RoundNumber, RoundNumberError, RunLogLayout, RunLogSlug, RunLogSlugError,
    RunLogSlugErrorKind, final_summary_terminal_heading, first_nonempty_line,
    manifest_pr_evidence_matches, stale_bail_heading_with_pr_evidence, terminal_bail_skip_signal,
    validate_run_log_slug,
};
pub use session_env::{
    DIFFICULTY_CHOICES, MAX_PATH_VALUE_LEN, RESTORE_FINALIZE_KEYS, RUN_FLAG_KEYS, RunParams,
    WRITE_DESIGN_ENV_KEYS, WRITE_ENV_KEYS, design_run_launcher_text, export_line, external_timeout,
    implement_run_launcher_text, is_bool, is_strict_run_id, is_valid_claude_pid,
    is_valid_plugin_root_value, is_valid_repo_value, is_valid_run_id, is_valid_session_id,
    parse_bool_arg, plugin_root_env_text, posix_path_display, restore_finalize_default,
    run_params_json, validate_no_newlines, validate_path_arg_value, validate_repo_root_value,
    validate_writer_keys,
};
pub use session_state::{
    IMPLEMENT_SENTINEL_RELATIVE_PATHS, IMPLEMENT_TMPDIR_PREFIX, IMPLEMENT_TMPDIR_TTL_SECONDS,
    allowed_session_roots, cleanup_cache_sessions_root, design_tmpdir_syntax_error,
    implement_session_roots, implement_tmpdir_ttl, prefers_implement_candidate,
};
pub use storage::{
    ENV_LARCH_LOGS_URI, ENV_LARCH_R2_ACCOUNT_ID, ENV_LARCH_R2_ENDPOINT, ENV_LARCH_STORAGE_BASE_URI,
    LARCH_TOOL_NAME, LOCAL_NAMESPACE_DOMAIN, RUN_LOGS_DATA_TYPE, RunLogStorageMode,
    RunLogStorageReason, RunLogStorageResolution, STORAGE_BASE_URI_FIELD, STORAGE_CONFIG_RELPATH,
    STORAGE_URI_SCHEMES, StorageBase, StorageConfigurationError, StoragePreflightError,
    ToolRepositoryStorage, format_preflight_stdout, injected_storage_resolution,
    local_namespace_id, parse_storage_base_uri, parse_tool_repository_uri,
    repository_leaf_from_remote, require_enabled_storage, resolve_run_log_storage,
    validate_client_repo,
};
pub use telemetry::{Breadcrumb, JournalRecord, RecordError, RecordErrorKind};
pub use test_shards::{
    TestShardMap, TestShardTiming, pack_test_shards, read_makefile_shards, rewrite_makefile_shards,
};
pub use text::{split_text_lines, tail_lines, truncate_utf8_bytes};
pub use time::{AsyncClock, BusinessClock, Deadline, MonotonicClock, MonotonicTime, Sleep};
pub use upgrade_larch::{
    ActiveRootState, InstalledVersionState, MarketplaceState, UpgradeDisposition,
    classify as classify_upgrade,
};
pub use vendor::{
    CAP_HIT_PAYLOAD, CLAUDE_DESCRIPTOR, CODEX_DESCRIPTOR, CODEX_PROBE_GATE_IMMEDIATE_TTL,
    COLLECTOR_NS_STRONG_HEADER, CURSOR_AUTH_MAX_ATTEMPTS, CURSOR_AUTH_RETRY_DELAY,
    CURSOR_DEGRADED_OUTPUT_TOKEN_FLOOR, CURSOR_DEGRADED_RESPONSE,
    CURSOR_DEGRADED_RESULT_BYTES_CEILING, CURSOR_DESCRIPTOR, CURSOR_EMPTY_RESPONSE,
    CURSOR_KEYCHAIN_ACCOUNT, CURSOR_KEYCHAIN_SERVICE, CURSOR_NO_ISSUES_JSON,
    CURSOR_NO_WORK_INPUT_TOKEN_FLOOR, CURSOR_PREFLIGHT_AUTH_RC, CURSOR_PREREAD_FAIL_MSG,
    CURSOR_PREREAD_FAIL_RC, CapHitArtifacts, ClaudeEnvelopeStatus, CodexEnvAuth, CodexProbeAttempt,
    CodexProbeLoop, CodexPromptSentinelRead, CodexPromptSidecarArgs, CodexReviewAuthPort,
    CursorCredential, CursorPreflightFailure, CursorProbeLoop, CursorResultWrite,
    CursorReviewAuthPort, CursorStallRecord, DEFAULT_CURSOR_LAUNCH_JITTER_MS,
    DirtyBaselineCapturePlan, DirtyTreeBaselinePort, ENV_CURSOR_LAUNCH_JITTER_MS,
    ENV_CURSOR_RETRY_EMPTY_RESULT, ENV_TOKEN_BUDGET_CAP_REVIEW, ENV_TRANSIENT_RETRY_DELAY,
    HostPlatform, LaunchTimingRecord, NO_OPEN_BROWSER_ON, PROBE_AUTH_RETRY_RC, PROBE_NO_RETRY_RC,
    PROBE_TRANSIENT_RC, ProbeConclusion, ProbeRetryLimits, ProbeStep, ProbeTtl,
    REQUIRED_CAPABILITIES, REVIEW_MAX_TRANSIENT_RETRIES, ResearchOutputValidator,
    RetryArtifactResetPlan, ReviewAuthVerdict, ReviewPreflightRefusal, SpecialistRenderPort,
    StreamResetPlan, TimeoutStallRecord, TimingTaskKind, TimingTaskKindError, VENDOR_DESCRIPTORS,
    VendorArgv, VendorArgvError, VendorArgvErrorKind, VendorCapCheckResult,
    VendorConfigurationGuard, VendorDescriptor, VendorDescriptorError, VendorDescriptorErrorKind,
    VendorFamilyHooks, VendorHookFuture, VendorLaunchContext, VendorLaunchError,
    VendorLaunchOutcome, VendorLaunchRequest, VendorLaunchStatus, VendorLifecycleHooks,
    VendorParsedResult, VendorPostHook, VendorProcessResult, VendorRetryClassification,
    VendorRetryPolicy, VendorSessionError, VendorSessionErrorKind, VendorSessionHandle,
    VendorSessionVendor, build_check_budget_argv, build_claude_argv, build_codex_argv,
    build_codex_resume_argv, build_codex_session_argv, build_cursor_argv,
    build_cursor_create_chat_argv, build_cursor_resume_argv, build_record_launch_timing_argv,
    build_vendor_registry, check_token_budget_cap, codex_auth_args, codex_compact_sentinel_offset,
    codex_env_auth_from_key, codex_gate_detail_file_name, codex_probe_identity,
    codex_probe_update_lock_file_name, cursor_child_environment, cursor_has_structured_findings,
    cursor_input_work_tokens, cursor_keychain_arguments, cursor_launch_jitter_ms,
    cursor_line_no_issues, cursor_normalize_no_issues, cursor_output_tokens,
    cursor_preflight_failure_message, cursor_preflight_refusal, cursor_result_is_no_issues,
    effective_review_token_cap, elapsed_minute_message, extract_model_from_argv,
    fresh_probe_verdict, is_cursor_empty_result, keychain_credential, parse_claude_envelope,
    parse_codex_gate_detail, plan_capture_cursor_dirty_baseline, plan_cursor_result_write,
    plan_retry_artifact_reset, plan_stream_reset, probe_cache_user, probe_stamp_contents,
    probe_stamp_file_name, read_codex_prompt_sentinel, render_cap_hit_artifacts,
    render_clean_readonly_dirty_tree, render_codex_gate_detail, render_codex_prompt_sidecar,
    render_cursor_degraded_diag, render_cursor_empty_response, render_cursor_no_work_diag,
    render_cursor_stall_json, render_preflight_bundle, render_timeout_stall_json,
    render_unknown_dirty_tree, resolve_codex_review_model, review_retry_delay_secs,
    run_codex_review_preflight, run_cursor_review_preflight, run_vendor_launch,
    run_with_vendor_retries, transient_probe_retries, trust_config_arg,
    write_cursor_dirty_tree_from_baseline,
};
pub use vendor_diagnostics::{
    FAILED_AGENT_STDERR_TAIL_BYTE_CAP, FAILED_AGENT_STDERR_TAIL_LINES, FailureDiagSource,
    FailureDiagWrite, LauncherArtifactKind, LauncherArtifactPaths, StderrCaptureMode,
    VENDOR_FAILURE_DIAG_BYTE_CAP, VENDOR_FAILURE_DIAG_SECTION_LINES, compose_failure_diag,
    failed_agent_stderr_candidates, failure_diag_section_body, failure_diag_source_order,
    plan_failure_diag_write, render_failed_agent_stderr_tail, stream_reset_history_entry,
};
pub use vendor_failure::{
    AuthVerdict, CodexGateDetail, CodexGateSignal, FailureClass, FailureReason, LaunchFailure,
    LaunchFailureInputs, LauncherArtifact, LauncherExitArtifacts, classify_launch_failure,
    detect_codex_cli_gate, effective_failure_class, is_quota_failure, is_transient_infra_failure,
    parse_launcher_exit_text, parse_launcher_failure_class, resolve_launcher_exit,
};
pub use vendor_usage::{UsageParseError, UsageTotals, json_usage_number, parse_codex_usage};

/// Immutable metadata about the running larch build.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct BuildMetadata {
    version: &'static str,
    target: &'static str,
}

impl BuildMetadata {
    /// Create metadata for a compile-time version.
    #[must_use]
    pub const fn new(version: &'static str, target: &'static str) -> Self {
        Self { version, target }
    }

    /// Return the build version.
    #[must_use]
    pub const fn version(self) -> &'static str {
        self.version
    }

    /// Return the compilation target triple.
    #[must_use]
    pub const fn target(self) -> &'static str {
        self.target
    }
}

/// Render the machine-readable identity checked by the installation shim.
#[must_use]
pub fn bootstrap_self_check(metadata: BuildMetadata) -> String {
    format!(
        "{{\"schema_version\":1,\"version\":\"{}\",\"target\":\"{}\"}}",
        metadata.version(),
        metadata.target()
    )
}

/// Non-production use cases that prove command dispatch and library wiring.
pub mod example {
    /// Return a caller-owned message unchanged.
    #[must_use]
    pub const fn echo(message: &str) -> &str {
        message
    }
}

#[cfg(test)]
mod tests {
    use super::{BuildMetadata, bootstrap_self_check, example};

    #[test]
    fn build_metadata_preserves_the_version() {
        let metadata = BuildMetadata::new("1.2.3", "aarch64-apple-darwin");

        assert_eq!(metadata.version(), "1.2.3");
        assert_eq!(metadata.target(), "aarch64-apple-darwin");
    }

    #[test]
    fn bootstrap_self_check_is_compact_machine_readable_json() {
        let metadata = BuildMetadata::new("1.2.3", "x86_64-unknown-linux-gnu");

        assert_eq!(
            bootstrap_self_check(metadata),
            r#"{"schema_version":1,"version":"1.2.3","target":"x86_64-unknown-linux-gnu"}"#
        );
    }

    #[test]
    fn example_echo_preserves_the_message() {
        assert_eq!(example::echo("library wiring"), "library wiring");
    }
}
