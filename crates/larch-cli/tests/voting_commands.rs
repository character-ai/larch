use std::{
    collections::BTreeMap,
    fs,
    path::Path,
    process::{Command, Output},
};

use serde::Deserialize;
use sha2::{Digest as _, Sha256};
use tempfile::TempDir;
const SANDBOX_TOKEN: &str = "{sandbox}";
#[derive(Deserialize)]
#[rustfmt::skip]
struct Transcript {
    name: String, arguments: Vec<String>, seeds: BTreeMap<String, String>,
    exit_code: i32, stdout: String, stderr: String,
    #[serde(default)] directories: Vec<String>, #[serde(default)] files: BTreeMap<String, String>,
    #[serde(default)] file_contains: BTreeMap<String, Vec<String>>, #[serde(default)] absent_files: Vec<String>,
    #[serde(default)] environment: BTreeMap<String, String>,
}
#[rustfmt::skip]
fn substitute(value: &str, sandbox: &Path) -> String {
    let remove_error = if cfg!(target_os = "macos") { "Operation not permitted (os error 1)" } else { "Is a directory (os error 21)" };
    value.replace(SANDBOX_TOKEN, &sandbox.display().to_string()).replace("{remove-dir-error}", remove_error)
}
fn run(arguments: &[String], sandbox: &Path, environment: &BTreeMap<String, String>) -> Output {
    let mut command = Command::new(env!("CARGO_BIN_EXE_larch"));
    command
        .arg("voting")
        .args(
            arguments
                .iter()
                .map(|argument| substitute(argument, sandbox)),
        )
        .current_dir(sandbox)
        .env_remove("LARCH_QUIET_ACTIVE")
        .env_remove("LARCH_QUIET_PID")
        .env_remove("LARCH_QUIET_DISABLE")
        .env_remove("LARCH_VOTER_JUDGE_ERROR_PARSE_THRESHOLD")
        .env_remove("LARCH_EXECUTION_ISSUES_LOG")
        .env_remove("SESSION_ENV_PATH")
        .env_remove("IMPLEMENT_TMPDIR");
    command.envs(environment);
    command.output().expect("run Rust voting command")
}
#[rustfmt::skip]
#[test]
fn every_migrated_voting_verb_matches_its_recorded_python_transcript() {
    let cases: Vec<Transcript> = serde_json::from_str(include_str!("../../../fixtures/rust-parity/voting-transcripts.json")).expect("valid recorded voting transcripts");
    let mut names = Vec::new();
    for case in cases {
        let sandbox = TempDir::new().expect("create transcript sandbox");
        names.push(case.arguments[0].clone());
        for relative in &case.directories { fs::create_dir_all(sandbox.path().join(relative)).expect("create transcript directory"); }
        for (relative, contents) in &case.seeds {
            fs::write(sandbox.path().join(relative), substitute(contents, sandbox.path())).expect("write transcript seed");
        }
        let output = run(&case.arguments, sandbox.path(), &case.environment);
        assert_eq!(output.status.code(), Some(case.exit_code), "{} exit", case.name);
        assert_eq!(String::from_utf8(output.stdout).expect("UTF-8 stdout"), substitute(&case.stdout, sandbox.path()), "{} stdout", case.name);
        assert_eq!(String::from_utf8(output.stderr).expect("UTF-8 stderr"), substitute(&case.stderr, sandbox.path()), "{} stderr", case.name);
        for (relative, expected) in &case.files {
            let body = fs::read_to_string(sandbox.path().join(relative)).unwrap_or_else(|error| panic!("{} file {relative}: {error}", case.name)); assert_eq!(body, substitute(expected, sandbox.path()), "{} file {relative}", case.name);
        }
        for (relative, expected) in &case.file_contains {
            let body = fs::read_to_string(sandbox.path().join(relative)).expect("read output file");
            for fragment in expected { assert!(body.contains(&substitute(fragment, sandbox.path())), "{} file {relative}", case.name); }
        }
        for relative in &case.absent_files { assert!(!sandbox.path().join(relative).exists(), "{} absent {relative}", case.name); }
        if case.name == "duplicate-ballot-refusal" {
            let blocks = sandbox.path().join("blocks");
            assert!(blocks.is_dir()); assert_eq!(fs::read_dir(blocks).expect("read refused directory").count(), 0);
        }
    }
    names.sort_unstable();
    names.dedup();
    #[rustfmt::skip]
    let expected = [
        "accept-finding", "ballot-parse", "classify-result", "code-review-classification-header",
        "false-positive-match", "file-line-regex", "findings-classification-header", "is-security-block",
        "panel-tier", "parse-judge-vote", "parse-rate-check", "parse-rate-diag-matches",
        "parse-rate-retry", "reviewer-for-block", "split-ballot", "vote-for-id",
    ];
    assert_eq!(names, expected);
}
#[rustfmt::skip]
#[test]
fn non_substantive_parse_rate_writes_a_bounded_matching_diagnostic() {
    let sandbox = TempDir::new().expect("create parse-rate sandbox");
    let ballot = sandbox.path().join("ballot.md");
    let voter = sandbox.path().join("voter.txt");
    fs::write(&ballot, "### FINDING_1: one\n### FINDING_2: two\n").expect("write ballot");
    fs::write(&voter, "X".repeat(1_000)).expect("write voter");
    #[rustfmt::skip]
    let arguments = [
        "parse-rate-check", "--voter-file", voter.to_str().expect("voter path"),
        "--voter-tool", "cursor", "--ballot-file", ballot.to_str().expect("ballot path"),
        "--id-grammar", "finding-only", "--review-tmpdir", sandbox.path().to_str().expect("sandbox path"),
        "--log-mode", "quiet",
    ].map(str::to_owned).to_vec();
    let environment = BTreeMap::new();
    let output = run(&arguments, sandbox.path(), &environment);
    assert_eq!(output.status.code(), Some(0));
    assert_eq!(output.stdout, b"PARSE_RATE_STATUS=NOT_SUBSTANTIVE\n");
    assert!(output.stderr.is_empty());
    let diagnostic = sandbox.path().join("voter-parse-rate-diag.txt");
    let body = fs::read_to_string(&diagnostic).expect("read diagnostic");
    assert!(body.contains("judge_error_count=2\ntotal_findings=2\ntotal_ballot_items=2\n"));
    assert!(body.contains(&format!("voter_sha256={:x}", Sha256::digest("X".repeat(1_000)))));
    assert!(body.contains(&format!("--- first 200 bytes of voter output ---\n{}\n", "X".repeat(200))));
    assert!(!body.contains(&"X".repeat(201)));
    let match_arguments = ["parse-rate-diag-matches", "--voter-file", voter.to_str().expect("voter path")].map(str::to_owned).to_vec();
    assert_eq!(run(&match_arguments, sandbox.path(), &environment).status.code(), Some(0));
    fs::write(&voter, "changed\n").expect("change voter");
    assert_eq!(run(&match_arguments, sandbox.path(), &environment).status.code(), Some(1));
    #[cfg(unix)] {
        use std::os::unix::fs::PermissionsExt as _;
        let original = fs::metadata(&voter).expect("voter metadata").permissions();
        fs::set_permissions(&voter, fs::Permissions::from_mode(0)).expect("deny voter read");
        let denied = run(&arguments, sandbox.path(), &environment);
        assert_eq!(denied.status.code(), Some(1)); assert!(denied.stdout.is_empty()); assert!(!denied.stderr.is_empty());
        fs::set_permissions(&voter, original).expect("restore voter permissions");
    }
}
