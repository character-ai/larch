//! Real-process regression harness for `bgjob start`, `wait`, `status`, and `reap`.
//!
//! Replaces the retired `scripts/test-bgjob.sh` shell harness: the commands are
//! Rust-owned after #8063, so their transport coverage runs where the verified
//! binary is already built.

#![cfg(unix)]

use assert_cmd::Command as AssertCommand;
use larch_adapters::SystemProcessIdentityHost;
use larch_core::{
    ENV_TEST_BGJOB_PHASE_BARRIER_DIR, ENV_TEST_BGJOB_STARTUP_ACK_TIMEOUT_S, KvDocument,
    ParseOptions, ProcessBirthIdentity, ProcessIdentityHost, RecordedProcessIdentity,
    RegistryEntry, RenderOptions, collect_process_group_members_checked, identity_to_json,
    read_entry, read_process_identity, write_entry_at,
};
use std::{
    fs,
    os::unix::fs::symlink,
    path::{Path, PathBuf},
    process::{Child, Command, Stdio},
    thread::sleep,
    time::{Duration, Instant, SystemTime, UNIX_EPOCH},
};
use tempfile::TempDir;

const POLL: Duration = Duration::from_millis(100);
const DEADLINE: Duration = Duration::from_secs(20);

struct Sandbox {
    root: TempDir,
    children: Vec<Child>,
}

impl Sandbox {
    fn new() -> Self {
        Self {
            root: TempDir::new().expect("sandbox"),
            children: Vec::new(),
        }
    }

    fn registry(&self) -> PathBuf {
        let path = self.root.path().join("registry");
        fs::create_dir_all(&path).expect("registry root");
        path
    }

    fn session(&self, step: &str) -> PathBuf {
        let path = self.root.path().join(step);
        fs::create_dir_all(&path).expect("session tmpdir");
        path
    }

    fn larch(&self) -> AssertCommand {
        let mut command = AssertCommand::cargo_bin("larch").expect("larch binary");
        command
            .env("LARCH_BGJOB_REGISTRY_ROOT", self.registry())
            .env("LARCH_TEST_BGJOB_OWNER_GRACE_S", "0.2")
            .env("LARCH_TEST_BGJOB_DAEMON_POLL_INTERVAL_S", "0.1")
            .env_remove("IMPLEMENT_TMPDIR")
            .env_remove("LARCH_BGJOB_OWNER_PID")
            .env_remove("LARCH_CLAUDE_PID")
            .env_remove("CLAUDE_PID")
            .env_remove("LARCH_RUN_ID")
            .env_remove(ENV_TEST_BGJOB_PHASE_BARRIER_DIR)
            .env_remove(ENV_TEST_BGJOB_STARTUP_ACK_TIMEOUT_S);
        command
    }

    /// Start a tracked owner or stale-process fixture.
    fn sleeper(&mut self) -> i32 {
        let child = Command::new("/bin/sleep")
            .arg("60")
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .expect("sleeper");
        let pid = i32::try_from(child.id()).expect("pid fits i32");
        self.children.push(child);
        pid
    }
}

fn raw_larch(sandbox: &Sandbox) -> Command {
    let mut command = Command::new(assert_cmd::cargo::cargo_bin("larch"));
    command
        .env("LARCH_BGJOB_REGISTRY_ROOT", sandbox.registry())
        .env("LARCH_TEST_BGJOB_OWNER_GRACE_S", "0.2")
        .env("LARCH_TEST_BGJOB_DAEMON_POLL_INTERVAL_S", "0.1")
        .env_remove("IMPLEMENT_TMPDIR")
        .env_remove("LARCH_BGJOB_OWNER_PID")
        .env_remove("LARCH_CLAUDE_PID")
        .env_remove("CLAUDE_PID")
        .env_remove("LARCH_RUN_ID")
        .env_remove(ENV_TEST_BGJOB_PHASE_BARRIER_DIR)
        .env_remove(ENV_TEST_BGJOB_STARTUP_ACK_TIMEOUT_S)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    command
}

impl Drop for Sandbox {
    fn drop(&mut self) {
        for child in &mut self.children {
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}

fn started_pgid(stdout: &str, step: &str) -> i32 {
    let expected = format!("BGJOB_STATUS=STARTED STEP={step} PGID=");
    let line = stdout.strip_suffix('\n').unwrap_or(stdout);
    assert!(
        !line.contains('\n'),
        "start printed more than one line: {stdout:?}"
    );
    let pgid = line
        .strip_prefix(&expected)
        .unwrap_or_else(|| panic!("unexpected start stdout: {stdout:?}"));
    pgid.parse().expect("numeric pgid")
}

fn start(
    sandbox: &Sandbox,
    step: &str,
    tmpdir: &Path,
    budget_s: &str,
    owner_pid: i32,
    command: &[&str],
) -> String {
    let output = sandbox
        .larch()
        .args(["bgjob", "start", "--step", step])
        .arg("--tmpdir")
        .arg(tmpdir)
        .args([
            "--budget-s",
            budget_s,
            "--owner-pid",
            &owner_pid.to_string(),
            "--",
        ])
        .args(command)
        .assert()
        .success()
        .get_output()
        .stdout
        .clone();
    String::from_utf8(output).expect("utf8 start stdout")
}

fn wait_once(sandbox: &Sandbox, step: &str, tmpdir: &Path, max_wait_s: &str) -> String {
    let output = sandbox
        .larch()
        .args(["bgjob", "wait", "--step", step])
        .arg("--tmpdir")
        .arg(tmpdir)
        .args(["--max-wait-s", max_wait_s, "--poll-interval-s", "0.1"])
        .assert()
        .success()
        .get_output()
        .stdout
        .clone();
    String::from_utf8(output).expect("utf8 wait stdout")
}

fn wait_with_run_id(sandbox: &Sandbox, step: &str, tmpdir: &Path, run_id: &str) -> String {
    let output = sandbox
        .larch()
        .args(["bgjob", "wait", "--step", step])
        .arg("--tmpdir")
        .arg(tmpdir)
        .args([
            "--run-id",
            run_id,
            "--max-wait-s",
            "1",
            "--poll-interval-s",
            "0.1",
        ])
        .assert()
        .success()
        .get_output()
        .stdout
        .clone();
    String::from_utf8(output).expect("utf8 retryable wait stdout")
}

/// Poll `bgjob wait` until it stops reporting `WAIT`.
fn wait_until_settled(sandbox: &Sandbox, step: &str, tmpdir: &Path) -> String {
    let deadline = Instant::now() + DEADLINE;
    let mut last = String::new();
    while Instant::now() < deadline {
        last = wait_once(sandbox, step, tmpdir, "1");
        if !last.contains("BGJOB_STATUS=WAIT") {
            return last;
        }
    }
    panic!("bgjob wait never settled for {step}: {last:?}");
}

fn registry_row(sandbox: &Sandbox, step: &str) -> PathBuf {
    let deadline = Instant::now() + DEADLINE;
    while Instant::now() < deadline {
        let found = fs::read_dir(sandbox.registry())
            .expect("registry root")
            .filter_map(Result::ok)
            .map(|entry| entry.path())
            .find(|path| {
                path.file_name()
                    .and_then(|name| name.to_str())
                    .is_some_and(|name| name.ends_with(&format!("-{step}.env")))
            });
        if let Some(path) = found {
            return path;
        }
        sleep(POLL);
    }
    panic!("no registry row for {step}");
}

fn recovery_lease_path(row: &Path) -> PathBuf {
    let parent = row.parent().expect("registry parent");
    let name = row.file_name().expect("registry name").to_string_lossy();
    parent.join(format!(".{name}.recovery"))
}

fn age_recovery_lease(path: &Path) {
    let file = fs::OpenOptions::new()
        .write(true)
        .open(path)
        .expect("recovery lease");
    let old = SystemTime::now() - Duration::from_secs(10);
    file.set_times(fs::FileTimes::new().set_modified(old))
        .expect("age recovery lease");
}

fn reap_process(sandbox: &Sandbox) -> Command {
    let mut command = Command::new(assert_cmd::cargo::cargo_bin("larch"));
    command
        .args(["bgjob", "reap"])
        .env("LARCH_BGJOB_REGISTRY_ROOT", sandbox.registry())
        .env("LARCH_TEST_BGJOB_OWNER_GRACE_S", "0.2")
        .env("LARCH_TEST_BGJOB_DAEMON_POLL_INTERVAL_S", "0.1")
        .env_remove("IMPLEMENT_TMPDIR")
        .env_remove("LARCH_BGJOB_OWNER_PID")
        .env_remove("LARCH_CLAUDE_PID")
        .env_remove("CLAUDE_PID")
        .env_remove("LARCH_RUN_ID")
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    command
}

fn pid_is_live(pid: i32) -> bool {
    nix::sys::signal::kill(nix::unistd::Pid::from_raw(pid), None).is_ok()
}

fn group_is_live(pgid: i32) -> bool {
    let host = SystemProcessIdentityHost::new();
    if host.get_pgid(pgid) == Some(pgid) && !host.process_is_zombie(pgid) {
        return true;
    }
    // An unavailable group probe is not evidence that the group is gone.
    collect_process_group_members_checked(&host, pgid).map_or_else(
        || nix::sys::signal::kill(nix::unistd::Pid::from_raw(-pgid), None).is_ok(),
        |members| !members.is_empty(),
    )
}

fn assert_group_gone(pgid: i32, context: &str) {
    let deadline = Instant::now() + DEADLINE;
    while group_is_live(pgid) && Instant::now() < deadline {
        sleep(POLL);
    }
    assert!(
        !group_is_live(pgid),
        "{context} left process group {pgid} alive"
    );
}

fn wait_for_file(path: &Path, context: &str) {
    let deadline = Instant::now() + DEADLINE;
    while Instant::now() < deadline {
        if fs::symlink_metadata(path).is_ok_and(|metadata| metadata.is_file()) {
            return;
        }
        sleep(POLL);
    }
    panic!("timed out waiting for {context}: {}", path.display());
}

fn phase_process_pid(path: &Path) -> i32 {
    fs::read_to_string(path)
        .expect("phase barrier payload")
        .strip_prefix("PID=")
        .and_then(|text| text.strip_suffix('\n'))
        .and_then(|text| text.parse().ok())
        .expect("phase barrier pid")
}

fn direct_child_pid(parent: i32, context: &str) -> i32 {
    let deadline = Instant::now() + DEADLINE;
    let host = SystemProcessIdentityHost::new();
    while Instant::now() < deadline {
        if let Some(pid) = host.pgrep_children(parent).into_iter().next() {
            return pid;
        }
        sleep(POLL);
    }
    panic!("timed out waiting for {context} child of {parent}");
}

fn epoch_now() -> i64 {
    i64::try_from(
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("epoch")
            .as_secs(),
    )
    .expect("epoch fits i64")
}

#[test]
fn start_prints_one_line_and_wait_reports_the_child_result() {
    let sandbox = Sandbox::new();
    let tmpdir = sandbox.session("start-check");
    let stdout = start(
        &sandbox,
        "start-check",
        &tmpdir,
        "20",
        std::process::id().try_into().expect("pid"),
        &["/bin/sh", "-c", "echo hello from child"],
    );
    assert!(started_pgid(&stdout, "start-check") > 0);

    let settled = wait_until_settled(&sandbox, "start-check", &tmpdir);
    assert!(settled.contains("BGJOB_STATUS=DONE"), "{settled:?}");
    assert!(settled.contains("BGJOB_RC=0"), "{settled:?}");
    assert!(settled.contains("STEP=start-check"), "{settled:?}");
    let log = fs::read_to_string(tmpdir.join("bgjob/start-check.stdout.log")).expect("stdout log");
    assert!(log.contains("hello from child"), "{log:?}");
    let result = fs::read_to_string(tmpdir.join("bgjob/start-check.result.env"))
        .expect("completed result envelope");
    let document =
        KvDocument::parse(&result, ParseOptions::environment()).expect("result KEY=value envelope");
    assert_eq!(
        document
            .render(RenderOptions::wire())
            .expect("canonical result envelope"),
        result,
        "result envelope has non-canonical bytes: {result:?}"
    );
    let keys = document
        .rows()
        .iter()
        .map(larch_core::KvRow::key)
        .collect::<Vec<_>>();
    assert_eq!(
        keys,
        ["BGJOB_RC", "BGJOB_ELAPSED_S", "STEP"],
        "result envelope key set drifted: {result:?}"
    );
    let completion = fs::read_to_string(tmpdir.join("bgjob/start-check.completion.env"))
        .expect("no-sentinel completion descriptor");
    assert!(completion.contains("STATE=COMMITTED\n"), "{completion:?}");
    assert!(completion.contains("SENTINEL_COUNT=0\n"), "{completion:?}");

    // A completed job leaves no registry row, so `reap` has nothing to remove.
    sandbox
        .larch()
        .args(["bgjob", "reap"])
        .assert()
        .success()
        .stdout("BGJOB_REAPED=0\n");
}

#[test]
fn direct_start_rejects_unsafe_merge_result_envs_before_launch() {
    let sandbox = Sandbox::new();
    let tmpdir = sandbox.session("direct-merge");
    let owner_pid = std::process::id().to_string();
    let outside = tempfile::tempdir().expect("outside directory");
    let leaf_target = outside.path().join("leaf-target.env");
    fs::write(&leaf_target, "CUSTOM=outside\n").expect("leaf target");
    let leaf_link = tmpdir.join("leaf-link.env");
    symlink(&leaf_target, &leaf_link).expect("leaf symlink");
    let ancestor_target = outside.path().join("ancestor");
    fs::create_dir(&ancestor_target).expect("ancestor target");
    let ancestor_link = tmpdir.join("ancestor-link");
    symlink(&ancestor_target, &ancestor_link).expect("ancestor symlink");
    let directory_merge = tmpdir.join("directory-merge");
    fs::create_dir(&directory_merge).expect("directory merge path");

    for (case, merge) in [
        ("relative", PathBuf::from("relative.env")),
        ("outside", outside.path().join("outside.env")),
        ("leaf-link", leaf_link),
        ("ancestor-link", ancestor_link.join("merge.env")),
        ("directory", directory_merge),
    ] {
        let step = format!("direct-{case}");
        let marker = sandbox.root.path().join(format!("{case}.ran"));
        let output = raw_larch(&sandbox)
            .args(["bgjob", "start", "--step", &step])
            .arg("--tmpdir")
            .arg(&tmpdir)
            .args([
                "--budget-s",
                "20",
                "--owner-pid",
                &owner_pid,
                "--merge-result-env",
            ])
            .arg(&merge)
            .args(["--", "/bin/sh", "-c", "touch \"$1\"", "sh"])
            .arg(&marker)
            .output()
            .expect("direct invalid start");
        assert_eq!(output.status.code(), Some(2), "{case}: {output:?}");
        assert!(
            !marker.exists(),
            "{case} merge path launched its child before validation"
        );
    }
}

#[test]
fn direct_start_preserves_valid_merge_result_rows() {
    let sandbox = Sandbox::new();
    let tmpdir = sandbox.session("direct-merge");
    let owner_pid = std::process::id().to_string();
    let valid_merge = tmpdir.join("valid-merge.env");
    let started = raw_larch(&sandbox)
        .args(["bgjob", "start", "--step", "direct-valid"])
        .arg("--tmpdir")
        .arg(&tmpdir)
        .args([
            "--budget-s",
            "20",
            "--owner-pid",
            &owner_pid,
            "--merge-result-env",
        ])
        .arg(&valid_merge)
        .args([
            "--",
            "/bin/sh",
            "-c",
            "printf 'CUSTOM=kept\\n' > \"$1\"",
            "sh",
        ])
        .arg(&valid_merge)
        .output()
        .expect("direct valid start");
    assert!(started.status.success(), "{started:?}");
    assert!(
        started_pgid(
            &String::from_utf8(started.stdout).expect("valid start stdout"),
            "direct-valid"
        ) > 0
    );
    let settled = wait_until_settled(&sandbox, "direct-valid", &tmpdir);
    assert!(settled.contains("BGJOB_STATUS=DONE"), "{settled:?}");
    let result = fs::read_to_string(tmpdir.join("bgjob/direct-valid.result.env"))
        .expect("valid merged result");
    let document =
        KvDocument::parse(&result, ParseOptions::environment()).expect("merged envelope");
    assert_eq!(
        document
            .rows()
            .iter()
            .map(larch_core::KvRow::key)
            .collect::<Vec<_>>(),
        ["BGJOB_RC", "BGJOB_ELAPSED_S", "STEP", "CUSTOM"],
        "merge row order changed: {result:?}"
    );
    assert!(
        result.ends_with("STEP=direct-valid\nCUSTOM=kept\n"),
        "{result:?}"
    );
}

#[test]
fn direct_start_revalidates_raced_merge_result_env() {
    let sandbox = Sandbox::new();
    let tmpdir = sandbox.session("direct-merge");
    let owner_pid = std::process::id().to_string();
    let outside = tempfile::tempdir().expect("outside directory");
    let raced_merge = tmpdir.join("raced-merge.env");
    let ready = tmpdir.join("merge-ready");
    let release = tmpdir.join("merge-release");
    let started = raw_larch(&sandbox)
        .args(["bgjob", "start", "--step", "direct-raced"])
        .arg("--tmpdir")
        .arg(&tmpdir)
        .args([
            "--budget-s",
            "20",
            "--owner-pid",
            &owner_pid,
            "--merge-result-env",
        ])
        .arg(&raced_merge)
        .args([
            "--",
            "/bin/sh",
            "-c",
            "printf 'CUSTOM=raced\\n' > \"$1\"; : > \"$2\"; while [ ! -f \"$3\" ]; do sleep 0.05; done",
            "sh",
        ])
        .args([&raced_merge, &ready, &release])
        .output()
        .expect("direct raced start");
    assert!(started.status.success(), "{started:?}");
    wait_for_file(&ready, "merge writer readiness");
    fs::remove_file(&raced_merge).expect("replace merge leaf");
    let raced_target = outside.path().join("raced-target.env");
    fs::write(&raced_target, "CUSTOM=outside\n").expect("raced target");
    symlink(&raced_target, &raced_merge).expect("replace merge with symlink");
    fs::write(&release, "").expect("release merge child");

    let settled = wait_until_settled(&sandbox, "direct-raced", &tmpdir);
    assert!(
        settled.contains("BGJOB_STATUS=DEAD"),
        "unsafe merge replacement became terminal: {settled:?}"
    );
    assert!(
        !tmpdir.join("bgjob/direct-raced.result.env").exists(),
        "unsafe merge replacement published a result"
    );
}

#[test]
fn completion_publication_crashes_recover_to_whole_output_sets() {
    for (index, phase) in [
        "before-completion-intent",
        "after-completion-stage",
        "after-completion-intent",
        "before-result-publication",
        "after-result-publication",
        "before-sentinel-0-publication",
        "after-sentinel-0-publication",
        "before-sentinel-1-publication",
        "after-sentinel-1-publication",
        "before-completion-commit",
        "after-completion-commit",
    ]
    .iter()
    .enumerate()
    {
        let sandbox = Sandbox::new();
        let step = format!("completion-phase-{index}");
        let tmpdir = sandbox.session(&step);
        let phases = sandbox.root.path().join("completion-phases");
        fs::create_dir_all(&phases).expect("phase directory");
        fs::write(phases.join(format!("{phase}.armed")), "").expect("arm completion phase");
        let first = tmpdir.join("first.sentinel");
        let second = tmpdir.join("second.sentinel");
        let owner_pid = std::process::id().to_string();
        let started = raw_larch(&sandbox)
            .args(["bgjob", "start", "--step", &step])
            .arg("--tmpdir")
            .arg(&tmpdir)
            .args(["--budget-s", "20", "--owner-pid", &owner_pid, "--sentinel"])
            .arg(&first)
            .arg("--sentinel")
            .arg(&second)
            .args(["--", "/bin/sh", "-c", "exit 0"])
            .env(ENV_TEST_BGJOB_PHASE_BARRIER_DIR, &phases)
            .output()
            .expect("start completion phase job");
        assert!(started.status.success(), "{phase}: {started:?}");
        let row = registry_row(&sandbox, &step);
        let reached = phases.join(format!("{phase}.reached"));
        wait_for_file(&reached, phase);
        let daemon = phase_process_pid(&reached);
        nix::sys::signal::kill(
            nix::unistd::Pid::from_raw(daemon),
            nix::sys::signal::Signal::SIGKILL,
        )
        .expect("kill completion daemon");

        let settled = wait_until_settled(&sandbox, &step, &tmpdir);
        let result = tmpdir.join("bgjob").join(format!("{step}.result.env"));
        if matches!(
            *phase,
            "before-completion-intent" | "after-completion-stage"
        ) {
            assert!(
                settled.contains("BGJOB_STATUS=DEAD"),
                "{phase}: {settled:?}"
            );
            assert!(!result.exists(), "{phase} leaked a partial result");
            assert!(!first.exists(), "{phase} leaked the first sentinel");
            assert!(!second.exists(), "{phase} leaked the second sentinel");
            assert!(
                !tmpdir
                    .join("bgjob")
                    .join(format!("{step}.completion-stage.env"))
                    .exists(),
                "{phase} retained an uncommitted staged result"
            );
        } else {
            assert!(
                settled.contains("BGJOB_STATUS=DONE"),
                "{phase}: {settled:?}"
            );
            assert!(settled.contains("BGJOB_RC=0"), "{phase}: {settled:?}");
            let text = fs::read_to_string(&result).expect("recovered result envelope");
            let document =
                KvDocument::parse(&text, ParseOptions::environment()).expect("recovered envelope");
            assert_eq!(
                document
                    .rows()
                    .iter()
                    .map(larch_core::KvRow::key)
                    .collect::<Vec<_>>(),
                ["BGJOB_RC", "BGJOB_ELAPSED_S", "STEP"],
                "{phase}: result row order changed: {text:?}"
            );
            assert!(first.is_file(), "{phase} omitted the first sentinel");
            assert!(second.is_file(), "{phase} omitted the second sentinel");
        }
        sandbox.larch().args(["bgjob", "reap"]).assert().success();
        assert!(!row.exists(), "{phase} retained its registry row");
    }
}

#[test]
fn sentinel_publication_failure_retains_a_recoverable_transaction() {
    let sandbox = Sandbox::new();
    let tmpdir = sandbox.session("sentinel-retry");
    let first = tmpdir.join("first.sentinel");
    let blocked = tmpdir.join("blocked.sentinel");
    fs::create_dir(&blocked).expect("blocked sentinel directory");
    let owner_pid = std::process::id().to_string();
    let started = raw_larch(&sandbox)
        .args(["bgjob", "start", "--step", "sentinel-retry"])
        .arg("--tmpdir")
        .arg(&tmpdir)
        .args(["--budget-s", "20", "--owner-pid", &owner_pid, "--sentinel"])
        .arg(&first)
        .arg("--sentinel")
        .arg(&blocked)
        .args(["--", "/bin/sh", "-c", "exit 0"])
        .output()
        .expect("start blocked sentinel job");
    assert!(started.status.success(), "{started:?}");
    let row = registry_row(&sandbox, "sentinel-retry");
    let deadline = Instant::now() + DEADLINE;
    let retryable = loop {
        let output = wait_once(&sandbox, "sentinel-retry", &tmpdir, "1");
        if output.contains("BGJOB_RECOVERY=retryable") {
            break output;
        }
        assert!(
            output.contains("BGJOB_STATUS=WAIT"),
            "sentinel publication became unexpectedly terminal: {output:?}"
        );
        assert!(
            Instant::now() < deadline,
            "sentinel failure did not become retryable"
        );
    };
    assert!(
        !retryable.contains("BGJOB_STATUS=DONE"),
        "partial output became terminal: {retryable:?}"
    );
    assert!(
        tmpdir.join("bgjob/sentinel-retry.result.env").is_file(),
        "the transaction did not preserve its staged result publication"
    );
    assert!(first.is_file(), "the first sentinel was not published");
    assert!(
        blocked.is_dir(),
        "the failing sentinel path was unexpectedly replaced"
    );
    assert!(
        row.exists(),
        "failed publication discarded durable recovery state"
    );

    fs::remove_dir(&blocked).expect("unblock sentinel path");
    let settled = wait_until_settled(&sandbox, "sentinel-retry", &tmpdir);
    assert!(
        settled.contains("BGJOB_STATUS=DONE") && settled.contains("BGJOB_RC=0"),
        "recovery did not converge after the I/O failure cleared: {settled:?}"
    );
    assert!(first.is_file(), "recovery lost the first sentinel");
    assert!(
        blocked.is_file(),
        "recovery did not publish the blocked sentinel"
    );
    assert!(
        !row.exists(),
        "recovery retained its completed registry row"
    );
}

#[test]
fn result_publication_failure_retains_a_recoverable_transaction() {
    let sandbox = Sandbox::new();
    let tmpdir = sandbox.session("result-retry");
    let phases = sandbox.root.path().join("result-retry-phases");
    fs::create_dir_all(&phases).expect("phase directory");
    fs::write(phases.join("before-result-publication.armed"), "").expect("arm result barrier");
    let sentinel = tmpdir.join("done.sentinel");
    let owner_pid = std::process::id().to_string();
    let started = raw_larch(&sandbox)
        .args(["bgjob", "start", "--step", "result-retry"])
        .arg("--tmpdir")
        .arg(&tmpdir)
        .args(["--budget-s", "20", "--owner-pid", &owner_pid, "--sentinel"])
        .arg(&sentinel)
        .args(["--", "/bin/sh", "-c", "exit 0"])
        .env(ENV_TEST_BGJOB_PHASE_BARRIER_DIR, &phases)
        .output()
        .expect("start blocked result job");
    assert!(started.status.success(), "{started:?}");
    let row = registry_row(&sandbox, "result-retry");
    wait_for_file(
        &phases.join("before-result-publication.reached"),
        "result publication barrier",
    );
    let result = tmpdir.join("bgjob/result-retry.result.env");
    fs::create_dir(&result).expect("block result path with directory");
    fs::write(phases.join("before-result-publication.release"), "")
        .expect("release result barrier");

    let deadline = Instant::now() + DEADLINE;
    let retryable = loop {
        let output = wait_once(&sandbox, "result-retry", &tmpdir, "1");
        if output.contains("BGJOB_RECOVERY=retryable") {
            break output;
        }
        assert!(
            output.contains("BGJOB_STATUS=WAIT"),
            "result publication became unexpectedly terminal: {output:?}"
        );
        assert!(
            Instant::now() < deadline,
            "result failure did not become retryable"
        );
    };
    assert!(
        !retryable.contains("BGJOB_STATUS=DONE"),
        "failed result publication became terminal: {retryable:?}"
    );
    assert!(
        result.is_dir(),
        "the blocked result path was unexpectedly replaced"
    );
    assert!(
        !sentinel.exists(),
        "a sentinel escaped before the result publication succeeded"
    );
    assert!(
        row.exists(),
        "failed result publication discarded recovery state"
    );

    fs::remove_dir(&result).expect("unblock result path");
    let settled = wait_until_settled(&sandbox, "result-retry", &tmpdir);
    assert!(
        settled.contains("BGJOB_STATUS=DONE") && settled.contains("BGJOB_RC=0"),
        "result recovery did not converge: {settled:?}"
    );
    assert!(
        result.is_file(),
        "recovery did not publish the result envelope"
    );
    assert!(sentinel.is_file(), "recovery did not publish its sentinel");
    assert!(
        !row.exists(),
        "recovery retained its completed registry row"
    );
}

#[test]
fn budget_expiry_reports_timeout_and_kills_the_child_group() {
    let sandbox = Sandbox::new();
    let tmpdir = sandbox.session("budget-expiry");
    let stdout = start(
        &sandbox,
        "budget-expiry",
        &tmpdir,
        "1",
        std::process::id().try_into().expect("pid"),
        &["/bin/sh", "-c", "while true; do sleep 1; done"],
    );
    let pgid = started_pgid(&stdout, "budget-expiry");
    let row = registry_row(&sandbox, "budget-expiry");
    let child_pid = read_entry(&row).expect("registry entry").child.pid;

    let settled = wait_until_settled(&sandbox, "budget-expiry", &tmpdir);
    assert!(settled.contains("BGJOB_STATUS=DONE"), "{settled:?}");
    assert!(settled.contains("BGJOB_RC=timeout"), "{settled:?}");
    assert_eq!(pgid, child_pid, "the job child leads its own process group");

    let deadline = Instant::now() + DEADLINE;
    while pid_is_live(child_pid) && Instant::now() < deadline {
        sleep(POLL);
    }
    assert!(
        !pid_is_live(child_pid),
        "timeout left child {child_pid} alive"
    );
    assert_group_gone(pgid, "timeout");
}

#[test]
fn budget_expiry_kills_a_child_that_execs_a_different_program() {
    let sandbox = Sandbox::new();
    let tmpdir = sandbox.session("budget-exec");
    let stdout = start(
        &sandbox,
        "budget-exec",
        &tmpdir,
        "3",
        std::process::id().try_into().expect("pid"),
        &["/bin/sh", "-c", "sleep 1; exec sleep 60"],
    );
    let pgid = started_pgid(&stdout, "budget-exec");
    let row = registry_row(&sandbox, "budget-exec");
    let child = read_entry(&row).expect("registry entry").child;
    assert!(
        child.birth_identity.is_some(),
        "missing durable birth identity"
    );
    assert!(
        child.command_signature.contains("bgjob start"),
        "the registry did not capture the persistent worker: {child:?}"
    );
    assert!(
        !read_entry(&row).expect("registry entry").child_allows_exec,
        "the persistent worker must remain an exact identity"
    );
    let child_pid = child.pid;

    let settled = wait_until_settled(&sandbox, "budget-exec", &tmpdir);
    assert!(settled.contains("BGJOB_STATUS=DONE"), "{settled:?}");
    assert!(settled.contains("BGJOB_RC=timeout"), "{settled:?}");
    assert!(
        !pid_is_live(child_pid),
        "timeout left exec child {child_pid} alive"
    );
    assert_group_gone(pgid, "timeout after exec");
    assert!(!row.exists(), "timeout retained the registry row");
}

#[test]
fn a_target_leader_can_exit_while_a_term_resistant_descendant_remains_owned() {
    let sandbox = Sandbox::new();
    let tmpdir = sandbox.session("leaderless-target");
    let stdout = start(
        &sandbox,
        "leaderless-target",
        &tmpdir,
        "1",
        std::process::id().try_into().expect("pid"),
        &[
            "/bin/sh",
            "-c",
            "(trap '' TERM; while true; do sleep 1; done) & exit 0",
        ],
    );
    let pgid = started_pgid(&stdout, "leaderless-target");
    let row = registry_row(&sandbox, "leaderless-target");
    let entry = read_entry(&row).expect("registry entry");
    assert!(
        entry.child.command_signature.contains("bgjob start"),
        "the durable group leader must be the persistent worker: {entry:?}"
    );

    let settled = wait_until_settled(&sandbox, "leaderless-target", &tmpdir);
    assert!(settled.contains("BGJOB_STATUS=DONE"), "{settled:?}");
    assert!(settled.contains("BGJOB_RC=timeout"), "{settled:?}");
    assert_group_gone(pgid, "leaderless target descendant");
    assert!(!row.exists(), "leaderless target retained the registry row");
}

#[test]
fn an_unacknowledged_start_is_bounded_and_recovers_its_durable_worker() {
    let sandbox = Sandbox::new();
    let tmpdir = sandbox.session("ack-timeout");
    let phases = sandbox.root.path().join("ack-timeout-phases");
    fs::create_dir_all(&phases).expect("phase directory");
    fs::write(phases.join("before-acknowledgement.armed"), "").expect("arm barrier");
    let mut launcher = raw_larch(&sandbox);
    launcher
        .args(["bgjob", "start", "--step", "ack-timeout"])
        .arg("--tmpdir")
        .arg(&tmpdir)
        .args([
            "--budget-s",
            "60",
            "--owner-pid",
            &std::process::id().to_string(),
            "--",
            "/bin/sh",
            "-c",
            "exec sleep 60",
        ])
        .env(ENV_TEST_BGJOB_PHASE_BARRIER_DIR, &phases)
        .env(ENV_TEST_BGJOB_STARTUP_ACK_TIMEOUT_S, "2");
    let launcher = launcher.spawn().expect("start launcher");
    wait_for_file(
        &phases.join("before-acknowledgement.reached"),
        "acknowledgement barrier",
    );
    let row = registry_row(&sandbox, "ack-timeout");
    let entry = read_entry(&row).expect("durable registry entry before acknowledgement");
    let marker =
        fs::read_to_string(tmpdir.join("bgjob/ack-timeout.startup.env")).expect("startup marker");
    assert!(
        marker.contains("STARTUP_PHASE=registry-published\n"),
        "{marker:?}"
    );
    assert!(marker.contains("CHILD_BIRTH_IDENTITY="), "{marker:?}");

    let output = launcher.wait_with_output().expect("bounded launcher exit");
    assert_eq!(output.status.code(), Some(2), "{output:?}");
    assert_eq!(output.stdout, b"BGJOB_ERROR=daemon-start-failed\n");
    assert_group_gone(entry.child.pgid, "unacknowledged start");
    assert!(
        !row.exists(),
        "unacknowledged start retained its registry row"
    );
    assert!(
        !tmpdir.join("bgjob/ack-timeout.startup.env").exists(),
        "unacknowledged start retained its startup marker"
    );
}

#[test]
fn daemon_crashes_at_every_startup_phase_without_stranding_its_worker_group() {
    for phase in [
        "after-child-spawn",
        "after-identity-capture",
        "after-registry-publication",
        "after-startup-marker",
        "before-acknowledgement",
        "after-acknowledgement",
    ] {
        let sandbox = Sandbox::new();
        let step = format!(
            "phase-{}",
            phase.trim_start_matches("after-").replace('-', "")
        );
        let tmpdir = sandbox.session(&step);
        let phases = sandbox.root.path().join("phases");
        fs::create_dir_all(&phases).expect("phase directory");
        fs::write(phases.join(format!("{phase}.armed")), "").expect("arm barrier");
        let mut launcher = raw_larch(&sandbox);
        launcher
            .args(["bgjob", "start", "--step", &step])
            .arg("--tmpdir")
            .arg(&tmpdir)
            .args([
                "--budget-s",
                "60",
                "--owner-pid",
                &std::process::id().to_string(),
                "--",
                "/bin/sh",
                "-c",
                "exec sleep 60",
            ])
            .env(ENV_TEST_BGJOB_PHASE_BARRIER_DIR, &phases);
        let launcher = launcher.spawn().expect("start launcher");
        let reached = phases.join(format!("{phase}.reached"));
        wait_for_file(&reached, phase);
        let daemon = phase_process_pid(&reached);
        let worker = direct_child_pid(daemon, phase);
        nix::sys::signal::kill(
            nix::unistd::Pid::from_raw(daemon),
            nix::sys::signal::Signal::SIGKILL,
        )
        .expect("kill blocked daemon");

        let output = launcher.wait_with_output().expect("launcher exit");
        if phase == "after-acknowledgement" {
            assert!(output.status.success(), "{phase}: {output:?}");
            assert!(String::from_utf8_lossy(&output.stdout).contains("BGJOB_STATUS=STARTED"));
            let settled = wait_until_settled(&sandbox, &step, &tmpdir);
            assert!(
                settled.contains("BGJOB_STATUS=DEAD"),
                "{phase}: {settled:?}"
            );
        } else {
            assert_eq!(output.status.code(), Some(2), "{phase}: {output:?}");
            assert_eq!(output.stdout, b"BGJOB_ERROR=daemon-start-failed\n");
        }
        assert_group_gone(worker, phase);
        assert!(
            !tmpdir
                .join("bgjob")
                .join(format!("{step}.startup.env"))
                .exists(),
            "{phase} retained a startup marker"
        );
        let retained = fs::read_dir(sandbox.registry())
            .expect("registry root")
            .filter_map(Result::ok)
            .any(|entry| {
                entry
                    .file_name()
                    .to_string_lossy()
                    .ends_with(&format!("-{step}.env"))
            });
        assert!(!retained, "{phase} retained a registry row");
    }
}

#[test]
fn concurrent_adapters_rejoin_the_one_startup_record_before_acknowledgement() {
    let sandbox = Sandbox::new();
    let tmpdir = sandbox.session("concurrent-adapt");
    let phases = sandbox.root.path().join("concurrent-adapt-phases");
    fs::create_dir_all(&phases).expect("phase directory");
    fs::write(phases.join("before-acknowledgement.armed"), "").expect("arm barrier");
    let plugin_root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .expect("repository root");
    let owner_pid = std::process::id().to_string();
    let mut first = raw_larch(&sandbox);
    first
        .args(["bgjob", "adapt", "--step", "concurrent-adapt"])
        .arg("--tmpdir")
        .arg(&tmpdir)
        .args(["--budget-s", "60", "--owner-pid"])
        .arg(&owner_pid)
        .args(["--", "/bin/sh", "-c", "while true; do sleep 1; done"])
        .env("CLAUDE_PLUGIN_ROOT", &plugin_root)
        .env(ENV_TEST_BGJOB_PHASE_BARRIER_DIR, &phases);
    let first = first.spawn().expect("first adapter");
    wait_for_file(
        &phases.join("before-acknowledgement.reached"),
        "first adapter acknowledgement barrier",
    );
    let row = registry_row(&sandbox, "concurrent-adapt");
    let mut second = raw_larch(&sandbox);
    second
        .args(["bgjob", "adapt", "--step", "concurrent-adapt"])
        .arg("--tmpdir")
        .arg(&tmpdir)
        .args(["--budget-s", "60", "--owner-pid"])
        .arg(&owner_pid)
        .args(["--", "/bin/sh", "-c", "while true; do sleep 1; done"])
        .env("CLAUDE_PLUGIN_ROOT", &plugin_root)
        .env(ENV_TEST_BGJOB_PHASE_BARRIER_DIR, &phases);
    let mut second = second.spawn().expect("second adapter");
    assert!(
        second.try_wait().expect("second adapter status").is_none(),
        "the second adapter bypassed the in-flight decision lock"
    );

    fs::write(phases.join("before-acknowledgement.release"), "").expect("release barrier");
    let first = first.wait_with_output().expect("first adapter output");
    let second = second.wait_with_output().expect("second adapter output");
    assert!(first.status.success(), "{first:?}");
    assert!(second.status.success(), "{second:?}");
    let first = String::from_utf8(first.stdout).expect("first stdout");
    let second = String::from_utf8(second.stdout).expect("second stdout");
    let first_pgid = started_pgid(&first, "concurrent-adapt");
    assert_eq!(
        started_pgid(&second, "concurrent-adapt"),
        first_pgid,
        "concurrent adapters started distinct jobs: {first:?} vs {second:?}"
    );

    let entry = read_entry(&row).expect("one shared registry row");
    nix::sys::signal::kill(
        nix::unistd::Pid::from_raw(entry.daemon.pid),
        nix::sys::signal::Signal::SIGKILL,
    )
    .expect("kill shared daemon");
    let recovered = wait_until_settled(&sandbox, "concurrent-adapt", &tmpdir);
    assert!(recovered.contains("BGJOB_STATUS=DEAD"), "{recovered:?}");
    assert_group_gone(first_pgid, "concurrent adapters cleanup");
    assert!(!row.exists(), "shared adapter row remained after recovery");
}

#[test]
fn clear_stall_retains_a_live_checks_registry_row_when_the_owner_is_gone() {
    let mut sandbox = Sandbox::new();
    let tmpdir = sandbox.session("clear-stall-live");
    fs::write(
        tmpdir.join("ship-pr-state.sh"),
        "STALL_TRACKING=true\nSTALL_STEP=3\n",
    )
    .expect("stall state");
    let owner_pid = sandbox.sleeper();
    let output = raw_larch(&sandbox)
        .args(["bgjob", "start", "--step", "implement-step3-checks"])
        .arg("--tmpdir")
        .arg(&tmpdir)
        .args(["--budget-s", "60", "--owner-pid"])
        .arg(owner_pid.to_string())
        .args(["--", "/bin/sh", "-c", "exec sleep 60"])
        .env("LARCH_TEST_BGJOB_OWNER_GRACE_S", "60")
        .output()
        .expect("checks start");
    assert!(output.status.success(), "{output:?}");
    let row = registry_row(&sandbox, "implement-step3-checks");
    let entry = read_entry(&row).expect("checks registry entry");
    let owner = sandbox
        .children
        .iter_mut()
        .find(|child| i32::try_from(child.id()).expect("pid") == owner_pid)
        .expect("owner child");
    owner.kill().expect("kill owner");
    owner.wait().expect("reap owner");

    sandbox
        .larch()
        .args(["stall-recovery", "--implement-tmpdir"])
        .arg(&tmpdir)
        .arg("clear-stall")
        .assert()
        .code(1)
        .stdout("CLEARED=false\n");
    assert!(
        row.exists(),
        "clear-stall stripped a live checks registry row"
    );
    assert_eq!(
        fs::read_to_string(tmpdir.join("ship-pr-state.sh")).expect("unchanged stall state"),
        "STALL_TRACKING=true\nSTALL_STEP=3\n"
    );

    nix::sys::signal::kill(
        nix::unistd::Pid::from_raw(entry.daemon.pid),
        nix::sys::signal::Signal::SIGKILL,
    )
    .expect("kill checks daemon");
    let recovered = wait_until_settled(&sandbox, "implement-step3-checks", &tmpdir);
    assert!(recovered.contains("BGJOB_STATUS=DEAD"), "{recovered:?}");
    assert_group_gone(entry.child.pgid, "clear-stall checks cleanup");
}

#[test]
fn owner_death_reports_orphaned() {
    let mut sandbox = Sandbox::new();
    let tmpdir = sandbox.session("owner-death");
    let owner_pid = sandbox.sleeper();
    let stdout = start(
        &sandbox,
        "owner-death",
        &tmpdir,
        "60",
        owner_pid,
        &["/bin/sh", "-c", "exec sleep 60"],
    );
    assert!(started_pgid(&stdout, "owner-death") > 0);

    let owner = sandbox
        .children
        .iter_mut()
        .find(|child| i32::try_from(child.id()).expect("pid") == owner_pid)
        .expect("owner child");
    owner.kill().expect("kill owner");
    owner.wait().expect("reap owner");

    let settled = wait_until_settled(&sandbox, "owner-death", &tmpdir);
    assert!(settled.contains("BGJOB_STATUS=DONE"), "{settled:?}");
    assert!(settled.contains("BGJOB_RC=orphaned"), "{settled:?}");
    assert_group_gone(started_pgid(&stdout, "owner-death"), "owner death");
}

#[test]
fn an_externally_killed_daemon_recovers_its_child_before_reporting_dead() {
    let sandbox = Sandbox::new();
    let tmpdir = sandbox.session("external-kill");
    let stdout = start(
        &sandbox,
        "external-kill",
        &tmpdir,
        "60",
        std::process::id().try_into().expect("pid"),
        &["/bin/sh", "-c", "while true; do sleep 1; done"],
    );
    assert!(started_pgid(&stdout, "external-kill") > 0);

    let row = registry_row(&sandbox, "external-kill");
    let entry = read_entry(&row).expect("registry entry");
    nix::sys::signal::kill(
        nix::unistd::Pid::from_raw(entry.daemon.pid),
        nix::sys::signal::Signal::SIGKILL,
    )
    .expect("kill daemon");

    let deadline = Instant::now() + DEADLINE;
    let mut settled = String::new();
    while Instant::now() < deadline {
        settled = wait_once(&sandbox, "external-kill", &tmpdir, "1");
        if settled.contains("BGJOB_STATUS=DEAD") {
            break;
        }
    }
    assert!(settled.contains("BGJOB_STATUS=DEAD"), "{settled:?}");
    assert!(
        settled.contains("BGJOB_DIAG=daemon-dead-recovered"),
        "{settled:?}"
    );
    assert!(!pid_is_live(entry.child.pid), "recovery left child alive");
    assert_group_gone(entry.child.pgid, "external daemon death");
    assert!(!row.exists(), "recovery retained the registry row");
    assert!(
        !tmpdir.join("bgjob/external-kill.result.env").exists(),
        "recovery left a partial result envelope"
    );
}

#[test]
fn reap_recovers_an_externally_killed_daemons_child_group() {
    let sandbox = Sandbox::new();
    let tmpdir = sandbox.session("reap-daemon-dead");
    let stdout = start(
        &sandbox,
        "reap-daemon-dead",
        &tmpdir,
        "60",
        std::process::id().try_into().expect("pid"),
        &["/bin/sh", "-c", "exec sleep 60"],
    );
    assert!(started_pgid(&stdout, "reap-daemon-dead") > 0);
    let row = registry_row(&sandbox, "reap-daemon-dead");
    let entry = read_entry(&row).expect("registry entry");
    nix::sys::signal::kill(
        nix::unistd::Pid::from_raw(entry.daemon.pid),
        nix::sys::signal::Signal::SIGKILL,
    )
    .expect("kill daemon");
    let deadline = Instant::now() + DEADLINE;
    while pid_is_live(entry.daemon.pid) && Instant::now() < deadline {
        sleep(POLL);
    }
    assert!(!pid_is_live(entry.daemon.pid), "daemon did not exit");

    sandbox
        .larch()
        .args(["bgjob", "reap"])
        .assert()
        .success()
        .stdout("BGJOB_REAPED=1\n");
    assert_group_gone(entry.child.pgid, "reap after external daemon death");
    assert!(!row.exists(), "reap retained the recovered registry row");
    assert!(
        !entry.result_env.exists(),
        "reap recovery left a partial result envelope"
    );
}

#[test]
fn reap_retries_a_stale_malformed_recovery_lease_without_stranding_the_child_group() {
    let sandbox = Sandbox::new();
    let tmpdir = sandbox.session("reap-malformed-lease");
    let stdout = start(
        &sandbox,
        "reap-malformed-lease",
        &tmpdir,
        "60",
        std::process::id().try_into().expect("pid"),
        &["/bin/sh", "-c", "exec sleep 60"],
    );
    assert!(started_pgid(&stdout, "reap-malformed-lease") > 0);
    let row = registry_row(&sandbox, "reap-malformed-lease");
    let entry = read_entry(&row).expect("registry entry");
    nix::sys::signal::kill(
        nix::unistd::Pid::from_raw(entry.daemon.pid),
        nix::sys::signal::Signal::SIGKILL,
    )
    .expect("kill daemon");
    let deadline = Instant::now() + DEADLINE;
    while pid_is_live(entry.daemon.pid) && Instant::now() < deadline {
        sleep(POLL);
    }
    assert!(!pid_is_live(entry.daemon.pid), "daemon did not exit");

    let lease = recovery_lease_path(&row);
    fs::write(&lease, "{\"pid\":").expect("malformed recovery lease");
    sandbox
        .larch()
        .args(["bgjob", "reap"])
        .assert()
        .success()
        .stdout("BGJOB_REAPED=0\n");
    assert!(
        row.exists(),
        "fresh malformed lease discarded the registry row"
    );
    assert!(
        pid_is_live(entry.child.pid),
        "fresh malformed lease killed the child"
    );
    assert!(
        lease.exists(),
        "fresh malformed lease was not retained for retry"
    );

    age_recovery_lease(&lease);
    sandbox
        .larch()
        .args(["bgjob", "reap"])
        .assert()
        .success()
        .stdout("BGJOB_REAPED=1\n");
    assert_group_gone(entry.child.pgid, "stale malformed recovery lease");
    assert!(!row.exists(), "reap retained the recovered registry row");
    assert!(
        !lease.exists(),
        "reap retained the reconciled recovery lease"
    );
}

#[test]
fn reap_recovers_after_the_live_recovery_claimant_is_killed() {
    let mut sandbox = Sandbox::new();
    let tmpdir = sandbox.session("reap-killed-claimant");
    let stdout = start(
        &sandbox,
        "reap-killed-claimant",
        &tmpdir,
        "60",
        std::process::id().try_into().expect("pid"),
        &["/bin/sh", "-c", "exec sleep 60"],
    );
    assert!(started_pgid(&stdout, "reap-killed-claimant") > 0);
    let row = registry_row(&sandbox, "reap-killed-claimant");
    let entry = read_entry(&row).expect("registry entry");
    nix::sys::signal::kill(
        nix::unistd::Pid::from_raw(entry.daemon.pid),
        nix::sys::signal::Signal::SIGKILL,
    )
    .expect("kill daemon");
    let deadline = Instant::now() + DEADLINE;
    while pid_is_live(entry.daemon.pid) && Instant::now() < deadline {
        sleep(POLL);
    }
    assert!(!pid_is_live(entry.daemon.pid), "daemon did not exit");

    let claimant_pid = sandbox.sleeper();
    let host = SystemProcessIdentityHost::new();
    let claimant = read_process_identity(&host, claimant_pid, "").expect("claimant identity");
    let lease = recovery_lease_path(&row);
    fs::write(&lease, identity_to_json(&claimant, None)).expect("recovery lease");
    sandbox
        .larch()
        .args(["bgjob", "reap"])
        .assert()
        .success()
        .stdout("BGJOB_REAPED=0\n");
    assert!(
        row.exists(),
        "live claimant did not retain the registry row"
    );
    assert!(
        pid_is_live(entry.child.pid),
        "live claimant allowed child teardown"
    );

    let claimant_child = sandbox
        .children
        .iter_mut()
        .find(|child| i32::try_from(child.id()).expect("pid") == claimant_pid)
        .expect("claimant child");
    claimant_child.kill().expect("kill claimant");
    claimant_child.wait().expect("reap claimant");

    sandbox
        .larch()
        .args(["bgjob", "reap"])
        .assert()
        .success()
        .stdout("BGJOB_REAPED=1\n");
    assert_group_gone(entry.child.pgid, "killed recovery claimant");
    assert!(
        !row.exists(),
        "reap retained the registry row after claimant death"
    );
    assert!(!lease.exists(), "reap retained the dead claimant lease");
}

#[test]
fn concurrent_reapers_leave_exactly_one_recovery_owner() {
    let sandbox = Sandbox::new();
    let tmpdir = sandbox.session("concurrent-reapers");
    let stdout = start(
        &sandbox,
        "concurrent-reapers",
        &tmpdir,
        "60",
        std::process::id().try_into().expect("pid"),
        &[
            "/bin/sh",
            "-c",
            "trap '' TERM; while true; do sleep 1; done",
        ],
    );
    assert!(started_pgid(&stdout, "concurrent-reapers") > 0);
    let row = registry_row(&sandbox, "concurrent-reapers");
    let entry = read_entry(&row).expect("registry entry");
    nix::sys::signal::kill(
        nix::unistd::Pid::from_raw(entry.daemon.pid),
        nix::sys::signal::Signal::SIGKILL,
    )
    .expect("kill daemon");
    let deadline = Instant::now() + DEADLINE;
    while pid_is_live(entry.daemon.pid) && Instant::now() < deadline {
        sleep(POLL);
    }
    assert!(!pid_is_live(entry.daemon.pid), "daemon did not exit");

    let first = reap_process(&sandbox).spawn().expect("first reaper");
    let second = reap_process(&sandbox).spawn().expect("second reaper");
    let first = first.wait_with_output().expect("first reaper output");
    let second = second.wait_with_output().expect("second reaper output");
    assert!(first.status.success(), "first reaper failed: {first:?}");
    assert!(second.status.success(), "second reaper failed: {second:?}");
    let reaped = [first.stdout, second.stdout]
        .into_iter()
        .filter(|stdout| stdout == b"BGJOB_REAPED=1\n")
        .count();
    assert_eq!(reaped, 1, "concurrent reapers did not elect one owner");
    assert_group_gone(entry.child.pgid, "concurrent recovery");
    assert!(
        !row.exists(),
        "concurrent recovery retained the registry row"
    );
}

#[test]
fn status_reports_a_live_registry_row_and_rejects_unsafe_steps() {
    let sandbox = Sandbox::new();
    let tmpdir = sandbox.session("status-check");
    let stdout = start(
        &sandbox,
        "status-check",
        &tmpdir,
        "60",
        std::process::id().try_into().expect("pid"),
        &["/bin/sh", "-c", "while true; do sleep 1; done"],
    );
    assert!(started_pgid(&stdout, "status-check") > 0);
    let row = registry_row(&sandbox, "status-check");

    let reported = String::from_utf8(
        sandbox
            .larch()
            .args(["bgjob", "status"])
            .assert()
            .success()
            .get_output()
            .stdout
            .clone(),
    )
    .expect("utf8 status stdout");
    assert!(
        reported.contains("BGJOB_STATUS=REGISTRY STEP=status-check"),
        "{reported:?}"
    );

    for step in ["../bad", "bad/step", "bad\\step", "BAD"] {
        sandbox
            .larch()
            .args(["bgjob", "start", "--step", step])
            .arg("--tmpdir")
            .arg(&tmpdir)
            .args(["--budget-s", "1", "--", "/bin/echo", "hi"])
            .assert()
            .code(2)
            .stdout(predicates::str::starts_with("BGJOB_ERROR="));
    }

    let entry = read_entry(&row).expect("registry entry");
    nix::sys::signal::kill(
        nix::unistd::Pid::from_raw(entry.daemon.pid),
        nix::sys::signal::Signal::SIGKILL,
    )
    .expect("kill daemon");
    let recovered = wait_until_settled(&sandbox, "status-check", &tmpdir);
    assert!(recovered.contains("BGJOB_STATUS=DEAD"), "{recovered:?}");
    assert!(
        !pid_is_live(entry.child.pid),
        "recovery left status child alive"
    );
    assert!(!row.exists(), "recovery retained status registry row");
}

#[test]
fn reap_retains_an_expired_row_when_its_child_birth_identity_is_stale() {
    let mut sandbox = Sandbox::new();
    let tmpdir = sandbox.session("reap-recycled");
    let log_dir = tmpdir.join("bgjob");
    fs::create_dir_all(&log_dir).expect("bgjob dir");
    let host = SystemProcessIdentityHost::new();
    let daemon_pid = sandbox.sleeper();
    let recycled_pid = sandbox.sleeper();
    let capture = |pid: i32| -> RecordedProcessIdentity {
        let deadline = Instant::now() + DEADLINE;
        loop {
            if let Some(identity) = read_process_identity(&host, pid, "") {
                return identity;
            }
            assert!(Instant::now() < deadline, "no identity for pid {pid}");
            sleep(POLL);
        }
    };
    let mut stale_child = capture(recycled_pid);
    stale_child.birth_identity = Some(match stale_child.birth_identity.expect("birth identity") {
        ProcessBirthIdentity::Darwin {
            seconds,
            microseconds,
        } => ProcessBirthIdentity::Darwin {
            seconds,
            microseconds: (microseconds + 1) % 1_000_000,
        },
        ProcessBirthIdentity::Linux {
            boot_id,
            start_ticks,
        } => ProcessBirthIdentity::Linux {
            boot_id,
            start_ticks: start_ticks.saturating_add(1),
        },
    });
    let mut stale_daemon = capture(daemon_pid);
    stale_daemon.start_time = format!("stale {}", stale_daemon.start_time);

    let entry = RegistryEntry {
        step: "reap-recycled".to_owned(),
        run_id: "reap-run".to_owned(),
        tmpdir,
        log_dir: log_dir.clone(),
        clone_path: std::env::current_dir().expect("cwd"),
        daemon: stale_daemon,
        child: stale_child,
        child_allows_exec: false,
        owner: None,
        start_epoch: epoch_now() - 10,
        budget_s: 1,
        stdout_log: log_dir.join("reap-recycled.stdout.log"),
        stderr_log: log_dir.join("reap-recycled.stderr.log"),
        result_env: log_dir.join("reap-recycled.result.env"),
    };
    for log in [&entry.stdout_log, &entry.stderr_log] {
        fs::write(log, "").expect("log file");
    }
    let row = write_entry_at(&entry, Some(&sandbox.registry())).expect("registry row");

    sandbox
        .larch()
        .args(["bgjob", "reap"])
        .assert()
        .code(2)
        .stdout(predicates::str::contains("BGJOB_RECOVERY_FAILED=1\n"));

    assert!(row.exists(), "reap discarded an unrecoverable registry row");
    assert!(
        pid_is_live(recycled_pid),
        "reap signalled the recycled pid {recycled_pid}"
    );
    let diagnostic = fs::read_to_string(&entry.stderr_log).expect("teardown diagnostic");
    assert!(
        diagnostic.contains("BGJOB_TEARDOWN_REASON=process-birth-identity-mismatch"),
        "reap did not retain a useful stale-identity diagnostic: {diagnostic:?}"
    );
    let waited = wait_with_run_id(&sandbox, "reap-recycled", &entry.tmpdir, "reap-run");
    assert!(waited.contains("BGJOB_STATUS=WAIT"), "{waited:?}");
    assert!(waited.contains("BGJOB_RECOVERY=retryable"), "{waited:?}");
    assert!(
        !waited.contains("BGJOB_STATUS=DEAD"),
        "unproven recovery became terminal: {waited:?}"
    );

    fs::write(
        &entry.result_env,
        "BGJOB_RC=0\nBGJOB_ELAPSED_S=0\nSTEP=reap-recycled\n",
    )
    .expect("completed envelope");
    sandbox
        .larch()
        .args(["bgjob", "reap"])
        .assert()
        .code(2)
        .stdout(predicates::str::contains("BGJOB_RECOVERY_FAILED=1\n"));
    assert!(
        row.exists(),
        "reap discarded a completed row without proving its group absent"
    );
}

#[test]
fn a_cancelled_wait_leaves_the_daemon_and_its_result_intact() {
    let sandbox = Sandbox::new();
    let tmpdir = sandbox.session("cancel-wait");
    let stdout = start(
        &sandbox,
        "cancel-wait",
        &tmpdir,
        "60",
        std::process::id().try_into().expect("pid"),
        &["/bin/sh", "-c", "sleep 2"],
    );
    assert!(started_pgid(&stdout, "cancel-wait") > 0);
    let row = registry_row(&sandbox, "cancel-wait");

    let mut waiter = Command::new(assert_cmd::cargo::cargo_bin("larch"))
        .args(["bgjob", "wait", "--step", "cancel-wait"])
        .arg("--tmpdir")
        .arg(&tmpdir)
        .args(["--max-wait-s", "200", "--poll-interval-s", "0.1"])
        .env("LARCH_BGJOB_REGISTRY_ROOT", sandbox.registry())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .expect("wait process");
    sleep(POLL);
    waiter.kill().expect("cancel the wait");
    waiter.wait().expect("reap the cancelled wait");

    // The daemon owns completion, so the cancelled wait leaves no partial
    // result behind and the next wait still observes the whole envelope.
    let settled = wait_until_settled(&sandbox, "cancel-wait", &tmpdir);
    assert!(settled.contains("BGJOB_STATUS=DONE"), "{settled:?}");
    assert!(settled.contains("BGJOB_RC=0"), "{settled:?}");
    let result =
        fs::read_to_string(tmpdir.join("bgjob/cancel-wait.result.env")).expect("result env");
    assert!(result.ends_with("STEP=cancel-wait\n"), "{result:?}");
    assert!(
        !row.exists(),
        "the finished daemon left its registry row behind"
    );
}
