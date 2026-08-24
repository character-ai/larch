//! `session setup`: one Rust-owned composition of the session bootstrap.
//!
//! The leaf's sibling commands already own preflight, reviewer probing, and
//! session-env publication.  This module sequences those owners, keeps setup's
//! stdout grammar stable, and owns only the temp-directory lifecycle glue.

use crate::{
    admission_commands, agent_commands,
    argparse_compat::{parse_with_flags, usage_error},
    github_repository_resolution, session_env_commands,
};
use larch_adapters::{
    PathSafetyError, PathSafetyErrorKind, SecureTempDir, SessionSetupOwner,
    SystemProcessIdentityHost, TemporaryRoot, commit_uncommitted_session_setup,
    ensure_directory_chain, path_under, read_kv_raw,
    runtime::{Cancellation, LarchRuntime},
    write_confined_file, write_session_id, write_uncommitted_session_setup_marker,
};
use larch_core::{
    RepositoryRead, allowed_session_roots, binary_on_path, cleanup_cache_sessions_root,
    read_process_identity, validate_repo_root_value,
};
use std::{
    collections::BTreeMap,
    env,
    ffi::OsString,
    fs,
    io::{self, Write as _},
    path::{Path, PathBuf},
    process::ExitCode,
    sync::{
        Arc,
        atomic::{AtomicU8, Ordering},
    },
    thread,
    time::Duration,
};

const SETUP_USAGE: &str = concat!(
    "usage: session setup [--prefix PREFIX] [--skip-preflight]\n",
    "                     [--skip-branch-check] [--skip-repo-check]\n",
    "                     [--check-reviewers] [--skip-codex-probe]\n",
    "                     [--skip-cursor-probe]\n",
    "                     [--write-session-env WRITE_SESSION_ENV]\n",
    "                     [--caller-env CALLER_ENV]\n",
    "                     [--deny-edit-write DENY_EDIT_WRITE]",
);
const SETUP_OPTIONS: &[&str] = &[
    "--prefix",
    "--write-session-env",
    "--caller-env",
    "--deny-edit-write",
];
/// The deny-edit-write activation tokens, duplicated from the hook allowlist
/// in `scripts/deny-edit-write.sh` (a Bash `case` line Rust cannot import).
/// `deny_edit_write_tokens_match_the_hook_allowlist` pins set equality.
const DENY_EDIT_WRITE_TOKENS: &[&str] = &[
    "research",
    "audit-umbrella",
    "file-bug",
    "complete-umbrella",
    "debate",
    "triage",
    "umbrella",
];
const SETUP_FLAGS: &[&str] = &[
    "--skip-preflight",
    "--skip-branch-check",
    "--skip-repo-check",
    "--check-reviewers",
    "--skip-codex-probe",
    "--skip-cursor-probe",
];
const CALLER_ENV_KEYS: &[&str] = &[
    "REPO",
    "REPO_ROOT",
    "REPO_UNAVAILABLE",
    "CLAUDE_BINARY_FOUND",
    "CODEX_BINARY_FOUND",
    "CURSOR_BINARY_FOUND",
    "LARCH_TOKEN_SESSION_ID",
    "LARCH_CLAUDE_SOURCE_FILE",
    "LARCH_TIMING_LEDGER",
    "PREV_IMPLEMENT_TMPDIR",
    "LARCH_DYNAMIC_ARCHETYPES_MAX",
];
const TMP_FALLBACK: &str = "/tmp";
const TEST_PAUSE_AFTER_CREATION: &str = "LARCH_TEST_SESSION_SETUP_PAUSE_AFTER_CREATION";
const TEST_FAIL_AFTER_CREATION: &str = "LARCH_TEST_SESSION_SETUP_FAIL_AFTER_CREATION";
const TEST_PAUSE_BEFORE_PUBLICATION: &str = "LARCH_TEST_SESSION_SETUP_PAUSE_BEFORE_PUBLICATION";
const TEST_PUBLICATION_PAUSE_MARKER: &str = ".larch-session-setup-publication-paused";
const TEST_PAUSE_DURING_STDOUT_WRITE: &str = "LARCH_TEST_SESSION_SETUP_PAUSE_DURING_STDOUT_WRITE";
const TEST_PAUSE_DURING_STDOUT_FLUSH: &str = "LARCH_TEST_SESSION_SETUP_PAUSE_DURING_STDOUT_FLUSH";
const TEST_STDOUT_WRITE_PAUSE_MARKER: &str = ".larch-session-setup-write-paused";
const TEST_STDOUT_FLUSH_PAUSE_MARKER: &str = ".larch-session-setup-flush-paused";
const TEST_PAUSE_AFTER_TRANSFER: &str = "LARCH_TEST_SESSION_SETUP_PAUSE_AFTER_TRANSFER";
const TEST_TRANSFER_PAUSE_MARKER: &str = ".larch-session-setup-transfer-paused";
const TEST_PAUSE_INTERVAL: Duration = Duration::from_millis(10);

/// Set up one session and emit its legacy KEY=value envelope.
pub fn setup(arguments: &[OsString]) -> ExitCode {
    let parsed = parse_with_flags(arguments, SETUP_OPTIONS, SETUP_FLAGS, 0);
    if let Some(error) = parsed.error() {
        return usage_error(SETUP_USAGE, "session setup", &error, 4);
    }
    let prefix = text(parsed.value("--prefix"));
    if prefix.is_empty() {
        eprintln!("session-setup.sh: --prefix is required");
        return ExitCode::from(4);
    }
    // Fail closed before any work: a typo must not silently skip enforcement.
    let deny_edit_write = text(parsed.value("--deny-edit-write"));
    if !deny_edit_write.is_empty() && !DENY_EDIT_WRITE_TOKENS.contains(&deny_edit_write.as_str()) {
        return usage_error(
            SETUP_USAGE,
            "session setup",
            &format!("argument --deny-edit-write: invalid choice: '{deny_edit_write}'"),
            4,
        );
    }
    let options = SetupOptions {
        prefix,
        deny_edit_write,
        preflight: PreflightOptions {
            skip: parsed.flag("--skip-preflight"),
            skip_branch_check: parsed.flag("--skip-branch-check"),
        },
        skip_repo_check: parsed.flag("--skip-repo-check"),
        reviewers: ReviewerOptions {
            check: parsed.flag("--check-reviewers"),
            skip_codex_probe: parsed.flag("--skip-codex-probe"),
            skip_cursor_probe: parsed.flag("--skip-cursor-probe"),
        },
        write_session_env: text(parsed.value("--write-session-env")),
        caller_env: text(parsed.value("--caller-env")),
    };
    let transfer = SetupTransfer::new();
    let listener = match SetupSignalListener::install(transfer.clone()) {
        Ok(listener) => listener,
        Err(message) => {
            eprintln!("session-setup.sh: {message}");
            return ExitCode::FAILURE;
        }
    };
    match run_setup(&options, listener.cancellation()) {
        Ok(pending) => emit_setup(pending, listener.cancellation(), &transfer),
        Err(failure) => emit_setup_failure(failure),
    }
}

/// Set up one skipped-preflight session for an in-process composer that owns stdout.
#[must_use]
pub fn setup_for_composer(prefix: &str) -> (u8, String, String) {
    let options = SetupOptions {
        prefix: prefix.to_owned(),
        deny_edit_write: String::new(),
        preflight: PreflightOptions {
            skip: true,
            skip_branch_check: true,
        },
        skip_repo_check: true,
        reviewers: ReviewerOptions {
            check: false,
            skip_codex_probe: false,
            skip_cursor_probe: false,
        },
        write_session_env: String::new(),
        caller_env: String::new(),
    };
    let transfer = SetupTransfer::new();
    let listener = match SetupSignalListener::install(transfer.clone()) {
        Ok(listener) => listener,
        Err(message) => {
            return (1, String::new(), format!("session-setup.sh: {message}\n"));
        }
    };
    match run_setup(&options, listener.cancellation()) {
        Ok(pending) => captured_setup_success(pending, listener.cancellation(), &transfer),
        Err(failure) => (failure.exit_code, failure.stdout, failure.stderr),
    }
}

fn captured_setup_success(
    pending: PendingSetup,
    cancellation: &Cancellation,
    transfer: &SetupTransfer,
) -> (u8, String, String) {
    let PendingSetup { result, session } = pending;
    if let Err(failure) = test_setup_before_publication(&session, cancellation) {
        let failure = session.discard(failure);
        return (failure.exit_code, failure.stdout, failure.stderr);
    }
    if let Err(failure) = check_setup_cancellation(cancellation) {
        let failure = session.discard(failure);
        return (failure.exit_code, failure.stdout, failure.stderr);
    }
    let mut stdout = Vec::new();
    if let Err(error) = write_setup_envelope(&result, &mut stdout) {
        let failure = session.discard(SetupFailure {
            exit_code: 1,
            stdout: String::new(),
            stderr: format!("session-setup.sh: failed to publish session setup: {error}\n"),
        });
        return (failure.exit_code, failure.stdout, failure.stderr);
    }
    if transfer.is_cancelled() {
        let failure = session.discard(cancelled_setup_failure());
        return (failure.exit_code, failure.stdout, failure.stderr);
    }
    if let Err(failure) = transfer.transfer() {
        let failure = session.discard(failure);
        return (failure.exit_code, failure.stdout, failure.stderr);
    }
    test_setup_after_transfer(&session, cancellation);
    if let Err(failure) = session.commit_after_publication() {
        // Publication already happened into `stdout`; keep that envelope so the
        // in-process composer can preserve SESSION_TMPDIR the same way a
        // subprocess capture of the CLI would.
        return (
            failure.exit_code,
            String::from_utf8_lossy(&stdout).into_owned(),
            failure.stderr,
        );
    }
    let stdout = String::from_utf8_lossy(&stdout).into_owned();
    let mut stderr = String::new();
    for diagnostic in &result.diagnostics {
        stderr.push_str(diagnostic);
        stderr.push('\n');
    }
    (result.exit_code, stdout, stderr)
}

#[derive(Clone, Debug)]
struct SetupOptions {
    prefix: String,
    deny_edit_write: String,
    preflight: PreflightOptions,
    skip_repo_check: bool,
    reviewers: ReviewerOptions,
    write_session_env: String,
    caller_env: String,
}

#[derive(Clone, Debug)]
struct PreflightOptions {
    skip: bool,
    skip_branch_check: bool,
}

#[derive(Clone, Debug)]
struct ReviewerOptions {
    check: bool,
    skip_codex_probe: bool,
    skip_cursor_probe: bool,
}

#[derive(Clone, Debug)]
struct SetupFailure {
    exit_code: u8,
    stdout: String,
    stderr: String,
}

#[derive(Clone, Debug)]
struct SetupResult {
    stdout: Vec<(String, String)>,
    notices: Vec<String>,
    diagnostics: Vec<String>,
    exit_code: u8,
}

/// A complete setup result whose session directory remains privately owned.
///
/// The caller receives the directory only after [`emit_setup`] writes and
/// flushes the full legacy stdout envelope. Dropping this value before then
/// closes the owned temporary directory.
struct PendingSetup {
    result: SetupResult,
    session: PendingSessionDirectory,
}

const TRANSFER_PENDING: u8 = 0;
const TRANSFER_CANCELLED: u8 = 1;
const TRANSFERRED: u8 = 2;

/// One linearization point for cancellation and session ownership transfer.
///
/// Signals race this state transition rather than a best-effort cancellation
/// check. The winner decides whether the flushed stdout envelope transfers the
/// directory or its private owner removes it.
#[derive(Clone)]
struct SetupTransfer {
    state: Arc<AtomicU8>,
}

impl SetupTransfer {
    fn new() -> Self {
        Self {
            state: Arc::new(AtomicU8::new(TRANSFER_PENDING)),
        }
    }

    fn cancel(&self) {
        let _ignored = self.state.compare_exchange(
            TRANSFER_PENDING,
            TRANSFER_CANCELLED,
            Ordering::AcqRel,
            Ordering::Acquire,
        );
    }

    fn is_cancelled(&self) -> bool {
        self.state.load(Ordering::Acquire) == TRANSFER_CANCELLED
    }

    fn transfer(&self) -> Result<(), SetupFailure> {
        match self.state.compare_exchange(
            TRANSFER_PENDING,
            TRANSFERRED,
            Ordering::AcqRel,
            Ordering::Acquire,
        ) {
            Ok(_) => Ok(()),
            Err(TRANSFER_CANCELLED) => Err(cancelled_setup_failure()),
            Err(_) => Err(SetupFailure {
                exit_code: 1,
                stdout: String::new(),
                stderr: "session-setup.sh: session ownership transfer was already finalized\n"
                    .to_owned(),
            }),
        }
    }
}

/// A private setup directory before its stdout envelope can be published.
///
/// `SecureTempDir` retains cleanup ownership until the full stdout envelope is
/// written and flushed. This gives ordinary errors and catchable shutdown
/// signals one uniform cleanup path.
struct PendingSessionDirectory {
    directory: SecureTempDir,
    root: TemporaryRoot,
    id: String,
    cache_warning: Option<String>,
}

impl PendingSessionDirectory {
    fn path(&self) -> &Path {
        self.directory.path()
    }

    fn id(&self) -> &str {
        &self.id
    }

    fn cache_warning(&self) -> Option<&str> {
        self.cache_warning.as_deref()
    }

    /// Close an unpublished directory and retain any cleanup diagnostic.
    fn discard(self, failure: SetupFailure) -> SetupFailure {
        let Self { directory, .. } = self;
        cleanup_owned_session_directory(directory, failure)
    }

    /// Transfer a successfully published session directory to its caller.
    ///
    /// This runs only after the entire stdout envelope is flushed. Cancellation
    /// is deliberately not checked here: after publication, a caller may safely
    /// use the emitted directory and a late signal must not retract it.
    fn commit_after_publication(self) -> Result<(), SetupFailure> {
        write_session_keepalive(self.path(), &self.id);
        let path = self.directory.keep().map_err(|error| SetupFailure {
            exit_code: 1,
            stdout: String::new(),
            stderr: format!(
                "session-setup.sh: failed to persist session temp directory: {error}\n"
            ),
        })?;
        let marker_commit = commit_uncommitted_session_setup(&self.root, &path);
        if let Err(error) = marker_commit {
            let failure = SetupFailure {
                exit_code: 1,
                stdout: String::new(),
                stderr: format!("session-setup.sh: failed to commit session setup: {error}\n"),
            };
            return Err(cleanup_persisted_pending_session(
                &self.root, &path, failure,
            ));
        }
        Ok(())
    }
}

#[derive(Clone, Debug)]
struct ReviewerStatus {
    codex_present: String,
    cursor_present: String,
    claude_binary_found: String,
    codex_binary_found: String,
    cursor_binary_found: String,
}

/// Process-local shutdown listener for the uncommitted setup window.
///
/// The listener is installed before any directory exists and holds the Tokio
/// runtime that services the signal streams. Once setup flushes its full
/// envelope and reaches the commit point, normal process completion owns the
/// directory and this listener is dropped without changing the committed result.
struct SetupSignalListener {
    _runtime: LarchRuntime,
    cancellation: Cancellation,
    task: tokio::task::JoinHandle<()>,
}

impl SetupSignalListener {
    fn install(transfer: SetupTransfer) -> Result<Self, String> {
        let runtime = LarchRuntime::new()
            .map_err(|error| format!("failed to install setup cancellation listener: {error}"))?;
        let cancellation = Cancellation::new();
        let (ready_sender, ready_receiver) = tokio::sync::oneshot::channel();
        let signal_cancellation = cancellation.clone();
        let task = runtime.spawn(async move {
            listen_for_setup_shutdown(&signal_cancellation, &transfer, ready_sender).await;
        });
        let ready = runtime.block_on(async move {
            ready_receiver
                .await
                .map_err(|_error| "setup cancellation listener exited before readiness".to_owned())
        })?;
        ready?;
        Ok(Self {
            _runtime: runtime,
            cancellation,
            task,
        })
    }

    const fn cancellation(&self) -> &Cancellation {
        &self.cancellation
    }
}

impl Drop for SetupSignalListener {
    fn drop(&mut self) {
        self.task.abort();
    }
}

async fn listen_for_setup_shutdown(
    cancellation: &Cancellation,
    transfer: &SetupTransfer,
    ready_sender: tokio::sync::oneshot::Sender<Result<(), String>>,
) {
    #[cfg(unix)]
    {
        let mut interrupt =
            match tokio::signal::unix::signal(tokio::signal::unix::SignalKind::interrupt()) {
                Ok(signal) => signal,
                Err(error) => {
                    let _ignored = ready_sender.send(Err(error.to_string()));
                    return;
                }
            };
        let mut terminate =
            match tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate()) {
                Ok(signal) => signal,
                Err(error) => {
                    let _ignored = ready_sender.send(Err(error.to_string()));
                    return;
                }
            };
        let _ignored = ready_sender.send(Ok(()));
        tokio::select! {
            signal = interrupt.recv() => {
                if signal.is_none() {
                    return;
                }
            }
            signal = terminate.recv() => {
                if signal.is_none() {
                    return;
                }
            }
        }
        // The compare-and-exchange is the cancellation side of the ownership
        // transfer linearization point. It must win before the broad token is
        // published so a concurrent emitter cannot observe only the token.
        transfer.cancel();
        cancellation.cancel();
    }
    #[cfg(not(unix))]
    {
        let _ignored = ready_sender.send(Ok(()));
        if tokio::signal::ctrl_c().await.is_ok() {
            transfer.cancel();
            cancellation.cancel();
        }
    }
}

fn run_setup(
    options: &SetupOptions,
    cancellation: &Cancellation,
) -> Result<PendingSetup, SetupFailure> {
    // Caller state is untrusted input. Read and validate it before preflight so
    // a malformed handoff cannot cause a Git mutation before setup refuses.
    let caller = read_caller_env(&options.caller_env).map_err(|message| SetupFailure {
        exit_code: 1,
        stdout: String::new(),
        stderr: format!("session-setup.sh: {message}\n"),
    })?;
    check_setup_cancellation(cancellation)?;
    let notices = preflight_notices(options)?;
    check_setup_cancellation(cancellation)?;
    let session = create_session_directory(&options.prefix)?;

    test_setup_after_directory_creation(&session, cancellation)?;
    check_setup_cancellation(cancellation)?;

    if let Some(warning) = session.cache_warning() {
        // The legacy fallback writes this breadcrumb while creating the
        // directory, before the delayed stdout session envelope.
        eprintln!("{warning}");
    }
    let mut stdout = vec![
        ("SESSION_TMPDIR".to_owned(), display_path(session.path())),
        ("SESSION_ID".to_owned(), session.id().to_owned()),
        (
            "LARCH_RENDER_CACHE_DIR".to_owned(),
            display_path(&session.path().join("render-cache")),
        ),
    ];
    let mut diagnostics = Vec::new();
    carry_forward_logs(&caller, session.path());
    check_setup_cancellation(cancellation)?;

    let (repo, repo_unavailable) = if options.skip_repo_check {
        (String::new(), "false".to_owned())
    } else if caller.contains_key("REPO") || caller.contains_key("REPO_UNAVAILABLE") {
        (
            caller.get("REPO").cloned().unwrap_or_default(),
            caller
                .get("REPO_UNAVAILABLE")
                .cloned()
                .unwrap_or_else(|| "false".to_owned()),
        )
    } else {
        let repo = github_repository_resolution::ambient_repo().unwrap_or_default();
        let unavailable = if repo.is_empty() { "true" } else { "false" };
        (repo, unavailable.to_owned())
    };
    check_setup_cancellation(cancellation)?;
    if !options.skip_repo_check {
        stdout.push(("REPO".to_owned(), repo.clone()));
        stdout.push(("REPO_UNAVAILABLE".to_owned(), repo_unavailable.clone()));
    }
    let repo_root = setup_repo_root(&caller);
    stdout.push(("REPO_ROOT".to_owned(), repo_root.clone()));

    let reviewers = append_reviewer_status(options, &caller, &mut stdout, &mut diagnostics);
    check_setup_cancellation(cancellation)?;
    stdout.push((
        "CLAUDE_BINARY_FOUND".to_owned(),
        reviewers.claude_binary_found.clone(),
    ));
    for key in ["LARCH_TOKEN_SESSION_ID", "LARCH_CLAUDE_SOURCE_FILE"] {
        if let Some(value) = caller.get(key).filter(|value| !value.is_empty()) {
            stdout.push((key.to_owned(), value.clone()));
        }
    }

    let exit_code = if options.write_session_env.is_empty() {
        0
    } else {
        let (writer_arguments, mut writer_diagnostics) = write_env_arguments(
            options,
            &caller,
            &repo,
            &repo_root,
            &repo_unavailable,
            &reviewers.codex_present,
            &reviewers.cursor_present,
            &reviewers.claude_binary_found,
            &reviewers.codex_binary_found,
            &reviewers.cursor_binary_found,
        );
        diagnostics.append(&mut writer_diagnostics);
        match session_env_commands::write_env_for_setup(&writer_arguments) {
            Ok(()) => 0,
            Err(message) => {
                diagnostics.push(message);
                1
            }
        }
    };
    check_setup_cancellation(cancellation)?;

    // The sentinel is the last fallible step: a refused setup never leaves
    // one, so the hook cannot stay armed for a session that was never handed
    // to its caller.
    append_deny_edit_write_sentinel(options, &mut stdout)?;

    let result = SetupResult {
        stdout,
        notices,
        diagnostics,
        exit_code,
    };
    // A writer failure is deliberately a publishable envelope (legacy stdout
    // carries SESSION_TMPDIR despite rc=1). The caller takes ownership only
    // after `emit_setup` writes and flushes that envelope.
    Ok(PendingSetup { result, session })
}

fn preflight_notices(options: &SetupOptions) -> Result<Vec<String>, SetupFailure> {
    if options.preflight.skip {
        return Ok(Vec::new());
    }
    let mut arguments = Vec::new();
    if options.preflight.skip_branch_check {
        arguments.push(OsString::from("--skip-branch-check"));
    }
    let preflight = admission_commands::preflight_result(&arguments);
    if preflight.exit_code() != 0 {
        return Err(SetupFailure {
            exit_code: preflight.exit_code(),
            stdout: preflight.combined_output(),
            stderr: String::new(),
        });
    }
    Ok(stale_plugin_notice())
}

fn check_setup_cancellation(cancellation: &Cancellation) -> Result<(), SetupFailure> {
    if cancellation.is_cancelled() {
        return Err(cancelled_setup_failure());
    }
    Ok(())
}

fn cancelled_setup_failure() -> SetupFailure {
    SetupFailure {
        exit_code: 130,
        stdout: String::new(),
        stderr: "session-setup.sh: setup cancelled\n".to_owned(),
    }
}

fn test_setup_after_directory_creation(
    _session: &PendingSessionDirectory,
    cancellation: &Cancellation,
) -> Result<(), SetupFailure> {
    if env::var(TEST_FAIL_AFTER_CREATION).as_deref() == Ok("true") {
        return Err(SetupFailure {
            exit_code: 1,
            stdout: String::new(),
            stderr: "session-setup.sh: test-induced post-creation failure\n".to_owned(),
        });
    }
    if env::var(TEST_PAUSE_AFTER_CREATION).as_deref() == Ok("true") {
        // The uncommitted marker already exists, so the integration harness can
        // observe this exact lifecycle window without a second public wire file.
        while !cancellation.is_cancelled() {
            thread::sleep(TEST_PAUSE_INTERVAL);
        }
        return check_setup_cancellation(cancellation);
    }
    Ok(())
}

/// Pause immediately before stdout publication for real-process recovery tests.
///
/// The private marker lets the integration harness distinguish this boundary
/// from the earlier post-creation window without creating a public wire file.
fn test_setup_before_publication(
    session: &PendingSessionDirectory,
    cancellation: &Cancellation,
) -> Result<(), SetupFailure> {
    check_setup_cancellation(cancellation)?;
    if env::var(TEST_PAUSE_BEFORE_PUBLICATION).as_deref() != Ok("true") {
        return Ok(());
    }
    write_confined_file(
        &session.path().join(TEST_PUBLICATION_PAUSE_MARKER),
        "paused\n",
        0o600,
        "session setup publication test marker",
    )
    .map_err(|error| SetupFailure {
        exit_code: 1,
        stdout: String::new(),
        stderr: format!("session-setup.sh: failed to pause before publication: {error}\n"),
    })?;
    while !cancellation.is_cancelled() {
        thread::sleep(TEST_PAUSE_INTERVAL);
    }
    check_setup_cancellation(cancellation)
}

fn cleanup_persisted_pending_session(
    root: &TemporaryRoot,
    path: &Path,
    mut failure: SetupFailure,
) -> SetupFailure {
    let cleanup = root
        .confine(path, larch_adapters::PathIntent::Cleanup)
        .map_err(|error| error.to_string())
        .and_then(|confined| {
            confined.revalidate().map_err(|error| error.to_string())?;
            larch_adapters::remove_session_tmpdir(confined.path())
        });
    if let Err(error) = cleanup {
        failure
            .stderr
            .push_str("session-setup.sh: failed to clean uncommitted session directory: ");
        failure.stderr.push_str(&error);
        failure.stderr.push('\n');
    }
    failure
}

fn create_session_directory(prefix: &str) -> Result<PendingSessionDirectory, SetupFailure> {
    let (handle, root, cache_warning) =
        make_session_tmpdir(prefix).map_err(|message| SetupFailure {
            exit_code: 1,
            stdout: String::new(),
            stderr: format!("session-setup.sh: {message}\n"),
        })?;
    let owner = match setup_owner_identity() {
        Ok(owner) => owner,
        Err(message) => {
            return Err(cleanup_owned_session_directory(
                handle,
                SetupFailure {
                    exit_code: 1,
                    stdout: String::new(),
                    stderr: format!("session-setup.sh: {message}\n"),
                },
            ));
        }
    };
    if let Err(error) = write_uncommitted_session_setup_marker(&root, handle.path(), &owner) {
        return Err(cleanup_owned_session_directory(
            handle,
            SetupFailure {
                exit_code: 1,
                stdout: String::new(),
                stderr: format!(
                    "session-setup.sh: failed to mark uncommitted session setup: {error}\n"
                ),
            },
        ));
    }
    let id = match write_session_identity(handle.path()) {
        Ok(id) => id,
        Err(message) => {
            return Err(cleanup_owned_session_directory(
                handle,
                SetupFailure {
                    exit_code: 1,
                    stdout: String::new(),
                    stderr: format!("session-setup.sh: {message}\n"),
                },
            ));
        }
    };
    Ok(PendingSessionDirectory {
        directory: handle,
        root,
        id,
        cache_warning,
    })
}

/// Capture a stable-enough identity for the process that owns an unpublished
/// setup directory. A marker without its kernel birth identity would conflate
/// a same-second reused PID with the original setup owner during crash recovery.
fn setup_owner_identity() -> Result<SessionSetupOwner, String> {
    let pid = std::process::id();
    let process_id = i32::try_from(pid)
        .map_err(|_error| "failed to record session setup owner: invalid process ID".to_owned())?;
    let host = SystemProcessIdentityHost::new();
    let identity = read_process_identity(&host, process_id, "")
        .ok_or_else(|| "failed to record session setup owner identity".to_owned())?;
    let birth_identity = identity
        .birth_identity
        .ok_or_else(|| "failed to record session setup owner birth identity".to_owned())?;
    SessionSetupOwner::new(pid, &identity.start_time, birth_identity)
        .ok_or_else(|| "failed to record session setup owner identity".to_owned())
}

fn cleanup_owned_session_directory(
    directory: SecureTempDir,
    mut failure: SetupFailure,
) -> SetupFailure {
    if let Err(error) = directory.close() {
        failure
            .stderr
            .push_str("session-setup.sh: failed to clean uncommitted session directory: ");
        failure.stderr.push_str(&error.to_string());
        failure.stderr.push('\n');
    }
    failure
}

fn append_reviewer_status(
    options: &SetupOptions,
    caller: &BTreeMap<String, String>,
    stdout: &mut Vec<(String, String)>,
    diagnostics: &mut Vec<String>,
) -> ReviewerStatus {
    let mut status = ReviewerStatus {
        codex_present: String::new(),
        cursor_present: String::new(),
        claude_binary_found: bool_value(caller.get("CLAUDE_BINARY_FOUND")),
        codex_binary_found: bool_value(caller.get("CODEX_BINARY_FOUND")),
        cursor_binary_found: bool_value(caller.get("CURSOR_BINARY_FOUND")),
    };
    if status.claude_binary_found.is_empty() {
        status.claude_binary_found = path_binary_found("claude");
    }
    if options.reviewers.check {
        let reviewer_environment = reviewer_environment();
        match agent_commands::check_reviewers_with_environment(
            options.reviewers.skip_codex_probe,
            options.reviewers.skip_cursor_probe,
            &reviewer_environment,
        ) {
            Ok(result) => {
                status.codex_present = bool_text(result.codex_present());
                status.cursor_present = bool_text(result.cursor_present());
                status.codex_binary_found = bool_text(result.codex_binary_found());
                status.cursor_binary_found = bool_text(result.cursor_binary_found());
                append_nonempty_reviewer_rows(stdout, &status, true);
            }
            Err(message) => diagnostics.push(message),
        }
    } else {
        if status.codex_binary_found.is_empty() {
            status.codex_binary_found = bool_value(caller.get("CODEX_PRESENT"));
        }
        if status.cursor_binary_found.is_empty() {
            status.cursor_binary_found = bool_value(caller.get("CURSOR_PRESENT"));
        }
        append_nonempty_reviewer_rows(stdout, &status, false);
    }
    status
}

fn append_nonempty_reviewer_rows(
    stdout: &mut Vec<(String, String)>,
    status: &ReviewerStatus,
    include_presence: bool,
) {
    let rows = if include_presence {
        vec![
            ("CODEX_PRESENT", &status.codex_present),
            ("CURSOR_PRESENT", &status.cursor_present),
            ("CODEX_BINARY_FOUND", &status.codex_binary_found),
            ("CURSOR_BINARY_FOUND", &status.cursor_binary_found),
        ]
    } else {
        vec![
            ("CODEX_BINARY_FOUND", &status.codex_binary_found),
            ("CURSOR_BINARY_FOUND", &status.cursor_binary_found),
        ]
    };
    for (key, value) in rows {
        if !value.is_empty() {
            stdout.push((key.to_owned(), value.clone()));
        }
    }
}

fn emit_setup(
    pending: PendingSetup,
    cancellation: &Cancellation,
    transfer: &SetupTransfer,
) -> ExitCode {
    let PendingSetup { result, session } = pending;
    if let Err(failure) = test_setup_before_publication(&session, cancellation) {
        return emit_setup_failure(session.discard(failure));
    }
    if let Err(failure) = check_setup_cancellation(cancellation) {
        return emit_setup_failure(session.discard(failure));
    }
    let publication = {
        let stdout = io::stdout();
        let mut stdout = stdout.lock();
        let mut writer = SetupPublicationWriter::new(&mut stdout, &session, cancellation);
        write_setup_envelope(&result, &mut writer)
    };
    if transfer.is_cancelled() {
        return emit_setup_failure(session.discard(cancelled_setup_failure()));
    }
    if let Err(error) = publication {
        return emit_setup_failure(session.discard(SetupFailure {
            exit_code: 1,
            stdout: String::new(),
            stderr: format!("session-setup.sh: failed to publish session setup: {error}\n"),
        }));
    }
    if let Err(failure) = transfer.transfer() {
        return emit_setup_failure(session.discard(failure));
    }
    test_setup_after_transfer(&session, cancellation);
    if let Err(failure) = session.commit_after_publication() {
        return emit_setup_failure(failure);
    }
    for diagnostic in result.diagnostics {
        write_setup_stderr(&format!("{diagnostic}\n"));
    }
    ExitCode::from(result.exit_code)
}

/// Pause after ownership has transferred so the signal tests can prove a late
/// signal cannot retract a fully published session. This is test-only and no
/// fallible work is allowed to turn that transferred state back into cleanup.
fn test_setup_after_transfer(session: &PendingSessionDirectory, cancellation: &Cancellation) {
    if env::var(TEST_PAUSE_AFTER_TRANSFER).as_deref() != Ok("true") {
        return;
    }
    let marker = session.path().join(TEST_TRANSFER_PAUSE_MARKER);
    if write_confined_file(
        &marker,
        "paused\n",
        0o600,
        "session setup transfer test marker",
    )
    .is_err()
    {
        return;
    }
    while !cancellation.is_cancelled() {
        thread::sleep(TEST_PAUSE_INTERVAL);
    }
}

/// Writer wrapper that exposes deterministic test barriers inside the actual
/// `Write` and `flush` calls used for stdout publication.
struct SetupPublicationWriter<'a, W> {
    inner: &'a mut W,
    session: &'a PendingSessionDirectory,
    cancellation: &'a Cancellation,
    write_barrier_seen: bool,
    flush_barrier_seen: bool,
}

impl<'a, W> SetupPublicationWriter<'a, W> {
    const fn new(
        inner: &'a mut W,
        session: &'a PendingSessionDirectory,
        cancellation: &'a Cancellation,
    ) -> Self {
        Self {
            inner,
            session,
            cancellation,
            write_barrier_seen: false,
            flush_barrier_seen: false,
        }
    }

    fn pause(&self, enabled: &str, marker: &str, boundary: &str) -> io::Result<()> {
        if env::var(enabled).as_deref() != Ok("true") {
            return Ok(());
        }
        write_confined_file(
            &self.session.path().join(marker),
            "paused\n",
            0o600,
            "session setup publication test marker",
        )
        .map_err(io::Error::other)?;
        while !self.cancellation.is_cancelled() {
            thread::sleep(TEST_PAUSE_INTERVAL);
        }
        Err(io::Error::other(
            // `write_all` retries `Interrupted`, which would cross this
            // deterministic cancellation boundary and publish the envelope.
            format!("session setup cancelled during stdout {boundary}"),
        ))
    }
}

impl<W: io::Write> io::Write for SetupPublicationWriter<'_, W> {
    fn write(&mut self, buffer: &[u8]) -> io::Result<usize> {
        if !self.write_barrier_seen {
            self.write_barrier_seen = true;
            self.pause(
                TEST_PAUSE_DURING_STDOUT_WRITE,
                TEST_STDOUT_WRITE_PAUSE_MARKER,
                "write",
            )?;
        }
        self.inner.write(buffer)
    }

    fn flush(&mut self) -> io::Result<()> {
        if !self.flush_barrier_seen {
            self.flush_barrier_seen = true;
            self.pause(
                TEST_PAUSE_DURING_STDOUT_FLUSH,
                TEST_STDOUT_FLUSH_PAUSE_MARKER,
                "flush",
            )?;
        }
        self.inner.flush()
    }
}

/// Write and flush the exact legacy stdout envelope before transferring state.
fn write_setup_envelope(result: &SetupResult, writer: &mut impl io::Write) -> io::Result<()> {
    let mut envelope = Vec::new();
    for notice in &result.notices {
        envelope.extend_from_slice(notice.as_bytes());
        envelope.push(b'\n');
    }
    for (key, value) in &result.stdout {
        envelope.extend_from_slice(key.as_bytes());
        envelope.push(b'=');
        envelope.extend_from_slice(value.as_bytes());
        envelope.push(b'\n');
    }
    writer.write_all(&envelope)?;
    writer.flush()
}

/// Emit a setup failure without panicking when its stdout destination is gone.
fn emit_setup_failure(failure: SetupFailure) -> ExitCode {
    let SetupFailure {
        exit_code,
        stdout,
        stderr,
    } = failure;
    if !stdout.is_empty() {
        let publication = {
            let handle = io::stdout();
            let mut handle = handle.lock();
            handle
                .write_all(stdout.as_bytes())
                .and_then(|()| handle.flush())
        };
        if let Err(error) = publication {
            write_setup_stderr(&format!(
                "session-setup.sh: failed to publish setup failure: {error}\n"
            ));
        }
    }
    if !stderr.is_empty() {
        write_setup_stderr(&stderr);
    }
    ExitCode::from(exit_code)
}

/// Stderr is diagnostic-only, so an unavailable destination must not panic.
fn write_setup_stderr(message: &str) {
    let stderr = io::stderr();
    let mut stderr = stderr.lock();
    let _ignored = stderr.write_all(message.as_bytes());
    let _ignored = stderr.flush();
}

fn read_caller_env(path: &str) -> Result<BTreeMap<String, String>, String> {
    let path = Path::new(path);
    if path.as_os_str().is_empty() || !path.is_file() {
        return Ok(BTreeMap::new());
    }
    read_kv_raw(path)
        .map_err(|error| error.to_string())
        .map(|rows| {
            rows.into_iter()
                .filter(|(key, value)| CALLER_ENV_KEYS.contains(&key.as_str()) && !value.is_empty())
                .collect()
        })
}

fn make_session_tmpdir(
    prefix: &str,
) -> Result<(SecureTempDir, TemporaryRoot, Option<String>), String> {
    let clone_tag = env::current_dir()
        .ok()
        .and_then(|path| {
            path.file_name()
                .map(|name| name.to_string_lossy().into_owned())
        })
        .map_or_else(|| "_".to_owned(), |name| sanitize_clone_tag(&name));
    let template = format!("{prefix}-{clone_tag}-");
    let cache_root = cleanup_cache_sessions_root(
        env::var_os("XDG_CACHE_HOME").as_deref(),
        env::var_os("HOME").as_deref(),
    );
    match create_session_tmpdir(&cache_root, &template) {
        Ok((directory, root)) => Ok((directory, root, None)),
        Err(error) if error.kind() == PathSafetyErrorKind::InvalidTempPrefix => {
            Err(format!("failed to create session temp directory: {error}"))
        }
        Err(_cache_error) => {
            let fallback = fs::canonicalize(TMP_FALLBACK)
                .map_err(|error| format!("failed to create session temp directory: {error}"))?;
            let (directory, root) = create_session_tmpdir(&fallback, &template)
                .map_err(|error| format!("failed to create session temp directory: {error}"))?;
            Ok((
                directory,
                root,
                Some(
                    "session-setup.sh: warning: cache session root unavailable, falling back to /tmp"
                        .to_owned(),
                ),
            ))
        }
    }
}

fn create_session_tmpdir(
    root: &Path,
    prefix: &str,
) -> Result<(SecureTempDir, TemporaryRoot), PathSafetyError> {
    ensure_directory_chain(root)?;
    let root = TemporaryRoot::resolve(Some(root))?;
    let directory = SecureTempDir::create(&root, prefix)?;
    Ok((directory, root))
}

fn sanitize_clone_tag(name: &str) -> String {
    let tag: String = name
        .chars()
        .map(|character| {
            if character.is_ascii_alphanumeric() || matches!(character, '_' | '-') {
                character
            } else {
                '_'
            }
        })
        .take(32)
        .collect();
    if tag.is_empty() { "_".to_owned() } else { tag }
}

/// Activate the opt-in deny-edit-write sentinel and publish its stdout key.
fn append_deny_edit_write_sentinel(
    options: &SetupOptions,
    stdout: &mut Vec<(String, String)>,
) -> Result<(), SetupFailure> {
    if options.deny_edit_write.is_empty() {
        return Ok(());
    }
    let sentinel =
        activate_deny_edit_write_sentinel(&options.deny_edit_write).map_err(|message| {
            SetupFailure {
                exit_code: 1,
                stdout: String::new(),
                stderr: format!("session-setup.sh: {message}\n"),
            }
        })?;
    stdout.push((
        "DENY_EDIT_WRITE_SENTINEL".to_owned(),
        display_path(&sentinel),
    ));
    Ok(())
}

/// Create the scoped deny-edit-write activation sentinel for a validated token.
///
/// The path mirrors `activation_dir()` in `scripts/deny-edit-write.sh`:
/// `$XDG_CACHE_HOME` (else `$HOME/.cache`) plus `larch/deny-edit-write-active`,
/// refusing when both are unset or empty. The hook never consults a `/tmp`
/// fallback root, so writing one there would silently skip enforcement.
fn activate_deny_edit_write_sentinel(token: &str) -> Result<PathBuf, String> {
    activate_named_write_sentinel(token, std::process::id())
}

/// Activate the scoped deny-edit-write sentinel using an explicit owner pid.
pub fn activate_named_write_sentinel(token: &str, pid: u32) -> Result<PathBuf, String> {
    let cache_home = env::var("XDG_CACHE_HOME")
        .ok()
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
        .or_else(|| {
            env::var("HOME")
                .ok()
                .filter(|value| !value.is_empty())
                .map(|home| Path::new(&home).join(".cache"))
        })
        .ok_or_else(|| {
            "failed to activate deny-edit-write sentinel: XDG_CACHE_HOME and HOME are unset"
                .to_owned()
        })?;
    activate_named_write_sentinel_in(&cache_home, token, pid)
}

/// Activate the scoped deny-edit-write sentinel under an explicit cache home.
pub fn activate_named_write_sentinel_in(
    cache_home: &Path,
    token: &str,
    pid: u32,
) -> Result<PathBuf, String> {
    if !DENY_EDIT_WRITE_TOKENS.contains(&token) {
        return Err(format!("invalid deny-edit-write token: {token}"));
    }
    let directory = cache_home.join("larch/deny-edit-write-active");
    ensure_directory_chain(&directory)
        .map_err(|error| format!("failed to activate deny-edit-write sentinel: {error}"))?;
    // The PID suffix is informational only; the hook matches `<token>-*`.
    let sentinel = directory.join(format!("{token}-{pid}"));
    write_confined_file(&sentinel, "", 0o600, "deny-edit-write activation sentinel")
        .map_err(|error| format!("failed to activate deny-edit-write sentinel: {error}"))?;
    Ok(sentinel)
}

fn write_session_identity(tmpdir: &Path) -> Result<String, String> {
    let roots = allowed_session_roots(
        env::var_os("XDG_CACHE_HOME").as_deref(),
        env::var_os("HOME").as_deref(),
    );
    let session_id = write_session_id(&tmpdir.join("session-id"), &roots)
        .map(|outcome| outcome.session_id().to_owned())?;
    Ok(session_id)
}

fn write_session_keepalive(tmpdir: &Path, session_id: &str) {
    let clone_path = env::current_dir().unwrap_or_default();
    let keepalive = format!(
        "# larch session identity (hook routing)\nCLONE_PATH={}\nSESSION_ID={session_id}\n",
        clone_path.display()
    );
    // The legacy keepalive write is warn-only.  Its absence only disables the
    // hook's session routing; it must not turn a created session into a failed
    // setup after the durable identity has been published.
    if write_confined_file(
        &tmpdir.join(".larch-keepalive"),
        &keepalive,
        0o600,
        "session keepalive",
    )
    .is_err()
    {
        eprintln!(
            "session-setup.sh: warning: failed to write session identity: {}",
            tmpdir.join(".larch-keepalive").display()
        );
    }
}

fn carry_forward_logs(caller: &BTreeMap<String, String>, tmpdir: &Path) {
    let Some(previous) = caller.get("PREV_IMPLEMENT_TMPDIR") else {
        return;
    };
    let source = Path::new(previous).join("larch-logs");
    if source.is_dir() {
        let _ignored = copy_logs_tree(&source, &tmpdir.join("larch-logs"));
    }
}

fn copy_logs_tree(source: &Path, destination: &Path) -> io::Result<()> {
    fs::create_dir_all(destination)?;
    for entry in fs::read_dir(source)? {
        let entry = entry?;
        let name = entry.file_name();
        if is_placeholder_run_dir(&name) {
            continue;
        }
        let source_path = entry.path();
        let destination_path = destination.join(name);
        let metadata = fs::symlink_metadata(&source_path)?;
        if metadata.is_dir() && !metadata.file_type().is_symlink() {
            copy_logs_tree(&source_path, &destination_path)?;
        } else if metadata.is_file() && !metadata.file_type().is_symlink() {
            let _copied = fs::copy(source_path, destination_path)?;
        }
    }
    Ok(())
}

fn is_placeholder_run_dir(name: &std::ffi::OsStr) -> bool {
    let Some(name) = name.to_str() else {
        return false;
    };
    name.strip_prefix("run-").is_some_and(|suffix| {
        !suffix.is_empty() && suffix.bytes().all(|byte| byte.is_ascii_digit())
    })
}

fn setup_repo_root(caller: &BTreeMap<String, String>) -> String {
    let fallback = display_path(&env::current_dir().unwrap_or_default());
    for candidate in [
        caller.get("REPO_ROOT").map(String::as_str),
        env::var("CLAUDE_PROJECT_DIR").ok().as_deref(),
        env::var("REPO_ROOT").ok().as_deref(),
    ] {
        let value = candidate.unwrap_or_default().trim();
        if !value.is_empty() && validate_repo_root_value(value, "--repo-root").is_ok() {
            return value.to_owned();
        }
    }
    fallback
}

fn reviewer_environment() -> BTreeMap<String, String> {
    let mut values: BTreeMap<String, String> = env::vars().collect();
    for (target, option) in [
        ("LARCH_CURSOR_MODEL", "CLAUDE_PLUGIN_OPTION_CURSOR_MODEL"),
        ("LARCH_CODEX_MODEL", "CLAUDE_PLUGIN_OPTION_CODEX_MODEL"),
    ] {
        if values.get(target).is_none_or(String::is_empty)
            && let Some(value) = values
                .get(option)
                .filter(|value| !value.is_empty())
                .cloned()
        {
            values.insert(target.to_owned(), value);
        }
    }
    values
}

#[allow(clippy::too_many_arguments)]
fn write_env_arguments(
    options: &SetupOptions,
    caller: &BTreeMap<String, String>,
    repo: &str,
    repo_root: &str,
    repo_unavailable: &str,
    codex_present: &str,
    cursor_present: &str,
    claude_binary_found: &str,
    codex_binary_found: &str,
    cursor_binary_found: &str,
) -> (Vec<OsString>, Vec<String>) {
    let mut arguments = vec![
        OsString::from("--output"),
        OsString::from(&options.write_session_env),
        OsString::from("--repo-unavailable"),
        OsString::from(repo_unavailable),
        OsString::from("--forked-target"),
        OsString::from("false"),
    ];
    for (flag, value) in [
        ("--repo", repo),
        ("--repo-root", repo_root),
        ("--codex-present", codex_present),
        ("--cursor-present", cursor_present),
        ("--claude-binary-found", claude_binary_found),
        ("--codex-binary-found", codex_binary_found),
        ("--cursor-binary-found", cursor_binary_found),
        (
            "--token-session-id",
            caller
                .get("LARCH_TOKEN_SESSION_ID")
                .map_or("", String::as_str),
        ),
        (
            "--claude-source-file",
            caller
                .get("LARCH_CLAUDE_SOURCE_FILE")
                .map_or("", String::as_str),
        ),
    ] {
        if !value.is_empty() {
            arguments.push(OsString::from(flag));
            arguments.push(OsString::from(value));
        }
    }
    let mut diagnostics = Vec::new();
    let dynamic = caller
        .get("LARCH_DYNAMIC_ARCHETYPES_MAX")
        .map_or("", String::as_str);
    if dynamic == "0" || dynamic == "1" {
        arguments.push(OsString::from("--dynamic-archetypes"));
        arguments.push(OsString::from(dynamic));
    } else if !dynamic.is_empty() {
        diagnostics.push("session-setup.sh: warning: ignoring invalid LARCH_DYNAMIC_ARCHETYPES_MAX from caller-env (must be 0..1)".to_owned());
    }
    let ledger = caller.get("LARCH_TIMING_LEDGER").map_or("", String::as_str);
    if !ledger.is_empty() {
        if safe_timing_ledger(ledger, &options.caller_env) {
            arguments.push(OsString::from("--timing-ledger"));
            arguments.push(OsString::from(ledger));
        } else {
            diagnostics.push("session-setup.sh: warning: ignoring unsafe LARCH_TIMING_LEDGER from caller-env (not under accepted root)".to_owned());
        }
    }
    (arguments, diagnostics)
}

fn safe_timing_ledger(path: &str, caller_env: &str) -> bool {
    if path.is_empty()
        || !path.starts_with('/')
        || path.len() > 512
        || path.contains(['\n', '\r'])
        || !path.bytes().all(|byte| {
            byte.is_ascii_alphanumeric() || matches!(byte, b'_' | b'.' | b'/' | b'~' | b'+' | b'-')
        })
    {
        return false;
    }
    let caller_root = Path::new(caller_env)
        .parent()
        .and_then(|parent| parent.canonicalize().ok())
        .map_or_else(String::new, |path| display_path(&path));
    [
        env::var("TMPDIR").unwrap_or_else(|_| TMP_FALLBACK.to_owned()),
        env::var("IMPLEMENT_TMPDIR").unwrap_or_default(),
        env::var("DESIGN_TMPDIR").unwrap_or_default(),
        env::var("REVIEW_TMPDIR").unwrap_or_default(),
        caller_root,
    ]
    .iter()
    .filter(|root| !root.is_empty())
    .any(|root| path_under(Path::new(path), Path::new(root)))
}

fn stale_plugin_notice() -> Vec<String> {
    let Some(root) = env::var_os("CLAUDE_PLUGIN_ROOT").map(PathBuf::from) else {
        return Vec::new();
    };
    let installed = root.join(".claude-plugin/plugin.json");
    let Ok(cwd) = env::current_dir() else {
        return Vec::new();
    };
    let Ok(repository) = larch_adapters::GixRepository::discover(&cwd) else {
        return Vec::new();
    };
    let Some(worktree) = repository.location().work_dir else {
        return Vec::new();
    };
    let worktree = PathBuf::from(String::from_utf8_lossy(worktree.as_bytes()).into_owned());
    if !worktree.join("skills/implement/SKILL.md").is_file() {
        return Vec::new();
    }
    let working = worktree.join(".claude-plugin/plugin.json");
    let (Ok(installed), Ok(working)) = (plugin_version(&installed), plugin_version(&working))
    else {
        return Vec::new();
    };
    if version_compare(&working, &installed).is_gt() {
        return vec![format!(
            "**⚠ larch: installed plugin version ({installed}) is behind the working tree ({working}). Reinstall or refresh the plugin from this checkout before the next run to pick up the latest fixes. Continuing with the cached version.**"
        )];
    }
    Vec::new()
}

fn plugin_version(path: &Path) -> Result<String, ()> {
    let content = fs::read_to_string(path).map_err(|_| ())?;
    serde_json::from_str::<serde_json::Value>(&content)
        .ok()
        .and_then(|value| {
            value
                .get("version")
                .and_then(serde_json::Value::as_str)
                .map(str::to_owned)
        })
        .filter(|value| !value.is_empty())
        .ok_or(())
}

fn version_compare(left: &str, right: &str) -> std::cmp::Ordering {
    let parse = |value: &str| {
        value
            .split('.')
            .take(3)
            .map(|part| part.parse::<i64>().unwrap_or_default())
            .chain(std::iter::repeat(0))
            .take(3)
            .collect::<Vec<_>>()
    };
    parse(left).cmp(&parse(right))
}

fn path_binary_found(name: &str) -> String {
    bool_text(binary_on_path(name, env::var("PATH").ok().as_deref()))
}

fn bool_value(value: Option<&String>) -> String {
    value
        .filter(|value| value.as_str() == "true" || value.as_str() == "false")
        .cloned()
        .unwrap_or_default()
}

fn bool_text(value: bool) -> String {
    if value {
        "true".to_owned()
    } else {
        "false".to_owned()
    }
}

fn display_path(path: &Path) -> String {
    path.to_string_lossy().into_owned()
}

fn text(value: Option<&std::ffi::OsStr>) -> String {
    value
        .map(|value| value.to_string_lossy().into_owned())
        .unwrap_or_default()
}

#[cfg(test)]
mod tests {
    use super::{DENY_EDIT_WRITE_TOKENS, SetupResult, write_setup_envelope};
    use std::io::{self, Write};

    /// G-Cfg-3 deviation guard: the token list lives in a Bash `case` line the
    /// Rust binary cannot import, so pin set equality against the hook source.
    #[test]
    fn deny_edit_write_tokens_match_the_hook_allowlist() {
        let hook = std::fs::read_to_string(
            std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
                .join("../../scripts/deny-edit-write.sh"),
        )
        .expect("read scripts/deny-edit-write.sh");
        let case_line = hook
            .lines()
            .map(str::trim)
            .find(|line| line.ends_with(") ;;") && line.contains('|'))
            .expect("hook token case line");
        let mut hook_tokens: Vec<&str> = case_line.trim_end_matches(") ;;").split('|').collect();
        hook_tokens.sort_unstable();
        let mut rust_tokens: Vec<&str> = DENY_EDIT_WRITE_TOKENS.to_vec();
        rust_tokens.sort_unstable();
        assert_eq!(rust_tokens, hook_tokens);
    }

    fn result() -> SetupResult {
        SetupResult {
            notices: vec!["NOTICE=before".to_owned()],
            stdout: vec![
                ("SESSION_TMPDIR".to_owned(), "/tmp/session".to_owned()),
                ("SESSION_ID".to_owned(), "session-id".to_owned()),
            ],
            diagnostics: Vec::new(),
            exit_code: 0,
        }
    }

    struct WriteFailure;

    impl Write for WriteFailure {
        fn write(&mut self, _buffer: &[u8]) -> io::Result<usize> {
            Err(io::Error::new(
                io::ErrorKind::BrokenPipe,
                "injected write failure",
            ))
        }

        fn flush(&mut self) -> io::Result<()> {
            Ok(())
        }
    }

    struct ShortWriteFailure {
        wrote_prefix: bool,
    }

    impl Write for ShortWriteFailure {
        fn write(&mut self, buffer: &[u8]) -> io::Result<usize> {
            if self.wrote_prefix {
                return Err(io::Error::new(
                    io::ErrorKind::BrokenPipe,
                    "injected write failure after a short write",
                ));
            }
            self.wrote_prefix = true;
            Ok(buffer.len().min(1))
        }

        fn flush(&mut self) -> io::Result<()> {
            Ok(())
        }
    }

    struct FlushFailure {
        bytes: Vec<u8>,
    }

    impl Write for FlushFailure {
        fn write(&mut self, buffer: &[u8]) -> io::Result<usize> {
            self.bytes.extend_from_slice(buffer);
            Ok(buffer.len())
        }

        fn flush(&mut self) -> io::Result<()> {
            Err(io::Error::new(
                io::ErrorKind::BrokenPipe,
                "injected flush failure",
            ))
        }
    }

    #[test]
    fn setup_envelope_preserves_legacy_bytes_before_flushing() {
        let mut output = Vec::new();

        write_setup_envelope(&result(), &mut output).expect("write envelope");

        assert_eq!(
            output,
            b"NOTICE=before\nSESSION_TMPDIR=/tmp/session\nSESSION_ID=session-id\n"
        );
    }

    #[test]
    fn setup_envelope_propagates_an_injected_write_failure() {
        let error = write_setup_envelope(&result(), &mut WriteFailure)
            .expect_err("injected write failure must be controlled");

        assert_eq!(error.kind(), io::ErrorKind::BrokenPipe);
    }

    #[test]
    fn setup_envelope_propagates_an_injected_short_write_failure() {
        let error = write_setup_envelope(
            &result(),
            &mut ShortWriteFailure {
                wrote_prefix: false,
            },
        )
        .expect_err("injected short write failure must be controlled");

        assert_eq!(error.kind(), io::ErrorKind::BrokenPipe);
    }

    #[test]
    fn setup_envelope_propagates_an_injected_flush_failure() {
        let mut writer = FlushFailure { bytes: Vec::new() };
        let error = write_setup_envelope(&result(), &mut writer)
            .expect_err("injected flush failure must be controlled");

        assert_eq!(error.kind(), io::ErrorKind::BrokenPipe);
        assert_eq!(
            writer.bytes,
            b"NOTICE=before\nSESSION_TMPDIR=/tmp/session\nSESSION_ID=session-id\n"
        );
    }
}
