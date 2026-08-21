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
    fs::write(tmpdir.join("repo-root.txt"), format!("{}\n", repo.display())).expect("repo-root.txt");

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

fn run(fixture: &Fixture, verb: &str, arguments: &[&str], set_tmpdir: bool) -> (i32, String, String) {
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
fn dispatch_stub(cases: &[(&str, &str)]) -> String {
    let mut body = String::from("#!/usr/bin/env bash\nset -u\ncase \"${1:-} ${2:-}\" in\n");
    for (needle, action) in cases {
        body.push_str(&format!("  \"{needle}\")\n{action}\n    ;;\n"));
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
    let (code, stdout, _stderr) = run(&fixture, "commit", &["-m", "impl commit", "README.md"], true);
    assert_eq!(code, 0);
    assert_eq!(kv(&stdout, "COMMITTED"), "true");
    assert_eq!(kv(&stdout, "SHA").len(), 40, "SHA should be a full hex commit id");
}

#[test]
fn commit_failure_envelope_folds_error() {
    let stub = dispatch_stub(&[
        ("token mark", "    exit 0"),
        ("timing mark", "    exit 0"),
        ("git commit", "    printf 'boom line one\\nboom line two' >&2\n    exit 1"),
    ]);
    let fixture = fixture(&stub);
    let (code, stdout, _stderr) = run(&fixture, "commit", &["-m", "impl commit", "README.md"], true);
    assert_eq!(code, 1);
    assert_eq!(kv(&stdout, "COMMITTED"), "false");
    assert_eq!(kv(&stdout, "SHA"), "");
    assert_eq!(kv(&stdout, "ERROR"), "boom line one boom line two");
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
        fixture.tmpdir.join("commit-route-step7.failure.log").is_file(),
        "a stall must persist a failure log"
    );
}

// ---------------------------------------------------------------------------
// implement checks-commit-route
// ---------------------------------------------------------------------------

#[test]
fn checks_commit_route_requires_both_sites() {
    let fixture = fixture(NOOP_STUB);
    let (code, _stdout, stderr) = run(&fixture, "checks-commit-route", &["--checks-site", "step7"], true);
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
