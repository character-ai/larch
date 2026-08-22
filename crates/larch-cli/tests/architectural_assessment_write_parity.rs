//! Black-box parity for architectural assessment-write commands (#8795).
//!
//! These cases pin the retired Python help, status envelopes, staged and
//! durable artifact bytes, identity checks, invalidation, and warning ledger.

#![cfg(unix)]

use std::{
    fs,
    path::{Path, PathBuf},
    process::Command as StdCommand,
};

use assert_cmd::Command as AssertCommand;
use sha2::{Digest as _, Sha256};
use tempfile::TempDir;

struct KindCase {
    domain: &'static str,
    prefix: &'static str,
    clean_note: &'static str,
    identifier: &'static str,
    knowledge: &'static str,
    staged_note: &'static str,
    staged_env: &'static str,
    durable_note: &'static str,
    durable_env: &'static str,
    diff: &'static str,
    status_key: &'static str,
}

const CASES: &[KindCase] = &[
    KindCase {
        domain: "architectural-guidelines",
        prefix: "ARCHITECTURAL_GUIDELINES",
        clean_note: "No architectural guideline deviations were found.",
        identifier: "G-Test-1",
        knowledge: "ARCHITECTURAL_GUIDELINES.md",
        staged_note: "architectural-guideline-staged-assessment.md",
        staged_env: "architectural-guideline-staged-assessment.env",
        durable_note: "architectural-guideline-note.md",
        durable_env: "architectural-guideline-note.meta.env",
        diff: "architectural-guideline-materialized-diff.txt",
        status_key: "GUIDELINES_STATUS",
    },
    KindCase {
        domain: "architectural-invariants",
        prefix: "ARCHITECTURAL_INVARIANTS",
        clean_note: "No architectural invariant violations were found.",
        identifier: "I-Test-1",
        knowledge: "ARCHITECTURAL_INVARIANTS.md",
        staged_note: "architectural-invariant-staged-assessment.md",
        staged_env: "architectural-invariant-staged-assessment.env",
        durable_note: "architectural-invariant-note.md",
        durable_env: "architectural-invariant-note.meta.env",
        diff: "architectural-invariant-materialized-diff.txt",
        status_key: "INVARIANTS_STATUS",
    },
];

const HEAD_A: &str = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
const HEAD_B: &str = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";

fn larch(root: &Path) -> AssertCommand {
    let mut command = AssertCommand::cargo_bin("larch").expect("larch binary should build");
    command.current_dir(root);
    command.env_remove("CLAUDE_PROJECT_DIR");
    command.env_remove("IMPLEMENT_TMPDIR");
    command
}

fn stdout(assertion: &assert_cmd::assert::Assert) -> String {
    String::from_utf8_lossy(&assertion.get_output().stdout).into_owned()
}

fn stderr(assertion: &assert_cmd::assert::Assert) -> String {
    String::from_utf8_lossy(&assertion.get_output().stderr).into_owned()
}

fn git(cwd: &Path, arguments: &[&str]) -> String {
    let completed = StdCommand::new("/usr/bin/git")
        .args(arguments)
        .current_dir(cwd)
        .output()
        .expect("git");
    assert!(
        completed.status.success(),
        "git {arguments:?} failed: {}",
        String::from_utf8_lossy(&completed.stderr)
    );
    String::from_utf8_lossy(&completed.stdout).trim().to_owned()
}

fn repository(tmp: &Path) -> PathBuf {
    let repo = tmp.join("repo");
    fs::create_dir_all(&repo).expect("repo");
    git(&repo, &["init"]);
    git(&repo, &["config", "user.name", "Larch Test"]);
    git(&repo, &["config", "user.email", "larch@example.invalid"]);
    fs::write(repo.join("README.md"), "base\n").expect("readme");
    git(&repo, &["add", "README.md"]);
    git(&repo, &["commit", "-m", "base"]);
    git(&repo, &["branch", "-M", "main"]);
    git(&repo, &["update-ref", "refs/remotes/origin/main", "HEAD"]);
    repo.canonicalize().expect("canonical repo")
}

fn fingerprint(text: &str) -> String {
    format!("{:x}", Sha256::digest(text.as_bytes()))
}

fn assert_staged_artifacts(
    root: &Path,
    case: &KindCase,
    implement: &Path,
    diff_file: &Path,
    diff_text: &str,
    expected_fingerprint: &str,
) -> String {
    let note = format!("{}\n", case.clean_note);
    let write = larch(root)
        .args([
            case.domain,
            "write-staged-assessment",
            "--implement-tmpdir",
            implement.to_str().expect("utf8"),
            "--assessment-text",
            &note,
            "--assessed-head-sha",
            HEAD_A,
            "--base-ref",
            "origin/main",
            "--diff-file",
            diff_file.to_str().expect("utf8"),
            "--outcome",
            "clean",
        ])
        .assert()
        .success();
    assert_eq!(stdout(&write), format!("{}_WRITE_STATUS=ok\n", case.prefix));
    assert_eq!(
        fs::read_to_string(implement.join(case.staged_note)).expect("staged note"),
        note
    );
    assert_eq!(
        fs::read_to_string(implement.join(case.diff)).expect("snapshot"),
        diff_text
    );
    let staged_env = fs::read_to_string(implement.join(case.staged_env)).expect("staged env");
    for row in [
        "STATUS=present".to_owned(),
        format!("ASSESSED_HEAD_SHA={HEAD_A}"),
        format!("DIFF_FINGERPRINT={expected_fingerprint}"),
        "BASE_REF=origin/main".to_owned(),
        format!("{}=present", case.status_key),
        "ASSESSMENT_KIND=clean".to_owned(),
    ] {
        if case.domain == "architectural-guidelines" && row == "GUIDELINES_STATUS=present" {
            continue;
        }
        assert!(staged_env.lines().any(|line| line == row), "{staged_env}");
    }
    assert!(
        staged_env
            .lines()
            .any(|line| line.starts_with("WRITTEN_AT=") && line.ends_with('Z'))
    );
    note
}

fn assert_pinned_artifacts(
    root: &Path,
    case: &KindCase,
    implement: &Path,
    note: &str,
    expected_fingerprint: &str,
) {
    let pin = larch(root)
        .args([
            case.domain,
            "pin-note-from-staged",
            "--implement-tmpdir",
            implement.to_str().expect("utf8"),
            "--head-sha",
            HEAD_B,
            "--base-ref",
            "origin/main",
        ])
        .assert()
        .success();
    assert_eq!(stdout(&pin), format!("{}_PIN_STATUS=ok\n", case.prefix));
    assert!(!implement.join(case.staged_note).exists());
    assert!(!implement.join(case.staged_env).exists());
    assert_eq!(
        fs::read_to_string(implement.join(case.durable_note)).expect("durable note"),
        note
    );
    let durable_env = fs::read_to_string(implement.join(case.durable_env)).expect("durable env");
    for row in [
        "STATUS=present".to_owned(),
        format!("HEAD_SHA={HEAD_B}"),
        format!("ASSESSED_HEAD_SHA={HEAD_A}"),
        format!("DIFF_FINGERPRINT={expected_fingerprint}"),
        "BASE_REF=origin/main".to_owned(),
        format!("{}=present", case.status_key),
        "ASSESSMENT_KIND=clean".to_owned(),
    ] {
        assert!(durable_env.lines().any(|line| line == row), "{durable_env}");
    }
}

fn assert_invalidation(root: &Path, case: &KindCase, implement: &Path) {
    let invalidate = larch(root)
        .args([
            case.domain,
            "invalidate",
            "--implement-tmpdir",
            implement.to_str().expect("utf8"),
        ])
        .assert()
        .success();
    assert_eq!(
        stdout(&invalidate),
        format!("{}_INVALIDATE_STATUS=ok\n", case.prefix)
    );
    assert!(!implement.join(case.durable_note).exists());
    assert!(!implement.join(case.durable_env).exists());
    assert!(implement.join(case.diff).exists());
}

#[test]
fn help_matches_retired_argparse_for_each_domain_and_write_verb() {
    let root = TempDir::new().expect("temp");
    for case in CASES {
        for verb in [
            "write-compose-assessment",
            "write-staged-assessment",
            "append-deviation-note",
            "pin-note-from-staged",
            "invalidate",
        ] {
            let assertion = larch(root.path())
                .args([case.domain, verb, "--help"])
                .assert()
                .success();
            let command = format!("{} {verb}", case.domain);
            let indent = " ".repeat(format!("usage: {command} ").len());
            let (usage_tail, options) = match verb {
                "write-compose-assessment" => (
                    format!(
                        "[-h]\n{indent}[--outcome OUTCOME]\n{indent}[--implement-tmpdir IMPLEMENT_TMPDIR]\n{indent}[--repo-root REPO_ROOT]\n{indent}(--assessment-file ASSESSMENT_FILE | --assessment-text ASSESSMENT_TEXT)"
                    ),
                    "  --outcome OUTCOME\n  --implement-tmpdir IMPLEMENT_TMPDIR\n  --repo-root REPO_ROOT\n  --assessment-file ASSESSMENT_FILE\n  --assessment-text ASSESSMENT_TEXT\n",
                ),
                "write-staged-assessment" => (
                    format!(
                        "[-h]\n{indent}[--outcome OUTCOME]\n{indent}[--implement-tmpdir IMPLEMENT_TMPDIR]\n{indent}(--assessment-file ASSESSMENT_FILE | --assessment-text ASSESSMENT_TEXT)\n{indent}[--assessed-head-sha ASSESSED_HEAD_SHA]\n{indent}[--diff-fingerprint DIFF_FINGERPRINT]\n{indent}[--base-ref BASE_REF]\n{indent}[--diff-file DIFF_FILE]"
                    ),
                    "  --outcome OUTCOME\n  --implement-tmpdir IMPLEMENT_TMPDIR\n  --assessment-file ASSESSMENT_FILE\n  --assessment-text ASSESSMENT_TEXT\n  --assessed-head-sha ASSESSED_HEAD_SHA\n  --diff-fingerprint DIFF_FINGERPRINT\n  --base-ref BASE_REF\n  --diff-file DIFF_FILE\n",
                ),
                "append-deviation-note" => (
                    format!(
                        "[-h]\n{indent}[--implement-tmpdir IMPLEMENT_TMPDIR]\n{indent}--note-file NOTE_FILE"
                    ),
                    "  --implement-tmpdir IMPLEMENT_TMPDIR\n  --note-file NOTE_FILE\n",
                ),
                "pin-note-from-staged" => (
                    format!(
                        "[-h]\n{indent}[--implement-tmpdir IMPLEMENT_TMPDIR]\n{indent}[--head-sha HEAD_SHA]\n{indent}[--base-ref BASE_REF]\n{indent}[--repo-root REPO_ROOT]"
                    ),
                    "  --implement-tmpdir IMPLEMENT_TMPDIR\n  --head-sha HEAD_SHA\n  --base-ref BASE_REF\n  --repo-root REPO_ROOT\n",
                ),
                "invalidate" => (
                    format!("[-h]\n{indent}[--implement-tmpdir IMPLEMENT_TMPDIR]"),
                    "  --implement-tmpdir IMPLEMENT_TMPDIR\n",
                ),
                _ => unreachable!(),
            };
            assert_eq!(
                stdout(&assertion),
                format!(
                    "usage: {command} {usage_tail}\n\noptions:\n  -h, --help            show this help message and exit\n{options}"
                ),
                "{} {verb}",
                case.domain
            );
        }
    }
}

#[test]
fn write_usage_status_and_reauthor_envelopes_match_python() {
    let root = TempDir::new().expect("temp");
    for case in CASES {
        let missing_source = larch(root.path())
            .args([case.domain, "write-staged-assessment"])
            .assert()
            .code(2);
        assert!(
            stderr(&missing_source)
                .contains("one of the arguments --assessment-file --assessment-text is required")
        );

        let missing_tmpdir = larch(root.path())
            .args([
                case.domain,
                "write-staged-assessment",
                "--assessment-text",
                case.clean_note,
            ])
            .assert()
            .code(2);
        assert_eq!(
            stdout(&missing_tmpdir),
            format!(
                "{}_WRITE_STATUS=failed\n{}_WARNING=missing implement tmpdir\n",
                case.prefix, case.prefix
            )
        );

        let implement = root.path().join(format!("{}-reauthor", case.domain));
        let mismatch = format!("{}: an adverse finding\n", case.identifier);
        let reauthor = larch(root.path())
            .args([
                case.domain,
                "write-staged-assessment",
                "--implement-tmpdir",
                implement.to_str().expect("utf8"),
                "--assessment-text",
                &mismatch,
                "--outcome",
                "clean",
            ])
            .assert()
            .code(7);
        assert_eq!(
            stdout(&reauthor),
            format!(
                "{}_WRITE_STATUS=re-author-required\n{}_WARNING=clean-outcome-prose-mismatch: identifier citation found in clean note\n",
                case.prefix, case.prefix
            )
        );
    }
}

#[test]
fn staged_pin_and_invalidate_preserve_artifact_wire_for_both_kinds() {
    let root = TempDir::new().expect("temp");
    let diff_text = "diff --git a/src/a.rs b/src/a.rs\n+change\n";
    let diff_file = root.path().join("diff.txt");
    fs::write(&diff_file, diff_text).expect("diff");
    let expected_fingerprint = fingerprint(diff_text);

    for case in CASES {
        let implement = root.path().join(case.domain);
        let note = assert_staged_artifacts(
            root.path(),
            case,
            &implement,
            &diff_file,
            diff_text,
            &expected_fingerprint,
        );
        assert_pinned_artifacts(root.path(), case, &implement, &note, &expected_fingerprint);
        assert_invalidation(root.path(), case, &implement);
    }
}

#[test]
fn compose_write_binds_frozen_head_and_normalizes_note() {
    let root = TempDir::new().expect("temp");
    let repo = repository(root.path());
    for case in CASES {
        fs::write(
            repo.join(case.knowledge),
            format!(
                "### {}: Preserve identity\n- Why: parity\n",
                case.identifier
            ),
        )
        .expect("knowledge");
    }
    fs::write(repo.join("README.md"), "base\nchange\n").expect("change");
    git(&repo, &["add", "."]);
    git(&repo, &["commit", "-m", "assessment change"]);
    let head = git(&repo, &["rev-parse", "HEAD"]);

    for case in CASES {
        let implement = root.path().join(format!("compose-{}", case.domain));
        let prepare = larch(&repo)
            .args([
                case.domain,
                "prepare-compose",
                "--repo-root",
                repo.to_str().expect("utf8"),
                "--implement-tmpdir",
                implement.to_str().expect("utf8"),
                "--expected-head-sha",
                &head,
            ])
            .assert()
            .success();
        assert!(
            stdout(&prepare).contains(&format!(
                "{}_COMPOSE_STATUS=assessment-required\n",
                case.prefix
            )),
            "{}",
            stdout(&prepare)
        );
        fs::write(implement.join("assessment.md"), case.clean_note).expect("assessment");
        let write = larch(&repo)
            .args([
                case.domain,
                "write-compose-assessment",
                "--repo-root",
                repo.to_str().expect("utf8"),
                "--implement-tmpdir",
                implement.to_str().expect("utf8"),
                "--assessment-file",
                "assessment.md",
                "--outcome",
                "clean",
            ])
            .assert()
            .success();
        assert_eq!(stdout(&write), format!("{}_WRITE_STATUS=ok\n", case.prefix));
        assert_eq!(
            fs::read_to_string(implement.join(case.durable_note)).expect("durable note"),
            format!("{}\n", case.clean_note)
        );
    }

    let implement = root.path().join("compose-drift");
    larch(&repo)
        .args([
            "architectural-guidelines",
            "prepare-compose",
            "--repo-root",
            repo.to_str().expect("utf8"),
            "--implement-tmpdir",
            implement.to_str().expect("utf8"),
        ])
        .assert()
        .success();
    fs::write(repo.join("README.md"), "base\nchange\ndrift\n").expect("drift");
    git(&repo, &["add", "README.md"]);
    git(&repo, &["commit", "-m", "head drift"]);
    let drift = larch(&repo)
        .args([
            "architectural-guidelines",
            "write-compose-assessment",
            "--repo-root",
            repo.to_str().expect("utf8"),
            "--implement-tmpdir",
            implement.to_str().expect("utf8"),
            "--assessment-text",
            CASES[0].clean_note,
            "--outcome",
            "clean",
        ])
        .assert()
        .code(1);
    assert_eq!(
        stdout(&drift),
        "ARCHITECTURAL_GUIDELINES_WRITE_STATUS=failed\nARCHITECTURAL_GUIDELINES_WARNING=HEAD changed after compose materialization; rerun Step 8\n"
    );
}

#[test]
fn append_and_live_pin_fail_closed_with_legacy_statuses() {
    let root = TempDir::new().expect("temp");
    let note = root.path().join("note.md");
    fs::write(&note, "G-Test-1 deviation: compatibility requires it.\n").expect("note");
    let implement = root.path().join("append");
    let first = larch(root.path())
        .args([
            "architectural-guidelines",
            "append-deviation-note",
            "--implement-tmpdir",
            implement.to_str().expect("utf8"),
            "--note-file",
            note.to_str().expect("utf8"),
        ])
        .assert()
        .success();
    assert_eq!(
        stdout(&first),
        "ARCHITECTURAL_GUIDELINES_APPEND_STATUS=ok\n"
    );
    let duplicate = larch(root.path())
        .args([
            "architectural-guidelines",
            "append-deviation-note",
            "--implement-tmpdir",
            implement.to_str().expect("utf8"),
            "--note-file",
            note.to_str().expect("utf8"),
        ])
        .assert()
        .success();
    assert_eq!(
        stdout(&duplicate),
        "ARCHITECTURAL_GUIDELINES_APPEND_STATUS=duplicate\n"
    );
    let ledger = fs::read_to_string(implement.join("execution-issues.md")).expect("ledger");
    assert_eq!(ledger.matches("G-Test-1 deviation").count(), 1);

    let empty = root.path().join("empty.md");
    fs::write(&empty, " \n\t\n").expect("empty");
    let rejected = larch(root.path())
        .args([
            "architectural-invariants",
            "append-deviation-note",
            "--implement-tmpdir",
            implement.to_str().expect("utf8"),
            "--note-file",
            empty.to_str().expect("utf8"),
        ])
        .assert()
        .code(1);
    assert_eq!(
        stdout(&rejected),
        "ARCHITECTURAL_INVARIANTS_APPEND_STATUS=failed\nARCHITECTURAL_INVARIANTS_WARNING=note-file: content must not be empty\n"
    );

    let repo = repository(root.path());
    fs::write(repo.join("README.md"), "base\nlive change\n").expect("change");
    git(&repo, &["add", "README.md"]);
    git(&repo, &["commit", "-m", "live change"]);
    let staged = root.path().join("live-pin");
    let stale_diff = root.path().join("stale.diff");
    fs::write(&stale_diff, "stale diff\n").expect("stale diff");
    larch(&repo)
        .args([
            "architectural-guidelines",
            "write-staged-assessment",
            "--implement-tmpdir",
            staged.to_str().expect("utf8"),
            "--assessment-text",
            CASES[0].clean_note,
            "--assessed-head-sha",
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "--base-ref",
            "origin/main",
            "--diff-file",
            stale_diff.to_str().expect("utf8"),
            "--outcome",
            "clean",
        ])
        .assert()
        .success();
    let skipped = larch(&repo)
        .args([
            "architectural-guidelines",
            "pin-note-from-staged",
            "--implement-tmpdir",
            staged.to_str().expect("utf8"),
            "--head-sha",
            "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "--base-ref",
            "origin/main",
            "--repo-root",
            repo.to_str().expect("utf8"),
        ])
        .assert()
        .success();
    assert_eq!(
        stdout(&skipped),
        "ARCHITECTURAL_GUIDELINES_PIN_STATUS=skipped\n"
    );
    assert!(staged.join(CASES[0].staged_note).exists());
    assert!(!staged.join(CASES[0].durable_note).exists());
}
