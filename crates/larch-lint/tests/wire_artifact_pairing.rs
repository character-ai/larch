mod support;

use predicates::prelude::*;
use support::TempRepo;

const MANIFEST: &str = "crates/larch-lint/data/wire-artifact-manifest.toml";
const BASELINE: &str = "crates/larch-lint/data/wire-artifact-pairing-baseline.toml";

const fn final_summary_manifest() -> &'static [u8] {
    b"[[artifact]]\nkind = \"basename\"\nname = \"final-summary.md\"\n"
}

#[test]
fn reader_without_writer_is_reported() {
    let repository = TempRepo::new();
    repository.write(MANIFEST, final_summary_manifest());
    repository.write(
        "crates/app/src/lib.rs",
        b"pub fn load() -> std::io::Result<String> {\n    \
          std::fs::read_to_string(\"final-summary.md\")\n}\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "wire-artifact-pairing"])
        .assert()
        .code(1)
        .stdout(
            predicate::str::contains(MANIFEST)
                .and(predicate::str::contains("basename:final-summary.md"))
                .and(predicate::str::contains("no production writer")),
        );
}

#[test]
fn production_writer_clears_the_finding() {
    let repository = TempRepo::new();
    repository.write(MANIFEST, final_summary_manifest());
    repository.write(
        "crates/app/src/lib.rs",
        b"pub fn load() -> std::io::Result<String> {\n    \
          std::fs::read_to_string(\"final-summary.md\")\n}\n\
          pub fn save(data: &[u8]) -> std::io::Result<()> {\n    \
          std::fs::write(\"final-summary.md\", data)\n}\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "wire-artifact-pairing"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty());
}

#[test]
fn residual_shell_writer_clears_the_finding() {
    let repository = TempRepo::new();
    repository.write(MANIFEST, final_summary_manifest());
    repository.write(
        "crates/app/src/lib.rs",
        b"pub fn load() -> std::io::Result<String> {\n    \
          std::fs::read_to_string(\"final-summary.md\")\n}\n",
    );
    repository.write(
        "scripts/emit.sh",
        b"#!/usr/bin/env bash\nprintf 'done' > \"$dir/final-summary.md\"\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "wire-artifact-pairing"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty());
}

#[test]
fn baseline_grandfathers_a_one_sided_artifact() {
    let repository = TempRepo::new();
    repository.write(MANIFEST, final_summary_manifest());
    repository.write(
        BASELINE,
        b"[[grandfathered]]\nartifact = \"final-summary.md\"\n\
          side = \"intentionally-one-sided\"\n\
          reason = \"produced outside the scanned Rust surface\"\n",
    );
    repository.write(
        "crates/app/src/lib.rs",
        b"pub fn load() -> std::io::Result<String> {\n    \
          std::fs::read_to_string(\"final-summary.md\")\n}\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "wire-artifact-pairing"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty());
}

#[test]
fn basename_boundary_does_not_match_a_longer_filename() {
    let repository = TempRepo::new();
    repository.write(
        MANIFEST,
        b"[[artifact]]\nkind = \"basename\"\nname = \"manifest.json\"\n",
    );
    repository.write(
        "crates/app/src/lib.rs",
        b"pub fn load() -> std::io::Result<String> {\n    \
          std::fs::read_to_string(\"run-manifest.json\")\n}\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "wire-artifact-pairing"])
        .assert()
        .success()
        .stdout(predicate::str::is_empty());
}

#[test]
fn non_utf8_file_under_shell_scope_is_tolerated() {
    let repository = TempRepo::new();
    repository.write(MANIFEST, final_summary_manifest());
    repository.write(
        "crates/app/src/lib.rs",
        b"pub fn load() -> std::io::Result<String> {\n    \
          std::fs::read_to_string(\"final-summary.md\")\n}\n",
    );
    // A non-UTF-8 file lives under the shell scope (which reads every file type,
    // not just scripts). It must be skipped, not abort the run with exit 2.
    repository.write("scripts/blob.bin", &[0xff, 0xfe, 0x00, 0xe9]);
    repository.commit_all();

    // The reader-without-writer finding still surfaces (exit 1), proving the
    // non-UTF-8 file was tolerated rather than turning the run into a hard error.
    TempRepo::command_from(repository.path())
        .args(["rule", "wire-artifact-pairing"])
        .assert()
        .code(1)
        .stdout(predicate::str::contains("basename:final-summary.md"));
}

#[test]
fn malformed_manifest_is_a_hard_error() {
    let repository = TempRepo::new();
    repository.write(
        MANIFEST,
        b"[[artifact]]\nkind = \"unsupported\"\nname = \"final-summary.md\"\n",
    );
    repository.commit_all();

    TempRepo::command_from(repository.path())
        .args(["rule", "wire-artifact-pairing"])
        .assert()
        .code(2)
        .stderr(predicate::str::contains("invalid manifest kind"));
}
