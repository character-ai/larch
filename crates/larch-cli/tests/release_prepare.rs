//! Black-box parity coverage for migrated release-planning commands.

use std::{fs, path::Path, process::Command};

use assert_cmd::Command as AssertCommand;
use tempfile::TempDir;

#[test]
fn read_version_preserves_best_effort_machine_output() {
    let root = tempfile::tempdir().expect("plugin root");
    fs::create_dir(root.path().join(".claude-plugin")).expect("manifest parent");
    fs::write(
        root.path().join(".claude-plugin/plugin.json"),
        r#"{"version":"9.8.7"}"#,
    )
    .expect("manifest");

    larch()
        .args(["plugin", "read-version"])
        .env("CLAUDE_PLUGIN_ROOT", root.path())
        .assert()
        .success()
        .stdout("LARCH_PLUGIN_VERSION=9.8.7\n");

    fs::write(root.path().join(".claude-plugin/plugin.json"), "not json")
        .expect("malformed manifest");
    larch()
        .args(["plugin", "read-version"])
        .env("CLAUDE_PLUGIN_ROOT", root.path())
        .assert()
        .success()
        .stdout("LARCH_PLUGIN_VERSION=unknown\n");
}

#[test]
fn classify_bump_covers_patch_minor_major_and_malformed_versions() {
    let patch = repository();
    let base = head(patch.path());
    fs::write(patch.path().join("README.md"), "changed\n").expect("patch change");
    commit_all(patch.path(), "docs");
    assert_bump(patch.path(), &base, "PATCH");

    let minor = repository();
    let base = head(minor.path());
    fs::create_dir_all(minor.path().join("skills/new")).expect("skill parent");
    fs::write(minor.path().join("skills/new/SKILL.md"), "# New\n").expect("skill");
    commit_all(minor.path(), "new skill");
    assert_bump(minor.path(), &base, "MINOR");

    let major = repository();
    let base = head(major.path());
    fs::remove_file(major.path().join("skills/base/SKILL.md")).expect("remove skill");
    commit_all(major.path(), "remove skill");
    assert_bump(major.path(), &base, "MAJOR");

    fs::write(
        major.path().join(".claude-plugin/plugin.json"),
        r#"{"version":"bad"}"#,
    )
    .expect("malformed version");
    larch()
        .current_dir(major.path())
        .args([
            "release",
            "classify-bump",
            "--base",
            &base,
            "--head",
            "HEAD",
        ])
        .assert()
        .failure()
        .stderr(predicates::str::contains("is not semver"));
}

#[test]
fn classify_bump_preserves_noop_idempotency() {
    let no_op = repository();
    let base = head(no_op.path());
    git(
        no_op.path(),
        ["update-ref", "refs/remotes/origin/main", &base],
    );
    fs::write(
        no_op.path().join(".claude-plugin/plugin.json"),
        r#"{"version":"1.2.4"}"#,
    )
    .expect("version bump");
    commit_all(no_op.path(), "Release v1.2.4");
    larch()
        .current_dir(no_op.path())
        .args(["release", "classify-bump"])
        .assert()
        .success()
        .stdout(predicates::str::contains("BUMP_TYPE=NONE\n"));
}

#[test]
fn release_prepare_rejects_dirty_main_before_network_access() {
    let repository = repository();
    git(
        repository.path(),
        ["remote", "add", "origin", "https://github.com/o/r.git"],
    );
    git(
        repository.path(),
        ["update-ref", "refs/remotes/origin/main", "HEAD"],
    );
    let out_dir = tempfile::tempdir().expect("output directory");
    fs::write(repository.path().join("untracked"), "dirty\n").expect("dirty file");
    larch()
        .current_dir(repository.path())
        .args([
            "release",
            "prepare",
            "--repo",
            "o/r",
            "--out-dir",
            out_dir.path().to_str().expect("UTF-8 output directory"),
        ])
        .assert()
        .failure()
        .stdout(predicates::str::contains("ERROR=dirty-main\n"));
}

#[test]
fn release_prepare_accepts_local_main_behind_origin_tip() {
    let repository = repository();
    git(
        repository.path(),
        ["remote", "add", "origin", "https://github.com/o/r.git"],
    );
    let behind = head(repository.path());
    fs::write(repository.path().join("README.md"), "ahead\n").expect("ahead change");
    commit_all(repository.path(), "ahead");
    git(
        repository.path(),
        ["update-ref", "refs/remotes/origin/main", &head(repository.path())],
    );
    git(repository.path(), ["reset", "--hard", "--quiet", &behind]);
    let out_dir = tempfile::tempdir().expect("output directory");
    // Local main may lag the pinned tip; prepare still fetches and reaches the
    // GitHub planning calls (which fail offline with a non-stale error).
    let assertion = larch()
        .current_dir(repository.path())
        .args([
            "release",
            "prepare",
            "--repo",
            "o/r",
            "--out-dir",
            out_dir.path().to_str().expect("UTF-8 output directory"),
        ])
        .assert()
        .failure();
    let stdout = String::from_utf8_lossy(&assertion.get_output().stdout);
    assert!(
        stdout.contains("ERROR="),
        "expected an ERROR= token, got {stdout:?}"
    );
    assert!(
        !stdout.contains("ERROR=stale-local-main\n"),
        "behind local main must not fail as stale-local-main: {stdout:?}"
    );
}

#[test]
fn release_prepare_accepts_clean_main_with_conversion_attributes() {
    let repository = repository();
    git(
        repository.path(),
        ["remote", "add", "origin", "https://github.com/o/r.git"],
    );
    git(
        repository.path(),
        ["update-ref", "refs/remotes/origin/main", "HEAD"],
    );
    let out_dir = tempfile::tempdir().expect("output directory");

    larch()
        .current_dir(repository.path())
        .env("HOME", repository.path())
        .env_remove("GH_CONFIG_DIR")
        .env_remove("XDG_CONFIG_HOME")
        .env("LARCH_GH_TOKEN", "must-not-authenticate")
        .env("GH_TOKEN", "must-not-authenticate")
        .env("GITHUB_TOKEN", "must-not-authenticate")
        .args([
            "release",
            "prepare",
            "--repo",
            "o/r",
            "--out-dir",
            out_dir.path().to_str().expect("UTF-8 output directory"),
        ])
        .assert()
        .failure()
        .stdout(predicates::str::contains("ERROR=fetch-origin-main-failed\n"));
}

fn assert_bump(repository: &Path, base: &str, expected: &str) {
    larch()
        .current_dir(repository)
        .args(["release", "classify-bump", "--base", base, "--head", "HEAD"])
        .assert()
        .success()
        .stdout(predicates::str::contains(format!("BUMP_TYPE={expected}\n")));
}

fn repository() -> TempDir {
    let repository = tempfile::tempdir().expect("repository");
    git(repository.path(), ["init", "--quiet"]);
    git(repository.path(), ["branch", "-M", "main"]);
    git(
        repository.path(),
        ["config", "user.email", "test@example.com"],
    );
    git(repository.path(), ["config", "user.name", "Test"]);
    fs::create_dir_all(repository.path().join(".claude-plugin")).expect("manifest parent");
    fs::create_dir_all(repository.path().join("skills/base")).expect("skill parent");
    fs::write(
        repository.path().join(".claude-plugin/plugin.json"),
        r#"{"version":"1.2.3"}"#,
    )
    .expect("manifest");
    fs::write(
        repository.path().join("skills/base/SKILL.md"),
        "---\nname: base\nargument-hint: [--old]\n---\n",
    )
    .expect("base skill");
    fs::write(
        repository.path().join(".gitattributes"),
        "* text=auto eol=lf\n",
    )
    .expect("conversion attributes");
    fs::write(repository.path().join("README.md"), "base\n").expect("readme");
    commit_all(repository.path(), "base");
    repository
}

fn commit_all(repository: &Path, subject: &str) {
    git(repository, ["add", "-A"]);
    git(repository, ["commit", "--quiet", "-m", subject]);
}

fn head(repository: &Path) -> String {
    let output = git_output(repository, ["rev-parse", "HEAD"]);
    String::from_utf8(output.stdout)
        .expect("UTF-8 object id")
        .trim()
        .to_owned()
}

fn git<const N: usize>(repository: &Path, arguments: [&str; N]) {
    let output = git_output(repository, arguments);
    assert!(
        output.status.success(),
        "git failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
}

fn git_output<const N: usize>(repository: &Path, arguments: [&str; N]) -> std::process::Output {
    Command::new("git")
        .args(arguments)
        .current_dir(repository)
        .output()
        .expect("launch git fixture command")
}

fn larch() -> AssertCommand {
    #[allow(deprecated)]
    AssertCommand::cargo_bin("larch").expect("larch binary")
}
