//! Command-boundary contract for `run-log render-session-transcript`.
//!
//! The rendering itself is covered by the differential parity tests in
//! `larch-core`. These assertions pin what a caller branches on: the `argparse`
//! usage and help text the retired Python owner printed, the exit code for each
//! refusal, and the two output destinations.

use std::{fs, path::Path, process::Command};

use tempfile::TempDir;

const HELP: &str = "usage: cli.py [-h] --input INPUT [--output OUTPUT]\n\nrender-session-transcript.py \u{2014} render a Claude Code session JSONL as a\nfiltered chat-view JSONL.\n\noptions:\n  -h, --help       show this help message and exit\n  --input INPUT    Path to raw Claude Code session JSONL\n  --output OUTPUT  Path to write filtered JSONL (default: stdout)\n";
const USAGE: &str = "usage: cli.py [-h] --input INPUT [--output OUTPUT]\n";
const RECORD: &str = "{\"type\":\"user\",\"message\":{\"role\":\"user\",\"content\":\"hello\"}}\n";
const RENDERED: &str = concat!(
    "{\"v\":3,\"source_basename\":\"raw.jsonl\",\"turns\":1,\"policy\":\"prose-errors-and-reference-reads\"}\n",
    "{\"turn\":1,\"role\":\"user\",\"blocks\":[{\"type\":\"text\",\"value\":\"hello\"}]}\n"
);

fn render(arguments: &[&Path]) -> std::process::Output {
    let mut command = Command::new(env!("CARGO_BIN_EXE_larch"));
    command.args(["run-log", "render-session-transcript"]);
    for argument in arguments {
        command.arg(argument);
    }
    command.output().expect("render command runs")
}

fn seed(directory: &TempDir, name: &str, body: &str) -> std::path::PathBuf {
    let path = directory.path().join(name);
    fs::write(&path, body).expect("seed input");
    path
}

#[test]
fn help_prints_the_recorded_argparse_text() {
    let output = render(&[Path::new("--help")]);
    assert!(output.status.success());
    assert_eq!(String::from_utf8_lossy(&output.stdout), HELP);
}

#[test]
fn a_missing_required_option_refuses_with_the_argparse_exit_code() {
    let output = render(&[]);
    assert_eq!(output.status.code(), Some(2));
    assert_eq!(
        String::from_utf8_lossy(&output.stderr),
        format!("{USAGE}cli.py: error: the following arguments are required: --input\n")
    );
}

#[test]
fn an_unrecognized_option_refuses_with_the_argparse_exit_code() {
    let directory = TempDir::new().expect("temp directory");
    let input = seed(&directory, "raw.jsonl", RECORD);
    let output = render(&[Path::new("--input"), &input, Path::new("--bogus")]);
    assert_eq!(output.status.code(), Some(2));
    assert_eq!(
        String::from_utf8_lossy(&output.stderr),
        format!("{USAGE}cli.py: error: unrecognized arguments: --bogus\n")
    );
}

#[test]
fn a_rendered_transcript_reaches_stdout_and_an_output_file_alike() {
    let directory = TempDir::new().expect("temp directory");
    let input = seed(&directory, "raw.jsonl", RECORD);
    let streamed = render(&[Path::new("--input"), &input]);
    assert!(streamed.status.success());
    assert_eq!(String::from_utf8_lossy(&streamed.stdout), RENDERED);
    assert!(streamed.stderr.is_empty());

    let destination = directory.path().join("session-transcript.jsonl");
    let written = render(&[
        Path::new("--input"),
        &input,
        Path::new("--output"),
        &destination,
    ]);
    assert!(written.status.success());
    assert!(written.stdout.is_empty());
    assert_eq!(fs::read_to_string(&destination).expect("output"), RENDERED);
}

#[test]
fn every_refusal_carries_the_exit_code_its_callers_branch_on() {
    let directory = TempDir::new().expect("temp directory");
    let absent = directory.path().join("absent.jsonl");
    let missing = render(&[Path::new("--input"), &absent]);
    assert_eq!(missing.status.code(), Some(2));
    assert_eq!(
        String::from_utf8_lossy(&missing.stderr),
        format!(
            "render-session-transcript: input missing: {}\n",
            absent.display()
        )
    );

    let empty = seed(&directory, "empty.jsonl", "\n{not json\n");
    let no_records = render(&[Path::new("--input"), &empty]);
    assert_eq!(no_records.status.code(), Some(3));
    assert_eq!(
        String::from_utf8_lossy(&no_records.stderr),
        format!(
            "render-session-transcript: no parseable records in {}\n",
            empty.display()
        )
    );
}

#[test]
fn replaced_bytes_are_reported_on_stderr_without_failing_the_render() {
    let directory = TempDir::new().expect("temp directory");
    let path = directory.path().join("raw.jsonl");
    let mut body = vec![0xff, b'\n'];
    body.extend_from_slice(RECORD.as_bytes());
    fs::write(&path, body).expect("seed invalid bytes");
    let output = render(&[Path::new("--input"), &path]);
    assert!(output.status.success());
    assert_eq!(String::from_utf8_lossy(&output.stdout), RENDERED);
    assert_eq!(
        String::from_utf8_lossy(&output.stderr),
        "render-session-transcript: replaced invalid UTF-8 bytes in 1 record(s)\n"
    );
}
