//! Black-box parity for the Rust `render voter` command (#8896).

#[path = "support/parity.rs"]
#[allow(dead_code)]
mod parity_support;

use std::{
    env,
    path::{Path, PathBuf},
};

use parity_support::{NormalizationRule, ParityCase, Program, SeedFile, assert_rust_golden_case};

const BALLOT: &str = "### FINDING_1:\nproblem text\n";
const LEDGER: &str = concat!(
    "round\tfinding_id\ttitle\tfile_line\toutcome\tvote_tally\treason\n",
    "1\tFINDING_1\tPrior title\tsrc/lib.rs:1\trejected\tNO\tPrior reason\n",
);
const STATS: &str = concat!(
    "tool\tyes_votes\tvalid_yes_severity_count\tmajor\tminor\tnit\tmissing_severity\thigh_rate\tcalibration_score\tuncalibrated\n",
    "codex\t10\t10\t8\t1\t1\t0\t0.800\t1.000\tfalse\n",
);
const ANCHOR: &str = "Originating issue scope with <tags> and ghp_abcdefghijklmnopqrst\n";

#[rustfmt::skip]
type Case = (
    &'static str,
    &'static [&'static str],
    &'static [(&'static str, &'static str)],
    &'static [&'static str],
);

#[rustfmt::skip]
const CASES: &[Case] = &[
    (
        "render-voter-basic-code",
        &[
            "render", "voter",
            "--ballot-file", "{sandbox}/ballot.txt",
            "--panel-role", "validity voter",
            "--id-grammar", "finding-oos",
            "--verification-context", "code",
            "--payload-bytes-output", "{sandbox}/payload.txt",
        ],
        &[("ballot.txt", BALLOT)],
        &["payload.txt"],
    ),
    (
        "render-voter-calibration-ledger",
        &[
            "render", "voter",
            "--ballot-file", "{sandbox}/ballot.txt",
            "--panel-role", "validity voter",
            "--id-grammar", "finding-oos",
            "--verification-context", "code",
            "--findings-ledger-file", "{sandbox}/findings-ledger.tsv",
            "--calibration-stats-file", "{sandbox}/stats.tsv",
            "--voter-tool", "codex",
            "--archetype", "validity-correctness",
            "--payload-bytes-output", "{sandbox}/payload.txt",
        ],
        &[
            ("ballot.txt", BALLOT),
            ("findings-ledger.tsv", LEDGER),
            ("stats.tsv", STATS),
        ],
        &["payload.txt"],
    ),
    (
        "render-voter-plan-scope-anchor",
        &[
            "render", "voter",
            "--ballot-file", "{sandbox}/ballot.txt",
            "--panel-role", "plan voter",
            "--id-grammar", "finding-oos",
            "--verification-context", "plan",
            "--scope-anchor-file", "{sandbox}/anchor.md",
            "--payload-bytes-output", "{sandbox}/payload.txt",
        ],
        &[("ballot.txt", BALLOT), ("anchor.md", ANCHOR)],
        &["payload.txt"],
    ),
    (
        "render-voter-finding-only",
        &[
            "render", "voter",
            "--ballot-file", "{sandbox}/ballot.txt",
            "--panel-role", "code voter",
            "--id-grammar", "finding-only",
            "--verification-context", "diff-plan",
        ],
        &[("ballot.txt", BALLOT)],
        &[],
    ),
    (
        "render-voter-missing-ballot",
        &["render", "voter", "--panel-role", "x", "--id-grammar", "finding-oos", "--verification-context", "code"],
        &[],
        &[],
    ),
    (
        "render-voter-help-refusal",
        &["render", "voter", "--help"],
        &[],
        &[],
    ),
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
    let &(name, arguments, seeds, side_effects) = case;
    let root = repository_root();
    let reference = fixture_directory().join("render_voter_reference.py");
    let path = env::var("PATH").expect("PATH");
    let common = |program: Program| {
        program
            .env("CLAUDE_PLUGIN_ROOT", &root.to_string_lossy())
            .env("LARCH_BINARY", env!("CARGO_BIN_EXE_larch"))
            .env("LARCH_QUIET_DISABLE", "1")
            .env("PATH", &path)
    };
    // Frozen reference takes voter flags only (no `render voter` domain/verb).
    let python_args = arguments
        .iter()
        .skip(2)
        .map(|argument| (*argument).to_owned())
        .collect::<Vec<_>>();
    ParityCase {
        name,
        python: common(
            Program::new(python_executable())
                .args(
                    std::iter::once(reference.to_string_lossy().into_owned()).chain(python_args),
                )
                .env("PYTHONPATH", &root.join("python").to_string_lossy()),
        ),
        rust: common(
            Program::new(env!("CARGO_BIN_EXE_larch"))
                .args(arguments.iter().map(|argument| (*argument).to_owned())),
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
fn render_voter_has_frozen_black_box_parity() {
    let goldens = fixture_directory().join("goldens");
    for definition in CASES {
        let case = parity_case(definition);
        assert_rust_golden_case(&case, &goldens.join(format!("{}.golden.json", case.name)))
            .unwrap_or_else(|error| panic!("{error}"));
    }
}
