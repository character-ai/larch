//! Shared vendor launch ordering, retries, timing, and stall records.
//!
//! This module is adapter parity only. Effects arrive through
//! [`VendorLifecycleHooks`]; executable ownership remains in the shared process
//! port and artifact paths remain caller supplied.

use super::{
    CAP_HIT_PAYLOAD, VendorArgvError, VendorCapCheckResult, VendorDescriptor, VendorLaunchOutcome,
    VendorLaunchRequest, VendorLaunchStatus, VendorProcessResult,
};
use crate::{SafeText, VendorProgram, is_positive_decimal, split_text_lines, truncate_utf8_bytes};
use serde::Serialize;
use std::{
    convert::Infallible,
    error::Error,
    fmt,
    future::{Future, ready},
    pin::Pin,
    task::{Context, Poll, Waker},
    time::Duration,
};

/// Future returned by one injected vendor lifecycle effect.
pub type VendorHookFuture<'a, T, E> = Pin<Box<dyn Future<Output = Result<T, E>> + Send + 'a>>;

/// Opaque configuration lifetime held across argv construction and all hooks.
///
/// An adapter can return its existing Cursor configuration context here. Its
/// destructor runs on success and on every early error.
pub trait VendorConfigurationGuard: Send {}

impl<T: Send> VendorConfigurationGuard for T {}

/// Immutable values supplied to execution, classification, and post hooks.
#[derive(Clone, Copy)]
pub struct VendorLaunchContext<'a> {
    /// Frozen descriptor for the selected family.
    pub descriptor: &'a VendorDescriptor,
    /// Model-resolved launch request.
    pub request: &'a VendorLaunchRequest,
    /// Full argv, including the closed vendor executable name.
    pub argv: &'a [String],
    /// Model extracted from argv, with the request model as fallback.
    pub model: &'a str,
}

/// Ordered post-execution stage selected by the shared lifecycle.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum VendorPostHook {
    /// Mirror quota diagnostics.
    MirrorQuota,
    /// Record launch timing.
    RecordTiming,
    /// Apply family output postprocessing.
    Postprocess,
    /// Record token usage.
    RecordUsage,
    /// Publish completion.
    PromoteCompletion,
}

const POST_HOOKS: [VendorPostHook; 5] = [
    VendorPostHook::MirrorQuota,
    VendorPostHook::RecordTiming,
    VendorPostHook::Postprocess,
    VendorPostHook::RecordUsage,
    VendorPostHook::PromoteCompletion,
];

/// Retry classifiers evaluated for one final attempt result.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct VendorRetryClassification {
    /// Authentication classification, which has priority.
    pub auth: bool,
    /// Transient failure classification.
    pub transient: bool,
    /// Successful-but-empty classification.
    pub empty: bool,
}

/// Injectable effects used by the inactive shared vendor lifecycle.
///
/// Execution is the only required effect; every other hook has a neutral
/// default. Hook failures stop the sequence, so a failed timing, postprocess, or
/// usage hook cannot promote completion.
pub trait VendorLifecycleHooks: Sync {
    /// Adapter-specific failure propagated by the lifecycle.
    type Error: Send;

    /// Run the positive token-cap check.
    ///
    /// The default reports no cap, which is what a launcher with no configured
    /// `token_cap` needs. `run_vendor_launch` skips the call entirely unless the
    /// request carries a positive cap, so the default is never a silent bypass.
    fn check_token_budget_cap<'a>(
        &'a self,
        _request: &'a VendorLaunchRequest,
    ) -> VendorHookFuture<'a, VendorCapCheckResult, Self::Error> {
        Box::pin(ready(Ok(VendorCapCheckResult::default())))
    }

    /// Publish the exact cap-hit carrier before returning.
    fn emit_cap_hit_artifact<'a>(
        &'a self,
        _request: &'a VendorLaunchRequest,
        _cap_check: &'a VendorCapCheckResult,
    ) -> VendorHookFuture<'a, (), Self::Error> {
        Box::pin(ready(Ok(())))
    }

    /// Return false to refuse execution after the cap check.
    fn preflight<'a>(
        &'a self,
        _descriptor: &'a VendorDescriptor,
        _request: &'a VendorLaunchRequest,
    ) -> VendorHookFuture<'a, bool, Self::Error> {
        Box::pin(ready(Ok(true)))
    }

    /// Resolve model-dependent request fields before argv construction.
    fn resolve_model<'a>(
        &'a self,
        request: &'a VendorLaunchRequest,
    ) -> VendorHookFuture<'a, VendorLaunchRequest, Self::Error> {
        Box::pin(ready(Ok(request.clone())))
    }

    /// Enter a family configuration context held through every later hook.
    ///
    /// The default enters no context, matching a launcher that runs the vendor
    /// against the ambient configuration.
    fn enter_configuration<'a>(
        &'a self,
        _descriptor: &'a VendorDescriptor,
        _request: &'a VendorLaunchRequest,
    ) -> VendorHookFuture<'a, Box<dyn VendorConfigurationGuard>, Self::Error> {
        Box::pin(ready(Ok(Box::new(()) as Box<dyn VendorConfigurationGuard>)))
    }

    /// Execute one attempt through the shared process port.
    fn execute<'a>(
        &'a self,
        context: VendorLaunchContext<'a>,
    ) -> VendorHookFuture<'a, VendorProcessResult, Self::Error>;

    /// Classify one result for the three independent retry budgets.
    fn classify_retry(&self, _result: &VendorProcessResult) -> VendorRetryClassification {
        VendorRetryClassification::default()
    }

    /// Wait before one retry. Tests can provide a deterministic clock.
    fn retry_delay(&self, _delay: Duration) -> VendorHookFuture<'_, (), Self::Error> {
        Box::pin(ready(Ok(())))
    }

    /// Run one ordered post stage. Any failure blocks later stages.
    fn post_execution<'a>(
        &'a self,
        _hook: VendorPostHook,
        _context: VendorLaunchContext<'a>,
        _result: &'a VendorProcessResult,
    ) -> VendorHookFuture<'a, (), Self::Error> {
        Box::pin(ready(Ok(())))
    }
}

/// Per-class retry budgets. Counts are retries after the first attempt.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct VendorRetryPolicy {
    /// Authentication retry budget.
    pub max_auth_retries: usize,
    /// Transient retry budget.
    pub max_transient_retries: usize,
    /// Empty-response retry budget.
    pub max_empty_retries: usize,
    /// Delay before each permitted retry.
    pub delay: Duration,
}

/// Failure from argv construction or an injected lifecycle hook.
#[derive(Debug)]
pub enum VendorLaunchError<E> {
    /// The frozen descriptor rejected the profile or request.
    Argv(VendorArgvError),
    /// An injected effect failed.
    Hook(E),
}

impl<E> fmt::Display for VendorLaunchError<E>
where
    E: fmt::Display,
{
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Argv(error) => write!(formatter, "vendor argv construction failed: {error}"),
            Self::Hook(error) => write!(formatter, "vendor lifecycle hook failed: {error}"),
        }
    }
}

impl<E> Error for VendorLaunchError<E>
where
    E: Error + 'static,
{
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::Argv(error) => Some(error),
            Self::Hook(error) => Some(error),
        }
    }
}

/// Run one execution function under the three independent retry budgets.
///
/// Authentication classification takes precedence over transient and empty
/// classification. Exhaustion returns the final process result.
///
/// # Errors
/// Returns the injected execution or delay error.
pub async fn run_with_vendor_retries<H>(
    hooks: &H,
    context: VendorLaunchContext<'_>,
    policy: VendorRetryPolicy,
) -> Result<VendorProcessResult, H::Error>
where
    H: VendorLifecycleHooks + ?Sized,
{
    let mut auth_retries = 0_usize;
    let mut transient_retries = 0_usize;
    let mut empty_retries = 0_usize;
    let mut result = hooks.execute(context).await?;
    loop {
        let classification = hooks.classify_retry(&result);
        if result.exit_code == 0 && !classification.empty {
            return Ok(result);
        }
        let retry = if classification.auth && auth_retries < policy.max_auth_retries {
            auth_retries += 1;
            true
        } else if !classification.auth
            && classification.transient
            && transient_retries < policy.max_transient_retries
        {
            transient_retries += 1;
            true
        } else if !classification.auth
            && classification.empty
            && empty_retries < policy.max_empty_retries
        {
            empty_retries += 1;
            true
        } else {
            false
        };
        if !retry {
            return Ok(result);
        }
        if !policy.delay.is_zero() {
            hooks.retry_delay(policy.delay).await?;
        }
        result = hooks.execute(context).await?;
    }
}

/// Run the shared vendor launch order without selecting a production executor.
///
/// Order is cap check, cap artifact, preflight, model resolution,
/// configuration, argv, retries, quota, timing, postprocess, usage, promotion.
///
/// # Errors
/// Returns argv rejection or the first hook failure.
pub async fn run_vendor_launch<H>(
    descriptor: &VendorDescriptor,
    profile: &str,
    request: &VendorLaunchRequest,
    hooks: &H,
    retry_policy: Option<VendorRetryPolicy>,
) -> Result<VendorLaunchOutcome, VendorLaunchError<H::Error>>
where
    H: VendorLifecycleHooks + ?Sized,
{
    let cap_check = if is_positive_decimal(&request.token_cap) {
        hooks
            .check_token_budget_cap(request)
            .await
            .map_err(VendorLaunchError::Hook)?
    } else {
        VendorCapCheckResult::default()
    };
    if cap_check.hit {
        hooks
            .emit_cap_hit_artifact(request, &cap_check)
            .await
            .map_err(VendorLaunchError::Hook)?;
        return Ok(VendorLaunchOutcome {
            status: VendorLaunchStatus::CapHit,
            process_result: None,
            model: String::new(),
            argv: Vec::new(),
            cap_check: Some(cap_check),
        });
    }
    if !hooks
        .preflight(descriptor, request)
        .await
        .map_err(VendorLaunchError::Hook)?
    {
        return Ok(VendorLaunchOutcome {
            status: VendorLaunchStatus::PreflightRefused,
            process_result: None,
            model: String::new(),
            argv: Vec::new(),
            cap_check: Some(cap_check),
        });
    }
    let working = hooks
        .resolve_model(request)
        .await
        .map_err(VendorLaunchError::Hook)?;
    let _configuration = hooks
        .enter_configuration(descriptor, &working)
        .await
        .map_err(VendorLaunchError::Hook)?;
    let vendor_argv = descriptor
        .build_argv(profile, &working)
        .map_err(VendorLaunchError::Argv)?;
    let argv = vendor_argv.full_argv();
    let extracted_model = descriptor.extract_model(&argv);
    let model = if extracted_model.is_empty() {
        working.model.clone()
    } else {
        extracted_model
    };
    let context = VendorLaunchContext {
        descriptor,
        request: &working,
        argv: &argv,
        model: &model,
    };
    let process_result = match retry_policy {
        Some(policy) => run_with_vendor_retries(hooks, context, policy)
            .await
            .map_err(VendorLaunchError::Hook)?,
        None => hooks
            .execute(context)
            .await
            .map_err(VendorLaunchError::Hook)?,
    };
    for hook in POST_HOOKS {
        hooks
            .post_execution(hook, context, &process_result)
            .await
            .map_err(VendorLaunchError::Hook)?;
    }
    Ok(VendorLaunchOutcome {
        status: VendorLaunchStatus::Completed,
        process_result: Some(process_result),
        model,
        argv,
        cap_check: Some(cap_check),
    })
}

/// Injectable effects for one launch, wired into the shared vendor lifecycle.
///
/// Every effect here is synchronous. The shared lifecycle is `async` so a future
/// vendor family can await real I/O, but a launcher whose own effects are local
/// file work must not stand up a second async runtime around them: the vendor
/// process it drives already owns one. Pair this with [`run_ready_launch`].
pub struct SyncLauncherHooks<'a> {
    /// Refuse the launch before argv construction.
    pub preflight: Option<&'a (dyn Fn() -> bool + Sync)>,
    /// Run the vendor for one built argv.
    execute: &'a (dyn Fn(&[String]) -> VendorProcessResult + Sync),
    /// Mirror vendor quota diagnostics.
    pub mirror_quota: Option<&'a (dyn Fn(&VendorProcessResult) + Sync)>,
    /// Record launch timing.
    pub record_timing: Option<&'a (dyn Fn(&VendorProcessResult) + Sync)>,
    /// Record token usage for the resolved model.
    pub record_usage: Option<&'a (dyn Fn(&str) + Sync)>,
    /// Publish completion.
    pub promote_completion: Option<&'a (dyn Fn(&VendorProcessResult) + Sync)>,
}

impl<'a> SyncLauncherHooks<'a> {
    /// Bind the one required effect: running the vendor for a built argv.
    #[must_use]
    pub fn new(execute: &'a (dyn Fn(&[String]) -> VendorProcessResult + Sync)) -> Self {
        Self {
            preflight: None,
            execute,
            mirror_quota: None,
            record_timing: None,
            record_usage: None,
            promote_completion: None,
        }
    }
}

impl VendorLifecycleHooks for SyncLauncherHooks<'_> {
    type Error = Infallible;

    fn preflight<'a>(
        &'a self,
        _descriptor: &'a VendorDescriptor,
        _request: &'a VendorLaunchRequest,
    ) -> VendorHookFuture<'a, bool, Self::Error> {
        Box::pin(ready(Ok(self.preflight.is_none_or(|hook| hook()))))
    }

    fn execute<'a>(
        &'a self,
        context: VendorLaunchContext<'a>,
    ) -> VendorHookFuture<'a, VendorProcessResult, Self::Error> {
        Box::pin(ready(Ok((self.execute)(context.argv))))
    }

    fn post_execution<'a>(
        &'a self,
        hook: VendorPostHook,
        context: VendorLaunchContext<'a>,
        result: &'a VendorProcessResult,
    ) -> VendorHookFuture<'a, (), Self::Error> {
        match hook {
            VendorPostHook::MirrorQuota => {
                if let Some(effect) = self.mirror_quota {
                    effect(result);
                }
            }
            VendorPostHook::RecordTiming => {
                if let Some(effect) = self.record_timing {
                    effect(result);
                }
            }
            VendorPostHook::RecordUsage => {
                if let Some(effect) = self.record_usage {
                    effect(context.model);
                }
            }
            VendorPostHook::PromoteCompletion => {
                if let Some(effect) = self.promote_completion {
                    effect(result);
                }
            }
            VendorPostHook::Postprocess => {}
        }
        Box::pin(ready(Ok(())))
    }
}

/// Drive an all-synchronous lifecycle future to completion without an executor.
///
/// Every hook above resolves immediately, so one poll finishes the sequence.
/// A future that yielded would mean a hook grew real asynchrony and needs a
/// real executor, which is a change this helper must not paper over.
/// # Errors
/// Returns argv rejection, or a hook that failed to resolve synchronously.
pub fn run_ready_launch(
    descriptor: &'static VendorDescriptor,
    profile: &str,
    request: &VendorLaunchRequest,
    hooks: &SyncLauncherHooks<'_>,
) -> Result<VendorLaunchOutcome, String> {
    let future = run_vendor_launch(descriptor, profile, request, hooks, None);
    let mut future = std::pin::pin!(future);
    let waker = Waker::noop();
    let mut context = Context::from_waker(waker);
    match future.as_mut().poll(&mut context) {
        Poll::Ready(Ok(outcome)) => Ok(outcome),
        Poll::Ready(Err(error)) => Err(error.to_string()),
        Poll::Pending => Err("vendor launch hooks must resolve synchronously".to_owned()),
    }
}

/// Read the process exit code from an outcome, or `refused` when none ran.
#[must_use]
pub fn outcome_exit_code(outcome: &VendorLaunchOutcome, refused: i32) -> i32 {
    outcome
        .process_result
        .as_ref()
        .map_or(refused, |result| result.exit_code)
}

/// Build the exact `cli.py token check-budget` argv.
#[must_use]
pub fn build_check_budget_argv(
    python_executable: &str,
    cli_path: &str,
    cap: &str,
    step: &str,
) -> Vec<String> {
    [
        python_executable,
        cli_path,
        "token",
        "check-budget",
        "--cap",
        cap,
        "--step",
        step,
    ]
    .map(str::to_owned)
    .to_vec()
}

/// Run a positive cap check through an injected command owner.
///
/// Nonnumeric and non-positive caps skip the runner. The first `STATUS` token
/// wins, matching the legacy KV parser.
///
/// # Errors
/// Returns the injected runner error.
pub fn check_token_budget_cap<E>(
    python_executable: &str,
    cli_path: &str,
    cap: &str,
    step: &str,
    runner: impl FnOnce(&[String]) -> Result<VendorProcessResult, E>,
) -> Result<VendorCapCheckResult, E> {
    if !is_positive_decimal(cap) {
        return Ok(VendorCapCheckResult::default());
    }
    let argv = build_check_budget_argv(python_executable, cli_path, cap, step);
    let result = runner(&argv)?;
    let hit = result
        .stdout
        .split_whitespace()
        .find_map(|token| token.strip_prefix("STATUS="))
        == Some("cap_hit");
    Ok(VendorCapCheckResult {
        hit,
        argv,
        stdout: result.stdout,
        payload: if hit {
            CAP_HIT_PAYLOAD.to_owned()
        } else {
            String::new()
        },
    })
}

/// Validated task-kind token used by the vendor timing command.
///
/// Literal constructor calls are checked against the canonical Python
/// allowlist by `timing-task-kind-allowlist`; dynamic values retain the legacy
/// grammar check.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TimingTaskKind(String);

impl TimingTaskKind {
    /// Validate one task kind.
    ///
    /// # Errors
    /// Rejects values outside `[a-z][a-z0-9-]{0,63}`.
    pub fn new(value: impl Into<String>) -> Result<Self, TimingTaskKindError> {
        let value = value.into();
        let mut bytes = value.bytes();
        let valid = value.len() <= 64
            && bytes.next().is_some_and(|byte| byte.is_ascii_lowercase())
            && bytes.all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'-');
        if !valid {
            return Err(TimingTaskKindError);
        }
        Ok(Self(value))
    }

    /// Borrow the validated wire token.
    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

/// A malformed timing task kind.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct TimingTaskKindError;

impl fmt::Display for TimingTaskKindError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("timing task kind must match [a-z][a-z0-9-]{0,63}")
    }
}

impl Error for TimingTaskKindError {}

/// Inputs for the exact `timing record-vendor-task` command.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LaunchTimingRecord {
    /// Closed vendor family.
    pub vendor: VendorProgram,
    /// Mechanically checked task kind.
    pub task_kind: TimingTaskKind,
    /// Integer launch start timestamp.
    pub start_s: i64,
    /// Integer completion timestamp.
    pub end_s: i64,
    /// Launcher output path.
    pub output: String,
    /// Final process exit code.
    pub exit_code: i32,
}

/// Build the exact `timing record-vendor-task` argv and key set.
///
/// The command is Rust-owned, so the argv starts at the verified bootstrap
/// script that remaining Python launchers execute.
#[must_use]
pub fn build_record_launch_timing_argv(
    entrypoint: &str,
    record: &LaunchTimingRecord,
) -> Vec<String> {
    let mut argv = [entrypoint, "timing", "record-vendor-task"]
        .map(str::to_owned)
        .to_vec();
    let status = if record.exit_code == 0 {
        "complete"
    } else {
        "signal"
    };
    argv.extend(
        [
            ("--vendor", record.vendor.executable().to_owned()),
            ("--task-kind", record.task_kind.as_str().to_owned()),
            ("--start-s", record.start_s.to_string()),
            ("--end-s", record.end_s.to_string()),
            ("--output", record.output.clone()),
            ("--exit-code", record.exit_code.to_string()),
            ("--status", status.to_owned()),
        ]
        .into_iter()
        .flat_map(|(flag, value)| [flag.to_owned(), value]),
    );
    argv
}

/// Return the once-per-minute legacy progress message, when due.
#[must_use]
pub fn elapsed_minute_message(
    vendor: VendorProgram,
    elapsed: Duration,
    last_progress_minute: u64,
) -> Option<(u64, String)> {
    let elapsed_minute = elapsed.as_secs() / 60;
    (elapsed_minute >= 1 && elapsed_minute != last_progress_minute).then(|| {
        (
            elapsed_minute,
            format!(
                "⏳ {} agent: still running ({}m elapsed)",
                vendor.executable(),
                elapsed_minute
            ),
        )
    })
}

/// Exact timeout stall payload.
#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct TimeoutStallRecord<'a> {
    /// Vendor label.
    pub tool: &'a str,
    /// Timeout exit code.
    pub exit_code: i32,
    /// Configured timeout seconds.
    pub timeout: u64,
}

/// Render one compact timeout stall JSON object with a trailing newline.
///
/// # Panics
/// Panics only if `serde_json` cannot serialize this fixed scalar record.
#[must_use]
pub fn render_timeout_stall_json(record: &TimeoutStallRecord<'_>) -> String {
    render_json(record, "timeout stall record is serializable")
}

/// Exact detailed Cursor CI stall payload.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CursorStallRecord(serde_json::Value);

impl CursorStallRecord {
    /// Build a redacted pre-SIGTERM record, retaining the final 110 lines.
    #[must_use]
    pub fn new(
        channel: impl Into<String>,
        pid: u32,
        elapsed: Duration,
        git_status: &str,
        transcript: &str,
    ) -> Self {
        let transcript = SafeText::from_untrusted(transcript);
        let mut start = transcript.as_str().len().saturating_sub(16_000);
        while !transcript.as_str().is_char_boundary(start) {
            start += 1;
        }
        let mut lines: Vec<String> = split_text_lines(&transcript.as_str()[start..])
            .into_iter()
            .map(str::to_owned)
            .collect();
        if lines.len() > 110 {
            lines.drain(..lines.len() - 110);
        }
        let git_status = SafeText::from_untrusted(git_status);
        Self(serde_json::json!({
            "tool": "cursor",
            "channel": channel.into(),
            "pid": pid,
            "time_since_last_progress": elapsed.as_secs(),
            "capture_phase": "pre_sigterm",
            "git_state": {
                "status_porcelain": truncate_utf8_bytes(git_status.as_str(), 32_000),
            },
            "last_transcript_lines": lines,
        }))
    }
}

/// Render one detailed Cursor CI stall JSON object with a trailing newline.
///
/// # Panics
/// Panics only if `serde_json` cannot serialize this fixed owned record.
#[must_use]
pub fn render_cursor_stall_json(record: &CursorStallRecord) -> String {
    render_json(&record.0, "Cursor stall record is serializable")
}

fn render_json(record: &impl Serialize, expectation: &'static str) -> String {
    format!("{}\n", serde_json::to_string(record).expect(expectation))
}
