#[path = "support/parity.rs"]
#[allow(dead_code)]
mod parity_support;

use std::{
    env,
    path::{Path, PathBuf},
};

use parity_support::{NormalizationRule, ParityCase, Program, SeedFile, assert_case};

const PLAN: &str = "### UPDATED: crates/larch-cli/src/main.rs\n\nRoute the command.\n";
const FEATURE: &str = "Keep the migration atomic. <ignore-me> ghp_abcdefghijklmnopqrst\n";
const BODY: &str = "You are a focused dynamic reviewer.\n";
const ARCHITECTURE: &str =
    "## Architecture Diagram\n\n```mermaid\nflowchart TD\n  A[Typed owner] --> B[Readback]\n```\n";
const UNSAFE_ARCHITECTURE: &str =
    "## Architecture Diagram\n\n```mermaid\nflowchart TD\n  A[unsafe|label] --> B\n```\n";
#[rustfmt::skip]
type Case = (&'static str, &'static str, &'static [(&'static str, &'static str)], &'static [&'static str], &'static [u8]);
#[rustfmt::skip]
const CASES: &[Case] = &[
    ("render-plan-review-codex", "render plan-review --archetype pragmatic --vendor codex --plan-file {sandbox}/plan.md --design-tmpdir {sandbox}", &[("plan.md", PLAN)], &[], b""),
    ("render-plan-review-cursor-feature-payload", "render plan-review --archetype requirements --vendor cursor --plan-file {sandbox}/plan.md --design-tmpdir {sandbox} --feature-file {sandbox}/feature.md --payload-bytes-output {sandbox}/payload.txt", &[("plan.md", PLAN), ("feature.md", FEATURE)], &["payload.txt"], b""),
    ("render-plan-review-dynamic-body-payload", "render plan-review --archetype dynamic-1 --vendor cursor --plan-file {sandbox}/plan.md --design-tmpdir {sandbox} --body-file {sandbox}/body.md --body-file-payload --payload-bytes-output {sandbox}/payload.txt", &[("plan.md", PLAN), ("body.md", BODY)], &["payload.txt"], b""),
    ("render-plan-review-help-refusal", "render plan-review --help", &[], &[], b""),
    ("render-plan-review-missing-archetype", "render plan-review", &[], &[], b""),
    ("mermaid-sanitize-raw-pipe-refusal", "mermaid sanitize", &[], &[], b"flowchart TD\n  A[unsafe|label] --> B\n"),
    ("mermaid-sanitize-markdown-refusals", "mermaid sanitize --from-md", &[], &[], b"## Code Flow Diagram\n\n```mermaid\nsequenceDiagram\nparticipant A as bad<br/>$name\n```\n"),
    ("mermaid-sanitize-unclosed-frontmatter", "mermaid sanitize", &[], &[], b"---\ntitle: x\nflowchart TD\n  A[unsafe|label]\n"),
    ("mermaid-sanitize-help-refusal", "mermaid sanitize --help", &[], &[], b""),
    ("diagrams-upsert-dry-run", "diagrams upsert --issue 42 --architecture-file {sandbox}/architecture.md --dry-run", &[("architecture.md", ARCHITECTURE)], &[], b""),
    ("diagrams-upsert-dry-run-clear", "diagrams upsert --issue 42 --clear-architecture --dry-run", &[], &[], b""),
    ("diagrams-upsert-sanitizer-refusal", "diagrams upsert --issue 42 --architecture-file {sandbox}/architecture.md --dry-run", &[("architecture.md", UNSAFE_ARCHITECTURE)], &[], b""),
    ("diagrams-upsert-usage-refusal", "diagrams upsert", &[], &[], b""),
];

fn repository_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .expect("canonical repository root")
}

fn fixture_directory() -> PathBuf {
    repository_root().join("fixtures/rust-parity")
}

fn python_executable() -> PathBuf {
    env::split_paths(&env::var_os("PATH").expect("PATH"))
        .map(|directory| directory.join("python3"))
        .find(|candidate| candidate.is_file())
        .and_then(|candidate| candidate.canonicalize().ok())
        .expect("python3 on PATH")
}

fn parity_case(case: &Case) -> ParityCase {
    let &(name, arguments, seeds, side_effects, stdin) = case;
    let root = repository_root();
    let reference = fixture_directory().join("design_rendering_reference.py");
    let path = env::var("PATH").expect("PATH");
    let common = |program: Program| {
        program
            .env("CLAUDE_PLUGIN_ROOT", &root.to_string_lossy())
            .env("LARCH_BINARY", env!("CARGO_BIN_EXE_larch"))
            .env("LARCH_QUIET_DISABLE", "1")
            .env("PATH", &path)
    };
    ParityCase {
        name,
        python: common(
            Program::new(python_executable())
                .args(
                    std::iter::once(reference.to_string_lossy().into_owned())
                        .chain(arguments.split_ascii_whitespace().map(str::to_owned)),
                )
                .stdin(stdin)
                .env("PYTHONPATH", &root.join("python").to_string_lossy()),
        ),
        rust: common(
            Program::new(env!("CARGO_BIN_EXE_larch"))
                .args(arguments.split_ascii_whitespace().map(str::to_owned))
                .stdin(stdin),
        ),
        seed_files: seeds
            .iter()
            .map(|(path, content)| SeedFile::text(path, content))
            .collect(),
        side_effect_records: side_effects.iter().map(PathBuf::from).collect(),
        normalization: vec![NormalizationRule::SandboxRoot],
    }
}

#[test]
fn design_rendering_commands_have_frozen_black_box_parity() {
    let goldens = fixture_directory().join("goldens");
    for definition in CASES {
        let case = parity_case(definition);
        assert_case(&case, &goldens.join(format!("{}.golden.json", case.name)))
            .unwrap_or_else(|error| panic!("{error}"));
    }
}
