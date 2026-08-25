use crate::support;

use std::fmt::Write as _;

use predicates::prelude::*;
use support::TempRepo;

const COMMANDS: [(&str, &str, u64, Option<&str>); 20] = [
    (
        "plugin",
        "read-version",
        7749,
        Some("clean-install-plugin-read-version"),
    ),
    (
        "release",
        "asset-candidate",
        7747,
        Some("clean-install-release-asset-candidate"),
    ),
    ("release", "asset-run", 7751, None),
    (
        "release",
        "classify-bump",
        7749,
        Some("clean-install-release-classify-bump"),
    ),
    (
        "release",
        "collect-assets",
        7747,
        Some("clean-install-release-collect-assets"),
    ),
    ("release", "ensure-policy", 7751, None),
    ("release", "finish", 7752, None),
    (
        "release",
        "package-asset",
        7747,
        Some("clean-install-release-package-asset"),
    ),
    (
        "release",
        "plugin-runtime",
        7748,
        Some("clean-install-release-plugin-runtime"),
    ),
    (
        "release",
        "prepare",
        7749,
        Some("clean-install-release-prepare"),
    ),
    ("release", "promote", 7752, None),
    ("release", "promote-latest", 7752, None),
    (
        "release",
        "reconcile-notes",
        7749,
        Some("clean-install-release-reconcile-notes"),
    ),
    (
        "release",
        "set-version",
        7750,
        Some("clean-install-release-set-version"),
    ),
    ("release", "stage", 7751, None),
    (
        "release",
        "validate-assets",
        7747,
        Some("clean-install-release-validate-assets"),
    ),
    ("release", "validate-draft", 7751, None),
    (
        "upgrade-larch",
        "release-step7-root",
        7753,
        Some("clean-install-upgrade-larch-release-step7-root"),
    ),
    (
        "upgrade-larch",
        "run",
        7753,
        Some("clean-install-upgrade-larch-run"),
    ),
    (
        "upgrade-larch",
        "sparse-dirs",
        7753,
        Some("clean-install-upgrade-larch-sparse-dirs"),
    ),
];

fn registry() -> String {
    let mut output = String::from("schema_version = 3\n");
    for (domain, verb, issue, fixture) in COMMANDS {
        let fixture = fixture
            .map(|value| format!("clean_install_test = \"{value}\"\n"))
            .unwrap_or_default();
        let _ = write!(
            output,
            r#"
[[commands]]
domain = "{domain}"
verb = "{verb}"
machine_stdout = false
owner = "rust"
planning_issue = 7674
migration_issue = {issue}
{fixture}"#,
        );
    }
    output
}

fn prepare(repository: &TempRepo) {
    repository.write(
        "crates/larch-lint/data/command-registry.toml",
        registry().as_bytes(),
    );
    repository.write(
        "crates/larch-cli/src/release_assets.rs",
        b"pub struct ReleaseAssets;\n",
    );
    repository.write(
        "python/larch/cli.py",
        b"_REGISTRY = {('other', 'run'): ('other', 'main', False)}\n",
    );
    repository.write(
        ".claude/skills/release/SKILL.md",
        b"```bash\n\"$PWD/scripts/larch.sh\" release finish --repo character-ai/larch\n```\n",
    );
    repository.write(
        "skills/upgrade-larch/SKILL.md",
        b"```bash\n\"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh\" upgrade-larch run\n```\n",
    );
    repository.write(
        ".github/workflows/rust-release-assets.yaml",
        b"run: ./target/release/larch release asset-candidate\n",
    );
    repository.write(
        "scripts/larch.sh",
        b"#!/usr/bin/env bash\nexec \"$plugin_root/bin/larch\" \"$@\"\n",
    );
}

#[test]
fn accepts_the_complete_python_free_boundary() {
    let repository = TempRepo::new();
    prepare(&repository);
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "release-python-free"])
        .assert()
        .success()
        .stdout("")
        .stderr("");
}

#[test]
fn rejects_non_final_missing_and_unapproved_rows() {
    let repository = TempRepo::new();
    prepare(&repository);
    let stale = registry()
        .replacen("owner = \"rust\"", "owner = \"retired\"", 1)
        .replace(
            "[[commands]]\ndomain = \"release\"\nverb = \"finish\"",
            "[[commands]]\ndomain = \"release\"\nverb = \"unowned\"",
        );
    repository.write(
        "crates/larch-lint/data/command-registry.toml",
        stale.as_bytes(),
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "release-python-free"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "non-final release command row: plugin read-version",
        ))
        .stdout(predicate::str::contains(
            "unapproved release-owned command row: release unowned",
        ))
        .stdout(predicate::str::contains(
            "missing final release-owned command row: release finish",
        ))
        .stderr("");
}

#[test]
fn rejects_python_registration_and_implementation() {
    let repository = TempRepo::new();
    prepare(&repository);
    repository.write(
        "python/larch/cli.py",
        b"_REGISTRY = {(\"release\", \"asset-candidate\"): (\"larch.release.retired\", \"asset_candidate_main\", False)}\n",
    );
    repository.write(
        "python/larch/release/assets.py",
        b"def candidate_main ():\n    pass\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "release-python-free"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "release-owned command remains registered in Python",
        ))
        .stdout(predicate::str::contains(
            "superseded release Python implementation remains",
        ))
        .stderr("");
}

#[test]
fn rejects_python_caller_and_direct_binary_bypasses() {
    let repository = TempRepo::new();
    prepare(&repository);
    repository.write(
        "skills/upgrade-larch/SKILL.md",
        b"```bash\npython3 python/cli.py upgrade-larch run\n\"$CLAUDE_PLUGIN_ROOT/bin/larch\" upgrade-larch run\n```\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "release-python-free"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "release command caller bypasses scripts/larch.sh: upgrade-larch run",
        ))
        .stdout(predicate::str::contains(
            "direct bin/larch release runtime entrypoint",
        ))
        .stderr("");
}

#[test]
fn rejects_direct_gh_process_fallbacks() {
    let repository = TempRepo::new();
    prepare(&repository);
    repository.write(
        "crates/larch-cli/src/release_bad.rs",
        b"let output = std::process::Command::new(\n    \"gh\",\n).arg(\"release\").output();\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "release-python-free"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "release implementation invokes gh directly; use the typed GitHub service",
        ))
        .stderr("");
}

#[test]
fn rejects_removal_of_the_complete_command_set() {
    let repository = TempRepo::new();
    prepare(&repository);
    repository.write(
        "crates/larch-lint/data/command-registry.toml",
        b"schema_version = 2\ncommands = []\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "release-python-free"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains(
            "missing final release-owned command row: release finish",
        ))
        .stdout(predicate::str::contains(
            "missing final release-owned command row: upgrade-larch run",
        ))
        .stderr("");
}
