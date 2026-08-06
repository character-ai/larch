use std::{
    env, fs,
    path::{Path, PathBuf},
    process::Command,
};

#[cfg(unix)]
use std::os::unix::fs::PermissionsExt as _;

use assert_cmd::Command as AssertCommand;
use predicates::prelude::*;
use tempfile::TempDir;

fn larch() -> AssertCommand {
    AssertCommand::cargo_bin("larch").expect("larch binary should build")
}

fn write(path: &Path, contents: &str) {
    let parent = path.parent().expect("fixture path has parent");
    fs::create_dir_all(parent).expect("create fixture parent");
    fs::write(path, contents).expect("write fixture");
}

#[cfg(unix)]
fn vendor_fixture(root: &Path, name: &str, body: &str) -> PathBuf {
    use std::os::unix::fs::PermissionsExt as _;

    let bin = root.join("bin");
    fs::create_dir_all(&bin).expect("fixture bin");
    let executable = bin.join(name);
    write(&executable, body);
    fs::set_permissions(&executable, fs::Permissions::from_mode(0o755))
        .expect("fixture executable permissions");
    executable
}

#[cfg(unix)]
fn larch_with_fixture_vendor(root: &Path) -> AssertCommand {
    let current_path = env::var_os("PATH").unwrap_or_default();
    let mut command = larch();
    let path =
        env::join_paths(std::iter::once(root.join("bin")).chain(env::split_paths(&current_path)))
            .expect("fixture PATH");
    command.env("PATH", path);
    command.current_dir(root);
    command
}

fn classify(plugin: &Path, diff: &Path) -> AssertCommand {
    let mut command = larch();
    command
        .env("CLAUDE_PLUGIN_ROOT", plugin)
        .args(["agent", "classify-diff"])
        .arg(diff);
    command
}

#[test]
fn classify_diff_covers_modes_mixed_changes_and_bad_manifests() {
    let fixture = TempDir::new().expect("fixture");
    let plugin = fixture.path().join("plugin");
    write(
        &plugin.join("scripts/generators.tsv"),
        "generate code-reviewer-agent\tagents/generated.md\n",
    );
    let cases = [
        ("docs", "diff --git a/docs/a.md b/docs/a.md\n", "docs-only"),
        (
            "test",
            "diff --git a/scripts/test-a.sh b/scripts/test-a.sh\n",
            "test-only",
        ),
        (
            "generated",
            "diff --git a/agents/generated.md b/agents/generated.md\n",
            "generated-only",
        ),
        (
            "mixed",
            "diff --git a/docs/a.md b/docs/a.md\ndiff --git a/scripts/test-a.sh b/scripts/test-a.sh\n",
            "generic",
        ),
        (
            "unsafe",
            "diff --git a/docs/../a.md b/docs/../a.md\n",
            "generic",
        ),
    ];
    for (name, diff, mode) in cases {
        let diff_path = fixture.path().join(format!("{name}.diff"));
        write(&diff_path, diff);
        classify(&plugin, &diff_path)
            .assert()
            .success()
            .stdout(format!("DIFF_MODE={mode}\n"));
    }

    let missing_plugin = fixture.path().join("missing-plugin");
    let diff_path = fixture.path().join("missing.diff");
    write(&diff_path, "diff --git a/docs/a.md b/docs/a.md\n");
    classify(&missing_plugin, &diff_path)
        .assert()
        .code(1)
        .stderr(predicate::str::contains(
            "scripts/generators.tsv is missing or unsafe",
        ));
    write(&plugin.join("scripts/generators.tsv"), "generate\t \n");
    classify(&plugin, &diff_path)
        .assert()
        .code(1)
        .stderr(predicate::str::contains(
            "contains an empty required column",
        ));
}

#[test]
fn wait_reviewers_preserves_validation_and_completion_rows() {
    let fixture = TempDir::new().expect("fixture");
    let done = fixture.path().join("done.done");
    let empty = fixture.path().join("empty.done");
    let missing = fixture.path().join("missing.done");
    write(&done, "0\n");
    write(&empty, "\n");
    larch()
        .env("WAIT_FOR_REVIEWERS_POLL_INTERVAL", "0.01")
        .args(["agent", "wait-reviewers", "--timeout", "1"])
        .arg(&done)
        .arg(&empty)
        .arg(&missing)
        .assert()
        .success()
        .stdout("DONE 1 done: exit=0\nDONE 2 empty: exit=unknown\nTIMEOUT 3 missing\n");
    larch()
        .args(["agent", "wait-reviewers", "--timeout", "00"])
        .arg(&done)
        .assert()
        .code(1)
        .stderr(predicate::str::contains("must be a positive integer"));
    for invalid_timeout in ["0", "000", "abc"] {
        larch()
            .args(["agent", "wait-reviewers", "--timeout", invalid_timeout])
            .arg(&done)
            .assert()
            .code(1)
            .stderr(predicate::str::contains("must be a positive integer"));
    }
    larch()
        .env("WAIT_FOR_REVIEWERS_POLL_INTERVAL", "00")
        .args(["agent", "wait-reviewers"])
        .arg(&done)
        .assert()
        .code(1)
        .stderr(predicate::str::contains("WAIT_FOR_REVIEWERS_POLL_INTERVAL"));
}

#[cfg(unix)]
#[test]
fn run_external_agent_writes_legacy_artifacts_and_failure_diagnostics() {
    let fixture = TempDir::new().expect("fixture");
    let _vendor = vendor_fixture(
        fixture.path(),
        "claude",
        "#!/bin/sh\nprintf 'stdout line\\n'\nprintf 'stderr line\\n' >&2\nexit 3\n",
    );
    let output = fixture.path().join("agent.out");
    larch_with_fixture_vendor(fixture.path())
        .args([
            "agent",
            "run-external-agent",
            "--tool",
            "claude",
            "--output",
        ])
        .arg(&output)
        .args(["--timeout", "5", "--capture-stdout-only", "--stderr-sink"])
        .arg(fixture.path().join("sink.log"))
        .args(["--", "claude"])
        .assert()
        .code(3);
    assert_eq!(
        fs::read_to_string(&output).expect("stdout artifact"),
        "stdout line\n"
    );
    assert_eq!(
        fs::read_to_string(format!("{}.diag", output.display())).expect("diag artifact"),
        "stderr line\nFailed with exit code 3. Output size: 12 bytes.\n"
    );
    assert_eq!(
        fs::read_to_string(format!("{}.done", output.display())).expect("done artifact"),
        "3\n"
    );
    assert_eq!(
        fs::read_to_string(format!("{}.meta", output.display())).expect("meta artifact"),
        format!(
            "TOOL=claude\nTIMEOUT=5\nCAPTURE_STDOUT=false\nCAPTURE_STDOUT_ONLY=true\nOUTPUT_FILE={}\nSTDERR_SINK={}\nCMD_JSON=[\"claude\"]\n",
            output.display(),
            fixture.path().join("sink.log").display(),
        )
    );
    assert_eq!(
        fs::read_to_string(format!("{}.stderr-tail", output.display()))
            .expect("stderr tail artifact"),
        "stderr line\nFailed with exit code 3. Output size: 12 bytes.\n"
    );
    assert!(PathBuf::from(format!("{}.failure-diag", output.display())).is_file());
}

#[test]
fn run_external_agent_rejects_invalid_arguments_before_creating_sidecars() {
    let fixture = TempDir::new().expect("fixture");
    let unsafe_output = fixture.path().join("bad\nout.txt");
    larch()
        .args([
            "agent",
            "run-external-agent",
            "--tool",
            "claude",
            "--output",
        ])
        .arg(&unsafe_output)
        .args(["--timeout", "5", "--", "claude"])
        .assert()
        .code(1)
        .stderr(predicate::str::contains(
            "ERROR: --output contains unsupported characters",
        ));
    assert!(!unsafe_output.exists());
    assert!(!PathBuf::from(format!("{}.done", unsafe_output.display())).exists());
    assert!(!PathBuf::from(format!("{}.meta", unsafe_output.display())).exists());

    let output = fixture.path().join("out.txt");
    larch()
        .args([
            "agent",
            "run-external-agent",
            "--tool",
            "claude",
            "--output",
        ])
        .arg(&output)
        .args(["--timeout", "0", "--", "claude"])
        .assert()
        .code(1)
        .stderr(predicate::str::contains(
            "ERROR: --timeout must be a positive integer, got '0'",
        ));
    assert!(!PathBuf::from(format!("{}.done", output.display())).exists());
}

#[cfg(unix)]
#[test]
fn run_external_agent_inner_sentinel_replaces_stale_artifacts() {
    let fixture = TempDir::new().expect("fixture");
    let _vendor = vendor_fixture(
        fixture.path(),
        "claude",
        "#!/bin/sh\nprintf 'fresh output\\n'\n",
    );
    let output = fixture.path().join("agent.out");
    write(&output, "stale output\n");
    write(&PathBuf::from(format!("{}.done", output.display())), "99\n");
    write(
        &PathBuf::from(format!("{}.inner.done", output.display())),
        "98\n",
    );
    larch_with_fixture_vendor(fixture.path())
        .env("RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX", ".inner.done")
        .args([
            "agent",
            "run-external-agent",
            "--tool",
            "claude",
            "--output",
        ])
        .arg(&output)
        .args(["--timeout", "5", "--capture-stdout", "--", "claude"])
        .assert()
        .success();
    assert_eq!(
        fs::read_to_string(&output).expect("fresh output"),
        "fresh output\n"
    );
    assert!(!PathBuf::from(format!("{}.done", output.display())).exists());
    assert_eq!(
        fs::read_to_string(format!("{}.inner.done", output.display()))
            .expect("inner completion sentinel"),
        "0\n"
    );
}

#[cfg(unix)]
#[test]
fn run_external_agent_fast_fails_a_codex_policy_rejection() {
    let fixture = TempDir::new().expect("fixture");
    let _vendor = vendor_fixture(
        fixture.path(),
        "codex",
        "#!/bin/sh\nprintf 'error=exec_command failed for bash: CreateProcess {\"message\":\"Rejected(blocked by policy)\"}\\n'\nwhile :; do sleep 1; done\n",
    );
    let output = fixture.path().join("codex.out");
    larch_with_fixture_vendor(fixture.path())
        .env("RUN_EXTERNAL_AGENT_POLL_INTERVAL", "0.02")
        .args(["agent", "run-external-agent", "--tool", "codex", "--output"])
        .arg(&output)
        .args(["--timeout", "30", "--capture-stdout-only", "--", "codex"])
        .assert()
        .code(1);
    let diag = fs::read_to_string(format!("{}.diag", output.display())).expect("policy diag");
    assert!(diag.contains("FAILURE_CLASS=policy-rejection"));
    assert!(diag.contains("POLICY_REJECTION=true"));
    assert!(diag.contains("Rejected(blocked by policy)"));
    assert_eq!(
        fs::read_to_string(format!("{}.done", output.display())).expect("policy done"),
        "1\n"
    );
}

#[cfg(unix)]
#[test]
fn run_external_agent_marks_a_completed_codex_policy_rejection() {
    let fixture = TempDir::new().expect("fixture");
    let _vendor = vendor_fixture(
        fixture.path(),
        "codex",
        "#!/bin/sh\nprintf 'error=exec_command failed for bash: CreateProcess {\"message\":\"Rejected(blocked by policy)\"}\\n'\n",
    );
    let output = fixture.path().join("codex.out");
    larch_with_fixture_vendor(fixture.path())
        .args(["agent", "run-external-agent", "--tool", "codex", "--output"])
        .arg(&output)
        .args(["--timeout", "5", "--capture-stdout-only", "--", "codex"])
        .assert()
        .code(1);
    let diag = fs::read_to_string(format!("{}.diag", output.display())).expect("policy diag");
    assert!(diag.contains("POLICY_REJECTION=true"));
}

#[cfg(unix)]
#[test]
fn run_external_agent_uses_typed_cursor_environment() {
    let fixture = TempDir::new().expect("fixture");
    let _vendor = vendor_fixture(
        fixture.path(),
        "cursor",
        concat!(
            "#!/bin/sh\nprintf '%s:%s\\n' \"$",
            "{NO_OPEN_BROWSER:-missing}\" \"$",
            "{CURSOR_API_KEY:-missing}\"\n",
        ),
    );
    let output = fixture.path().join("cursor.out");
    larch_with_fixture_vendor(fixture.path())
        .env("CURSOR_API_KEY", "  cursor-token  ")
        .args([
            "agent",
            "run-external-agent",
            "--tool",
            "cursor",
            "--output",
        ])
        .arg(&output)
        .args(["--timeout", "5", "--capture-stdout", "--", "cursor"])
        .assert()
        .success();
    assert_eq!(
        fs::read_to_string(output).expect("cursor output"),
        "1:cursor-token\n"
    );
}

#[cfg(unix)]
#[test]
fn run_external_agent_deadline_kills_the_whole_vendor_process_group() {
    use nix::{errno::Errno, sys::signal::kill, unistd::Pid};

    let fixture = TempDir::new().expect("fixture");
    let pid_file = fixture.path().join("pids");
    let _vendor = vendor_fixture(
        fixture.path(),
        "codex",
        "#!/bin/sh\necho \"$$\" >> pids\nsh -c 'echo \"$$\" >> pids; sh -c '\\''echo \"$$\" >> pids; while :; do sleep 1; done'\\'' & wait' &\nwhile :; do sleep 1; done\n",
    );
    let output = fixture.path().join("hung.out");
    let command_output = larch_with_fixture_vendor(fixture.path())
        .args(["agent", "run-external-agent", "--tool", "codex", "--output"])
        .arg(&output)
        .args(["--timeout", "2", "--capture-stdout", "--", "codex"])
        .output()
        .expect("run timeout fixture");
    assert_eq!(
        command_output.status.code(),
        Some(124),
        "stderr={} diag={}",
        String::from_utf8_lossy(&command_output.stderr),
        fs::read_to_string(format!("{}.diag", output.display())).unwrap_or_default(),
    );
    let pids: Vec<i32> = fs::read_to_string(&pid_file)
        .expect("vendor PID ledger")
        .lines()
        .map(|line| line.parse().expect("numeric PID"))
        .collect();
    assert_eq!(pids.len(), 3, "fixture should record a process tree");
    let mut distinct_pids = pids.clone();
    distinct_pids.sort_unstable();
    distinct_pids.dedup();
    assert_eq!(
        distinct_pids.len(),
        3,
        "fixture should record unique processes"
    );
    for _attempt in 0..50 {
        if pids
            .iter()
            .all(|pid| matches!(kill(Pid::from_raw(*pid), None), Err(Errno::ESRCH)))
        {
            return;
        }
        std::thread::sleep(std::time::Duration::from_millis(10));
    }
    let live: Vec<i32> = pids
        .into_iter()
        .filter(|pid| !matches!(kill(Pid::from_raw(*pid), None), Err(Errno::ESRCH)))
        .collect();
    assert!(live.is_empty(), "live vendor descendants: {live:?}");
}

#[test]
fn compose_collector_failure_log_redacts_and_writes_sections() {
    let fixture = TempDir::new().expect("fixture");
    let reviewer = fixture.path().join("reviewer.txt");
    let secret = format!("sk-{}", "a".repeat(24));
    let session_path = fixture.path().join("larch-implement-redact123");
    write(&reviewer, "reviewer body\n");
    write(&fixture.path().join("reviewer.txt.diag"), "diag body\n");
    write(
        &fixture.path().join("reviewer.txt.launch-stderr"),
        &format!("line one {} {secret}\nline two\n", session_path.display()),
    );
    write(
        &fixture.path().join("reviewer.txt.stderr-tail"),
        &"é".repeat(6_000),
    );
    let output = fixture.path().join("failure.log");
    larch()
        .args(["agent", "compose-collector-failure-log", "--reviewer-file"])
        .arg(&reviewer)
        .args(["--structured-record", "STATUS=FAILED", "--output"])
        .arg(&output)
        .assert()
        .success();
    let body = fs::read_to_string(&output).expect("collector output");
    assert!(body.contains("## Structured collector record"));
    assert!(body.contains("reviewer body"));
    assert!(body.contains("diag body"));
    assert!(!body.contains(&secret));
    assert!(!body.contains(&session_path.display().to_string()));
    assert!(body.contains("<REDACTED-TOKEN>"));
    assert!(body.len() < 6_000, "stderr tails must remain bounded");
    #[cfg(unix)]
    assert_eq!(
        fs::metadata(&output)
            .expect("output metadata")
            .permissions()
            .mode()
            & 0o777,
        0o600
    );
    larch()
        .args([
            "agent",
            "compose-collector-failure-log",
            "--structured-record",
            "",
        ])
        .arg("--output")
        .arg(fixture.path().join("bad.log"))
        .assert()
        .code(2)
        .stderr(predicate::str::contains("required and non-empty"));
    larch()
        .args([
            "agent",
            "compose-collector-failure-log",
            "--structured-record",
            "STATUS=FAILED",
            "--output",
            "",
        ])
        .assert()
        .code(2)
        .stderr(predicate::str::contains("--output is required"));
}

fn git_output(repository: &Path, arguments: &[&str]) -> std::process::Output {
    let output = Command::new("git")
        .args(arguments)
        .current_dir(repository)
        .output()
        .expect("run fixture git");
    assert!(
        output.status.success(),
        "git {:?} failed: {}",
        arguments,
        String::from_utf8_lossy(&output.stderr)
    );
    output
}

fn git(repository: &Path, arguments: &[&str]) {
    let _ = git_output(repository, arguments);
}

fn git_stdout(repository: &Path, arguments: &[&str]) -> String {
    String::from_utf8(git_output(repository, arguments).stdout).expect("UTF-8 git stdout")
}

fn commit(repository: &Path, path: &str, contents: &str, message: &str) {
    write(&repository.join(path), contents);
    git(repository, &["add", path]);
    git(repository, &["commit", "-m", message]);
}

#[test]
fn gather_branch_context_excludes_larch_logs() {
    let fixture = TempDir::new().expect("fixture");
    let repository = fixture.path().join("repository");
    fs::create_dir(&repository).expect("repository dir");
    git(&repository, &["init", "-b", "main"]);
    git(&repository, &["config", "user.email", "test@example.com"]);
    git(&repository, &["config", "user.name", "Test User"]);
    commit(&repository, "src/feature.txt", "v1\n", "base code");
    git(&repository, &["checkout", "-b", "feature"]);
    commit(
        &repository,
        "larch-logs/run/session.txt",
        "run log\n",
        "add run log",
    );
    commit(&repository, "src/feature.txt", "v1\nv2\n", "feature change");
    let output = fixture.path().join("context");
    fs::create_dir(&output).expect("context dir");
    larch()
        .current_dir(&repository)
        .args(["agent", "gather-branch-context", "--output-dir"])
        .arg(&output)
        .assert()
        .success()
        .stdout(predicate::str::contains("COMMIT_COUNT=1"));
    let diff = fs::read_to_string(output.join("diff.txt")).expect("diff");
    let files = fs::read_to_string(output.join("file-list.txt")).expect("file list");
    let commits = fs::read_to_string(output.join("commit-log.txt")).expect("commit log");
    assert!(diff.contains("src/feature.txt"));
    assert!(files.contains("src/feature.txt"));
    assert!(commits.contains("feature change"));
    assert!(!diff.contains("larch-logs"));
    assert!(!files.contains("larch-logs"));
    assert!(!commits.contains("add run log"));
}

#[test]
fn gather_branch_context_prefers_origin_main_when_local_main_is_stale() {
    let fixture = TempDir::new().expect("fixture");
    let origin = fixture.path().join("origin.git");
    git(
        fixture.path(),
        &[
            "init",
            "--bare",
            "-b",
            "main",
            origin.to_str().expect("origin path"),
        ],
    );
    let repository = fixture.path().join("repository");
    fs::create_dir(&repository).expect("repository dir");
    git(&repository, &["init", "-b", "main"]);
    git(&repository, &["config", "user.email", "test@example.com"]);
    git(&repository, &["config", "user.name", "Test User"]);
    git(
        &repository,
        &[
            "remote",
            "add",
            "origin",
            origin.to_str().expect("origin path"),
        ],
    );
    commit(&repository, "feature.txt", "v1\n", "base A");
    git(&repository, &["push", "origin", "main"]);
    let base_a = git_stdout(&repository, &["rev-parse", "HEAD"])
        .trim()
        .to_owned();
    git(&repository, &["checkout", "-b", "feature"]);
    commit(
        &repository,
        "feature.txt",
        "v1\nfeature-edit\n",
        "feature change",
    );
    git(&repository, &["checkout", "main"]);
    commit(
        &repository,
        "unrelated.txt",
        "other-pr\n",
        "unrelated PR merged to main",
    );
    let base_b = git_stdout(&repository, &["rev-parse", "HEAD"])
        .trim()
        .to_owned();
    git(&repository, &["push", "origin", "main"]);
    git(&repository, &["reset", "--hard", &base_a]);
    git(&repository, &["checkout", "feature"]);
    git(&repository, &["rebase", &base_b]);
    git(&repository, &["fetch", "origin", "main"]);

    let output = fixture.path().join("context");
    fs::create_dir(&output).expect("context dir");
    larch()
        .current_dir(&repository)
        .args(["agent", "gather-branch-context", "--output-dir"])
        .arg(&output)
        .assert()
        .success()
        .stdout(predicate::str::contains("COMMIT_COUNT=1"));
    let diff = fs::read_to_string(output.join("diff.txt")).expect("diff");
    let files = fs::read_to_string(output.join("file-list.txt")).expect("file list");
    let commits = fs::read_to_string(output.join("commit-log.txt")).expect("commit log");
    assert!(files.contains("feature.txt"));
    assert!(commits.contains("feature change"));
    assert!(!files.contains("unrelated.txt"));
    assert!(!diff.contains("unrelated.txt"));
    assert!(!commits.contains("unrelated PR merged to main"));
}
