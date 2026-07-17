mod support;

use std::fs;

use predicates::prelude::*;
use support::TempRepo;

#[test]
fn all_resolves_root_from_a_nested_working_directory() {
    let repository = TempRepo::new();
    repository.write("tracked.md", b"tracked\n");
    repository.commit_all();
    let nested = repository.path().join("nested/workdir");
    fs::create_dir_all(&nested).expect("nested directory");

    TempRepo::command_from(nested)
        .arg("all")
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}

#[test]
fn rules_lists_registered_rules_in_name_order() {
    let repository = TempRepo::new();
    TempRepo::command_from(repository.path())
        .arg("rules")
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "fixture\tValidate decentralized rule registration\n",
        ))
        .stdout(predicate::str::contains(
            "git-push-refspec\tRequire Git push commands to name a destination refspec\n",
        ))
        .stdout(predicate::str::contains(
            "kv-codec\tReject ad-hoc KEY=value readers and emitters outside shared codec owners\n",
        ))
        .stdout(predicate::str::contains(
            "result-env-key-parity\tReject divergent key sets across sibling writers of the same result-env basename\n",
        ))
        .stdout(predicate::str::contains(
            "tempfile-dir\tRequire the scratch owner for ambient temporary directories\n",
        ))
        .stdout(predicate::str::contains(
            "tmpdir-arg-env-fallback\tRequire an environment fallback for args.tmpdir\n",
        ))
        .stderr(predicate::str::is_empty());
}

#[test]
fn temporary_directory_policy_covers_constructor_builder_and_suppression_shapes() {
    let repository = TempRepo::new();
    repository.write(
        "crates/larch/src/worker.rs",
        br"use tempfile::{tempdir as make_dir, Builder, TempDir};

fn create() {
    let _ = tempfile::tempdir();
    let _ = TempDir::new();
    let _ = Builder::new().tempdir();
    let _ = make_dir();
    let _ = tempfile::tempdir(); // lint-tempfile-dir: ok fixture exemption
}
",
    );
    repository.write(
        "crates/larch/src/scratch.rs",
        b"fn create() { let _ = tempfile::tempdir(); }\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "tempfile-dir"])
        .assert()
        .code(1)
        .stdout(concat!(
            "crates/larch/src/worker.rs:4: ambient temporary directory; use the scratch owner\n",
            "crates/larch/src/worker.rs:5: ambient temporary directory; use the scratch owner\n",
            "crates/larch/src/worker.rs:6: ambient temporary directory; use the scratch owner\n",
            "crates/larch/src/worker.rs:7: ambient temporary directory; use the scratch owner\n",
        ))
        .stderr(predicate::str::is_empty());
}

#[test]
fn temporary_directory_policy_ignores_unrelated_constructor_names() {
    let repository = TempRepo::new();
    repository.write(
        "crates/larch/src/worker.rs",
        br"struct TempDir;
impl TempDir { fn new() -> Self { Self } }
struct Builder;
impl Builder {
    fn new() -> Self { Self }
    fn tempdir(self) {}
}
fn tempdir() {}
fn create() {
    tempdir();
    let _ = TempDir::new();
    Builder::new().tempdir();
}
",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "tempfile-dir"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}

#[test]
fn tmpdir_policy_requires_an_option_environment_fallback_and_reasoned_suppression() {
    let repository = TempRepo::new();
    repository.write(
        "crates/larch/src/worker.rs",
        br"use std::path::PathBuf;

fn create(args: Args) {
    let _ = args.tmpdir;
    let _ = args.tmpdir.as_deref();
    let _ = args.tmpdir.or_else(|| std::env::var_os(config::ENV_IMPLEMENT_TMPDIR).map(PathBuf::from));
    let _ = args.tmpdir.as_deref().or_else(|| std::env::var_os(config::ENV_IMPLEMENT_TMPDIR).as_deref());
    let _ = args.tmpdir; // lint-tmpdir-arg-env-fallback: ok fixture exemption
}
",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "tmpdir-arg-env-fallback"])
        .assert()
        .code(1)
        .stdout(concat!(
            "crates/larch/src/worker.rs:4: direct args.tmpdir consumption; use ENV_IMPLEMENT_TMPDIR fallback\n",
            "crates/larch/src/worker.rs:5: direct args.tmpdir consumption; use ENV_IMPLEMENT_TMPDIR fallback\n",
        ))
        .stderr(predicate::str::is_empty());
}

#[test]
fn git_push_refspec_flags_raw_arrays_slices_constants_and_builders() {
    let repository = TempRepo::new();
    repository.write(
        "src/push.rs",
        br#"const GIT: &str = "git";
const PUSH: &str = "push";
const BARE: [&str; 3] = [GIT, PUSH, "origin"];
const DESTINATION: &[&str] = &["push", "origin", "HEAD:refs/heads/main"];

fn commands(remote: &str, refspec: &str) {
    let array = ["git", "push", "origin"];
    let slice = &["git", "push", "origin"];
    let accepted = ["git", "push", "origin", "HEAD:refs/heads/main"];
    std::process::Command::new("git").args(["push", "origin"]);
    std::process::Command::new("git").args(&["push", "origin"]);
    std::process::Command::new("git").args(DESTINATION);
    custom::Command::new("git").args(["push", "origin"]);
    std::process::Command::new("git").args([
        "push",
        "--force-with-lease",
        "origin",
        "HEAD:refs/heads/main",
    ]);
    std::process::Command::new("git")
        .arg("push")
        .arg(remote)
        .arg(refspec);
    std::process::Command::new("git").args(["push", "origin", "HEAD:refs/heads/main"]);
}
"#,
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "git-push-refspec"])
        .assert()
        .code(1)
        .stdout(
            "src/push.rs:3: contains git push without an explicit destination refspec\n\
             src/push.rs:7: contains git push without an explicit destination refspec\n\
             src/push.rs:8: contains git push without an explicit destination refspec\n\
             src/push.rs:10: contains git push without an explicit destination refspec\n\
             src/push.rs:11: contains git push without an explicit destination refspec\n",
        )
        .stderr(predicate::str::is_empty());
}

#[test]
fn git_push_refspec_requires_reasoned_test_only_suppressions() {
    let suppressed = TempRepo::new();
    suppressed.write(
        "crates/larch-lint/tests/suppressed.rs",
        b"fn fixture() { let bare = [\"git\", \"push\", \"origin\"]; // lint-git-push-refspec: ok fixture verifies config resolution\n}\n",
    );
    suppressed.commit_all();
    TempRepo::command_from(suppressed.path())
        .args(["rule", "git-push-refspec"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());

    let production = TempRepo::new();
    production.write(
        "src/production.rs",
        b"fn command() { let bare = [\"git\", \"push\", \"origin\"]; // lint-git-push-refspec: ok production exception\n}\n",
    );
    production.commit_all();
    TempRepo::command_from(production.path())
        .args(["rule", "git-push-refspec"])
        .assert()
        .code(1)
        .stdout("src/production.rs:1: contains git push without an explicit destination refspec\n")
        .stderr(predicate::str::is_empty());

    let missing_reason = TempRepo::new();
    missing_reason.write(
        "crates/larch-lint/tests/missing_reason.rs",
        b"fn fixture() { let bare = [\"git\", \"push\", \"origin\"]; // lint-git-push-refspec: ok\n}\n",
    );
    missing_reason.commit_all();
    TempRepo::command_from(missing_reason.path())
        .args(["rule", "git-push-refspec"])
        .assert()
        .code(2)
        .stdout(predicate::str::is_empty())
        .stderr("larch-lint: error: suppression lint-git-push-refspec lacks a reason\n");
}

#[test]
fn fixture_rule_is_discovered_without_a_central_registry_edit() {
    let repository = TempRepo::new();
    repository.write("fixtures/demo.fixture", b"allowed\nforbidden\n");
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .arg("all")
        .assert()
        .code(1)
        .stdout("fixtures/demo.fixture:2: fixture violation\n")
        .stderr(predicate::str::is_empty());
}

#[test]
fn migration_ledger_rejects_missing_duplicate_and_stale_records() {
    let missing = TempRepo::new();
    fs::remove_file(
        missing
            .path()
            .join("crates/larch-lint/migration-ledger/fixture.toml"),
    )
    .expect("remove default ledger");
    missing.write("tracked.md", b"tracked\n");
    missing.commit_all();
    TempRepo::command_from(missing.path())
        .arg("all")
        .assert()
        .code(2)
        .stderr("larch-lint: error: missing migration-ledger record: crates/larch-lint/migration-ledger/fixture.toml\n");

    let duplicate = TempRepo::new();
    duplicate.write(
        "crates/larch-lint/migration-ledger/fixture-copy.toml",
        b"rule = \"fixture\"\n",
    );
    duplicate.commit_all();
    TempRepo::command_from(duplicate.path())
        .arg("all")
        .assert()
        .code(2)
        .stderr("larch-lint: error: duplicate migration-ledger rule record: fixture\n");

    let stale = TempRepo::new();
    stale.write(
        "crates/larch-lint/migration-ledger/obsolete.toml",
        b"rule = \"obsolete\"\n",
    );
    stale.commit_all();
    TempRepo::command_from(stale.path())
        .arg("all")
        .assert()
        .code(2)
        .stderr("larch-lint: error: stale migration-ledger rule record: obsolete\n");
}

#[test]
fn unknown_rule_has_a_distinct_error_exit() {
    let repository = TempRepo::new();
    TempRepo::command_from(repository.path())
        .args(["rule", "missing"])
        .assert()
        .code(2)
        .stdout(predicate::str::is_empty())
        .stderr("larch-lint: error: unknown rule: missing\n");
}

#[test]
fn malformed_cli_input_has_the_error_exit() {
    let repository = TempRepo::new();
    TempRepo::command_from(repository.path())
        .arg("unknown-command")
        .assert()
        .code(2)
        .stderr("error: unrecognized subcommand\n");
}

#[test]
fn kv_codec_and_result_env_rules_are_clean_on_empty_rust_corpus() {
    let repository = TempRepo::new();
    repository.write("crates/demo/src/lib.rs", b"pub fn ok() {}\n");
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "kv-codec"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty());
    TempRepo::command_from(repository.path())
        .args(["rule", "result-env-key-parity"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty());
}

#[test]
fn kv_codec_reports_ad_hoc_split() {
    let repository = TempRepo::new();
    repository.write(
        "crates/demo/src/lib.rs",
        b"fn parse(line: &str) {\n    let _ = line.split_once('=');\n}\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "kv-codec"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "crates/demo/src/lib.rs:2: ad-hoc KEY=value split",
        ));
}

#[test]
fn result_env_key_parity_reports_divergent_siblings() {
    let repository = TempRepo::new();
    repository.write(
        "crates/a/src/lib.rs",
        b"fn emit() {\n    write_result_env(\"slot.env\", [(\"A\", \"1\"), (\"B\", \"2\")]);\n}\n",
    );
    repository.write(
        "crates/b/src/lib.rs",
        b"fn emit() {\n    write_result_env(\"slot.env\", [(\"A\", \"1\")]);\n}\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "result-env-key-parity"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "slot.env writer missing key B present in sibling writers",
        ));
}

#[test]
#[cfg(unix)]
fn tracked_symlink_fails_closed() {
    use std::os::unix::fs::symlink;

    let repository = TempRepo::new();
    repository.write("target.md", b"target\n");
    symlink("target.md", repository.path().join("link.md")).expect("fixture symlink");
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .arg("all")
        .assert()
        .code(2)
        .stderr("larch-lint: error: link.md: tracked symlinks are not supported\n");
}
