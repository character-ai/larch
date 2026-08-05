//! Tokio-backed execution for the closed external-process port.

use crate::logging::JsonlJournal;
use crate::runtime::{Cancellation, ChildProcess, ChildWait, shutdown_child};
use larch_core::{
    BusinessClock, ChildEnvironment, ExternalProcessRunner, ExternalProgram, HostUtilityProgram,
    JournalRecord, ProcessCancellation, ProcessError, ProcessErrorKind, ProcessEvent,
    ProcessEventKind, ProcessFuture, ProcessObserver, ProcessOutput, ProcessRequest, ProcessStatus,
    RunId, env as larch_env,
};
use std::{
    env,
    ffi::OsString,
    io::{self, Write},
    num::NonZeroUsize,
    path::Path,
    process::{ExitStatus, Stdio},
    sync::{
        Arc, Mutex,
        atomic::{AtomicUsize, Ordering},
    },
    time::Duration,
};
use tokio::{
    io::{AsyncRead, AsyncReadExt, AsyncWriteExt},
    process::{Child, ChildStderr, ChildStdin, ChildStdout, Command},
    task::JoinHandle,
    time,
};

#[cfg(unix)]
use nix::{
    errno::Errno,
    sys::signal::{Signal, killpg},
    unistd::Pid,
};

impl ProcessCancellation for Cancellation {
    fn is_cancelled(&self) -> bool {
        self.is_cancelled()
    }

    fn cancelled(&self) -> std::pin::Pin<Box<dyn Future<Output = ()> + Send + '_>> {
        Box::pin(self.cancelled())
    }
}

use std::future::Future;

/// Observation sink used when composition does not configure a process journal.
#[derive(Clone, Copy, Debug, Default)]
pub struct NoopProcessObserver;

impl ProcessObserver for NoopProcessObserver {
    fn observe(&self, _event: ProcessEvent) {}
}

/// Best-effort JSONL process observer. It records only closed labels and counts.
pub struct ProcessJournalObserver<Writer, Clock> {
    journal: Mutex<JsonlJournal<Writer>>,
    run_id: RunId,
    clock: Clock,
    dropped_records: AtomicUsize,
}

impl<Writer, Clock> ProcessJournalObserver<Writer, Clock>
where
    Writer: Write,
{
    /// Bind a run-scoped journal and its injected business clock.
    #[must_use]
    pub const fn new(writer: Writer, run_id: RunId, clock: Clock) -> Self {
        Self {
            journal: Mutex::new(JsonlJournal::new(writer)),
            run_id,
            clock,
            dropped_records: AtomicUsize::new(0),
        }
    }

    /// Return the number of records dropped after validation, locking, or I/O failure.
    #[must_use]
    pub fn dropped_records(&self) -> usize {
        self.dropped_records.load(Ordering::Relaxed)
    }
}

impl<Writer, Clock> ProcessObserver for ProcessJournalObserver<Writer, Clock>
where
    Writer: Write + Send,
    Clock: BusinessClock + Send + Sync,
{
    fn observe(&self, event: ProcessEvent) {
        let exit_code = event
            .exit_code()
            .map_or_else(|| "none".to_owned(), |code| code.to_string());
        let fields = [
            ("kind", event_kind(event.kind()).to_owned()),
            ("operation", event.operation().to_owned()),
            ("exit_code", exit_code),
            ("stdout_bytes", event.stdout_bytes().to_string()),
            ("stderr_bytes", event.stderr_bytes().to_string()),
        ];
        let record = JournalRecord::new(
            self.clock.now(),
            self.run_id.clone(),
            "external-process",
            fields.iter().map(|(key, value)| (*key, value.as_str())),
        );
        let written = record.ok().and_then(|record| {
            self.journal
                .lock()
                .ok()
                .and_then(|mut journal| journal.append(&record).ok())
        });
        if written.is_none() {
            self.dropped_records.fetch_add(1, Ordering::Relaxed);
        }
    }
}

const fn event_kind(kind: ProcessEventKind) -> &'static str {
    match kind {
        ProcessEventKind::Started => "started",
        ProcessEventKind::Exited => "exited",
        ProcessEventKind::Cancelled => "cancelled",
        ProcessEventKind::TimedOut => "timed-out",
        ProcessEventKind::Failed => "failed",
    }
}

/// Production process runner. The observer receives only bounded counts and closed labels.
pub struct TokioProcessRunner {
    observer: Arc<dyn ProcessObserver>,
}

impl TokioProcessRunner {
    /// Bind the structured process-observation sink.
    #[must_use]
    pub fn new(observer: Arc<dyn ProcessObserver>) -> Self {
        Self { observer }
    }

    fn observe(
        &self,
        kind: ProcessEventKind,
        request: &ProcessRequest,
        output: Option<&ProcessOutput>,
    ) {
        let (exit_code, stdout_bytes, stderr_bytes) = output.map_or((None, 0, 0), |output| {
            (
                output.status().code(),
                output.stdout().len(),
                output.stderr().len(),
            )
        });
        self.observer.observe(ProcessEvent::new(
            kind,
            request.program().operation(),
            exit_code,
            stdout_bytes,
            stderr_bytes,
        ));
    }

    async fn run_owned(
        &self,
        request: ProcessRequest,
        cancellation: &dyn ProcessCancellation,
    ) -> Result<ProcessOutput, ProcessError> {
        if cancellation.is_cancelled() {
            self.observe(ProcessEventKind::Cancelled, &request, None);
            return Err(ProcessError::new(
                ProcessErrorKind::Cancelled,
                "external process cancelled before spawn",
                None,
            ));
        }
        self.observe(ProcessEventKind::Started, &request, None);
        let mut child = match spawn_child(&request) {
            Ok(child) => child,
            Err(error) => {
                self.observe(ProcessEventKind::Failed, &request, None);
                return Err(process_io_error(
                    ProcessErrorKind::Spawn,
                    "cannot spawn external process",
                    &error,
                ));
            }
        };
        let streams = match Captures::start(&mut child, &request) {
            Ok(streams) => streams,
            Err(error) => {
                let cleanup = shutdown_child(&mut child, request.shutdown_grace()).await;
                self.observe(ProcessEventKind::Failed, &request, None);
                return cleanup.map_or_else(
                    |cleanup_error| {
                        Err(process_io_error(
                            ProcessErrorKind::Termination,
                            "cannot clean up external process after pipe setup failure",
                            &cleanup_error,
                        ))
                    },
                    |_status| Err(error),
                );
            }
        };
        let wait = wait_for_child(&mut child, &request, cancellation).await;
        let (status, interrupted) = match wait {
            Ok(result) => result,
            Err(error) => {
                streams.abort().await;
                self.observe(ProcessEventKind::Failed, &request, None);
                return Err(error);
            }
        };
        let captured_pair = match streams.finish().await {
            Ok(captured) => captured,
            Err(error) => {
                self.observe(ProcessEventKind::Failed, &request, None);
                return Err(error);
            }
        };
        let output = ProcessOutput::new(
            ProcessStatus::new(status.success(), status.code()),
            captured_pair.stdout.bytes,
            captured_pair.stderr.bytes,
            captured_pair.stdout.truncated,
            captured_pair.stderr.truncated,
        );
        if let Some(kind) = interrupted {
            let event = match kind {
                ProcessErrorKind::Cancelled => ProcessEventKind::Cancelled,
                ProcessErrorKind::TimedOut => ProcessEventKind::TimedOut,
                _ => ProcessEventKind::Failed,
            };
            self.observe(event, &request, Some(&output));
            return Err(ProcessError::new(
                kind,
                interruption_message(kind),
                Some(output),
            ));
        }
        self.observe(ProcessEventKind::Exited, &request, Some(&output));
        Ok(output)
    }
}

impl Default for TokioProcessRunner {
    fn default() -> Self {
        Self::new(Arc::new(NoopProcessObserver))
    }
}

/// Result of the bounded host open-file probe used by Git index-lock recovery.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum OpenFileHolderStatus {
    Held,
    Absent,
    Unverifiable,
}

/// Determine whether another process has one absolute file path open.
pub async fn probe_open_file_holder<R: ExternalProcessRunner>(
    runner: &R,
    path: &Path,
    working_directory: &Path,
    cancellation: &dyn ProcessCancellation,
) -> OpenFileHolderStatus {
    if !path.is_absolute() || path.as_os_str().as_encoded_bytes().contains(&0) {
        return OpenFileHolderStatus::Unverifiable;
    }
    let request = ProcessRequest::new(
        ExternalProgram::HostUtility(HostUtilityProgram::Lsof),
        [OsString::from("-t"), OsString::from("--"), path.into()],
        working_directory.to_path_buf(),
        Duration::from_secs(3),
        Duration::from_secs(1),
        NonZeroUsize::new(16 * 1024).unwrap_or(NonZeroUsize::MIN),
    );
    let Ok(request) = request else {
        return OpenFileHolderStatus::Unverifiable;
    };
    let Ok(output) = runner.run(request, cancellation).await else {
        return OpenFileHolderStatus::Unverifiable;
    };
    if !output.status().success() {
        return if output.stdout().is_empty() && output.stderr().is_empty() {
            OpenFileHolderStatus::Absent
        } else {
            OpenFileHolderStatus::Unverifiable
        };
    }
    let current = std::process::id();
    let mut saw_pid = false;
    for line in output.stdout().split(|byte| *byte == b'\n') {
        if line.is_empty() {
            continue;
        }
        let Ok(text) = std::str::from_utf8(line) else {
            return OpenFileHolderStatus::Unverifiable;
        };
        let Ok(pid) = text.parse::<u32>() else {
            return OpenFileHolderStatus::Unverifiable;
        };
        saw_pid = true;
        if pid != current {
            return OpenFileHolderStatus::Held;
        }
    }
    if saw_pid {
        OpenFileHolderStatus::Absent
    } else {
        OpenFileHolderStatus::Unverifiable
    }
}

impl ExternalProcessRunner for TokioProcessRunner {
    fn run<'a>(
        &'a self,
        request: ProcessRequest,
        cancellation: &'a dyn ProcessCancellation,
    ) -> ProcessFuture<'a> {
        Box::pin(self.run_owned(request, cancellation))
    }
}

fn spawn_child(request: &ProcessRequest) -> io::Result<OwnedChild> {
    let mut command = Command::new(request.program().executable());
    let mut arguments: Vec<OsString> = request.arguments().to_vec();
    request.program().append_fixed_arguments(&mut arguments);
    command
        .args(arguments)
        .current_dir(request.working_directory())
        .env_clear()
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .kill_on_drop(true);
    copy_allowed_environment(&mut command, request);
    #[cfg(unix)]
    command.process_group(0);
    let child = command.spawn()?; // lint-subprocess-via-runner: ok shared process runner is the sole product owner
    OwnedChild::new(child)
}

fn copy_allowed_environment(command: &mut Command, request: &ProcessRequest) {
    for key in ChildEnvironment::production() {
        if let Some(value) = env::var_os(key.name()) {
            command.env(key.name(), value);
        }
    }
    if matches!(request.program(), ExternalProgram::GitHub(_)) {
        for (key, name) in [
            (ChildEnvironment::GhConfigDir, larch_env::GH_CONFIG_DIR),
            (ChildEnvironment::XdgConfigHome, larch_env::XDG_CONFIG_HOME),
        ] {
            if let Some(value) = env::var_os(name) {
                command.env(key.name(), value);
            }
        }
    }
    for (key, value) in request.environment() {
        command.env(key.name(), value);
    }
}

struct OwnedChild {
    child: Child,
    #[cfg(unix)]
    process_group: Pid,
}

impl OwnedChild {
    fn new(child: Child) -> io::Result<Self> {
        #[cfg(unix)]
        let process_group = child
            .id()
            .and_then(|id| i32::try_from(id).ok())
            .map(Pid::from_raw)
            .ok_or_else(|| io::Error::other("spawned child has no process group identity"))?;
        Ok(Self {
            child,
            #[cfg(unix)]
            process_group,
        })
    }

    const fn stdin(&mut self) -> Option<ChildStdin> {
        self.child.stdin.take()
    }

    const fn stdout(&mut self) -> Option<ChildStdout> {
        self.child.stdout.take()
    }

    const fn stderr(&mut self) -> Option<ChildStderr> {
        self.child.stderr.take()
    }

    #[cfg(unix)]
    fn signal_group(&self, signal: Signal) -> io::Result<()> {
        match killpg(self.process_group, signal) {
            Ok(()) | Err(Errno::ESRCH) => Ok(()),
            Err(error) => Err(io::Error::from_raw_os_error(error as i32)),
        }
    }
}

impl ChildProcess for OwnedChild {
    type Exit = ExitStatus;

    fn request_shutdown(&mut self) -> io::Result<()> {
        #[cfg(unix)]
        let result = self.signal_group(Signal::SIGTERM);
        #[cfg(not(unix))]
        let result = self.child.start_kill();
        result
    }

    fn force_kill(&mut self) -> io::Result<()> {
        #[cfg(unix)]
        let result = self.signal_group(Signal::SIGKILL);
        #[cfg(not(unix))]
        let result = self.child.start_kill();
        result
    }

    fn wait(&mut self) -> ChildWait<'_, Self::Exit> {
        Box::pin(self.child.wait())
    }
}

async fn wait_for_child(
    child: &mut OwnedChild,
    request: &ProcessRequest,
    cancellation: &dyn ProcessCancellation,
) -> Result<(ExitStatus, Option<ProcessErrorKind>), ProcessError> {
    enum WaitResult {
        Exited(io::Result<ExitStatus>),
        Interrupted(ProcessErrorKind),
    }
    let result = tokio::select! {
        biased;
        () = cancellation.cancelled() => WaitResult::Interrupted(ProcessErrorKind::Cancelled),
        () = time::sleep(request.timeout()) => WaitResult::Interrupted(ProcessErrorKind::TimedOut),
        status = child.wait() => WaitResult::Exited(status),
    };
    match result {
        WaitResult::Exited(Ok(status)) => Ok((status, None)),
        WaitResult::Exited(Err(wait_error)) => {
            shutdown_child(child, request.shutdown_grace())
                .await
                .map_err(|cleanup_error| {
                    process_io_error(
                        ProcessErrorKind::Termination,
                        "cannot clean up external process after wait failure",
                        &cleanup_error,
                    )
                })?;
            Err(process_io_error(
                ProcessErrorKind::Wait,
                "cannot wait for external process",
                &wait_error,
            ))
        }
        WaitResult::Interrupted(kind) => shutdown_child(child, request.shutdown_grace())
            .await
            .map(|status| (status, Some(kind)))
            .map_err(|error| {
                process_io_error(
                    ProcessErrorKind::Termination,
                    "cannot terminate external process group",
                    &error,
                )
            }),
    }
}

struct CapturedStream {
    bytes: Vec<u8>,
    truncated: bool,
}

struct CapturedPair {
    stdout: CapturedStream,
    stderr: CapturedStream,
}

struct Captures {
    stdin: JoinHandle<io::Result<()>>,
    stdout: JoinHandle<io::Result<CapturedStream>>,
    stderr: JoinHandle<io::Result<CapturedStream>>,
}

impl Captures {
    fn start(child: &mut OwnedChild, request: &ProcessRequest) -> Result<Self, ProcessError> {
        let stdin = child.stdin().ok_or_else(|| missing_pipe("stdin"))?;
        let stdout = child.stdout().ok_or_else(|| missing_pipe("stdout"))?;
        let stderr = child.stderr().ok_or_else(|| missing_pipe("stderr"))?;
        let input = request.stdin().to_vec();
        let limit = request.output_limit().get();
        Ok(Self {
            stdin: tokio::spawn(write_input(stdin, input)),
            stdout: tokio::spawn(capture_stream(stdout, limit)),
            stderr: tokio::spawn(capture_stream(stderr, limit)),
        })
    }

    async fn finish(self) -> Result<CapturedPair, ProcessError> {
        join_input(self.stdin).await?;
        let stdout = join_capture(self.stdout, "stdout").await?;
        let stderr = join_capture(self.stderr, "stderr").await?;
        Ok(CapturedPair { stdout, stderr })
    }

    async fn abort(self) {
        self.stdin.abort();
        self.stdout.abort();
        self.stderr.abort();
        let _results = tokio::join!(self.stdin, self.stdout, self.stderr);
    }
}

async fn write_input(mut stdin: ChildStdin, input: Vec<u8>) -> io::Result<()> {
    stdin.write_all(&input).await?;
    stdin.shutdown().await
}

async fn capture_stream(
    mut stream: impl AsyncRead + Unpin,
    limit: usize,
) -> io::Result<CapturedStream> {
    let mut bytes = Vec::with_capacity(limit.min(8 * 1024));
    let mut buffer = [0_u8; 8 * 1024];
    let mut truncated = false;
    loop {
        let read = stream.read(&mut buffer).await?;
        if read == 0 {
            break;
        }
        let remaining = limit.saturating_sub(bytes.len());
        let keep = read.min(remaining);
        bytes.extend_from_slice(&buffer[..keep]);
        truncated |= keep != read;
    }
    Ok(CapturedStream { bytes, truncated })
}

async fn join_input(handle: JoinHandle<io::Result<()>>) -> Result<(), ProcessError> {
    handle
        .await
        .map_err(|error| {
            ProcessError::new(
                ProcessErrorKind::Input,
                format!("external process stdin task failed: {error}"),
                None,
            )
        })?
        .map_err(|error| {
            process_io_error(
                ProcessErrorKind::Input,
                "cannot write external process stdin",
                &error,
            )
        })
}

async fn join_capture(
    handle: JoinHandle<io::Result<CapturedStream>>,
    stream: &str,
) -> Result<CapturedStream, ProcessError> {
    handle
        .await
        .map_err(|error| {
            ProcessError::new(
                ProcessErrorKind::Capture,
                format!("external process {stream} task failed: {error}"),
                None,
            )
        })?
        .map_err(|error| {
            process_io_error(
                ProcessErrorKind::Capture,
                &format!("cannot capture external process {stream}"),
                &error,
            )
        })
}

fn missing_pipe(stream: &str) -> ProcessError {
    ProcessError::new(
        ProcessErrorKind::Spawn,
        format!("external process {stream} pipe is unavailable"),
        None,
    )
}

fn process_io_error(kind: ProcessErrorKind, context: &str, error: &io::Error) -> ProcessError {
    ProcessError::new(kind, format!("{context}: {error}"), None)
}

const fn interruption_message(kind: ProcessErrorKind) -> &'static str {
    match kind {
        ProcessErrorKind::Cancelled => "external process cancelled",
        ProcessErrorKind::TimedOut => "external process timed out",
        _ => "external process failed",
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::runtime::LarchRuntime;
    use larch_core::{
        ExternalProgram, GitCliOperation, GitHubCliOperation, HostUtilityProgram, ProcessRequest,
        ProcessRequestError, VendorProgram,
    };
    use larch_test_support::{FakeProcessRunner, NeverCancelled, ProcessOutputBuilder, TestClock};
    use std::{
        num::NonZeroUsize,
        sync::Mutex,
        time::{Duration, SystemTime},
    };

    #[derive(Default)]
    struct RecordingObserver(Mutex<Vec<ProcessEvent>>);

    impl ProcessObserver for RecordingObserver {
        fn observe(&self, event: ProcessEvent) {
            self.0.lock().expect("observer lock").push(event);
        }
    }

    fn request(limit: usize) -> Result<ProcessRequest, ProcessRequestError> {
        ProcessRequest::new(
            ExternalProgram::Git(GitCliOperation::Version),
            std::iter::empty::<&str>(),
            std::env::current_dir().expect("cwd"),
            Duration::from_secs(5),
            Duration::from_millis(10),
            NonZeroUsize::new(limit).expect("non-zero limit"),
        )
    }

    #[test]
    fn captures_approved_git_output_and_structured_observations() {
        let runtime = LarchRuntime::new().expect("runtime");
        let observer = Arc::new(RecordingObserver::default());
        let runner = TokioProcessRunner::new(observer.clone());
        let output = runtime
            .block_on(runner.run(request(4096).expect("request"), &Cancellation::new()))
            .expect("Git version should run");

        assert!(output.status().success());
        assert!(String::from_utf8_lossy(output.stdout()).starts_with("git version "));
        assert!(output.stderr().is_empty());
        let event_kinds = {
            let events = observer.0.lock().expect("observer lock");
            (
                events.first().map(|event| event.kind()),
                events.last().map(|event| event.kind()),
            )
        };
        assert_eq!(event_kinds.0, Some(ProcessEventKind::Started));
        assert_eq!(event_kinds.1, Some(ProcessEventKind::Exited));
    }

    #[test]
    fn cancellation_before_spawn_does_not_launch_the_child() {
        let runtime = LarchRuntime::new().expect("runtime");
        let cancellation = Cancellation::new();
        cancellation.cancel();
        let error = runtime
            .block_on(
                TokioProcessRunner::default().run(request(1024).expect("request"), &cancellation),
            )
            .expect_err("cancelled request should fail");
        assert_eq!(error.kind(), ProcessErrorKind::Cancelled);
        assert!(error.output().is_none());
    }

    #[test]
    fn output_capture_is_bounded_while_the_pipe_is_fully_drained() {
        let runtime = LarchRuntime::new().expect("runtime");
        let output = runtime
            .block_on(
                TokioProcessRunner::default()
                    .run(request(4).expect("request"), &Cancellation::new()),
            )
            .expect("Git version should exit");
        assert_eq!(output.stdout().len(), 4);
        assert!(output.stdout_truncated());
    }

    #[test]
    fn executable_allowlist_contains_only_approved_typed_processes() {
        let allowed = [
            ExternalProgram::Vendor(VendorProgram::Claude),
            ExternalProgram::Vendor(VendorProgram::Codex),
            ExternalProgram::Vendor(VendorProgram::Cursor),
            ExternalProgram::Git(GitCliOperation::Version),
            ExternalProgram::GitHub(GitHubCliOperation::AuthToken),
            ExternalProgram::HostUtility(HostUtilityProgram::Lsof),
        ];
        assert_eq!(allowed.len(), 6);
        assert!(allowed.iter().all(|program| !program.reason().is_empty()));
        assert!(
            allowed
                .iter()
                .any(|program| matches!(program.executable().to_str(), Some("gh")))
        );
        assert!(
            !allowed
                .iter()
                .any(|program| matches!(program.executable().to_str(), Some("gcloud")))
        );
        let inherited: Vec<&str> = ChildEnvironment::production()
            .map(ChildEnvironment::name)
            .collect();
        assert!(!inherited.contains(&"LARCH_GH_TOKEN"));
        assert!(!inherited.contains(&"GH_TOKEN"));
        assert!(!inherited.contains(&"GITHUB_TOKEN"));
        assert!(!inherited.contains(&"GOOGLE_APPLICATION_CREDENTIALS"));
        assert!(!inherited.contains(&"OPENAI_API_KEY"));
        assert!(!inherited.contains(&"CURSOR_CONFIG_DIR"));
    }

    #[test]
    fn open_file_probe_is_typed_and_fails_closed() {
        let runtime = LarchRuntime::new().expect("runtime");
        let cwd = std::env::current_dir().expect("cwd");
        let path = cwd.join("index.lock");
        let other_pid = std::process::id().saturating_add(1);
        let runner = FakeProcessRunner::new([
            Ok(ProcessOutputBuilder::success()
                .stdout(format!("{other_pid}\n").into_bytes())
                .build()),
            Ok(ProcessOutputBuilder::failure(1).build()),
            Ok(ProcessOutputBuilder::failure(1)
                .stderr(b"probe warning".to_vec())
                .build()),
        ]);

        let held = runtime.block_on(probe_open_file_holder(
            &runner,
            &path,
            &cwd,
            &NeverCancelled,
        ));
        let absent = runtime.block_on(probe_open_file_holder(
            &runner,
            &path,
            &cwd,
            &NeverCancelled,
        ));
        let unverifiable = runtime.block_on(probe_open_file_holder(
            &runner,
            &path,
            &cwd,
            &NeverCancelled,
        ));

        assert_eq!(held, OpenFileHolderStatus::Held);
        assert_eq!(absent, OpenFileHolderStatus::Absent);
        assert_eq!(unverifiable, OpenFileHolderStatus::Unverifiable);
        let requests = runner.requests();
        assert_eq!(requests[0].program().operation(), "host.open-file-probe");
        assert_eq!(requests[0].arguments()[..2], ["-t", "--"]);
    }

    #[test]
    fn process_journal_records_only_closed_fields_and_counts() {
        let observer = ProcessJournalObserver::new(
            Vec::new(),
            RunId::parse("run-process").expect("run ID"),
            TestClock::new(SystemTime::UNIX_EPOCH),
        );
        observer.observe(ProcessEvent::new(
            ProcessEventKind::Exited,
            "vendor.codex",
            Some(0),
            12,
            3,
        ));

        assert_eq!(observer.dropped_records(), 0);
        let bytes = observer
            .journal
            .into_inner()
            .expect("journal lock")
            .into_inner();
        let line = String::from_utf8(bytes).expect("JSONL UTF-8");
        assert!(line.contains(r#""event":"external-process""#));
        assert!(line.contains(r#""operation":"vendor.codex""#));
        assert!(line.contains(r#""stdout_bytes":"12""#));
    }
}
