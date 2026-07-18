#[path = "support/parity.rs"]
mod parity_support;

use std::{
    env,
    path::{Path, PathBuf},
    process::Command,
    time::Duration,
};

use parity_support::{NormalizationRule, ParityCase, Program, SeedFile, assert_case};
use tempfile::TempDir;

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
