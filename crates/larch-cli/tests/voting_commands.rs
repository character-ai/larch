use std::{
    collections::BTreeMap,
    fs,
    path::{Path, PathBuf},
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
    let cases: Vec<Transcript> = serde_json::from_str(include_str!("fixtures/voting-transcripts.json")).expect("valid recorded voting transcripts");
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
            let path = PathBuf::from(substitute(relative, sandbox.path())); let body = fs::read_to_string(if path.is_absolute() { path } else { sandbox.path().join(path) }).unwrap_or_else(|error| panic!("{} file {relative}: {error}", case.name)); assert_eq!(body, substitute(expected, sandbox.path()), "{} file {relative}", case.name);
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
        let _ = fs::remove_dir_all(format!("{}-outside", sandbox.path().display()));
    }
    names.sort_unstable();
    names.dedup();
    #[rustfmt::skip]
    let expected = [
        "accept-finding", "ballot-parse", "classify-result", "code-review-classification-header",
        "compose-tally-record", "degraded-warning", "effective-judges", "false-positive-match",
        "file-line-regex", "findings-classification-header", "is-security-block", "panel-tier",
        "parse-judge-vote", "parse-rate-check", "parse-rate-diag-matches", "parse-rate-retry",
        "reviewer-for-block", "scoreboard", "split-ballot", "tally-vote", "vote-for-id",
        "voter-status-block", "write-tally",
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
        fs::set_permissions(&voter, fs::Permissions::from_mode(0o0)).expect("deny voter read");
        let denied = run(&arguments, sandbox.path(), &environment);
        assert_eq!(denied.status.code(), Some(1)); assert!(denied.stdout.is_empty()); assert!(!denied.stderr.is_empty());
        fs::set_permissions(&voter, original).expect("restore voter permissions");
    }
}

#[test]
fn self_review_write_tally_composes_exact_paired_artifacts() {
    let temporary = TempDir::new().expect("create tally sandbox");
    let sandbox = fs::canonicalize(temporary.path()).expect("canonical tally sandbox");
    let findings = sandbox.join("findings.jsonl");
    let log_root = sandbox.join("larch-logs");
    let output = Command::new(env!("CARGO_BIN_EXE_larch"))
        .args([
            "voting",
            "write-tally",
            "--log-root",
            log_root.to_str().expect("log root"),
            "--skill",
            "implement",
            "--run-id",
            "run-sr",
            "--phase",
            "code-review",
            "--mode",
            "self-review",
            "--rounds",
            "1",
            "--accepted",
            "1",
            "--rejected",
            "1",
            "--self-review-findings-file",
            findings.to_str().expect("findings path"),
        ])
        .output()
        .expect("run write-tally");
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let tally = log_root.join("implement/run-sr/code-review-tally.json");
    assert_eq!(
        fs::read_to_string(tally).expect("read tally"),
        "{\"schema_version\":2,\"phase\":\"code-review\",\"batch\":\"code-review-tally\",\"mode\":\"self-review\",\"rounds\":1,\"accepted_count\":1,\"rejected_count\":1,\"exonerated_count\":0}\n",
    );
    assert_eq!(
        fs::read_to_string(findings).expect("read findings"),
        concat!(
            "{\"id\":\"SELF_REVIEW_ACCEPTED_1\",\"issue_number\":\"0\",\"phase\":\"code-review\",\"outcome\":\"accepted\",\"schema_version\":\"2\",\"reviewer_slots\":[\"self-review\"],\"round_num\":\"1\",\"category\":\"\",\"body_severity\":\"\",\"focus_area\":\"\",\"prose_body\":\"\"}\n",
            "{\"id\":\"SELF_REVIEW_REJECTED_1\",\"issue_number\":\"0\",\"phase\":\"code-review\",\"outcome\":\"rejected\",\"schema_version\":\"2\",\"reviewer_slots\":[\"self-review\"],\"round_num\":\"1\",\"category\":\"\",\"body_severity\":\"\",\"focus_area\":\"\",\"prose_body\":\"\"}\n",
        ),
    );

    let outside = TempDir::new().expect("create outside root");
    let escaped = outside.path().join("escaped.jsonl");
    let arguments = [
        "write-tally",
        "--log-root",
        log_root.to_str().expect("log root"),
        "--skill",
        "implement",
        "--run-id",
        "run-escape",
        "--phase",
        "code-review",
        "--mode",
        "self-review",
        "--accepted",
        "1",
        "--self-review-findings-file",
        escaped.to_str().expect("escape path"),
    ]
    .map(str::to_owned)
    .to_vec();
    let refused = run(&arguments, &sandbox, &BTreeMap::new());
    assert_eq!(refused.status.code(), Some(2));
    assert!(!escaped.exists());
}

#[test]
fn write_tally_preserves_header_warning_and_staging_guards() {
    let temporary = TempDir::new().expect("create tally sandbox");
    let sandbox = fs::canonicalize(temporary.path()).expect("canonical tally sandbox");
    let body = sandbox.join("body.md");
    #[rustfmt::skip]
    fs::write(&body, "# Rejected Findings\n## Accepted Findings\n## Rejected Code Review Findings\n## Voting Tally\n# Code Review Voting Tally\n## Per-finding vote breakdown\n## Reviewer Competition Scoreboard\n## Voter Agreement Scoreboard\n## Voter Severity Scoreboard\n## Foo\n").expect("write tally body");
    let log_root = sandbox.join("larch-logs");
    let arguments = [
        "write-tally",
        "--log-root",
        log_root.to_str().expect("log root"),
        "--skill",
        "implement",
        "--run-id",
        "run-warning",
        "--phase",
        "code-review",
        "--mode",
        "simple",
        "--body-file",
        body.to_str().expect("body path"),
    ]
    .map(str::to_owned)
    .to_vec();
    let output = run(&arguments, &sandbox, &BTreeMap::new());
    assert_eq!(output.status.code(), Some(0));
    assert_eq!(
        output.stderr,
        b"WARNING=code-review body header validation ignored: unrecognized section header: ## Foo\n",
    );
    assert_eq!(
        fs::read_to_string(log_root.join("implement/run-warning/code-review-tally.json"))
            .expect("read tally"),
        "{\"schema_version\":2,\"phase\":\"code-review\",\"batch\":\"code-review-tally\",\"mode\":\"simple\",\"rounds\":0,\"accepted_count\":0,\"rejected_count\":0,\"exonerated_count\":0}\n",
    );
    let unsafe_arguments = [
        "write-tally",
        "--log-root",
        "/larch-logs",
        "--skill",
        "implement",
        "--run-id",
        "unsafe",
        "--phase",
        "code-review",
        "--mode",
        "simple",
    ]
    .map(str::to_owned)
    .to_vec();
    let unsafe_output = run(&unsafe_arguments, &sandbox, &BTreeMap::new());
    assert_eq!(unsafe_output.status.code(), Some(2));
    assert!(
        String::from_utf8_lossy(&unsafe_output.stderr)
            .contains("unsafe write-tally staging parent")
    );
    #[cfg(unix)]
    {
        std::os::unix::fs::symlink(&sandbox, sandbox.join("linked-parent"))
            .expect("create parent link");
        let linked_root = sandbox.join("linked-parent/larch-logs");
        let linked_arguments = [
            "write-tally",
            "--log-root",
            linked_root.to_str().expect("linked root"),
            "--skill",
            "implement",
            "--run-id",
            "linked",
            "--phase",
            "code-review",
            "--mode",
            "simple",
        ]
        .map(str::to_owned)
        .to_vec();
        let linked = run(&linked_arguments, &sandbox, &BTreeMap::new());
        assert_eq!(linked.status.code(), Some(2));
        assert!(String::from_utf8_lossy(&linked.stderr).contains("symlinked ancestors"));
    }
}
