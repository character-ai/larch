//! CLI coverage for the #8107 vendor-config / wrap / announcement commands.

use std::{
    fs,
    io::{Read as _, Write as _},
    net::TcpListener,
    path::Path,
    sync::mpsc,
    thread,
    time::Duration,
};

use assert_cmd::Command as AssertCommand;
use predicates::prelude::*;
use tempfile::TempDir;

fn larch() -> AssertCommand {
    AssertCommand::cargo_bin("larch").expect("larch binary should build")
}

fn write(path: &Path, contents: &str) {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).expect("create fixture parent");
    }
    fs::write(path, contents).expect("write fixture");
}

#[test]
fn model_args_emits_cursor_and_codex_tokens() {
    larch()
        .env_remove("LARCH_CURSOR_MODEL")
        .env_remove("CLAUDE_PLUGIN_OPTION_CURSOR_MODEL")
        .args(["agent", "model-args", "--tool", "cursor"])
        .assert()
        .success()
        .stdout("--model\ncomposer-2.5\n");

    larch()
        .env_remove("LARCH_CODEX_MODEL")
        .env_remove("CLAUDE_PLUGIN_OPTION_CODEX_MODEL")
        .env_remove("LARCH_CODEX_EFFORT")
        .args(["agent", "model-args", "--tool", "codex", "--with-effort"])
        .assert()
        .success()
        .stdout(predicate::str::starts_with(
            "-m\ngpt-5.6-sol\n-c\nmodel_reasoning_effort=\"high\"\n",
        ));

    larch()
        .env("LARCH_CODEX_MODEL", "   ")
        .args(["agent", "model-args", "--tool", "codex"])
        .assert()
        .code(1)
        .stderr(predicate::str::contains("must not be blank"));

    larch()
        .args(["agent", "model-args", "--tool", "nope"])
        .assert()
        .code(1)
        .stderr(predicate::str::contains("must be 'cursor' or 'codex'"));
}

#[test]
fn cursor_wrap_prompt_and_registry_cover_stdout_shapes() {
    larch()
        .args(["agent", "cursor-wrap-prompt", "hello"])
        .assert()
        .success()
        .stdout(" /max-mode on. Prompt: hello");

    larch()
        .args(["agent", "cursor-wrap-prompt"])
        .assert()
        .code(1)
        .stderr(predicate::str::contains("single prompt argument"));

    larch()
        .args(["agent", "external-tool-registry"])
        .assert()
        .success()
        .stdout("EXTERNAL_TOOLS=codex,cursor\nIMPLEMENTER_CODERS=claude,codex,cursor\n");

    larch()
        .args([
            "agent",
            "external-tool-registry",
            "--kind",
            "external-tools",
        ])
        .assert()
        .success()
        .stdout("codex\ncursor\n");

    larch()
        .args([
            "agent",
            "external-tool-registry",
            "--kind",
            "implementer-coders",
        ])
        .assert()
        .success()
        .stdout("claude\ncodex\ncursor\n");

    larch()
        .args(["agent", "external-tool-registry", "--kind", "bogus"])
        .assert()
        .code(1)
        .stderr(predicate::str::contains("unsupported --kind"));
}

#[test]
fn read_claude_model_prefers_source_file_transcript() {
    let fixture = TempDir::new().expect("fixture");
    let transcript = fixture.path().join("session.jsonl");
    write(
        &transcript,
        r#"{"type":"assistant","message":{"model":"claude-test-model"}}
"#,
    );
    let source = fixture.path().join("source.txt");
    write(
        &source,
        &format!("TRANSCRIPT_PATH={}\n", transcript.display()),
    );

    larch()
        .env("LARCH_CLAUDE_SOURCE_FILE", source.as_os_str())
        .args(["agent", "read-claude-model"])
        .assert()
        .success()
        .stdout("CLAUDE_MODEL=claude-test-model\n");
}

#[test]
fn external_defaults_docs_role_and_resolve_vendor() {
    larch()
        .args(["external-defaults", "docs"])
        .assert()
        .success()
        .stdout(predicate::str::starts_with("DOC_ROW_COUNT="))
        .stdout(predicate::str::contains("DOC_ROW="));

    larch()
        .args(["external-defaults", "docs", "extra"])
        .assert()
        .code(2)
        .stderr(predicate::str::contains("no arguments expected"));

    larch()
        .args([
            "external-defaults",
            "role",
            "--role",
            "implement.step2_coder",
        ])
        .assert()
        .success()
        .stdout(predicate::str::contains("ROLE=implement.step2_coder"))
        .stdout(predicate::str::contains("KIND="));

    larch()
        .args(["external-defaults", "role", "--role", "missing.role"])
        .assert()
        .code(2)
        .stderr(predicate::str::contains("ERROR="));

    larch()
        .args([
            "external-defaults",
            "resolve-vendor",
            "--role",
            "design.plan_drafter",
            "--codex-present",
            "true",
            "--cursor-present",
            "false",
        ])
        .assert()
        .success()
        .stdout(predicate::str::contains("VENDOR=codex"));
}

#[test]
fn slack_issue_announce_covers_required_paths_and_http_post() {
    let fixture = TempDir::new().expect("fixture");
    let tmpdir = fixture.path().join("implement");
    fs::create_dir_all(&tmpdir).expect("tmpdir");

    larch()
        .args(["slack", "issue-announce"])
        .assert()
        .code(2)
        .stdout(predicate::str::contains("STATUS=failed"))
        .stdout(predicate::str::contains("--implement-tmpdir is required"));

    larch()
        .args([
            "slack",
            "issue-announce",
            "--implement-tmpdir",
            tmpdir.to_str().expect("utf8"),
        ])
        .env_remove("LARCH_SLACK_WEBHOOK_URL")
        .assert()
        .success()
        .stdout(predicate::str::contains("STATUS=skipped"));

    write(
        &tmpdir.join("parent-issue.md"),
        "ISSUE_NUMBER=8107\nRUN_ID=run-1\n",
    );
    write(
        &tmpdir.join("ship-pr-state.sh"),
        "PR_URL=https://example.test/pr/1\nPR_TITLE=announce\n",
    );
    write(&tmpdir.join("session-id"), "sess-1\n");

    let listener = TcpListener::bind("127.0.0.1:0").expect("bind");
    let addr = listener.local_addr().expect("addr");
    let (tx, rx) = mpsc::channel();
    thread::spawn(move || {
        let (mut stream, _) = listener.accept().expect("accept");
        let mut buf = [0_u8; 4096];
        let _ = stream.read(&mut buf);
        let _ = stream.write_all(b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n");
        let _ = tx.send(());
    });

    let webhook = format!("http://{addr}/hooks/secret-token");
    larch()
        .env("LARCH_SLACK_WEBHOOK_URL", &webhook)
        .args([
            "slack",
            "issue-announce",
            "--implement-tmpdir",
            tmpdir.to_str().expect("utf8"),
        ])
        .assert()
        .success()
        .stdout("STATUS=posted\n")
        .stdout(predicate::str::contains("secret-token").not());
    rx.recv_timeout(Duration::from_secs(2))
        .expect("webhook request received");

    // Bad scheme fails closed; --best-effort still exits 0.
    larch()
        .env("LARCH_SLACK_WEBHOOK_URL", "ftp://example.test/hook")
        .args([
            "slack",
            "issue-announce",
            "--implement-tmpdir",
            tmpdir.to_str().expect("utf8"),
            "--best-effort",
        ])
        .assert()
        .success()
        .stdout(predicate::str::contains("STATUS=failed"));
}
