#[path = "support/parity.rs"]
#[allow(dead_code)]
mod parity_support;

use parity_support::{NormalizationRule, ParityCase, Program, SeedFile, assert_case};
use std::{
    env,
    path::{Path, PathBuf},
    process::Command,
};

fn fixture_directory() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../fixtures/rust-parity")
        .canonicalize()
        .expect("canonical parity fixture directory")
}

fn secret_fixture_input(include_log_only_families: bool) -> String {
    const COMMAND_FAMILIES: &[&str] = &[
        "anthropic-openai-key",
        "github-token",
        "aws-akia",
        "jwt",
        "pem-private-key",
        "cursor-api-key",
    ];
    let source = fixture_directory()
        .join("../rust-redaction/secret-families.tsv")
        .canonicalize()
        .expect("canonical secret-family fixture");
    let text = std::fs::read_to_string(source).expect("read secret-family fixture");
    let mut input = String::new();
    for line in text.lines().filter(|line| !line.starts_with('#')) {
        let mut fields = line.splitn(3, '\t');
        let family = fields.next().expect("secret family");
        let prefix = fields.next().expect("secret prefix");
        let suffix = fields.next().expect("secret suffix");
        if include_log_only_families || COMMAND_FAMILIES.contains(&family) {
            if family == "pem-private-key" {
                input.push_str(prefix);
                input.push_str(suffix);
                input.push('\n');
                input.push_str("private body\n-----END RSA PRIVATE KEY-----\n");
            } else {
                input.push_str(family);
                input.push_str(": ");
                input.push_str(prefix);
                input.push_str(suffix);
                input.push('\n');
            }
        }
    }
    input
}

fn python_executable() -> PathBuf {
    let output = Command::new("python3")
        .args(["-c", "import sys; print(sys.executable)"])
        .output()
        .expect("resolve python3 executable");
    assert!(output.status.success(), "python3 executable probe failed");
    PathBuf::from(
        String::from_utf8(output.stdout)
            .expect("python path is UTF-8")
            .trim(),
    )
    .canonicalize()
    .expect("canonical python3 executable")
}

fn programs(verb: &str, arguments: &[&str], stdin: Option<&[u8]>) -> (Program, Program) {
    let reference = fixture_directory().join("redact_reference.py");
    let mut python_arguments = vec![reference.to_string_lossy().into_owned(), verb.to_owned()];
    python_arguments.extend(arguments.iter().map(|argument| (*argument).to_owned()));
    let mut rust_arguments = vec![String::from("redact"), verb.to_owned()];
    rust_arguments.extend(arguments.iter().map(|argument| (*argument).to_owned()));
    let mut python = Program::new(python_executable()).args(python_arguments);
    let mut rust = Program::new(env!("CARGO_BIN_EXE_larch")).args(rust_arguments);
    if let Some(input) = stdin {
        python = python.stdin(input);
        rust = rust.stdin(input);
    }
    (python, rust)
}

fn case(
    name: &'static str,
    verb: &str,
    arguments: &[&str],
    stdin: Option<&[u8]>,
    seed_files: Vec<SeedFile>,
    side_effects: &[&str],
) -> ParityCase {
    let (python, rust) = programs(verb, arguments, stdin);
    ParityCase {
        name,
        python,
        rust,
        seed_files,
        side_effect_records: side_effects.iter().map(PathBuf::from).collect(),
        normalization: vec![NormalizationRule::SandboxRoot],
    }
}

fn stream_cases() -> Vec<ParityCase> {
    let secret_input = secret_fixture_input(false);
    let open_pem = ["before\n-----BEGIN ", "PRIVATE KEY-----\nbody\n"].concat();
    vec![
        case(
            "redact-secrets-all-families",
            "secrets",
            &[],
            Some(secret_input.as_bytes()),
            Vec::new(),
            &[],
        ),
        case(
            "redact-secrets-adds-final-newline",
            "secrets",
            &[],
            Some(b"ordinary text"),
            Vec::new(),
            &[],
        ),
        case(
            "redact-secrets-streaming-continuation",
            "secrets",
            &["--streaming", "--state-file", "{sandbox}/state.env"],
            Some(b"body\n-----END PRIVATE KEY-----\nafter sk-abcdefghijklmnopqrstuvwxyz"),
            vec![SeedFile::text("state.env", "prefix-in_pem=1-suffix\n")],
            &["state.env"],
        ),
        case(
            "redact-secrets-streaming-open-pem",
            "secrets",
            &["--streaming", "--state-file", "{sandbox}/state.env"],
            Some(open_pem.as_bytes()),
            Vec::new(),
            &["state.env"],
        ),
        case(
            "redact-secrets-missing-state-value",
            "secrets",
            &["--state-file"],
            None,
            Vec::new(),
            &[],
        ),
        case(
            "redact-tmpdir-paths",
            "tmpdir-paths",
            &[],
            Some(b"/tmp/larch-design-session/result /Users/alice/project/file"),
            Vec::new(),
            &[],
        ),
        case(
            "redact-tmpdir-paths-unknown-option",
            "tmpdir-paths",
            &["--help"],
            None,
            Vec::new(),
            &[],
        ),
    ]
}

fn scrub_cases() -> Vec<ParityCase> {
    let log_secret_input = secret_fixture_input(true);
    let surviving_pem = [
        "prefix -----BEGIN RSA ",
        "PRIVATE KEY-----\nbody\n-----END RSA PRIVATE KEY-----\n",
    ]
    .concat();
    vec![
        case(
            "redact-scrub-log-secrets",
            "scrub-log-secrets",
            &["--log-root", "{sandbox}/logs"],
            None,
            vec![
                SeedFile::text("logs/a.txt", &log_secret_input),
                SeedFile::text("logs/clean.txt", "ordinary text\n"),
            ],
            &["logs/a.txt", "logs/clean.txt"],
        ),
        case(
            "redact-scrub-log-missing-directory",
            "scrub-log-secrets",
            &["{sandbox}/missing"],
            None,
            Vec::new(),
            &[],
        ),
        case(
            "redact-scrub-log-surviving-pem-marker",
            "scrub-log-secrets",
            &["{sandbox}/logs"],
            None,
            vec![SeedFile::text("logs/a.txt", &surviving_pem)],
            &["logs/a.txt"],
        ),
        case(
            "redact-scrub-submodule-paths",
            "scrub-submodule-paths",
            &[
                "--input",
                "{sandbox}/findings.md",
                "--output",
                "{sandbox}/out/findings.md",
                "--log",
                "{sandbox}/audit/removed.txt",
            ],
            None,
            vec![
                SeedFile::text(
                    ".gitmodules",
                    "[submodule \"lib\"]\n\tpath = vendor/libfoo\n",
                ),
                SeedFile::text(
                    "findings.md",
                    concat!(
                        "préamble 😀\n",
                        "### FINDING_1: keep\n- **Location**: src/main.rs:2\nbody\n",
                        "### FINDING_2: drop\n- **Location**: vendor/libfoo:12\nbody\n",
                        "### OOS_3: retain\nmentions vendor/live/file.rs\n",
                    ),
                ),
                SeedFile::executable_text(".bin/git", "#!/bin/sh\nprintf '%s\\n' 'vendor/live'\n"),
            ],
            &["out/findings.md", "audit/removed.txt"],
        ),
        case(
            "redact-scrub-submodule-incomplete-option",
            "scrub-submodule-paths",
            &["--input"],
            None,
            Vec::new(),
            &[],
        ),
        case(
            "redact-scrub-submodule-missing-input",
            "scrub-submodule-paths",
            &[
                "--input",
                "{sandbox}/missing.md",
                "--output",
                "{sandbox}/out.md",
                "--log",
                "{sandbox}/audit.txt",
            ],
            None,
            Vec::new(),
            &[],
        ),
    ]
}

fn cases() -> Vec<ParityCase> {
    stream_cases().into_iter().chain(scrub_cases()).collect()
}

#[test]
fn migrated_redact_commands_match_frozen_python() {
    let goldens = fixture_directory().join("goldens");
    for case in cases() {
        let golden = goldens.join(format!("{}.golden.json", case.name));
        assert_case(&case, &golden).unwrap_or_else(|error| panic!("{error}"));
    }
}
