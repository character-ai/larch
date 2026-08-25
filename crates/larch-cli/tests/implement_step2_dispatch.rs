//! Black-box coverage for the four Rust-owned Step 2 dispatch verbs (#8623).
//!
//! `implement step2-dispatch`, `implement run-dispatch`, `implement
//! step-2-post-dispatch`, and `implement kill-active-leg` all publish a
//! `KEY=value` contract the `/implement` orchestrator routes on. These cases
//! drive real temporary repositories through the branches that need no external
//! implementer: the Claude fallback, the usage refusals, the post-dispatch
//! branch expectation, and the stranded active-leg cleanup.

use std::{
    fs,
    path::{Path, PathBuf},
    process::Command,
};

use assert_cmd::Command as AssertCommand;
use tempfile::TempDir;

struct Fixture {
    _root: TempDir,
    repo: PathBuf,
    tmpdir: PathBuf,
}

fn git(repo: &Path, arguments: &[&str]) {
    let status = Command::new("git")
        .args(arguments)
        .current_dir(repo)
        .env("GIT_CONFIG_GLOBAL", "/dev/null")
        .env("GIT_CONFIG_SYSTEM", "/dev/null")
        .status()
        .expect("run git");
    assert!(status.success(), "git {arguments:?} failed");
}

/// Seed a committed repository plus the session artifacts Step 2 requires.
fn fixture(branch: &str) -> Fixture {
    let root = TempDir::new().expect("temp root");
    let repo = root.path().join("repo");
    let tmpdir = root.path().join("tmp");
    fs::create_dir_all(&repo).expect("repo");
    fs::create_dir_all(&tmpdir).expect("tmpdir");
    git(&repo, &["init", "--quiet", "-b", branch]);
    git(&repo, &["config", "user.email", "larch@example.invalid"]);
    git(&repo, &["config", "user.name", "larch"]);
    git(&repo, &["config", "commit.gpgsign", "false"]);
    fs::write(repo.join("README.md"), "base\n").expect("readme");
    git(&repo, &["add", "README.md"]);
    git(&repo, &["commit", "--quiet", "-m", "base"]);

    let repo = fs::canonicalize(&repo).expect("canonical repo");
    let tmpdir = fs::canonicalize(&tmpdir).expect("canonical tmpdir");
    fs::write(tmpdir.join("plan.txt"), "## Files to modify\n").expect("plan");
    fs::write(tmpdir.join("feature-description.txt"), "feature\n").expect("feature");
    fs::write(
        tmpdir.join("session-env.sh"),
        format!("REPO_ROOT={}\n", repo.display()),
    )
    .expect("session env");
    fs::write(tmpdir.join("session-id"), "step2-parity-session\n").expect("session id");
    Fixture {
        _root: root,
        repo,
        tmpdir,
    }
}

fn run(fixture: &Fixture, verb: &str, arguments: &[&str]) -> (i32, String, String) {
    let output = AssertCommand::cargo_bin("larch")
        .expect("larch binary")
        .args(["implement", verb])
        .args(arguments)
        .env("IMPLEMENT_TMPDIR", &fixture.tmpdir)
        .env("CLAUDE_PLUGIN_ROOT", workspace_root())
        .current_dir(&fixture.repo)
        .output()
        .expect("run dispatch verb");
    (
        output.status.code().unwrap_or(-1),
        String::from_utf8_lossy(&output.stdout).into_owned(),
        String::from_utf8_lossy(&output.stderr).into_owned(),
    )
}

fn workspace_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

fn kv(stdout: &str, key: &str) -> String {
    stdout
        .lines()
        .filter_map(|line| line.strip_prefix(&format!("{key}=")))
        .next_back()
        .unwrap_or_default()
        .to_owned()
}

// ---------------------------------------------------------------------------
// step2-dispatch
// ---------------------------------------------------------------------------

#[test]
fn step2_dispatch_relays_the_claude_fallback_envelope_with_edit_authority() {
    let fixture = fixture("feature/parity");
    let tmpdir = fixture.tmpdir.display().to_string();
    let plan = fixture.tmpdir.join("plan.txt").display().to_string();
    let feature = fixture
        .tmpdir
        .join("feature-description.txt")
        .display()
        .to_string();

    let (code, stdout, stderr) = run(
        &fixture,
        "step2-dispatch",
        &[
            "--tmpdir",
            &tmpdir,
            "--plan-file",
            &plan,
            "--feature-file",
            &feature,
            "--coder",
            "claude",
        ],
    );

    assert_eq!(code, 0, "stdout: {stdout}\nstderr: {stderr}");
    assert_eq!(kv(&stdout, "STATUS"), "claude_fallback");
    assert_eq!(
        kv(&stdout, "ORCHESTRATOR_EDIT_AUTHORITY"),
        "allowed",
        "the Claude fallback is the one branch that allows orchestrator edits"
    );
    assert_eq!(
        kv(&stdout, "TOOL"),
        "",
        "the direct Claude route names no external tool"
    );
    assert!(
        fixture.tmpdir.join("step2-baseline.txt").is_file(),
        "the fallback still freezes the Step 2 baseline"
    );
}

#[test]
fn step2_dispatch_refuses_an_unknown_coder_before_touching_the_repository() {
    let fixture = fixture("feature/parity");
    let tmpdir = fixture.tmpdir.display().to_string();
    let plan = fixture.tmpdir.join("plan.txt").display().to_string();
    let feature = fixture
        .tmpdir
        .join("feature-description.txt")
        .display()
        .to_string();

    let (code, _stdout, stderr) = run(
        &fixture,
        "step2-dispatch",
        &[
            "--tmpdir",
            &tmpdir,
            "--plan-file",
            &plan,
            "--feature-file",
            &feature,
            "--coder",
            "gemini",
        ],
    );

    assert_eq!(code, 2);
    assert!(stderr.contains("--coder"), "stderr: {stderr}");
}

#[test]
fn step2_dispatch_rejects_a_difficulty_outside_the_tier_set() {
    let fixture = fixture("feature/parity");
    let tmpdir = fixture.tmpdir.display().to_string();
    let plan = fixture.tmpdir.join("plan.txt").display().to_string();
    let feature = fixture
        .tmpdir
        .join("feature-description.txt")
        .display()
        .to_string();

    let (code, _stdout, stderr) = run(
        &fixture,
        "step2-dispatch",
        &[
            "--tmpdir",
            &tmpdir,
            "--plan-file",
            &plan,
            "--feature-file",
            &feature,
            "--coder",
            "claude",
            "--difficulty",
            "EPIC",
        ],
    );

    assert_eq!(code, 2);
    assert!(stderr.contains("--difficulty"), "stderr: {stderr}");
}

#[test]
fn step2_dispatch_help_matches_the_retired_argparse_usage() {
    let fixture = fixture("feature/parity");

    let (code, stdout, _stderr) = run(&fixture, "step2-dispatch", &["--help"]);

    assert_eq!(code, 0);
    assert!(
        stdout.starts_with("usage: cli.py implement step2-dispatch [-h] --tmpdir TMPDIR"),
        "stdout: {stdout}"
    );
    assert!(stdout.contains("--completion-retry"), "stdout: {stdout}");
}

// ---------------------------------------------------------------------------
// run-dispatch
// ---------------------------------------------------------------------------

#[test]
fn run_dispatch_requires_the_bgjob_child_and_merge_env_flags_together() {
    let fixture = fixture("feature/parity");
    let tmpdir = fixture.tmpdir.display().to_string();

    let (code, _stdout, stderr) = run(
        &fixture,
        "run-dispatch",
        &[
            "--implement-tmpdir",
            &tmpdir,
            "--coder",
            "claude",
            "--bgjob-child",
        ],
    );

    assert_eq!(code, 2);
    assert!(
        stderr.contains("--bgjob-child and --merge-result-env must be supplied together"),
        "stderr: {stderr}"
    );
}

#[test]
fn run_dispatch_refuses_a_tmpdir_that_is_not_a_directory() {
    let fixture = fixture("feature/parity");
    let missing = fixture.tmpdir.join("absent").display().to_string();

    let (code, _stdout, stderr) = run(
        &fixture,
        "run-dispatch",
        &["--implement-tmpdir", &missing, "--coder", "claude"],
    );

    assert_eq!(code, 2);
    assert!(
        stderr.contains("--implement-tmpdir not a directory"),
        "stderr: {stderr}"
    );
}

#[test]
fn run_dispatch_refuses_a_missing_answers_path() {
    let fixture = fixture("feature/parity");
    let tmpdir = fixture.tmpdir.display().to_string();
    let answers = fixture.tmpdir.join("absent.json").display().to_string();

    let (code, _stdout, stderr) = run(
        &fixture,
        "run-dispatch",
        &[
            "--implement-tmpdir",
            &tmpdir,
            "--coder",
            "claude",
            "--answers",
            &answers,
        ],
    );

    assert_eq!(code, 2);
    assert!(
        stderr.contains("--answers path does not exist"),
        "stderr: {stderr}"
    );
}

#[test]
fn run_dispatch_help_matches_the_retired_argparse_usage() {
    let fixture = fixture("feature/parity");

    let (code, stdout, _stderr) = run(&fixture, "run-dispatch", &["--help"]);

    assert_eq!(code, 0);
    assert!(
        stdout.starts_with("usage: cli.py implement run-dispatch [-h]"),
        "stdout: {stdout}"
    );
    assert!(stdout.contains("--merge-result-env"), "stdout: {stdout}");
}

// ---------------------------------------------------------------------------
// step-2-post-dispatch
// ---------------------------------------------------------------------------

#[test]
fn post_dispatch_continues_and_seeds_the_ship_context_on_the_expected_branch() {
    let fixture = fixture("feature/parity");
    fs::write(fixture.tmpdir.join("manifest.json"), "{}\n").expect("manifest");
    fs::write(
        fixture.tmpdir.join("bootstrap-routing.env"),
        "coder=codex\n",
    )
    .expect("routing");

    let (code, stdout, stderr) = run(
        &fixture,
        "step-2-post-dispatch",
        &["--expected-branch", "feature/parity"],
    );

    assert_eq!(code, 0, "stdout: {stdout}\nstderr: {stderr}");
    assert_eq!(kv(&stdout, "POST_DISPATCH_NEXT"), "continue");
    assert_eq!(kv(&stdout, "BRANCH"), "feature/parity");
    assert_eq!(kv(&stdout, "COMMIT_SHA").len(), 7, "stdout: {stdout}");
    let seed = fs::read_to_string(fixture.tmpdir.join("ship-seed-input.env")).expect("seed");
    assert!(
        seed.contains(&format!(
            "MANIFEST_PATH={}",
            fixture.tmpdir.join("manifest.json").display()
        )),
        "seed: {seed}"
    );
    assert!(seed.contains("TOOL_LABEL=Codex"), "seed: {seed}");
    assert!(seed.contains("DISPATCHER_COMMITTED=true"), "seed: {seed}");
}

#[test]
fn post_dispatch_bails_when_the_checked_out_branch_is_not_the_expected_one() {
    let fixture = fixture("main");

    let (code, stdout, stderr) = run(
        &fixture,
        "step-2-post-dispatch",
        &["--expected-branch", "feature/parity"],
    );

    assert_eq!(code, 0, "stdout: {stdout}\nstderr: {stderr}");
    assert_eq!(kv(&stdout, "POST_DISPATCH_NEXT"), "bail");
    assert_eq!(kv(&stdout, "BAIL_REASON"), "main-branch-post-dispatch");
    assert_eq!(kv(&stdout, "BRANCH"), "main");
    let seed = fs::read_to_string(fixture.tmpdir.join("ship-seed-input.env")).expect("seed");
    assert!(
        !seed.contains("DISPATCHER_COMMITTED=true"),
        "a bail never claims the dispatcher committed: {seed}"
    );
}

#[test]
fn post_dispatch_requires_the_expected_branch_flag() {
    let fixture = fixture("main");

    let (code, _stdout, stderr) = run(&fixture, "step-2-post-dispatch", &[]);

    assert_eq!(code, 2);
    assert!(stderr.contains("--expected-branch"), "stderr: {stderr}");
}

// ---------------------------------------------------------------------------
// kill-active-leg
// ---------------------------------------------------------------------------

#[test]
fn kill_active_leg_logs_a_refusal_when_no_owner_token_is_given() {
    let fixture = fixture("main");
    let tmpdir = fixture.tmpdir.display().to_string();

    let (code, _stdout, _stderr) = run(
        &fixture,
        "kill-active-leg",
        &["--implement-tmpdir", &tmpdir],
    );

    assert_eq!(
        code, 0,
        "a shell trap invokes this, so a refusal is never a driver failure"
    );
    let log =
        fs::read_to_string(fixture.tmpdir.join("active-leg-kill.log.jsonl")).expect("kill log");
    assert!(log.contains("missing-owner-token"), "log: {log}");
    assert!(log.contains("\"event\":\"refusal\""), "log: {log}");
}

#[test]
fn kill_active_leg_refuses_and_removes_the_retired_pgid_sidecar() {
    let fixture = fixture("main");
    let tmpdir = fixture.tmpdir.display().to_string();
    let sidecar = fixture.tmpdir.join(".active-leg-pgid");
    fs::write(&sidecar, "4242\n").expect("sidecar");

    let (code, _stdout, _stderr) = run(
        &fixture,
        "kill-active-leg",
        &["--implement-tmpdir", &tmpdir, "--owner-token", "token-a"],
    );

    assert_eq!(code, 0);
    assert!(
        !sidecar.exists(),
        "a bare pgid carries no identity, so it is removed unconditionally"
    );
    let log =
        fs::read_to_string(fixture.tmpdir.join("active-leg-kill.log.jsonl")).expect("kill log");
    assert!(log.contains("legacy-active-leg-pgid-refused"), "log: {log}");
}

#[test]
fn kill_active_leg_removes_a_malformed_record_and_logs_the_reason() {
    let fixture = fixture("main");
    let tmpdir = fixture.tmpdir.display().to_string();
    let record = fixture.tmpdir.join(".active-leg.json");
    fs::write(&record, "{not json\n").expect("record");

    let (code, _stdout, _stderr) = run(
        &fixture,
        "kill-active-leg",
        &["--implement-tmpdir", &tmpdir, "--owner-token", "token-a"],
    );

    assert_eq!(code, 0);
    assert!(!record.exists(), "an unparseable record is never retained");
    let log =
        fs::read_to_string(fixture.tmpdir.join("active-leg-kill.log.jsonl")).expect("kill log");
    assert!(log.contains("malformed-active-leg-record"), "log: {log}");
}

#[test]
fn kill_active_leg_leaves_a_record_owned_by_another_token_untouched() {
    let fixture = fixture("main");
    let tmpdir = fixture.tmpdir.display().to_string();
    let record = fixture.tmpdir.join(".active-leg.json");
    fs::write(
        &record,
        "{\"owner_token\":\"token-b\",\"pid\":4242,\"pgid\":4242,\
         \"start_time\":\"1\",\"command_signature\":\"other\"}\n",
    )
    .expect("record");

    let (code, _stdout, _stderr) = run(
        &fixture,
        "kill-active-leg",
        &["--implement-tmpdir", &tmpdir, "--owner-token", "token-a"],
    );

    assert_eq!(code, 0);
    assert!(
        record.exists(),
        "another live owner published this record; it is not ours to clear"
    );
    assert!(
        !fixture.tmpdir.join("active-leg-kill.log.jsonl").exists(),
        "a foreign record produces no kill-log entry at all"
    );
}

#[test]
fn kill_active_leg_refuses_a_record_whose_identity_no_longer_matches() {
    let fixture = fixture("main");
    let tmpdir = fixture.tmpdir.display().to_string();
    let record = fixture.tmpdir.join(".active-leg.json");
    // A live pid whose recorded start time cannot be this process's: refusing is
    // the only safe outcome, because the pid may have been recycled.
    fs::write(
        &record,
        format!(
            "{{\"owner_token\":\"token-a\",\"pid\":{pid},\"pgid\":{pid},\
             \"start_time\":\"1\",\"command_signature\":\"stale\"}}\n",
            pid = std::process::id(),
        ),
    )
    .expect("record");

    let (code, _stdout, _stderr) = run(
        &fixture,
        "kill-active-leg",
        &["--implement-tmpdir", &tmpdir, "--owner-token", "token-a"],
    );

    assert_eq!(code, 0);
    assert!(
        record.exists(),
        "an unproven identity is refused, not terminated"
    );
    let log =
        fs::read_to_string(fixture.tmpdir.join("active-leg-kill.log.jsonl")).expect("kill log");
    assert!(log.contains("\"event\":\"refusal\""), "log: {log}");
}

#[test]
fn kill_active_leg_help_matches_the_retired_argparse_usage() {
    let fixture = fixture("main");

    let (code, stdout, _stderr) = run(&fixture, "kill-active-leg", &["--help"]);

    assert_eq!(code, 0);
    assert!(
        stdout.starts_with("usage: cli.py implement kill-active-leg [-h] --implement-tmpdir"),
        "stdout: {stdout}"
    );
    assert!(stdout.contains("--owner-token"), "stdout: {stdout}");
}
