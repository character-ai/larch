const MAKEFILE: &str = include_str!("../../../Makefile");

#[test]
fn harness_mark_uses_the_dependency_free_timer_and_separate_target_directory() {
    let definition = MAKEFILE
        .lines()
        .find(|line| line.starts_with("HARNESS_MARK ?="))
        .expect("Makefile should define HARNESS_MARK");
    assert!(
        definition.contains("LARCH_HARNESS_BOOTSTRAP_START_NS"),
        "{definition}"
    );
    assert!(
        definition.contains("LARCH_HARNESS_BOOTSTRAP_KIND"),
        "{definition}"
    );
    assert!(
        definition.contains("rustc --edition=2024 --crate-name larch_harness_mark"),
        "{definition}"
    );
    assert!(
        definition.contains("target/harness-mark/larch-harness-mark"),
        "{definition}"
    );
    assert!(
        definition.contains("mktemp -d target/harness-mark/.build.XXXXXX"),
        "{definition}"
    );
    assert!(
        definition.contains("mv \"$$build_directory/larch-harness-mark\" \"$$timer\""),
        "{definition}"
    );
    assert!(!definition.contains("cargo run"), "{definition}");
    assert!(!definition.contains("larch-cli"), "{definition}");
    assert!(!definition.contains("target/debug/larch"), "{definition}");
    assert!(!definition.contains("python"), "{definition}");
}

#[test]
fn harness_mark_classifies_bootstrap_from_the_rebuild_predicate_before_building() {
    let definition = MAKEFILE
        .lines()
        .find(|line| line.starts_with("HARNESS_MARK ?="))
        .expect("Makefile should define HARNESS_MARK");
    let started = definition
        .find("LARCH_HARNESS_BOOTSTRAP_START_NS=")
        .expect("Makefile should sample bootstrap start");
    let rebuild_predicate = definition
        .find("if test ! -x \"$$timer\"")
        .expect("Makefile should classify bootstrap from its rebuild predicate");
    let kind = definition
        .find("LARCH_HARNESS_BOOTSTRAP_KIND=cold")
        .expect("Makefile should mark a rebuild as cold");
    let build = definition
        .find("rustc --edition=2024 --crate-name larch_harness_mark")
        .expect("Makefile should build only after classification");

    assert!(
        started < rebuild_predicate && rebuild_predicate < kind && kind < build,
        "{definition}"
    );
    assert!(
        definition.contains("if test \"$$LARCH_HARNESS_BOOTSTRAP_KIND\" = cold; then"),
        "{definition}"
    );
}
