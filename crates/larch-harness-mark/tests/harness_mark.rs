use std::{
    process::{Command, Output},
    time::{SystemTime, UNIX_EPOCH},
};

fn run(arguments: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_larch-harness-mark"))
        .args(arguments)
        .output()
        .expect("harness wrapper should launch")
}

fn stdout(output: &Output) -> String {
    String::from_utf8_lossy(&output.stdout).into_owned()
}

fn stderr(output: &Output) -> String {
    String::from_utf8_lossy(&output.stderr).into_owned()
}

#[test]
fn wrapper_preserves_child_streams_exit_status_and_timing_row() {
    let output = run(&[
        "--label",
        "unit",
        "--",
        "/bin/sh",
        "-c",
        "printf child-out; printf child-err >&2; exit 7",
    ]);
    assert_eq!(output.status.code(), Some(7), "{}", stderr(&output));
    assert!(stdout(&output).contains("child-out"), "{}", stdout(&output));
    assert!(stderr(&output).contains("child-err"), "{}", stderr(&output));
    assert!(
        stdout(&output).contains("LARCH_HARNESS_TIMING\tunit\t"),
        "{}",
        stdout(&output)
    );
}

#[test]
fn wrapper_emits_a_pre_child_bootstrap_diagnostic() {
    let start_ns = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("system clock should follow Unix epoch")
        .as_nanos()
        .to_string();
    let output = Command::new(env!("CARGO_BIN_EXE_larch-harness-mark"))
        .env("LARCH_HARNESS_BOOTSTRAP_START_NS", start_ns)
        .env("LARCH_HARNESS_BOOTSTRAP_KIND", "cold")
        .args(["--label", "bootstrap", "--", "/bin/sh", "-c", "printf ok"])
        .output()
        .expect("harness wrapper should launch");
    assert!(output.status.success(), "{}", stderr(&output));
    let stdout = stdout(&output);
    let bootstrap = stdout
        .find("LARCH_HARNESS_BOOTSTRAP\tbootstrap\tcold\t")
        .expect("bootstrap diagnostic should be present");
    let child = stdout.find("ok").expect("child output should be present");
    let timing = stdout
        .find("LARCH_HARNESS_TIMING\tbootstrap\t")
        .expect("child timing row should be present");
    assert!(bootstrap < child && child < timing, "{stdout}");
}

#[test]
fn wrapper_does_not_leak_bootstrap_metadata_to_the_child() {
    let output = Command::new(env!("CARGO_BIN_EXE_larch-harness-mark"))
        .env("LARCH_HARNESS_BOOTSTRAP_START_NS", "1")
        .env("LARCH_HARNESS_BOOTSTRAP_KIND", "warm")
        .args([
            "--label",
            "environment",
            "--",
            "/bin/sh",
            "-c",
            "test -z \"${LARCH_HARNESS_BOOTSTRAP_START_NS:-}\" && test -z \"${LARCH_HARNESS_BOOTSTRAP_KIND:-}\"",
        ])
        .output()
        .expect("harness wrapper should launch");
    assert!(output.status.success(), "{}", stderr(&output));
}

#[test]
fn wrapper_rejects_a_missing_child_and_reports_missing_programs() {
    let missing_child = run(&["--label", "unit", "--"]);
    assert_eq!(missing_child.status.code(), Some(2));
    assert!(stderr(&missing_child).contains("requires --label <label> -- <command>"));

    let missing_program = run(&["unit", "/larch/no/such/binary"]);
    assert_eq!(missing_program.status.code(), Some(127));
    assert!(
        stdout(&missing_program).contains("LARCH_HARNESS_TIMING\tunit\t"),
        "{}",
        stdout(&missing_program)
    );
}

#[cfg(unix)]
#[test]
fn wrapper_records_a_signal_terminated_child() {
    let output = run(&["signal", "/bin/sh", "-c", "kill -TERM $$"]);
    assert_eq!(output.status.code(), Some(1));
    assert!(
        stdout(&output).contains("LARCH_HARNESS_TIMING\tsignal\t"),
        "{}",
        stdout(&output)
    );
}
