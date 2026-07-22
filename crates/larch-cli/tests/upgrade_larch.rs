#![cfg(unix)]

use assert_cmd::Command;
use predicates::prelude::*;
use std::{
    fs,
    os::unix::fs::PermissionsExt,
    path::{Path, PathBuf},
};
use tempfile::TempDir;

const SOURCE: &str =
    "https://raw.githubusercontent.com/character-ai/larch/main/.claude-plugin/marketplace.json";

struct Harness {
    _temp: TempDir,
    home: PathBuf,
    data: PathBuf,
    fake_bin: PathBuf,
    old_root: PathBuf,
    new_root: PathBuf,
    state: PathBuf,
    log: PathBuf,
}

impl Harness {
    fn new() -> Self {
        let temp = tempfile::tempdir().expect("tempdir");
        let home = temp.path().join("home");
        let data = temp.path().join("data");
        let fake_bin = temp.path().join("fake-bin");
        let state = temp.path().join("state");
        let log = temp.path().join("calls.log");
        fs::create_dir_all(&fake_bin).expect("fake bin");
        fs::create_dir_all(&data).expect("plugin data");
        fs::create_dir_all(&state).expect("state");
        fs::write(state.join("installed"), "1.0.0").expect("installed state");
        fs::write(state.join("desired"), "2.0.0").expect("desired state");
        fs::write(state.join("marketplace"), "remote").expect("marketplace state");
        let cache = home.join(".claude/plugins/cache/larch-local/larch");
        let old_root = cache.join("1.0.0");
        let new_root = cache.join("2.0.0");
        install_root(&old_root, "1.0.0", &state, &log);
        install_root(&new_root, "2.0.0", &state, &log);
        write_executable(
            &fake_bin.join("claude"),
            &claude_script(&state, &log, &old_root, &new_root),
        );
        Self {
            _temp: temp,
            home,
            data,
            fake_bin,
            old_root,
            new_root,
            state,
            log,
        }
    }

    fn command(&self) -> Command {
        let coverage_profile = std::env::var_os("LLVM_PROFILE_FILE");
        let mut command = Command::cargo_bin("larch").expect("larch binary");
        command
            .env_clear()
            .env("HOME", &self.home)
            .env("PATH", format!("{}:/bin", self.fake_bin.display()))
            .env("CLAUDE_PLUGIN_DATA", &self.data)
            .env("CLAUDE_PLUGIN_ROOT", &self.old_root)
            .env("LARCH_EXPECTED_STABLE_VERSION", "2.0.0");
        if let Some(profile) = coverage_profile {
            command.env("LLVM_PROFILE_FILE", profile);
        }
        command
    }

    fn set(&self, name: &str, value: &str) {
        fs::write(self.state.join(name), value).expect("state write");
    }

    fn flag(&self, name: &str) {
        fs::write(self.state.join(name), "1").expect("flag");
    }

    fn clear(&self, name: &str) {
        let _ = fs::remove_file(self.state.join(name));
    }
}

#[test]
fn auxiliary_commands_preserve_their_machine_output() {
    let harness = Harness::new();
    harness
        .command()
        .arg("upgrade-larch")
        .arg("sparse-dirs")
        .assert()
        .success()
        .stdout(".claude-plugin\n");
    harness
        .command()
        .arg("upgrade-larch")
        .arg("release-step7-root")
        .assert()
        .success()
        .stdout(format!("RESOLVED_ROOT={}\n", harness.old_root.display()));

    harness
        .command()
        .args([
            "upgrade-larch",
            "release-step7-root",
            "1.2.3",
            "--current-version",
            "1.2.3",
        ])
        .assert()
        .failure()
        .stderr(predicates::str::contains("an argument cannot be used with"));
}

#[test]
fn no_op_repairs_and_verifies_the_binary_without_python() {
    let harness = Harness::new();
    harness.set("installed", "2.0.0");
    fs::remove_file(harness.new_root.join("bin/larch")).expect("remove broken binary");
    harness
        .command()
        .env("CLAUDE_PLUGIN_ROOT", &harness.new_root)
        .arg("upgrade-larch")
        .arg("run")
        .assert()
        .success()
        .stderr(predicate::str::contains(
            "Binary verification passed. No upgrade needed.",
        ));
    assert!(harness.new_root.join("bin/larch").is_file());
    assert!(
        !fs::read_to_string(&harness.log)
            .expect("log")
            .contains("python")
    );
}

#[test]
fn ordinary_upgrade_preflights_then_preserves_the_active_old_root() {
    let harness = Harness::new();
    let marker = harness.old_root.join("active-session");
    fs::write(&marker, "old").expect("marker");
    harness
        .command()
        .env("GH_TOKEN", "must-not-be-forwarded")
        .env("GITHUB_TOKEN", "must-not-be-forwarded")
        .env("GH_CONFIG_DIR", harness.home.join(".config/gh"))
        .arg("upgrade-larch")
        .arg("run")
        .assert()
        .success()
        .stderr(
            predicate::str::contains("LARCH_RESTART_REQUIRED=true")
                .and(predicate::str::contains("LARCH_NEW_VERSION_INSTALLED=true")),
        );
    assert_eq!(fs::read_to_string(marker).expect("old marker"), "old");
    let log = fs::read_to_string(&harness.log).expect("log");
    let preflight = log
        .find("bootstrap --preflight-release 2.0.0")
        .expect("preflight");
    let refresh = log
        .find("claude plugin marketplace update larch-local")
        .expect("refresh");
    assert!(preflight < refresh);
    assert!(!log.contains("bootstrap-gh-token-present"));
    assert!(log.contains("bootstrap-gh-config-present"));
}

#[test]
fn release_step7_can_keep_execution_and_installed_roots_separate() {
    let harness = Harness::new();
    harness
        .command()
        .env("CLAUDE_PLUGIN_ROOT", &harness.new_root)
        .args(["upgrade-larch", "run", "--plugin-root"])
        .arg(&harness.old_root)
        .assert()
        .success()
        .stderr(predicate::str::contains("LARCH_NEW_VERSION_INSTALLED=true"));
}

#[test]
fn preflight_uses_the_driver_root_when_the_install_target_predates_the_flag() {
    let harness = Harness::new();
    // Simulate upgrading from a version whose larch.sh predates
    // `--preflight-release` (e.g. 53.x), which errors on the flag. The preflight
    // must still succeed by running the driver's (CLAUDE_PLUGIN_ROOT) larch.sh,
    // not the install target's.
    write_executable(
        &harness.old_root.join("scripts/larch.sh"),
        "#!/bin/sh\ncase \"$1\" in\n--preflight-release) echo 'unexpected argument' >&2; exit 1 ;;\nesac\n",
    );
    harness
        .command()
        .env("CLAUDE_PLUGIN_ROOT", &harness.new_root)
        .env("LARCH_EXPECTED_STABLE_VERSION", "2.0.0")
        .args(["upgrade-larch", "run", "--plugin-root"])
        .arg(&harness.old_root)
        .assert()
        .success()
        .stderr(predicate::str::contains("LARCH_NEW_VERSION_INSTALLED=true"));
}

#[test]
fn active_old_session_is_refreshed_without_deleting_its_cache_root() {
    let harness = Harness::new();
    harness.set("installed", "2.0.0");
    harness
        .command()
        .arg("upgrade-larch")
        .arg("run")
        .assert()
        .success()
        .stderr(
            predicate::str::contains("still running cached larch 1.0.0")
                .and(predicate::str::contains("LARCH_RESTART_REQUIRED=true")),
        );
    assert!(harness.old_root.join("bin/larch").is_file());
    assert!(harness.new_root.join("bin/larch").is_file());
}

#[test]
fn marketplace_migration_removes_only_the_legacy_clone_and_reinstalls() {
    let harness = Harness::new();
    harness.set("marketplace", "legacy");
    let clone = harness
        .home
        .join(".claude/plugins/marketplaces/larch-local");
    fs::create_dir_all(&clone).expect("clone");
    fs::write(clone.join("legacy"), "legacy").expect("legacy marker");
    harness
        .command()
        .arg("upgrade-larch")
        .arg("run")
        .assert()
        .success()
        .stderr(predicate::str::contains(
            "LARCH_MARKETPLACE_RECONCILED=true",
        ));
    assert!(!clone.exists());
    assert!(harness.old_root.is_dir());
    let log = fs::read_to_string(&harness.log).expect("log");
    assert!(log.contains(&format!("claude plugin marketplace add {SOURCE}")));
    assert!(log.contains("claude plugin install larch@larch-local"));
}

#[test]
fn ambiguous_installed_roots_fail_closed_with_retry_guidance() {
    let harness = Harness::new();
    harness.set("installed", "2.0.0");
    harness.flag("ambiguous");
    harness
        .command()
        .env("CLAUDE_PLUGIN_ROOT", &harness.new_root)
        .arg("upgrade-larch")
        .arg("run")
        .assert()
        .failure()
        .stderr(predicate::str::contains("Recovery: retry /upgrade-larch"));
}

#[test]
fn interrupted_preflight_is_retryable_and_does_not_mutate_plugin_state() {
    let harness = Harness::new();
    harness.flag("fail_preflight");
    harness
        .command()
        .arg("upgrade-larch")
        .arg("run")
        .assert()
        .failure()
        .stderr(predicate::str::contains("stable release preflight failed"));
    assert_eq!(
        fs::read_to_string(harness.state.join("installed")).expect("state"),
        "1.0.0"
    );
    harness.clear("fail_preflight");
    harness
        .command()
        .arg("upgrade-larch")
        .arg("run")
        .assert()
        .success();
}

#[test]
fn missing_plugin_data_fails_closed_before_any_mutation_with_the_remedy() {
    let harness = Harness::new();
    harness
        .command()
        .env_remove("CLAUDE_PLUGIN_DATA")
        .arg("upgrade-larch")
        .arg("run")
        .assert()
        .failure()
        .stderr(
            predicate::str::contains("CLAUDE_PLUGIN_DATA is required")
                .and(predicate::str::contains("docs/installation-and-setup.md")),
        );
    let log = fs::read_to_string(&harness.log).expect("log");
    assert!(!log.contains("bootstrap --preflight-release"));
    assert_eq!(
        fs::read_to_string(harness.state.join("installed")).expect("installed state"),
        "1.0.0"
    );
    assert_eq!(
        fs::read_to_string(harness.state.join("marketplace")).expect("marketplace state"),
        "remote"
    );
}

#[test]
fn failed_refresh_and_failed_install_leave_the_prior_root_usable() {
    let harness = Harness::new();
    harness.flag("fail_refresh");
    harness
        .command()
        .arg("upgrade-larch")
        .arg("run")
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "prior plugin cache root was not changed",
        ));
    assert!(harness.old_root.join("bin/larch").is_file());
    harness.clear("fail_refresh");
    harness.flag("fail_install");
    harness
        .command()
        .arg("upgrade-larch")
        .arg("run")
        .assert()
        .code(7)
        .stderr(predicate::str::contains("Plugin install failed"));
    assert!(harness.old_root.join("bin/larch").is_file());
}

#[test]
fn failed_new_root_bootstrap_preserves_rollback_and_retry_state() {
    let harness = Harness::new();
    harness.flag("fail_bootstrap_2.0.0");
    let marker = harness.old_root.join("rollback-marker");
    fs::write(&marker, "old").expect("marker");
    harness
        .command()
        .arg("upgrade-larch")
        .arg("run")
        .assert()
        .failure()
        .stderr(predicate::str::contains("Upgrade incomplete"));
    assert_eq!(fs::read_to_string(marker).expect("marker"), "old");
    assert!(harness.new_root.is_dir());
}

fn install_root(root: &Path, version: &str, state: &Path, log: &Path) {
    fs::create_dir_all(root.join(".claude-plugin")).expect("manifest dir");
    fs::create_dir_all(root.join("scripts")).expect("scripts dir");
    fs::create_dir_all(root.join("bin")).expect("bin dir");
    fs::write(
        root.join(".claude-plugin/plugin.json"),
        format!(r#"{{"version":"{version}"}}"#),
    )
    .expect("manifest");
    let binary = identity_script(version, log);
    write_executable(&root.join("bin-template"), &binary);
    write_executable(&root.join("bin/larch"), &binary);
    write_executable(
        &root.join("scripts/larch.sh"),
        &bootstrap_script(root, version, state, log),
    );
}

fn identity_script(version: &str, log: &Path) -> String {
    format!(
        "#!/bin/sh\nprintf 'binary %s\\n' \"$*\" >> '{}'\nprintf '{{\"schema_version\":1,\"version\":\"{version}\",\"target\":\"test-target\"}}\\n'\n",
        log.display()
    )
}

fn bootstrap_script(root: &Path, version: &str, state: &Path, log: &Path) -> String {
    format!(
        r#"#!/bin/sh
printf 'bootstrap %s\n' "$*" >> '{log}'
[ -z "${{GH_TOKEN:-}}" ] || printf 'bootstrap-gh-token-present\n' >> '{log}'
[ -z "${{GITHUB_TOKEN:-}}" ] || printf 'bootstrap-gh-token-present\n' >> '{log}'
[ -z "${{GH_CONFIG_DIR:-}}" ] || printf 'bootstrap-gh-config-present\n' >> '{log}'
case "${{1:-}}" in
  --latest-stable-version) printf 'LARCH_STABLE_VERSION=2.0.0\n' ;;
  --preflight-release)
    [ ! -f '{state}/fail_preflight' ] || exit 1
    printf 'LARCH_PREFLIGHT_VERSION=%s\n' "$2"
    ;;
  bootstrap)
    [ ! -f '{state}/fail_bootstrap_{version}' ] || exit 1
    if [ ! -x '{root}/bin/larch' ]; then
      /bin/cp '{root}/bin-template' '{root}/bin/larch'
      /bin/chmod 755 '{root}/bin/larch'
    fi
    exec '{root}/bin/larch' "$@"
    ;;
esac
"#,
        log = log.display(),
        state = state.display(),
        root = root.display()
    )
}

fn claude_script(state: &Path, log: &Path, old_root: &Path, new_root: &Path) -> String {
    format!(
        r#"#!/bin/sh
printf 'claude %s\n' "$*" >> '{log}'
installed="$(/bin/cat '{state}/installed')"
case "$*" in
  'plugin list --json')
    if [ "$installed" = 2.0.0 ]; then root='{new_root}'; else root='{old_root}'; fi
    if [ -f '{state}/ambiguous' ]; then
      printf '[{{"id":"larch@larch-local","version":"%s","installPath":"%s"}},{{"id":"larch@larch-local","version":"%s","installPath":"%s/other"}}]\n' "$installed" "$root" "$installed" "$root"
    else
      printf '[{{"id":"larch@larch-local","version":"%s","installPath":"%s"}}]\n' "$installed" "$root"
    fi
    ;;
  'plugin marketplace list --json')
    if [ "$(/bin/cat '{state}/marketplace')" = remote ]; then
      printf '[{{"name":"larch-local","source":"url","url":"{source}"}}]\n'
    else
      printf '[{{"name":"larch-local","source":"github","url":"legacy"}}]\n'
    fi
    ;;
  'plugin marketplace update larch-local') [ ! -f '{state}/fail_refresh' ] || exit 1 ;;
  'plugin marketplace remove larch-local') : ;;
  'plugin marketplace add {source}') printf remote > '{state}/marketplace' ;;
  'plugin update larch@larch-local'|'plugin install larch@larch-local')
    [ ! -f '{state}/fail_install' ] || exit 7
    /bin/cat '{state}/desired' > '{state}/installed'
    ;;
  'plugin list') printf 'larch@larch-local %s\n' "$installed" ;;
esac
"#,
        log = log.display(),
        state = state.display(),
        old_root = old_root.display(),
        new_root = new_root.display(),
        source = SOURCE
    )
}

fn write_executable(path: &Path, body: &str) {
    fs::write(path, body).expect("script write");
    let mut permissions = fs::metadata(path).expect("script metadata").permissions();
    permissions.set_mode(0o755);
    fs::set_permissions(path, permissions).expect("script permissions");
}
