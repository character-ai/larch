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

fn parity_case(name: &'static str, arguments: &[String], seeds: Vec<SeedFile>) -> ParityCase {
    let root = repository_root();
    let reference = fixture_directory().join("design_router_migrated_reference.py");
    let python_path = root.join("python");
    let plugin_root = root.to_string_lossy().into_owned();
    let path = env::var("PATH").expect("PATH");
    ParityCase {
        name,
        python: Program::new(python_executable())
            .args(
                std::iter::once(reference.to_string_lossy().into_owned())
                    .chain(arguments.iter().cloned()),
            )
            .env("PYTHONPATH", &python_path.to_string_lossy())
            .env("CLAUDE_PLUGIN_ROOT", &plugin_root)
            // The frozen reference routes title-eligibility and session
            // subprocesses at the built binary; see its docstring.
            .env("LARCH_BINARY", env!("CARGO_BIN_EXE_larch"))
            .env("LARCH_QUIET_DISABLE", "1")
            .env("COLUMNS", "1000")
            .env("PATH", &path),
        rust: Program::new(env!("CARGO_BIN_EXE_larch"))
            .args(std::iter::once("design".to_owned()).chain(arguments.iter().cloned()))
            .env("CLAUDE_PLUGIN_ROOT", &plugin_root)
            .env("LARCH_QUIET_DISABLE", "1")
            .env("COLUMNS", "1000")
            .env("PATH", &path),
        seed_files: seeds,
        side_effect_records: Vec::new(),
        normalization: vec![NormalizationRule::SandboxRoot],
    }
}

fn args(values: &[&str]) -> Vec<String> {
    values.iter().map(|value| (*value).to_owned()).collect()
}

// ---------------------------------------------------------------- parse-flags

fn parse_flags_cases() -> Vec<ParityCase> {
    vec![
        parity_case(
            "design-parse-flags-no-args",
            &args(&["parse-flags"]),
            Vec::new(),
        ),
        parity_case(
            "design-parse-flags-flags-both-sides-of-issue",
            &args(&[
                "parse-flags",
                "-p",
                "123",
                "--brainstorm",
                "--run-id",
                "rid-1",
                "--difficulty",
                "hard",
                "--skip-approve",
                "--per-round-approval",
                "--no-dedup",
            ]),
            Vec::new(),
        ),
        parity_case(
            "design-parse-flags-issue-then-nonflag-ignored",
            &args(&["parse-flags", "7", "trailing", "words"]),
            Vec::new(),
        ),
        parity_case(
            "design-parse-flags-verbal-tail-keeps-flaglike-tokens",
            &args(&["parse-flags", "-p", "add", "a", "--hard", "widget"]),
            Vec::new(),
        ),
        parity_case(
            "design-parse-flags-double-dash-issue",
            &args(&["parse-flags", "--brainstorm", "--", "42"]),
            Vec::new(),
        ),
        parity_case(
            "design-parse-flags-double-dash-verbal",
            &args(&["parse-flags", "--", "--hard", "literal", "text"]),
            Vec::new(),
        ),
        parity_case(
            "design-parse-flags-lifecycle-parent-context-leading",
            &args(&[
                "parse-flags",
                "--lifecycle-parent-context",
                "{sandbox}/context.md",
                "123",
            ]),
            Vec::new(),
        ),
        parity_case(
            "design-parse-flags-lifecycle-parent-context-misplaced",
            &args(&["parse-flags", "123", "--lifecycle-parent-context", "ctx"]),
            Vec::new(),
        ),
        parity_case(
            "design-parse-flags-output-success",
            &args(&[
                "parse-flags",
                "--output",
                "{sandbox}/parsed.env",
                "-p",
                "123",
                "--run-id",
                "it's-rid",
            ]),
            Vec::new(),
        ),
        parity_case(
            "design-parse-flags-output-write-failure",
            &args(&[
                "parse-flags",
                "--output",
                "{sandbox}/missing-parent/parsed.env",
                "123",
            ]),
            Vec::new(),
        ),
    ]
}

fn parse_flags_rejection_cases() -> Vec<ParityCase> {
    vec![
        parity_case(
            "design-parse-flags-rejects-hard",
            &args(&["parse-flags", "--hard", "123"]),
            Vec::new(),
        ),
        parity_case(
            "design-parse-flags-rejects-unknown-flag",
            &args(&["parse-flags", "123", "--bogus"]),
            Vec::new(),
        ),
        parity_case(
            "design-parse-flags-rejects-duplicate-skip-approve",
            &args(&["parse-flags", "--skip-approve", "-s", "123"]),
            Vec::new(),
        ),
        parity_case(
            "design-parse-flags-rejects-duplicate-per-round-approval",
            &args(&[
                "parse-flags",
                "--per-round-approval",
                "--per-round-approval",
            ]),
            Vec::new(),
        ),
        parity_case(
            "design-parse-flags-rejects-flag-valued-run-id",
            &args(&["parse-flags", "--run-id", "--partition"]),
            Vec::new(),
        ),
        parity_case(
            "design-parse-flags-rejects-missing-run-id-value",
            &args(&["parse-flags", "123", "--run-id"]),
            Vec::new(),
        ),
        parity_case(
            "design-parse-flags-rejects-bad-difficulty",
            &args(&["parse-flags", "--difficulty", "extreme"]),
            Vec::new(),
        ),
        parity_case(
            "design-parse-flags-rejects-newline-in-value",
            &args(&["parse-flags", "--run-id", "line one\nline two", "123"]),
            Vec::new(),
        ),
        parity_case(
            "design-parse-flags-rejects-newline-in-verbal",
            &args(&["parse-flags", "verbal", "with\nnewline"]),
            Vec::new(),
        ),
        parity_case(
            "design-parse-flags-rejects-public-output",
            &args(&["parse-flags", "123", "--output", "{sandbox}/x.env"]),
            Vec::new(),
        ),
        parity_case(
            "design-parse-flags-rejects-second-output-after-strip",
            &args(&[
                "parse-flags",
                "--output",
                "{sandbox}/parsed.env",
                "--output",
                "{sandbox}/again.env",
            ]),
            Vec::new(),
        ),
    ]
}

// ---------------------------------------------------------------------- route

const SESSION_RELATIVE: &str = ".home/.cache/larch/sessions/design-router-parity";

fn session_dir() -> String {
    format!("{{sandbox}}/{SESSION_RELATIVE}")
}

fn body_path() -> String {
    format!("{}/issue-body.txt", session_dir())
}

const PLAIN_BODY: &str = "## Fixture issue\n\nJust prose.\n";
const PLAN_BODY: &str = "## Fixture issue\n\n<!-- larch:plan:start -->\n### NEW: fixture step\ndiff_lines: 1\n<!-- larch:plan:end -->\n";
const RUN_PARAMS: &str = "{\n  \"schema_version\": 3,\n  \"partition_requested\": false,\n  \"brainstorm_requested\": false,\n  \"approve_requested\": false,\n  \"skip_approve_requested\": false,\n  \"difficulty_override\": \"\"\n}\n";

fn body_seed(body: &str) -> Vec<SeedFile> {
    vec![SeedFile::text(
        &format!("{SESSION_RELATIVE}/issue-body.txt"),
        body,
    )]
}

fn route_arguments(title: &str, clarify: &str, extra: &[&str]) -> Vec<String> {
    let mut arguments = args(&[
        "route",
        "--design-tmpdir",
        &session_dir(),
        "--issue",
        "7680",
        "--issue-title",
        title,
        "--issue-body-file",
        &body_path(),
        "--has-clarify-label",
        clarify,
        "--claude-pid",
        "4242",
        "--session-id",
        "sid-1",
    ]);
    arguments.extend(extra.iter().map(|value| (*value).to_owned()));
    arguments
}

fn route_cases() -> Vec<ParityCase> {
    vec![
        parity_case("design-route-help", &args(&["route", "--help"]), Vec::new()),
        parity_case("design-route-no-args", &args(&["route"]), Vec::new()),
        parity_case(
            "design-route-unknown-option",
            &args(&["route", "--nope", "x"]),
            Vec::new(),
        ),
        parity_case(
            "design-route-missing-value",
            &args(&["route", "--issue"]),
            Vec::new(),
        ),
        parity_case(
            "design-route-body-file-not-regular",
            &route_arguments("Add a widget", "false", &[]),
            Vec::new(),
        ),
        parity_case(
            "design-route-proceed",
            &route_arguments("Add a widget", "false", &[]),
            body_seed(PLAIN_BODY),
        ),
        parity_case(
            "design-route-clarify",
            &route_arguments("Add a widget", "true", &[]),
            body_seed(PLAIN_BODY),
        ),
        parity_case(
            "design-route-brainstorm-prefix",
            &route_arguments("brainstorm better caching", "false", &[]),
            body_seed(PLAIN_BODY),
        ),
        parity_case(
            "design-route-already-planned-merges-flags",
            &route_arguments(
                "Add a widget",
                "false",
                &["--brainstorm-requested", "true", "--difficulty", "HARD"],
            ),
            vec![
                SeedFile::text(&format!("{SESSION_RELATIVE}/issue-body.txt"), PLAN_BODY),
                SeedFile::text(&format!("{SESSION_RELATIVE}/run-params.json"), RUN_PARAMS),
            ],
        ),
        parity_case(
            "design-route-already-planned-missing-run-params-warns",
            &route_arguments("Add a widget", "false", &["--partition-requested", "true"]),
            body_seed(PLAN_BODY),
        ),
        parity_case(
            "design-route-lifecycle-reject",
            &route_arguments("[IMPLEMENTING] Fix the widget", "false", &[]),
            body_seed(PLAIN_BODY),
        ),
        parity_case(
            "design-route-archival-reject",
            &route_arguments("[Audit report] Quarterly numbers", "false", &[]),
            body_seed(PLAIN_BODY),
        ),
        parity_case(
            "design-route-designed-plan-special-case",
            &route_arguments("[DESIGNED] Fix the widget", "false", &[]),
            body_seed(PLAN_BODY),
        ),
        parity_case(
            "design-route-designed-plan-clarify",
            &route_arguments("[DESIGNED] Fix the widget", "true", &[]),
            body_seed(PLAN_BODY),
        ),
        parity_case(
            "design-route-designed-without-plan-rejects",
            &route_arguments("[DESIGNED] Fix the widget", "false", &[]),
            body_seed(PLAIN_BODY),
        ),
        // Plan-block grammar edges retired from the Python direct-CLI harness:
        // whitespace-tolerant and empty blocks still read as already-planned,
        // while malformed marker pairs fall through to proceed.
        parity_case(
            "design-route-whitespace-plan-already-planned",
            &route_arguments("Add a widget", "false", &[]),
            body_seed(
                "x\n  <!--   larch:plan:start   -->  \nplan\n  <!--   larch:plan:end   -->\n",
            ),
        ),
        parity_case(
            "design-route-empty-plan-already-planned",
            &route_arguments("Add a widget", "false", &[]),
            body_seed("x\n<!-- larch:plan:start -->\n<!-- larch:plan:end -->\n"),
        ),
        parity_case(
            "design-route-duplicate-plan-blocks-proceed",
            &route_arguments("Add a widget", "false", &[]),
            body_seed(
                "x\n<!-- larch:plan:start -->\nfirst\n<!-- larch:plan:end -->\n<!-- larch:plan:start -->\nsecond\n<!-- larch:plan:end -->\n",
            ),
        ),
        parity_case(
            "design-route-unterminated-plan-proceeds",
            &route_arguments("Add a widget", "false", &[]),
            body_seed("x\n<!-- larch:plan:start -->\nplan only\n"),
        ),
    ]
}

// ------------------------------------------------------------- init-runparams

fn init_arguments(session_id: &str) -> Vec<String> {
    args(&[
        "init-runparams",
        "--design-tmpdir",
        &session_dir(),
        "--issue",
        "7680",
        "--session-id",
        session_id,
        "--claude-pid",
        "4242",
        "--partition-requested",
        "false",
        "--brainstorm-requested",
        "false",
        "--approve-requested",
        "false",
        "--skip-approve-requested",
        "false",
        "--classification",
        "ignored",
    ])
}

fn init_runparams_cases() -> Vec<ParityCase> {
    vec![
        parity_case(
            "design-init-runparams-help",
            &args(&["init-runparams", "--help"]),
            Vec::new(),
        ),
        parity_case(
            "design-init-runparams-no-args",
            &args(&["init-runparams"]),
            Vec::new(),
        ),
        parity_case(
            "design-init-runparams-unknown-option",
            &args(&["init-runparams", "--nope", "x"]),
            Vec::new(),
        ),
        parity_case(
            "design-init-runparams-missing-value",
            &args(&["init-runparams", "--issue"]),
            Vec::new(),
        ),
        // An invalid session id makes `session write-design-env` refuse before
        // any write, exercising the env-refresh-failed row without touching
        // the network-backed rename branch (unit tests own that seam).
        parity_case(
            "design-init-runparams-env-refresh-failed",
            &init_arguments("bad session id"),
            body_seed(PLAIN_BODY),
        ),
    ]
}

fn assert_cases(cases: impl IntoIterator<Item = ParityCase>) {
    let goldens = fixture_directory().join("goldens");
    for case in cases {
        assert_case(&case, &goldens.join(format!("{}.golden.json", case.name)))
            .unwrap_or_else(|error| panic!("{error}"));
    }
}

#[test]
fn design_parse_flags_matches_frozen_python_reference() {
    assert_cases(parse_flags_cases());
}

#[test]
fn design_parse_flags_rejections_match_frozen_python_reference() {
    assert_cases(parse_flags_rejection_cases());
}

#[test]
fn design_route_matches_frozen_python_reference() {
    assert_cases(route_cases());
}

#[test]
fn design_init_runparams_matches_frozen_python_reference() {
    assert_cases(init_runparams_cases());
}
