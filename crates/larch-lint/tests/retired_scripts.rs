mod support;

use std::fs;

use predicates::prelude::*;
use support::TempRepo;

const MANIFEST: &str = "python/migrated-scripts.tsv";
const DEV_SKILL_SCRIPT_DIR: &str = ".claude/skills/release/scripts/";
const CLASSIFY_BUMP: &str = "classify-bump.sh";
const SCRIPT_DIR: &str = "scripts/";
const APPEND_EXECUTION_ISSUE: &str = "append-execution-issue.sh";
const RESOLVE_REPO: &str = "resolve-repo.sh";

fn run(repository: &TempRepo) -> assert_cmd::assert::Assert {
    TempRepo::command_from(repository.path())
        .args(["rule", "retired-scripts"])
        .assert()
}

fn manifest(repository: &TempRepo, entries: &[&str]) {
    let body = entries.iter().fold(String::new(), |mut body, entry| {
        body.push_str(entry);
        body.push_str("\t#fixture\n");
        body
    });
    repository.write(MANIFEST, body.as_bytes());
}

fn retired_path(directory: &str, basename: &str) -> String {
    format!("{directory}{basename}")
}

#[test]
fn clean_manifest_emits_the_established_contract() {
    let repository = TempRepo::new();
    repository.commit_all();

    run(&repository)
        .success()
        .stdout("LINT_STATUS=ok\nRETIRED_PATHS=0\nRETIRED_REFS=0\nEMBEDDED_LEGACY_REFS=0\n")
        .stderr(predicate::str::is_empty());
}

#[test]
fn reports_full_paths_comments_and_non_shell_paths() {
    let repository = TempRepo::new();
    manifest(
        &repository,
        &[
            "scripts/old-helper.sh",
            "scripts/synthetic-retired-helper.sh",
            "python/old_ci_helper.py",
            "python/cli.py ci wait",
        ],
    );
    repository.write(
        "docs/consumer.md",
        b"Call scripts/old-helper.sh.\n# scripts/synthetic-retired-helper.sh\nImport python/old_ci_helper.py.\n",
    );
    repository.write(
        "scripts/ship-driver.txt",
        b"record_failure checks \"python/cli.py ci wait exited unexpectedly\" \"$rc\"\n",
    );
    repository.commit_all();

    run(&repository)
        .code(1)
        .stdout(predicate::str::contains(
            "docs/consumer.md:1: references retired path \"scripts/old-helper.sh\"\n",
        ))
        .stdout(predicate::str::contains(
            "docs/consumer.md:2: references retired path \"scripts/synthetic-retired-helper.sh\"\n",
        ))
        .stdout(predicate::str::contains("LINT_STATUS=findings\n"))
        .stdout(predicate::str::contains("RETIRED_REFS=4\n"));
}

#[test]
fn catches_script_dir_references_only_in_the_retired_directory() {
    let repository = TempRepo::new();
    let retired = retired_path(SCRIPT_DIR, RESOLVE_REPO);
    manifest(&repository, &[&retired]);
    repository.write(
        "scripts/caller.sh",
        b"REPO=$(\"$SCRIPT_DIR/resolve-repo.sh\")\n",
    );
    repository.write("docs/consumer.md", b"helpers/resolve-repo.sh\n");
    repository.commit_all();

    run(&repository)
        .code(1)
        .stdout(predicate::str::contains("scripts/caller.sh:1:"))
        .stdout(predicate::str::contains("docs/consumer.md").not());
}

#[test]
fn catches_allowed_dev_skill_and_implement_skill_basenames() {
    let repository = TempRepo::new();
    let classify_bump = retired_path(DEV_SKILL_SCRIPT_DIR, CLASSIFY_BUMP);
    manifest(
        &repository,
        &[&classify_bump, "scripts/implement-helper.sh"],
    );
    repository.write(
        &format!("{DEV_SKILL_SCRIPT_DIR}classify-bump.md"),
        b"Call `classify-bump.sh`.\n",
    );
    repository.write(
        "skills/implement/SKILL.md",
        b"Call `implement-helper.sh`.\n",
    );
    repository.commit_all();

    run(&repository)
        .code(1)
        .stdout(predicate::str::contains(
            ".claude/skills/release/scripts/classify-bump.md:1:",
        ))
        .stdout(predicate::str::contains("skills/implement/SKILL.md:1:"));
}

#[test]
fn full_paths_remain_findings_with_a_lint_ignore_marker() {
    let repository = TempRepo::new();
    let classify_bump = retired_path(DEV_SKILL_SCRIPT_DIR, CLASSIFY_BUMP);
    manifest(&repository, &[&classify_bump]);
    repository.write(
        &format!("{DEV_SKILL_SCRIPT_DIR}classify-bump.md"),
        format!("Call {classify_bump}. # lint-ignore\n").as_bytes(),
    );
    repository.commit_all();

    run(&repository).code(1).stdout(predicate::str::contains(
        ".claude/skills/release/scripts/classify-bump.md:1:",
    ));
}

#[test]
fn bare_basename_exceptions_remain_clean() {
    let repository = TempRepo::new();
    let classify_bump = retired_path(DEV_SKILL_SCRIPT_DIR, CLASSIFY_BUMP);
    let append_execution_issue = retired_path(SCRIPT_DIR, APPEND_EXECUTION_ISSUE);
    manifest(&repository, &[&classify_bump, &append_execution_issue]);
    repository.write(
        &format!("{DEV_SKILL_SCRIPT_DIR}ignored.md"),
        b"classify-bump.sh # lint-ignore\n",
    );
    repository.write(
        ".claude/skills/other/scripts/consumer.md",
        b"classify-bump.sh\n",
    );
    repository.write(
        &format!("{DEV_SKILL_SCRIPT_DIR}path.md"),
        b"other/path/classify-bump.sh\n",
    );
    repository.write(
        &format!("{DEV_SKILL_SCRIPT_DIR}notes.txt"),
        b"classify-bump.sh\n",
    );
    repository.write(
        &format!("{DEV_SKILL_SCRIPT_DIR}live.md"),
        b"classify-bump.sh\n",
    );
    repository.write(&format!("{DEV_SKILL_SCRIPT_DIR}live.sh"), b"echo live\n");
    repository.write("scripts/contract.md", b"append-execution-issue.sh\n");
    repository.commit_all();

    run(&repository)
        .success()
        .stdout(predicate::str::contains("LINT_STATUS=ok\n"));
}

#[test]
fn excludes_historical_and_binary_content() {
    let repository = TempRepo::new();
    manifest(&repository, &["scripts/old-helper.sh"]);
    repository.write(
        "larch-logs/implement/run-1/log.md",
        b"scripts/old-helper.sh\n",
    );
    repository.write("CHANGELOG.md", b"scripts/old-helper.sh\n");
    repository.write(".claude-plugin/plugin.json", b"scripts/old-helper.sh\n");
    repository.write("assets/image.bin", b"\0scripts/old-helper.sh\0");
    repository.commit_all();

    run(&repository).success();
}

#[test]
fn still_present_retired_path_is_a_finding() {
    let repository = TempRepo::new();
    manifest(&repository, &["scripts/old-helper.sh"]);
    repository.write("scripts/old-helper.sh", b"#!/bin/bash\n");
    repository.commit_all();

    run(&repository)
        .code(1)
        .stdout(predicate::str::contains(
            "scripts/old-helper.sh:1: retired path is still present in the tree\n",
        ))
        .stdout(predicate::str::contains("RETIRED_REFS=0\n"));
}

#[test]
fn malformed_missing_and_unsafe_manifests_fail_closed() {
    let malformed = TempRepo::new();
    malformed.write(MANIFEST, b"bad-row\n");
    malformed.commit_all();
    run(&malformed)
        .code(2)
        .stderr(predicate::str::contains("manifest line 1 malformed"));

    let unsafe_path = TempRepo::new();
    unsafe_path.write(MANIFEST, b"../outside.sh\t#fixture\n");
    unsafe_path.commit_all();
    run(&unsafe_path)
        .code(2)
        .stderr(predicate::str::contains("unsafe retired manifest path"));

    let missing = TempRepo::new();
    fs::remove_file(missing.path().join(MANIFEST)).expect("remove manifest");
    missing.commit_all();
    run(&missing).code(2).stderr(predicate::str::contains(
        "manifest not found: python/migrated-scripts.tsv",
    ));
}

#[test]
fn counts_embedded_legacy_tuple_references() {
    let repository = TempRepo::new();
    manifest(&repository, &["scripts/old-helper.sh"]);
    repository.write(
        "python/larch/review/plan_review.py",
        b"_run_legacy((\"scripts\", \"old-helper.sh\"))\n",
    );
    repository.write(
        "python/larch/review/plan_review_panel.py",
        b"_p(\"scripts\", \"old-helper.sh\")\n",
    );
    repository.commit_all();

    run(&repository)
        .success()
        .stdout(predicate::str::contains("EMBEDDED_LEGACY_REFS=2\n"))
        .stdout(predicate::str::contains("RETIRED_REFS=0\n"));
}

#[test]
fn root_flag_supports_an_explicit_repository() {
    let repository = TempRepo::new();
    repository.commit_all();

    TempRepo::command_from("/")
        .args([
            "--root",
            repository.path().to_str().expect("utf8 fixture path"),
            "rule",
            "retired-scripts",
        ])
        .assert()
        .success()
        .stdout(predicate::str::contains("LINT_STATUS=ok\n"));
}
