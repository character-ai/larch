//! Executable-boundary coverage for fixed-endpoint connectivity waits.

use std::time::{Duration, Instant};

use assert_cmd::Command;
use larch_core::MAX_NET_WAIT_CEILING;
use predicates::prelude::*;

#[test]
fn forced_offline_probe_waits_to_the_ceiling_without_extra_attempts() {
    let started = Instant::now();
    let output = Command::cargo_bin("larch")
        .expect("larch binary should build")
        .env("LARCH_TEST_NET_FORCE_OFFLINE", "true")
        .env("ANTHROPIC_API_KEY", "must-not-be-printed")
        .env("GH_TOKEN", "must-not-be-printed")
        .args(["net", "wait-online", "--ceiling-s", "1"])
        .output()
        .expect("connectivity helper should run");

    assert!(!output.status.success());
    assert_eq!(
        String::from_utf8(output.stdout).expect("UTF-8 stdout"),
        "NET_ONLINE=false\nNET_PROBE_ATTEMPT_COUNT=1\nNET_WAIT_SECONDS=1\n"
    );
    assert!(output.stderr.is_empty());
    assert!(started.elapsed() >= Duration::from_millis(900));
}

#[test]
fn excessive_ceiling_fails_before_waiting_or_probing() {
    let excessive = MAX_NET_WAIT_CEILING.as_secs().saturating_add(1).to_string();
    Command::cargo_bin("larch")
        .expect("larch binary should build")
        .env("LARCH_TEST_NET_FORCE_OFFLINE", "true")
        .args(["net", "wait-online", "--ceiling-s", &excessive])
        .assert()
        .failure()
        .stdout("")
        .stderr(predicate::str::contains(format!(
            "connectivity wait ceiling must not exceed {} seconds",
            MAX_NET_WAIT_CEILING.as_secs()
        )));
}
