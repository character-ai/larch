//! Process-boundary contracts for the Rust-owned execution-issue verbs.

use assert_cmd::Command;
use std::{fs, os::unix::fs::PermissionsExt, path::Path};
use tempfile::TempDir;

fn command() -> Command {
    Command::cargo_bin("larch").expect("larch binary")
}

fn install_bootstrap_stub(root: &Path) -> std::path::PathBuf {
    let plugin_root = root.join("plugin");
    let scripts = plugin_root.join("scripts");
    fs::create_dir_all(&scripts).expect("stub scripts");
    fs::create_dir_all(plugin_root.join(".claude-plugin")).expect("stub plugin metadata");
    fs::write(
        plugin_root.join(".claude-plugin/plugin.json"),
        r#"{"version":"1.2.3"}"#,
    )
    .expect("stub plugin version");
    let bootstrap = scripts.join("larch.sh");
    fs::write(
        &bootstrap,
        r#"#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$@" >"$CLAUDE_PLUGIN_ROOT/reentry.args"
if [ "$1 $2" = "tracking-issue upsert-summary" ]; then
  shift 2
  content_file=
  while (( $# > 0 )); do
    case "$1" in
      --content-file) content_file=$2; shift 2 ;;
      *) shift ;;
    esac
  done
  test -n "$content_file"
  cp "$content_file" "$CLAUDE_PLUGIN_ROOT/published-summary.md"
  printf 'COMMENT_URL=https://example.test/comment/1\n'
  exit 0
fi
log_root=
run_id=
record_file=
while (( $# > 0 )); do
  case "$1" in
    --log-root) log_root=$2; shift 2 ;;
    --run-id) run_id=$2; shift 2 ;;
    --record-file) record_file=$2; shift 2 ;;
    *) shift ;;
  esac
done
test -n "$log_root" -a -n "$run_id" -a -n "$record_file"
batch="$log_root/implement/$run_id/execution-issues.ndjson"
mkdir -p "$(dirname "$batch")"
cat "$record_file" >>"$batch"
printf 'LOG_WRITTEN=true\n'
"#,
    )
    .expect("stub bootstrap");
    let mut permissions = fs::metadata(&bootstrap)
        .expect("stub metadata")
        .permissions();
    permissions.set_mode(0o755);
    fs::set_permissions(&bootstrap, permissions).expect("executable stub");
    plugin_root
}

fn assert_append_reentry(plugin_root: &Path, log_root: &Path, session: &Path) {
    let reentry = fs::read_to_string(plugin_root.join("reentry.args")).expect("re-entry arguments");
    let reentry: Vec<&str> = reentry.lines().collect();
    assert_eq!(
        reentry.get(..11),
        Some(
            [
                "run-log",
                "append",
                "--log-root",
                log_root.to_str().expect("log root"),
                "--skill",
                "implement",
                "--run-id",
                "run-1",
                "--batch",
                "execution-issues",
                "--record-file",
            ]
            .as_slice()
        )
    );
    let reentry_record = Path::new(reentry.get(11).expect("record file argument"));
    assert_eq!(reentry_record.parent(), Some(session));
    assert!(
        reentry_record
            .file_name()
            .and_then(|name| name.to_str())
            .is_some_and(|name| name.starts_with(".flush-execution-issues-append.")
                && name.ends_with(".log.records"))
    );
}

#[test]
fn append_preserves_the_quiet_wire_and_offers_a_typed_status_wire() {
    let directory = TempDir::new().expect("sandbox");
    let root = fs::canonicalize(directory.path()).expect("canonical sandbox");
    let log = root.join("execution-issues.md");

    command()
        .args([
            "execution-issues",
            "append",
            "--log",
            log.to_str().expect("path"),
            "--category",
            "Warnings",
            "--entry",
            "- first",
        ])
        .assert()
        .success()
        .stdout("")
        .stderr("");
    command()
        .args([
            "execution-issues",
            "append",
            "--log",
            log.to_str().expect("path"),
            "--category",
            "Warnings",
            "--entry",
            "- first\n- second",
            "--report-status",
        ])
        .assert()
        .success()
        .stdout("APPEND_STATUS=appended\n")
        .stderr("");
    command()
        .args([
            "execution-issues",
            "append",
            "--log",
            log.to_str().expect("path"),
            "--category",
            "Warnings",
            "--entry",
            "- first\n- second",
            "--report-status",
        ])
        .assert()
        .success()
        .stdout("APPEND_STATUS=duplicate\n")
        .stderr("");

    let text = fs::read_to_string(log).expect("ledger");
    assert_eq!(text.lines().filter(|line| *line == "- first").count(), 1);
    assert_eq!(text.lines().filter(|line| *line == "- second").count(), 1);

    command()
        .current_dir(&root)
        .args([
            "execution-issues",
            "append",
            "--log",
            "relative.md",
            "--entry",
            "- relative",
        ])
        .assert()
        .success()
        .stdout("")
        .stderr("");
    assert_eq!(
        fs::read_to_string(root.join("relative.md")).expect("relative ledger"),
        "### Tool Failures\n- relative\n"
    );
}

#[test]
fn append_ignores_malformed_batch_rows_and_refuses_hostile_paths() {
    let directory = TempDir::new().expect("sandbox");
    let root = fs::canonicalize(directory.path()).expect("canonical sandbox");
    let log = root.join("execution-issues.md");
    let batch = root.join("execution-issues.ndjson");
    fs::write(
        &batch,
        "malformed\n{\"body\":\"- durable\\n\",\"category\":\"Warnings\"}\n",
    )
    .expect("batch");

    command()
        .args([
            "execution-issues",
            "append",
            "--log",
            log.to_str().expect("path"),
            "--category",
            "Warnings",
            "--entry",
            "- durable\n- new",
            "--existing-batch",
            batch.to_str().expect("path"),
            "--report-status",
        ])
        .assert()
        .success()
        .stdout("APPEND_STATUS=appended\n")
        .stderr("");
    assert_eq!(
        fs::read_to_string(&log).expect("ledger"),
        "### Warnings\n- new\n"
    );

    let linked_batch = root.join("linked.ndjson");
    std::os::unix::fs::symlink(&batch, &linked_batch).expect("symlink");
    command()
        .args([
            "execution-issues",
            "append",
            "--log",
            log.to_str().expect("path"),
            "--entry",
            "- hostile",
            "--existing-batch",
            linked_batch.to_str().expect("path"),
            "--report-status",
        ])
        .assert()
        .code(1)
        .stdout("")
        .stderr(format!(
            "cli.py execution-issues append: error: refusing to read non-regular execution-issues batch: {}\n",
            linked_batch.display()
        ));
}

#[test]
fn flush_safety_net_and_refresh_pin_local_wires_and_exit_codes() {
    let directory = TempDir::new().expect("sandbox");
    let root = fs::canonicalize(directory.path()).expect("canonical sandbox");
    let log_root = root.join("larch-logs");
    let session = root.join("session");
    let issue_log = session.join("execution-issues.md");
    let records = root.join("records.ndjson");
    fs::create_dir_all(&log_root).expect("log root");
    fs::create_dir_all(&session).expect("session");
    fs::write(&issue_log, "### Warnings\n- warning\n").expect("ledger");

    command()
        .args([
            "execution-issues",
            "flush-safety-net",
            "--log-root",
            log_root.to_str().expect("path"),
            "--run-id",
            "run-1",
            "--issue-log",
            issue_log.to_str().expect("path"),
            "--record-file",
            records.to_str().expect("path"),
        ])
        .assert()
        .success()
        .stdout("FLUSH_STATUS=rendered\nRECORDS=1\n")
        .stderr("");
    assert!(
        fs::read_to_string(&records)
            .expect("records")
            .contains("\"category\":\"Warnings\"")
    );

    fs::write(&issue_log, "").expect("empty ledger");
    command()
        .args([
            "execution-issues",
            "flush",
            "--log-root",
            log_root.to_str().expect("path"),
            "--run-id",
            "run-1",
            "--issue-log",
            issue_log.to_str().expect("path"),
        ])
        .assert()
        .success()
        .stdout("FLUSH_STATUS=skip\nRECORDS=0\n")
        .stderr("");

    fs::write(
        session.join("parent-issue.md"),
        "ISSUE_NUMBER=0\nRUN_ID=run-1\n",
    )
    .expect("parent issue");
    command()
        .args([
            "execution-issues",
            "refresh",
            "--implement-tmpdir",
            session.to_str().expect("path"),
        ])
        .assert()
        .success()
        .stdout("REFRESHED=true\nREASON=issue-not-set\n")
        .stderr("");

    command()
        .args([
            "execution-issues",
            "flush",
            "--log-root",
            "relative",
            "--run-id",
            "bad_slug",
        ])
        .assert()
        .code(2)
        .stdout(concat!(
            "FLUSH_STATUS=failed\n",
            "RECORDS=0\n",
            "APPEND_LOG_FILE=--log-root must be absolute\n",
            "ERROR=--log-root must be absolute\n"
        ))
        .stderr("");
}

#[test]
fn ordinary_flush_reenters_the_bootstrap_and_publishes_durably() {
    let directory = TempDir::new().expect("sandbox");
    let root = fs::canonicalize(directory.path()).expect("canonical sandbox");
    let log_root = root.join("larch-logs");
    let session = root.join("session");
    let issue_log = session.join("execution-issues.md");
    fs::create_dir_all(&log_root).expect("log root");
    fs::create_dir_all(&session).expect("session");
    fs::write(&issue_log, "### Warnings\n- first\n").expect("ledger");
    let plugin_root = install_bootstrap_stub(&root);

    let output = command()
        .env("CLAUDE_PLUGIN_ROOT", &plugin_root)
        .args([
            "execution-issues",
            "flush",
            "--log-root",
            log_root.to_str().expect("path"),
            "--run-id",
            "run-1",
            "--issue-log",
            issue_log.to_str().expect("path"),
        ])
        .output()
        .expect("ordinary flush");
    let stdout = String::from_utf8(output.stdout.clone()).expect("UTF-8 stdout");
    let rows: Vec<&str> = stdout.lines().collect();
    let append_log = rows
        .get(2)
        .and_then(|row| row.strip_prefix("APPEND_LOG_FILE="))
        .unwrap_or_default();
    let append_capture = fs::read_to_string(append_log).unwrap_or_default();
    assert!(
        output.status.success(),
        "status={} stdout={} stderr={} append={}",
        output.status,
        stdout,
        String::from_utf8_lossy(&output.stderr),
        append_capture,
    );
    assert_eq!(rows.first(), Some(&"FLUSH_STATUS=ok"));
    assert_eq!(rows.get(1), Some(&"RECORDS=1"));
    let append_log = rows
        .get(2)
        .and_then(|row| row.strip_prefix("APPEND_LOG_FILE="))
        .expect("append log row");
    assert!(Path::new(append_log).is_file());
    assert_append_reentry(&plugin_root, &log_root, &session);
    assert_eq!(fs::read_to_string(&issue_log).expect("cleared ledger"), "");
    let batch = log_root.join("implement/run-1/execution-issues.ndjson");
    assert!(
        fs::read_to_string(&batch)
            .expect("durable batch")
            .contains("\"body\":\"- first\\n\"")
    );

    fs::write(&issue_log, "### CI Issues\n- second\n").expect("second ledger");
    let safety = command()
        .env("CLAUDE_PLUGIN_ROOT", &plugin_root)
        .args([
            "execution-issues",
            "flush-safety-net",
            "--log-root",
            log_root.to_str().expect("path"),
            "--run-id",
            "run-1",
            "--issue-log",
            issue_log.to_str().expect("path"),
        ])
        .output()
        .expect("safety-net flush");
    assert!(
        safety.status.success(),
        "{}",
        String::from_utf8_lossy(&safety.stderr)
    );
    assert!(String::from_utf8_lossy(&safety.stdout).starts_with("FLUSH_STATUS=ok\nRECORDS=1\n"));
    assert_eq!(
        fs::read_to_string(&issue_log).expect("retained safety-net ledger"),
        "### CI Issues\n- second\n"
    );
    assert!(
        fs::read_to_string(batch)
            .expect("updated batch")
            .contains("\"body\":\"- second\\n\"")
    );
}

#[test]
fn refresh_restores_the_exact_pre_cutover_summary_rows() {
    let directory = TempDir::new().expect("sandbox");
    let root = fs::canonicalize(directory.path()).expect("canonical sandbox");
    let session = root.join("session");
    fs::create_dir_all(&session).expect("session");
    fs::write(
        session.join("parent-issue.md"),
        "ISSUE_NUMBER=42\nRUN_ID=run-1\n",
    )
    .expect("parent issue");
    fs::write(
        session.join("session-env.sh"),
        "REPO=owner/name\nAGENT=claude\nCODER=codex\n",
    )
    .expect("session env");
    fs::write(
        session.join("execution-issues.md"),
        "### Warnings\n\n- first\n- second\n",
    )
    .expect("execution issues");
    let plugin_root = install_bootstrap_stub(&root);

    command()
        .env("CLAUDE_PLUGIN_ROOT", &plugin_root)
        .args([
            "execution-issues",
            "refresh",
            "--implement-tmpdir",
            session.to_str().expect("session path"),
        ])
        .assert()
        .success()
        .stdout("REFRESHED=true\n")
        .stderr("");

    assert_eq!(
        fs::read_to_string(plugin_root.join("published-summary.md")).expect("published summary"),
        concat!(
            "Run ID: `run-1`\n",
            "Run log: provider `unknown`, skill `implement`, run ID `run-1`\n",
            "Tracking issue: #42\n",
            "Agent: `claude`\n",
            "Coder: `codex`\n",
            "Larch version: `1.2.3`\n",
            "Execution issues pending flush: `2`\n",
        )
    );
}
