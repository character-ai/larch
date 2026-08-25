//! Black-box parity coverage for the Rust `implement code-flow-diagram`
//! command (#8933).
//!
//! Each case drives the real binary with `LARCH_TEST_LAUNCH_CLAUDE_SUBPROCESS`
//! pointing at a deterministic stub launcher and pins the
//! `STATUS`/`DIAGRAM_FILE`/`SKIP_REASON` KV stdout grammar, the exit code, and
//! the retry sidecar the retired Python `generate_code_flow_diagram` produced.
//! Retries run with a zeroed delay so the persistent-failure path stays fast.

#![cfg(unix)]

use std::{fs, os::unix::fs::PermissionsExt as _, path::Path};

use assert_cmd::Command as AssertCommand;
use tempfile::TempDir;

/// Write an executable stub launcher and return its path.
fn write_stub(dir: &Path, name: &str, body: &str) -> String {
    let path = dir.join(name);
    fs::write(&path, body).unwrap();
    let mut permissions = fs::metadata(&path).unwrap().permissions();
    permissions.set_mode(0o755);
    fs::set_permissions(&path, permissions).unwrap();
    path.display().to_string()
}

/// Run `implement code-flow-diagram` against `tmpdir` from a non-repository working
/// directory so the changed-file probe is deterministic and offline.
fn run(
    tmpdir: &Path,
    work: &Path,
    launcher: &str,
    extra_env: &[(&str, &str)],
) -> assert_cmd::assert::Assert {
    let mut command = AssertCommand::cargo_bin("larch").expect("larch binary");
    command
        .current_dir(work)
        .env("LARCH_TEST_LAUNCH_CLAUDE_SUBPROCESS", launcher)
        .env("LARCH_TEST_DIAGRAM_RETRY_DELAY_SECONDS", "0")
        .args([
            "implement",
            "code-flow-diagram",
            "--implement-tmpdir",
            &tmpdir.display().to_string(),
        ]);
    for (key, value) in extra_env {
        command.env(key, value);
    }
    command.assert()
}

const FIND_OUTPUT: &str = "out=\"\"\nprev=\"\"\nfor a in \"$@\"; do\n  if [ \"$prev\" = \"--output-file\" ]; then out=\"$a\"; fi\n  prev=\"$a\"\ndone\n";

#[test]
fn help_exits_zero() {
    AssertCommand::cargo_bin("larch")
        .expect("larch binary")
        .args(["implement", "code-flow-diagram", "--help"])
        .assert()
        .success()
        .stdout("")
        .stderr(predicates::str::contains(
            "Usage: scripts/larch.sh implement code-flow-diagram",
        ));
}

#[test]
fn compatibility_selector_remains_available() {
    AssertCommand::cargo_bin("larch")
        .expect("larch binary")
        .args(["diagram", "code-flow", "--help"])
        .assert()
        .success()
        .stdout(predicates::str::contains("usage: cli.py diagram code-flow"));
}

#[test]
fn missing_tmpdir_is_a_usage_error() {
    AssertCommand::cargo_bin("larch")
        .expect("larch binary")
        .args(["implement", "code-flow-diagram"])
        .assert()
        .code(2)
        .stdout(predicates::str::contains(
            "STATUS=failed\nDIAGRAM_FILE=\nSKIP_REASON=--implement-tmpdir is required\n",
        ));
}

#[test]
fn rejects_relative_tmpdir_and_unsafe_base_names() {
    AssertCommand::cargo_bin("larch")
        .expect("larch binary")
        .args([
            "implement",
            "code-flow-diagram",
            "--implement-tmpdir",
            "relative",
        ])
        .assert()
        .code(2)
        .stdout(predicates::str::contains(
            "SKIP_REASON=--implement-tmpdir must be absolute",
        ));
    AssertCommand::cargo_bin("larch")
        .expect("larch binary")
        .args([
            "implement",
            "code-flow-diagram",
            "--implement-tmpdir",
            "/tmp/larch-code-flow-test",
            "--base-ref",
            "main:unsafe",
        ])
        .assert()
        .code(2)
        .stdout(predicates::str::contains(
            "SKIP_REASON=--base-ref must match ^[A-Za-z0-9._/-]+$",
        ));
}

#[test]
fn accepts_a_valid_mermaid_diagram() {
    let tmp = TempDir::new().unwrap();
    let work = TempDir::new().unwrap();
    let stubs = TempDir::new().unwrap();
    let launcher = write_stub(
        stubs.path(),
        "ok.sh",
        &format!(
            "#!/bin/sh\n{FIND_OUTPUT}printf '## Code Flow Diagram\\n\\n```mermaid\\nflowchart LR\\n  A --> B\\n```\\n' > \"$out\"\nexit 0\n"
        ),
    );
    let diagram = tmp.path().join("code-flow-diagram.md");
    run(tmp.path(), work.path(), &launcher, &[])
        .success()
        .stdout(predicates::str::contains("STATUS=ok"))
        .stdout(predicates::str::contains(format!(
            "DIAGRAM_FILE={}",
            diagram.display()
        )))
        .stdout(predicates::str::contains("SKIP_REASON=\n"));
    assert!(diagram.is_file());
    assert_eq!(
        fs::read_to_string(tmp.path().join("code-flow-prompt.md")).unwrap(),
        "Generate a concise Mermaid code-flow diagram for the committed implementation diff.\nReturn markdown containing exactly one `## Code Flow Diagram` heading and one mermaid fence.\nFocus on runtime calls, data flow, and control flow. Avoid structural architecture duplication.\n\nChanged files:\n"
    );
    assert!(tmp.path().join("code-flow-launch.out").is_file());
    assert!(tmp.path().join("code-flow-launch.err").is_file());
    assert_eq!(
        fs::read_to_string(tmp.path().join("code-flow-sanitizer.failure.log")).unwrap(),
        "STATUS=ok\n"
    );
}

#[test]
fn rejects_an_unsafe_mermaid_diagram() {
    let tmp = TempDir::new().unwrap();
    let work = TempDir::new().unwrap();
    let stubs = TempDir::new().unwrap();
    let launcher = write_stub(
        stubs.path(),
        "skip.sh",
        &format!(
            "#!/bin/sh\n{FIND_OUTPUT}printf '## Code Flow Diagram\\n\\n```mermaid\\nflowchart LR\\n  A[foo|bar] --> B\\n```\\n' > \"$out\"\nexit 0\n"
        ),
    );
    run(tmp.path(), work.path(), &launcher, &[])
        .success()
        .stdout(predicates::str::contains("STATUS=skipped"))
        .stdout(predicates::str::contains("SKIP_REASON=pipe-in-node-label"));
    assert_eq!(
        fs::read_to_string(tmp.path().join("code-flow-sanitizer.failure.log")).unwrap(),
        "STATUS=rejected\nREASON_TOKEN=pipe-in-node-label\n"
    );
}

#[test]
fn reports_candidate_write_failure() {
    let tmp = TempDir::new().unwrap();
    let work = TempDir::new().unwrap();
    let stubs = TempDir::new().unwrap();
    fs::create_dir(tmp.path().join("code-flow-diagram.candidate.md")).unwrap();
    let launcher = write_stub(
        stubs.path(),
        "candidate-failure.sh",
        &format!(
            "#!/bin/sh\n{FIND_OUTPUT}printf '## Code Flow Diagram\\n\\n```mermaid\\nflowchart LR\\n  A --> B\\n```\\n' > \"$out\"\nexit 0\n"
        ),
    );
    run(tmp.path(), work.path(), &launcher, &[])
        .code(1)
        .stdout(predicates::str::contains("STATUS=failed"))
        .stdout(predicates::str::contains(
            "SKIP_REASON=candidate-write-failed",
        ));
}

#[test]
fn reports_candidate_promotion_failure() {
    let tmp = TempDir::new().unwrap();
    let work = TempDir::new().unwrap();
    let stubs = TempDir::new().unwrap();
    fs::create_dir(tmp.path().join("code-flow-diagram.md")).unwrap();
    let launcher = write_stub(
        stubs.path(),
        "promotion-failure.sh",
        &format!(
            "#!/bin/sh\n{FIND_OUTPUT}printf '## Code Flow Diagram\\n\\n```mermaid\\nflowchart LR\\n  A --> B\\n```\\n' > \"$out\"\nexit 0\n"
        ),
    );
    run(tmp.path(), work.path(), &launcher, &[])
        .code(1)
        .stdout(predicates::str::contains("STATUS=failed"))
        .stdout(predicates::str::contains(
            "SKIP_REASON=candidate-write-failed",
        ));
}

#[test]
fn labels_a_launcher_failure_class_without_retry() {
    let tmp = TempDir::new().unwrap();
    let work = TempDir::new().unwrap();
    let stubs = TempDir::new().unwrap();
    // Exit 1 with no output file written: a hard failure that is not retried.
    let launcher = write_stub(
        stubs.path(),
        "failed.sh",
        "#!/bin/sh\nprintf 'LAUNCHER_FAILURE_CLASS=health\\nLAUNCHER_FAILURE_REASON=auth\\n'\nexit 1\n",
    );
    run(tmp.path(), work.path(), &launcher, &[])
        .code(1)
        .stdout(predicates::str::contains("STATUS=failed"))
        .stdout(predicates::str::contains(
            "SKIP_REASON=generation-failed health/auth rc=1",
        ));
    assert!(!tmp.path().join("code-flow-diagram.retried").is_file());
    assert!(tmp.path().join("code-flow-diagram.failure.log").is_file());
    assert!(tmp.path().join("code-flow-launch.out").is_file());
    assert!(tmp.path().join("code-flow-launch.err").is_file());
}

#[test]
fn retries_then_succeeds_and_records_the_sidecar() {
    let tmp = TempDir::new().unwrap();
    let work = TempDir::new().unwrap();
    let stubs = TempDir::new().unwrap();
    let counter = stubs.path().join("count");
    // First attempt times out with an empty file; the first retry succeeds.
    let launcher = write_stub(
        stubs.path(),
        "retry.sh",
        &format!(
            "#!/bin/sh\n{FIND_OUTPUT}n=0\n[ -f \"$LARCH_STUB_COUNTER\" ] && n=$(cat \"$LARCH_STUB_COUNTER\")\nn=$((n+1))\necho \"$n\" > \"$LARCH_STUB_COUNTER\"\nif [ \"$n\" -eq 1 ]; then : > \"$out\"; exit 124; fi\nprintf '## Code Flow Diagram\\n\\n```mermaid\\nflowchart LR\\n  A --> B\\n```\\n' > \"$out\"\nexit 0\n"
        ),
    );
    run(
        tmp.path(),
        work.path(),
        &launcher,
        &[("LARCH_STUB_COUNTER", &counter.display().to_string())],
    )
    .success()
    .stdout(predicates::str::contains("STATUS=ok"));
    let sidecar = tmp.path().join("code-flow-diagram.retried");
    assert!(sidecar.is_file());
    let recorded = fs::read_to_string(&sidecar).unwrap();
    assert!(recorded.contains("FIRST_RC=124"), "{recorded}");
    assert!(recorded.contains("RETRY_1_RC=0"), "{recorded}");
    assert!(recorded.contains("RETRIES=1"), "{recorded}");
}

#[test]
fn persistent_empty_output_is_empty_generation() {
    let tmp = TempDir::new().unwrap();
    let work = TempDir::new().unwrap();
    let stubs = TempDir::new().unwrap();
    // Always exit 0 with an empty file: retried to the cap, then empty-generation.
    let launcher = write_stub(
        stubs.path(),
        "empty.sh",
        &format!("#!/bin/sh\n{FIND_OUTPUT}: > \"$out\"\nexit 0\n"),
    );
    run(tmp.path(), work.path(), &launcher, &[])
        .code(1)
        .stdout(predicates::str::contains("STATUS=failed"))
        .stdout(predicates::str::contains("SKIP_REASON=empty-generation"));
    let sidecar = tmp.path().join("code-flow-diagram.retried");
    assert!(sidecar.is_file());
    let recorded = fs::read_to_string(&sidecar).unwrap();
    assert!(recorded.contains("FIRST_RC=0"), "{recorded}");
    assert!(recorded.contains("RETRIES=4"), "{recorded}");
}
