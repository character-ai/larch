use std::{fs, path::Path};

use assert_cmd::Command;
use predicates::prelude::*;

const ROOT_HELP: &str = "\
Larch workflow automation

Usage: larch <COMMAND>

Commands:
  example  Non-production commands that exercise dispatcher wiring
  help     Print this message or the help of the given subcommand(s)

Options:
  -h, --help     Print help
  -V, --version  Print version
";

const EXAMPLE_HELP: &str = "\
Non-production commands that exercise dispatcher wiring

Usage: larch example <COMMAND>

Commands:
  echo  Print a message through the core library
  help  Print this message or the help of the given subcommand(s)

Options:
  -h, --help  Print help
";

fn larch() -> Command {
    Command::cargo_bin("larch").expect("larch binary should build")
}

#[test]
fn help_has_pinned_output_and_success_exit() {
    larch()
        .arg("--help")
        .assert()
        .code(0)
        .stdout(ROOT_HELP)
        .stderr("");
}

#[test]
fn version_reports_the_workspace_version() {
    larch()
        .arg("--version")
        .assert()
        .success()
        .stderr("")
        .stdout(predicate::eq(format!(
            "larch {}\n",
            env!("CARGO_PKG_VERSION")
        )));
}

#[test]
fn compiled_version_matches_the_plugin_release_version() {
    let plugin_manifest_path =
        Path::new(env!("CARGO_MANIFEST_DIR")).join("../../.claude-plugin/plugin.json");
    let plugin_manifest =
        fs::read_to_string(&plugin_manifest_path).expect("plugin manifest should be readable");
    let plugin_manifest: serde_json::Value =
        serde_json::from_str(&plugin_manifest).expect("plugin manifest should contain valid JSON");

    assert_eq!(
        plugin_manifest["version"].as_str(),
        Some(env!("CARGO_PKG_VERSION")),
        "workspace package version must match .claude-plugin/plugin.json"
    );
}

#[test]
fn example_echo_dispatches_through_the_core_library() {
    larch()
        .args(["example", "echo", "library wiring"])
        .assert()
        .success()
        .stdout("library wiring\n")
        .stderr("");
}

#[test]
fn missing_domain_has_pinned_help_and_usage_exit() {
    larch().assert().code(2).stdout("").stderr(ROOT_HELP);
}

#[test]
fn unknown_domain_has_pinned_error_and_does_not_fallback() {
    larch()
        .arg("python-command")
        .assert()
        .code(2)
        .stdout("")
        .stderr("error: unrecognized subcommand\n");
}

#[test]
fn missing_verb_has_pinned_help_and_usage_exit() {
    larch()
        .arg("example")
        .assert()
        .code(2)
        .stdout("")
        .stderr(EXAMPLE_HELP);
}

#[test]
fn unknown_verb_has_pinned_error_and_does_not_fallback() {
    larch()
        .args(["example", "python-verb"])
        .assert()
        .code(2)
        .stdout("")
        .stderr("error: unrecognized subcommand\n");
}

#[test]
fn missing_argument_has_pinned_error_and_usage_exit() {
    larch()
        .args(["example", "echo"])
        .assert()
        .code(2)
        .stdout("")
        .stderr("error: one or more required arguments were not provided\n");
}
