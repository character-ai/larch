//! Integration coverage for the vendor credential preflight and probe cache.

use larch_adapters::{
    TemporaryRoot,
    runtime::LarchRuntime,
    vendor_auth::{
        CursorPreflightConfig, CursorProbeSession, CursorTokenPreread, ProbeCache,
        VendorAuthContext, cursor_auth_preflight, cursor_preread_service_token,
    },
    vendor_lifecycle::StartupLockConfig,
};
use larch_core::{
    CURSOR_PREFLIGHT_AUTH_RC, ChildEnvironment, CodexGateDetail, ProbeTtl, ProcessOutput,
    VendorProgram, codex_probe_identity, cursor_preflight_failure_message, detect_codex_cli_gate,
    env,
};
use larch_test_support::{FakeProcessRunner, NeverCancelled, ProcessOutputBuilder};
use std::{
    fs,
    path::Path,
    sync::{
        Arc, Barrier,
        atomic::{AtomicUsize, Ordering},
    },
    thread,
    time::{Duration, SystemTime},
};

const SECRET: &str = "cursor-secret-token-value";

fn temporary_root(path: &Path) -> TemporaryRoot {
    TemporaryRoot::resolve(Some(path)).expect("temporary root")
}

fn lock_config(platform: &str) -> StartupLockConfig {
    StartupLockConfig::from_values(
        VendorProgram::Cursor,
        platform,
        Some("ada"),
        None,
        None,
        Some("0"),
    )
    .expect("startup lock config")
}

fn keychain_hit() -> ProcessOutput {
    ProcessOutputBuilder::success()
        .stdout(format!("{SECRET}\n").into_bytes())
        .build()
}

fn keychain_miss() -> ProcessOutput {
    ProcessOutputBuilder::failure(1)
        .stderr(b"The specified item could not be found in the keychain.\n".to_vec())
        .build()
}

fn preflight(
    responses: Vec<ProcessOutput>,
    platform: &str,
    api_key: Option<&str>,
) -> (larch_core::ReviewAuthVerdict, usize) {
    let temp = tempfile::tempdir().expect("temp");
    let root = temporary_root(temp.path());
    let lock = lock_config(platform);
    let runner = FakeProcessRunner::new(responses.into_iter().map(Ok));
    let runtime = LarchRuntime::current_thread().expect("runtime");
    let config =
        CursorPreflightConfig::from_values(platform, api_key, "agent cursor-auth-preflight")
            .with_retry_delay(Duration::ZERO);

    let verdict = runtime.block_on(cursor_auth_preflight(
        &runner,
        &config,
        VendorAuthContext {
            temporary_root: &root,
            startup_lock: &lock,
            working_directory: temp.path(),
        },
        &NeverCancelled,
    ));
    (verdict, runner.requests().len())
}

#[test]
fn a_usable_environment_key_clears_the_preflight_without_a_keychain_read() {
    let (verdict, spawns) = preflight(Vec::new(), "Darwin", Some(SECRET));

    assert!(verdict.ok);
    assert_eq!(verdict.rc, 0);
    assert_eq!(spawns, 0);
}

#[test]
fn a_line_spliced_environment_key_falls_through_to_the_keychain() {
    let (verdict, spawns) = preflight(
        vec![keychain_hit()],
        "Darwin",
        Some("token\nCURSOR_API_KEY=stolen"),
    );

    assert!(verdict.ok);
    assert_eq!(spawns, 1);
}

#[test]
fn a_non_darwin_host_has_no_keychain_to_consult() {
    let (verdict, spawns) = preflight(Vec::new(), "Linux", None);

    assert!(verdict.ok);
    assert_eq!(spawns, 0);
}

#[test]
fn a_readable_keychain_entry_clears_the_preflight() {
    let (verdict, spawns) = preflight(vec![keychain_hit()], "Darwin", None);

    assert!(verdict.ok);
    assert_eq!(spawns, 1);
}

#[test]
fn a_late_keychain_read_still_clears_within_the_attempt_budget() {
    let (verdict, spawns) = preflight(
        vec![keychain_miss(), keychain_miss(), keychain_hit()],
        "Darwin",
        None,
    );

    assert!(verdict.ok);
    assert_eq!(spawns, 3);
}

#[test]
fn an_unreadable_keychain_entry_fails_closed_with_operator_guidance() {
    let (verdict, spawns) = preflight(
        vec![keychain_miss(), keychain_miss(), keychain_miss()],
        "Darwin",
        None,
    );

    assert!(!verdict.ok);
    assert_eq!(verdict.rc, CURSOR_PREFLIGHT_AUTH_RC);
    assert_eq!(
        verdict.message,
        cursor_preflight_failure_message("agent cursor-auth-preflight")
    );
    assert_eq!(spawns, 3);
}

#[test]
fn an_exit_zero_read_that_returns_no_token_still_fails_closed() {
    let empty = || {
        ProcessOutputBuilder::success()
            .stdout(b"\n".to_vec())
            .build()
    };
    let (verdict, spawns) = preflight(vec![empty(), empty(), empty()], "Darwin", None);

    assert!(!verdict.ok);
    assert_eq!(spawns, 3);
}

#[test]
fn the_verdict_never_carries_the_credential_it_read() {
    let (verdict, _spawns) = preflight(vec![keychain_hit()], "Darwin", None);

    assert!(!format!("{verdict:?}").contains(SECRET));
    assert!(!verdict.message.contains(SECRET));
}

#[test]
fn a_denied_keychain_read_reports_the_unreadable_preread_outcome() {
    let temp = tempfile::tempdir().expect("temp");
    let root = temporary_root(temp.path());
    let lock = lock_config("Darwin");
    let runner = FakeProcessRunner::new([Ok(keychain_miss())]);
    let runtime = LarchRuntime::current_thread().expect("runtime");
    let config = CursorPreflightConfig::from_values("Darwin", None, "agent check-reviewers")
        .with_retry_delay(Duration::ZERO);

    let preread = runtime.block_on(cursor_preread_service_token(
        &runner,
        &config,
        VendorAuthContext {
            temporary_root: &root,
            startup_lock: &lock,
            working_directory: temp.path(),
        },
        &NeverCancelled,
    ));

    assert_eq!(preread, CursorTokenPreread::Unreadable);
}

#[test]
fn a_successful_preread_carries_the_credential_only_as_a_child_override() {
    let temp = tempfile::tempdir().expect("temp");
    let root = temporary_root(temp.path());
    let lock = lock_config("Darwin");
    let runner = FakeProcessRunner::new([Ok(keychain_hit())]);
    let runtime = LarchRuntime::current_thread().expect("runtime");
    let config = CursorPreflightConfig::from_values("Darwin", None, "agent check-reviewers")
        .with_retry_delay(Duration::ZERO);

    let preread = runtime.block_on(cursor_preread_service_token(
        &runner,
        &config,
        VendorAuthContext {
            temporary_root: &root,
            startup_lock: &lock,
            working_directory: temp.path(),
        },
        &NeverCancelled,
    ));

    let CursorTokenPreread::Proceed(credential) = preread else {
        panic!("expected a usable credential");
    };
    let credential = credential.expect("credential");
    assert_eq!(credential.expose(), SECRET);
    assert!(!format!("{credential:?}").contains(SECRET));
    assert!(std::env::var_os(env::CURSOR_API_KEY).is_none_or(|value| value != SECRET));
}

fn age_file(path: &Path, age: Duration) {
    let file = fs::File::options().write(true).open(path).expect("open");
    let modified = SystemTime::now()
        .checked_sub(age)
        .expect("representable time");
    file.set_times(fs::FileTimes::new().set_modified(modified))
        .expect("set mtime");
}

fn cache(root: &Path, positive: u64, negative: u64) -> ProbeCache {
    ProbeCache::new(
        temporary_root(root),
        Some("ada"),
        ProbeTtl::from_seconds(positive, negative),
    )
}

fn stamp_path(root: &Path, kind: &str) -> std::path::PathBuf {
    fs::canonicalize(root)
        .expect("canonical root")
        .join(larch_core::probe_stamp_file_name(kind, "ada"))
}

#[test]
fn a_positive_verdict_expires_after_its_ttl() {
    let temp = tempfile::tempdir().expect("temp");
    let cache = cache(temp.path(), 60, 30);

    cache.write_verdict("codex", true).expect("write");
    assert_eq!(cache.read_verdict("codex"), Some(true));

    age_file(&stamp_path(temp.path(), "codex"), Duration::from_secs(120));
    assert_eq!(cache.read_verdict("codex"), None);
}

#[test]
fn a_negative_verdict_expires_on_its_own_shorter_ttl() {
    let temp = tempfile::tempdir().expect("temp");
    let cache = cache(temp.path(), 600, 30);

    cache.write_verdict("codex", false).expect("write");
    assert_eq!(cache.read_verdict("codex"), Some(false));

    age_file(&stamp_path(temp.path(), "codex"), Duration::from_secs(60));
    assert_eq!(cache.read_verdict("codex"), None);
}

#[test]
fn a_disabled_positive_ttl_never_reuses_any_verdict() {
    let temp = tempfile::tempdir().expect("temp");
    let cache = cache(temp.path(), 0, 0);

    cache.write_verdict("codex", true).expect("write");
    assert_eq!(cache.read_verdict("codex"), None);
}

#[test]
fn a_preflight_config_never_renders_the_key_it_was_handed() {
    let config =
        CursorPreflightConfig::from_values("Darwin", Some(SECRET), "agent cursor-auth-preflight");

    assert!(!format!("{config:?}").contains(SECRET));
}

#[test]
fn a_negative_verdict_is_never_reused_when_negative_caching_is_off() {
    let temp = tempfile::tempdir().expect("temp");
    let cache = cache(temp.path(), 600, 0);

    cache.write_verdict("codex", true).expect("write");
    assert_eq!(cache.read_verdict("codex"), Some(true));

    cache.write_verdict("codex", false).expect("write");
    assert_eq!(cache.read_verdict("codex"), None);
}

fn gate_detail() -> CodexGateDetail {
    detect_codex_cli_gate("requires a newer version of Codex", "gpt-5.6-sol").expect("gate detail")
}

#[test]
fn a_gate_detail_round_trips_expires_and_clears() {
    let temp = tempfile::tempdir().expect("temp");
    let cache = cache(temp.path(), 60, 30);
    let identity = codex_probe_identity(larch_core::CodexEnvAuth::Omit, "gpt-5.6-sol");
    let detail = gate_detail();

    cache.write_gate_detail(&identity, &detail).expect("write");
    assert_eq!(
        cache.read_gate_detail(&identity, Duration::from_secs(30)),
        Some(detail)
    );
    assert_eq!(cache.read_gate_detail(&identity, Duration::ZERO), None);
    assert_eq!(
        cache.read_gate_detail("codex-login-other", Duration::from_secs(30)),
        None
    );

    cache.clear_gate_detail(&identity).expect("clear");
    assert_eq!(
        cache.read_gate_detail(&identity, Duration::from_secs(30)),
        None
    );
    cache.clear_gate_detail(&identity).expect("clear again");
}

#[test]
fn a_gate_detail_older_than_its_probe_stamp_is_discarded() {
    let temp = tempfile::tempdir().expect("temp");
    let cache = cache(temp.path(), 600, 600);
    let identity = codex_probe_identity(larch_core::CodexEnvAuth::Omit, "gpt-5.6-sol");

    cache
        .write_gate_detail(&identity, &gate_detail())
        .expect("write detail");
    cache.write_verdict(&identity, true).expect("write stamp");
    age_file(
        &fs::canonicalize(temp.path())
            .expect("canonical root")
            .join(larch_core::codex_gate_detail_file_name(&identity, "ada")),
        Duration::from_secs(30),
    );

    assert_eq!(
        cache.read_gate_detail(&identity, Duration::from_secs(600)),
        None
    );
}

#[test]
fn concurrent_probes_serialize_and_publish_one_consistent_gate_detail() {
    let temp = tempfile::tempdir().expect("temp");
    let root = temp.path().to_path_buf();
    let identity = codex_probe_identity(larch_core::CodexEnvAuth::Omit, "gpt-5.6-sol");
    let probes_run = Arc::new(AtomicUsize::new(0));
    let barrier = Arc::new(Barrier::new(8));
    let mut handles = Vec::new();

    for _worker in 0..8 {
        let root = root.clone();
        let identity = identity.clone();
        let probes_run = Arc::clone(&probes_run);
        let barrier = Arc::clone(&barrier);
        handles.push(thread::spawn(move || {
            let cache = cache(&root, 600, 600);
            barrier.wait();
            let _lock = cache.update_lock(&identity).expect("update lock");
            if cache.read_verdict(&identity).is_none() {
                probes_run.fetch_add(1, Ordering::SeqCst);
                cache.write_verdict(&identity, false).expect("write stamp");
                cache
                    .write_gate_detail(&identity, &gate_detail())
                    .expect("write detail");
            }
            cache.read_gate_detail(&identity, Duration::from_secs(600))
        }));
    }

    let observed: Vec<Option<CodexGateDetail>> = handles
        .into_iter()
        .map(|handle| handle.join().expect("worker"))
        .collect();

    assert_eq!(probes_run.load(Ordering::SeqCst), 1);
    assert!(
        observed
            .iter()
            .all(|detail| detail.as_ref() == Some(&gate_detail())),
        "every serialized probe observed the same gate detail"
    );
}

#[test]
fn a_probe_session_exposes_isolation_and_the_credential_as_child_overrides() {
    let temp = tempfile::tempdir().expect("temp");
    let home = tempfile::tempdir().expect("home");
    let credential = larch_core::CursorCredential::parse(SECRET).expect("credential");

    let session =
        CursorProbeSession::open(&temporary_root(temp.path()), home.path(), Some(credential))
            .expect("session");
    let overrides = session.child_environment();

    assert!(session.config_directory().is_dir());
    assert_eq!(overrides[0].0, ChildEnvironment::NoOpenBrowser);
    assert_eq!(overrides[1].0, ChildEnvironment::CursorApiKey);
    assert_eq!(overrides[1].1, SECRET);
    assert_eq!(overrides[2].0, ChildEnvironment::CursorConfigDir);
    assert_eq!(overrides[2].1, session.config_directory().as_os_str());
    assert!(
        std::env::var_os(env::CURSOR_CONFIG_DIR)
            .is_none_or(|value| { value != session.config_directory().as_os_str() })
    );
}

/// Every probe exit path releases the private configuration directory.
#[test]
fn the_private_configuration_directory_is_removed_on_every_exit_path() {
    #[derive(Clone, Copy)]
    enum Exit {
        Success,
        Failure,
        Timeout,
        Cancellation,
    }

    for exit in [
        Exit::Success,
        Exit::Failure,
        Exit::Timeout,
        Exit::Cancellation,
    ] {
        let temp = tempfile::tempdir().expect("temp");
        let home = tempfile::tempdir().expect("home");
        let session = CursorProbeSession::open(&temporary_root(temp.path()), home.path(), None)
            .expect("session");
        let directory = session.config_directory().to_path_buf();
        assert!(directory.is_dir());

        match exit {
            Exit::Success => session.close().expect("explicit cleanup"),
            Exit::Failure => drop(session),
            Exit::Timeout => {
                let outcome: Result<(), &str> = Err("probe timed out");
                drop(session);
                assert!(outcome.is_err());
            }
            Exit::Cancellation => {
                let worker = thread::spawn(move || {
                    let _held = session;
                    panic!("cancelled mid-probe");
                });
                assert!(worker.join().is_err());
            }
        }

        assert!(
            !directory.exists(),
            "probe configuration directory survived an exit path"
        );
    }
}

#[test]
fn a_credential_shaped_probe_value_never_reaches_a_cache_artifact() {
    let temp = tempfile::tempdir().expect("temp");
    let cache = cache(temp.path(), 600, 600);
    let identity = codex_probe_identity(larch_core::CodexEnvAuth::Omit, "gpt-5.6-sol");

    cache.write_verdict(&identity, false).expect("stamp");
    cache
        .write_gate_detail(&identity, &gate_detail())
        .expect("detail");

    let canonical = fs::canonicalize(temp.path()).expect("canonical root");
    let mut inspected = 0_usize;
    for entry in fs::read_dir(&canonical).expect("read cache dir") {
        let path = entry.expect("entry").path();
        let contents = fs::read_to_string(&path).unwrap_or_default();
        assert!(
            !contents.contains(SECRET),
            "cache artifact {} leaked a credential",
            path.display()
        );
        inspected += 1;
    }
    assert!(inspected >= 2, "expected the stamp and the gate detail");
}
