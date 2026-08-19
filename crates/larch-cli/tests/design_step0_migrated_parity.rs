//! Golden-driven black-box parity for the migrated `/design` Step 0 verbs (#8578).
//!
//! The frozen Python reference at
//! `fixtures/rust-parity/design_step0_migrated_reference.py` executes the
//! byte-frozen pre-cutover modules; each case runs both it and the Rust owner in
//! isolated sandboxes and asserts stdout/stderr/exit/wire-file parity plus a
//! recorded golden, mirroring `design_router_migrated_parity.rs`.
//!
//! Scope note: the heavy `step0-session` orchestration and the `step0-route`
//! success path (a proceed route folding `INIT_STATUS=ok` with a non-empty
//! `RUN_PARAMS_PATH=`) are covered by injected-seam unit tests in
//! `crates/larch-cli/src/design_step0_commands.rs`, because a byte-identical
//! `session setup`/`write-design-env` success needs a live session the offline
//! sandbox cannot record. The goldens here cover the deterministic verbs plus
//! the proceed route's folded env-refresh path.

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

/// One migrated Step 0 parity case: the frozen reference plus the Rust owner in
/// matched sandboxes. `env_rows` sets identical process-env overrides on both
/// (e.g. `DESIGN_TMPDIR`, `SUMMARY_OUTCOME`); `{sandbox}` expands per side.
fn parity_case(
    name: &'static str,
    arguments: &[String],
    seeds: Vec<SeedFile>,
    env_rows: &[(&str, &str)],
) -> ParityCase {
    let root = repository_root();
    let reference = fixture_directory().join("design_step0_migrated_reference.py");
    let python_path = root.join("python");
    let plugin_root = root.to_string_lossy().into_owned();
    let path = env::var("PATH").expect("PATH");
    let binary = env!("CARGO_BIN_EXE_larch");

    let mut python = Program::new(python_executable())
        .args(
            std::iter::once(reference.to_string_lossy().into_owned())
                .chain(arguments.iter().cloned()),
        )
        .env("PYTHONPATH", &python_path.to_string_lossy())
        .env("CLAUDE_PLUGIN_ROOT", &plugin_root)
        // The frozen reference routes child verbs (design parse-flags/route/
        // init-runparams, session/run-log/agent/progress/token/timing) and the
        // stage-terminal-state bridge at the built binary; see its docstring.
        .env("LARCH_BINARY", binary)
        .env("LARCH_QUIET_DISABLE", "1")
        // Fix the timing-ledger clock so `timing mark` rows are byte-stable
        // across golden re-recording; both sides share the same fixed epoch.
        .env("LARCH_TEST_TIMING_NOW", "1787000000")
        .env("COLUMNS", "1000")
        .env("PATH", &path);
    let mut rust = Program::new(binary)
        .args(std::iter::once("design".to_owned()).chain(arguments.iter().cloned()))
        .env("CLAUDE_PLUGIN_ROOT", &plugin_root)
        // The Rust owner's live child-verb runner and pause/stage bridges prefer
        // the same harness binary so both sides cross identical process seams.
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

// ------------------------------------------------------------ settle-next-action

fn settle(name: &'static str, tail: &[&str]) -> ParityCase {
    let mut argv = args(&["settle-next-action"]);
    argv.extend(tail.iter().map(|value| (*value).to_owned()));
    parity_case(name, &argv, Vec::new(), &[])
}

fn settle_cases() -> Vec<ParityCase> {
    vec![
        settle("design-step0-settle-help", &["-h"]),
        settle("design-step0-settle-missing-site", &["--postplan-rc", "0"]),
        settle("design-step0-settle-missing-rc", &["--site", "gate-b"]),
        settle(
            "design-step0-settle-unknown-option",
            &["--site", "gate-b", "--bogus"],
        ),
        settle(
            "design-step0-settle-invalid-site",
            &["--site", "gate-x", "--postplan-rc", "0"],
        ),
        settle(
            "design-step0-settle-invalid-rc",
            &["--site", "gate-b", "--postplan-rc", "not-a-number"],
        ),
        settle(
            "design-step0-settle-gate-b-continue",
            &["--site", "gate-b", "--postplan-rc", "0"],
        ),
        settle(
            "design-step0-settle-gate-b-hard-size",
            &["--site", "gate-b", "--postplan-rc", "12"],
        ),
        settle(
            "design-step0-settle-gate-a-pause",
            &["--site", "gate-a", "--postplan-rc", "11"],
        ),
        settle(
            "design-step0-settle-gate-c-split",
            &["--site", "gate-c", "--postplan-rc", "13"],
        ),
        settle(
            "design-step0-settle-discussion-round2-validator-fail",
            &["--site", "discussion-round2", "--postplan-rc", "10"],
        ),
        settle(
            "design-step0-settle-unknown-dispatch",
            &["--site", "gate-c", "--postplan-rc", "99"],
        ),
    ]
}

// --------------------------------------------------------------------- step0-parse

const DESIGN_RELATIVE: &str = "design";

fn design_tmpdir_env() -> Vec<(&'static str, &'static str)> {
    vec![("DESIGN_TMPDIR", "{sandbox}/design")]
}

fn design_dir_seed() -> Vec<SeedFile> {
    vec![SeedFile::text(&format!("{DESIGN_RELATIVE}/.keep"), "")]
}

fn parse_args(tail: &[&str]) -> Vec<String> {
    let mut argv = args(&["step0-parse", "--plugin-root", "{sandbox}", "--claude-pid", "4242"]);
    argv.push("--".to_owned());
    argv.extend(tail.iter().map(|value| (*value).to_owned()));
    argv
}

fn parse_cases() -> Vec<ParityCase> {
    vec![
        parity_case(
            "design-step0-parse-issue-success",
            &parse_args(&["123"]),
            Vec::new(),
            &[],
        ),
        parity_case(
            "design-step0-parse-flags-and-run-id",
            &parse_args(&["-p", "--brainstorm", "--run-id", "it's-rid", "123"]),
            Vec::new(),
            &[],
        ),
        parity_case(
            "design-step0-parse-verbal-unicode",
            &parse_args(&["add", "a", "😀", "café", "ÿ", "widget"]),
            Vec::new(),
            &[],
        ),
        parity_case(
            "design-step0-parse-rejects-hard",
            &parse_args(&["--hard", "123"]),
            Vec::new(),
            &[],
        ),
        parity_case(
            "design-step0-parse-public-argv-words-abort",
            &parse_args(&["${PUBLIC_ARGV_WORDS}"]),
            Vec::new(),
            &[],
        ),
        parity_case(
            "design-step0-parse-empty-plugin-root",
            &args(&["step0-parse", "--plugin-root", "", "--claude-pid", "4242", "--", "123"]),
            Vec::new(),
            &[],
        ),
    ]
}

// -------------------------------------------------------------- wrapper-arg errors

fn wrapper_error_cases() -> Vec<ParityCase> {
    vec![
        parity_case(
            "design-step0-parse-unknown-argument",
            &args(&["step0-parse", "--bogus"]),
            Vec::new(),
            &[],
        ),
        parity_case(
            "design-step0-route-missing-value",
            &args(&["step0-route", "--claude-pid"]),
            Vec::new(),
            &[],
        ),
    ]
}

// --------------------------------------------------------------- abort-cleanup

fn abort_cleanup_cases() -> Vec<ParityCase> {
    vec![
        // PID rejection short-circuits before any child dispatch: exit 2 with the
        // legacy `design-step0-abort-cleanup.sh:` stderr label.
        parity_case(
            "design-step0-abort-cleanup-bad-pid",
            &args(&[
                "step0-abort-cleanup",
                "--plugin-root",
                "{sandbox}",
                "--claude-pid",
                "not-a-pid",
            ]),
            design_dir_seed(),
            &design_tmpdir_env(),
        ),
        parity_case(
            "design-step0-abort-cleanup-missing-tmpdir",
            &args(&[
                "step0-abort-cleanup",
                "--plugin-root",
                "{sandbox}",
                "--claude-pid",
                "4242",
            ]),
            Vec::new(),
            &[],
        ),
    ]
}

// ----------------------------------------------------- ap-continue and step0c

fn sentinel_cases() -> Vec<ParityCase> {
    vec![
        parity_case(
            "design-step0-ap-continue-writes-sentinels",
            &args(&[
                "step0-ap-continue",
                "--plugin-root",
                "{sandbox}",
                "--claude-pid",
                "4242",
            ]),
            design_dir_seed(),
            &design_tmpdir_env(),
        ),
        parity_case(
            "design-step0c-writes-folded-sentinel",
            &args(&[
                "step0c",
                "--plugin-root",
                "{sandbox}",
                "--claude-pid",
                "4242",
            ]),
            design_dir_seed(),
            &design_tmpdir_env(),
        ),
    ]
}

// --------------------------------------------------------- clarify-hard-halt

fn clarify_hard_halt_cases() -> Vec<ParityCase> {
    vec![
        // Unconditional rc 0; the detail log is contained inside DESIGN_TMPDIR and
        // the stage-terminal-state bridge writes its wire env.
        parity_case(
            "design-step0-clarify-hard-halt-contained",
            &args(&[
                "step0-clarify-hard-halt",
                "--plugin-root",
                "{sandbox}",
                "--claude-pid",
                "4242",
            ]),
            design_dir_seed(),
            &design_tmpdir_env(),
        ),
        // A detail log outside DESIGN_TMPDIR is rejected and reset to the default
        // in-tmpdir path.
        parity_case(
            "design-step0-clarify-hard-halt-escaping-detail-log",
            &args(&[
                "step0-clarify-hard-halt",
                "--plugin-root",
                "{sandbox}",
                "--claude-pid",
                "4242",
                "--failure-detail-log",
                "{sandbox}/escapes.log",
            ]),
            design_dir_seed(),
            &design_tmpdir_env(),
        ),
    ]
}

// ------------------------------------------------------------- route and init

const PLAIN_BODY: &str = "## Fixture issue\n\nJust prose.\n";

fn route_body_seed() -> Vec<SeedFile> {
    vec![
        SeedFile::text(&format!("{DESIGN_RELATIVE}/.keep"), ""),
        SeedFile::text(&format!("{DESIGN_RELATIVE}/issue-body.txt"), PLAIN_BODY),
    ]
}

fn route_cases() -> Vec<ParityCase> {
    vec![
        // No ISSUE_NUMBER: the GitHub read is skipped, `design route` decides
        // `proceed` from the seeded body/empty title, and the folded init driver
        // runs `session write-design-env` (env-refresh-failed without a live
        // session) — the deterministic proceed→init wire path.
        parity_case(
            "design-step0-route-proceed-folded-init",
            &args(&[
                "step0-route",
                "--plugin-root",
                "{sandbox}",
                "--claude-pid",
                "4242",
            ]),
            route_body_seed(),
            &design_tmpdir_env(),
        ),
        // A lifecycle-reject title cancels via the title filter with no init.
        parity_case(
            "design-step0-route-cancel-title-filter",
            &args(&[
                "step0-route",
                "--plugin-root",
                "{sandbox}",
                "--claude-pid",
                "4242",
            ]),
            route_body_seed(),
            &[
                ("DESIGN_TMPDIR", "{sandbox}/design"),
                ("ISSUE_TITLE", "[IMPLEMENTING] Fix the widget"),
            ],
        ),
    ]
}

fn init_cases() -> Vec<ParityCase> {
    vec![parity_case(
        "design-step0-init-env-refresh-failed",
        &args(&[
            "step0-init",
            "--plugin-root",
            "{sandbox}",
            "--claude-pid",
            "4242",
        ]),
        route_body_seed(),
        &[
            ("DESIGN_TMPDIR", "{sandbox}/design"),
            ("SESSION_ID", "bad session id"),
        ],
    )]
}

#[test]
fn design_step0_migrated_verbs_match_frozen_python_reference() {
    let goldens = fixture_directory().join("goldens");
    for case in settle_cases()
        .into_iter()
        .chain(parse_cases())
        .chain(wrapper_error_cases())
        .chain(abort_cleanup_cases())
        .chain(sentinel_cases())
        .chain(clarify_hard_halt_cases())
        .chain(route_cases())
        .chain(init_cases())
    {
        assert_case(&case, &goldens.join(format!("{}.golden.json", case.name)))
            .unwrap_or_else(|error| panic!("{error}"));
    }
}
