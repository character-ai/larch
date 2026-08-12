#![cfg(unix)]

use larch_adapters::SystemProcessIdentityHost;
use larch_core::{
    IdentityProbeOutput, KillLogEvent, ProcessBirthIdentity, ProcessBirthIdentityProbeOutput,
    ProcessIdentityHost, ProcessIdentityValidationPolicy, RecordedProcessIdentity, TerminateSignal,
    append_kill_log, kill_session_background_processes, read_identity_record,
    read_process_identity, validate_process_identity_with_policy, write_identity_record,
};
use std::{
    fs,
    process::{self, Command},
    thread,
    time::{Duration, Instant},
};
use tempfile::TempDir;

#[test]
fn system_host_probes_the_current_process() {
    let host = SystemProcessIdentityHost::new();
    let process_id = i32::try_from(process::id()).expect("pid");
    let process_group_id = host.get_pgid(process_id).expect("current process pgid");
    assert!(process_group_id > 0);
    match host.probe_ps_identity(process_id) {
        IdentityProbeOutput::Stdout(stdout) => assert!(!stdout.trim().is_empty()),
        other => panic!("unexpected probe result: {other:?}"),
    }
    assert!(host.parent_of(process_id).is_some());
    assert!(!host.list_processes().is_empty());
    assert_eq!(host.current_pid(), process_id);
    #[cfg(any(target_os = "macos", target_os = "linux"))]
    assert!(
        read_process_identity(&host, process_id, "")
            .and_then(|identity| identity.birth_identity)
            .is_some(),
        "supported hosts must expose a kernel process-birth identity"
    );
    assert!(host.parent_pid() > 0);
    assert!(!host.resolve_path("/tmp").is_empty());
    assert!(!host.signal_process(i32::MAX - 1, TerminateSignal::Term));
}

#[cfg(any(target_os = "macos", target_os = "linux"))]
#[test]
fn system_host_probes_a_live_child_process() {
    let host = SystemProcessIdentityHost::new();
    let mut child = Command::new("/bin/sleep")
        .arg("30")
        .spawn()
        .expect("sleep child");
    let process_id = i32::try_from(child.id()).expect("child pid");
    let identity = read_process_identity(&host, process_id, "");
    let _ignored = child.kill();
    let _ignored = child.wait();
    assert!(
        identity
            .and_then(|identity| identity.birth_identity)
            .is_some(),
        "supported hosts must expose a kernel process-birth identity for a live child"
    );
}

#[cfg(any(target_os = "macos", target_os = "linux"))]
#[test]
fn system_host_keeps_birth_identity_through_child_exec() {
    let host = SystemProcessIdentityHost::new();
    let mut child = Command::new("/bin/sh")
        .args(["-c", "sleep 1; exec sleep 30"])
        .spawn()
        .expect("exec child");
    let process_id = i32::try_from(child.id()).expect("child pid");
    let recorded = read_process_identity(&host, process_id, "").expect("wrapper identity");
    let deadline = Instant::now() + Duration::from_secs(5);
    let mut validation = validate_process_identity_with_policy(
        &host,
        &recorded,
        ProcessIdentityValidationPolicy::AllowCommandTransition,
    );
    while !(validation.ok
        && validation
            .current
            .as_ref()
            .is_some_and(|current| current.command_signature != recorded.command_signature))
        && Instant::now() < deadline
    {
        thread::sleep(Duration::from_millis(50));
        validation = validate_process_identity_with_policy(
            &host,
            &recorded,
            ProcessIdentityValidationPolicy::AllowCommandTransition,
        );
    }
    let _ignored = child.kill();
    let _ignored = child.wait();
    assert!(
        validation
            .current
            .as_ref()
            .is_some_and(|current| current.command_signature != recorded.command_signature),
        "child did not exec before deadline: {validation:?}"
    );
    assert!(validation.ok, "exec validation failed: {validation:?}");
}

#[cfg(any(target_os = "macos", target_os = "linux"))]
#[test]
fn system_host_marks_a_reaped_child_birth_probe_missing() {
    let host = SystemProcessIdentityHost::new();
    let mut child = Command::new("/usr/bin/true").spawn().expect("true child");
    let process_id = i32::try_from(child.id()).expect("child pid");
    child.wait().expect("reap true child");
    assert!(matches!(
        host.probe_process_birth_identity(process_id),
        ProcessBirthIdentityProbeOutput::Missing
    ));
}

#[test]
fn system_host_round_trips_identity_and_kill_log() {
    let host = SystemProcessIdentityHost::new();
    let root = TempDir::new().expect("tmpdir");
    let path = root.path().join("identity.json");
    let recorded = RecordedProcessIdentity {
        pid: 7,
        pgid: 7,
        start_time: "start".to_owned(),
        birth_identity: Some(ProcessBirthIdentity::Darwin {
            seconds: 1,
            microseconds: 7,
        }),
        command_signature: "cmd".to_owned(),
        expected_signature: "cmd".to_owned(),
    };
    write_identity_record(&host, &path, &recorded, None).expect("write");
    assert_eq!(read_identity_record(&host, &path), Some(recorded));
    assert!(host.is_regular_file(&path));
    assert!(host.file_mtime_ns(&path).is_some());
    assert!(host.read_text_lossy(&path).is_some());

    let log = root.path().join("kill.jsonl");
    append_kill_log(
        &host,
        Some(&log),
        &KillLogEvent {
            event: "signal".to_owned(),
            signal: "SIGTERM".to_owned(),
            pid: 7,
            pgid: 7,
            command: "cmd".to_owned(),
            caller: "test".to_owned(),
            reason: "unit".to_owned(),
            descendants: Vec::new(),
            tmpdir_needle: String::new(),
            physical_needle: String::new(),
        },
    );
    let text = fs::read_to_string(&log).expect("log");
    assert!(text.contains("\"signal\":\"SIGTERM\""));
    host.remove_file(&path);
    assert!(!path.exists());
}

#[test]
fn system_host_kill_session_is_safe_for_empty_and_isolated_tmpdir() {
    let host = SystemProcessIdentityHost::default();
    assert!(!kill_session_background_processes(&host, ""));
    let root = TempDir::new().expect("tmpdir");
    let needle = root.path().join("unique-larch-kill-needle-8061");
    fs::create_dir_all(&needle).expect("dir");
    assert!(!kill_session_background_processes(
        &host,
        needle.to_str().expect("utf8")
    ));
    let _ = read_process_identity(&host, -1, "");
    assert!(host.pgrep_children(-1).is_empty());
    assert!(host.pgrep_group(-1).is_empty());
    assert!(host.get_pgid(-1).is_none());
    assert!(host.get_pgid(0).is_none());
    match host.probe_ps_identity(-1) {
        IdentityProbeOutput::Missing | IdentityProbeOutput::Error => {}
        other => panic!("unexpected probe for invalid pid: {other:?}"),
    }
    host.sleep(std::time::Duration::from_millis(1));
    assert!(host.monotonic_now().as_nanos() > 0);
    assert!(host.wall_time_secs() > 0.0);
    assert!(!host.signal_group(i32::MAX, TerminateSignal::Kill));
}
