//! Black-box fixtures for the `repo size` developer report.

use std::{fs, path::Path, process::Command as StdCommand};

use assert_cmd::Command;
use tempfile::TempDir;

const MIXED_REPORT: &str = "\
┌───────────────────────────────────────────────┬───────┬────────┐
│                   Category                    │ Files │ Lines  │
├───────────────────────────────────────────────┼───────┼────────┤
│ Bash scripts (runtime, non-test *.sh)         │     1 │      1 │
├───────────────────────────────────────────────┼───────┼────────┤
│ Bash tests (test-*.sh)                        │     1 │      2 │
├───────────────────────────────────────────────┼───────┼────────┤
│ Python code (non-test *.py)                   │     1 │      3 │
├───────────────────────────────────────────────┼───────┼────────┤
│ Python tests (test_*.py + tests/)             │     1 │      1 │
├───────────────────────────────────────────────┼───────┼────────┤
│ Rust code (non-test *.rs)                     │     2 │      3 │
├───────────────────────────────────────────────┼───────┼────────┤
│ Rust tests (#[cfg(test)] + tests/ + benches/) │     3 │      8 │
├───────────────────────────────────────────────┼───────┼────────┤
│ All Markdown (*.md)                           │     3 │      3 │
└───────────────────────────────────────────────┴───────┴────────┘

Repo (tracked content):          0.00 MB
larch-logs/ total:               0.00 MB   ( 2.8% of repo)
  ├─ implement:                  0.00 MB   (33.3% of run-logs)
  ├─ design:                     0.00 MB   (33.3% of run-logs)
  └─ rest (shared, etc.):        0.00 MB   (33.3% of run-logs)
Repo minus larch-logs:           0.00 MB   (97.2% of repo)
";

const EMPTY_REPORT: &str = "\
┌───────────────────────────────────────────────┬───────┬────────┐
│                   Category                    │ Files │ Lines  │
├───────────────────────────────────────────────┼───────┼────────┤
│ Bash scripts (runtime, non-test *.sh)         │     0 │      0 │
├───────────────────────────────────────────────┼───────┼────────┤
│ Bash tests (test-*.sh)                        │     0 │      0 │
├───────────────────────────────────────────────┼───────┼────────┤
│ Python code (non-test *.py)                   │     0 │      0 │
├───────────────────────────────────────────────┼───────┼────────┤
│ Python tests (test_*.py + tests/)             │     0 │      0 │
├───────────────────────────────────────────────┼───────┼────────┤
│ Rust code (non-test *.rs)                     │     0 │      0 │
├───────────────────────────────────────────────┼───────┼────────┤
│ Rust tests (#[cfg(test)] + tests/ + benches/) │     0 │      0 │
├───────────────────────────────────────────────┼───────┼────────┤
│ All Markdown (*.md)                           │     0 │      0 │
└───────────────────────────────────────────────┴───────┴────────┘

Repo (tracked content):          0.00 MB
larch-logs/ total:               0.00 MB   ( 0.0% of repo)
  ├─ implement:                  0.00 MB   ( 0.0% of run-logs)
  ├─ design:                     0.00 MB   ( 0.0% of run-logs)
  └─ rest (shared, etc.):        0.00 MB   ( 0.0% of run-logs)
Repo minus larch-logs:           0.00 MB   ( 0.0% of repo)
";

fn larch() -> Command {
    Command::cargo_bin("larch").expect("larch binary should build")
}

fn git(root: &Path, args: &[&str]) {
    let status = StdCommand::new("git")
        .args(args)
        .current_dir(root)
        .status()
        .expect("git should run");
    assert!(status.success(), "git {args:?} failed");
}

fn repository() -> TempDir {
    let temporary = TempDir::new().expect("temporary repository");
    git(temporary.path(), &["init", "-q"]);
    temporary
}

fn write(root: &Path, relative: &str, content: &[u8]) {
    let path = root.join(relative);
    fs::create_dir_all(path.parent().expect("fixture parent")).expect("create fixture parent");
    fs::write(path, content).expect("write fixture");
}

#[test]
fn mixed_repository_matches_the_golden_fixture() {
    let repository = repository();
    let root = repository.path();

    write(root, "scripts/run.sh", b"run\n");
    write(root, "scripts/test-unit.sh", b"first\nsecond\n");
    write(root, "python/tool.py", b"one\ntwo\nthree\n");
    write(root, "python/test_tool.py", b"test\n");
    write(
        root,
        "crates/example/src/lib.rs",
        b"fn production() {}\n\
          #[cfg(test)]\n\
          mod tests {\n\
              #[test]\n\
              fn unit() {}\n\
          }\n",
    );
    write(
        root,
        "crates/example/src/main.rs",
        b"fn first() {}\nfn second() {}\n",
    );
    write(
        root,
        "crates/example/tests/integration.rs",
        b"fn first() {}\nfn second() {}\n",
    );
    write(
        root,
        "crates/example/benches/throughput.rs",
        b"fn benchmark() {}\n",
    );
    write(root, "docs/guide.md", b"guide\n");
    write(root, "docs/space name.md", b"space\n");
    write(root, "docs/binary.md", b"\xff\n");
    write(root, "node_modules/pkg/ignored.md", b"ignored\nagain\n");
    write(root, "larch-logs/implement/run.md", b"i\n");
    write(root, "larch-logs/design/run.md", b"d\n");
    write(root, "larch-logs/shared.bin", b"\xff\n");
    write(root, "assets/data.bin", b"\xff");
    git(root, &["add", "-A"]);

    larch()
        .args(["repo", "size"])
        .current_dir(root)
        .assert()
        .success()
        .stdout(MIXED_REPORT)
        .stderr("");
}

#[test]
fn empty_repository_has_the_zero_total_golden_fixture() {
    let repository = repository();

    larch()
        .args(["repo", "size"])
        .current_dir(repository.path())
        .assert()
        .success()
        .stdout(EMPTY_REPORT)
        .stderr("");
}
