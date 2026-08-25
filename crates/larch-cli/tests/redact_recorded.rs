#[path = "support/recorded.rs"]
#[allow(dead_code)]
mod recorded_support;

use recorded_support::{NormalizationRule, Program, RecordedCase, SeedFile, assert_recorded_case};
use std::{env, path::{Path, PathBuf}};

fn repository_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .expect("canonical repository root")
}

fn fixture_directory() -> PathBuf {
    repository_root().join("fixtures/rust-redaction")
}

fn golden_directory() -> PathBuf {
    repository_root().join("crates/larch-cli/tests/fixtures/recorded/goldens")
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
        .join("secret-families.tsv")
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

fn program(verb: &str, arguments: &[&str], stdin: Option<&[u8]>) -> Program {
    let mut rust_arguments = vec![String::from("redact"), verb.to_owned()];
    rust_arguments.extend(arguments.iter().map(|argument| (*argument).to_owned()));
    let program = Program::new(env!("CARGO_BIN_EXE_larch")).args(rust_arguments);
    match stdin {
        Some(input) => program.stdin(input),
        None => program,
    }
}

fn case(
    name: &'static str,
    verb: &str,
    arguments: &[&str],
    stdin: Option<&[u8]>,
    seed_files: Vec<SeedFile>,
    side_effects: &[&str],
) -> RecordedCase {
    RecordedCase {
        name,
        program: program(verb, arguments, stdin),
        seed_files,
        side_effect_records: side_effects.iter().map(PathBuf::from).collect(),
        normalization: vec![NormalizationRule::SandboxRoot],
    }
}

fn stream_cases() -> Vec<RecordedCase> {
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

fn scrub_cases() -> Vec<RecordedCase> {
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

fn cases() -> Vec<RecordedCase> {
    stream_cases().into_iter().chain(scrub_cases()).collect()
}

#[test]
fn recorded_redaction_contract() {
    let goldens = golden_directory();
    for case in cases() {
        let golden = goldens.join(format!("{}.golden.json", case.name));
        assert_recorded_case(&case, &golden).unwrap_or_else(|error| panic!("{error}"));
    }
}
