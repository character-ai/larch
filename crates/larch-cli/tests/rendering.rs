//! Command-boundary contract for the paths no parity golden can record.
//!
//! Differential parity against the frozen Python owner lives in
//! `tests/parity.rs`. These assertions cover the three refusals where the
//! retired Python owner exited on an uncaught traceback, whose absolute paths
//! and line numbers make a byte-exact golden impossible, plus the bounded
//! `--width` this leaf added so an absurd width cannot exhaust memory.

use std::{fs, process::Command};

use tempfile::TempDir;

fn run(arguments: &[&str]) -> std::process::Output {
    Command::new(env!("CARGO_BIN_EXE_larch"))
        .args(arguments)
        .output()
        .expect("rendering command runs")
}

fn stderr(output: &std::process::Output) -> String {
    String::from_utf8_lossy(&output.stderr).into_owned()
}

#[test]
fn render_chart_reports_a_missing_path_at_the_traceback_exit_code() {
    let directory = TempDir::new().expect("sandbox");
    let absent = directory.path().join("absent.tsv");
    let output = run(&[
        "analyze-issues",
        "render-chart",
        absent.to_str().expect("path"),
    ]);

    assert_eq!(output.status.code(), Some(1));
    assert_eq!(
        stderr(&output),
        format!(
            "ERROR: [Errno 2] No such file or directory: '{}'\n",
            absent.display()
        )
    );
}

#[test]
fn render_chart_refuses_non_utf8_input() {
    let directory = TempDir::new().expect("sandbox");
    let path = directory.path().join("growth.tsv");
    fs::write(&path, b"key\tlabel\tb\nA\tBug\xff\t1\n").expect("seed");
    let output = run(&[
        "analyze-issues",
        "render-chart",
        path.to_str().expect("path"),
    ]);

    assert_eq!(output.status.code(), Some(1));
    assert_eq!(
        stderr(&output),
        format!("ERROR: cannot decode {} as UTF-8\n", path.display())
    );
}

#[test]
fn render_chart_refuses_a_non_integer_bucket_value() {
    let directory = TempDir::new().expect("sandbox");
    let path = directory.path().join("growth.tsv");
    fs::write(&path, "key\tlabel\tb\nA\tBug\tmany\n").expect("seed");
    let output = run(&[
        "analyze-issues",
        "render-chart",
        path.to_str().expect("path"),
    ]);

    assert_eq!(output.status.code(), Some(1));
    assert_eq!(
        stderr(&output),
        "ERROR: invalid literal for int() with base 10: 'many'\n"
    );
}

#[test]
fn gantt_render_refuses_a_width_past_the_bound() {
    let directory = TempDir::new().expect("sandbox");
    let rows = directory.path().join("rows.tsv");
    fs::write(&rows, "a\t0\t5\n").expect("seed");
    let output = run(&[
        "gantt",
        "render",
        "--window-start-s",
        "0",
        "--window-end-s",
        "10",
        "--rows-tsv",
        rows.to_str().expect("path"),
        "--width",
        "10001",
    ]);

    assert_eq!(output.status.code(), Some(2));
    assert_eq!(stderr(&output), "ERROR: --width must be at most 10000\n");
}

#[test]
fn gantt_render_refuses_a_window_bound_outside_the_integer_range() {
    let directory = TempDir::new().expect("sandbox");
    let rows = directory.path().join("rows.tsv");
    fs::write(&rows, "a\t0\t5\n").expect("seed");
    let output = run(&[
        "gantt",
        "render",
        "--window-start-s",
        "99999999999999999999999",
        "--window-end-s",
        "10",
        "--rows-tsv",
        rows.to_str().expect("path"),
    ]);

    assert_eq!(output.status.code(), Some(2));
    assert!(
        stderr(&output).ends_with(
            "error: argument --window-start-s: invalid int value: '99999999999999999999999'\n"
        ),
        "{}",
        stderr(&output)
    );
}
