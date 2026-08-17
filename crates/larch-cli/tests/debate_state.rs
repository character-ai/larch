//! Round-trip parity, migration, lock, and stale-fingerprint coverage for the
//! effectful debate state store, driven by recorded Python state fixtures.

use std::fs;
use std::path::Path;

use larch_cli::debate_state::{load_state, write_state};
use larch_core::debate::state::{STATE_FILENAME, StateErrorClass, require_fingerprint};
use serde_json::Value;
use tempfile::TempDir;

const STATE_V2: &str = include_str!("fixtures/debate_state/state-v2.json");
const STATE_V2_ACTIVE: &str = include_str!("fixtures/debate_state/state-v2-active.json");
const STATE_V1: &str = include_str!("fixtures/debate_state/state-v1.json");

fn seed_root(fixture: &str) -> TempDir {
    let dir = TempDir::new().expect("temp dir");
    fs::write(dir.path().join(STATE_FILENAME), fixture).expect("seed state");
    dir
}

fn fixture_fingerprint(fixture: &str) -> String {
    let value: Value = serde_json::from_str(fixture).expect("fixture json");
    value["fingerprint"]
        .as_str()
        .expect("fingerprint")
        .to_owned()
}

fn state_bytes(root: &Path) -> String {
    fs::read_to_string(root.join(STATE_FILENAME)).expect("read state")
}

fn assert_byte_identical_round_trip(fixture: &str) {
    let dir = seed_root(fixture);
    let root = dir.path();
    let loaded = load_state(root).expect("load");
    assert_eq!(loaded.fingerprint, fixture_fingerprint(fixture));

    let written = write_state(root, &loaded).expect("write");
    assert_eq!(written.fingerprint, loaded.fingerprint);
    assert_eq!(state_bytes(root), fixture);
}

#[test]
fn v2_state_round_trips_byte_for_byte() {
    assert_byte_identical_round_trip(STATE_V2);
}

#[test]
fn v2_active_state_round_trips_byte_for_byte() {
    assert_byte_identical_round_trip(STATE_V2_ACTIVE);
}

#[test]
fn v1_state_migrates_to_schema_two() {
    let dir = seed_root(STATE_V1);
    let root = dir.path();
    let loaded = load_state(root).expect("load v1");

    let _written = write_state(root, &loaded).expect("write");
    let migrated = state_bytes(root);
    assert_ne!(migrated, STATE_V1);
    assert!(migrated.contains("\"schema_version\":2"));

    let reloaded = load_state(root).expect("reload");
    assert_eq!(reloaded.proposal, loaded.proposal);
    assert_eq!(reloaded.initialization, loaded.initialization);
}

#[test]
fn write_state_creates_the_debate_root() {
    let source = seed_root(STATE_V2);
    let loaded = load_state(source.path()).expect("load");

    let dir = TempDir::new().expect("temp dir");
    let root = dir.path().join("nested/debate");
    assert!(!root.exists());

    let _written = write_state(&root, &loaded).expect("write into fresh root");
    assert!(root.join(STATE_FILENAME).is_file());
    let reloaded = load_state(&root).expect("reload");
    assert_eq!(reloaded, load_state(source.path()).expect("source reload"));
}

#[test]
fn load_state_require_fingerprint_flags_a_stale_expectation() {
    let dir = seed_root(STATE_V2);
    let loaded = load_state(dir.path()).expect("load");
    assert!(require_fingerprint(&loaded, &loaded.fingerprint).is_ok());

    let error = require_fingerprint(&loaded, "ABSENT").expect_err("stale");
    assert_eq!(error.class(), StateErrorClass::StaleFingerprint);
    assert_eq!(error.exit_code(), 3);
}

#[cfg(unix)]
mod lock {
    use super::{STATE_V2, seed_root};
    use larch_cli::debate_state::lock_state;
    use larch_core::debate::state::{STATE_LOCK_FILENAME, StateErrorClass};
    use nix::sys::stat::Mode;
    use nix::unistd::mkfifo;
    use std::fs;
    use std::os::unix::fs::symlink;

    #[test]
    fn lock_refuses_a_non_regular_lock_path() {
        let dir = seed_root(STATE_V2);
        let lock = dir.path().join(STATE_LOCK_FILENAME);
        mkfifo(&lock, Mode::S_IRUSR | Mode::S_IWUSR).expect("mkfifo");

        let error = lock_state(dir.path()).expect_err("non-regular lock");
        assert_eq!(error.class(), StateErrorClass::PersistenceFailure);
        assert_eq!(error.exit_code(), 5);
    }

    #[test]
    fn lock_refuses_a_symlinked_lock_path() {
        let dir = seed_root(STATE_V2);
        let target = dir.path().join("elsewhere.lock");
        fs::write(&target, "").expect("target");
        let lock = dir.path().join(STATE_LOCK_FILENAME);
        symlink(&target, &lock).expect("symlink");

        let error = lock_state(dir.path()).expect_err("symlinked lock");
        assert_eq!(error.class(), StateErrorClass::PersistenceFailure);
        assert_eq!(error.exit_code(), 5);
        assert!(
            fs::symlink_metadata(&lock)
                .expect("lstat")
                .file_type()
                .is_symlink()
        );
    }
}
