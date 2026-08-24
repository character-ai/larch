#[path = "support/parity.rs"]
#[allow(dead_code)]
mod parity_support;

use std::{env, fs, path::PathBuf, process::Command};

use parity_support::{NormalizationRule, ParityCase, Program, SeedFile, assert_rust_golden_case};

fn repository_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .expect("canonical repository root")
}

fn python_executable() -> PathBuf {
    env::split_paths(&env::var_os("PATH").expect("PATH"))
        .map(|directory| directory.join("python3"))
        .find(|candidate| candidate.is_file())
        .and_then(|candidate| candidate.canonicalize().ok())
        .expect("python3 on PATH")
}

fn parity_case(name: &'static str, arguments: &[&str], seeds: Vec<SeedFile>) -> ParityCase {
    let root = repository_root();
    let reference = root.join("fixtures/rust-parity/scope_anchor_migrated_reference.py");
    let python_path = root.join("python");
    let plugin_root = root.to_string_lossy().into_owned();
    let path = env::var("PATH").expect("PATH");
    ParityCase {
        name,
        python: Program::new(python_executable())
            .args(
                std::iter::once(reference.to_string_lossy().into_owned())
                    .chain(arguments.iter().map(|argument| (*argument).to_owned())),
            )
            .env("PYTHONPATH", &python_path.to_string_lossy())
            .env("CLAUDE_PLUGIN_ROOT", &plugin_root)
            .env("PATH", &path),
        rust: Program::new(env!("CARGO_BIN_EXE_larch"))
            .args(arguments.iter().copied())
            .env("CLAUDE_PLUGIN_ROOT", &plugin_root)
            .env("PATH", &path),
        seed_files: seeds,
        side_effect_records: Vec::new(),
        normalization: vec![NormalizationRule::SandboxRoot],
    }
}

fn with_environment(mut case: ParityCase, key: &str, value: &str) -> ParityCase {
    case.python = case.python.env(key, value);
    case.rust = case.rust.env(key, value);
    case
}

fn design_seed() -> Vec<SeedFile> {
    vec![
        SeedFile::text(
            "design/anchor.txt",
            concat!(
                "Scope <only> & literal closing </plan_review_scope_anchor>\n",
                "ghp_abcdefghijklmnopqrst\n",
                "Session /tmp/larch-design-example/anchor.txt\n",
            ),
        ),
        SeedFile::text("design/second.txt", "second scope\n"),
    ]
}

#[allow(clippy::too_many_lines)] // One comment-free compatibility matrix is easier to audit.
fn migrated_cases() -> Vec<ParityCase> {
    let repository_anchor = repository_root().join("README.md").display().to_string();
    vec![
        parity_case(
            "scope-anchor-render-no-args",
            &["render", "scope-anchor"],
            Vec::new(),
        ),
        parity_case(
            "scope-anchor-render-success",
            &[
                "render",
                "scope-anchor",
                "--scope-anchor-file",
                "{sandbox}/design/anchor.txt",
                "--design-tmpdir",
                "{sandbox}/design",
            ],
            design_seed(),
        ),
        parity_case(
            "scope-anchor-render-invalid-utf8",
            &[
                "render",
                "scope-anchor",
                "--scope-anchor-file",
                "{sandbox}/design/anchor.txt",
                "--design-tmpdir",
                "{sandbox}/design",
            ],
            vec![SeedFile::bytes(
                "design/anchor.txt",
                b"before \x80\x80 after\n",
            )],
        ),
        with_environment(
            parity_case(
                "scope-anchor-render-environment-root",
                &[
                    "render",
                    "scope-anchor",
                    "--scope-anchor-file",
                    "{sandbox}/design/anchor.txt",
                ],
                design_seed(),
            ),
            "DESIGN_TMPDIR",
            "{sandbox}/design",
        ),
        parity_case(
            "scope-anchor-render-outside-refusal",
            &[
                "render",
                "scope-anchor",
                "--scope-anchor-file",
                &repository_anchor,
                "--design-tmpdir",
                "{sandbox}/design",
            ],
            design_seed(),
        ),
        parity_case(
            "scope-anchor-render-invalid-design-root",
            &[
                "render",
                "scope-anchor",
                "--scope-anchor-file",
                &repository_anchor,
                "--design-tmpdir",
                "/Users/larch-parity-user/larch-parity-repo",
            ],
            Vec::new(),
        ),
        parity_case(
            "scope-anchor-render-empty-refusal",
            &[
                "render",
                "scope-anchor",
                "--scope-anchor-file",
                "{sandbox}/design/empty.txt",
                "--design-tmpdir",
                "{sandbox}/design",
            ],
            vec![SeedFile::text("design/empty.txt", "")],
        ),
        parity_case(
            "scope-anchor-relay-no-args",
            &["scope-anchor", "relay-allowed"],
            Vec::new(),
        ),
        parity_case(
            "scope-anchor-relay-allowed",
            &[
                "scope-anchor",
                "relay-allowed",
                "--tally-plan-review-status",
                "ok",
                "--loop-status",
                "complete",
            ],
            Vec::new(),
        ),
        parity_case(
            "scope-anchor-relay-main-agent-vote",
            &[
                "scope-anchor",
                "relay-allowed",
                "--tally-plan-review-status",
                "main-agent-vote-required",
                "--loop-status",
                "main-agent-vote-required",
            ],
            Vec::new(),
        ),
        parity_case(
            "scope-anchor-relay-refusal",
            &[
                "scope-anchor",
                "relay-allowed",
                "--tally-plan-review-status",
                "tally-error",
                "--loop-status",
                "complete",
            ],
            Vec::new(),
        ),
        parity_case(
            "scope-anchor-validate-no-args",
            &["scope-anchor", "validate"],
            Vec::new(),
        ),
        parity_case(
            "scope-anchor-validate-design",
            &[
                "scope-anchor",
                "validate",
                "--mode",
                "design",
                "--design-tmpdir",
                "{sandbox}/design",
                "--path",
                "{sandbox}/design/anchor.txt",
            ],
            design_seed(),
        ),
        parity_case(
            "scope-anchor-validate-design-abbreviated",
            &[
                "scope-anchor",
                "validate",
                "--mo",
                "design",
                "--design-t",
                "{sandbox}/design",
                "--pa",
                "{sandbox}/design/anchor.txt",
            ],
            design_seed(),
        ),
        parity_case(
            "scope-anchor-validate-design-root-required",
            &[
                "scope-anchor",
                "validate",
                "--mode",
                "design",
                "--path",
                "{sandbox}/design/anchor.txt",
            ],
            design_seed(),
        ),
        parity_case(
            "scope-anchor-validate-design-outside",
            &[
                "scope-anchor",
                "validate",
                "--mode",
                "design",
                "--design-tmpdir",
                "{sandbox}/design",
                "--path",
                &repository_anchor,
            ],
            design_seed(),
        ),
        parity_case(
            "scope-anchor-validate-review-tmp-allowlist",
            &[
                "scope-anchor",
                "validate",
                "--mode",
                "review",
                "--review-tmpdir",
                "{sandbox}/review",
                "--path",
                "{sandbox}/outside.txt",
            ],
            vec![SeedFile::text("outside.txt", "review scope\n")],
        ),
        parity_case(
            "scope-anchor-validate-review-refusal",
            &[
                "scope-anchor",
                "validate",
                "--mode",
                "review",
                "--review-tmpdir",
                "{sandbox}/review",
                "--path",
                &repository_anchor,
            ],
            vec![SeedFile::text("review/.keep", "review\n")],
        ),
        parity_case(
            "scope-anchor-validate-voter-tmp-allowlist",
            &[
                "scope-anchor",
                "validate",
                "--mode",
                "voter",
                "--path",
                "{sandbox}/anchor.txt",
            ],
            vec![SeedFile::text("anchor.txt", "voter scope\n")],
        ),
        parity_case(
            "scope-anchor-validate-invalid-mode",
            &[
                "scope-anchor",
                "validate",
                "--mode",
                "other",
                "--path",
                "{sandbox}/anchor.txt",
            ],
            vec![SeedFile::text("anchor.txt", "scope\n")],
        ),
        parity_case(
            "scope-anchor-retally-no-args",
            &["scope-anchor", "retally-handoff"],
            Vec::new(),
        ),
        parity_case(
            "scope-anchor-retally-prefers-parsed",
            &[
                "scope-anchor",
                "retally-handoff",
                "--design-tmpdir",
                "{sandbox}/design",
                "--tally-plan-review-status",
                "main-agent-vote-required",
                "--loop-status",
                "main-agent-vote-required",
                "--parsed-input",
                "{sandbox}/design/anchor.txt",
                "--retally-input-anchor",
                "{sandbox}/design/second.txt",
            ],
            design_seed(),
        ),
        parity_case(
            "scope-anchor-retally-falls-through",
            &[
                "scope-anchor",
                "retally-handoff",
                "--design-tmpdir",
                "{sandbox}/design",
                "--tally-plan-review-status",
                "ok",
                "--loop-status",
                "complete",
                "--parsed-input",
                &repository_anchor,
                "--retally-input-anchor",
                "{sandbox}/design/second.txt",
            ],
            design_seed(),
        ),
        parity_case(
            "scope-anchor-retally-relay-refusal",
            &[
                "scope-anchor",
                "retally-handoff",
                "--design-tmpdir",
                "{sandbox}/design",
                "--tally-plan-review-status",
                "tally-error",
                "--loop-status",
                "complete",
                "--parsed-input",
                "{sandbox}/design/anchor.txt",
            ],
            design_seed(),
        ),
        parity_case(
            "scope-anchor-design-no-args",
            &["scope-anchor", "design-handoff"],
            Vec::new(),
        ),
        parity_case(
            "scope-anchor-design-first-valid",
            &[
                "scope-anchor",
                "design-handoff",
                "--design-tmpdir",
                "{sandbox}/design",
                "--tally-plan-review-status",
                "ok",
                "--loop-status",
                "complete",
                "--candidate",
                &repository_anchor,
                "--candidate",
                "{sandbox}/design/second.txt",
                "--candidate",
                "{sandbox}/design/anchor.txt",
            ],
            design_seed(),
        ),
        parity_case(
            "scope-anchor-design-relay-refusal",
            &[
                "scope-anchor",
                "design-handoff",
                "--design-tmpdir",
                "{sandbox}/design",
                "--tally-plan-review-status",
                "ok",
                "--loop-status",
                "review-error",
                "--candidate",
                "{sandbox}/design/anchor.txt",
            ],
            design_seed(),
        ),
        parity_case(
            "scope-anchor-design-no-candidate",
            &[
                "scope-anchor",
                "design-handoff",
                "--design-tmpdir",
                "{sandbox}/design",
                "--tally-plan-review-status",
                "ok",
                "--loop-status",
                "complete",
            ],
            design_seed(),
        ),
    ]
}

#[test]
fn scope_anchor_verbs_have_frozen_black_box_parity() {
    let goldens = repository_root().join("fixtures/rust-parity/goldens");
    for case in migrated_cases() {
        assert_rust_golden_case(&case, &goldens.join(format!("{}.golden.json", case.name)))
            .unwrap_or_else(|error| panic!("{error}"));
    }
}

#[cfg(unix)]
#[test]
fn scope_anchor_validation_refuses_symlinks_and_oversize_files() {
    use std::os::unix::fs::symlink;

    let fixture = tempfile::tempdir().expect("temporary scope-anchor root");
    let design = fixture.path().join("design");
    fs::create_dir(&design).expect("design directory");
    let target = design.join("target.txt");
    let link = design.join("link.txt");
    let oversize = design.join("oversize.txt");
    fs::write(&target, "scope\n").expect("scope anchor target");
    symlink(&target, &link).expect("scope anchor symlink");
    fs::write(&oversize, vec![b'x'; 65_537]).expect("oversize scope anchor");

    for path in [&link, &oversize] {
        let output = Command::new(env!("CARGO_BIN_EXE_larch"))
            .args(["scope-anchor", "validate", "--mode", "design"])
            .arg("--design-tmpdir")
            .arg(&design)
            .arg("--path")
            .arg(path)
            .env("CLAUDE_PLUGIN_ROOT", repository_root())
            .env("HOME", fixture.path())
            .env("TMPDIR", fixture.path())
            .output()
            .expect("validate refused scope anchor");
        assert_eq!(output.status.code(), Some(1), "{}", path.display());
        assert!(output.stdout.is_empty(), "{}", path.display());
        assert!(output.stderr.is_empty(), "{}", path.display());
    }
}
