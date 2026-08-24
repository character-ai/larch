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

fn assert_contains_all(source: &str, needles: &[&str]) {
    for needle in needles {
        assert!(source.contains(needle), "missing {needle:?}");
    }
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

#[test]
fn required_rust_checks_cover_each_execution_shape_without_a_serial_full_gate() {
    let root = repository_root();
    let workflow = fs::read_to_string(root.join(".github/workflows/ci.yaml"))
        .expect("read CI workflow");
    let coverage = section(&workflow, "\n  rust-coverage:");
    let gate = section(&workflow, "\n  rust-gate:");

    assert!(!workflow.contains("\n  rust-full:\n"));
    assert_contains_all(
        &coverage,
        &[
            "name: rust-coverage",
            "needs: [rust-selection, rust-full-lcov-tool, rust-full-shards, rust-full-policy, rust-partial, rust-skip]",
            "if: always()",
            "FULL_SHARDS_RESULT",
            "FULL_POLICY_RESULT",
            "FULL_TOOL_RESULT",
            "PARTIAL_RESULT",
            "SELECTION_RESULT",
            "SKIP_RESULT",
            "case \"$mode\" in",
            "full)",
            "partial)",
            "skip)",
        ],
    );
    assert_contains_all(
        &gate,
        &[
            "name: rust-gate",
            "needs: [rust-lint, rust-deny, rust-full-shards, rust-full-policy, rust-partial, rust-skip]",
            "if: always()",
            "[ \"$lint_result\" = success ]",
            "[ \"$deny_result\" = success ]",
            "success:success:skipped:skipped|skipped:skipped:success:skipped|skipped:skipped:skipped:success",
        ],
    );
    assert!(!gate.contains("needs: [rust-coverage"));
    assert!(!gate.contains("coverage_result"));
}

#[test]
fn rust_coverage_merges_every_report_with_a_prefetched_pinned_lcov_runtime() {
    let root = repository_root();
    let workflow = fs::read_to_string(root.join(".github/workflows/ci.yaml"))
        .expect("read CI workflow");
    let tool = section(&workflow, "\n  rust-full-lcov-tool:");
    let coverage = section(&workflow, "\n  rust-coverage:");

    assert_contains_all(
        &tool,
        &[
            "name: rust-full LCOV tool",
            "needs: [rust-selection]",
            "LCOV_PACKAGE_VERSION: 2.0-4ubuntu2",
            "apt-get install --yes --no-install-recommends",
            "dpkg-query --listfiles",
            "--no-recursion --verbatim-files-from",
            "sha256sum lcov-runtime.tar.gz lcov-runtime.env packages.txt",
            "name: rust-coverage-lcov-tools",
        ],
    );
    assert_eq!(coverage.matches("actions/download-artifact@").count(), 1);
    assert_contains_all(
        &coverage,
        &[
            "RUST_COVERAGE_MIN_LINES: \"88.000\"",
            "pattern: rust-coverage-lcov-*",
            "tool_root=\"$RUNNER_TEMP/rust-coverage-shards/rust-coverage-lcov-tools\"",
            "sha256sum --check --strict SHA256SUMS",
            "test \"$archive_bytes\" -le 67108864",
            "test \"$archive_entry_count\" -le 16384",
            "unsafe LCOV runtime archive entry",
            "lcov: LCOV version 2.0-1",
            "LCOV_RUNTIME_BIN",
            "expected_report_count=\"$((RUST_COVERAGE_SHARD_COUNT + 1))\"",
            "policy_report=\"$shard_root/rust-coverage-lcov-policy/lcov.info\"",
            "rust-coverage-lcov-shard-$shard_index/lcov.info",
            "\"$LCOV_RUNTIME_BIN\" --parallel \"$expected_report_count\"",
            "LC_ALL=C awk -F: -v minimum=\"$RUST_COVERAGE_MIN_LINES\"",
            "malformed || found_records != hit_records || found == 0 || hit > found",
            "rate = 100 * hit / found",
            "if (rate < minimum)",
            "name: rust-coverage-lcov",
        ],
    );
    assert!(!coverage.contains("apt-get install"));
    assert!(!coverage.contains("lcov --summary"));
}
