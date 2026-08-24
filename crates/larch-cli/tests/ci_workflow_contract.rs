use std::{fs, path::Path};

fn repository_root() -> std::path::PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(Path::parent)
        .expect("workspace root")
        .to_path_buf()
}

fn section(source: &str, heading: &str) -> String {
    source
        .split_once(heading)
        .unwrap_or_else(|| panic!("missing workflow section {heading:?}"))
        .1
        .lines()
        .take_while(|line| line.is_empty() || line.starts_with("    "))
        .collect::<Vec<_>>()
        .join("\n")
}

fn assert_tree_lacks(path: &Path, needle: &str) {
    for entry in fs::read_dir(path).expect("read test tree") {
        let entry = entry.expect("read test-tree entry");
        let file_type = entry.file_type().expect("read test-tree entry type");
        if file_type.is_dir() {
            assert_tree_lacks(&entry.path(), needle);
        } else if file_type.is_file() {
            let source = fs::read(entry.path()).expect("read test source");
            assert!(
                !source
                    .windows(needle.len())
                    .any(|window| window == needle.as_bytes()),
                "{} retains {needle:?}",
                entry.path().display()
            );
        }
    }
}

#[test]
fn selected_rust_bootstrap_job_replaces_the_pytest_integration_lane() {
    let root = repository_root();
    let workflow = fs::read_to_string(root.join(".github/workflows/ci.yaml"))
        .expect("read CI workflow");
    let integration = section(&workflow, "\n  python-rust-integration:");

    for required in [
        "name: python-tests-gate",
        "needs: [rust-coverage, python-tests]",
        "if: always()",
        "Verify selected Rust integration artifact",
        "sha256sum --check --strict larch.sha256",
        "LARCH_TEST_RUST_BINARY_SHA256",
        "bash scripts/test-rust-integration-consumer.sh",
    ] {
        assert!(integration.contains(required), "missing {required:?}");
    }
    for retired in [
        "actions/setup-python",
        "requirements-test.txt",
        "python3 -m pytest",
        "-m rust_integration",
    ] {
        assert!(!integration.contains(retired), "retains {retired:?}");
    }

    let python_tests = section(&workflow, "\n  python-tests:");
    assert!(!python_tests.contains("PYTEST_ADDOPTS"));
    let makefile = fs::read_to_string(root.join("Makefile")).expect("read Makefile");
    assert!(!makefile.contains("python3 -m pytest"));
    assert_tree_lacks(&root.join("python/tests"), "rust_integration");
}
