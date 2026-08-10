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
}
