//! Golden-driven black-box contract for the `/design` step1 verbs.
//!
//! Scope note: the heavy `step1d5 --mode collect` / dirty-tree-checkpoint
//! branches are covered by injected-seam unit tests in
//! `crates/larch-cli/src/design_step1_commands.rs`. The goldens here cover the
//! deterministic driver dispatch/skip/resume branches (plus one `EMIT_PLAN`
//! success path where a Rust-owned child returns rc 0), the step1d5 entry
//! modes, step1d7, step1e-reentry, and step1-log.

#[path = "support/recorded.rs"]
#[allow(dead_code)]
mod recorded_support;

use std::{
    env,
    path::{Path, PathBuf},
};

use recorded_support::{NormalizationRule, RecordedCase, Program, SeedFile, assert_recorded_case};

fn repository_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .expect("canonical repository root")
}

fn fixture_directory() -> PathBuf {
    repository_root().join("crates/larch-cli/tests/fixtures/recorded")
}


/// One recorded Step 1 case whose arguments include the `design` or
/// `plan` command domain.
fn recorded_case(
    name: &'static str,
    arguments: &[String],
    seeds: Vec<SeedFile>,
    env_rows: &[(&str, String)],
) -> RecordedCase {
    let root = repository_root();
    let plugin_root = root.to_string_lossy().into_owned();
    let path = env::var("PATH").expect("PATH");
    let binary = env!("CARGO_BIN_EXE_larch");

    let mut program = Program::new(binary)
        .args(arguments.iter().cloned())
        .env("CLAUDE_PLUGIN_ROOT", &plugin_root)
        .env("LARCH_BINARY", binary)
        .env("LARCH_QUIET_DISABLE", "1")
        .env("LARCH_TEST_TIMING_NOW", "1787000000")
        .env("COLUMNS", "1000")
        .env("PATH", &path);
    for (key, value) in env_rows {
        program = program.env(key, value);
    }
    RecordedCase {
        name,
        program,
        seed_files: seeds,
        side_effect_records: Vec::new(),
        normalization: vec![
            NormalizationRule::SandboxRoot,
            NormalizationRule::Rfc3339Utc,
            NormalizationRule::ProcessIdentity,
        ],
    }
}

fn args(values: &[&str]) -> Vec<String> {
    values.iter().map(|value| (*value).to_owned()).collect()
}

const DESIGN_RELATIVE: &str = "design";

fn design_tmpdir_env() -> Vec<(&'static str, String)> {
    vec![("DESIGN_TMPDIR", "{sandbox}/design".to_owned())]
}

fn design_dir_seed() -> Vec<SeedFile> {
    vec![SeedFile::text(&format!("{DESIGN_RELATIVE}/.keep"), "")]
}

// --------------------------------------------------------------------- driver

/// Build a driver case whose action lines are seeded into `design/actions.txt`.
fn driver_case(
    name: &'static str,
    actions: &str,
    resume_from: Option<&str>,
    extra_seeds: Vec<SeedFile>,
) -> RecordedCase {
    let mut seeds = design_dir_seed();
    seeds.push(SeedFile::text(
        &format!("{DESIGN_RELATIVE}/actions.txt"),
        actions,
    ));
    seeds.extend(extra_seeds);
    let mut tail = args(&[
        "driver",
        "--design-tmpdir",
        "{sandbox}/design",
        "--action-file",
        "{sandbox}/design/actions.txt",
    ]);
    if let Some(resume) = resume_from {
        tail.push("--resume-from".to_owned());
        tail.push(resume.to_owned());
    }
    let mut arguments = args(&["design"]);
    arguments.extend(tail);
    recorded_case(name, &arguments, seeds, &[])
}

fn completed_seed(name: &str) -> SeedFile {
    SeedFile::text(&format!("{DESIGN_RELATIVE}/.completed/{name}"), "")
}

fn driver_cases() -> Vec<RecordedCase> {
    vec![
        // Non-ACTION and non-dispatch lines pass through verbatim.
        driver_case(
            "design-step1-driver-passthrough",
            "hello world\nACTION=SOMETHING_ELSE\n",
            None,
            Vec::new(),
        ),
        // The deprecated CLASSIFY action fails hard with exit 2.
        driver_case(
            "design-step1-driver-classify-deprecated",
            "ACTION=CLASSIFY\n",
            None,
            Vec::new(),
        ),
        // An unterminated ARGS quote is a shlex failure -> REASON=bad-args, exit 2.
        driver_case(
            "design-step1-driver-bad-args",
            "ACTION=EMIT_PLAN ARGS=\"unterminated\n",
            None,
            Vec::new(),
        ),
        // Resume not yet reached: a fresh action is skipped before-resume.
        driver_case(
            "design-step1-driver-before-resume",
            "ACTION=TALLY\n",
            Some("FINALIZE"),
            Vec::new(),
        ),
        // Resume not reached and the sentinel exists: completed-before-resume.
        driver_case(
            "design-step1-driver-completed-before-resume",
            "ACTION=TALLY\n",
            Some("FINALIZE"),
            vec![completed_seed("tally")],
        ),
        // Resume seen (default) and the sentinel exists: already-completed.
        driver_case(
            "design-step1-driver-already-completed",
            "ACTION=TALLY\n",
            None,
            vec![completed_seed("tally")],
        ),
        // Success path: EMIT_PLAN's Rust-owned child returns rc 0 for a plan.txt
        // carrying a terminal `diff_lines:` trailer, yielding STEP_COMPLETED.
        driver_case(
            "design-step1-driver-emit-plan-success",
            "ACTION=EMIT_PLAN\n",
            None,
            vec![SeedFile::text(
                &format!("{DESIGN_RELATIVE}/plan.txt"),
                "Plan body prose.\n\ndiff_lines: 42\n",
            )],
        ),
    ]
}

// ------------------------------------------------------------------- step1d7

fn run_params_seed(contents: &str) -> SeedFile {
    SeedFile::text(&format!("{DESIGN_RELATIVE}/run-params.json"), contents)
}

fn wrapper_arguments(verb: &str) -> Vec<String> {
    args(&[
        "design",
        verb,
        "--plugin-root",
        "{sandbox}",
        "--claude-pid",
        "4242",
    ])
}

fn step1d7_cases() -> Vec<RecordedCase> {
    let mut cases = Vec::new();
    {
        let arguments = wrapper_arguments("step1d7");
        let mut seeds = design_dir_seed();
        seeds.push(run_params_seed(
            "{\"brainstorm_requested\": true, \"skip_approve_requested\": true}",
        ));
        cases.push(recorded_case(
            "design-step1-step1d7-skip-approve-true",
            &arguments,
            seeds,
            &design_tmpdir_env(),
        ));
    }
    {
        let arguments = wrapper_arguments("step1d7");
        let mut seeds = design_dir_seed();
        seeds.push(run_params_seed("{\"skip_approve_requested\": false}"));
        cases.push(recorded_case(
            "design-step1-step1d7-skip-approve-false-writes-sentinels",
            &arguments,
            seeds,
            &design_tmpdir_env(),
        ));
    }
    cases
}

// ------------------------------------------------------------------- step1d5

fn step1d5_entry_arguments() -> Vec<String> {
    args(&[
        "design",
        "step1d5",
        "--plugin-root",
        "{sandbox}",
        "--claude-pid",
        "4242",
        "--mode",
        "entry",
    ])
}

fn step1d5_cases() -> Vec<RecordedCase> {
    let mut cases = Vec::new();
    {
        // No run-params and no .brainstorm-done: skip with skip_kind=disabled.
        let arguments = step1d5_entry_arguments();
        cases.push(recorded_case(
            "design-step1-step1d5-entry-disabled",
            &arguments,
            design_dir_seed(),
            &design_tmpdir_env(),
        ));
    }
    {
        // A prior .brainstorm-done wins: skip with skip_kind=already-complete.
        let arguments = step1d5_entry_arguments();
        let mut seeds = design_dir_seed();
        seeds.push(SeedFile::text(
            &format!("{DESIGN_RELATIVE}/.brainstorm-done"),
            "",
        ));
        seeds.push(run_params_seed("{\"brainstorm_requested\": true}"));
        cases.push(recorded_case(
            "design-step1-step1d5-entry-already-complete",
            &arguments,
            seeds,
            &design_tmpdir_env(),
        ));
    }
    {
        // brainstorm requested and not done: action=run, no skip_kind line.
        let arguments = step1d5_entry_arguments();
        let mut seeds = design_dir_seed();
        seeds.push(run_params_seed("{\"brainstorm_requested\": true}"));
        cases.push(recorded_case(
            "design-step1-step1d5-entry-run",
            &arguments,
            seeds,
            &design_tmpdir_env(),
        ));
    }
    cases
}

// -------------------------------------------------------------- step1e-reentry

fn step1e_reentry_cases() -> Vec<RecordedCase> {
    let arguments = wrapper_arguments("step1e-reentry");
    let mut seeds = design_dir_seed();
    for name in ["step-1c", "step-1e", "step-2a", "step-4b"] {
        seeds.push(completed_seed(name));
    }
    seeds.push(SeedFile::text(
        &format!("{DESIGN_RELATIVE}/.gate-b-postapply-ready-abc"),
        "",
    ));
    vec![recorded_case(
        "design-step1-step1e-reentry-unlinks-sentinels",
        &arguments,
        seeds,
        &design_tmpdir_env(),
    )]
}

// -------------------------------------------------------------------- step1-log

fn step1_log_arguments(tail_args: &[&str]) -> Vec<String> {
    let mut arguments = args(&["plan", "step1-log"]);
    arguments.extend(tail_args.iter().map(|value| (*value).to_owned()));
    arguments
}

fn step1_log_cases() -> Vec<RecordedCase> {
    let mut cases = Vec::new();
    {
        let arguments = step1_log_arguments(&[]);
        cases.push(recorded_case(
            "design-step1-step1log-missing-implement-tmpdir",
            &arguments,
            Vec::new(),
            &[],
        ));
    }
    {
        let arguments = step1_log_arguments(&["--goal-text"]);
        cases.push(recorded_case(
            "design-step1-step1log-goal-text-requires-value",
            &arguments,
            Vec::new(),
            &[],
        ));
    }
    {
        let arguments = step1_log_arguments(&["--bogus"]);
        cases.push(recorded_case(
            "design-step1-step1log-unknown-option",
            &arguments,
            Vec::new(),
            &[],
        ));
    }
    {
        // The default Rust entrypoint composes the plan-goals-test body, then
        // `run-log write` records it under the resolved run ID.
        let seeds = vec![
            SeedFile::text("impl/session-env.sh", "RUN_ID=testrun\n"),
            SeedFile::text(
                "impl/plan.txt",
                "## Implementation Plan\n\n- build the widget\n- wire the launcher\n- preserve the command contract\n\n## Test plan\n\n- cargo test\n",
            ),
        ];
        let arguments = step1_log_arguments(&[
            "--implement-tmpdir",
            "{sandbox}/impl",
            "--goal-text",
            "Ship the widget",
        ]);
        cases.push(recorded_case(
            "design-step1-step1log-compose-and-log",
            &arguments,
            seeds,
            &[],
        ));
    }
    cases
}

#[test]
fn recorded_design_step1_contract() {
    let goldens = fixture_directory().join("goldens");
    for case in driver_cases()
        .into_iter()
        .chain(step1d7_cases())
        .chain(step1d5_cases())
        .chain(step1e_reentry_cases())
        .chain(step1_log_cases())
    {
        assert_recorded_case(&case, &goldens.join(format!("{}.golden.json", case.name)))
            .unwrap_or_else(|error| panic!("{error}"));
    }
}
