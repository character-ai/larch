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
            "env-via-config-constant\tReject bare environment-key literals already owned by shared ENV_* constants\n",
        ))
        .stdout(predicate::str::contains(
            "fixture\tValidate decentralized rule registration\n",
        ))
        .stdout(predicate::str::contains(
            "guideline-no-exception\tRequire baselines for no-exception architectural guidelines\n",
        ))
        .stdout(predicate::str::contains(
            "literal-counts\tReject drift-prone literal item counts in Markdown\n",
        ))
        .stdout(predicate::str::contains(
            "bg-wait-coverage\tReject unallowlisted background-launch prose in skills\n",
        ))
        .stdout(predicate::str::contains(
            "git-push-refspec\tRequire Git push commands to name a destination refspec\n",
        ))
        .stdout(predicate::str::contains(
            "gh-argv-literal\tRequire raw gh command ownership by the GitHub wrapper\n",
        ))
        .stdout(predicate::str::contains(
            "kv-codec\tReject ad-hoc KEY=value readers and emitters outside shared codec owners\n",
        ))
        .stdout(predicate::str::contains(
            "result-env-key-parity\tReject divergent key sets across sibling writers of the same result-env basename\n",
        ))
        .stdout(predicate::str::contains(
            "root-resolution\tReject private root helpers and direct git rev-parse --show-toplevel construction\n",
        ))
        .stdout(predicate::str::contains(
            "tempfile-dir\tRequire the scratch owner for ambient temporary directories\n",
        ))
        .stdout(predicate::str::contains(
            "tmpdir-arg-env-fallback\tRequire an environment fallback for args.tmpdir\n",
        ))
        .stdout(predicate::str::contains(
            "status-routing\tRequire explicit Option, Result, and status-enum variant routing instead of boolean shortcuts\n",
        ))
        .stdout(predicate::str::contains(
            "subprocess-via-runner\tRequire std::process::Command ownership by the shared runner\n",
        ))
        .stdout(predicate::str::contains(
            "self-disarmable-gate\tReject optional metadata that suppresses a design size or publish hard gate\n",
        ))
        .stderr(predicate::str::is_empty());
}

#[test]
fn status_routing_requires_explicit_variants_without_a_baseline() {
    let repository = TempRepo::new();
    repository.write(
        "crates/demo/src/lib.rs",
        br"enum Status { Done, Pending }

fn enum_route(status: Status) {
    match status {
        Status::Done if audit() => finish(),
        Status::Pending => retry(),
    }
    let _ = status.is_empty();
}

fn option_route(status: Option<Status>) {
    if let Some(Status::Done) = status {
        finish();
    }
    if status.is_some() {
        finish();
    }
    if Option::is_none(&status) {
        retry();
    }
}

fn result_route(result: Result<Status, ()>) {
    match result {
        Ok(Status::Done) => finish(),
        Err(_) => retry(),
    }
    if result.is_ok() {
        finish();
    }
    let _ = Result::is_err(&result);
}

fn adapter_route(outcome: Status) {
    if outcome == Status::Done {
        finish();
    }
    let _ = bool::from(outcome);
    let _ = Into::<bool>::into(outcome);
}

fn optional_value(message: Option<String>) {
    if message.is_some() {
        print(message);
    }
}

fn explicit_option_route(status: Option<Status>) {
    if matches!(status, Some(Status::Done)) {
        finish();
    }
    if status.is_some() {
        finish();
    }
}

fn unrelated_optional_check(status: Option<Status>, settings: Settings) {
    if status == settings.default {
        finish();
    }
    if status.is_some() {
        finish();
    }
}
",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "status-routing"])
        .assert()
        .code(1)
        .stdout(concat!(
            "crates/demo/src/lib.rs:8: boolean shortcut is_empty on routed status; use an explicit variant pattern\n",
            "crates/demo/src/lib.rs:15: boolean shortcut is_some on routed status; use an explicit variant pattern\n",
            "crates/demo/src/lib.rs:18: boolean shortcut is_none on routed status; use an explicit variant pattern\n",
            "crates/demo/src/lib.rs:28: boolean shortcut is_ok on routed result; use an explicit variant pattern\n",
            "crates/demo/src/lib.rs:31: boolean shortcut is_err on routed result; use an explicit variant pattern\n",
            "crates/demo/src/lib.rs:38: boolean shortcut bool::from on routed outcome; use an explicit variant pattern\n",
            "crates/demo/src/lib.rs:39: boolean shortcut Into::<bool>::into on routed outcome; use an explicit variant pattern\n",
            "crates/demo/src/lib.rs:52: boolean shortcut is_some on routed status; use an explicit variant pattern\n",
        ))
        .stderr(predicate::str::is_empty());
}

#[test]
fn status_routing_honors_reasoned_suppressions() {
    let repository = TempRepo::new();
    repository.write(
        "crates/demo/src/lib.rs",
        br"enum Status { Done }

fn route(status: Option<Status>) {
    match status {
        Some(Status::Done) => finish(),
        None => retry(),
    }
    if status.is_some() { // lint-status-routing: ok fixture exercises suppression
        finish();
    }
}
",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "status-routing"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
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
fn literal_counts_covers_violations_fences_pragmas_and_untracked_markdown() {
    let repository = TempRepo::new();
    repository.write(
        "docs/policy.md",
        b"5 reviewers require a refresh.\n```markdown\n7 agents are fenced.\n```\n8 rows fixed by statute. <!-- lint-literal-counts: allow historical -->\n",
    );
    repository.write(
        "larch-logs/implement/run/final-summary.md",
        b"9 reviewers are historical artifacts.\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "literal-counts"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "docs/policy.md:1: literal item count",
        ))
        .stdout(predicate::str::contains("larch-logs/implement/run/final-summary.md").not())
        .stderr(predicate::str::is_empty());

    repository.write("docs/untracked.md", b"6 specialists are untracked.\n");
    TempRepo::command_from(repository.path())
        .args(["rule", "literal-counts"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "docs/untracked.md:1: literal item count",
        ));
}

#[test]
fn literal_counts_rejects_malformed_utf8() {
    let repository = TempRepo::new();
    repository.write("docs/invalid.md", b"\xff");
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "literal-counts"])
        .assert()
        .code(2)
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::contains(
            "docs/invalid.md: cannot read UTF-8 source",
        ));
}

#[test]
fn background_wait_coverage_allows_documented_exceptions_and_rejects_new_prose() {
    let repository = TempRepo::new();
    repository.write(
        "crates/larch-lint/config/bg-wait-allowlist.txt",
        b"skills/shared/legacy.md\tretained migration contract\n",
    );
    repository.write(
        "skills/shared/legacy.md",
        b"Use `run_in_background: true` for the retained contract.\n",
    );
    repository.write(
        "skills/implement/SKILL.md",
        b"do NOT set `run_in_background: true` for this lane.\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "bg-wait-coverage"])
        .assert()
        .success();

    repository.write(
        "skills/design/SKILL.md",
        b"Set `run_in_background: true` for this lane.\n",
    );
    TempRepo::command_from(repository.path())
        .args(["rule", "bg-wait-coverage"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "skills/design/SKILL.md:1: run_in_background is forbidden",
        ));
}

#[test]
fn background_wait_coverage_rejects_malformed_allowlist_rows() {
    let repository = TempRepo::new();
    repository.write(
        "crates/larch-lint/config/bg-wait-allowlist.txt",
        b"skills/design/SKILL.md\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "bg-wait-coverage"])
        .assert()
        .code(2)
        .stderr(predicate::str::contains("malformed allowlist row 1"));
}

#[test]
fn guideline_no_exception_warns_for_baselined_entries_and_fails_new_or_stale_ones() {
    let repository = TempRepo::new();
    repository.write(
        "crates/larch-lint/config/guideline-no-exception-baseline.json",
        b"[{\"guideline_id\":\"G-Kept-1\",\"reason\":\"kept as guidance\"}]\n",
    );
    repository.write(
        "ARCHITECTURAL_GUIDELINES.md",
        b"### G-Kept-1: Kept guidance\n- Why: fixture body.\n- Deviate when: never; fixture.\n\n### G-New-1: New guidance\n- Why: fixture body.\n- Deviate when: n/a for fixture.\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "guideline-no-exception"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "ARCHITECTURAL_GUIDELINES.md:7: G-New-1 has a no-exception",
        ))
        .stderr(predicate::str::contains(
            "warning: G-Kept-1 line 3 has a no-exception deviate clause (baselined)",
        ));

    repository.write(
        "ARCHITECTURAL_GUIDELINES.md",
        b"### G-Kept-1: Kept guidance\n- Why: fixture body.\n- Deviate when: when a fixture needs an exception.\n",
    );
    TempRepo::command_from(repository.path())
        .args(["rule", "guideline-no-exception"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "guideline-no-exception-baseline.json:1: stale baseline row: G-Kept-1",
        ));
}

#[test]
fn guideline_no_exception_rejects_malformed_baselines_and_ignores_fenced_headings() {
    let repository = TempRepo::new();
    repository.write(
        "ARCHITECTURAL_GUIDELINES.md",
        b"```markdown\n### G-Fenced-1: Not an entry\n- Deviate when: never.\n```\n### G-Real-1: Real entry\n- Why: fixture body.\n- Deviate when: when a fixture needs an exception.\n",
    );
    repository.commit_all();
    TempRepo::command_from(repository.path())
        .args(["rule", "guideline-no-exception"])
        .assert()
        .success();

    repository.write(
        "crates/larch-lint/config/guideline-no-exception-baseline.json",
        b"[{\"guideline_id\":\"G-Real-1\"}]\n",
    );
    TempRepo::command_from(repository.path())
        .args(["rule", "guideline-no-exception"])
        .assert()
        .code(2)
        .stderr(predicate::str::contains("invalid JSON baseline"));
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
fn rust_policy_rules_are_clean_on_empty_rust_corpus() {
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
    TempRepo::command_from(repository.path())
        .args(["rule", "self-disarmable-gate"])
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
