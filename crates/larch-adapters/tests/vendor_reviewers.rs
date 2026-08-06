//! Integration coverage for `check_reviewers` probe orchestration.

use larch_adapters::{
    TemporaryRoot,
    runtime::LarchRuntime,
    vendor_auth::ProbeCache,
    vendor_reviewers::{CheckReviewersContext, check_reviewers, run_cursor_model_list},
};
use larch_core::{
    CURSOR_MODEL_LIST_HEADER, CheckReviewersConfig, ChildEnvironment,
    MODEL_PINS_STATUS_LIST_FAILED, PROBE_TIMEOUT_EXIT_CODE, ProbeTtl, ProcessError,
    ProcessErrorKind, VendorProgram, list_failed_detail, probe_stamp_file_name, resolve_model_pins,
};
use larch_test_support::{FakeProcessRunner, NeverCancelled, ProcessOutputBuilder};
use std::{
    collections::BTreeMap,
    fs,
    os::unix::fs::PermissionsExt,
    path::{Path, PathBuf},
    time::Duration,
};

fn temporary_root(path: &Path) -> TemporaryRoot {
    TemporaryRoot::resolve(Some(path)).expect("temporary root")
}

fn make_executable(dir: &Path, name: &str) -> PathBuf {
    fs::create_dir_all(dir).expect("bin dir");
    let path = dir.join(name);
    fs::write(&path, b"#!/bin/sh\nexit 0\n").expect("write binary");
    let mut permissions = fs::metadata(&path).expect("meta").permissions();
    permissions.set_mode(0o755);
    fs::set_permissions(&path, permissions).expect("chmod");
    path
}

fn config(skip_codex: bool, skip_cursor: bool) -> CheckReviewersConfig {
    CheckReviewersConfig::from_env_values(
        Some("60"),
        Some("0"),
        Some("5"),
        Some("1"),
        Some("0"),
        Some("0"),
        skip_codex,
        skip_cursor,
        Some(5),
    )
}

fn run_check(
    runner: &FakeProcessRunner,
    config: &CheckReviewersConfig,
    temp: &Path,
    home: &Path,
    path_env: Option<&str>,
    cursor_api_key: Option<&str>,
) -> larch_core::CheckReviewersResult {
    let root = temporary_root(temp);
    let env_map = BTreeMap::new();
    let context = CheckReviewersContext {
        temporary_root: &root,
        home,
        working_directory: temp,
        path_env,
        user: Some("ada"),
        openai_api_key: None,
        cursor_api_key,
        platform: "Linux",
        env_map: &env_map,
    };
    let runtime = LarchRuntime::current_thread().expect("runtime");
    runtime.block_on(check_reviewers(runner, config, context, &NeverCancelled))
}

#[test]
fn missing_binaries_report_all_false_without_spawning() {
    let temp = tempfile::tempdir().expect("temp");
    let empty = temp.path().join("empty-bin");
    fs::create_dir_all(&empty).expect("empty bin");
    let home = tempfile::tempdir().expect("home");
    let runner = FakeProcessRunner::new(std::iter::empty());

    let result = run_check(
        &runner,
        &config(false, false),
        temp.path(),
        home.path(),
        Some(empty.to_str().expect("utf8")),
        None,
    );

    assert!(!result.codex_binary_found());
    assert!(!result.cursor_binary_found());
    assert!(!result.codex_present());
    assert!(!result.cursor_present());
    assert!(!result.codex_probe_timed_out());
    assert!(!result.cursor_probe_timed_out());
    assert_eq!(runner.requests().len(), 0);
}

#[test]
fn cursor_cache_hit_skips_probe_spawn() {
    let temp = tempfile::tempdir().expect("temp");
    let bin = temp.path().join("bin");
    make_executable(&bin, "cursor");
    let home = tempfile::tempdir().expect("home");
    let cache = ProbeCache::new(
        temporary_root(temp.path()),
        Some("ada"),
        ProbeTtl::from_seconds(60, 0),
    );
    cache.write_verdict("cursor", true).expect("stamp");
    let runner = FakeProcessRunner::new(std::iter::empty());

    let result = run_check(
        &runner,
        &config(true, false),
        temp.path(),
        home.path(),
        Some(bin.to_str().expect("utf8")),
        Some("cursor-secret-token-value"),
    );

    assert!(result.cursor_binary_found());
    assert!(result.cursor_present());
    assert!(!result.cursor_probe_timed_out());
    assert_eq!(runner.requests().len(), 0);
}

#[test]
fn cursor_probe_success_marks_present_and_writes_stamp() {
    let temp = tempfile::tempdir().expect("temp");
    let bin = temp.path().join("bin");
    make_executable(&bin, "cursor");
    let home = tempfile::tempdir().expect("home");
    let runner = FakeProcessRunner::new([Ok(ProcessOutputBuilder::success()
        .stdout(b"OK\n".to_vec())
        .build())]);

    let result = run_check(
        &runner,
        &config(true, false),
        temp.path(),
        home.path(),
        Some(bin.to_str().expect("utf8")),
        Some("cursor-secret-token-value"),
    );

    assert!(result.cursor_binary_found());
    assert!(result.cursor_present());
    assert!(!result.cursor_probe_timed_out());
    assert_eq!(runner.requests().len(), 1);
    let request = &runner.requests()[0];
    assert_eq!(
        request.program(),
        &larch_core::ExternalProgram::Vendor(VendorProgram::Cursor)
    );
    assert!(
        request
            .environment()
            .iter()
            .any(|(key, _)| *key == ChildEnvironment::CursorApiKey
                || *key == ChildEnvironment::CursorConfigDir
                || *key == ChildEnvironment::NoOpenBrowser)
    );

    let stamp = temporary_root(temp.path())
        .path()
        .join(probe_stamp_file_name("cursor", "ada"));
    assert_eq!(fs::read_to_string(stamp).expect("stamp"), "true\n");
}

#[test]
fn cursor_model_list_timeout_and_list_failed_shapes() {
    let temp = tempfile::tempdir().expect("temp");
    let workdir = fs::canonicalize(temp.path()).expect("canonical");
    let runtime = LarchRuntime::current_thread().expect("runtime");

    let timed_out = FakeProcessRunner::new([Err(ProcessError::new(
        ProcessErrorKind::TimedOut,
        "timed out",
        None,
    ))]);
    let timeout_outcome = runtime.block_on(run_cursor_model_list(
        &timed_out,
        &workdir,
        Duration::from_secs(1),
        &NeverCancelled,
    ));
    assert!(timeout_outcome.timed_out);
    assert_eq!(timeout_outcome.returncode, PROBE_TIMEOUT_EXIT_CODE);
    let pins = resolve_model_pins("ok", "ok", Some(timeout_outcome.clone()));
    assert_eq!(pins.cursor.status(), MODEL_PINS_STATUS_LIST_FAILED);
    assert_eq!(
        pins.cursor.detail(),
        list_failed_detail(
            timeout_outcome.returncode,
            &timeout_outcome.stderr,
            timeout_outcome.timed_out
        )
    );

    let failed = FakeProcessRunner::new([Ok(ProcessOutputBuilder::failure(2)
        .stderr(b"list blew up\n".to_vec())
        .build())]);
    let failed_outcome = runtime.block_on(run_cursor_model_list(
        &failed,
        &workdir,
        Duration::from_secs(1),
        &NeverCancelled,
    ));
    assert!(!failed_outcome.timed_out);
    assert_eq!(failed_outcome.returncode, 2);
    assert_eq!(failed_outcome.stderr, "list blew up\n");
    let pins = resolve_model_pins("ok", "ok", Some(failed_outcome.clone()));
    assert_eq!(pins.cursor.status(), MODEL_PINS_STATUS_LIST_FAILED);
    assert_eq!(
        pins.cursor.detail(),
        list_failed_detail(
            failed_outcome.returncode,
            &failed_outcome.stderr,
            failed_outcome.timed_out
        )
    );

    let ok = FakeProcessRunner::new([Ok(ProcessOutputBuilder::success()
        .stdout(format!("{CURSOR_MODEL_LIST_HEADER}\nother - x\n").into_bytes())
        .build())]);
    let ok_outcome = runtime.block_on(run_cursor_model_list(
        &ok,
        &workdir,
        Duration::from_secs(1),
        &NeverCancelled,
    ));
    assert_eq!(ok_outcome.returncode, 0);
    assert!(!ok_outcome.timed_out);
    assert!(ok_outcome.stdout.contains(CURSOR_MODEL_LIST_HEADER));
}
