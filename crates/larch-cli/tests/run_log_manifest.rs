use std::{
    collections::BTreeMap,
    env, fs,
    path::{Path, PathBuf},
    process::Command,
};

use assert_cmd::Command as AssertCommand;
use larch_test_support::{
    ExecutionSnapshot, ReportingParityOracle, RunLogFixture, RunLogSnapshot, RunLogTree,
};
use serde_json::Value;
use sha2::{Digest as _, Sha256};

fn larch() -> AssertCommand {
    AssertCommand::cargo_bin("larch").expect("larch binary should build")
}

fn manifest_arguments(tree: &RunLogTree) -> Vec<String> {
    vec![
        "run-log".to_owned(),
        "manifest".to_owned(),
        "--log-root".to_owned(),
        tree.staging_root().display().to_string(),
        "--skill".to_owned(),
        tree.skill().to_owned(),
        "--run-id".to_owned(),
        tree.run_id().to_owned(),
        "--field".to_owned(),
        "status=true".to_owned(),
        "--field".to_owned(),
        "steps_ran.step8=true".to_owned(),
        "--field".to_owned(),
        "pr_number=17".to_owned(),
        "--field".to_owned(),
        "z_extension=snowman ☃".to_owned(),
    ]
}

#[test]
fn manifest_command_matches_python_full_run_log_tree_snapshot() {
    let rust_tree = RunLogTree::builder(RunLogFixture::PartialStaging)
        .build()
        .expect("Rust fixture should build");
    let python_tree = RunLogTree::builder(RunLogFixture::PartialStaging)
        .build()
        .expect("Python fixture should build");
    let arguments = manifest_arguments(&rust_tree);

    let output = larch()
        .args(&arguments)
        .output()
        .expect("manifest command should launch");

    assert!(
        output.status.success(),
        "manifest command failed: stdout={} stderr={}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    );
    let envelope = envelope(&output.stdout);
    let manifest_path = rust_tree.run_dir().join("manifest.json");
    let manifest_bytes = fs::read(&manifest_path).expect("Rust manifest should read");
    assert_eq!(envelope.get("LOG_WRITTEN"), Some(&"true".to_owned()));
    assert_eq!(
        envelope.get("LOG_PATH"),
        Some(&manifest_path.display().to_string())
    );
    assert_eq!(
        envelope.get("BYTES"),
        Some(&manifest_bytes.len().to_string())
    );
    assert_eq!(
        envelope.get("SHA256"),
        Some(&format!("{:x}", Sha256::digest(&manifest_bytes)))
    );
    assert_eq!(envelope.get("COMMIT_SHA"), Some(&String::new()));
    assert_eq!(envelope.get("UNCHANGED"), Some(&"false".to_owned()));

    let timestamp = serde_json::from_slice::<Value>(&manifest_bytes)
        .expect("manifest JSON should parse")
        .get("updated_at")
        .and_then(Value::as_str)
        .expect("updated timestamp should exist")
        .to_owned();
    run_python_reference(&python_tree, &timestamp);

    let rust_snapshot = RunLogSnapshot::capture(&rust_tree, ExecutionSnapshot::success())
        .expect("Rust snapshot should capture");
    let python_snapshot = RunLogSnapshot::capture(&python_tree, ExecutionSnapshot::success())
        .expect("Python snapshot should capture");
    assert!(
        ReportingParityOracle::new()
            .compare_run_logs(&rust_snapshot, &python_snapshot)
            .is_empty(),
        "Rust and Python run-log snapshots diverged:\nRust:\n{}\nPython:\n{}",
        rust_snapshot.render(),
        python_snapshot.render()
    );
}

#[test]
fn manifest_command_fails_closed_for_immutable_missing_and_unknown_sources() {
    let tree = RunLogTree::builder(RunLogFixture::PartialStaging)
        .build()
        .expect("fixture should build");
    let manifest_path = tree.run_dir().join("manifest.json");
    let original = fs::read(&manifest_path).expect("manifest should read");

    let immutable = larch()
        .args([
            "run-log",
            "manifest",
            "--log-root",
            &tree.staging_root().display().to_string(),
            "--skill",
            tree.skill(),
            "--run-id",
            tree.run_id(),
            "--field",
            "run_id=other",
        ])
        .output()
        .expect("immutable command should launch");
    assert_eq!(immutable.status.code(), Some(1));
    assert!(String::from_utf8_lossy(&immutable.stdout).contains("ERROR=immutable-field:run_id"));
    assert_eq!(
        fs::read(&manifest_path).expect("manifest should read"),
        original
    );

    fs::write(
        &manifest_path,
        b"{\"schema_version\":99,\"steps_ran\":{}}\n",
    )
    .expect("unknown manifest should write");
    let unknown_original = fs::read(&manifest_path).expect("unknown source should read");
    let unknown = larch()
        .args([
            "run-log",
            "manifest",
            "--log-root",
            &tree.staging_root().display().to_string(),
            "--skill",
            tree.skill(),
            "--run-id",
            tree.run_id(),
        ])
        .output()
        .expect("unknown command should launch");
    assert_eq!(unknown.status.code(), Some(1));
    assert!(String::from_utf8_lossy(&unknown.stdout).contains("ERROR=unknown-schema-version:"));
    assert_eq!(
        fs::read(&manifest_path).expect("unknown source should read"),
        unknown_original
    );

    fs::remove_file(&manifest_path).expect("manifest should remove");
    let missing = larch()
        .args([
            "run-log",
            "manifest",
            "--log-root",
            &tree.staging_root().display().to_string(),
            "--skill",
            tree.skill(),
            "--run-id",
            tree.run_id(),
        ])
        .output()
        .expect("missing command should launch");
    assert_eq!(missing.status.code(), Some(1));
    assert!(String::from_utf8_lossy(&missing.stdout).contains(&format!(
        "ERROR=manifest not found: {}",
        manifest_path.display()
    )));
}

#[test]
fn manifest_command_rejects_log_root_escape_from_implement_tmpdir() {
    let tree = RunLogTree::builder(RunLogFixture::PartialStaging)
        .build()
        .expect("fixture should build");

    let output = larch()
        .args([
            "run-log",
            "manifest",
            "--log-root",
            "/../../escaped",
            "--skill",
            tree.skill(),
            "--run-id",
            tree.run_id(),
        ])
        .env("IMPLEMENT_TMPDIR", tree.staging_root())
        .output()
        .expect("manifest command should launch");

    assert_eq!(output.status.code(), Some(1));
    assert!(
        String::from_utf8_lossy(&output.stderr).contains("--log-root escapes IMPLEMENT_TMPDIR")
    );
    assert!(String::from_utf8_lossy(&output.stdout).contains("ERROR=invalid manifest arguments"));
}

fn envelope(stdout: &[u8]) -> BTreeMap<String, String> {
    String::from_utf8_lossy(stdout)
        .lines()
        .filter_map(|line| line.split_once('='))
        .map(|(key, value)| (key.to_owned(), value.to_owned()))
        .collect()
}

fn run_python_reference(tree: &RunLogTree, timestamp: &str) {
    let source_root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let python_root = source_root.join("python");
    let script = r#"
from pathlib import Path
import sys
import larch.report.run_log_manifest as manifest

manifest._now_utc = lambda: sys.argv[2]
manifest._update_manifest_v2(
    path=Path(sys.argv[1]),
    updates={
        "status": True,
        "steps_ran.step8": True,
        "pr_number": 17,
        "z_extension": "snowman ☃",
    },
)
"#;
    let status = Command::new(find_executable("python3"))
        .arg("-c")
        .arg(script)
        .arg(
            fs::canonicalize(tree.run_dir().join("manifest.json"))
                .expect("Python manifest path should canonicalize"),
        )
        .arg(timestamp)
        .env("PYTHONPATH", python_root)
        .status()
        .expect("Python reference should launch");
    assert!(status.success(), "Python reference should succeed");
}

fn find_executable(name: &str) -> PathBuf {
    let path = env::var_os("PATH").expect("PATH should exist");
    env::split_paths(&path)
        .map(|directory| {
            if directory.is_absolute() {
                directory.join(name)
            } else {
                env::current_dir()
                    .expect("current directory should resolve")
                    .join(directory)
                    .join(name)
            }
        })
        .find(|candidate| candidate.is_file())
        .unwrap_or_else(|| panic!("required executable not found on PATH: {name}"))
}
