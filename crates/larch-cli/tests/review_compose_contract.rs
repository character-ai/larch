#[rustfmt::skip]
mod tests {
// Frozen composer contracts stay compact enough for #8445's explicit line budget.
use std::{fs, path::Path, process::Command};
use assert_cmd::Command as AssertCommand;
use predicates::prelude::*;
use serde_json::Value;
use tempfile::TempDir;
fn larch() -> AssertCommand { AssertCommand::cargo_bin("larch").expect("larch binary") }
fn write(path: &Path, text: &str) { fs::create_dir_all(path.parent().expect("parent")).expect("create parent"); fs::write(path, text).expect("write fixture"); }
#[test]
fn compose_findings_preserves_argparse_forms() { let fixture = TempDir::new().expect("fixture"); let output = fixture.path().join("findings.jsonl"); larch().args(["review", "compose-findings", "--issue=8445"]) .arg(format!("--output={}", output.display()))
        .assert().success().stdout(predicates::str::contains("COMPOSED=true\n")); larch().args(["review", "compose-findings", "--issue"]) .assert().code(2).stdout("")
        .stderr(predicates::str::contains("usage: compose-findings").and(predicates::str::contains("compose-findings: error: argument --issue: expected one argument"))); larch().args(["review", "compose-findings", "--issue", "1", "--output", output.to_str().expect("output"), "--unexpected"])
        .assert().code(2).stdout("") .stderr(predicates::str::contains("compose-findings: error: unrecognized arguments: --unexpected")); larch().args(["review", "compose-findings", "--help"]) .assert().success().stderr("")
        .stdout("usage: compose-findings [-h] [--design-artifacts-dir DESIGN_ARTIFACTS_DIR]\n                        [--implement-tmpdir IMPLEMENT_TMPDIR] --issue ISSUE\n                        --output OUTPUT [--archive-dir ARCHIVE_DIR]\n                        [--archive-threshold ARCHIVE_THRESHOLD]\n\noptions:\n  -h, --help            show this help message and exit\n  --design-artifacts-dir DESIGN_ARTIFACTS_DIR\n  --implement-tmpdir IMPLEMENT_TMPDIR\n  --issue ISSUE\n  --output OUTPUT\n  --archive-dir ARCHIVE_DIR\n  --archive-threshold ARCHIVE_THRESHOLD\n");
}
#[test]
fn compose_findings_emits_the_frozen_record_shape() { let fixture = TempDir::new().expect("fixture"); let implement = fixture.path().join("implement");
    write(&implement.join("round-1/accepted-findings.md"), "### FINDING_1: correctness: src/lib.rs: broken\n- **Reviewer(s)**: codex-correctness\n- **Severity**: major\n- **Focus area**: correctness\n- **Concern**: broken path\n"); let output = fixture.path().join("findings.jsonl");
    larch().args(["review", "compose-findings", "--implement-tmpdir"]) .arg(&implement).args(["--issue", "8445", "--output"]).arg(&output) .assert().success().stdout(predicates::str::contains("FINDINGS_TOTAL=1\n"));
    let record: Value = serde_json::from_str(fs::read_to_string(output).expect("output").trim()).expect("record"); assert_eq!(record["id"], "FINDING_1"); assert_eq!(record["phase"], "code-review"); assert_eq!(record["outcome"], "accepted"); assert_eq!(record["category"], "correctness"); }
#[cfg(unix)]
#[test]
fn compose_findings_rejects_symlink_artifacts() { use std::os::unix::fs::symlink; let fixture = TempDir::new().expect("fixture"); let implement = fixture.path().join("implement"); fs::create_dir_all(implement.join("round-1")).expect("round"); let outside = fixture.path().join("outside.md");
    write(&outside, "### FINDING_1: outside\n"); symlink(&outside, implement.join("round-1/accepted-findings.md")).expect("symlink"); let output = fixture.path().join("findings.jsonl"); larch().args(["review", "compose-findings", "--implement-tmpdir"]) .arg(&implement).args(["--issue", "8445", "--output"]).arg(&output)
        .assert().code(2).stdout(predicates::str::contains("FAILED=true\n").and(predicates::str::contains("cannot read artifact"))); assert!(!output.exists()); }
#[cfg(unix)]
#[test]
fn compose_findings_reuses_the_validated_gate_b_owner() { use std::os::unix::fs::PermissionsExt as _; let fixture = TempDir::new().expect("fixture"); let plugin = fixture.path().join("plugin"); let script = plugin.join("scripts/larch.sh");
    write(&script, "#!/bin/sh\n[ \"$1:$2\" = \"plan-review:filter-gate-b-skipped\" ] || exit 9\nprintf '%s\\n' '### FINDING_1: correctness: keep' '- **Reviewer(s)**: codex-plan-correctness' '- **Concern**: keep'\n"); fs::set_permissions(&script, fs::Permissions::from_mode(0o755)).expect("mode");
    let design = fixture.path().join("design"); write(&design.join("accepted-plan-findings.md"), "### FINDING_1: correctness: keep\n- **Reviewer(s)**: codex-plan-correctness\n- **Concern**: keep\n\n### FINDING_2: correctness: skip\n- **Reviewer(s)**: codex-plan-correctness\n- **Concern**: skip\n");
    write(&design.join("rejected-findings.md"), "### FINDING_2: skip\n- Reason: rejected by user during one-by-one review\n"); let output = fixture.path().join("findings.jsonl"); let result = Command::new(env!("CARGO_BIN_EXE_larch")) .env("CLAUDE_PLUGIN_ROOT", plugin)
        .args(["review", "compose-findings", "--design-artifacts-dir"]).arg(&design) .args(["--issue", "8445", "--output"]).arg(&output).output().expect("compose"); assert!(result.status.success(), "{}", String::from_utf8_lossy(&result.stderr)); let text = fs::read_to_string(output).expect("output");
    assert!(text.contains("FINDING_1")); assert!(!text.contains("FINDING_2")); }
}
