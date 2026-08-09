use std::{collections::BTreeMap, fs};

use assert_cmd::Command as AssertCommand;
use larch_core::{KvDocument, ParseOptions};
use larch_test_support::{RunLogFixture, RunLogTree};
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
        "large_integer=00018446744073709551616000000000000000000000".to_owned(),
        "--field".to_owned(),
        "z_extension=snowman ☃".to_owned(),
    ]
}

#[test]
fn manifest_command_updates_full_run_log_tree() {
    let tree = RunLogTree::builder(RunLogFixture::PartialStaging)
        .build()
        .expect("Rust fixture should build");
    let arguments = manifest_arguments(&tree);

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
    let manifest_path = tree.run_dir().join("manifest.json");
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

    let manifest: Value =
        serde_json::from_slice(&manifest_bytes).expect("manifest JSON should parse");
    assert_eq!(manifest["status"], Value::String("True".to_owned()));
    assert_eq!(manifest["steps_ran"]["step8"], Value::Bool(true));
    assert_eq!(manifest["pr_number"], Value::from(17));
    let large_integer: Value = serde_json::from_str("18446744073709551616000000000000000000000")
        .expect("large JSON integer should parse");
    assert_eq!(manifest["large_integer"], large_integer);
    assert_eq!(
        manifest["z_extension"],
        Value::String("snowman ☃".to_owned())
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
    let stdout = String::from_utf8_lossy(stdout);
    KvDocument::parse(&stdout, ParseOptions::legacy())
        .expect("manifest envelope should be valid KEY=value output")
        .rows()
        .iter()
        .map(|row| (row.key().to_owned(), row.value().to_owned()))
        .collect()
}
