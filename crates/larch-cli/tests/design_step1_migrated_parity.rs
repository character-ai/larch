//! Golden-driven black-box parity for the migrated `/design` step1 verbs (#8579).
//!
//! The frozen Python reference at
//! `fixtures/rust-parity/design_step1_migrated_reference.py` executes the
//! byte-frozen pre-cutover modules; each case runs both it and the Rust owner in
//! isolated sandboxes and asserts stdout/stderr/exit/wire-file parity plus a
//! recorded golden, mirroring `design_step0_migrated_parity.rs`.
//!
//! Scope note: the heavy `step1d5 --mode collect` / dirty-tree-checkpoint
//! branches are covered by injected-seam unit tests in
//! `crates/larch-cli/src/design_step1_commands.rs`. The goldens here cover the
//! deterministic driver dispatch/skip/resume branches (plus one `EMIT_PLAN`
//! success path where a Rust-owned child returns rc 0), the step1d5 entry
//! modes, step1d7, step1e-reentry, and step1-log.

#[path = "support/parity.rs"]
#[allow(dead_code)]
mod parity_support;

use std::{
    env,
    path::{Path, PathBuf},
};

use parity_support::{NormalizationRule, ParityCase, Program, SeedFile, assert_case};

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

/// One migrated step1 parity case. `reference_tail` is the verb plus its args
/// passed to the frozen reference; `rust_tail` is the argv passed to the built
/// larch binary (including the `design`/`plan` domain). `env_rows` sets
/// identical process-env overrides on both, with `{sandbox}` expanded per side.
fn parity_case(
    name: &'static str,
    reference_tail: &[String],
    rust_tail: &[String],
    seeds: Vec<SeedFile>,
    env_rows: &[(&str, String)],
) -> ParityCase {
    let root = repository_root();
    let reference = fixture_directory().join("design_step1_migrated_reference.py");
    let python_path = root.join("python");
    let plugin_root = root.to_string_lossy().into_owned();
    let path = env::var("PATH").expect("PATH");
    let binary = env!("CARGO_BIN_EXE_larch");

    let mut python = Program::new(python_executable())
        .args(
            std::iter::once(reference.to_string_lossy().into_owned())
                .chain(reference_tail.iter().cloned()),
        )
        .env("PYTHONPATH", &python_path.to_string_lossy())
        .env("CLAUDE_PLUGIN_ROOT", &plugin_root)
        // The frozen reference routes every larch child (plan-review, plan
        // validate, run-log, timing, agent, dirty-tree) at the built binary.
        .env("LARCH_BINARY", binary)
        .env("LARCH_QUIET_DISABLE", "1")
        .env("LARCH_TEST_TIMING_NOW", "1787000000")
        .env("COLUMNS", "1000")
        .env("PATH", &path);
    let mut rust = Program::new(binary)
        .args(rust_tail.iter().cloned())
        .env("CLAUDE_PLUGIN_ROOT", &plugin_root)
        .env("LARCH_BINARY", binary)
        .env("LARCH_QUIET_DISABLE", "1")
        .env("LARCH_TEST_TIMING_NOW", "1787000000")
        .env("COLUMNS", "1000")
        .env("PATH", &path);
    for (key, value) in env_rows {
        python = python.env(key, value);
        rust = rust.env(key, value);
    }
    ParityCase {
        name,
        python,
        rust,
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
) -> ParityCase {
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
    let mut rust_tail = args(&["design"]);
    rust_tail.extend(tail.iter().cloned());
    parity_case(name, &tail, &rust_tail, seeds, &[])
}

fn completed_seed(name: &str) -> SeedFile {
    SeedFile::text(&format!("{DESIGN_RELATIVE}/.completed/{name}"), "")
}

fn driver_cases() -> Vec<ParityCase> {
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

fn wrapper_tail(verb: &str) -> (Vec<String>, Vec<String>) {
    let tail = args(&[verb, "--plugin-root", "{sandbox}", "--claude-pid", "4242"]);
    let mut rust_tail = args(&["design"]);
    rust_tail.extend(tail.iter().cloned());
    (tail, rust_tail)
}

fn step1d7_cases() -> Vec<ParityCase> {
    let mut cases = Vec::new();
    {
        let (tail, rust_tail) = wrapper_tail("step1d7");
        let mut seeds = design_dir_seed();
        seeds.push(run_params_seed(
            "{\"brainstorm_requested\": true, \"skip_approve_requested\": true}",
        ));
        cases.push(parity_case(
            "design-step1-step1d7-skip-approve-true",
            &tail,
            &rust_tail,
            seeds,
            &design_tmpdir_env(),
        ));
    }
    {
        let (tail, rust_tail) = wrapper_tail("step1d7");
        let mut seeds = design_dir_seed();
        seeds.push(run_params_seed("{\"skip_approve_requested\": false}"));
        cases.push(parity_case(
            "design-step1-step1d7-skip-approve-false-writes-sentinels",
            &tail,
            &rust_tail,
            seeds,
            &design_tmpdir_env(),
        ));
    }
    cases
}

// ------------------------------------------------------------------- step1d5

fn step1d5_entry_tail() -> (Vec<String>, Vec<String>) {
    let tail = args(&[
        "step1d5",
        "--plugin-root",
        "{sandbox}",
        "--claude-pid",
        "4242",
        "--mode",
        "entry",
    ]);
    let mut rust_tail = args(&["design"]);
    rust_tail.extend(tail.iter().cloned());
    (tail, rust_tail)
}

fn step1d5_cases() -> Vec<ParityCase> {
    let mut cases = Vec::new();
    {
        // No run-params and no .brainstorm-done: skip with skip_kind=disabled.
        let (tail, rust_tail) = step1d5_entry_tail();
        cases.push(parity_case(
            "design-step1-step1d5-entry-disabled",
            &tail,
            &rust_tail,
            design_dir_seed(),
            &design_tmpdir_env(),
        ));
    }
    {
        // A prior .brainstorm-done wins: skip with skip_kind=already-complete.
        let (tail, rust_tail) = step1d5_entry_tail();
        let mut seeds = design_dir_seed();
        seeds.push(SeedFile::text(
            &format!("{DESIGN_RELATIVE}/.brainstorm-done"),
            "",
        ));
        seeds.push(run_params_seed("{\"brainstorm_requested\": true}"));
        cases.push(parity_case(
            "design-step1-step1d5-entry-already-complete",
            &tail,
            &rust_tail,
            seeds,
            &design_tmpdir_env(),
        ));
    }
    {
        // brainstorm requested and not done: action=run, no skip_kind line.
        let (tail, rust_tail) = step1d5_entry_tail();
        let mut seeds = design_dir_seed();
        seeds.push(run_params_seed("{\"brainstorm_requested\": true}"));
        cases.push(parity_case(
            "design-step1-step1d5-entry-run",
            &tail,
            &rust_tail,
            seeds,
            &design_tmpdir_env(),
        ));
    }
    cases
}

// -------------------------------------------------------------- step1e-reentry

fn step1e_reentry_cases() -> Vec<ParityCase> {
    let (tail, rust_tail) = wrapper_tail("step1e-reentry");
    let mut seeds = design_dir_seed();
    for name in ["step-1c", "step-1e", "step-2a", "step-4b"] {
        seeds.push(completed_seed(name));
    }
    seeds.push(SeedFile::text(
        &format!("{DESIGN_RELATIVE}/.gate-b-postapply-ready-abc"),
        "",
    ));
    vec![parity_case(
        "design-step1-step1e-reentry-unlinks-sentinels",
        &tail,
        &rust_tail,
        seeds,
        &design_tmpdir_env(),
    )]
}

// -------------------------------------------------------------------- step1-log

const IMPL_RELATIVE: &str = "impl";

fn step1_log_tail(tail_args: &[&str]) -> (Vec<String>, Vec<String>) {
    let mut tail = args(&["step1-log"]);
    tail.extend(tail_args.iter().map(|value| (*value).to_owned()));
    let mut rust_tail = args(&["plan"]);
    rust_tail.extend(tail.iter().cloned());
    (tail, rust_tail)
}

fn step1_log_cases() -> Vec<ParityCase> {
    let mut cases = Vec::new();
    {
        let (tail, rust_tail) = step1_log_tail(&[]);
        cases.push(parity_case(
            "design-step1-step1log-missing-implement-tmpdir",
            &tail,
            &rust_tail,
            Vec::new(),
            &[],
        ));
    }
    {
        let (tail, rust_tail) = step1_log_tail(&["--goal-text"]);
        cases.push(parity_case(
            "design-step1-step1log-goal-text-requires-value",
            &tail,
            &rust_tail,
            Vec::new(),
            &[],
        ));
    }
    {
        let (tail, rust_tail) = step1_log_tail(&["--bogus"]);
        cases.push(parity_case(
            "design-step1-step1log-unknown-option",
            &tail,
            &rust_tail,
            Vec::new(),
            &[],
        ));
    }
    {
        // Happy path: a compose override writes a fixed plan-goals-test body,
        // then `run-log write` records it under the resolved RUN_ID.
        let python = python_executable().to_string_lossy().into_owned();
        let compose = format!("{python} {{sandbox}}/{IMPL_RELATIVE}/compose.py");
        let seeds = vec![
            SeedFile::text(&format!("{IMPL_RELATIVE}/session-env.sh"), "RUN_ID=testrun\n"),
            SeedFile::text(&format!("{IMPL_RELATIVE}/plan.txt"), "plan body\n"),
            SeedFile::text(
                &format!("{IMPL_RELATIVE}/compose.py"),
                "import sys\nsys.stdout.write(\n    \"## Goal\\nShip the widget\\n\\n\"\n    \"## Implementation Plan\\n- build the widget\\n- wire the launcher\\n\\n\"\n    \"## Test plan\\n- cargo test\\n\"\n)\n",
            ),
        ];
        let (tail, rust_tail) = step1_log_tail(&[
            "--implement-tmpdir",
            "{sandbox}/impl",
            "--goal-text",
            "Ship the widget",
        ]);
        cases.push(parity_case(
            "design-step1-step1log-compose-and-log",
            &tail,
            &rust_tail,
            seeds,
            &[("RUN_STEP1_COMPOSE_CMD", compose)],
        ));
    }
    cases
}

#[test]
fn design_step1_migrated_verbs_match_frozen_python_reference() {
    let goldens = fixture_directory().join("goldens");
    for case in driver_cases()
        .into_iter()
        .chain(step1d7_cases())
        .chain(step1d5_cases())
        .chain(step1e_reentry_cases())
        .chain(step1_log_cases())
    {
        assert_case(&case, &goldens.join(format!("{}.golden.json", case.name)))
            .unwrap_or_else(|error| panic!("{error}"));
    }
}
