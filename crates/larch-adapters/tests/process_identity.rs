#![cfg(unix)]

use larch_adapters::SystemProcessIdentityHost;
use larch_core::{
    IdentityProbeOutput, KillLogEvent, ProcessIdentityHost, RecordedProcessIdentity,
    TerminateSignal, append_kill_log, kill_session_background_processes, read_identity_record,
    read_process_identity, write_identity_record,
};
use std::{fs, process};
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
    assert!(host.parent_pid() > 0);
    assert!(!host.resolve_path("/tmp").is_empty());
    assert!(!host.signal_process(i32::MAX - 1, TerminateSignal::Term));
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
