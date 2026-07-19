#[path = "support/parity.rs"]
mod parity_support;

use std::{
    env, fs,
    path::{Path, PathBuf},
    process::Command,
    time::Duration,
};

#[cfg(unix)]
use std::os::unix::fs::PermissionsExt as _;

use parity_support::{NormalizationRule, ParityCase, Program, SeedFile, assert_case};
use tempfile::TempDir;

#[derive(Clone, Copy)]
struct CleanInstallCase {
    id: &'static str,
    domain: &'static str,
    verb: &'static str,
}

impl CleanInstallCase {
    const fn new(id: &'static str, domain: &'static str, verb: &'static str) -> Self {
        Self { id, domain, verb }
    }
}

const CLEAN_INSTALL_CASES: &[CleanInstallCase] = &[
    CleanInstallCase::new("clean-install-gh-remote-repo", "gh", "remote-repo"),
    CleanInstallCase::new("clean-install-gh-resolve-repo", "gh", "resolve-repo"),
    CleanInstallCase::new("clean-install-gh-run-logs", "gh", "run-logs"),
    CleanInstallCase::new("clean-install-gh-workflow-path", "gh", "workflow-path"),
    CleanInstallCase::new("clean-install-git-amend-add", "git", "amend-add"),
    CleanInstallCase::new("clean-install-git-branch-info", "git", "branch-info"),
    CleanInstallCase::new(
        "clean-install-git-check-main-sync",
        "git",
        "check-main-sync",
    ),
    CleanInstallCase::new(
        "clean-install-git-check-phantom-dirty",
        "git",
        "check-phantom-dirty",
    ),
    CleanInstallCase::new(
        "clean-install-git-check-remote-branch",
        "git",
        "check-remote-branch",
    ),
    CleanInstallCase::new("clean-install-git-checkout-ours", "git", "checkout-ours"),
    CleanInstallCase::new("clean-install-git-clean-tree", "git", "clean-tree"),
    CleanInstallCase::new("clean-install-git-commit", "git", "commit"),
    CleanInstallCase::new("clean-install-git-conflict-files", "git", "conflict-files"),
    CleanInstallCase::new("clean-install-git-count-commits", "git", "count-commits"),
    CleanInstallCase::new("clean-install-git-current-branch", "git", "current-branch"),
    CleanInstallCase::new("clean-install-git-phantom-probe", "git", "phantom-probe"),
    CleanInstallCase::new("clean-install-git-rebase-abort", "git", "rebase-abort"),
    CleanInstallCase::new("clean-install-git-rebase-skip", "git", "rebase-skip"),
    CleanInstallCase::new("clean-install-git-show-stage", "git", "show-stage"),
    CleanInstallCase::new(
        "clean-install-git-snapshot-untracked",
        "git",
        "snapshot-untracked",
    ),
    CleanInstallCase::new("clean-install-git-stage", "git", "stage"),
    CleanInstallCase::new(
        "clean-install-git-sync-local-main",
        "git",
        "sync-local-main",
    ),
    CleanInstallCase::new(
        "clean-install-plugin-read-version",
        "plugin",
        "read-version",
    ),
    CleanInstallCase::new("clean-install-push-branch", "push", "branch"),
    CleanInstallCase::new(
        "clean-install-push-checkpoint-probe",
        "push",
        "checkpoint-probe",
    ),
    CleanInstallCase::new("clean-install-push-force", "push", "force"),
    CleanInstallCase::new("clean-install-push-rebase", "push", "rebase"),
    CleanInstallCase::new(
        "clean-install-release-asset-candidate",
        "release",
        "asset-candidate",
    ),
    CleanInstallCase::new(
        "clean-install-release-classify-bump",
        "release",
        "classify-bump",
    ),
    CleanInstallCase::new(
        "clean-install-release-collect-assets",
        "release",
        "collect-assets",
    ),
    CleanInstallCase::new(
        "clean-install-release-package-asset",
        "release",
        "package-asset",
    ),
    CleanInstallCase::new(
        "clean-install-release-plugin-runtime",
        "release",
        "plugin-runtime",
    ),
    CleanInstallCase::new("clean-install-release-prepare", "release", "prepare"),
    CleanInstallCase::new(
        "clean-install-release-set-version",
        "release",
        "set-version",
    ),
    CleanInstallCase::new(
        "clean-install-release-validate-assets",
        "release",
        "validate-assets",
    ),
    CleanInstallCase::new(
        "clean-install-upgrade-larch-release-step7-root",
        "upgrade-larch",
        "release-step7-root",
    ),
    CleanInstallCase::new("clean-install-upgrade-larch-run", "upgrade-larch", "run"),
    CleanInstallCase::new(
        "clean-install-upgrade-larch-sparse-dirs",
        "upgrade-larch",
        "sparse-dirs",
    ),
];

#[test]
fn representative_python_and_rust_commands_have_reviewed_parity() {
    let fixture_directory = fixture_directory();
    let python = find_executable("python3");
    let compiled_rust_fixture = compile_rust_fixture(&fixture_directory);
    let rust_fixture = compiled_rust_fixture.path().join("reference-command");
    let python_fixture = fixture_directory.join("reference_command.py");
    let golden_directory = fixture_directory.join("goldens");

    let cases = [
        ParityCase {
            name: "clean",
            python: Program::new(&python)
                .args([path_text(&python_fixture), "clean", "{sandbox}"])
                .env("FIXTURE_TIMESTAMP", "2026-07-18T20:00:00.123Z"),
            rust: Program::new(&rust_fixture)
                .args(["clean", "{sandbox}"])
                .env("FIXTURE_TIMESTAMP", "2026-07-18T20:00:01Z"),
            seed_files: vec![SeedFile::text("input/seed.txt", "fixture\n")],
            side_effect_records: vec![PathBuf::from("effects.ndjson")],
            normalization: vec![
                NormalizationRule::SandboxRoot,
                NormalizationRule::Rfc3339Utc,
            ],
        },
        ParityCase {
            name: "usage-error",
            python: Program::new(&python).args([path_text(&python_fixture)]),
            rust: Program::new(&rust_fixture),
            seed_files: Vec::new(),
            side_effect_records: Vec::new(),
            normalization: Vec::new(),
        },
        ParityCase {
            name: "malformed-input",
            python: Program::new(&python).args([
                path_text(&python_fixture),
                "malformed",
                "{sandbox}",
            ]),
            rust: Program::new(&rust_fixture).args(["malformed", "{sandbox}"]),
            seed_files: Vec::new(),
            side_effect_records: Vec::new(),
            normalization: Vec::new(),
        },
        ParityCase {
            name: "environmental-failure",
            python: Program::new(&python).args([
                path_text(&python_fixture),
                "environment",
                "{sandbox}",
            ]),
            rust: Program::new(&rust_fixture).args(["environment", "{sandbox}"]),
            seed_files: Vec::new(),
            side_effect_records: Vec::new(),
            normalization: Vec::new(),
        },
        ParityCase {
            name: "service-isolation",
            python: Program::new(&python).args([
                path_text(&python_fixture),
                "isolation",
                "{sandbox}",
            ]),
            rust: Program::new(&rust_fixture).args(["isolation", "{sandbox}"]),
            seed_files: Vec::new(),
            side_effect_records: Vec::new(),
            normalization: vec![NormalizationRule::SandboxRoot],
        },
    ];

    for case in cases {
        let golden = golden_directory.join(format!("{}.golden.json", case.name));
        assert_case(&case, &golden).unwrap_or_else(|error| panic!("{error}"));
    }
}

#[test]
fn hung_command_fails_at_the_case_boundary() {
    let fixture_directory = fixture_directory();
    let python = find_executable("python3");
    let compiled_rust_fixture = compile_rust_fixture(&fixture_directory);
    let case = ParityCase {
        name: "timeout",
        python: Program::new(&python)
            .args(["-c", "import time; time.sleep(2)"])
            .timeout(Duration::from_millis(50)),
        rust: Program::new(compiled_rust_fixture.path().join("reference-command")),
        seed_files: Vec::new(),
        side_effect_records: Vec::new(),
        normalization: Vec::new(),
    };

    let error = assert_case(&case, Path::new("unused.golden.json"))
        .expect_err("hung command should fail the harness");

    assert!(error.contains("timed out after 50ms"));
}

#[test]
fn rust_owned_selector_matrix_enters_through_verified_clean_install_script() {
    let fixture = clean_install_fixture();
    for case in CLEAN_INSTALL_CASES {
        fs::write(&fixture.events, b"").expect("clear clean-install event log");
        let output = run_clean_install_case(&fixture, *case, None);
        assert!(
            output.status.success(),
            "{} failed: {}",
            case.id,
            String::from_utf8_lossy(&output.stderr)
        );
        let events = fs::read_to_string(&fixture.events).expect("read clean-install events");
        let lines: Vec<&str> = events.lines().collect();
        assert_eq!(lines.first(), Some(&"--version"), "{}", case.id);
        assert_eq!(lines.get(1), Some(&"bootstrap self-check"), "{}", case.id);
        assert_eq!(
            lines.get(2),
            Some(&format!("{} {} --help", case.domain, case.verb).as_str()),
            "{}",
            case.id
        );
        assert_eq!(lines.len(), 3, "{}", case.id);
        assert!(!fixture.root.join("bin/larch").exists(), "{}", case.id);
    }
}

#[test]
fn clean_install_validation_failures_precede_selector_dispatch() {
    let fixture = clean_install_fixture();
    let case = CLEAN_INSTALL_CASES[0];
    for failure in ["version", "target", "bootstrap"] {
        fs::write(&fixture.events, b"").expect("clear clean-install event log");
        let output = run_clean_install_case(&fixture, case, Some(failure));
        assert!(
            !output.status.success(),
            "{failure} unexpectedly dispatched"
        );
        let events = fs::read_to_string(&fixture.events).expect("read clean-install events");
        assert!(
            !events
                .lines()
                .any(|line| line == format!("{} {} --help", case.domain, case.verb)),
            "{failure} reached selector dispatch"
        );
    }
}

struct CleanInstallFixture {
    _temporary: TempDir,
    root: PathBuf,
    wrapper: PathBuf,
    events: PathBuf,
    binary: PathBuf,
}

fn clean_install_fixture() -> CleanInstallFixture {
    let temporary = tempfile::tempdir().expect("clean-install tempdir");
    let temporary_root = fs::canonicalize(temporary.path()).expect("canonical clean-install root");
    let root = temporary_root.join("plugin");
    let scripts = root.join("scripts");
    let manifest_directory = root.join(".claude-plugin");
    fs::create_dir_all(&scripts).expect("create clean-install scripts directory");
    fs::create_dir_all(&manifest_directory).expect("create clean-install manifest directory");
    fs::copy(
        Path::new(env!("CARGO_MANIFEST_DIR")).join("../../scripts/larch.sh"),
        scripts.join("larch.sh"),
    )
    .expect("copy verified bootstrap script");
    fs::write(
        manifest_directory.join("plugin.json"),
        format!(
            "{{\n  \"name\": \"larch\",\n  \"version\": \"{}\"\n}}\n",
            env!("CARGO_PKG_VERSION")
        ),
    )
    .expect("write clean-install plugin manifest");
    let wrapper = temporary_root.join("verified-larch");
    fs::write(
        &wrapper,
        r#"#!/bin/sh
set -eu
printf '%s\n' "$*" >> "$CLEAN_INSTALL_EVENTS"
case "$CLEAN_INSTALL_FAILURE" in
  version)
    if [ "$1" = --version ]; then printf '%s\n' 'larch 0.0.0'; exit 0; fi
    ;;
  target)
    if [ "$1" = bootstrap ]; then
      if [ "$2" = self-check ]; then
        "$REAL_LARCH" "$@" | sed 's/"target":"[^"]*"/"target":"wrong-target"/'
        exit "$?"
      fi
    fi
    ;;
  bootstrap)
    if [ "$1" = bootstrap ]; then
      if [ "$2" = self-check ]; then exit 9; fi
    fi
    ;;
esac
exec "$REAL_LARCH" "$@"
"#,
    )
    .expect("write verified binary wrapper");
    #[cfg(unix)]
    {
        let mut permissions = fs::metadata(&wrapper)
            .expect("read wrapper metadata")
            .permissions();
        permissions.set_mode(0o755);
        fs::set_permissions(&wrapper, permissions).expect("make wrapper executable");
    }
    CleanInstallFixture {
        events: temporary_root.join("events.log"),
        binary: PathBuf::from(env!("CARGO_BIN_EXE_larch")),
        _temporary: temporary,
        root,
        wrapper,
    }
}

fn run_clean_install_case(
    fixture: &CleanInstallFixture,
    case: CleanInstallCase,
    failure: Option<&str>,
) -> std::process::Output {
    let mut command = Command::new("/bin/bash");
    command
        .arg(fixture.root.join("scripts/larch.sh"))
        .args([case.domain, case.verb, "--help"])
        .env("CLAUDE_PLUGIN_ROOT", &fixture.root)
        .env("LARCH_BINARY", &fixture.wrapper)
        .env("REAL_LARCH", &fixture.binary)
        .env("CLEAN_INSTALL_EVENTS", &fixture.events)
        .env("CLEAN_INSTALL_FAILURE", failure.unwrap_or_default());
    command.output().expect("run clean-install selector")
}

fn fixture_directory() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../fixtures/rust-parity")
}

fn compile_rust_fixture(fixture_directory: &Path) -> TempDir {
    let output = tempfile::tempdir().expect("compiled Rust fixture tempdir");
    let executable = output.path().join("reference-command");
    let rustc = env::var_os("RUSTC").map_or_else(|| find_executable("rustc"), PathBuf::from);
    let status = Command::new(&rustc)
        .args(["--edition=2024", "-o"])
        .arg(&executable)
        .arg(fixture_directory.join("reference_command.rs"))
        .status()
        .unwrap_or_else(|error| panic!("launch {}: {error}", rustc.display()));
    assert!(status.success(), "Rust parity fixture failed to compile");
    output
}

fn find_executable(name: &str) -> PathBuf {
    let path = env::var_os("PATH").expect("test process should have PATH");
    env::split_paths(&path)
        .map(|directory| {
            if directory.is_absolute() {
                directory.join(name)
            } else {
                env::current_dir()
                    .expect("test process should have a current directory")
                    .join(directory)
                    .join(name)
            }
        })
        .find(|candidate| candidate.is_file())
        .unwrap_or_else(|| panic!("required executable not found on PATH: {name}"))
}

fn path_text(path: &Path) -> &str {
    path.to_str().expect("fixture path should be UTF-8")
}
