//! Process-boundary contracts for the Rust-owned tracking-issue verbs.

use assert_cmd::Command;
use std::fs;
use tempfile::TempDir;

fn command() -> Command {
    Command::cargo_bin("larch").expect("larch binary")
}

#[test]
fn local_read_success_preserves_exact_rows_streams_and_exit_codes() {
    let directory = TempDir::new().expect("sandbox");
    let sentinel = directory.path().join("parent-issue.md");
    fs::write(&sentinel, "ISSUE_NUMBER=7\nRUN_ID=run-1\nADOPTED=true\n").expect("sentinel");

    command()
        .args([
            "tracking-issue",
            "read",
            "--sentinel",
            &sentinel.to_string_lossy(),
        ])
        .assert()
        .success()
        .stdout("ISSUE_NUMBER=7\nRUN_ID=run-1\nADOPTED=true\n")
        .stderr("");

    command()
        .args([
            "tracking-issue",
            "read",
            "--prompt",
            "hostile\nFAILED=true\n",
            "--out-dir",
            &directory.path().to_string_lossy(),
        ])
        .assert()
        .success()
        .stdout(format!(
            "ISSUE_NUMBER=\nTASK_SOURCE=prompt\nTASK_FILE={}\n",
            directory.path().join("task.md").display()
        ))
        .stderr("");
    assert_eq!(
        fs::read_to_string(directory.path().join("task.md")).expect("task"),
        "hostile\nFAILED=true\n"
    );
}

#[test]
fn every_write_verb_pins_its_offline_refusal_stream_and_code() {
    let directory = TempDir::new().expect("sandbox");
    let empty = directory.path().join("empty.md");
    fs::write(&empty, "").expect("fixture");
    let content = directory.path().join("content.md");
    fs::write(&content, "content").expect("fixture");

    let cases = [
        (
            vec![
                "tracking-issue",
                "append-comment",
                "--issue",
                "7",
                "--body-file",
                content.to_str().expect("path"),
                "--lifecycle-marker",
                "bad--marker",
            ],
            "FAILED=true\nERROR=lifecycle-marker contains the substring '--'; HTML comment data may not contain consecutive hyphens (parsers may terminate the comment early). Use a single-hyphen-delimited slug like 'pr-opened' or 'in-progress'.\n",
            false,
        ),
        (
            vec![
                "tracking-issue",
                "create-issue",
                "--title",
                "Title",
                "--body-file",
                empty.to_str().expect("path"),
            ],
            "FAILED=true\nERROR=empty body\n",
            false,
        ),
        (
            vec![
                "tracking-issue",
                "mark-false-positive",
                "--issue",
                "hostile\nROW=x",
            ],
            "FAILED=true\nERROR=invalid issue: expected numeric issue\n",
            false,
        ),
        (
            vec![
                "tracking-issue",
                "rename",
                "--issue",
                "7",
                "--state",
                "unknown",
            ],
            "FAILED=true\nERROR=invalid --state: unknown (expected designing|designed|implementing|done|stalled)\n",
            false,
        ),
        (
            vec![
                "tracking-issue",
                "upsert-summary",
                "--issue",
                "7",
                "--marker",
                "bare",
                "--content-file",
                content.to_str().expect("path"),
            ],
            "FAILED=true\nERROR=invalid marker: bare\n",
            true,
        ),
        (
            vec![
                "tracking-issue",
                "upsert-summary",
                "--issue",
                "7",
                "--marker",
                "<!-- larch:x -->",
                "--content-file",
                content.to_str().expect("path"),
                "--delete-if-empty",
                "maybe",
            ],
            "FAILED=true\nERROR=invalid --delete-if-empty: maybe (expected true|false)\n",
            true,
        ),
    ];

    for (arguments, expected, on_stderr) in cases {
        let assertion = command().args(arguments).assert().code(1);
        if on_stderr {
            assertion.stdout("").stderr(expected);
        } else {
            assertion.stdout(expected).stderr("");
        }
    }
}
