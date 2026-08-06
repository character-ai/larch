//! One in-process owner for running an approved vendor executable.
//!
//! Every larch launcher — the `agent run-external-agent` command, the drafter
//! launchers, and the Codex exec launcher — publishes the same launcher
//! artifact family: a `.meta` record, a `.diag` capture, a completion sentinel,
//! and a bounded stderr tail plus failure diagnostic on failure. This module is
//! the sole owner of that behavior so no launcher re-derives it.

use std::{
    env,
    ffi::OsString,
    fmt::Write as _,
    fs,
    io::{Read as _, Seek as _, SeekFrom},
    num::NonZeroUsize,
    path::{Path, PathBuf},
    sync::Arc,
    time::Duration,
};

use larch_adapters::{
    ConfinedPath, NoopProcessObserver, PathIntent, ProcessFileRouting, ProcessStdinRouting,
    TemporaryRoot, TokioProcessRunner, atomic_write_utf8_in, ensure_directory_chain,
    read_optional_utf8_lossy, remove_optional_file,
    runtime::{Cancellation, LarchRuntime},
    vendor_auth::{CursorPreflightConfig, VendorAuthContext, cursor_auth_preflight},
    vendor_diagnostics::{
        select_failed_agent_stderr_source, write_failed_agent_stderr_tail, write_failure_diag,
    },
    vendor_lifecycle::{
        StartupLockConfig, external_startup_lock_acquire, external_startup_lock_release_after,
    },
};
use larch_core::{
    ChildEnvironment, CursorCredential, ExternalAuthVerdict, ExternalProgram, LauncherArtifactKind,
    LauncherArtifactPaths, ProcessError, ProcessErrorKind, ReviewAuthVerdict, StderrCaptureMode,
    VendorProgram, codex_policy_rejection_excerpt, cursor_child_environment, env as env_names,
    external_auth_verdict, sanitize_tool_label,
};

/// Bounded in-memory capture used only for the process port's own accounting.
const OUTPUT_LIMIT: usize = 64 * 1024;
/// Grace period before a deadline-exceeded vendor process group is killed.
const SHUTDOWN_GRACE: Duration = Duration::from_secs(5);
/// Startup-lock carrier shared with every remaining Python vendor caller.
const SHARED_STARTUP_LOCK_ROOT: &str = "/tmp";
/// Default authentication-retry budget for the retrying launcher.
const DEFAULT_AUTH_RETRIES: usize = 5;
/// Environment override for the authentication-retry budget.
const AUTH_RETRIES_ENV: &str = "LARCH_EXTERNAL_AUTH_RETRIES";

/// Where the launched vendor's standard streams are routed.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ExternalAgentRouting {
    /// Both streams land in the output file.
    CaptureCombined,
    /// Standard output lands in the output file; standard error in the diag file.
    CaptureStdoutOnly,
    /// Explicit stream files. An unset stream stays attached to this process.
    Streams {
        /// Destination for the vendor's standard output.
        stdout: Option<PathBuf>,
        /// Destination for the vendor's standard error.
        stderr: Option<PathBuf>,
    },
}

impl ExternalAgentRouting {
    const fn capture_stdout(&self) -> bool {
        matches!(self, Self::CaptureCombined)
    }

    const fn capture_stdout_only(&self) -> bool {
        matches!(self, Self::CaptureStdoutOnly)
    }

    const fn stderr_mode(&self) -> StderrCaptureMode {
        match self {
            Self::CaptureCombined => StderrCaptureMode::Combined,
            Self::CaptureStdoutOnly => StderrCaptureMode::StdoutOnly,
            Self::Streams { .. } => StderrCaptureMode::Separate,
        }
    }

    fn stream_paths(&self) -> Vec<PathBuf> {
        match self {
            Self::CaptureCombined | Self::CaptureStdoutOnly => Vec::new(),
            Self::Streams { stdout, stderr } => stdout
                .iter()
                .chain(stderr.iter())
                .map(PathBuf::clone)
                .collect(),
        }
    }
}

/// One vendor launch and the artifact family it publishes.
#[derive(Clone, Debug)]
pub struct ExternalAgentLaunch {
    /// Launcher tool label recorded in `.meta` and progress lines.
    pub tool: String,
    /// Launcher output path exactly as the caller supplied it.
    pub output: String,
    /// Deadline in seconds.
    pub timeout_seconds: u64,
    /// Full argv including the approved vendor executable at index zero.
    pub command: Vec<String>,
    /// Closed vendor program selected from the command.
    pub program: VendorProgram,
    /// Stream routing.
    pub routing: ExternalAgentRouting,
    /// Additional stderr candidate consulted when composing diagnostics.
    pub stderr_sink: Option<PathBuf>,
    /// Working directory; defaults to the current directory when unset.
    pub working_directory: Option<PathBuf>,
    /// Typed child-environment overrides layered on the vendor defaults.
    pub environment: Vec<(ChildEnvironment, OsString)>,
    /// Completion-sentinel suffix (`.done` or `.inner.done`).
    pub sentinel_suffix: &'static str,
    /// Interval between policy-watch samples while the vendor runs.
    pub poll_interval: Duration,
    /// Confined file supplying the child's standard input, when the vendor
    /// consumes its prompt from a stream rather than argv.
    pub stdin: Option<ConfinedPath>,
}

/// Terminal result of one launch.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ExternalAgentOutcome {
    /// Launcher exit code written to the completion sentinel.
    pub exit_code: i32,
}

/// Files the launcher owns for one launch.
pub struct PreparedExternalAgentFiles {
    root: TemporaryRoot,
    paths: LauncherArtifactPaths,
    output_file: ConfinedPath,
    diag_file: ConfinedPath,
    diag: PathBuf,
    done: PathBuf,
    stdout_file: Option<ConfinedPath>,
    stderr_file: Option<ConfinedPath>,
}

/// Run one vendor launch and publish its completion sentinel.
///
/// # Errors
/// Returns when the launcher artifact family cannot be prepared or published.
pub fn run_external_agent_launch(
    launch: &ExternalAgentLaunch,
) -> Result<ExternalAgentOutcome, String> {
    let prepared = prepare_external_agent_files(launch)?;
    let exit_code = run_prepared_external_agent(launch, &prepared);
    write_done_sentinel(&prepared, exit_code)?;
    Ok(ExternalAgentOutcome { exit_code })
}

/// One vendor run that publishes no launcher artifacts.
pub struct BareVendorRun<'a> {
    /// Closed vendor program selected from the command.
    pub program: VendorProgram,
    /// Full argv including the approved vendor executable at index zero.
    pub argv: &'a [String],
    /// Working directory for the vendor.
    pub working_directory: &'a Path,
    /// Typed child-environment overrides layered on the vendor defaults.
    pub environment: Vec<(ChildEnvironment, OsString)>,
    /// Confined file supplying the child's standard input, when it reads one.
    pub stdin: Option<ConfinedPath>,
    /// Confined destination for the vendor's standard output.
    pub stdout: Option<ConfinedPath>,
    /// Confined destination for the vendor's standard error.
    pub stderr: Option<ConfinedPath>,
    /// Deadline in seconds.
    pub timeout_seconds: u64,
}

/// Run one vendor through the approved process layer without publishing artifacts.
///
/// This is the whole surface a caller needs when it owns its own output files,
/// such as the reviewer negotiation round. Failure to spawn returns the same
/// exit codes the artifact-publishing launcher reports, and the caller decides
/// where to record the diagnostic.
///
/// # Errors
/// Returns a readable spawn or runtime failure with its exit code.
pub fn run_bare_vendor(run: &BareVendorRun<'_>) -> Result<i32, (i32, String)> {
    let runtime = LarchRuntime::current_thread()
        .map_err(|_error| (127, "could not start the local runtime".to_owned()))?;
    let output_limit = NonZeroUsize::new(OUTPUT_LIMIT).unwrap_or(NonZeroUsize::MIN);
    let mut request = larch_core::ProcessRequest::new(
        ExternalProgram::Vendor(run.program),
        run.argv.iter().skip(1).cloned(),
        run.working_directory.to_path_buf(),
        Duration::from_secs(run.timeout_seconds),
        SHUTDOWN_GRACE,
        output_limit,
    )
    .map(|request| request.with_environment_for_vendor(run.program))
    .map_err(|error| (127, error.to_string()))?;
    for (key, value) in &run.environment {
        request = request.with_environment(*key, value.clone());
    }
    let routing = ProcessFileRouting::streams(run.stdout.clone(), run.stderr.clone()).with_stdin(
        run.stdin
            .clone()
            .map_or(ProcessStdinRouting::Null, ProcessStdinRouting::File),
    );
    let runner = TokioProcessRunner::new(Arc::new(NoopProcessObserver));
    let cancellation = Cancellation::new();
    match runtime.block_on(runner.run_with_files(request, &cancellation, routing)) {
        Ok(output) => Ok(output.status().code().unwrap_or(1)),
        Err(error) if error.kind() == ProcessErrorKind::TimedOut => Ok(124),
        Err(error) => Err((spawn_error_exit_code(&error), error.message().to_owned())),
    }
}

/// Hold the shared vendor startup lock across one caller-owned launch.
#[must_use]
pub fn hold_vendor_startup_lock(
    program: VendorProgram,
) -> Option<larch_adapters::vendor_lifecycle::StartupLockRelease> {
    hold_startup_lock(program)
}

/// Run one vendor launch under the shared startup lock and authentication retries.
///
/// Authentication signatures in the launch diagnostics retry up to the
/// configured budget. A first empty, unclassified failure retries exactly once,
/// which covers a vendor that dies during startup without a readable reason.
///
/// # Errors
/// Returns the first launch-preparation or sentinel-publication failure.
pub fn run_external_agent_with_auth_retries(
    launch: &ExternalAgentLaunch,
) -> Result<ExternalAgentOutcome, String> {
    let max_auth = auth_retry_limit();
    let mut auth_attempt = 1_usize;
    let mut retried_unclassified_empty = false;
    loop {
        let _release = hold_startup_lock(launch.program);
        let outcome = run_external_agent_launch(launch)?;
        if outcome.exit_code == 0 {
            return Ok(outcome);
        }
        let paths = LauncherArtifactPaths::new(PathBuf::from(&launch.output));
        if policy_rejection_marker_present(&paths) {
            return Ok(outcome);
        }
        let empty_verdict = auth_verdict(launch, &paths, false);
        let verdict = auth_verdict(launch, &paths, true);
        if !retried_unclassified_empty
            && outcome.exit_code == 1
            && empty_verdict == ExternalAuthVerdict::Unclassified
            && verdict != ExternalAuthVerdict::Auth
        {
            retried_unclassified_empty = true;
            continue;
        }
        if verdict == ExternalAuthVerdict::Auth && auth_attempt < max_auth {
            auth_attempt += 1;
            continue;
        }
        return Ok(outcome);
    }
}

fn auth_retry_limit() -> usize {
    env::var(AUTH_RETRIES_ENV)
        .ok()
        .and_then(|raw| raw.parse::<usize>().ok())
        .filter(|value| *value > 0)
        .unwrap_or(DEFAULT_AUTH_RETRIES)
}

/// Hold the shared Darwin vendor startup lock across one launch's startup.
///
/// A lock the launcher cannot acquire is not fatal, matching the legacy
/// launcher: contention only serializes keychain access, it never gates a run.
fn hold_startup_lock(
    program: VendorProgram,
) -> Option<larch_adapters::vendor_lifecycle::StartupLockRelease> {
    let root = shared_startup_lock_root()?;
    let config = StartupLockConfig::from_values(
        program,
        platform_name(),
        env::var(env_names::USER).ok().as_deref(),
        None,
        None,
        None,
    )
    .ok()?;
    let state = external_startup_lock_acquire(&root, &config).ok()?;
    external_startup_lock_release_after(state, &config).ok()
}

/// Prove Cursor can authenticate before a Cursor lane launches.
///
/// This is the single owner of the Cursor preflight composition: the standalone
/// `agent cursor-auth-preflight` command and every launcher that gates on Cursor
/// authentication call it rather than re-deriving the lock, config, and runner.
pub fn cursor_preflight_verdict(caller: &str) -> ReviewAuthVerdict {
    let refuse = |message: String| ReviewAuthVerdict::refuse(1, message);
    let Ok(runtime) = LarchRuntime::current_thread() else {
        return refuse(format!("{caller}: could not start the local runtime"));
    };
    let Ok(working_directory) = env::current_dir() else {
        return refuse(format!("{caller}: could not resolve the working directory"));
    };
    let config = CursorPreflightConfig::from_values(
        platform_name(),
        env::var(env_names::CURSOR_API_KEY).ok().as_deref(),
        caller,
    );
    let Some(lock_root) = shared_startup_lock_root() else {
        return refuse(format!(
            "{caller}: could not resolve the shared vendor startup-lock directory"
        ));
    };
    // Release delay `0`: the preflight holds the shared vendor startup lock only
    // for its own keychain read and must not add latency to a concurrent launch.
    let Ok(startup_lock) = StartupLockConfig::from_values(
        VendorProgram::Cursor,
        platform_name(),
        env::var(env_names::USER).ok().as_deref(),
        None,
        None,
        Some("0"),
    ) else {
        return refuse(format!(
            "{caller}: USER is unusable as a startup-lock path component"
        ));
    };
    let runner = TokioProcessRunner::new(Arc::new(NoopProcessObserver));
    runtime.block_on(cursor_auth_preflight(
        &runner,
        &config,
        VendorAuthContext {
            temporary_root: &lock_root,
            startup_lock: &startup_lock,
            working_directory: &working_directory,
        },
        &Cancellation::new(),
    ))
}

/// Resolve the startup-lock carrier, following the macOS `/tmp` symlink.
pub fn shared_startup_lock_root() -> Option<TemporaryRoot> {
    let canonical = fs::canonicalize(SHARED_STARTUP_LOCK_ROOT).ok()?;
    TemporaryRoot::resolve(Some(&canonical)).ok()
}

/// Report the operating system under the name the vendor gates already use.
pub fn platform_name() -> &'static str {
    match env::consts::OS {
        "macos" => "Darwin",
        "linux" => "Linux",
        other => other,
    }
}

fn policy_rejection_marker_present(paths: &LauncherArtifactPaths) -> bool {
    let diag = paths.path(LauncherArtifactKind::Diag);
    let text = read_optional_utf8_lossy(&diag)
        .unwrap_or_default()
        .unwrap_or_default();
    text.contains("POLICY_REJECTION=true") || text.contains("FAILURE_CLASS=policy-rejection")
}

/// Classify readable launch diagnostics for the retry decision.
///
/// The empty-failure probe deliberately excludes `.diag`, because the launcher
/// always writes a failure line there: including it would make every failure
/// look classified and suppress the one startup retry.
fn auth_verdict(
    launch: &ExternalAgentLaunch,
    paths: &LauncherArtifactPaths,
    include_diag: bool,
) -> ExternalAuthVerdict {
    let mut candidates: Vec<PathBuf> = launch.routing.stream_paths();
    candidates.extend([
        paths.path(LauncherArtifactKind::Sidecar),
        paths.path(LauncherArtifactKind::Events),
        paths.output().to_path_buf(),
    ]);
    if include_diag {
        candidates.push(paths.path(LauncherArtifactKind::Diag));
    }
    let texts: Vec<String> = candidates
        .iter()
        .map(|path| {
            read_optional_utf8_lossy(path)
                .unwrap_or_default()
                .unwrap_or_default()
        })
        .collect();
    external_auth_verdict(&launch.tool, texts.iter().map(String::as_str))
}

fn write_done_sentinel(
    prepared: &PreparedExternalAgentFiles,
    exit_code: i32,
) -> Result<(), String> {
    atomic_write_utf8_in(
        &prepared.root,
        &prepared.done,
        &format!("{exit_code}\n"),
        true,
        0o600,
    )
    .map_err(|error| format!("could not write completion sentinel: {error}"))
}

fn prepare_external_agent_files(
    launch: &ExternalAgentLaunch,
) -> Result<PreparedExternalAgentFiles, String> {
    let working_directory = env::current_dir().map_err(|error| error.to_string())?;
    let requested_output = PathBuf::from(&launch.output);
    let output = if requested_output.is_absolute() {
        requested_output
    } else {
        working_directory.join(requested_output)
    };
    let parent = output
        .parent()
        .ok_or_else(|| "--output has no parent directory".to_owned())?;
    let file_name = output
        .file_name()
        .ok_or_else(|| "--output must name a file".to_owned())?;
    ensure_directory_chain(parent).map_err(|error| error.to_string())?;
    let root = TemporaryRoot::resolve(Some(parent)).map_err(|error| error.to_string())?;
    let output = root
        .confine(root.path().join(file_name), PathIntent::Write)
        .map_err(|error| error.to_string())?
        .path()
        .to_path_buf();
    let paths = LauncherArtifactPaths::new(output);
    let diag = paths.path(LauncherArtifactKind::Diag);
    let done = suffixed_launcher_path(paths.output(), launch.sentinel_suffix);
    let mut stale_paths = vec![
        paths.output().to_path_buf(),
        paths.path(LauncherArtifactKind::Done),
        paths.path(LauncherArtifactKind::InnerDone),
        paths.path(LauncherArtifactKind::Meta),
        diag.clone(),
        paths.path(LauncherArtifactKind::StderrTail),
        paths.path(LauncherArtifactKind::FailureDiag),
    ];
    stale_paths.extend(launch.routing.stream_paths());
    for stale in stale_paths {
        remove_external_agent_stale(&root, &stale)?;
    }
    write_launch_meta(launch, &root, &paths)?;
    let output_file = root
        .confine(paths.output(), PathIntent::Write)
        .map_err(|error| error.to_string())?;
    let diag_file = root
        .confine(&diag, PathIntent::Write)
        .map_err(|error| error.to_string())?;
    let (stdout_file, stderr_file) = confine_stream_files(&launch.routing, &root)?;
    Ok(PreparedExternalAgentFiles {
        root,
        paths,
        output_file,
        diag_file,
        diag,
        done,
        stdout_file,
        stderr_file,
    })
}

fn confine_stream_files(
    routing: &ExternalAgentRouting,
    root: &TemporaryRoot,
) -> Result<(Option<ConfinedPath>, Option<ConfinedPath>), String> {
    let ExternalAgentRouting::Streams { stdout, stderr } = routing else {
        return Ok((None, None));
    };
    let confine = |path: &Option<PathBuf>| -> Result<Option<ConfinedPath>, String> {
        path.as_ref()
            .map(|path| {
                root.confine(path, PathIntent::Write)
                    .map_err(|error| error.to_string())
            })
            .transpose()
    };
    Ok((confine(stdout)?, confine(stderr)?))
}

fn write_launch_meta(
    launch: &ExternalAgentLaunch,
    root: &TemporaryRoot,
    paths: &LauncherArtifactPaths,
) -> Result<(), String> {
    let command_json = serde_json::to_string(&launch.command).map_err(|error| error.to_string())?;
    let mut meta = format!(
        "TOOL={}\nTIMEOUT={}\nCAPTURE_STDOUT={}\nCAPTURE_STDOUT_ONLY={}\nOUTPUT_FILE={}\n",
        sanitize_tool_label(&launch.tool),
        launch.timeout_seconds,
        launch.routing.capture_stdout(),
        launch.routing.capture_stdout_only(),
        launch.output,
    );
    if let Some(stderr_sink) = &launch.stderr_sink {
        writeln!(&mut meta, "STDERR_SINK={}", stderr_sink.display())
            .expect("formatting a String is infallible");
    }
    writeln!(&mut meta, "CMD_JSON={command_json}").expect("formatting a String is infallible");
    atomic_write_utf8_in(
        root,
        &paths.path(LauncherArtifactKind::Meta),
        &meta,
        true,
        0o600,
    )
    .map_err(|error| error.to_string())
}

fn run_prepared_external_agent(
    launch: &ExternalAgentLaunch,
    prepared: &PreparedExternalAgentFiles,
) -> i32 {
    let Ok(runtime) = LarchRuntime::current_thread() else {
        append_diag(
            prepared,
            "Failed to launch child: could not start the local runtime\n",
        );
        return 127;
    };
    let working_directory = match launch
        .working_directory
        .clone()
        .map_or_else(env::current_dir, Ok)
    {
        Ok(directory) => directory,
        Err(_error) => {
            append_diag(
                prepared,
                "Failed to launch child: could not resolve the working directory\n",
            );
            return 127;
        }
    };
    let request = match external_agent_request(launch, working_directory) {
        Ok(value) => value,
        Err(error) => {
            append_diag(prepared, &format!("Failed to launch child: {error}\n"));
            return 127;
        }
    };
    let (routing, policy_watch) = external_agent_file_routing(launch, prepared);
    let cancellation = Cancellation::new();
    let runner = TokioProcessRunner::new(Arc::new(NoopProcessObserver));
    let (result, policy_excerpt) = runtime.block_on(run_file_routed_external_agent(
        &runner,
        request,
        &cancellation,
        routing,
        policy_watch.as_ref(),
        launch.poll_interval,
    ));
    let exit_code = external_agent_exit_code(launch, prepared, result, policy_excerpt.is_some());
    if let Some(excerpt) = policy_excerpt {
        append_external_agent_policy_failure(prepared, &excerpt);
    }
    finish_external_agent_launch(launch, prepared, exit_code);
    exit_code
}

fn external_agent_request(
    launch: &ExternalAgentLaunch,
    working_directory: PathBuf,
) -> Result<larch_core::ProcessRequest, String> {
    let output_limit = NonZeroUsize::new(OUTPUT_LIMIT).unwrap_or(NonZeroUsize::MIN);
    let mut request = larch_core::ProcessRequest::new(
        ExternalProgram::Vendor(launch.program),
        launch.command.iter().skip(1).cloned(),
        working_directory,
        Duration::from_secs(launch.timeout_seconds),
        SHUTDOWN_GRACE,
        output_limit,
    )
    .map(|request| request.with_environment_for_vendor(launch.program))
    .map_err(|error| error.to_string())?;
    for (key, value) in &launch.environment {
        request = request.with_environment(*key, value.clone());
    }
    Ok(request)
}

fn external_agent_file_routing(
    launch: &ExternalAgentLaunch,
    prepared: &PreparedExternalAgentFiles,
) -> (ProcessFileRouting, Option<ConfinedPath>) {
    let (routing, stdout_target) = match &launch.routing {
        ExternalAgentRouting::CaptureCombined => (
            ProcessFileRouting::combined(prepared.output_file.clone()),
            Some(prepared.output_file.clone()),
        ),
        ExternalAgentRouting::CaptureStdoutOnly => (
            ProcessFileRouting::separate(prepared.output_file.clone(), prepared.diag_file.clone()),
            Some(prepared.output_file.clone()),
        ),
        ExternalAgentRouting::Streams { .. } => (
            ProcessFileRouting::streams(prepared.stdout_file.clone(), prepared.stderr_file.clone()),
            prepared.stdout_file.clone(),
        ),
    };
    let stdin = launch.stdin.clone().map_or_else(
        || {
            if launch.tool == "codex" {
                ProcessStdinRouting::Null
            } else {
                ProcessStdinRouting::Inherit
            }
        },
        ProcessStdinRouting::File,
    );
    let routing = routing.with_stdin(stdin);
    // Only Codex publishes the structured event stream a policy rejection lands
    // in, so the watcher stays keyed to the file that receives its stdout.
    let policy_watch = (launch.tool == "codex").then_some(stdout_target).flatten();
    (routing, policy_watch)
}

fn external_agent_exit_code(
    launch: &ExternalAgentLaunch,
    prepared: &PreparedExternalAgentFiles,
    result: Result<larch_core::ProcessOutput, ProcessError>,
    policy_rejected: bool,
) -> i32 {
    if policy_rejected {
        return 1;
    }
    match result {
        Ok(output) => output.status().code().unwrap_or(1),
        Err(error) if error.kind() == ProcessErrorKind::TimedOut => {
            let size = output_size(prepared.paths.output());
            append_diag(
                prepared,
                &format!(
                    "Timed out after {}s (limit: {}s). Process was killed after exceeding the timeout. Output size: {size} bytes.\n",
                    launch.timeout_seconds, launch.timeout_seconds
                ),
            );
            124
        }
        Err(error) => {
            let code = spawn_error_exit_code(&error);
            if error.kind() == ProcessErrorKind::Spawn {
                let _ignored =
                    atomic_write_utf8_in(&prepared.root, prepared.paths.output(), "", true, 0o600);
            }
            append_diag(
                prepared,
                &format!("Failed to launch child: {}\n", error.message()),
            );
            code
        }
    }
}

fn append_external_agent_policy_failure(prepared: &PreparedExternalAgentFiles, excerpt: &str) {
    append_diag(
        prepared,
        &format!(
            "FAILURE_CLASS=policy-rejection\nPOLICY_REJECTION=true\nCodex exec_command policy rejection detected in events stream.\nMatched excerpt:\n{}\n",
            excerpt.trim_end()
        ),
    );
}

trait VendorRequestEnvironment {
    fn with_environment_for_vendor(self, program: VendorProgram) -> Self;
}

impl VendorRequestEnvironment for larch_core::ProcessRequest {
    fn with_environment_for_vendor(mut self, program: VendorProgram) -> Self {
        match program {
            VendorProgram::Claude | VendorProgram::Codex => {
                let key = if program == VendorProgram::Claude {
                    ChildEnvironment::AnthropicApiKey
                } else {
                    ChildEnvironment::OpenAiApiKey
                };
                if let Some(value) = env::var_os(key.name()) {
                    self = self.with_environment(key, value);
                }
            }
            VendorProgram::Cursor => {
                let credential = env::var(env_names::CURSOR_API_KEY)
                    .ok()
                    .and_then(|value| CursorCredential::parse(&value));
                for (key, value) in cursor_child_environment(credential.as_ref()) {
                    self = self.with_environment(key, value);
                }
            }
        }
        self
    }
}

async fn run_file_routed_external_agent(
    runner: &TokioProcessRunner,
    request: larch_core::ProcessRequest,
    cancellation: &Cancellation,
    routing: ProcessFileRouting,
    policy_watch: Option<&ConfinedPath>,
    poll_interval: Duration,
) -> (
    Result<larch_core::ProcessOutput, ProcessError>,
    Option<String>,
) {
    let mut launch = Box::pin(runner.run_with_files(request, cancellation, routing));
    let mut ticker = tokio::time::interval(poll_interval);
    let mut policy_excerpt = None;
    loop {
        tokio::select! {
            result = &mut launch => {
                if policy_excerpt.is_none()
                    && let Some(path) = policy_watch
                    && let Some(excerpt) = codex_policy_excerpt_from_file(path)
                {
                    policy_excerpt = Some(excerpt);
                }
                return (result, policy_excerpt);
            }
            _ = ticker.tick(), if policy_watch.is_some() && policy_excerpt.is_none() => {
                if let Some(path) = policy_watch
                    && let Some(excerpt) = codex_policy_excerpt_from_file(path)
                {
                    eprintln!("❌ codex agent: exec_command policy rejection detected, killing");
                    cancellation.cancel();
                    policy_excerpt = Some(excerpt);
                }
            }
        }
    }
}

fn codex_policy_excerpt_from_file(path: &ConfinedPath) -> Option<String> {
    path.revalidate().ok()?;
    let mut file = fs::File::open(path.path()).ok()?;
    let length = file.metadata().ok()?.len();
    let cap = u64::try_from(larch_core::CODEX_POLICY_REJECTION_TAIL_BYTES + 1).ok()?;
    if length > cap {
        file.seek(SeekFrom::Start(length - cap)).ok()?;
    }
    let mut bytes = Vec::with_capacity(usize::try_from(length.min(cap)).ok()?);
    file.read_to_end(&mut bytes).ok()?;
    let excerpt = codex_policy_rejection_excerpt(&String::from_utf8_lossy(&bytes));
    (!excerpt.is_empty()).then_some(excerpt)
}

fn finish_external_agent_launch(
    launch: &ExternalAgentLaunch,
    prepared: &PreparedExternalAgentFiles,
    exit_code: i32,
) {
    let size = output_size(prepared.paths.output());
    if exit_code != 0 {
        eprintln!(
            "❌ {} agent: FAILED (exit code {exit_code}, output {size} bytes)",
            launch.tool
        );
        append_diag(
            prepared,
            &format!("Failed with exit code {exit_code}. Output size: {size} bytes.\n"),
        );
        if let Ok(Some(source)) = select_failed_agent_stderr_source(
            &prepared.paths,
            launch.routing.stderr_mode(),
            launch.stderr_sink.as_deref(),
        ) {
            let _ignored = write_failed_agent_stderr_tail(
                &prepared.root,
                &source,
                &prepared.paths,
                None,
                None,
            );
        }
        let _ignored = write_failure_diag(
            &prepared.root,
            &prepared.paths,
            launch.stderr_sink.as_deref(),
            None,
            None,
        );
    } else if size == 0 {
        eprintln!(
            "⚠ {} agent: completed but OUTPUT IS EMPTY (exit code 0)",
            launch.tool
        );
        append_diag(
            prepared,
            "Process exited successfully (code 0) but produced no output.\n",
        );
        remove_failure_diag(prepared);
    } else {
        eprintln!(
            "✓ {} agent: completed (exit code 0, output {size} bytes)",
            launch.tool
        );
        remove_failure_diag(prepared);
    }
}

fn remove_failure_diag(prepared: &PreparedExternalAgentFiles) {
    let _ignored = remove_external_agent_stale(
        &prepared.root,
        &prepared.paths.path(LauncherArtifactKind::FailureDiag),
    );
}

fn append_diag(prepared: &PreparedExternalAgentFiles, text: &str) {
    let _ignored = append_launcher_text(&prepared.root, &prepared.diag, text);
}

fn append_launcher_text(root: &TemporaryRoot, path: &Path, text: &str) -> Result<(), String> {
    let existing = read_external_agent_text(root, path)?;
    atomic_write_utf8_in(root, path, &format!("{existing}{text}"), true, 0o600)
        .map_err(|error| error.to_string())
}

fn remove_external_agent_stale(root: &TemporaryRoot, path: &Path) -> Result<(), String> {
    match fs::symlink_metadata(path) {
        Ok(_metadata) => {
            let confined = root
                .confine(path, PathIntent::Cleanup)
                .map_err(|error| error.to_string())?;
            remove_optional_file(confined.path()).map_err(|error| error.to_string())
        }
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(()),
        Err(error) => Err(error.to_string()),
    }
}

fn read_external_agent_text(root: &TemporaryRoot, path: &Path) -> Result<String, String> {
    match fs::symlink_metadata(path) {
        Ok(_metadata) => {
            let confined = root
                .confine(path, PathIntent::Read)
                .map_err(|error| error.to_string())?;
            fs::read(confined.path())
                .map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
                .map_err(|error| error.to_string())
        }
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(String::new()),
        Err(error) => Err(error.to_string()),
    }
}

fn output_size(path: &Path) -> u64 {
    fs::metadata(path).map_or(0, |metadata| metadata.len())
}

fn spawn_error_exit_code(error: &ProcessError) -> i32 {
    if error.kind() == ProcessErrorKind::Spawn && error.message().contains("Permission denied") {
        126
    } else if error.kind() == ProcessErrorKind::Spawn {
        127
    } else {
        1
    }
}

/// Append a suffix to a launcher output path without touching its extension.
pub fn suffixed_launcher_path(output: &Path, suffix: &str) -> PathBuf {
    let mut rendered = output.as_os_str().to_owned();
    rendered.push(suffix);
    PathBuf::from(rendered)
}
