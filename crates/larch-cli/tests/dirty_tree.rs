//! Differential and contract coverage for the Rust-owned dirty-tree commands.

use std::{
    ffi::OsString,
    fs,
    path::{Path, PathBuf},
    process::{Command as ProcessCommand, Output},
};

#[cfg(unix)]
use std::os::unix::ffi::OsStringExt as _;

use assert_cmd::Command;
use larch_test_support::{GitFixture, GitFixtureError, GitRepository};
use tempfile::TempDir;

fn larch_output(cwd: &Path, arguments: &[String]) -> Output {
    Command::cargo_bin("larch")
        .expect("larch binary should build")
        .args(arguments)
        .current_dir(cwd)
        .output()
        .expect("run larch dirty-tree command")
}

fn text_path(path: &Path) -> String {
    path.to_str()
        .unwrap_or_else(|| panic!("fixture path must be UTF-8: {}", path.display()))
        .to_owned()
}

fn dirty_tree_arguments(command: &str, arguments: &[(&str, &Path)]) -> Vec<String> {
    let mut values = vec!["dirty-tree".to_owned(), command.to_owned()];
    for (name, value) in arguments {
        values.push((*name).to_owned());
        values.push(text_path(value));
    }
    values
}

fn raw_dirty_tree_arguments(command: &str, arguments: &[&str]) -> Vec<String> {
    ["dirty-tree", command]
        .into_iter()
        .chain(arguments.iter().copied())
        .map(str::to_owned)
        .collect()
}

fn fixture_or_skip(fixture: GitFixture) -> Option<GitRepository> {
    match GitRepository::builder(fixture).build() {
        Ok(repository) => Some(repository),
        Err(GitFixtureError::Skip(skip)) => {
            eprintln!("explicit capability skip: {skip}");
            None
        }
        Err(error) => panic!("Git fixture failed: {error}"),
    }
}

fn fixture_path(name: &str) -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../fixtures/rust-parity")
        .join(name)
}

fn python_baseline_output(cwd: &Path, baseline: &Path, sidecar: &Path) -> Output {
    ProcessCommand::new("python3") // lint-subprocess-via-runner: ok frozen test-only Python parity oracle
        .arg(fixture_path("dirty_tree_reference.py"))
        .args([
            "--baseline",
            text_path(baseline).as_str(),
            "--sidecar",
            text_path(sidecar).as_str(),
            "--cwd",
            text_path(cwd).as_str(),
        ])
        .env("GIT_CONFIG_NOSYSTEM", "1")
        .env("GIT_CONFIG_GLOBAL", "/dev/null")
        .output()
        .expect("run frozen Python dirty-tree oracle")
}

fn normalize_workspace_paths(bytes: &[u8], workspace: &Path) -> Vec<u8> {
    let text = String::from_utf8(bytes.to_vec()).expect("dirty-tree metadata must be UTF-8");
    let workspace = text_path(workspace);
    text.replace(&workspace, "<WORKSPACE>").into_bytes()
}

#[test]
fn baseline_matches_frozen_python_oracle_for_non_utf8_paths() {
    #[cfg(not(unix))]
    {
        eprintln!("explicit capability skip: raw-byte paths require Unix");
        return;
    }

    #[cfg(unix)]
    {
        let Some(python_repository) = fixture_or_skip(GitFixture::NonUtf8Path) else {
            return;
        };
        let Some(rust_repository) = fixture_or_skip(GitFixture::NonUtf8Path) else {
            return;
        };
        let tracked = OsString::from_vec(b"non-utf8-\xff".to_vec());
        let untracked = OsString::from_vec(b"new-untracked-\xfe".to_vec());
        for repository in [&python_repository, &rust_repository] {
            fs::write(repository.root().join(&tracked), b"changed\n")
                .expect("modify raw-byte tracked file");
            fs::write(repository.root().join(&untracked), b"new\n")
                .expect("write raw-byte untracked file");
        }

        let python_baseline = python_repository.workspace_root().join("baseline.z");
        let python_sidecar = python_repository.workspace_root().join("dirty-tree");
        let rust_baseline = rust_repository.workspace_root().join("baseline.z");
        let rust_sidecar = rust_repository.workspace_root().join("dirty-tree");
        fs::write(&python_baseline, []).expect("write Python baseline");
        fs::write(&rust_baseline, []).expect("write Rust baseline");

        let python =
            python_baseline_output(python_repository.root(), &python_baseline, &python_sidecar);
        let rust = larch_output(
            rust_repository.root(),
            &dirty_tree_arguments(
                "baseline",
                &[("--baseline", &rust_baseline), ("--sidecar", &rust_sidecar)],
            ),
        );

        assert_eq!(rust.status.code(), python.status.code());
        assert_eq!(
            normalize_workspace_paths(&rust.stdout, rust_repository.workspace_root()),
            normalize_workspace_paths(&python.stdout, python_repository.workspace_root()),
        );
        assert_eq!(rust.stderr, python.stderr);
        assert_eq!(
            normalize_workspace_paths(
                &fs::read(&rust_sidecar).expect("read Rust sidecar"),
                rust_repository.workspace_root(),
            ),
            normalize_workspace_paths(
                &fs::read(&python_sidecar).expect("read Python sidecar"),
                python_repository.workspace_root(),
            ),
        );
        assert_eq!(
            fs::read(PathBuf::from(format!(
                "{}.tracked-paths",
                rust_sidecar.display()
            )))
            .expect("read Rust tracked paths"),
            fs::read(PathBuf::from(format!(
                "{}.tracked-paths",
                python_sidecar.display()
            )))
            .expect("read Python tracked paths"),
        );
        assert_eq!(
            fs::read(PathBuf::from(format!(
                "{}.new-untracked-paths",
                rust_sidecar.display()
            )))
            .expect("read Rust untracked paths"),
            b"new-untracked-\xfe\0",
        );
    }
}

#[test]
fn baseline_and_checkpoint_preserve_dirty_tree_envelopes() {
    let Some(repository) = fixture_or_skip(GitFixture::Changes) else {
        return;
    };
    let artifacts = TempDir::new().expect("artifact directory");
    let baseline = artifacts.path().join("baseline.z");
    let sidecar = artifacts.path().join("baseline.out");
    fs::write(&baseline, b".gitignore\0untracked.txt\0").expect("write baseline");

    let baseline_output = larch_output(
        repository.root(),
        &dirty_tree_arguments(
            "baseline",
            &[("--baseline", &baseline), ("--sidecar", &sidecar)],
        ),
    );
    assert!(baseline_output.status.success());
    assert_eq!(
        String::from_utf8(baseline_output.stdout).expect("baseline stdout"),
        format!(
            "STATUS=dirty\nMODE=baseline\nUNTRACKED_BASELINE=present\nTRACKED_PATHS_FILE={}.tracked-paths\nREASON=working-tree-dirty\n",
            sidecar.display(),
        ),
    );
    assert_eq!(
        fs::read(PathBuf::from(format!(
            "{}.tracked-paths",
            sidecar.display()
        )))
        .expect("tracked output"),
        b"staged.txt\0tracked.txt\0",
    );
    assert_eq!(
        fs::read(&sidecar).expect("baseline sidecar"),
        format!(
            "STATUS=dirty\nMODE=baseline\nUNTRACKED_BASELINE=present\nTRACKED_PATHS_FILE={}.tracked-paths\nREASON=working-tree-dirty\n",
            sidecar.display(),
        )
        .into_bytes(),
    );

    let checkpoint = larch_output(repository.root(), &dirty_tree_arguments("checkpoint", &[]));
    assert!(checkpoint.status.success());
    assert_eq!(
        checkpoint.stdout,
        b"STATUS=dirty\nMODE=checkpoint\nREASON=checkpoint-dirty\n",
    );

    let missing = artifacts.path().join("missing.z");
    let ambiguous = larch_output(
        repository.root(),
        &dirty_tree_arguments("baseline", &[("--baseline", &missing)]),
    );
    assert!(ambiguous.status.success());
    let ambiguous_text = String::from_utf8(ambiguous.stdout).expect("ambiguous stdout");
    assert!(ambiguous_text.starts_with(
        "STATUS=unknown\nMODE=baseline\nUNTRACKED_BASELINE=missing\nTRACKED_PATHS_FILE=",
    ));
    assert!(
        ambiguous_text.ends_with(".tracked-paths\nREASON=baseline-missing-untracked-ambiguous\n",)
    );
}

#[test]
fn baseline_and_checkpoint_preserve_clean_and_invalid_path_envelopes() {
    let Some(repository) = fixture_or_skip(GitFixture::Refs) else {
        return;
    };
    let artifacts = TempDir::new().expect("artifact directory");
    let missing = artifacts.path().join("missing.z");
    let clean = larch_output(
        repository.root(),
        &dirty_tree_arguments("baseline", &[("--baseline", &missing)]),
    );
    assert!(clean.status.success());
    assert_eq!(
        clean.stdout,
        b"STATUS=clean\nMODE=baseline\nUNTRACKED_BASELINE=missing\n",
    );

    let checkpoint = larch_output(repository.root(), &dirty_tree_arguments("checkpoint", &[]));
    assert!(checkpoint.status.success());
    assert_eq!(checkpoint.stdout, b"STATUS=clean\nMODE=checkpoint\n");

    let bad_baseline = artifacts.path().join("bad baseline.z");
    let bad_baseline_output = larch_output(
        repository.root(),
        &dirty_tree_arguments("baseline", &[("--baseline", &bad_baseline)]),
    );
    assert_eq!(
        bad_baseline_output.stdout,
        b"STATUS=unknown\nMODE=baseline\nUNTRACKED_BASELINE=missing\nREASON=bad-baseline-path\n",
    );

    let valid_baseline = artifacts.path().join("baseline.z");
    let bad_sidecar = artifacts.path().join("bad sidecar");
    fs::write(&valid_baseline, []).expect("write valid baseline");
    let bad_sidecar_output = larch_output(
        repository.root(),
        &dirty_tree_arguments(
            "baseline",
            &[("--baseline", &valid_baseline), ("--sidecar", &bad_sidecar)],
        ),
    );
    assert_eq!(
        bad_sidecar_output.stdout,
        b"STATUS=unknown\nMODE=baseline\nUNTRACKED_BASELINE=missing\nREASON=bad-sidecar-path\n",
    );
    assert!(!bad_sidecar.exists());
}

#[test]
fn baseline_treats_an_unresolved_merge_as_a_tracked_dirty_path() {
    let Some(repository) = fixture_or_skip(GitFixture::Conflict) else {
        return;
    };
    let artifacts = TempDir::new().expect("conflict artifacts");
    let baseline = artifacts.path().join("baseline.z");
    let sidecar = artifacts.path().join("baseline.out");

    let output = larch_output(
        repository.root(),
        &dirty_tree_arguments(
            "baseline",
            &[("--baseline", &baseline), ("--sidecar", &sidecar)],
        ),
    );

    assert!(output.status.success());
    assert_eq!(
        output.stdout,
        format!(
            "STATUS=dirty\nMODE=baseline\nUNTRACKED_BASELINE=missing\nTRACKED_PATHS_FILE={}.tracked-paths\nREASON=working-tree-dirty\n",
            sidecar.display(),
        )
        .into_bytes(),
    );
    assert_eq!(
        fs::read(PathBuf::from(format!(
            "{}.tracked-paths",
            sidecar.display()
        )))
        .expect("conflict tracked paths"),
        b"tracked.txt\0",
    );
}

#[test]
fn scope_check_accepts_declared_paths_and_reports_raw_out_of_scope_paths() {
    let temporary = TempDir::new().expect("scope fixture");
    let plan = temporary.path().join("plan.txt");
    let paths = temporary.path().join("paths.z");
    fs::write(
        &plan,
        "## Files to modify\n\n### UPDATED: `python/larch/state/bootstrap.py`\n### MAY_UPDATE: README.md\n",
    )
    .expect("write plan");
    fs::write(&paths, b"python/larch/state/bootstrap.py\0README.md\0")
        .expect("write in-scope paths");
    let in_scope = larch_output(
        temporary.path(),
        &dirty_tree_arguments(
            "scope-check",
            &[("--plan-file", &plan), ("--paths-file", &paths)],
        ),
    );
    assert!(in_scope.status.success());
    assert!(in_scope.stdout.is_empty());
    assert!(in_scope.stderr.is_empty());

    fs::write(&paths, b"README.md\0bad-\xff-path\0").expect("write out-of-scope paths");
    let out_of_scope = larch_output(
        temporary.path(),
        &dirty_tree_arguments(
            "scope-check",
            &[("--plan-file", &plan), ("--paths-file", &paths)],
        ),
    );
    assert_eq!(out_of_scope.status.code(), Some(1));
    assert_eq!(out_of_scope.stdout, b"");
    assert_eq!(out_of_scope.stderr, b"bad-\xff-path\n");

    fs::write(&plan, "## Files to modify\n\n### UPDATED[README.md]\n")
        .expect("write malformed plan heading");
    fs::write(&paths, b"README.md\0").expect("write malformed-plan path");
    let malformed_heading = larch_output(
        temporary.path(),
        &dirty_tree_arguments(
            "scope-check",
            &[("--plan-file", &plan), ("--paths-file", &paths)],
        ),
    );
    assert_eq!(malformed_heading.status.code(), Some(1));
    assert_eq!(malformed_heading.stderr, b"README.md\n");
}

#[test]
fn scope_marker_recognizes_contract_fields_but_ignores_code() {
    let temporary = TempDir::new().expect("scope-marker fixture");
    let finding = temporary.path().join("finding.md");
    fs::write(
        &finding,
        "### FINDING_1: [important] [SCOPE-REDUCTION] trim scope\n- **Concern**: [latent] keep scope\n",
    )
    .expect("write finding");
    let heading = larch_output(
        temporary.path(),
        &dirty_tree_arguments("scope-marker", &[("--file", &finding)]),
    );
    assert!(heading.status.success());

    fs::write(
        &finding,
        "what: `[SCOPE-REDUCTION] code only`\n```\nwhat: [SCOPE-REDUCTION] fenced\n```\n",
    )
    .expect("write coded finding");
    let code_only = larch_output(
        temporary.path(),
        &dirty_tree_arguments("scope-marker", &[("--file", &finding)]),
    );
    assert_eq!(code_only.status.code(), Some(1));
    assert!(code_only.stdout.is_empty());
    assert!(code_only.stderr.is_empty());

    fs::write(
        &finding,
        "###FINDING_1: [SCOPE-REDUCTION] malformed heading\n",
    )
    .expect("write malformed heading");
    let malformed_heading = larch_output(
        temporary.path(),
        &dirty_tree_arguments("scope-marker", &[("--file", &finding)]),
    );
    assert_eq!(malformed_heading.status.code(), Some(1));
}

#[test]
fn compatibility_argument_errors_preserve_python_argparse_precedence() {
    let temporary = TempDir::new().expect("parser fixture");

    let baseline = larch_output(
        temporary.path(),
        &raw_dirty_tree_arguments("baseline", &["--bogus", "x"]),
    );
    assert!(baseline.status.success());
    assert_eq!(
        baseline.stdout,
        b"STATUS=unknown\nMODE=baseline\nUNTRACKED_BASELINE=missing\nREASON=argv-error\n",
    );
    assert_eq!(
        baseline.stderr,
        b"usage: dirty-tree baseline [-h] --baseline BASELINE [--sidecar SIDECAR]\n\
dirty-tree baseline: error: the following arguments are required: --baseline\n",
    );

    let dash_baseline = larch_output(
        temporary.path(),
        &raw_dirty_tree_arguments("baseline", &["--baseline", "-"]),
    );
    assert!(dash_baseline.status.success());
    assert_eq!(
        dash_baseline.stdout,
        b"STATUS=unknown\nMODE=baseline\nUNTRACKED_BASELINE=missing\nREASON=git-status-failed\n",
    );
    assert!(dash_baseline.stderr.is_empty());

    let checkpoint = larch_output(
        temporary.path(),
        &raw_dirty_tree_arguments("checkpoint", &["--", "--bogus"]),
    );
    assert!(checkpoint.status.success());
    assert_eq!(
        checkpoint.stdout,
        b"STATUS=unknown\nMODE=checkpoint\nREASON=argv-error\n",
    );
    assert_eq!(
        checkpoint.stderr,
        b"usage: dirty-tree checkpoint [-h] [--sidecar SIDECAR] [--cwd CWD]\n\
dirty-tree checkpoint: error: unrecognized arguments: -- --bogus\n",
    );

    let scope_check = larch_output(
        temporary.path(),
        &raw_dirty_tree_arguments("scope-check", &["--bogus", "x"]),
    );
    assert_eq!(scope_check.status.code(), Some(2));
    assert!(scope_check.stdout.is_empty());
    assert_eq!(
        scope_check.stderr,
        br"usage: dirty-tree scope-check [-h] --plan-file PLAN_FILE --paths-file
                              PATHS_FILE
dirty-tree scope-check: error: the following arguments are required: --plan-file, --paths-file
",
    );

    let ambiguous_scope_option = larch_output(
        temporary.path(),
        &raw_dirty_tree_arguments(
            "scope-check",
            &["--p", "x", "--plan-file", "plan", "--paths-file", "paths"],
        ),
    );
    assert_eq!(ambiguous_scope_option.status.code(), Some(2));
    assert_eq!(
        ambiguous_scope_option.stderr,
        br"usage: dirty-tree scope-check [-h] --plan-file PLAN_FILE --paths-file
                              PATHS_FILE
dirty-tree scope-check: error: ambiguous option: --p could match --plan-file, --paths-file
",
    );

    let scope_marker = larch_output(
        temporary.path(),
        &raw_dirty_tree_arguments("scope-marker", &["--", "--bogus"]),
    );
    assert_eq!(scope_marker.status.code(), Some(2));
    assert!(scope_marker.stdout.is_empty());
    assert_eq!(
        scope_marker.stderr,
        b"usage: dirty-tree scope-marker [-h] [--file FILE]\n\
dirty-tree scope-marker: error: unrecognized arguments: -- --bogus\n",
    );
}
