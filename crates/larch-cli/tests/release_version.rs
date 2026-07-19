//! Black-box parity coverage for synchronized release-version mutation.

use std::{
    collections::BTreeMap,
    fs,
    path::{Path, PathBuf},
};

use assert_cmd::Command;
use predicates::prelude::*;
use tempfile::TempDir;

const ROOT_ENV: &str = "LARCH_RELEASE_SET_VERSION_REPO_ROOT";
const FAIL_AFTER_ENV: &str = "LARCH_TEST_RELEASE_SET_VERSION_FAIL_AFTER_WRITE";

#[test]
fn set_version_synchronizes_every_surface_and_preserves_formatting() {
    let repository = release_repository(true);

    larch(repository.path(), "1.2.4")
        .assert()
        .success()
        .stdout("PREVIOUS_VERSION=1.2.3\nNEW_VERSION=1.2.4\n")
        .stderr("");

    assert_eq!(
        plugin_version(repository.path(), ".claude-plugin/plugin.json"),
        "1.2.4"
    );
    assert_eq!(
        plugin_version(repository.path(), "plugin/.claude-plugin/plugin.json"),
        "1.2.4"
    );
    let manifest = read(repository.path(), "Cargo.toml");
    assert!(manifest.contains("version = \"1.2.4\""));
    assert!(manifest.contains("larch-core = { version = \"=1.2.4\""));
    assert!(manifest.contains("# formatting sentinel\n"));
    let lock = read(repository.path(), "Cargo.lock");
    assert_eq!(lock.matches("version = \"1.2.4\"").count(), 2);
    assert_eq!(
        read(repository.path(), ".claude-plugin/plugin.json"),
        "{\n  \"version\": \"1.2.4\",\n  \"description\": \"fixture \\u2014\",\n  \"author\": {\n    \"z\": \"last\",\n    \"a\": \"first\"\n  }\n}\n"
    );
}

#[test]
fn set_version_preserves_optional_projection_behavior() {
    let repository = release_repository(false);

    larch(repository.path(), "1.2.4")
        .assert()
        .success()
        .stdout("PREVIOUS_VERSION=1.2.3\nNEW_VERSION=1.2.4\n");

    assert!(
        !repository
            .path()
            .join("plugin/.claude-plugin/plugin.json")
            .exists()
    );
}

#[test]
fn set_version_treats_member_manifests_as_read_only_inputs() {
    let repository = release_repository(true);
    fs::hard_link(
        repository.path().join("crates/larch-core/Cargo.toml"),
        repository.path().join("member-manifest-backup.toml"),
    )
    .expect("hard-link member manifest fixture");

    larch(repository.path(), "1.2.4").assert().success();

    assert_eq!(
        read(repository.path(), "crates/larch-core/Cargo.toml"),
        read(repository.path(), "member-manifest-backup.toml")
    );
}

#[test]
fn set_version_rejects_invalid_regressive_and_noop_versions_without_writes() {
    for (version, error) in [
        ("1.2", "invalid semver"),
        ("1.2.2", "downgrade refused"),
        ("1.2.3", "no-op: version already 1.2.3"),
    ] {
        let repository = release_repository(true);
        let before = release_bytes(repository.path());

        larch(repository.path(), version)
            .assert()
            .failure()
            .stdout("")
            .stderr(predicate::str::contains(format!("ERROR={error}")));

        assert_eq!(release_bytes(repository.path()), before);
    }
}

#[test]
fn set_version_rejects_missing_and_malformed_files_without_writes() {
    let missing = release_repository(true);
    fs::remove_file(missing.path().join("Cargo.lock")).expect("remove lockfile");
    let before = release_bytes(missing.path());
    larch(missing.path(), "1.2.4")
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "required release version file is missing or unsafe: Cargo.lock",
        ));
    assert_eq!(release_bytes(missing.path()), before);

    let malformed_manifest = release_repository(true);
    fs::write(
        malformed_manifest.path().join("Cargo.toml"),
        "not = [toml\n",
    )
    .expect("malformed manifest");
    let before = release_bytes(malformed_manifest.path());
    larch(malformed_manifest.path(), "1.2.4")
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "Cargo.toml is not valid UTF-8 TOML",
        ));
    assert_eq!(release_bytes(malformed_manifest.path()), before);

    let malformed_lock = release_repository(true);
    fs::write(malformed_lock.path().join("Cargo.lock"), "not = [toml\n")
        .expect("malformed lockfile");
    let before = release_bytes(malformed_lock.path());
    larch(malformed_lock.path(), "1.2.4")
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "Cargo.lock is not valid UTF-8 TOML",
        ));
    assert_eq!(release_bytes(malformed_lock.path()), before);

    let malformed_plugin = release_repository(true);
    fs::write(
        malformed_plugin.path().join(".claude-plugin/plugin.json"),
        "not json\n",
    )
    .expect("malformed plugin manifest");
    let before = release_bytes(malformed_plugin.path());
    larch(malformed_plugin.path(), "1.2.4")
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            ".claude-plugin/plugin.json is not valid JSON",
        ));
    assert_eq!(release_bytes(malformed_plugin.path()), before);
}

#[test]
fn set_version_rejects_every_inconsistent_old_version() {
    let cargo = release_repository(true);
    replace(
        cargo.path(),
        "Cargo.toml",
        "version = \"1.2.3\"",
        "version = \"1.2.2\"",
    );
    assert_inconsistent(cargo.path(), "Cargo workspace version does not match");

    let dependency = release_repository(true);
    replace(
        dependency.path(),
        "Cargo.toml",
        "version = \"=1.2.3\"",
        "version = \"=1.2.2\"",
    );
    assert_inconsistent(
        dependency.path(),
        "workspace path dependency version mismatch",
    );

    let lock = release_repository(true);
    replace(
        lock.path(),
        "Cargo.lock",
        "version = \"1.2.3\"",
        "version = \"1.2.2\"",
    );
    assert_inconsistent(lock.path(), "Cargo.lock workspace package version mismatch");

    let projection = release_repository(true);
    replace(
        projection.path(),
        "plugin/.claude-plugin/plugin.json",
        "1.2.3",
        "1.2.2",
    );
    assert_inconsistent(
        projection.path(),
        "runtime projection plugin version source is out of sync",
    );
}

#[test]
fn set_version_rolls_back_an_interruption_at_every_write_boundary() {
    for boundary in 1..=4 {
        let repository = release_repository(true);
        let before = release_bytes(repository.path());

        larch(repository.path(), "1.2.4")
            .env(FAIL_AFTER_ENV, boundary.to_string())
            .assert()
            .failure()
            .stdout("")
            .stderr(predicate::str::contains(
                "ERROR=release version update failed: injected write interruption",
            ));

        assert_eq!(
            release_bytes(repository.path()),
            before,
            "boundary {boundary} must restore every original byte"
        );
        assert_no_atomic_temporary_files(repository.path());
    }
}

#[test]
fn set_version_replay_is_idempotent_after_success() {
    let repository = release_repository(true);
    larch(repository.path(), "1.2.4").assert().success();
    let after = release_bytes(repository.path());

    larch(repository.path(), "1.2.4")
        .assert()
        .failure()
        .stdout("")
        .stderr("ERROR=no-op: version already 1.2.4\n");

    assert_eq!(release_bytes(repository.path()), after);
}

fn assert_inconsistent(root: &Path, error: &str) {
    let before = release_bytes(root);
    larch(root, "1.2.4")
        .assert()
        .failure()
        .stderr(predicate::str::contains(error));
    assert_eq!(release_bytes(root), before);
}

fn larch(root: &Path, version: &str) -> Command {
    #[allow(deprecated)]
    let mut command = Command::cargo_bin("larch").expect("larch binary");
    command
        .current_dir(root)
        .env(ROOT_ENV, root)
        .env_remove(FAIL_AFTER_ENV)
        .args(["release", "set-version", version]);
    command
}

fn release_repository(projected: bool) -> TempDir {
    let repository = tempfile::tempdir().expect("release repository");
    for path in [
        ".claude-plugin",
        "crates/larch-cli",
        "crates/larch-core",
        "plugin/.claude-plugin",
    ] {
        fs::create_dir_all(repository.path().join(path)).expect("fixture directory");
    }
    let plugin = "{\"version\":\"1.2.3\",\"description\":\"fixture \\u2014\",\"author\":{\"z\":\"last\",\"a\":\"first\"}}\n";
    fs::write(repository.path().join(".claude-plugin/plugin.json"), plugin)
        .expect("plugin manifest");
    if projected {
        fs::write(
            repository.path().join("plugin/.claude-plugin/plugin.json"),
            plugin,
        )
        .expect("projected plugin manifest");
    }
    fs::write(
        repository.path().join("Cargo.toml"),
        r#"[workspace]
members = ["crates/larch-cli", "crates/larch-core"]

[workspace.package]
version = "1.2.3"
edition = "2024"

[workspace.dependencies]
larch-core = { version = "=1.2.3", path = "crates/larch-core" }
serde = "1"
# formatting sentinel
"#,
    )
    .expect("workspace manifest");
    for name in ["larch-cli", "larch-core"] {
        fs::write(
            repository.path().join(format!("crates/{name}/Cargo.toml")),
            format!(
                r#"[package]
name = "{name}"
version.workspace = true
"#
            ),
        )
        .expect("member manifest");
    }
    fs::write(
        repository.path().join("Cargo.lock"),
        r#"version = 4

[[package]]
name = "larch-cli"
version = "1.2.3"
dependencies = ["larch-core"]

[[package]]
name = "larch-core"
version = "1.2.3"
"#,
    )
    .expect("lockfile");
    repository
}

fn release_bytes(root: &Path) -> BTreeMap<PathBuf, Vec<u8>> {
    [
        ".claude-plugin/plugin.json",
        "Cargo.toml",
        "Cargo.lock",
        "plugin/.claude-plugin/plugin.json",
    ]
    .into_iter()
    .filter_map(|relative| {
        let path = root.join(relative);
        path.exists().then(|| {
            (
                PathBuf::from(relative),
                fs::read(path).expect("release bytes"),
            )
        })
    })
    .collect()
}

fn read(root: &Path, relative: &str) -> String {
    fs::read_to_string(root.join(relative)).expect("UTF-8 fixture")
}

fn plugin_version(root: &Path, relative: &str) -> String {
    serde_json::from_str::<serde_json::Value>(&read(root, relative))
        .expect("valid plugin JSON")
        .get("version")
        .and_then(serde_json::Value::as_str)
        .expect("plugin version")
        .to_owned()
}

fn replace(root: &Path, relative: &str, old: &str, new: &str) {
    let path = root.join(relative);
    let text = read(root, relative);
    fs::write(path, text.replacen(old, new, 1)).expect("replace fixture text");
}

fn assert_no_atomic_temporary_files(root: &Path) {
    let mut pending = vec![root.to_path_buf()];
    while let Some(directory) = pending.pop() {
        for entry in fs::read_dir(directory).expect("read fixture directory") {
            let entry = entry.expect("fixture entry");
            let kind = entry.file_type().expect("fixture file type");
            if kind.is_dir() {
                pending.push(entry.path());
            } else {
                let name = entry.file_name();
                let name = name.to_string_lossy();
                assert!(
                    !(name.starts_with(".Cargo") || name.starts_with(".plugin.json")),
                    "atomic temporary file survived: {}",
                    entry.path().display()
                );
            }
        }
    }
}
