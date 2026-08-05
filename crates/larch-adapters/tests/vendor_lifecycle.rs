use larch_adapters::{
    TemporaryRoot,
    vendor_lifecycle::{
        StartupLockConfig, external_startup_lock_acquire, external_startup_lock_release_after,
        stall_channel_progress, tree_latest_mtime, write_cursor_ci_stall_artifacts,
        write_timeout_stall_json,
    },
};
use larch_core::{
    CursorStallRecord, LauncherArtifactKind, LauncherArtifactPaths, TimeoutStallRecord,
    VendorProgram,
};
use std::{fs, thread, time::Duration};

fn temporary_root(path: &std::path::Path) -> TemporaryRoot {
    TemporaryRoot::resolve(Some(path)).expect("temporary root")
}

fn config(program: VendorProgram) -> StartupLockConfig {
    StartupLockConfig::from_values(
        program,
        "Darwin",
        Some("tester"),
        Some("30"),
        Some("100"),
        Some("0.05"),
    )
    .expect("startup config")
    .with_retry_delay(Duration::from_millis(5))
}

#[test]
fn startup_lock_is_platform_scoped_and_rejects_path_components() {
    let directory = tempfile::tempdir().expect("temporary directory");
    let root = temporary_root(directory.path());
    let linux = StartupLockConfig::from_values(
        VendorProgram::Codex,
        "Linux",
        Some("tester"),
        None,
        None,
        None,
    )
    .expect("Linux config");
    assert!(
        !external_startup_lock_acquire(&root, &linux)
            .expect("disabled lock")
            .is_acquired()
    );
    assert!(
        StartupLockConfig::from_values(
            VendorProgram::Codex,
            "Darwin",
            Some("../escape"),
            None,
            None,
            None,
        )
        .is_err()
    );
}

#[test]
fn concurrent_startups_serialize_until_delayed_release() {
    let directory = tempfile::tempdir().expect("temporary directory");
    let root = temporary_root(directory.path());
    let config = config(VendorProgram::Cursor);
    let first = external_startup_lock_acquire(&root, &config).expect("first lock");
    assert!(first.is_acquired());
    let release = external_startup_lock_release_after(first, &config).expect("schedule release");
    let started = std::time::Instant::now();
    let waiter = thread::spawn(move || external_startup_lock_acquire(&root, &config));
    let second = waiter.join().expect("waiter thread").expect("second lock");

    assert!(second.is_acquired());
    assert!(started.elapsed() >= Duration::from_millis(30));
    release.wait().expect("release completed");
    drop(second);
    assert!(
        !directory
            .path()
            .join("larch-external-startup-tester.lock")
            .exists()
    );
}

#[test]
fn stall_channels_track_stdout_file_and_tree_markers() {
    let directory = tempfile::tempdir().expect("temporary directory");
    let output = directory.path().join("output");
    fs::write(&output, b"abc").expect("output");
    let (changed, marker) = stall_channel_progress("stdout", &output, 0.0);
    assert!(changed);
    assert_eq!(marker.to_bits(), 3.0_f64.to_bits());
    assert_eq!(
        stall_channel_progress("stdout", &output, marker),
        (false, marker)
    );

    let watched = directory.path().join("watched");
    fs::write(&watched, b"body").expect("watched file");
    let channel = format!("file:{}", watched.display());
    let (changed, file_marker) = stall_channel_progress(&channel, &output, 0.0);
    assert!(changed);
    assert!(file_marker > 4.0);

    let git = directory.path().join(".git");
    fs::create_dir(&git).expect("git directory");
    fs::write(git.join("ignored"), b"ignored").expect("ignored file");
    assert!(tree_latest_mtime(directory.path()) > 0.0);
    assert_eq!(
        stall_channel_progress("unknown", &output, 17.0),
        (false, 17.0)
    );
}

#[test]
fn stall_artifacts_use_explicit_confined_paths_and_exact_json() {
    let directory = tempfile::tempdir().expect("temporary directory");
    let root = temporary_root(directory.path());
    let paths = LauncherArtifactPaths::new(root.path().join("output"));
    let primary = paths.path(LauncherArtifactKind::StallJson);
    let sidecar = root.path().join("sidecar.json");
    let record = CursorStallRecord::new(
        "stdout",
        99,
        Duration::from_secs(45),
        " M file",
        "last output",
    );
    write_cursor_ci_stall_artifacts(&root, &paths, Some(&sidecar), &record)
        .expect("Cursor artifacts");
    assert_eq!(
        fs::read_to_string(&primary).expect("primary"),
        fs::read_to_string(&sidecar).expect("sidecar")
    );
    let rejected_sidecar = directory.path().with_extension("outside.json");
    write_cursor_ci_stall_artifacts(&root, &paths, Some(&rejected_sidecar), &record)
        .expect("best-effort sidecar");
    assert!(!rejected_sidecar.exists());

    let timeout_paths = LauncherArtifactPaths::new(root.path().join("timeout"));
    let timeout = timeout_paths.path(LauncherArtifactKind::StallJson);
    let timeout_record = TimeoutStallRecord {
        tool: "cursor",
        exit_code: 124,
        timeout: 600,
    };
    assert!(
        write_timeout_stall_json(&root, &timeout_paths, &timeout_record, false)
            .expect("write timeout")
    );
    assert_eq!(
        fs::read_to_string(&timeout).expect("timeout JSON"),
        "{\"tool\":\"cursor\",\"exit_code\":124,\"timeout\":600}\n"
    );
    assert!(
        !write_timeout_stall_json(&root, &timeout_paths, &timeout_record, false)
            .expect("preserve timeout")
    );
}
