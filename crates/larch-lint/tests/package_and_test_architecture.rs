mod support;

use predicates::prelude::*;
use support::TempRepo;

fn write_workspace(repository: &TempRepo, core_dependency: &str) {
    repository.write(
        "Cargo.toml",
        b"[workspace]\nmembers = [\"crates/larch-io\", \"crates/larch-core\", \"crates/larch-cli\"]\nresolver = \"3\"\n",
    );
    repository.write(
        "crates/larch-io/Cargo.toml",
        b"[package]\nname = \"larch-io\"\nversion = \"0.1.0\"\nedition = \"2024\"\n",
    );
    repository.write("crates/larch-io/src/lib.rs", b"");
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
        .stdout(
            "crates/larch-core/Cargo.toml:1: package larch-core depends on higher layer larch-cli\n",
        )
        .stderr(predicate::str::is_empty());
}

#[test]
fn package_layering_allows_downward_and_test_only_dependencies() {
    let repository = TempRepo::new();
    write_workspace(
        &repository,
        "[dependencies]\nlarch-io = { path = \"../larch-io\" }\n[dev-dependencies]\nlarch-cli = { path = \"../larch-cli\" }\n",
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
