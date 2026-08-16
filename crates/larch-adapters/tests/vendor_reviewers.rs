//! Integration coverage for `check_reviewers` probe orchestration.

use larch_adapters::{
    SecureTempDir, TemporaryRoot,
    runtime::LarchRuntime,
    vendor_auth::ProbeCache,
    vendor_reviewers::{
        CheckReviewersContext, CursorModelListContext, check_reviewers, prepare_codex_home,
        run_cursor_model_list,
    },
};
use larch_core::{
    CODEX_REVIEW_MODEL_DEFAULT, CURSOR_MODEL_LIST_HEADER, CheckReviewersConfig, ChildEnvironment,
    CodexGateDetail, ExternalProgram, HostUtilityProgram, MODEL_PINS_STATUS_LIST_FAILED,
    PROBE_TIMEOUT_EXIT_CODE, ProbeTtl, ProcessError, ProcessErrorKind, VendorProgram,
    codex_env_auth_from_key, codex_gate_detail_file_name, codex_probe_identity,
    detect_codex_cli_gate, list_failed_detail, probe_stamp_file_name, resolve_model_pins,
};
use larch_test_support::{FakeProcessRunner, NeverCancelled, ProcessOutputBuilder};
use std::{
    collections::BTreeMap,
    fs,
    os::unix::fs::PermissionsExt,
    path::{Path, PathBuf},
    time::Duration,
};

const SECRET: &str = "cursor-secret-token-value";

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

fn config_with_negative_cache(skip_codex: bool, skip_cursor: bool) -> CheckReviewersConfig {
    CheckReviewersConfig::from_env_values(
        Some("60"),
        Some("30"),
        Some("5"),
        Some("1"),
        Some("0"),
        Some("0"),
        skip_codex,
        skip_cursor,
        Some(5),
    )
}

fn codex_identity(openai_api_key: Option<&str>) -> String {
    codex_probe_identity(
        codex_env_auth_from_key(openai_api_key),
        CODEX_REVIEW_MODEL_DEFAULT,
    )
}

fn codex_cache(temp: &Path) -> ProbeCache {
    ProbeCache::new(
        temporary_root(temp),
        Some("ada"),
        ProbeTtl::from_seconds(60, 0),
    )
}

fn gate_detail() -> CodexGateDetail {
    detect_codex_cli_gate(
        "requires a newer version of Codex",
        CODEX_REVIEW_MODEL_DEFAULT,
    )
    .expect("gate detail")
}

fn keychain_miss() -> larch_core::ProcessOutput {
    ProcessOutputBuilder::failure(1)
        .stderr(b"The specified item could not be found in the keychain.\n".to_vec())
        .build()
}

#[allow(clippy::too_many_arguments)] // test harness mirrors CheckReviewersContext fields
fn run_check_on_platform(
    runner: &FakeProcessRunner,
    config: &CheckReviewersConfig,
    temp: &Path,
    home: &Path,
    path_env: Option<&str>,
    openai_api_key: Option<&str>,
    cursor_api_key: Option<&str>,
    platform: &str,
) -> larch_core::CheckReviewersResult {
    let root = temporary_root(temp);
    let env_map = BTreeMap::new();
    let context = CheckReviewersContext {
        temporary_root: &root,
        home,
        working_directory: temp,
        path_env,
        user: Some("ada"),
        openai_api_key,
        cursor_api_key,
        platform,
        env_map: &env_map,
    };
    let runtime = LarchRuntime::current_thread().expect("runtime");
    runtime.block_on(check_reviewers(runner, config, context, &NeverCancelled))
}

fn run_check(
    runner: &FakeProcessRunner,
    config: &CheckReviewersConfig,
    temp: &Path,
    home: &Path,
    path_env: Option<&str>,
    cursor_api_key: Option<&str>,
) -> larch_core::CheckReviewersResult {
    run_check_on_platform(
        runner,
        config,
        temp,
        home,
        path_env,
        None,
        cursor_api_key,
        "Linux",
    )
}

const fn model_list_context<'a>(
    root: &'a TemporaryRoot,
    home: &'a Path,
    working_directory: &'a Path,
) -> CursorModelListContext<'a> {
    CursorModelListContext {
        temporary_root: root,
        home,
        working_directory,
        user: Some("ada"),
        cursor_api_key: Some(SECRET),
        platform: "Linux",
        caller: "test cursor model list",
    }
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
    let root = temporary_root(temp.path());
    let home = tempfile::tempdir().expect("home");
    let runtime = LarchRuntime::current_thread().expect("runtime");

    let timed_out = FakeProcessRunner::new([Err(ProcessError::new(
        ProcessErrorKind::TimedOut,
        "timed out",
        None,
    ))]);
    let timeout_outcome = runtime.block_on(run_cursor_model_list(
        &timed_out,
        model_list_context(&root, home.path(), &workdir),
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
        model_list_context(&root, home.path(), &workdir),
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
        model_list_context(&root, home.path(), &workdir),
        Duration::from_secs(1),
        &NeverCancelled,
    ));
    assert_eq!(ok_outcome.returncode, 0);
    assert!(!ok_outcome.timed_out);
    assert!(ok_outcome.stdout.contains(CURSOR_MODEL_LIST_HEADER));
    let request = &ok.requests()[0];
    assert!(
        request
            .environment()
            .iter()
            .any(|(key, value)| { *key == ChildEnvironment::CursorApiKey && value == SECRET })
    );
    assert!(
        request
            .environment()
            .iter()
            .any(|(key, _)| *key == ChildEnvironment::CursorConfigDir)
    );
    assert!(
        request
            .environment()
            .iter()
            .any(|(key, _)| *key == ChildEnvironment::NoOpenBrowser)
    );
}

#[test]
fn codex_positive_cache_hit_skips_probe_spawn() {
    let temp = tempfile::tempdir().expect("temp");
    let bin = temp.path().join("bin");
    make_executable(&bin, "codex");
    let home = tempfile::tempdir().expect("home");
    let identity = codex_identity(None);
    codex_cache(temp.path())
        .write_verdict(&identity, true)
        .expect("stamp");
    let runner = FakeProcessRunner::new(std::iter::empty());

    let result = run_check_on_platform(
        &runner,
        &config(false, true),
        temp.path(),
        home.path(),
        Some(bin.to_str().expect("utf8")),
        None,
        None,
        "Linux",
    );

    assert!(result.codex_binary_found());
    assert!(result.codex_present());
    assert!(!result.codex_probe_timed_out());
    assert!(result.codex_gate_detail().is_none());
    assert_eq!(runner.requests().len(), 0);
}

#[test]
fn codex_negative_cache_hit_returns_gate_detail_without_spawn() {
    let temp = tempfile::tempdir().expect("temp");
    let bin = temp.path().join("bin");
    make_executable(&bin, "codex");
    let home = tempfile::tempdir().expect("home");
    let identity = codex_identity(None);
    let cache = codex_cache(temp.path());
    let detail = gate_detail();
    cache.write_verdict(&identity, false).expect("stamp");
    cache
        .write_gate_detail(&identity, &detail)
        .expect("gate detail");
    let runner = FakeProcessRunner::new(std::iter::empty());

    let result = run_check_on_platform(
        &runner,
        &config_with_negative_cache(false, true),
        temp.path(),
        home.path(),
        Some(bin.to_str().expect("utf8")),
        None,
        None,
        "Linux",
    );

    assert!(result.codex_binary_found());
    assert!(!result.codex_present());
    assert_eq!(result.codex_gate_detail(), Some(&detail));
    assert_eq!(runner.requests().len(), 0);
}

#[test]
fn codex_live_probe_success_writes_identity_stamp() {
    let temp = tempfile::tempdir().expect("temp");
    let bin = temp.path().join("bin");
    make_executable(&bin, "codex");
    let home = tempfile::tempdir().expect("home");
    let runner = FakeProcessRunner::new([Ok(ProcessOutputBuilder::success().build())]);
    let identity = codex_identity(None);

    let result = run_check_on_platform(
        &runner,
        &config(false, true),
        temp.path(),
        home.path(),
        Some(bin.to_str().expect("utf8")),
        None,
        None,
        "Linux",
    );

    assert!(result.codex_binary_found());
    assert!(result.codex_present());
    assert!(!result.codex_probe_timed_out());
    assert!(result.codex_gate_detail().is_none());
    assert_eq!(runner.requests().len(), 1);
    assert_eq!(
        runner.requests()[0].program(),
        &larch_core::ExternalProgram::Vendor(VendorProgram::Codex)
    );
    assert!(
        runner.requests()[0]
            .environment()
            .iter()
            .any(|(key, _)| *key == ChildEnvironment::CodexHome)
    );

    let stamp = temporary_root(temp.path())
        .path()
        .join(probe_stamp_file_name(&identity, "ada"));
    assert_eq!(fs::read_to_string(stamp).expect("stamp"), "true\n");
}

#[test]
fn codex_probe_timeout_sets_timed_out_flag() {
    let temp = tempfile::tempdir().expect("temp");
    let bin = temp.path().join("bin");
    make_executable(&bin, "codex");
    let home = tempfile::tempdir().expect("home");
    let runner = FakeProcessRunner::new([Err(ProcessError::new(
        ProcessErrorKind::TimedOut,
        "timed out",
        None,
    ))]);

    let result = run_check_on_platform(
        &runner,
        &config(false, true),
        temp.path(),
        home.path(),
        Some(bin.to_str().expect("utf8")),
        None,
        None,
        "Linux",
    );

    assert!(result.codex_binary_found());
    assert!(!result.codex_present());
    assert!(result.codex_probe_timed_out());
    assert_eq!(runner.requests().len(), 1);
}

#[test]
fn codex_probe_gate_failure_persists_gate_detail() {
    let temp = tempfile::tempdir().expect("temp");
    let bin = temp.path().join("bin");
    make_executable(&bin, "codex");
    let home = tempfile::tempdir().expect("home");
    let identity = codex_identity(None);
    let detail = gate_detail();
    let runner = FakeProcessRunner::new([Ok(ProcessOutputBuilder::failure(1)
        .stderr(b"requires a newer version of Codex\n".to_vec())
        .build())]);

    let result = run_check_on_platform(
        &runner,
        &config(false, true),
        temp.path(),
        home.path(),
        Some(bin.to_str().expect("utf8")),
        None,
        None,
        "Linux",
    );

    assert!(!result.codex_present());
    assert!(!result.codex_probe_timed_out());
    assert_eq!(result.codex_gate_detail(), Some(&detail));
    let gate_path = temporary_root(temp.path())
        .path()
        .join(codex_gate_detail_file_name(&identity, "ada"));
    assert!(gate_path.is_file());
}

#[test]
fn codex_probe_auth_failure_marks_absent() {
    let temp = tempfile::tempdir().expect("temp");
    let bin = temp.path().join("bin");
    make_executable(&bin, "codex");
    let home = tempfile::tempdir().expect("home");
    let runner = FakeProcessRunner::new([Ok(ProcessOutputBuilder::failure(1)
        .stderr(b"not logged in\n".to_vec())
        .build())]);

    let result = run_check_on_platform(
        &runner,
        &config(false, true),
        temp.path(),
        home.path(),
        Some(bin.to_str().expect("utf8")),
        None,
        None,
        "Linux",
    );

    assert!(!result.codex_present());
    assert!(!result.codex_probe_timed_out());
    assert!(result.codex_gate_detail().is_none());
    assert_eq!(runner.requests().len(), 1);
}

#[test]
fn codex_home_strips_sensitive_operator_config() {
    let temp = tempfile::tempdir().expect("temp");
    let home = temp.path().join("home");
    let codex_dir = home.join(".codex");
    fs::create_dir_all(&codex_dir).expect("codex dir");
    fs::write(
        codex_dir.join("config.toml"),
        r#"model = "gpt-test"
[[model_providers.openai-larch-env]]
base_url = "https://example.com"
env_key = "OPENAI_API_KEY"
api_key = "sk-secret-should-not-appear"
model_provider = "openai-larch-env"
openai_api_key = "also-stripped"
[features]
enabled = true
"#,
    )
    .expect("write config");

    let root = temporary_root(temp.path());
    let probe_home = SecureTempDir::create(&root, "larch-codex-probe-home-").expect("probe home");
    prepare_codex_home(probe_home.path(), &home, None).expect("prepare");

    let stripped = fs::read_to_string(probe_home.path().join("config.toml")).expect("probe config");
    assert!(stripped.contains("model = \"gpt-test\""));
    assert!(stripped.contains("[features]"));
    assert!(!stripped.contains("openai-larch-env"));
    assert!(!stripped.contains("OPENAI_API_KEY"));
    assert!(!stripped.contains("sk-secret"));
    assert!(!stripped.contains("api_key"));
}

#[test]
fn cursor_probe_timeout_sets_timed_out_flag() {
    let temp = tempfile::tempdir().expect("temp");
    let bin = temp.path().join("bin");
    make_executable(&bin, "cursor");
    let home = tempfile::tempdir().expect("home");
    let runner = FakeProcessRunner::new([Err(ProcessError::new(
        ProcessErrorKind::TimedOut,
        "timed out",
        None,
    ))]);

    let result = run_check(
        &runner,
        &config(true, false),
        temp.path(),
        home.path(),
        Some(bin.to_str().expect("utf8")),
        Some(SECRET),
    );

    assert!(result.cursor_binary_found());
    assert!(!result.cursor_present());
    assert!(result.cursor_probe_timed_out());
    assert_eq!(runner.requests().len(), 1);
}

#[test]
fn cursor_preread_failure_on_darwin_skips_agent_probe() {
    let temp = tempfile::tempdir().expect("temp");
    let bin = temp.path().join("bin");
    make_executable(&bin, "cursor");
    let home = tempfile::tempdir().expect("home");
    let runner = FakeProcessRunner::new([
        Ok(keychain_miss()),
        Ok(keychain_miss()),
        Ok(keychain_miss()),
        Ok(keychain_miss()),
    ]);

    let result = run_check_on_platform(
        &runner,
        &config(true, false),
        temp.path(),
        home.path(),
        Some(bin.to_str().expect("utf8")),
        None,
        None,
        "Darwin",
    );

    assert!(result.cursor_binary_found());
    assert!(!result.cursor_present());
    assert!(!result.cursor_probe_timed_out());
    assert_eq!(runner.requests().len(), 4);
    assert!(runner.requests().iter().all(|request| {
        matches!(
            request.program(),
            &ExternalProgram::HostUtility(HostUtilityProgram::Security)
        )
    }));

    let stamp = temporary_root(temp.path())
        .path()
        .join(probe_stamp_file_name("cursor", "ada"));
    assert_eq!(fs::read_to_string(stamp).expect("stamp"), "false\n");
}

#[test]
fn cursor_probe_auth_failure_marks_absent() {
    let temp = tempfile::tempdir().expect("temp");
    let bin = temp.path().join("bin");
    make_executable(&bin, "cursor");
    let home = tempfile::tempdir().expect("home");
    let runner = FakeProcessRunner::new([Ok(ProcessOutputBuilder::failure(1)
        .stderr(b"authentication failed\n".to_vec())
        .build())]);

    let result = run_check(
        &runner,
        &config(true, false),
        temp.path(),
        home.path(),
        Some(bin.to_str().expect("utf8")),
        Some(SECRET),
    );

    assert!(result.cursor_binary_found());
    assert!(!result.cursor_present());
    assert!(!result.cursor_probe_timed_out());
    assert_eq!(runner.requests().len(), 1);
}

#[test]
fn cursor_model_list_spawn_error_is_non_timeout_failure() {
    let temp = tempfile::tempdir().expect("temp");
    let workdir = fs::canonicalize(temp.path()).expect("canonical");
    let root = temporary_root(temp.path());
    let home = tempfile::tempdir().expect("home");
    let runtime = LarchRuntime::current_thread().expect("runtime");
    let runner = FakeProcessRunner::new([Err(ProcessError::new(
        ProcessErrorKind::Spawn,
        "spawn failed",
        None,
    ))]);
    let outcome = runtime.block_on(run_cursor_model_list(
        &runner,
        model_list_context(&root, home.path(), &workdir),
        Duration::from_secs(1),
        &NeverCancelled,
    ));
    assert!(!outcome.timed_out);
    assert_eq!(outcome.returncode, 1);
    assert!(outcome.stdout.is_empty());
    assert!(outcome.stderr.is_empty());
}

#[test]
fn codex_home_links_operator_auth_when_env_key_omitted() {
    let temp = tempfile::tempdir().expect("temp");
    let home = temp.path().join("home");
    let codex_dir = home.join(".codex");
    fs::create_dir_all(&codex_dir).expect("codex dir");
    let auth = codex_dir.join("auth.json");
    fs::write(&auth, b"{\"tokens\":{}}").expect("auth");
    fs::write(
        codex_dir.join("config.toml"),
        "model = \"kept\"\napi_key = '''\nsecret-multiline\n'''\nother = 1\n",
    )
    .expect("config");

    let root = temporary_root(temp.path());
    let probe_home = SecureTempDir::create(&root, "larch-codex-probe-home-").expect("probe home");
    prepare_codex_home(probe_home.path(), &home, None).expect("prepare");

    let linked = probe_home.path().join("auth.json");
    assert!(linked.exists());
    let meta = fs::symlink_metadata(&linked).expect("symlink meta");
    assert!(meta.file_type().is_symlink());
    let stripped = fs::read_to_string(probe_home.path().join("config.toml")).expect("config");
    assert!(stripped.contains("model = \"kept\""));
    assert!(stripped.contains("other = 1"));
    assert!(!stripped.contains("secret-multiline"));
    assert!(!stripped.contains("api_key"));
}

#[test]
fn cursor_and_codex_probe_spawn_errors_mark_absent() {
    let temp = tempfile::tempdir().expect("temp");
    let bin = temp.path().join("bin");
    make_executable(&bin, "cursor");
    make_executable(&bin, "codex");
    let home = tempfile::tempdir().expect("home");
    let runner = FakeProcessRunner::new([
        Err(ProcessError::new(
            ProcessErrorKind::Spawn,
            "cursor spawn failed",
            None,
        )),
        Err(ProcessError::new(
            ProcessErrorKind::Spawn,
            "codex spawn failed",
            None,
        )),
    ]);

    let result = run_check(
        &runner,
        &config(false, false),
        temp.path(),
        home.path(),
        Some(bin.to_str().expect("utf8")),
        Some(SECRET),
    );

    assert!(result.cursor_binary_found());
    assert!(result.codex_binary_found());
    assert!(!result.cursor_present());
    assert!(!result.codex_present());
    assert!(!result.cursor_probe_timed_out());
    assert!(!result.codex_probe_timed_out());
    assert!(runner.requests().len() >= 2);
}
