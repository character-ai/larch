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
    PathSafetyError, PathSafetyErrorKind, SecureTempDir, TemporaryRoot,
    commit_uncommitted_session_setup, ensure_directory_chain, path_under, read_kv_raw,
    runtime::{Cancellation, LarchRuntime},
    write_confined_file, write_session_id, write_uncommitted_session_setup_marker,
};
use larch_core::{
    RepositoryRead, allowed_session_roots, binary_on_path, cleanup_cache_sessions_root,
    validate_repo_root_value,
};
use std::{
    collections::BTreeMap,
    env,
    ffi::OsString,
    fs, io,
    path::{Path, PathBuf},
    process::ExitCode,
    thread,
    time::Duration,
};

const SETUP_USAGE: &str = concat!(
    "usage: session setup [--prefix PREFIX] [--skip-preflight]\n",
    "                     [--skip-branch-check] [--skip-repo-check]\n",
    "                     [--check-reviewers] [--skip-codex-probe]\n",
    "                     [--skip-cursor-probe]\n",
    "                     [--write-session-env WRITE_SESSION_ENV]\n",
    "                     [--caller-env CALLER_ENV]",
);
const SETUP_OPTIONS: &[&str] = &["--prefix", "--write-session-env", "--caller-env"];
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
    let options = SetupOptions {
        prefix,
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
    let listener = match SetupSignalListener::install() {
        Ok(listener) => listener,
        Err(message) => {
            eprintln!("session-setup.sh: {message}");
            return ExitCode::FAILURE;
        }
    };
    match run_setup(&options, listener.cancellation()) {
        Ok(result) => emit_setup(result),
        Err(failure) => {
            print!("{}", failure.stdout);
            eprint!("{}", failure.stderr);
            ExitCode::from(failure.exit_code)
        }
    }
}

#[derive(Clone, Debug)]
struct SetupOptions {
    prefix: String,
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

/// A private setup directory before its stdout envelope can be published.
///
/// `SecureTempDir` retains cleanup ownership until [`Self::commit`] removes
/// the durable uncommitted marker. This gives ordinary errors and catchable
/// shutdown signals one uniform cleanup path.
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

    fn commit(self, cancellation: &Cancellation) -> Result<(), SetupFailure> {
        check_setup_cancellation(cancellation)?;
        write_session_keepalive(self.path(), &self.id);
        check_setup_cancellation(cancellation)?;
        let path = self.directory.keep().map_err(|error| SetupFailure {
            exit_code: 1,
            stdout: String::new(),
            stderr: format!(
                "session-setup.sh: failed to persist session temp directory: {error}\n"
            ),
        })?;
        if let Err(failure) = check_setup_cancellation(cancellation) {
            return Err(cleanup_persisted_pending_session(
                &self.root, &path, failure,
            ));
        }
        if let Err(error) = commit_uncommitted_session_setup(&self.root, &path) {
            let failure = SetupFailure {
                exit_code: 1,
                stdout: String::new(),
                stderr: format!("session-setup.sh: failed to commit session setup: {error}\n"),
            };
            return Err(cleanup_persisted_pending_session(
                &self.root, &path, failure,
            ));
        }
        if let Err(failure) = check_setup_cancellation(cancellation) {
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
/// runtime that services the signal streams. Once setup reaches its commit
/// point, normal process completion owns the directory and this listener is
/// dropped without changing the committed result.
struct SetupSignalListener {
    _runtime: LarchRuntime,
    cancellation: Cancellation,
    task: tokio::task::JoinHandle<()>,
}

impl SetupSignalListener {
    fn install() -> Result<Self, String> {
        let runtime = LarchRuntime::new()
            .map_err(|error| format!("failed to install setup cancellation listener: {error}"))?;
        let cancellation = Cancellation::new();
        let (ready_sender, ready_receiver) = tokio::sync::oneshot::channel();
        let signal_cancellation = cancellation.clone();
        let task = runtime.spawn(async move {
            listen_for_setup_shutdown(&signal_cancellation, ready_sender).await;
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
        cancellation.cancel();
    }
    #[cfg(not(unix))]
    {
        let _ignored = ready_sender.send(Ok(()));
        if tokio::signal::ctrl_c().await.is_ok() {
            cancellation.cancel();
        }
    }
}

fn run_setup(
    options: &SetupOptions,
    cancellation: &Cancellation,
) -> Result<SetupResult, SetupFailure> {
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

    let result = SetupResult {
        stdout,
        notices,
        diagnostics,
        exit_code,
    };
    // This is the only setup commit point. A writer failure is deliberately a
    // published envelope (legacy stdout carries SESSION_TMPDIR despite rc=1),
    // while every earlier error leaves `session` to remove its private tree.
    session.commit(cancellation)?;
    Ok(result)
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
        return Err(SetupFailure {
            exit_code: 130,
            stdout: String::new(),
            stderr: "session-setup.sh: setup cancelled\n".to_owned(),
        });
    }
    Ok(())
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
    if let Err(error) =
        write_uncommitted_session_setup_marker(&root, handle.path(), std::process::id())
    {
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

fn emit_setup(result: SetupResult) -> ExitCode {
    for notice in result.notices {
        println!("{notice}");
    }
    for (key, value) in result.stdout {
        println!("{key}={value}");
    }
    for diagnostic in result.diagnostics {
        eprintln!("{diagnostic}");
    }
    ExitCode::from(result.exit_code)
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
