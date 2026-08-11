//! Real-process regression harness for `bgjob start`, `wait`, `status`, and `reap`.
//!
//! Replaces the retired `scripts/test-bgjob.sh` shell harness: the commands are
//! Rust-owned after #8063, so their transport coverage runs where the verified
//! binary is already built.

#![cfg(unix)]

use assert_cmd::Command as AssertCommand;
use larch_adapters::SystemProcessIdentityHost;
use larch_core::{
    KvDocument, ParseOptions, RecordedProcessIdentity, RegistryEntry, RenderOptions, read_entry,
    read_process_identity, write_entry_at,
};
use std::{
    fs,
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
            .env_remove("LARCH_RUN_ID");
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

fn pid_is_live(pid: i32) -> bool {
    nix::sys::signal::kill(nix::unistd::Pid::from_raw(pid), None).is_ok()
}

fn group_is_live(pgid: i32) -> bool {
    nix::sys::signal::kill(nix::unistd::Pid::from_raw(-pgid), None).is_ok()
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

    // A completed job leaves no registry row, so `reap` has nothing to remove.
    sandbox
        .larch()
        .args(["bgjob", "reap"])
        .assert()
        .success()
        .stdout("BGJOB_REAPED=0\n");
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
        "1",
        std::process::id().try_into().expect("pid"),
        &["/bin/sh", "-c", "exec sleep 60"],
    );
    let pgid = started_pgid(&stdout, "budget-exec");
    let row = registry_row(&sandbox, "budget-exec");
    let child_pid = read_entry(&row).expect("registry entry").child.pid;

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
fn reap_retains_an_expired_row_when_its_child_identity_is_stale() {
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
    stale_child.start_time = format!("stale {}", stale_child.start_time);
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
        .success()
        .stdout("BGJOB_REAPED=0\n");

    assert!(row.exists(), "reap discarded an unrecoverable registry row");
    assert!(
        pid_is_live(recycled_pid),
        "reap signalled the recycled pid {recycled_pid}"
    );
    let diagnostic = fs::read_to_string(&entry.stderr_log).expect("teardown diagnostic");
    assert!(
        diagnostic.contains("BGJOB_TEARDOWN_REASON=start-time-mismatch"),
        "reap did not retain a useful stale-identity diagnostic: {diagnostic:?}"
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
        .success()
        .stdout("BGJOB_REAPED=0\n");
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
