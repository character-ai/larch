//! Black-box coverage for the `implement` verbs migrated from Python by #8609.

use std::{fs, path::Path};

use assert_cmd::Command;
use tempfile::TempDir;

/// Every case runs with a scrubbed environment so an operator's own
/// `CLONE_TAG` or `IMPLEMENT_TMPDIR` cannot leak into a derivation.
fn larch(arguments: &[&str]) -> Command {
    let mut command = Command::cargo_bin("larch").expect("larch binary should build");
    command
        .env_remove("CLONE_TAG")
        .env_remove("IMPLEMENT_TMPDIR")
        .args(arguments);
    command
}

fn clone_tag_with_pwd(pwd: &str) -> String {
    let output = larch(&["implement", "clone-tag"])
        .env("PWD", pwd)
        .assert()
        .success()
        .get_output()
        .stdout
        .clone();
    String::from_utf8(output).expect("clone-tag stdout is UTF-8")
}

#[test]
fn a_declared_clone_tag_survives_shell_quoting_verbatim() {
    let declared = "tag with spaces; $(echo nope) 'quoted'";

    let stdout = larch(&["implement", "clone-tag"])
        .env("CLONE_TAG", declared)
        .assert()
        .success()
        .get_output()
        .stdout
        .clone();

    assert_eq!(
        String::from_utf8(stdout).expect("clone-tag stdout is UTF-8"),
        concat!(
            r#"CLONE_TAG_FULL='tag with spaces; $(echo nope) '"'"'quoted'"'"''"#,
            "\n",
            r#"EXPECTED_TMPDIR_BASENAME_PREFIX='claude-implement-tag with spaces; $(echo nope) '"'"'quoted'"'"'-'"#,
            "\n",
        )
    );
}

#[test]
fn an_absent_clone_tag_derives_from_the_logical_pwd() {
    assert_eq!(
        clone_tag_with_pwd("/logical/repo with spaces!"),
        concat!(
            "CLONE_TAG_FULL=repo_with_spaces_\n",
            "EXPECTED_TMPDIR_BASENAME_PREFIX=claude-implement-repo_with_spaces_-\n",
        )
    );
}

#[test]
fn a_derived_clone_tag_truncates_after_thirty_two_bytes() {
    let long = format!("/parent/{}", "x".repeat(40));

    assert_eq!(
        clone_tag_with_pwd(&long),
        format!(
            "CLONE_TAG_FULL={tag}\nEXPECTED_TMPDIR_BASENAME_PREFIX=claude-implement-{tag}-\n",
            tag = "x".repeat(32)
        )
    );
}

#[test]
fn an_empty_logical_basename_derives_the_underscore_fallback() {
    assert_eq!(
        clone_tag_with_pwd("/"),
        concat!(
            "CLONE_TAG_FULL=_\n",
            "EXPECTED_TMPDIR_BASENAME_PREFIX=claude-implement-_-\n",
        )
    );
}

#[test]
fn coder_scout_normalization_requires_a_tmpdir() {
    larch(&["implement", "normalize-coder-scout"])
        .assert()
        .code(2)
        .stderr(predicates_str("--tmpdir is required"));
}

#[test]
fn coder_scout_normalization_refuses_a_tmpdir_that_is_not_a_directory() {
    let fixture = TempDir::new().expect("fixture");
    let file = fixture.path().join("not-a-directory");
    fs::write(&file, "").expect("seed regular file");

    larch(&["implement", "normalize-coder-scout", "--tmpdir"])
        .arg(&file)
        .assert()
        .code(2)
        .stderr(predicates_str("not a directory"));
}

#[test]
fn coder_scout_normalization_rejects_an_unknown_producer() {
    larch(&["implement", "normalize-coder-scout", "--producer", "robot"])
        .assert()
        .code(2)
        .stderr(predicates_str("invalid choice: 'robot'"));
}

#[test]
fn coder_scout_normalization_reports_a_missing_manifest_as_invalid() {
    let fixture = TempDir::new().expect("fixture");
    let tmpdir = fixture.path();

    let stdout = larch(&["implement", "normalize-coder-scout", "--tmpdir"])
        .arg(tmpdir)
        .assert()
        .success()
        .get_output()
        .stdout
        .clone();

    let text = String::from_utf8(stdout).expect("normalize stdout is UTF-8");
    assert!(
        text.contains("SCOUT_CODER_STATUS=missing-or-invalid"),
        "absent raw manifest must normalize to missing-or-invalid: {text}"
    );
    assert_eq!(
        read(&tmpdir.join("scout-coder-manifest.json")),
        "{\"archetypes\":[]}\n",
        "a refused normalization still publishes the empty manifest"
    );
}

#[test]
fn step_zero_bootstrap_requires_a_mode() {
    larch(&["implement", "step-0-bootstrap"])
        .assert()
        .code(2)
        .stderr(predicates_str(
            "the following arguments are required: --mode",
        ));
}

#[test]
fn step_zero_bootstrap_rejects_an_unknown_mode() {
    larch(&["implement", "step-0-bootstrap", "--mode", "sideways"])
        .assert()
        .code(2)
        .stderr(predicates_str("invalid choice: 'sideways'"));
}

#[test]
fn step_zero_bootstrap_rejects_a_non_boolean_flag_value() {
    larch(&[
        "implement",
        "step-0-bootstrap",
        "--mode",
        "initial",
        "--forked-target",
        "yes",
    ])
    .assert()
    .code(2)
    .stderr("step-0-bootstrap: --forked-target must be true or false\n");
}

#[test]
fn step_zero_bootstrap_rejects_an_unknown_difficulty() {
    larch(&[
        "implement",
        "step-0-bootstrap",
        "--mode",
        "initial",
        "--difficulty",
        "EPIC",
    ])
    .assert()
    .code(2)
    .stderr("step-0-bootstrap: --difficulty must be TRIVIAL, MODERATE, or HARD\n");
}

#[test]
fn step_zero_bootstrap_resume_requires_an_exported_implement_tmpdir() {
    larch(&["implement", "step-0-bootstrap", "--mode", "resume"])
        .assert()
        .code(2)
        .stderr("bootstrap invoke: --mode resume requires exported IMPLEMENT_TMPDIR\n");
}

#[test]
fn the_degraded_gate_requires_an_exported_implement_tmpdir() {
    larch(&["implement", "step-0-degraded-gate"])
        .assert()
        .code(2)
        .stderr("IMPLEMENT_TMPDIR required\n");
}

#[test]
fn the_degraded_gate_refuses_a_surplus_argument() {
    larch(&["implement", "step-0-degraded-gate", "surplus"])
        .assert()
        .code(2)
        .stderr(predicates_str("unrecognized arguments: surplus"));
}

#[test]
fn preflight_refuses_a_command_line_without_its_required_options() {
    larch(&["implement", "preflight"])
        .assert()
        .code(2)
        .stderr(predicates_str(
            "the following arguments are required: --issue, --preflight-tmpdir",
        ));
}

#[test]
fn preflight_refuses_a_non_numeric_issue() {
    let fixture = TempDir::new().expect("fixture");

    larch(&[
        "implement",
        "preflight",
        "--issue",
        "12a",
        "--preflight-tmpdir",
    ])
    .arg(fixture.path())
    .assert()
    .code(2)
    .stderr(
        "usage: cli.py implement preflight --issue N [--repo R] [--force] --preflight-tmpdir D\n",
    );
}

/// `-f` is the short spelling of `--force`, so it must clear argv validation
/// and reach composition rather than refuse as an unrecognized argument.
#[test]
fn test_preflight_force_short_flag_missing_plan_refuses_without_fallback() {
    let fixture = TempDir::new().expect("fixture");

    larch(&["implement", "preflight", "-f", "--issue", "12"])
        .arg("--preflight-tmpdir")
        .arg(fixture.path())
        .env_remove("CLAUDE_PLUGIN_ROOT")
        .assert()
        .code(2)
        .stdout(predicates_str("cannot resolve CLAUDE_PLUGIN_ROOT"));
}

#[test]
fn preflight_serves_its_help_text_on_stdout() {
    larch(&["implement", "preflight", "--help"])
        .assert()
        .success()
        .stdout(predicates_str(
            "usage: cli.py implement preflight --issue N",
        ));
}

fn read(path: &Path) -> String {
    fs::read_to_string(path).unwrap_or_else(|error| panic!("read {}: {error}", path.display()))
}

fn predicates_str(needle: &str) -> predicates::str::ContainsPredicate {
    predicates::str::contains(needle)
}
