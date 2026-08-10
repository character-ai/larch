//! `session setup` compatibility, isolation, and publication coverage.
//!
//! The old Python owner minted random directory suffixes and UUIDs. The stdout
//! assertions therefore normalize only those two entropy-bearing values, then
//! compare every remaining byte and line order against the frozen wire contract.

use std::{
    collections::BTreeMap,
    fs,
    path::{Path, PathBuf},
    process::{Command, Output},
    thread,
};

use larch_core::{KvDocument, ParseOptions};
use tempfile::TempDir;

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
    let mut command = Command::new(env!("CARGO_BIN_EXE_larch"));
    command
        .args(["session", "setup"])
        .args(arguments)
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
        .env_remove("REVIEW_TMPDIR");
    for (key, value) in environment {
        command.env(key, value);
    }
    command.output().expect("run session setup")
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
