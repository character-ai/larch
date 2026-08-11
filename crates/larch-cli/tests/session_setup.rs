//! `session setup` compatibility, isolation, and publication coverage.
//!
//! The old Python owner minted random directory suffixes and UUIDs. The stdout
//! assertions therefore normalize only those two entropy-bearing values, then
//! compare every remaining byte and line order against the frozen wire contract.

use std::{
    collections::BTreeMap,
    fs,
    path::{Path, PathBuf},
    process::{Child, Command, Output, Stdio},
    thread,
    time::{Duration, Instant},
};

use larch_adapters::UNCOMMITTED_SESSION_SETUP_MARKER;
use larch_core::{KvDocument, ParseOptions};
use tempfile::TempDir;

#[cfg(unix)]
use nix::{
    sys::signal::{Signal, kill},
    unistd::Pid,
};

struct Sandbox {
    _directory: TempDir,
    root: PathBuf,
}

impl Sandbox {
    fn new() -> Self {
        let directory = tempfile::Builder::new()
            .prefix("larch-session-setup-")
            .tempdir_in(real_temporary_root())
            .expect("session setup sandbox");
        let root = directory
            .path()
            .canonicalize()
            .expect("canonical session setup sandbox");
        for relative in ["cache", "home", "tmp"] {
            fs::create_dir_all(root.join(relative)).expect("sandbox directory");
        }
        Self {
            _directory: directory,
            root,
        }
    }

    fn path(&self, relative: &str) -> PathBuf {
        self.root.join(relative)
    }

    fn run(&self, arguments: &[&str]) -> Output {
        run_setup(&self.root, arguments, &[])
    }
}

fn real_temporary_root() -> PathBuf {
    std::env::temp_dir()
        .canonicalize()
        .unwrap_or_else(|_error| std::env::temp_dir())
}

fn run_setup(root: &Path, arguments: &[&str], environment: &[(&str, &str)]) -> Output {
    let mut command = larch_command(root);
    command.args(["session", "setup"]).args(arguments);
    for (key, value) in environment {
        command.env(key, value);
    }
    command.output().expect("run session setup")
}

fn larch_command(root: &Path) -> Command {
    let mut command = Command::new(env!("CARGO_BIN_EXE_larch"));
    command
        .current_dir(root)
        .env("XDG_CACHE_HOME", root.join("cache"))
        .env("HOME", root.join("home"))
        .env("TMPDIR", root.join("tmp"))
        .env("PATH", "")
        .env_remove("CLAUDE_PLUGIN_ROOT")
        .env_remove("CLAUDE_PROJECT_DIR")
        .env_remove("REPO_ROOT")
        .env_remove("IMPLEMENT_TMPDIR")
        .env_remove("DESIGN_TMPDIR")
        .env_remove("REVIEW_TMPDIR")
        .env_remove("LARCH_TEST_SESSION_SETUP_PAUSE_AFTER_CREATION")
        .env_remove("LARCH_TEST_SESSION_SETUP_FAIL_AFTER_CREATION");
    command
}

fn run_cleanup(root: &Path) -> Output {
    larch_command(root)
        .args(["cleanup", "run"])
        .output()
        .expect("run cleanup")
}

fn spawn_paused_setup(root: &Path, prefix: &str) -> Child {
    larch_command(root)
        .args([
            "session",
            "setup",
            "--prefix",
            prefix,
            "--skip-preflight",
            "--skip-repo-check",
        ])
        .env("LARCH_TEST_SESSION_SETUP_PAUSE_AFTER_CREATION", "true")
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("spawn paused session setup")
}

fn wait_for_uncommitted_setup(root: &Path, prefix: &str) -> PathBuf {
    let sessions = root.join("cache/larch/sessions");
    let deadline = Instant::now() + Duration::from_secs(5);
    loop {
        if let Ok(entries) = fs::read_dir(&sessions)
            && let Some(path) = entries.flatten().map(|entry| entry.path()).find(|path| {
                path.file_name()
                    .is_some_and(|name| name.to_string_lossy().starts_with(prefix))
                    && path.join(UNCOMMITTED_SESSION_SETUP_MARKER).is_file()
            })
        {
            return path;
        }
        assert!(
            Instant::now() < deadline,
            "timed out waiting for {prefix} setup to reach its uncommitted window"
        );
        thread::sleep(Duration::from_millis(10));
    }
}

fn assert_no_uncommitted_setup(root: &Path, prefix: &str) {
    let sessions = root.join("cache/larch/sessions");
    let has_unpublished_directory = fs::read_dir(sessions)
        .map(|entries| {
            entries.flatten().any(|entry| {
                entry.file_name().to_string_lossy().starts_with(prefix) && entry.path().is_dir()
            })
        })
        .unwrap_or(false);
    assert!(
        !has_unpublished_directory,
        "unpublished {prefix} session survived"
    );
}

#[cfg(unix)]
fn signal_child(child: &Child, signal: Signal) {
    let process_id = i32::try_from(child.id()).expect("child process ID fits i32");
    kill(Pid::from_raw(process_id), signal).expect("signal paused setup");
}

fn output_text(output: &Output) -> (String, String) {
    (
        String::from_utf8_lossy(&output.stdout).into_owned(),
        String::from_utf8_lossy(&output.stderr).into_owned(),
    )
}

fn session_tmpdir(stdout: &str) -> PathBuf {
    stdout
        .lines()
        .find_map(|line| line.strip_prefix("SESSION_TMPDIR="))
        .map(PathBuf::from)
        .expect("SESSION_TMPDIR")
}

fn session_id(stdout: &str) -> String {
    stdout
        .lines()
        .find_map(|line| line.strip_prefix("SESSION_ID="))
        .map(str::to_owned)
        .expect("SESSION_ID")
}

/// Keep the contract byte-for-byte while replacing only unpredictable values.
fn normalize_stdout(root: &Path, stdout: &str) -> String {
    let root = root.to_string_lossy();
    stdout
        .lines()
        .map(|line| {
            if line.starts_with("SESSION_TMPDIR=") {
                "SESSION_TMPDIR=<SESSION>".to_owned()
            } else if line.starts_with("SESSION_ID=") {
                "SESSION_ID=<SESSION_ID>".to_owned()
            } else if line.starts_with("LARCH_RENDER_CACHE_DIR=") {
                "LARCH_RENDER_CACHE_DIR=<SESSION>/render-cache".to_owned()
            } else {
                line.replace(root.as_ref(), "<SANDBOX>")
            }
        })
        .collect::<Vec<_>>()
        .join("\n")
        + "\n"
}

fn parse_kv(text: &str) -> BTreeMap<String, String> {
    KvDocument::parse(text, ParseOptions::legacy())
        .expect("session setup output uses the legacy KV grammar")
        .select(larch_core::DuplicatePolicy::Last)
}

#[test]
fn setup_stdout_parity_matrix_pins_flag_forms_and_key_order() {
    let cases: &[(&[&str], &str)] = &[
        (
            &[
                "--prefix",
                "matrix",
                "--skip-preflight",
                "--skip-repo-check",
            ],
            concat!(
                "SESSION_TMPDIR=<SESSION>\n",
                "SESSION_ID=<SESSION_ID>\n",
                "LARCH_RENDER_CACHE_DIR=<SESSION>/render-cache\n",
                "REPO_ROOT=<SANDBOX>\n",
                "CLAUDE_BINARY_FOUND=false\n",
            ),
        ),
        (
            &[
                "--prefix=matrix",
                "--skip-preflight",
                "--skip-branch-check",
                "--skip-repo-check",
            ],
            concat!(
                "SESSION_TMPDIR=<SESSION>\n",
                "SESSION_ID=<SESSION_ID>\n",
                "LARCH_RENDER_CACHE_DIR=<SESSION>/render-cache\n",
                "REPO_ROOT=<SANDBOX>\n",
                "CLAUDE_BINARY_FOUND=false\n",
            ),
        ),
        (
            &["--prefix", "matrix", "--skip-preflight"],
            concat!(
                "SESSION_TMPDIR=<SESSION>\n",
                "SESSION_ID=<SESSION_ID>\n",
                "LARCH_RENDER_CACHE_DIR=<SESSION>/render-cache\n",
                "REPO=\n",
                "REPO_UNAVAILABLE=true\n",
                "REPO_ROOT=<SANDBOX>\n",
                "CLAUDE_BINARY_FOUND=false\n",
            ),
        ),
    ];

    for (arguments, expected) in cases {
        let sandbox = Sandbox::new();
        let output = sandbox.run(arguments);
        let (stdout, stderr) = output_text(&output);
        assert!(output.status.success(), "{arguments:?}: {stderr}");
        assert_eq!(
            normalize_stdout(&sandbox.root, &stdout),
            *expected,
            "{arguments:?}"
        );
        assert!(session_tmpdir(&stdout).is_dir(), "{arguments:?}");
    }
}

#[test]
fn setup_rehydrates_caller_state_and_writes_the_rust_owned_session_env() {
    let sandbox = Sandbox::new();
    let caller = sandbox.path("caller/session.env");
    let ledger = sandbox.path("caller/timing.log");
    let ledger_text = ledger.to_string_lossy().replace("/private/tmp/", "/tmp/");
    let output = sandbox.path("cache/larch/sessions/writer/session-env.sh");
    let plugin_root = sandbox.path("plugin-root");
    fs::create_dir_all(caller.parent().expect("caller parent")).expect("caller parent");
    fs::create_dir_all(output.parent().expect("writer parent")).expect("writer parent");
    fs::create_dir_all(&plugin_root).expect("plugin root");
    fs::write(
        &caller,
        format!(
            concat!(
                "REPO=owner/repo\n",
                "REPO_UNAVAILABLE=false\n",
                "REPO_ROOT=/caller/root\n",
                "CLAUDE_BINARY_FOUND=true\n",
                "CODEX_BINARY_FOUND=false\n",
                "CURSOR_BINARY_FOUND=true\n",
                "LARCH_TOKEN_SESSION_ID=token.1\n",
                "LARCH_CLAUDE_SOURCE_FILE=/tmp/source.env\n",
                "LARCH_DYNAMIC_ARCHETYPES_MAX=1\n",
                "LARCH_TIMING_LEDGER={}\n",
            ),
            ledger_text,
        ),
    )
    .expect("caller env");
    let session_env_path = output.to_string_lossy().into_owned();
    let caller_text = caller.to_string_lossy().into_owned();
    let plugin_text = plugin_root.to_string_lossy().into_owned();
    let command = run_setup(
        &sandbox.root,
        &[
            "--prefix",
            "writer",
            "--skip-preflight",
            "--caller-env",
            &caller_text,
            "--write-session-env",
            &session_env_path,
        ],
        &[("CLAUDE_PLUGIN_ROOT", &plugin_text)],
    );
    let (stdout, stderr) = output_text(&command);
    assert!(command.status.success(), "{stderr}");
    assert_eq!(
        normalize_stdout(&sandbox.root, &stdout),
        concat!(
            "SESSION_TMPDIR=<SESSION>\n",
            "SESSION_ID=<SESSION_ID>\n",
            "LARCH_RENDER_CACHE_DIR=<SESSION>/render-cache\n",
            "REPO=owner/repo\n",
            "REPO_UNAVAILABLE=false\n",
            "REPO_ROOT=/caller/root\n",
            "CODEX_BINARY_FOUND=false\n",
            "CURSOR_BINARY_FOUND=true\n",
            "CLAUDE_BINARY_FOUND=true\n",
            "LARCH_TOKEN_SESSION_ID=token.1\n",
            "LARCH_CLAUDE_SOURCE_FILE=/tmp/source.env\n",
        ),
    );
    let values = parse_kv(&fs::read_to_string(&output).expect("session env"));
    assert_eq!(values.get("REPO"), Some(&"owner/repo".to_owned()));
    assert_eq!(values.get("REPO_ROOT"), Some(&"/caller/root".to_owned()));
    assert_eq!(values.get("LARCH_TIMING_LEDGER"), Some(&ledger_text));
    assert_eq!(
        values.get("LARCH_DYNAMIC_ARCHETYPES_MAX"),
        Some(&"1".to_owned())
    );
    assert_eq!(values.get("LARCH_CLAUDE_PLUGIN_ROOT"), Some(&plugin_text));
}

#[test]
fn setup_drops_an_unsafe_caller_ledger_but_keeps_the_other_rehydrated_values() {
    let sandbox = Sandbox::new();
    let caller = sandbox.path("caller.env");
    let output = sandbox.path("cache/larch/sessions/unsafe/session-env.sh");
    fs::create_dir_all(output.parent().expect("writer parent")).expect("writer parent");
    fs::write(
        &caller,
        concat!(
            "REPO=owner/repo\n",
            "REPO_UNAVAILABLE=false\n",
            "LARCH_TIMING_LEDGER=/etc/passwd\n",
            "LARCH_TOKEN_SESSION_ID=parent-session\n",
        ),
    )
    .expect("caller env");
    let caller_text = caller.to_string_lossy().into_owned();
    let session_env_path = output.to_string_lossy().into_owned();
    let command = sandbox.run(&[
        "--prefix",
        "unsafe-ledger",
        "--skip-preflight",
        "--skip-repo-check",
        "--caller-env",
        &caller_text,
        "--write-session-env",
        &session_env_path,
    ]);
    let (stdout, stderr) = output_text(&command);
    assert!(command.status.success(), "{stderr}");
    assert!(stdout.contains("LARCH_TOKEN_SESSION_ID=parent-session\n"));
    assert_eq!(
        stderr,
        "session-setup.sh: warning: ignoring unsafe LARCH_TIMING_LEDGER from caller-env (not under accepted root)\n",
    );
    let values = parse_kv(&fs::read_to_string(output).expect("session env"));
    assert_eq!(values.get("LARCH_TIMING_LEDGER").map(String::as_str), None);
    assert_eq!(
        values.get("LARCH_TOKEN_SESSION_ID").map(String::as_str),
        Some("parent-session")
    );
}

#[test]
fn setup_preserves_a_ledger_at_an_accepted_root_boundary() {
    let sandbox = Sandbox::new();
    let caller = sandbox.path("caller.env");
    let output = sandbox.path("cache/larch/sessions/ledger-boundary/session-env.sh");
    fs::create_dir_all(output.parent().expect("writer parent")).expect("writer parent");
    let ledger = sandbox.path("tmp");
    fs::write(
        &caller,
        format!("LARCH_TIMING_LEDGER={}\n", ledger.display()),
    )
    .expect("caller env");
    let caller_text = caller.to_string_lossy().into_owned();
    let session_env_path = output.to_string_lossy().into_owned();
    let command = sandbox.run(&[
        "--prefix",
        "ledger-boundary",
        "--skip-preflight",
        "--skip-repo-check",
        "--caller-env",
        &caller_text,
        "--write-session-env",
        &session_env_path,
    ]);
    let (_stdout, stderr) = output_text(&command);
    assert!(command.status.success(), "{stderr}");
    let values = parse_kv(&fs::read_to_string(output).expect("session env"));
    assert_eq!(
        values.get("LARCH_TIMING_LEDGER"),
        Some(&ledger.to_string_lossy().into_owned())
    );
}

#[test]
fn setup_preserves_log_carry_forward_and_drops_placeholder_run_directories() {
    let sandbox = Sandbox::new();
    let previous = sandbox.path("previous");
    let uuid_run = "0199F1E2-2238-403D-89F3-F37CA6989999";
    for relative in [
        format!("larch-logs/implement/{uuid_run}"),
        "larch-logs/implement/run-1".to_owned(),
        "larch-logs/shared".to_owned(),
    ] {
        fs::create_dir_all(previous.join(relative)).expect("previous log directory");
    }
    fs::write(
        previous.join(format!("larch-logs/implement/{uuid_run}/manifest.json")),
        "{}",
    )
    .expect("uuid manifest");
    fs::write(
        previous.join("larch-logs/implement/run-1/manifest.json"),
        "{}",
    )
    .expect("placeholder manifest");
    fs::write(previous.join("larch-logs/shared/state.json"), "{}").expect("shared state");
    let caller = sandbox.path("caller.env");
    fs::write(
        &caller,
        format!("PREV_IMPLEMENT_TMPDIR={}\n", previous.display()),
    )
    .expect("caller env");
    let caller_text = caller.to_string_lossy().into_owned();
    let output = sandbox.run(&[
        "--prefix",
        "carry",
        "--skip-preflight",
        "--skip-repo-check",
        "--caller-env",
        &caller_text,
    ]);
    let (stdout, stderr) = output_text(&output);
    assert!(output.status.success(), "{stderr}");
    let carried = session_tmpdir(&stdout).join("larch-logs");
    assert!(
        carried
            .join(format!("implement/{uuid_run}/manifest.json"))
            .is_file()
    );
    assert!(carried.join("shared/state.json").is_file());
    assert!(!carried.join("implement/run-1").exists());
}

#[test]
fn setup_check_reviewers_keeps_presence_before_binary_rows() {
    let sandbox = Sandbox::new();
    let output = sandbox.run(&[
        "--prefix",
        "reviewers",
        "--skip-preflight",
        "--skip-repo-check",
        "--check-reviewers",
        "--skip-codex-probe",
        "--skip-cursor-probe",
    ]);
    let (stdout, stderr) = output_text(&output);
    assert!(output.status.success(), "{stderr}");
    assert_eq!(
        normalize_stdout(&sandbox.root, &stdout),
        concat!(
            "SESSION_TMPDIR=<SESSION>\n",
            "SESSION_ID=<SESSION_ID>\n",
            "LARCH_RENDER_CACHE_DIR=<SESSION>/render-cache\n",
            "REPO_ROOT=<SANDBOX>\n",
            "CODEX_PRESENT=false\n",
            "CURSOR_PRESENT=false\n",
            "CODEX_BINARY_FOUND=false\n",
            "CURSOR_BINARY_FOUND=false\n",
            "CLAUDE_BINARY_FOUND=false\n",
        ),
    );
}

#[test]
fn concurrent_setups_publish_disjoint_session_roots() {
    let sandbox = Sandbox::new();
    let first_root = sandbox.root.clone();
    let second_root = sandbox.root;
    let first = thread::spawn(move || {
        run_setup(
            &first_root,
            &[
                "--prefix",
                "parallel",
                "--skip-preflight",
                "--skip-repo-check",
            ],
            &[],
        )
    });
    let second = thread::spawn(move || {
        run_setup(
            &second_root,
            &[
                "--prefix",
                "parallel",
                "--skip-preflight",
                "--skip-repo-check",
            ],
            &[],
        )
    });
    let first = first.join().expect("first setup");
    let second = second.join().expect("second setup");
    let (first_stdout, first_stderr) = output_text(&first);
    let (second_stdout, second_stderr) = output_text(&second);
    assert!(first.status.success(), "{first_stderr}");
    assert!(second.status.success(), "{second_stderr}");
    let first_dir = session_tmpdir(&first_stdout);
    let second_dir = session_tmpdir(&second_stdout);
    assert_ne!(first_dir, second_dir);
    for (directory, stdout) in [(&first_dir, &first_stdout), (&second_dir, &second_stdout)] {
        assert!(directory.is_dir());
        assert_eq!(
            fs::read_to_string(directory.join("session-id"))
                .expect("session identity")
                .trim(),
            session_id(stdout),
        );
        assert!(directory.join(".larch-keepalive").is_file());
    }
}

#[test]
fn rejected_setup_does_not_create_a_partial_session_directory() {
    let sandbox = Sandbox::new();
    let output = sandbox.run(&["--skip-preflight", "--skip-repo-check"]);
    let (stdout, stderr) = output_text(&output);
    assert_eq!(output.status.code(), Some(4));
    assert!(stdout.is_empty());
    assert_eq!(stderr, "session-setup.sh: --prefix is required\n");
    assert!(!sandbox.path("cache/larch/sessions").exists());
}

#[test]
fn ordinary_post_creation_failure_removes_its_unpublished_session_directory() {
    let sandbox = Sandbox::new();
    let output = run_setup(
        &sandbox.root,
        &[
            "--prefix",
            "post-creation-failure",
            "--skip-preflight",
            "--skip-repo-check",
        ],
        &[("LARCH_TEST_SESSION_SETUP_FAIL_AFTER_CREATION", "true")],
    );
    let (stdout, stderr) = output_text(&output);
    assert_eq!(output.status.code(), Some(1));
    assert!(stdout.is_empty());
    assert_eq!(
        stderr,
        "session-setup.sh: test-induced post-creation failure\n"
    );
    assert_no_uncommitted_setup(&sandbox.root, "post-creation-failure");
}

#[cfg(unix)]
#[test]
fn sigint_and_sigterm_after_directory_creation_remove_unpublished_sessions() {
    for (prefix, signal) in [
        ("cancel-sigint", Signal::SIGINT),
        ("cancel-sigterm", Signal::SIGTERM),
    ] {
        let sandbox = Sandbox::new();
        let child = spawn_paused_setup(&sandbox.root, prefix);
        let directory = wait_for_uncommitted_setup(&sandbox.root, prefix);
        assert!(directory.is_dir());
        assert!(directory.join(UNCOMMITTED_SESSION_SETUP_MARKER).is_file());

        signal_child(&child, signal);
        let output = child.wait_with_output().expect("wait for cancelled setup");
        let (stdout, stderr) = output_text(&output);
        assert_eq!(output.status.code(), Some(130), "{prefix}: {stderr}");
        assert!(stdout.is_empty(), "{prefix}: {stdout}");
        assert_eq!(stderr, "session-setup.sh: setup cancelled\n", "{prefix}");
        assert!(!directory.exists(), "{prefix}");
        assert_no_uncommitted_setup(&sandbox.root, prefix);
    }
}

#[cfg(unix)]
#[test]
fn cleanup_recovers_crashed_uncommitted_setup_without_touching_live_or_committed_siblings() {
    let sandbox = Sandbox::new();
    let completed = sandbox.run(&[
        "--prefix",
        "committed-sibling",
        "--skip-preflight",
        "--skip-repo-check",
    ]);
    let (completed_stdout, completed_stderr) = output_text(&completed);
    assert!(completed.status.success(), "{completed_stderr}");
    let committed_directory = session_tmpdir(&completed_stdout);
    assert!(
        !committed_directory
            .join(UNCOMMITTED_SESSION_SETUP_MARKER)
            .exists()
    );

    let live = spawn_paused_setup(&sandbox.root, "live-sibling");
    let live_directory = wait_for_uncommitted_setup(&sandbox.root, "live-sibling");
    let crashed = spawn_paused_setup(&sandbox.root, "crashed-sibling");
    let crashed_directory = wait_for_uncommitted_setup(&sandbox.root, "crashed-sibling");
    signal_child(&crashed, Signal::SIGKILL);
    let crashed_output = crashed.wait_with_output().expect("wait for killed setup");
    assert!(!crashed_output.status.success());
    assert!(crashed_directory.is_dir());

    let cleanup = run_cleanup(&sandbox.root);
    let (cleanup_stdout, cleanup_stderr) = output_text(&cleanup);
    assert!(cleanup.status.success(), "{cleanup_stderr}");
    assert!(
        cleanup_stdout.contains("CACHE_REMOVED=1\n"),
        "{cleanup_stdout}"
    );
    assert!(!crashed_directory.exists());
    assert!(live_directory.is_dir());
    assert!(
        live_directory
            .join(UNCOMMITTED_SESSION_SETUP_MARKER)
            .is_file()
    );
    assert!(committed_directory.is_dir());

    signal_child(&live, Signal::SIGINT);
    let live_output = live
        .wait_with_output()
        .expect("wait for live setup cancellation");
    assert_eq!(live_output.status.code(), Some(130));
    assert!(!live_directory.exists());
    assert!(committed_directory.is_dir());
}

#[test]
fn malformed_caller_env_aborts_before_session_creation() {
    let sandbox = Sandbox::new();
    let caller = sandbox.path("caller.env");
    fs::write(&caller, b"REPO=owner/repo\r\n").expect("malformed caller env");
    let caller_text = caller.to_string_lossy().into_owned();
    let output = sandbox.run(&[
        "--prefix",
        "malformed-caller",
        "--skip-preflight",
        "--skip-repo-check",
        "--caller-env",
        &caller_text,
    ]);
    let (stdout, stderr) = output_text(&output);
    assert_eq!(output.status.code(), Some(1));
    assert!(stdout.is_empty());
    assert!(stderr.contains("session env file contains carriage return"));
    assert!(!sandbox.path("cache/larch/sessions").exists());
}

#[test]
fn unsafe_setup_prefix_cannot_escape_the_session_root() {
    let sandbox = Sandbox::new();
    let escaped_prefix = format!("{}/outside-", sandbox.root.display());
    let output = sandbox.run(&[
        "--prefix",
        &escaped_prefix,
        "--skip-preflight",
        "--skip-repo-check",
    ]);
    let (stdout, stderr) = output_text(&output);
    assert_eq!(output.status.code(), Some(1));
    assert!(stdout.is_empty());
    assert!(stderr.starts_with("session-setup.sh: failed to create session temp directory:"));
    let escaped = fs::read_dir(&sandbox.root)
        .expect("sandbox entries")
        .filter_map(Result::ok)
        .any(|entry| entry.file_name().to_string_lossy().starts_with("outside-"));
    assert!(
        !escaped,
        "unsafe prefix must not create outside the session root"
    );
}

#[test]
fn setup_reemits_session_writer_failures_as_redacted_breadcrumbs() {
    let sandbox = Sandbox::new();
    let output = sandbox.run(&[
        "--prefix",
        "writer-failure",
        "--skip-preflight",
        "--skip-repo-check",
        "--write-session-env",
        "/etc/larch-session-setup-test.env",
    ]);
    let (stdout, stderr) = output_text(&output);
    assert_eq!(output.status.code(), Some(1));
    assert!(stdout.starts_with("SESSION_TMPDIR="));
    let directory = session_tmpdir(&stdout);
    assert!(directory.is_dir());
    assert!(!directory.join(UNCOMMITTED_SESSION_SETUP_MARKER).exists());
    assert_eq!(
        stderr,
        "ERROR=output path not under allowed session root: /etc/larch-session-setup-test.env\n"
    );
}

#[test]
fn setup_argument_refusals_match_the_legacy_argparse_usage_bytes() {
    let usage = concat!(
        "usage: session setup [--prefix PREFIX] [--skip-preflight]\n",
        "                     [--skip-branch-check] [--skip-repo-check]\n",
        "                     [--check-reviewers] [--skip-codex-probe]\n",
        "                     [--skip-cursor-probe]\n",
        "                     [--write-session-env WRITE_SESSION_ENV]\n",
        "                     [--caller-env CALLER_ENV]",
    );
    for (arguments, error) in [
        (
            vec![
                "--prefix",
                "matrix",
                "--skip-preflight",
                "--skip-repo-check",
                "--bogus",
            ],
            "unrecognized arguments: --bogus",
        ),
        (
            vec!["--prefix", "matrix", "--skip-preflight=true"],
            "argument --skip-preflight: ignored explicit argument 'true'",
        ),
        (
            vec!["--prefix", "--skip-preflight"],
            "argument --prefix: expected one argument",
        ),
    ] {
        let sandbox = Sandbox::new();
        let output = sandbox.run(&arguments);
        let (stdout, stderr) = output_text(&output);
        assert_eq!(output.status.code(), Some(4), "{arguments:?}");
        assert!(stdout.is_empty(), "{arguments:?}");
        assert_eq!(
            stderr,
            format!("{usage}\nsession setup: error: {error}\n"),
            "{arguments:?}"
        );
    }
}
