mod support;

use std::fmt::Write as _;

use predicates::prelude::*;
use support::TempRepo;

const COMMANDS: [(&str, &str, u64, Option<&str>); 19] = [
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
    let mut output = String::from("schema_version = 1\n");
    for (domain, verb, issue, fixture) in COMMANDS {
        let (python_module, python_function) = python_target(domain, verb);
        let fixture = fixture
            .map(|value| format!("clean_install_test = \"{value}\"\n"))
            .unwrap_or_default();
        let _ = write!(
            output,
            r#"
[[commands]]
domain = "{domain}"
verb = "{verb}"
python_module = "{python_module}"
python_function = "{python_function}"
machine_stdout = false
owner = "rust"
implementation_parity = "complete"
consumer_cutover = "complete"
python_removal = "complete"
migration_issue = {issue}
{fixture}"#,
        );
    }
    output
}

fn python_target(domain: &str, verb: &str) -> (&'static str, &'static str) {
    match (domain, verb) {
        ("plugin", "read-version") => ("larch.release.version_bump", "read_plugin_version_main"),
        ("release", "asset-candidate") => ("larch.release.assets", "candidate_main"),
        ("release", "asset-run") => ("larch.release.release_finish", "asset_run_main"),
        ("release", "classify-bump") => ("larch.release.version_bump", "classify_bump_main"),
        ("release", "collect-assets") => ("larch.release.assets", "collect_main"),
        ("release", "ensure-policy") => ("larch.release.release_finish", "ensure_policy_main"),
        ("release", "finish") => ("larch.release.release_finish", "main"),
        ("release", "package-asset") => ("larch.release.assets", "package_main"),
        ("release", "plugin-runtime") => ("larch.release.plugin_runtime", "main"),
        ("release", "prepare") => ("larch.release.release_prepare", "main"),
        ("release", "promote") => ("larch.release.promote_release", "promote_main"),
        ("release", "promote-latest") => ("larch.release.promote_release", "promote_latest_main"),
        ("release", "set-version") => ("larch.release.version_bump", "set_version_main"),
        ("release", "stage") => ("larch.release.release_finish", "stage_main"),
        ("release", "validate-assets") => ("larch.release.assets", "validate_main"),
        ("release", "validate-draft") => ("larch.release.release_finish", "validate_draft_main"),
        ("upgrade-larch", "release-step7-root") => {
            ("larch.core.upgrade_larch", "release_step7_root_main")
        }
        ("upgrade-larch", "run") => ("larch.core.upgrade_larch", "run_main"),
        ("upgrade-larch", "sparse-dirs") => ("larch.core.upgrade_larch", "sparse_dirs_main"),
        _ => panic!("unexpected fixture selector {domain} {verb}"),
    }
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
        .replacen("owner = \"rust\"", "owner = \"python\"", 1)
        .replacen(
            "python_module = \"larch.release.version_bump\"",
            "python_module = \"larch.release.redirected\"",
            1,
        )
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
            "non-final release Python-free command row: plugin read-version",
        ))
        .stdout(predicate::str::contains(
            "release retired Python target drift: plugin read-version",
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
        b"schema_version = 1\ncommands = []\n",
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
