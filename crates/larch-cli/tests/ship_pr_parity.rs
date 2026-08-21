//! Black-box contracts for the Rust-owned `ship pr` entrypoint (#8628).

use std::{fs, path::Path, process::Command};

use tempfile::TempDir;

fn run(program: &Path, arguments: &[&str]) -> std::process::Output {
    run_in(
        &Path::new(env!("CARGO_MANIFEST_DIR")).join("../.."),
        program,
        arguments,
    )
}

fn run_in(cwd: &Path, program: &Path, arguments: &[&str]) -> std::process::Output {
    Command::new(program)
        .args(arguments)
        .current_dir(cwd)
        .output()
        .expect("run parity command")
}

fn git(cwd: &Path, arguments: &[&str]) {
    let output = run_in(cwd, Path::new("git"), arguments);
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
}

#[test]
fn help_identifies_the_rust_owner() {
    let rust = run(
        Path::new(env!("CARGO_BIN_EXE_larch")),
        &["ship", "pr", "--help"],
    );
    assert!(rust.status.success());
    assert!(rust.stderr.is_empty());
    let stdout = String::from_utf8(rust.stdout).expect("UTF-8 help");
    assert!(stdout.starts_with("usage: cli.py [-h] [--branch BRANCH]"));
    assert!(stdout.contains("Run the Rust ship-pr driver"));
    assert!(stdout.contains("--result-env-path RESULT_ENV_PATH"));
}

#[test]
fn malformed_arguments_use_the_frozen_driver_result_wire() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let cli = root.join("python/cli.py");
    let python = run(
        Path::new("python3"),
        &[cli.to_str().expect("UTF-8 path"), "ship", "pr", "--unknown"],
    );
    let rust = run(
        Path::new(env!("CARGO_BIN_EXE_larch")),
        &["ship", "pr", "--unknown"],
    );
    assert_eq!(python.status.code(), Some(2));
    assert!(python.stdout.is_empty());
    assert!(String::from_utf8_lossy(&python.stderr).contains("unknown subcommand 'ship' 'pr'"));
    assert_eq!(rust.status.code(), Some(1));
    assert!(String::from_utf8_lossy(&rust.stderr).contains("unrecognized arguments: --unknown"));
    let value: serde_json::Value = serde_json::from_slice(&rust.stdout).expect("driver JSON");
    assert_eq!(value["outcome"], "INTERNAL_ERROR");
    assert_eq!(value["detail"], "argparse failed with exit 2");
}

#[test]
fn manual_merge_recovery_retains_its_frozen_usage_contract() {
    let output = run(
        Path::new(env!("CARGO_BIN_EXE_larch")),
        &["ship", "reconcile-manual-merge", "--help"],
    );
    assert_eq!(output.status.code(), Some(1));
    assert!(output.stderr.is_empty());
    let stdout = String::from_utf8(output.stdout).expect("UTF-8 help");
    assert!(stdout.starts_with("usage: cli.py ship reconcile-manual-merge"));
    assert!(stdout.ends_with("RECONCILE_STATUS=failed\nERROR=usage\n"));
}

#[test]
#[allow(clippy::too_many_lines)] // One fixture proves the success-to-conflict recovery transition.
fn local_only_success_and_rebase_conflict_preserve_state_handoffs() {
    let fixture = TempDir::new().expect("fixture");
    let origin = fixture.path().join("origin.git");
    let repo = fixture.path().join("repo");
    let tmpdir = fixture.path().join("claude-implement-ship-pr-parity");
    fs::create_dir_all(&repo).expect("repo");
    fs::create_dir_all(&tmpdir).expect("tmpdir");
    git(
        fixture.path(),
        &["init", "--bare", origin.to_str().expect("origin")],
    );
    git(&repo, &["init"]);
    git(&repo, &["config", "user.name", "Larch Test"]);
    git(&repo, &["config", "user.email", "larch@example.invalid"]);
    fs::write(
        repo.join("ARCHITECTURAL_INVARIANTS.md"),
        "# Architectural Invariants\n\n### I-Test-1: Keep identity\n\nKeep identity.\n",
    )
    .expect("invariants");
    fs::write(repo.join("ARCHITECTURAL_GUIDELINES.md"), "# Architectural Guidelines\n\n### G-Test-1: Keep parity\n- Why: parity matters.\n- Guidance: preserve it.\n- Deviate when: never in this fixture.\n").expect("guidelines");
    fs::write(repo.join("conflict.txt"), "base\n").expect("base file");
    git(&repo, &["add", "."]);
    git(&repo, &["commit", "-m", "base"]);
    git(&repo, &["branch", "-M", "main"]);
    git(
        &repo,
        &["remote", "add", "origin", origin.to_str().expect("origin")],
    );
    git(&repo, &["push", "-u", "origin", "main"]);
    git(&repo, &["checkout", "-b", "feature/ship"]);
    fs::create_dir_all(repo.join("docs")).expect("docs");
    fs::write(repo.join("docs/feature.md"), "feature\n").expect("docs change");
    git(&repo, &["add", "docs/feature.md"]);
    git(&repo, &["commit", "-m", "docs feature"]);
    let manifest = tmpdir.join("manifest.json");
    let state = tmpdir.join("ship-pr-state.sh");
    fs::write(&manifest, "{}\n").expect("manifest");
    let binary = Path::new(env!("CARGO_BIN_EXE_larch"));
    let seeded = run_in(
        &repo,
        binary,
        &[
            "ship",
            "seed-initial-state",
            "--tmpdir",
            tmpdir.to_str().expect("tmpdir"),
            "--state-file",
            state.to_str().expect("state"),
            "--branch",
            "feature/ship",
            "--issue",
            "8626",
            "--repo",
            "owner/repo",
            "--run-id",
            "run-8626",
            "--manifest-path",
            manifest.to_str().expect("manifest"),
            "--repo-unavailable",
            "true",
        ],
    );
    assert!(
        seeded.status.success(),
        "{}",
        String::from_utf8_lossy(&seeded.stderr)
    );
    let local = run_in(
        &repo,
        binary,
        &[
            "ship",
            "pr",
            "--tmpdir",
            tmpdir.to_str().expect("tmpdir"),
            "--state-file",
            state.to_str().expect("state"),
        ],
    );
    assert!(
        local.status.success(),
        "status={:?} stdout={} stderr={}",
        local.status.code(),
        String::from_utf8_lossy(&local.stdout),
        String::from_utf8_lossy(&local.stderr)
    );
    assert!(String::from_utf8_lossy(&local.stdout).contains(r#""detail": "local-only""#));
    let local_state = fs::read_to_string(&state).expect("state");
    for row in [
        "PHASE=done",
        "STALL_TRACKING=false",
        "STALL_STEP=",
        "EXIT_CODE=0",
        "BAIL_REASON=",
        "BAIL_NEEDS_USER_INPUT=false",
    ] {
        assert!(
            local_state.lines().any(|line| line == row),
            "missing {row}: {local_state}"
        );
    }

    git(&repo, &["checkout", "main"]);
    fs::write(repo.join("conflict.txt"), "main\n").expect("main conflict");
    git(&repo, &["commit", "-am", "main conflict"]);
    git(&repo, &["push", "origin", "main"]);
    git(&repo, &["checkout", "feature/ship"]);
    fs::write(repo.join("conflict.txt"), "feature\n").expect("feature conflict");
    git(&repo, &["commit", "-am", "feature conflict"]);
    let conflict = run_in(
        &repo,
        binary,
        &[
            "ship",
            "pr",
            "--tmpdir",
            tmpdir.to_str().expect("tmpdir"),
            "--state-file",
            state.to_str().expect("state"),
        ],
    );
    assert_eq!(conflict.status.code(), Some(4));
    let state = fs::read_to_string(state).expect("conflict state");
    for row in [
        "PHASE=rebase",
        "RESUME_PHASE=ship-pr-rrr-phase14",
        "CALLER_KIND=ship_pr_pre_push",
        "CONFLICT_FILES=conflict.txt",
        "STALL_TRACKING=true",
        "STALL_STEP=rebase-failed",
    ] {
        assert!(
            state.lines().any(|line| line == row),
            "missing {row}: {state}"
        );
    }
    let status = run_in(&repo, Path::new("git"), &["status", "--porcelain"]);
    assert!(status.status.success());
    assert!(
        String::from_utf8_lossy(&status.stdout).contains("UU conflict.txt"),
        "conflict handoff must leave the rebase available to its resolver"
    );
}
