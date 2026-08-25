//! Golden-driven black-box contracts for `implement cleanup` and `implement-finalize`.

#![cfg(unix)]

#[path = "support/recorded.rs"]
#[allow(dead_code)]
mod recorded_support;

use std::{env, path::PathBuf};

use recorded_support::{NormalizationRule, Program, RecordedCase, SeedFile, assert_recorded_case};

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

fn case(
    name: &'static str,
    verb: &str,
    tail: &[&str],
    seeds: Vec<SeedFile>,
) -> RecordedCase {
    let mut arguments = if verb == "cleanup" {
        vec!["implement".to_owned(), "cleanup".to_owned()]
    } else {
        vec!["implement-finalize".to_owned(), verb.to_owned()]
    };
    arguments.extend(tail.iter().map(|value| (*value).to_owned()));
    RecordedCase {
        name,
        program: Program::new(env!("CARGO_BIN_EXE_larch"))
            .args(arguments)
            .env("LARCH_BINARY", env!("CARGO_BIN_EXE_larch")),
        seed_files: seeds,
        side_effect_records: Vec::new(),
        normalization: vec![NormalizationRule::SandboxRoot],
    }
}

fn state_case(name: &'static str, verb: &str, state: &str, mut extra: Vec<SeedFile>) -> RecordedCase {
    extra.push(SeedFile::text("session/finalize-state.sh", state));
    let args = if verb == "postmerge" {
        extra.push(SeedFile::text("session/bail", ""));
        POSTMERGE_ARGS
    } else {
        TMPDIR_ARGS
    };
    case(name, verb, args, extra)
}

fn cleanup_state_case(name: &'static str, state: &str, session_id: Option<&str>) -> RecordedCase {
    let mut seeds = vec![SeedFile::text("session/finalize-state.sh", state)];
    if let Some(session_id) = session_id {
        seeds.push(SeedFile::text("session/session-id", session_id));
    }
    case(name, "cleanup", &["--implement-tmpdir", TMPDIR], seeds)
}

fn with_env(mut case: RecordedCase, key: &str, value: &str) -> RecordedCase {
    case.program = case.program.env(key, value);
    case
}

fn cleanup_empty_ambient_case() -> RecordedCase {
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
fn cleanup_cases() -> Vec<RecordedCase> {
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
fn finalize_state_cases() -> Vec<RecordedCase> {
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

fn assert_cases(cases: impl IntoIterator<Item = RecordedCase>) {
    let goldens = repository_root().join("crates/larch-cli/tests/fixtures/recorded/goldens");
    for case in cases {
        assert_recorded_case(&case, &goldens.join(format!("{}.golden.json", case.name)))
            .unwrap_or_else(|error| panic!("{error}"));
    }
}

#[test]
fn recorded_cleanup_contract() {
    assert_cases(cleanup_cases());
}

#[test]
fn recorded_finalize_state_contract() {
    assert_cases(finalize_state_cases());
}
