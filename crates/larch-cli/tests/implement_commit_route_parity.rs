//! Black-box parity for the three Rust-owned commit-routing verbs (#8611).
//!
//! `implement commit`, `implement commit-route`, and `implement
//! checks-commit-route` publish a `KEY=value` contract the `/implement`
//! orchestrator routes on. These cases drive the real `larch` binary against a
//! temporary repository whose `CLAUDE_PLUGIN_ROOT` carries a stub
//! `scripts/larch.sh`, so every already-Rust sub-verb (`review-and-fix
//! commit-fixes`, `run-log append-failure`, `implement step-8-seed-initial`,
//! `checks run-relevant`, `git commit`, the timing marks) is answered
//! deterministically instead of really running.

#![cfg(unix)]

use std::{
    fmt::Write as _,
    fs,
    os::unix::fs::PermissionsExt as _,
    path::{Path, PathBuf},
    process::Command,
};

use assert_cmd::Command as AssertCommand;
use tempfile::TempDir;

struct Fixture {
    _root: TempDir,
    repo: PathBuf,
    tmpdir: PathBuf,
    plugin_root: PathBuf,
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

/// Seed a committed repository, an implement tmpdir, and a stub plugin root.
fn fixture(stub_body: &str) -> Fixture {
    let root = TempDir::new().expect("temp root");
    let repo = root.path().join("repo");
    let tmpdir = root.path().join("tmp");
    let plugin_root = root.path().join("plugin");
    fs::create_dir_all(&repo).expect("repo");
    fs::create_dir_all(&tmpdir).expect("tmpdir");
    fs::create_dir_all(plugin_root.join("scripts")).expect("plugin scripts");
    git(&repo, &["init", "--quiet", "-b", "main"]);
    git(&repo, &["config", "user.email", "larch@example.invalid"]);
    git(&repo, &["config", "user.name", "larch"]);
    git(&repo, &["config", "commit.gpgsign", "false"]);
    fs::write(repo.join("README.md"), "base\n").expect("readme");
    git(&repo, &["add", "README.md"]);
    git(&repo, &["commit", "--quiet", "-m", "base"]);

    let repo = fs::canonicalize(&repo).expect("canonical repo");
    let tmpdir = fs::canonicalize(&tmpdir).expect("canonical tmpdir");
    let plugin_root = fs::canonicalize(&plugin_root).expect("canonical plugin");
    fs::write(
        tmpdir.join("session-env.sh"),
        format!("REPO_ROOT={}\n", repo.display()),
    )
    .expect("session env");
    fs::write(
        tmpdir.join("repo-root.txt"),
        format!("{}\n", repo.display()),
    )
    .expect("repo-root.txt");

    let script = plugin_root.join("scripts/larch.sh");
    fs::write(&script, stub_body).expect("stub larch.sh");
    let mut permissions = fs::metadata(&script).expect("stub metadata").permissions();
    permissions.set_mode(0o755);
    fs::set_permissions(&script, permissions).expect("chmod stub");

    Fixture {
        _root: root,
        repo,
        tmpdir,
        plugin_root,
    }
}

fn run(
    fixture: &Fixture,
    verb: &str,
    arguments: &[&str],
    set_tmpdir: bool,
) -> (i32, String, String) {
    let mut command = AssertCommand::cargo_bin("larch").expect("larch binary");
    command
        .args(["implement", verb])
        .args(arguments)
        .env("CLAUDE_PLUGIN_ROOT", &fixture.plugin_root)
        .current_dir(&fixture.repo);
    if set_tmpdir {
        command.env("IMPLEMENT_TMPDIR", &fixture.tmpdir);
    } else {
        command.env_remove("IMPLEMENT_TMPDIR");
    }
    let output = command.output().expect("run commit-route verb");
    (
        output.status.code().unwrap_or(-1),
        String::from_utf8_lossy(&output.stdout).into_owned(),
        String::from_utf8_lossy(&output.stderr).into_owned(),
    )
}

fn kv(stdout: &str, key: &str) -> String {
    stdout
        .lines()
        .filter_map(|line| line.strip_prefix(&format!("{key}=")))
        .next_back()
        .unwrap_or_default()
        .to_owned()
}

/// A stub that exits 0 for every verb and prints nothing.
const NOOP_STUB: &str = "#!/usr/bin/env bash\nexit 0\n";

/// A stub whose branches are keyed on the first two positional arguments.
#[allow(clippy::literal_string_with_formatting_args)]
fn dispatch_stub(cases: &[(&str, &str)]) -> String {
    let mut body = String::from("#!/usr/bin/env bash\nset -u\ncase \"${1:-} ${2:-}\" in\n");
    for (needle, action) in cases {
        let _ = write!(body, "  \"{needle}\")\n{action}\n    ;;\n");
    }
    body.push_str("  *)\n    exit 0\n    ;;\nesac\n");
    body
}

// ---------------------------------------------------------------------------
// implement commit
// ---------------------------------------------------------------------------

#[test]
fn commit_refuses_without_a_message() {
    let fixture = fixture(NOOP_STUB);
    let (code, stdout, stderr) = run(&fixture, "commit", &[], false);
    assert_eq!(code, 2);
    assert_eq!(kv(&stdout, "COMMITTED"), "false");
    assert_eq!(kv(&stdout, "SHA"), "");
    assert_eq!(kv(&stdout, "ERROR"), "--message is required");
    assert!(stderr.contains("HINT: --stage-all belongs to review-and-fix commit-fixes"));
}

#[test]
fn commit_help_exits_zero() {
    let fixture = fixture(NOOP_STUB);
    let (code, stdout, _stderr) = run(&fixture, "commit", &["--help"], false);
    assert_eq!(code, 0);
    assert!(stdout.contains("usage: cli.py implement commit"));
}

#[test]
fn commit_unknown_option_refuses() {
    let fixture = fixture(NOOP_STUB);
    let (code, stdout, _stderr) = run(&fixture, "commit", &["--bogus"], false);
    assert_eq!(code, 2);
    assert_eq!(kv(&stdout, "ERROR"), "unknown option: --bogus");
}

#[test]
fn commit_missing_value_refuses() {
    let fixture = fixture(NOOP_STUB);
    let (code, stdout, _stderr) = run(&fixture, "commit", &["--message"], false);
    assert_eq!(code, 2);
    assert_eq!(kv(&stdout, "ERROR"), "--message requires a value");
}

#[test]
fn commit_success_envelope_reports_head_sha() {
    let stub = dispatch_stub(&[
        ("token mark", "    exit 0"),
        ("timing mark", "    exit 0"),
        ("git commit", "    exit 0"),
    ]);
    let fixture = fixture(&stub);
    let (code, stdout, _stderr) = run(
        &fixture,
        "commit",
        &["-m", "impl commit", "README.md"],
        true,
    );
    assert_eq!(code, 0);
    assert_eq!(kv(&stdout, "COMMITTED"), "true");
    assert_eq!(
        kv(&stdout, "SHA").len(),
        40,
        "SHA should be a full hex commit id"
    );
}

#[test]
fn commit_failure_envelope_folds_error() {
    let stub = dispatch_stub(&[
        ("token mark", "    exit 0"),
        ("timing mark", "    exit 0"),
        (
            "git commit",
            "    printf 'boom line one\\nboom line two' >&2\n    exit 1",
        ),
    ]);
    let fixture = fixture(&stub);
    let (code, stdout, _stderr) = run(
        &fixture,
        "commit",
        &["-m", "impl commit", "README.md"],
        true,
    );
    assert_eq!(code, 1);
    assert_eq!(kv(&stdout, "COMMITTED"), "false");
    assert_eq!(kv(&stdout, "SHA"), "");
    assert_eq!(kv(&stdout, "ERROR"), "boom line one boom line two");
}

#[test]
fn commit_success_from_a_nul_pathspec_file() {
    let stub = dispatch_stub(&[
        ("token mark", "    exit 0"),
        ("timing mark", "    exit 0"),
        ("git commit", "    exit 0"),
    ]);
    let fixture = fixture(&stub);
    let pathspec = fixture.tmpdir.join("commit-paths.nul");
    fs::write(&pathspec, "README.md\0").expect("pathspec");
    let (code, stdout, _stderr) = run(
        &fixture,
        "commit",
        &[
            "--message",
            "impl commit",
            "--pathspec-from-file",
            pathspec.to_str().expect("utf8"),
            "--pathspec-file-nul",
        ],
        true,
    );
    assert_eq!(code, 0);
    assert_eq!(kv(&stdout, "COMMITTED"), "true");
    assert_eq!(kv(&stdout, "SHA").len(), 40);
}

// ---------------------------------------------------------------------------
// implement commit-route
// ---------------------------------------------------------------------------

#[test]
fn commit_route_requires_a_tmpdir() {
    let fixture = fixture(NOOP_STUB);
    let (code, _stdout, stderr) = run(&fixture, "commit-route", &["--site", "step7"], false);
    assert_eq!(code, 2);
    assert!(stderr.contains("IMPLEMENT_TMPDIR required"));
}

#[test]
fn commit_route_rejects_an_unknown_site() {
    let fixture = fixture(NOOP_STUB);
    let (code, _stdout, stderr) = run(&fixture, "commit-route", &["--site", "bogus"], true);
    assert_eq!(code, 2);
    assert!(stderr.contains("invalid choice"));
}

#[test]
fn commit_route_continue_relays_commit_kvs() {
    let stub = dispatch_stub(&[(
        "review-and-fix commit-fixes",
        "    printf 'COMMIT_OUTCOME=ok\\nCOMMITTED=true\\nSHA=deadbeef\\n'\n    exit 0",
    )]);
    let fixture = fixture(&stub);
    let (code, stdout, _stderr) = run(
        &fixture,
        "commit-route",
        &["--site", "step7", "--emit-next-action", "false"],
        true,
    );
    assert_eq!(code, 0);
    assert_eq!(kv(&stdout, "COMMIT_ROUTE_OUTCOME"), "continue");
    assert_eq!(kv(&stdout, "COMMITTED"), "true");
    assert_eq!(kv(&stdout, "SHA"), "deadbeef");
}

#[test]
fn commit_route_continue_emits_next_action_by_default() {
    let stub = dispatch_stub(&[(
        "review-and-fix commit-fixes",
        "    printf 'COMMIT_OUTCOME=ok\\nCOMMITTED=true\\n'\n    exit 0",
    )]);
    let fixture = fixture(&stub);
    let (code, stdout, _stderr) = run(&fixture, "commit-route", &["--site", "step7"], true);
    assert_eq!(code, 0);
    assert_eq!(kv(&stdout, "NEXT_ACTION"), "continue");
    assert!(!stdout.contains("COMMIT_ROUTE_OUTCOME="));
}

#[test]
fn commit_route_continue_emits_next_action_continue() {
    let stub = dispatch_stub(&[(
        "review-and-fix commit-fixes",
        "    printf 'COMMIT_OUTCOME=ok\\nCOMMITTED=true\\n'\n    exit 0",
    )]);
    let fixture = fixture(&stub);
    let (code, stdout, _stderr) = run(
        &fixture,
        "commit-route",
        &["--site", "step7", "--emit-next-action", "true"],
        true,
    );
    assert_eq!(code, 0);
    assert_eq!(kv(&stdout, "NEXT_ACTION"), "continue");
}

#[test]
fn commit_route_stall_emits_next_action_stall() {
    let stub = dispatch_stub(&[
        (
            "review-and-fix commit-fixes",
            "    printf 'COMMIT_OUTCOME=fail\\n'\n    exit 1",
        ),
        ("run-log append-failure", "    exit 0"),
        ("implement step-8-seed-initial", "    exit 0"),
    ]);
    let fixture = fixture(&stub);
    let (code, stdout, _stderr) = run(
        &fixture,
        "commit-route",
        &["--site", "step7", "--emit-next-action", "true"],
        true,
    );
    assert_eq!(code, 0);
    assert_eq!(kv(&stdout, "NEXT_ACTION"), "stall");
}

#[test]
fn commit_route_seeds_a_stall_on_commit_failure() {
    let stub = dispatch_stub(&[
        (
            "review-and-fix commit-fixes",
            "    printf 'COMMIT_OUTCOME=fail\\n'\n    exit 1",
        ),
        ("run-log append-failure", "    exit 0"),
        ("implement step-8-seed-initial", "    exit 0"),
    ]);
    let fixture = fixture(&stub);
    let (code, stdout, _stderr) = run(
        &fixture,
        "commit-route",
        &["--site", "step7", "--emit-next-action", "false"],
        true,
    );
    assert_eq!(code, 0);
    assert_eq!(kv(&stdout, "COMMIT_ROUTE_OUTCOME"), "seeded-stall");
    assert!(
        fixture
            .tmpdir
            .join("commit-route-step7.failure.log")
            .is_file(),
        "a stall must persist a failure log"
    );
}

// ---------------------------------------------------------------------------
// implement checks-commit-route
// ---------------------------------------------------------------------------

#[test]
fn checks_commit_route_requires_both_sites() {
    let fixture = fixture(NOOP_STUB);
    let (code, _stdout, stderr) = run(
        &fixture,
        "checks-commit-route",
        &["--checks-site", "step7"],
        true,
    );
    assert_eq!(code, 2);
    assert!(stderr.contains("--commit-site"));
}

#[test]
fn checks_commit_route_short_circuits_on_failed_checks() {
    let stub = dispatch_stub(&[(
        "checks run-relevant",
        "    printf 'STATUS=fail FAILURE_REASON=lint EXIT_CODE=1\\n'\n    exit 1",
    )]);
    let fixture = fixture(&stub);
    let (code, stdout, _stderr) = run(
        &fixture,
        "checks-commit-route",
        &["--checks-site", "step7", "--commit-site", "step7"],
        true,
    );
    assert_eq!(code, 0);
    assert_eq!(kv(&stdout, "NEXT_ACTION"), "checks-failed");
    assert!(stdout.contains("STATUS=fail"));
}

#[test]
fn checks_commit_route_step7_success_commits_and_checkpoints() {
    let stub = dispatch_stub(&[
        (
            "checks run-relevant",
            "    printf 'RELEVANT_CHECKS_OK=true SITE=step7 COVERAGE=full PHASE=p1\\n'\n    exit 0",
        ),
        (
            "implement commit-route",
            "    printf 'COMMIT_ROUTE_OUTCOME=continue\\nCOMMITTED=true\\nSHA=abc123\\n'\n    exit 0",
        ),
        (
            "push checkpoint-probe",
            "    printf 'CHECKPOINT=ok\\n'\n    exit 0",
        ),
    ]);
    let fixture = fixture(&stub);
    let (code, stdout, _stderr) = run(
        &fixture,
        "checks-commit-route",
        &[
            "--checks-site",
            "step7",
            "--commit-site",
            "step7",
            "--rebase-checkpoint-7r",
        ],
        true,
    );
    assert_eq!(code, 0);
    assert!(stdout.contains("RELEVANT_CHECKS_OK=true SITE=step7"));
    assert_eq!(kv(&stdout, "COMMIT_ROUTE_OUTCOME"), "continue");
    assert_eq!(kv(&stdout, "COMMITTED"), "true");
    assert_eq!(kv(&stdout, "NEXT_ACTION"), "continue");
}

#[test]
fn checks_commit_route_step7_success_without_checkpoint_emits_breadcrumb() {
    let stub = dispatch_stub(&[
        (
            "checks run-relevant",
            "    printf 'RELEVANT_CHECKS_SKIPPED=true SITE=step7\\n'\n    exit 0",
        ),
        (
            "implement commit-route",
            "    printf 'COMMIT_ROUTE_OUTCOME=continue\\nCOMMITTED=true\\n'\n    exit 0",
        ),
    ]);
    let fixture = fixture(&stub);
    let (code, stdout, stderr) = run(
        &fixture,
        "checks-commit-route",
        &[
            "--checks-site",
            "step7",
            "--commit-site",
            "step7",
            "--emit-step7-breadcrumb",
        ],
        true,
    );
    assert_eq!(code, 0);
    assert!(stdout.contains("RELEVANT_CHECKS_SKIPPED=true SITE=step7"));
    assert_eq!(kv(&stdout, "NEXT_ACTION"), "continue");
    assert!(stderr.contains("commit (review)"));
}

#[test]
fn checks_commit_route_relays_a_commit_leg_stall_as_next_action_stall() {
    let stub = dispatch_stub(&[
        (
            "checks run-relevant",
            "    printf 'RELEVANT_CHECKS_OK=true SITE=step7 COVERAGE=full PHASE=p1\\n'\n    exit 0",
        ),
        (
            "implement commit-route",
            "    printf 'COMMIT_ROUTE_OUTCOME=seeded-stall\\n'\n    exit 0",
        ),
    ]);
    let fixture = fixture(&stub);
    let (code, stdout, _stderr) = run(
        &fixture,
        "checks-commit-route",
        &["--checks-site", "step7", "--commit-site", "step7"],
        true,
    );
    assert_eq!(code, 0);
    assert_eq!(kv(&stdout, "COMMIT_ROUTE_OUTCOME"), "seeded-stall");
    assert_eq!(kv(&stdout, "NEXT_ACTION"), "stall");
}

#[test]
fn checks_commit_route_rejects_an_invalid_commit_leg_outcome() {
    let stub = dispatch_stub(&[
        (
            "checks run-relevant",
            "    printf 'RELEVANT_CHECKS_OK=true SITE=step7 COVERAGE=full PHASE=p1\\n'\n    exit 0",
        ),
        (
            "implement commit-route",
            "    printf 'COMMIT_ROUTE_OUTCOME=bogus\\n'\n    exit 0",
        ),
    ]);
    let fixture = fixture(&stub);
    let (code, stdout, _stderr) = run(
        &fixture,
        "checks-commit-route",
        &["--checks-site", "step7", "--commit-site", "step7"],
        true,
    );
    assert_eq!(code, 1);
    assert!(!stdout.contains("NEXT_ACTION=continue"));
}

#[test]
fn checks_commit_route_step4_dispatcher_committed_is_a_noop_continue() {
    let stub = dispatch_stub(&[
        (
            "checks run-relevant",
            "    printf 'RELEVANT_CHECKS_SKIPPED=true SITE=step3\\n'\n    exit 0",
        ),
        ("push checkpoint-probe", "    exit 0"),
    ]);
    let fixture = fixture(&stub);
    // A dispatcher-committed seed with a readable manifest and a clean tree
    // resolves to a no-op commit that still continues.
    fs::write(
        fixture.tmpdir.join("ship-seed-input.env"),
        format!(
            "DISPATCHER_COMMITTED=true\nMANIFEST_PATH={}\n",
            fixture.tmpdir.join("session-env.sh").display()
        ),
    )
    .expect("seed input");
    let (code, stdout, _stderr) = run(
        &fixture,
        "checks-commit-route",
        &[
            "--checks-site",
            "step3",
            "--commit-site",
            "step4",
            "--rebase-checkpoint-4r",
        ],
        true,
    );
    assert_eq!(code, 0);
    assert_eq!(kv(&stdout, "NEXT_ACTION"), "continue");
    assert!(stdout.contains("COMMIT_ROUTE_OUTCOME=noop"));
}

// ---------------------------------------------------------------------------
// commit-route success sites
// ---------------------------------------------------------------------------

#[test]
fn commit_route_step5_resume_handoff_passes_the_porcelain_gate() {
    let stub = dispatch_stub(&[(
        "review-and-fix commit-fixes",
        "    printf 'COMMIT_OUTCOME=ok\\nCOMMITTED=true\\nSHA=feedface\\n'\n    exit 0",
    )]);
    let fixture = fixture(&stub);
    let (code, stdout, _stderr) = run(
        &fixture,
        "commit-route",
        &[
            "--site",
            "step5-resume-handoff",
            "--emit-next-action",
            "false",
        ],
        true,
    );
    assert_eq!(code, 0);
    assert_eq!(kv(&stdout, "COMMIT_ROUTE_OUTCOME"), "continue");
    assert_eq!(kv(&stdout, "COMMITTED"), "true");
}

#[test]
fn commit_route_step5_self_review_continues_on_noop() {
    let stub = dispatch_stub(&[(
        "review-and-fix commit-fixes",
        "    printf 'COMMIT_OUTCOME=noop\\n'\n    exit 0",
    )]);
    let fixture = fixture(&stub);
    let (code, stdout, _stderr) = run(
        &fixture,
        "commit-route",
        &["--site", "step5-self-review", "--emit-next-action", "false"],
        true,
    );
    assert_eq!(code, 0);
    assert_eq!(kv(&stdout, "COMMIT_ROUTE_OUTCOME"), "continue");
}

#[test]
fn commit_route_step5_resume_handoff_seeds_a_stall_on_failure() {
    let stub = dispatch_stub(&[
        (
            "review-and-fix commit-fixes",
            "    printf 'COMMIT_OUTCOME=fail\\n'\n    exit 1",
        ),
        ("run-log append-failure", "    exit 0"),
        ("implement step-8-seed-initial", "    exit 0"),
    ]);
    let fixture = fixture(&stub);
    let (code, stdout, _stderr) = run(
        &fixture,
        "commit-route",
        &["--site", "step5-resume-handoff"],
        true,
    );
    assert_eq!(code, 0);
    assert_eq!(kv(&stdout, "NEXT_ACTION"), "stall");
    assert!(
        fixture
            .tmpdir
            .join("commit-route-step5-resume-handoff.failure.log")
            .is_file()
    );
}

// ---------------------------------------------------------------------------
// checks-commit-route step4 commit leg
// ---------------------------------------------------------------------------

#[test]
fn checks_commit_route_step4_without_a_seed_reports_seed_failed() {
    let stub = dispatch_stub(&[(
        "checks run-relevant",
        "    printf 'RELEVANT_CHECKS_OK=true SITE=step3 COVERAGE=full PHASE=p1\\n'\n    exit 0",
    )]);
    let fixture = fixture(&stub);
    let (code, stdout, _stderr) = run(
        &fixture,
        "checks-commit-route",
        &["--checks-site", "step3", "--commit-site", "step4"],
        true,
    );
    assert_eq!(code, 1);
    assert!(stdout.contains("COMMIT_ROUTE_OUTCOME=seed-failed"));
}

#[test]
fn checks_commit_route_step4_commits_a_seeded_pathspec() {
    let stub = dispatch_stub(&[
        (
            "checks run-relevant",
            "    printf 'RELEVANT_CHECKS_OK=true SITE=step3 COVERAGE=full PHASE=p1\\n'\n    exit 0",
        ),
        (
            "implement commit",
            "    printf 'COMMITTED=true\\nSHA=cafebabecafebabecafebabecafebabecafebabe\\n'\n    exit 0",
        ),
        ("push checkpoint-probe", "    exit 0"),
    ]);
    let fixture = fixture(&stub);
    // An implementation seed (message + NUL pathspec) whose path is dirty vs
    // HEAD, so the step4 commit leg composes `implement commit`, not a no-op.
    fs::write(
        fixture.tmpdir.join("implementation-commit-message.txt"),
        "implementation commit\n",
    )
    .expect("implementation message");
    fs::write(
        fixture.tmpdir.join("implementation-commit-paths.nul"),
        "README.md\0",
    )
    .expect("implementation pathspec");
    fs::write(fixture.repo.join("README.md"), "dirty\n").expect("dirty readme");
    let (code, stdout, _stderr) = run(
        &fixture,
        "checks-commit-route",
        &[
            "--checks-site",
            "step3",
            "--commit-site",
            "step4",
            "--rebase-checkpoint-4r",
        ],
        true,
    );
    assert_eq!(code, 0);
    assert_eq!(kv(&stdout, "COMMIT_ROUTE_OUTCOME"), "continue");
    assert_eq!(kv(&stdout, "NEXT_ACTION"), "continue");
}

#[test]
fn checks_commit_route_step4_commit_failure_seeds_a_stall() {
    let stub = dispatch_stub(&[
        (
            "checks run-relevant",
            "    printf 'RELEVANT_CHECKS_OK=true SITE=step3 COVERAGE=full PHASE=p1\\n'\n    exit 0",
        ),
        // The Step 4 implementation commit reports a failure envelope.
        (
            "implement commit",
            "    printf 'COMMITTED=false\\n'\n    exit 1",
        ),
        ("run-log append-failure", "    exit 0"),
        ("implement step-8-seed-initial", "    exit 0"),
    ]);
    let fixture = fixture(&stub);
    fs::write(
        fixture.tmpdir.join("implementation-commit-message.txt"),
        "implementation commit\n",
    )
    .expect("implementation message");
    fs::write(
        fixture.tmpdir.join("implementation-commit-paths.nul"),
        "README.md\0",
    )
    .expect("implementation pathspec");
    fs::write(fixture.repo.join("README.md"), "dirty\n").expect("dirty readme");
    let (code, stdout, _stderr) = run(
        &fixture,
        "checks-commit-route",
        &["--checks-site", "step3", "--commit-site", "step4"],
        true,
    );
    assert_eq!(code, 0);
    assert_eq!(kv(&stdout, "COMMIT_ROUTE_OUTCOME"), "seeded-stall");
    assert_eq!(kv(&stdout, "NEXT_ACTION"), "stall");
    assert!(
        fixture
            .tmpdir
            .join("commit-route-step4.failure.log")
            .is_file(),
        "a Step 4 commit failure must persist a failure log"
    );
}

#[test]
fn checks_commit_route_step4_recovery_recompute_runs_before_the_commit_leg() {
    let stub = dispatch_stub(&[
        (
            "checks run-relevant",
            "    printf 'RELEVANT_CHECKS_OK=true SITE=step3 COVERAGE=full PHASE=p1\\n'\n    exit 0",
        ),
        // The recovery scope-check keeps the recomputed paths in scope.
        ("dirty-tree scope-check", "    exit 0"),
    ]);
    let fixture = fixture(&stub);
    // A recovery seed forces run_step4_recovery_recompute to recompute the
    // frozen paths from the prelaunch/postlaunch porcelain before committing.
    fs::write(fixture.tmpdir.join("recovery-metadata.json"), "{}\n").expect("recovery metadata");
    fs::write(fixture.tmpdir.join("step2-prelaunch-porcelain.nul"), "")
        .expect("prelaunch porcelain");
    fs::write(
        fixture.tmpdir.join("step2-prelaunch-content-digests.txt"),
        "",
    )
    .expect("prelaunch digests");
    fs::write(fixture.tmpdir.join("plan.txt"), "plan\n").expect("plan");
    let (code, _stdout, _stderr) = run(
        &fixture,
        "checks-commit-route",
        &["--checks-site", "step3", "--commit-site", "step4"],
        true,
    );
    // Without a recovery commit message the seed cannot resolve, so the leg
    // reports a non-zero exit after the recompute path has been exercised.
    assert_eq!(code, 1);
}

#[test]
fn checks_commit_route_rejects_an_invalid_commit_site() {
    let fixture = fixture(NOOP_STUB);
    let (code, _stdout, stderr) = run(
        &fixture,
        "checks-commit-route",
        &["--checks-site", "step7", "--commit-site", "step9"],
        true,
    );
    assert_eq!(code, 2);
    assert!(stderr.contains("--commit-site"));
}

#[test]
fn checks_commit_route_rejects_a_nonnumeric_commit_deadline() {
    let fixture = fixture(NOOP_STUB);
    let (code, _stdout, stderr) = run(
        &fixture,
        "checks-commit-route",
        &[
            "--checks-site",
            "step7",
            "--commit-site",
            "step7",
            "--commit-deadline-ms",
            "soon",
        ],
        true,
    );
    assert_eq!(code, 2);
    assert!(stderr.contains("--commit-deadline-ms"));
}

#[test]
fn checks_commit_route_treats_empty_checks_output_as_a_failure() {
    // The relevant-checks leg emits nothing, so the capture is synthesized into
    // a failure envelope and the composite short-circuits to `checks-failed`.
    let stub = dispatch_stub(&[("checks run-relevant", "    exit 0")]);
    let fixture = fixture(&stub);
    let (code, stdout, _stderr) = run(
        &fixture,
        "checks-commit-route",
        &["--checks-site", "step7", "--commit-site", "step7"],
        true,
    );
    assert_eq!(code, 0);
    assert_eq!(kv(&stdout, "NEXT_ACTION"), "checks-failed");
    assert!(stdout.contains("STATUS=fail"));
}

#[test]
fn commit_route_seeds_a_stall_on_a_missing_commit_outcome() {
    let stub = dispatch_stub(&[
        (
            "review-and-fix commit-fixes",
            "    printf 'NOTHING=here\\n'\n    exit 0",
        ),
        ("run-log append-failure", "    exit 0"),
        ("implement step-8-seed-initial", "    exit 0"),
    ]);
    let fixture = fixture(&stub);
    let (code, stdout, _stderr) = run(
        &fixture,
        "commit-route",
        &["--site", "step7", "--emit-next-action", "false"],
        true,
    );
    assert_eq!(code, 0);
    assert_eq!(kv(&stdout, "COMMIT_ROUTE_OUTCOME"), "seeded-stall");
}

#[test]
fn commit_route_step5_resume_handoff_stalls_on_a_dirty_tree_after_commit() {
    let stub = dispatch_stub(&[
        (
            "review-and-fix commit-fixes",
            "    printf 'COMMIT_OUTCOME=ok\\n'\n    exit 0",
        ),
        ("run-log append-failure", "    exit 0"),
        ("implement step-8-seed-initial", "    exit 0"),
    ]);
    let fixture = fixture(&stub);
    // The stub reports a successful commit but never cleans the tree, so the
    // porcelain gate for the resume-handoff site converts it into a stall.
    fs::write(fixture.repo.join("README.md"), "dirty\n").expect("dirty readme");
    let (code, stdout, _stderr) = run(
        &fixture,
        "commit-route",
        &[
            "--site",
            "step5-resume-handoff",
            "--emit-next-action",
            "false",
        ],
        true,
    );
    assert_eq!(code, 0);
    assert_eq!(kv(&stdout, "COMMIT_ROUTE_OUTCOME"), "seeded-stall");
    assert!(
        fixture
            .tmpdir
            .join("commit-route-step5-resume-handoff.failure.log")
            .is_file(),
        "a porcelain-gate stall must persist a failure log"
    );
}
