mod support;

use predicates::prelude::*;
use support::TempRepo;

fn write_workspace(repository: &TempRepo, core_dependency: &str) {
    repository.write(
        "Cargo.toml",
        b"[workspace]\nmembers = [\"crates/larch-adapters\", \"crates/larch-core\", \"crates/larch-cli\"]\nresolver = \"3\"\n",
    );
    repository.write(
        "crates/larch-adapters/Cargo.toml",
        b"[package]\nname = \"larch-adapters\"\nversion = \"0.1.0\"\nedition = \"2024\"\n",
    );
    repository.write("crates/larch-adapters/src/lib.rs", b"");
    repository.write(
        "crates/larch-cli/Cargo.toml",
        b"[package]\nname = \"larch-cli\"\nversion = \"0.1.0\"\nedition = \"2024\"\n",
    );
    repository.write("crates/larch-cli/src/lib.rs", b"");
    repository.write(
        "crates/larch-core/Cargo.toml",
        format!(
            "[package]\nname = \"larch-core\"\nversion = \"0.1.0\"\nedition = \"2024\"\n{core_dependency}"
        )
        .as_bytes(),
    );
    repository.write("crates/larch-core/src/lib.rs", b"");
}

#[test]
fn package_layering_rejects_a_renamed_normal_dependency_on_a_higher_tier() {
    let repository = TempRepo::new();
    write_workspace(
        &repository,
        "[dependencies]\nlarch_cli = { package = \"larch-cli\", path = \"../larch-cli\" }\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "layering"])
        .assert()
        .code(1)
        .stdout("crates/larch-core/Cargo.toml:1: package larch-core may not depend on larch-cli\n")
        .stderr(predicate::str::is_empty());
}

#[test]
fn package_layering_allows_downward_and_test_only_dependencies() {
    let repository = TempRepo::new();
    write_workspace(
        &repository,
        "[dev-dependencies]\nlarch-cli = { path = \"../larch-cli\" }\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "layering"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}

#[test]
fn package_layering_rejects_product_dependencies_on_repository_tooling() {
    let repository = TempRepo::new();
    repository.write(
        "Cargo.toml",
        b"[workspace]\nmembers = [\"crates/larch-cli\", \"crates/larch-lint\"]\nresolver = \"3\"\n",
    );
    repository.write(
        "crates/larch-cli/Cargo.toml",
        b"[package]\nname = \"larch-cli\"\nversion = \"0.1.0\"\nedition = \"2024\"\n[dependencies]\nlarch-lint = { path = \"../larch-lint\" }\n",
    );
    repository.write("crates/larch-cli/src/lib.rs", b"");
    repository.write(
        "crates/larch-lint/Cargo.toml",
        b"[package]\nname = \"larch-lint\"\nversion = \"0.1.0\"\nedition = \"2024\"\n",
    );
    repository.write("crates/larch-lint/src/lib.rs", b"");
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "layering"])
        .assert()
        .code(1)
        .stdout("crates/larch-cli/Cargo.toml:1: package larch-cli may not depend on larch-lint\n")
        .stderr(predicate::str::is_empty());
}

#[test]
fn workspace_dependency_policy_allows_inherited_dependencies_in_all_sections() {
    let repository = TempRepo::new();
    repository.write(
        "crates/larch-core/Cargo.toml",
        b"[dependencies]\nserde.workspace = true\n[dev-dependencies]\ntempfile.workspace = true\n[target.'cfg(unix)'.build-dependencies]\ncc.workspace = true\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "workspace-dependency-policy"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}

#[test]
fn workspace_dependency_policy_rejects_member_local_dependency_settings() {
    let repository = TempRepo::new();
    repository.write(
        "crates/larch-core/Cargo.toml",
        b"[dependencies]\nserde = { version = \"1\", features = [\"derive\"] }\n[dev-dependencies]\ntempfile = \"3\"\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "workspace-dependency-policy"])
        .assert()
        .code(1)
        .stdout(
            "crates/larch-core/Cargo.toml:1: dependency serde must inherit its version and features from [workspace.dependencies]\n\
             crates/larch-core/Cargo.toml:1: dependency tempfile must inherit its version and features from [workspace.dependencies]\n",
        )
        .stderr(predicate::str::is_empty());
}

#[test]
fn workspace_dependency_policy_rejects_member_local_package_versions() {
    let repository = TempRepo::new();
    repository.write(
        "crates/larch-core/Cargo.toml",
        b"[package]\nname = \"larch-core\"\nversion = \"0.1.0\"\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "workspace-dependency-policy"])
        .assert()
        .code(1)
        .stdout(
            "crates/larch-core/Cargo.toml:1: package version must inherit from [workspace.package]\n",
        )
        .stderr(predicate::str::is_empty());
}

#[test]
fn workspace_dependency_policy_requires_disabled_registry_defaults() {
    let repository = TempRepo::new();
    repository.write(
        "Cargo.toml",
        b"[workspace]\n[workspace.dependencies]\nlarch-core = { path = \"crates/larch-core\" }\nserde = { version = \"1\" }\ntoml = { version = \"1\", default-features = false }\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "workspace-dependency-policy"])
        .assert()
        .code(1)
        .stdout("Cargo.toml:1: workspace dependency serde must set default-features = false\n")
        .stderr(predicate::str::is_empty());
}

#[test]
fn test_layout_requires_cfg_test_for_crate_local_tests_and_allows_integration_tests() {
    let repository = TempRepo::new();
    repository.write(
        "crates/larch-core/src/lib.rs",
        b"#[test]\nfn loose() {}\n\n#[cfg(test)]\nmod tests {\n    #[test]\n    fn local() {}\n}\n",
    );
    repository.write(
        "crates/larch-core/tests/integration.rs",
        b"#[test]\nfn integration() {}\n",
    );
    repository.write(
        "crates/larch-core/src/tests/helper.rs",
        b"#[test]\nfn misplaced() {}\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "flat-tests"])
        .assert()
        .code(1)
        .stdout(
            "crates/larch-core/src/lib.rs:2: test is outside a #[cfg(test)] crate-local module\n\
             crates/larch-core/src/tests/helper.rs:2: test is outside a #[cfg(test)] crate-local module\n",
        )
        .stderr(predicate::str::is_empty());
}

#[test]
fn test_layout_ignores_fixtures_and_honors_reasoned_suppressions() {
    let repository = TempRepo::new();
    repository.write(
        "crates/larch-core/src/lib.rs",
        b"#[test]\nfn loose() {} // lint-test-layout: ok fixture proves the narrow escape hatch\n",
    );
    repository.write("crates/larch-core/tests/fixtures/not-rust.rs", b"fn {");
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "flat-tests"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}

#[test]
fn test_layout_rejects_a_suppression_without_a_reason() {
    let repository = TempRepo::new();
    repository.write(
        "crates/larch-core/src/lib.rs",
        b"#[test]\nfn loose() {} // lint-test-layout: ok\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "flat-tests"])
        .assert()
        .code(2)
        .stdout(predicate::str::is_empty())
        .stderr("larch-lint: error: suppression lint-test-layout lacks a reason\n");
}

#[test]
fn renderer_rule_accepts_reexports_renamed_modules_and_aliases_from_golden_tests() {
    let repository = TempRepo::new();
    repository.write(
        "crates/larch-report/src/lib.rs",
        b"#[path = \"renderer.rs\"]\nmod renamed_renderer;\npub use renamed_renderer::_render_progress;\n",
    );
    repository.write(
        "crates/larch-report/src/renderer.rs",
        b"fn _render_progress() -> String { String::new() }\n",
    );
    repository.write(
        "crates/larch-report/tests/progress_golden.rs",
        b"use larch_report::_render_progress as golden;\n#[test]\nfn progress_golden() { assert_eq!(golden(), \"\"); }\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "renderer-golden-tests"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}

#[test]
fn renderer_rule_requires_explicit_golden_references_and_allows_suppression() {
    let repository = TempRepo::new();
    repository.write(
        "crates/larch-report/src/report.rs",
        b"fn _render_missing() -> String { String::new() }\nfn _render_suppressed() -> String { String::new() } // lint-renderer-golden-tests: ok fixture-only report helper\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "renderer-golden-tests"])
        .assert()
        .code(1)
        .stdout(
            "crates/larch-report/src/report.rs:1: renderer helper _render_missing lacks an explicit golden-test reference\n",
        )
        .stderr(predicate::str::is_empty());
}

#[test]
fn renderer_rule_accepts_references_from_crate_local_test_modules() {
    let repository = TempRepo::new();
    repository.write(
        "crates/larch-report/src/report.rs",
        b"fn _render_progress() -> String { String::new() }\n#[cfg(test)]\nmod tests {\n    use super::_render_progress;\n    #[test]\n    fn progress_golden() { assert_eq!(_render_progress(), \"\"); }\n}\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "renderer-golden-tests"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());
}
