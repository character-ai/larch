mod support;

use predicates::prelude::*;
use support::TempRepo;

fn run(repository: &TempRepo) -> assert_cmd::assert::Assert {
    TempRepo::command_from(repository.path())
        .args(["rule", "run-log-corpus-walkers"])
        .assert()
}

#[test]
fn raw_read_dir_over_a_corpus_root_is_reported() {
    let repository = TempRepo::new();
    repository.write(
        "crates/app/src/lib.rs",
        b"pub fn scan(log_root: &std::path::Path) {\n    \
          let _ = std::fs::read_dir(log_root);\n}\n",
    );
    repository.commit_all();

    run(&repository).code(1).stdout(
        predicate::str::contains("crates/app/src/lib.rs:2:")
            .and(predicate::str::contains("raw corpus directory read")),
    );
}

#[test]
fn glob_and_walk_families_are_reported() {
    let repository = TempRepo::new();
    repository.write(
        "crates/app/src/lib.rs",
        b"pub fn a(log_base: &str) {\n    let _ = glob::glob(log_base);\n}\n\
          pub fn b(impl_root: &std::path::Path) {\n    let _ = walkdir::WalkDir::new(impl_root);\n}\n",
    );
    repository.commit_all();

    run(&repository).code(1).stdout(
        predicate::str::contains("raw corpus glob")
            .and(predicate::str::contains("raw corpus directory walk")),
    );
}

#[test]
fn owner_module_is_exempt() {
    let repository = TempRepo::new();
    repository.write(
        "crates/app/src/report/run_log_corpus.rs",
        b"pub fn scan(log_root: &std::path::Path) {\n    \
          let _ = std::fs::read_dir(log_root);\n}\n",
    );
    repository.commit_all();

    run(&repository)
        .success()
        .stdout(predicate::str::is_empty());
}

#[test]
fn session_scoped_corpus_argument_is_not_flagged() {
    let repository = TempRepo::new();
    // The argument carries a corpus marker (`log_root`) and a session marker
    // (`session_tmpdir`); the session-marker override wins, exercising the real
    // override branch and nested-paren argument scoping.
    repository.write(
        "crates/app/src/lib.rs",
        b"pub fn scan(session_tmpdir: &std::path::Path, log_root: &str) {\n    \
          let _ = std::fs::read_dir(session_tmpdir.join(log_root));\n}\n",
    );
    repository.commit_all();

    run(&repository)
        .success()
        .stdout(predicate::str::is_empty());
}

#[test]
fn walker_token_quoted_in_a_string_is_not_flagged() {
    let repository = TempRepo::new();
    // A walker token inside an error/log string is data, not a call.
    repository.write(
        "crates/app/src/lib.rs",
        b"pub fn scan(log_root: &str) -> String {\n    \
          format!(\"failed to read_dir({log_root})\")\n}\n",
    );
    repository.commit_all();

    run(&repository)
        .success()
        .stdout(predicate::str::is_empty());
}

#[test]
fn inline_suppression_with_reason_is_honored() {
    let repository = TempRepo::new();
    repository.write(
        "crates/app/src/lib.rs",
        b"pub fn scan(log_root: &std::path::Path) {\n    \
          let _ = std::fs::read_dir(log_root); // lint-run-log-corpus-walkers: ok external tool root\n}\n",
    );
    repository.commit_all();

    run(&repository)
        .success()
        .stdout(predicate::str::is_empty());
}

#[test]
fn inline_suppression_without_reason_is_an_error() {
    let repository = TempRepo::new();
    repository.write(
        "crates/app/src/lib.rs",
        b"pub fn scan(log_root: &std::path::Path) {\n    \
          let _ = std::fs::read_dir(log_root); // lint-run-log-corpus-walkers: ok\n}\n",
    );
    repository.commit_all();

    run(&repository)
        .code(2)
        .stderr(predicate::str::contains("lacks a reason"));
}

#[test]
fn python_corpus_walkers_keep_alias_and_manifest_protection() {
    let repository = TempRepo::new();
    repository.write(
        "python/larch/example.py",
        b"import os\n\
          def scan(log_root):\n\
              corpus = log_root\n\
              implement = corpus / \"implement\"\n\
              list(implement.glob(\"*\"))\n\
              list(log_root.rglob(\"findings-classification.tsv\"))\n\
              list(os.walk(log_root))\n\
              list(os.scandir(log_root))\n\
              for name in (\"manifest.json\", \"run-manifest.json\"):\n\
                  print(name)\n",
    );
    repository.commit_all();

    run(&repository).code(1).stdout(
        predicate::str::contains("python/larch/example.py:5: raw corpus glob")
            .and(predicate::str::contains(
                "python/larch/example.py:6: raw corpus glob",
            ))
            .and(predicate::str::contains(
                "python/larch/example.py:7: raw corpus directory walk",
            ))
            .and(predicate::str::contains(
                "python/larch/example.py:8: raw corpus directory read",
            ))
            .and(predicate::str::contains(
                "python/larch/example.py:9: dual-manifest candidate loop",
            )),
    );
}

#[test]
fn python_safe_run_aliases_and_unrelated_manifest_mentions_are_not_reported() {
    let repository = TempRepo::new();
    repository.write(
        "python/larch/example.py",
        b"def scan(log_root, names):\n\
              for run_dir in safe_child_run_dirs(log_root):\n\
                  list(run_dir.glob(\"*\"))\n\
              for name in names:\n\
                  if name == \"manifest.json\":\n\
                      print(name)\n\
                  elif name == \"run-manifest.json\":\n\
                      print(name)\n",
    );
    repository.commit_all();

    run(&repository)
        .success()
        .stdout(predicate::str::is_empty());
}
