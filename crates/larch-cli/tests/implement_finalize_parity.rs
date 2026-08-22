//! Black-box parity for `implement cleanup` and `implement-finalize` (#8793).

#![cfg(unix)]

#[path = "support/parity.rs"]
#[allow(dead_code)]
mod parity_support;

use std::{env, path::PathBuf, process::Command};

use parity_support::{NormalizationRule, ParityCase, Program, SeedFile, assert_case};

const COMMON: &str = concat!(
    "BRANCH_NAME=feature\n",
    "PR_NUMBER=\n",
    "PR_TITLE=Implement feature\n",
    "PR_URL=\n",
    "ISSUE_NUMBER=\n",
    "REPO=\n",
    "DRAFT=false\n",
    "MERGE=false\n",
    "DEFERRED=false\n",
    "REPO_UNAVAILABLE=true\n",
    "PR_CLOSED=false\n",
    "DESIGN_ONLY_DONE=false\n",
    "BAIL_NEEDS_USER_INPUT=false\n",
    "STALL_TRACKING=false\n",
    "DONE_RENAME_APPLIED=false\n",
);
const STATE: &str = "{sandbox}/session/finalize-state.sh";
const BAIL: &str = "{sandbox}/session/bail";
const TMPDIR: &str = "{sandbox}/session";
const POSTMERGE_ARGS: &[&str] = &["--state-file", STATE, "--final-bail-reason-file", BAIL];
const TMPDIR_ARGS: &[&str] = &["--state-file", STATE, "--implement-tmpdir", TMPDIR];
const POSTBUMP_STATE: &str = "BRANCH_NAME=feature\nISSUE_NUMBER=\nPR_TITLE=Title\nREPO=\nREPO_UNAVAILABLE=false\nFORKED_TARGET=false\nBUMP_TYPE=NONE\nNEW_VERSION=\n";

fn repository_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .expect("canonical repository root")
}

fn python_executable() -> PathBuf {
    let output = Command::new("python3")
        .args(["-c", "import sys; print(sys.executable)"])
        .output()
        .expect("resolve Python interpreter");
    assert!(output.status.success());
    PathBuf::from(String::from_utf8(output.stdout).expect("UTF-8").trim())
}

fn case(name: &'static str, verb: &str, tail: &[&str], seeds: Vec<SeedFile>) -> ParityCase {
    case_with_setup(name, verb, tail, seeds, None)
}

fn case_with_setup(
    name: &'static str,
    verb: &str,
    tail: &[&str],
    seeds: Vec<SeedFile>,
    setup: Option<&str>,
) -> ParityCase {
    let root = repository_root();
    let reference = root.join("fixtures/rust-parity/implement_finalize_reference.py");
    let mut python_args = vec![reference.to_string_lossy().into_owned(), verb.to_owned()];
    python_args.extend(tail.iter().map(|value| (*value).to_owned()));
    let mut rust_args = if verb == "cleanup" {
        vec!["implement".to_owned(), "cleanup".to_owned()]
    } else {
        vec!["implement-finalize".to_owned(), verb.to_owned()]
    };
    rust_args.extend(tail.iter().map(|value| (*value).to_owned()));
    let wrap = |executable: PathBuf, arguments: Vec<String>| {
        if let Some(scenario) = setup {
            let fixture = root.join("fixtures/rust-parity/implement_finalize_git_fixture.py");
            let mut wrapped = vec![
                fixture.to_string_lossy().into_owned(),
                scenario.to_owned(),
                executable.to_string_lossy().into_owned(),
            ];
            wrapped.extend(arguments);
            Program::new(python_executable()).args(wrapped)
        } else {
            Program::new(executable).args(arguments)
        }
        .env("PYTHONPATH", &root.join("python").to_string_lossy())
        .env("LARCH_BINARY", env!("CARGO_BIN_EXE_larch"))
    };
    ParityCase {
        name,
        python: wrap(python_executable(), python_args),
        rust: wrap(PathBuf::from(env!("CARGO_BIN_EXE_larch")), rust_args),
        seed_files: seeds,
        side_effect_records: Vec::new(),
        normalization: vec![NormalizationRule::SandboxRoot],
    }
}

fn git_case(name: &'static str, verb: &str, state: &str, scenario: &str) -> ParityCase {
    let mut seeds = vec![
        SeedFile::executable_text(
            ".bin/git",
            "#!/bin/sh\nexec /usr/bin/env PATH=/usr/bin:/bin git \"$@\"\n",
        ),
        SeedFile::text("session/finalize-state.sh", state),
        SeedFile::text("session/bail", ""),
    ];
    if scenario.starts_with("teardown-stall") {
        seeds.push(SeedFile::expanded_text(
            "session/source-env.sh",
            "REPO_ROOT={sandbox}/repo\n",
        ));
        seeds.push(SeedFile::text("session/plan-coverage.json", "not json\n"));
    }
    if scenario == "postbump-checkpoint-corrupt" {
        seeds.push(SeedFile::text("session/.postbump-phase", "UPPERCASE\n"));
    }
    case_with_setup(
        name,
        verb,
        if verb == "postmerge" {
            POSTMERGE_ARGS
        } else {
            TMPDIR_ARGS
        },
        seeds,
        Some(scenario),
    )
}

fn state_case(name: &'static str, verb: &str, state: &str, mut extra: Vec<SeedFile>) -> ParityCase {
    extra.push(SeedFile::text("session/finalize-state.sh", state));
    let args = if verb == "postmerge" {
        extra.push(SeedFile::text("session/bail", ""));
        POSTMERGE_ARGS
    } else {
        TMPDIR_ARGS
    };
    case(name, verb, args, extra)
}

fn cleanup_state_case(name: &'static str, state: &str, session_id: Option<&str>) -> ParityCase {
    let mut seeds = vec![SeedFile::text("session/finalize-state.sh", state)];
    if let Some(session_id) = session_id {
        seeds.push(SeedFile::text("session/session-id", session_id));
    }
    case(name, "cleanup", &["--implement-tmpdir", TMPDIR], seeds)
}

fn with_env(mut case: ParityCase, key: &str, value: &str) -> ParityCase {
    case.python = case.python.env(key, value);
    case.rust = case.rust.env(key, value);
    case
}

fn cleanup_empty_ambient_case() -> ParityCase {
    with_env(
        cleanup_state_case(
            "implement-finalize-cleanup-honors-empty-ambient-identity",
            "EXPECTED_SESSION_ID=owned\nEXPECTED_TMPDIR_BASENAME_PREFIX=other-prefix-\n",
            Some("owned\n"),
        ),
        "EXPECTED_SESSION_ID",
        "",
    )
}

#[rustfmt::skip]
fn cleanup_cases() -> Vec<ParityCase> {
    vec![
        case("implement-finalize-cleanup-help", "cleanup", &["--help"], vec![]),
        case("implement-finalize-cleanup-rejects-root", "cleanup", &["--implement-tmpdir", "/"], vec![]),
        case("implement-finalize-cleanup-rejects-parent-component", "cleanup", &["--implement-tmpdir", "{sandbox}/session/../session"], vec![SeedFile::text("session/finalize-state.sh", "EXPECTED_SESSION_ID=\nEXPECTED_TMPDIR_BASENAME_PREFIX=session\n")]),
        cleanup_state_case("implement-finalize-cleanup-rejects-malformed-state", "BROKEN\n", None),
        cleanup_state_case("implement-finalize-cleanup-removes-owned-session", "EXPECTED_SESSION_ID=owned\nEXPECTED_TMPDIR_BASENAME_PREFIX=other-prefix-\n", Some("owned\n")),
        cleanup_state_case("implement-finalize-cleanup-rejects-session-mismatch", "EXPECTED_SESSION_ID=owned\nEXPECTED_TMPDIR_BASENAME_PREFIX=other-prefix-\n", Some("wrong\n")),
        cleanup_state_case("implement-finalize-cleanup-rejects-missing-session", "EXPECTED_SESSION_ID=owned\nEXPECTED_TMPDIR_BASENAME_PREFIX=other-prefix-\n", None),
        cleanup_state_case("implement-finalize-cleanup-accepts-prefix-only", "EXPECTED_SESSION_ID=\nEXPECTED_TMPDIR_BASENAME_PREFIX=session\n", None),
        cleanup_empty_ambient_case(),
    ]
}

#[rustfmt::skip]
fn finalize_state_cases() -> Vec<ParityCase> {
    vec![
        case("implement-finalize-postbump-help", "postbump", &["--help"], vec![]),
        case("implement-finalize-postmerge-help", "postmerge", &["--help"], vec![]),
        case("implement-finalize-teardown-help", "teardown", &["--help"], vec![]),
        case("implement-finalize-postbump-rejects-missing-arguments", "postbump", &[], vec![]),
        case("implement-finalize-postmerge-rejects-missing-arguments", "postmerge", &[], vec![]),
        case("implement-finalize-teardown-rejects-missing-arguments", "teardown", &[], vec![]),
        case("implement-finalize-postmerge-rejects-unknown-option", "postmerge", &["--state-file", STATE, "--final-bail-reason-file", BAIL, "--unknown"], vec![SeedFile::text("session/finalize-state.sh", COMMON), SeedFile::text("session/bail", "")]),
        case(
            "implement-finalize-postmerge-missing-state",
            "postmerge",
            &["--state-file", "{sandbox}/session/missing", "--final-bail-reason-file", BAIL],
            vec![SeedFile::text("session/bail", "")],
        ),
        state_case(
            "implement-finalize-postmerge-rejects-duplicate-state",
            "postmerge",
            "DRAFT=false\nDRAFT=true\n",
            vec![],
        ),
        state_case("implement-finalize-postmerge-rejects-malformed-bool", "postmerge", &COMMON.replace("MERGE=false", "MERGE=yes"), vec![]),
        state_case("implement-finalize-postmerge-rejects-malformed-state", "postmerge", "BROKEN\n", vec![]),
        state_case("implement-finalize-postmerge-rejects-missing-key", "postmerge", "DRAFT=false\n", vec![]),
        case("implement-finalize-teardown-rejects-root-state", "teardown", &["--state-file", "/", "--implement-tmpdir", TMPDIR], vec![]),
        case("implement-finalize-teardown-rejects-root-tmpdir", "teardown", &["--state-file", STATE, "--implement-tmpdir", "/"], vec![SeedFile::text("session/finalize-state.sh", COMMON)]),
        case("implement-finalize-teardown-rejects-state-outside-tmpdir", "teardown", &["--state-file", "{sandbox}/outside-state.sh", "--implement-tmpdir", TMPDIR], vec![SeedFile::text("outside-state.sh", COMMON)]),
        case("implement-finalize-postmerge-rejects-root-bail-file", "postmerge", &["--state-file", STATE, "--final-bail-reason-file", "/"], vec![SeedFile::text("session/finalize-state.sh", COMMON)]),
        state_case(
            "implement-finalize-postmerge-skips-draft",
            "postmerge",
            &COMMON.replace("DRAFT=false", "DRAFT=true"),
            vec![],
        ),
        state_case("implement-finalize-postmerge-skips-merge-false", "postmerge", COMMON, vec![]),
        state_case("implement-finalize-postmerge-rejects-main-branch", "postmerge", &COMMON.replace("MERGE=false", "MERGE=true").replace("BRANCH_NAME=feature", "BRANCH_NAME=main"), vec![]),
        state_case("implement-finalize-postmerge-reports-non-repository", "postmerge", &COMMON.replace("MERGE=false", "MERGE=true"), vec![]),
        state_case(
            "implement-finalize-postmerge-skips-state-bail",
            "postmerge",
            &format!("{COMMON}FINAL_BAIL_REASON=blocked\n").replace("MERGE=false", "MERGE=true"),
            vec![],
        ),
        state_case(
            "implement-finalize-postbump-rejects-version",
            "postbump",
            "BRANCH_NAME=feature\nISSUE_NUMBER=\nPR_TITLE=Title\nREPO=\nREPO_UNAVAILABLE=true\nFORKED_TARGET=false\nBUMP_TYPE=PATCH\nNEW_VERSION=v1.2.3\n",
            vec![],
        ),
        state_case("implement-finalize-postbump-rejects-bump-type", "postbump", &POSTBUMP_STATE.replace("BUMP_TYPE=NONE", "BUMP_TYPE=BREAKING"), vec![]),
        state_case("implement-finalize-postbump-rejects-empty-branch", "postbump", &POSTBUMP_STATE.replace("BRANCH_NAME=feature", "BRANCH_NAME="), vec![]),
        state_case("implement-finalize-postbump-rejects-missing-version", "postbump", &POSTBUMP_STATE.replace("BUMP_TYPE=NONE", "BUMP_TYPE=PATCH"), vec![]),
        state_case("implement-finalize-postbump-reports-non-repository", "postbump", POSTBUMP_STATE, vec![]),
        state_case("implement-finalize-teardown-deactivates-run", "teardown", &format!("{COMMON}RUN_ID=run-8793\n"), vec![]),
        state_case("implement-finalize-teardown-preserves-stall-without-repository", "teardown", &COMMON.replace("STALL_TRACKING=false", "STALL_TRACKING=true"), vec![]),
        state_case("implement-finalize-teardown-skips-unowned-cleanup", "teardown", COMMON, vec![]),
        state_case(
            "implement-finalize-teardown-cleans-owned-session",
            "teardown",
            &format!("{COMMON}EXPECTED_SESSION_ID=owned\nEXPECTED_TMPDIR_BASENAME_PREFIX=other-\n"),
            vec![SeedFile::text("session/session-id", "owned\n")],
        ),
    ]
}

#[rustfmt::skip]
fn finalize_git_cases() -> Vec<ParityCase> {
    vec![
        git_case("implement-finalize-postbump-remote-absent", "postbump", POSTBUMP_STATE, "postbump-absent"),
        git_case("implement-finalize-postbump-repo-unavailable", "postbump", &POSTBUMP_STATE.replace("REPO_UNAVAILABLE=false", "REPO_UNAVAILABLE=true"), "postbump-absent"),
        git_case("implement-finalize-postbump-rejects-branch-mismatch", "postbump", &POSTBUMP_STATE.replace("BRANCH_NAME=feature", "BRANCH_NAME=other"), "postbump-absent"),
        git_case("implement-finalize-postbump-rejects-corrupt-checkpoint", "postbump", POSTBUMP_STATE, "postbump-checkpoint-corrupt"),
        git_case("implement-finalize-postbump-rejects-protected-branch", "postbump", &POSTBUMP_STATE.replace("BRANCH_NAME=feature", "BRANCH_NAME=main"), "postbump-main"),
        git_case("implement-finalize-postbump-force-pushes", "postbump", POSTBUMP_STATE, "postbump-present"),
        git_case("implement-finalize-postbump-reports-conflicts", "postbump", POSTBUMP_STATE, "postbump-conflict"),
        git_case(
            "implement-finalize-postmerge-cleans-branch",
            "postmerge",
            &COMMON
                .replace("PR_NUMBER=", "PR_NUMBER=7")
                .replace("MERGE=false", "MERGE=true"),
            "postmerge",
        ),
        git_case(
            "implement-finalize-postmerge-does-not-borrow-title-suffix",
            "postmerge",
            &COMMON
                .replace("PR_TITLE=Implement feature", "PR_TITLE=Wrong title (#7)")
                .replace("MERGE=false", "MERGE=true"),
            "postmerge",
        ),
        git_case("implement-finalize-postmerge-handles-missing-local-branch", "postmerge", &COMMON.replace("BRANCH_NAME=feature", "BRANCH_NAME=missing").replace("PR_NUMBER=", "PR_NUMBER=7").replace("MERGE=false", "MERGE=true"), "postmerge"),
        git_case("implement-finalize-postmerge-rejects-invalid-local-branch", "postmerge", &COMMON.replace("BRANCH_NAME=feature", "BRANCH_NAME=bad ref").replace("PR_NUMBER=", "PR_NUMBER=7").replace("MERGE=false", "MERGE=true"), "postmerge"),
        git_case("implement-finalize-postmerge-reports-empty-title", "postmerge", &COMMON.replace("PR_TITLE=Implement feature", "PR_TITLE=").replace("PR_NUMBER=", "PR_NUMBER=7").replace("MERGE=false", "MERGE=true"), "postmerge"),
        git_case("implement-finalize-postmerge-preserves-invalid-title-suffix", "postmerge", &COMMON.replace("PR_TITLE=Implement feature", "PR_TITLE=Implement feature (#x)").replace("PR_NUMBER=", "PR_NUMBER=7").replace("MERGE=false", "MERGE=true"), "postmerge"),
        with_env(
            git_case(
                "implement-finalize-postmerge-uses-ambient-branch-fallback",
                "postmerge",
                &COMMON
                    .replace("BRANCH_NAME=feature", "BRANCH_NAME=")
                    .replace("PR_NUMBER=", "PR_NUMBER=7")
                    .replace("MERGE=false", "MERGE=true"),
                "postmerge",
            ),
            "BRANCH",
            "feature",
        ),
        git_case(
            "implement-finalize-teardown-preserves-stall",
            "teardown",
            &format!("{}ISSUE=8793\nSTALL_STEP=step-8\n", COMMON.replace("REPO=", "REPO=character-ai/larch").replace("STALL_TRACKING=false", "STALL_TRACKING=true")),
            "teardown-stall",
        ),
        git_case("implement-finalize-teardown-preserves-clean-stall", "teardown", &format!("{}ISSUE=8793\nSTALL_STEP=step-8\n", COMMON.replace("REPO=", "REPO=character-ai/larch").replace("STALL_TRACKING=false", "STALL_TRACKING=true")), "teardown-stall-clean"),
    ]
}

fn assert_cases(cases: Vec<ParityCase>) {
    let goldens = repository_root().join("fixtures/rust-parity/goldens");
    for case in cases {
        assert_case(&case, &goldens.join(format!("{}.golden.json", case.name)))
            .unwrap_or_else(|error| panic!("{error}"));
    }
}

#[test]
fn cleanup_matches_the_frozen_python_owner() {
    assert_cases(cleanup_cases());
}

#[test]
fn finalize_matches_the_frozen_python_owner() {
    assert_cases(finalize_state_cases());
    assert_cases(finalize_git_cases());
}
