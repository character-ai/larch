//! Black-box coverage for the Rust-owned `implement scope-disposition` verb.
//!
//! Each case drives a real temporary Git repository through the frozen Step 2
//! baseline path, which is the branch a clone without a resolvable
//! `origin/HEAD` takes.

use std::{
    fmt::Write as _,
    fs,
    path::{Path, PathBuf},
    process::Command,
};

use assert_cmd::Command as AssertCommand;
use tempfile::TempDir;

struct Fixture {
    root: TempDir,
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

/// Seed a committed repository plus the frozen-baseline session artifacts.
fn fixture(plan_paths: &[&str], existing: &[&str]) -> Fixture {
    let root = TempDir::new().expect("temp root");
    let repo = root.path().join("repo");
    let tmpdir = root.path().join("tmp");
    fs::create_dir_all(&repo).expect("repo");
    fs::create_dir_all(&tmpdir).expect("tmpdir");
    git(&repo, &["init", "--quiet", "-b", "main"]);
    git(&repo, &["config", "user.email", "larch@example.invalid"]);
    git(&repo, &["config", "user.name", "larch"]);
    git(&repo, &["config", "commit.gpgsign", "false"]);
    fs::write(repo.join("README.md"), "base\n").expect("readme");
    git(&repo, &["add", "README.md"]);
    git(&repo, &["commit", "--quiet", "-m", "base"]);

    let repo = fs::canonicalize(&repo).expect("canonical repo");
    let tmpdir = fs::canonicalize(&tmpdir).expect("canonical tmpdir");
    let head = String::from_utf8(
        Command::new("git")
            .args(["rev-parse", "HEAD"])
            .current_dir(&repo)
            .output()
            .expect("rev-parse")
            .stdout,
    )
    .expect("utf8 sha");
    fs::write(tmpdir.join("step2-baseline.txt"), head.trim()).expect("baseline");
    fs::write(tmpdir.join("session-id"), "scope-parity-session\n").expect("session id");

    let mut plan = String::from("## Files to modify\n\n");
    for path in plan_paths {
        let _ = writeln!(plan, "### NEW: `{path}`");
    }
    fs::write(tmpdir.join("plan.txt"), plan).expect("plan");
    for path in existing {
        fs::write(repo.join(path), "touched\n").expect("touched file");
    }
    Fixture { root, repo, tmpdir }
}

fn run(fixture: &Fixture, arguments: &[&str]) -> (i32, String) {
    let output = AssertCommand::cargo_bin("larch")
        .expect("larch binary")
        .args(["implement", "scope-disposition"])
        .args(arguments)
        .env("IMPLEMENT_TMPDIR", &fixture.tmpdir)
        .current_dir(&fixture.repo)
        .output()
        .expect("run scope-disposition");
    (
        output.status.code().unwrap_or(-1),
        String::from_utf8_lossy(&output.stdout).into_owned(),
    )
}

fn compute(fixture: &Fixture) -> (i32, String) {
    let repo = fixture.repo.display().to_string();
    let tmpdir = fixture.tmpdir.display().to_string();
    run(
        fixture,
        &["compute", "--tmpdir", &tmpdir, "--repo-root", &repo],
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

#[test]
fn compute_reports_an_advisory_band_when_every_firm_path_is_touched() {
    let fixture = fixture(&["a.txt", "b.txt"], &["a.txt", "b.txt"]);

    let (code, stdout) = compute(&fixture);

    assert_eq!(code, 0, "stdout: {stdout}");
    assert_eq!(kv(&stdout, "PLAN_COVERAGE_TOTAL"), "2");
    assert_eq!(kv(&stdout, "PLAN_COVERAGE_TOUCHED"), "2");
    assert_eq!(kv(&stdout, "PLAN_COVERAGE_UNTOUCHED"), "0");
    assert_eq!(kv(&stdout, "PLAN_COVERAGE_BAND"), "advisory");
    assert_eq!(kv(&stdout, "PLAN_COVERAGE_DISPOSITION_REQUIRED"), "false");
    assert_eq!(kv(&stdout, "PLAN_FIDELITY_FORCED"), "false");
    assert!(fixture.tmpdir.join("plan-coverage.json").is_file());
    assert!(fixture.tmpdir.join("plan-coverage.env").is_file());
    assert_eq!(
        fs::read_to_string(fixture.tmpdir.join("plan-coverage-untouched.txt")).expect("inventory"),
        ""
    );
}

#[test]
fn compute_reports_a_high_band_and_requires_disposition_at_half_untouched() {
    let fixture = fixture(&["a.txt", "b.txt"], &["a.txt"]);

    let (code, stdout) = compute(&fixture);

    assert_eq!(code, 0, "stdout: {stdout}");
    assert_eq!(kv(&stdout, "PLAN_COVERAGE_UNTOUCHED"), "1");
    assert_eq!(kv(&stdout, "PLAN_COVERAGE_UNTOUCHED_PERCENT"), "50");
    assert_eq!(kv(&stdout, "PLAN_COVERAGE_BAND"), "high");
    assert_eq!(kv(&stdout, "PLAN_COVERAGE_DISPOSITION_REQUIRED"), "true");
    assert_eq!(kv(&stdout, "PLAN_FIDELITY_FORCED"), "true");
    assert_eq!(
        fs::read_to_string(fixture.tmpdir.join("plan-coverage-untouched.txt")).expect("inventory"),
        "b.txt\n"
    );
    assert!(!kv(&stdout, "PLAN_COVERAGE_FINGERPRINT").is_empty());
}

#[test]
fn validate_ship_refuses_a_high_band_without_a_recorded_disposition() {
    let fixture = fixture(&["a.txt", "b.txt"], &["a.txt"]);
    let (code, stdout) = compute(&fixture);
    assert_eq!(code, 0, "stdout: {stdout}");

    let (code, stdout) = run(
        &fixture,
        &[
            "validate-ship",
            "--tmpdir",
            &fixture.tmpdir.display().to_string(),
            "--repo-root",
            &fixture.repo.display().to_string(),
        ],
    );

    assert_eq!(code, 3, "stdout: {stdout}");
    assert_eq!(kv(&stdout, "SCOPE_DISPOSITION_VALID"), "false");
    assert_eq!(kv(&stdout, "SCOPE_DISPOSITION_REQUIRED"), "true");
    assert_eq!(
        kv(&stdout, "SCOPE_DISPOSITION_REASON"),
        "scope-disposition-missing"
    );
    assert_eq!(kv(&stdout, "PLAN_COVERAGE_BAND"), "high");
}

#[test]
fn invalidate_if_stale_deletes_a_disposition_that_no_longer_matches_coverage() {
    let fixture = fixture(&["a.txt", "b.txt"], &["a.txt"]);
    let (code, stdout) = compute(&fixture);
    assert_eq!(code, 0, "stdout: {stdout}");
    let disposition = fixture.tmpdir.join("scope-disposition.json");
    fs::write(
        &disposition,
        format!(
            "{{\n  \"coverage_file\": {:?},\n  \"disposition\": \"proceed-partial\",\n  \"fingerprint\": \"stale\",\n  \"followup_issue_number\": \"\",\n  \"followup_issue_url\": \"\"\n}}\n",
            fixture.tmpdir.join("plan-coverage.json").display().to_string()
        ),
    )
    .expect("disposition");

    let (code, stdout) = run(
        &fixture,
        &[
            "invalidate-if-stale",
            "--tmpdir",
            &fixture.tmpdir.display().to_string(),
            "--repo-root",
            &fixture.repo.display().to_string(),
        ],
    );

    assert_eq!(code, 3, "stdout: {stdout}");
    assert_eq!(
        kv(&stdout, "SCOPE_DISPOSITION_REASON"),
        "scope-disposition-stale"
    );
    assert!(
        !disposition.exists(),
        "a stale disposition must be invalidated"
    );
}

#[test]
fn summary_line_is_empty_when_a_session_recorded_no_coverage_artifacts() {
    let root = TempDir::new().expect("temp root");
    let tmpdir = fs::canonicalize(root.path()).expect("canonical tmpdir");

    let output = AssertCommand::cargo_bin("larch")
        .expect("larch binary")
        .args(["implement", "scope-disposition", "summary-line"])
        .args(["--tmpdir", &tmpdir.display().to_string()])
        .current_dir(&tmpdir)
        .output()
        .expect("run summary-line");
    let stdout = String::from_utf8_lossy(&output.stdout).into_owned();

    assert_eq!(output.status.code(), Some(0), "stdout: {stdout}");
    assert!(
        stdout.lines().any(|line| line == "PLAN_COVERAGE_LINE="),
        "stdout: {stdout}"
    );
}

#[test]
fn render_deferred_inventory_lists_untouched_firm_plan_paths() {
    let fixture = fixture(&["a.txt", "b.txt"], &["a.txt"]);
    let (code, stdout) = compute(&fixture);
    assert_eq!(code, 0, "stdout: {stdout}");

    let (code, stdout) = run(
        &fixture,
        &[
            "render-deferred-inventory",
            "--tmpdir",
            &fixture.tmpdir.display().to_string(),
            "--repo-root",
            &fixture.repo.display().to_string(),
        ],
    );

    assert_eq!(code, 0, "stdout: {stdout}");
    assert_eq!(
        stdout,
        "## Deferred plan inventory\n\nUntouched firm plan paths:\n- `b.txt`\n"
    );
}

fn write_manifest(tmpdir: &Path, todos: &[&str]) -> PathBuf {
    let path = tmpdir.join("manifest.json");
    let payload = serde_json::json!({ "todos_left": todos });
    fs::write(&path, format!("{payload}\n")).expect("manifest");
    path
}

#[test]
fn compute_ignores_nonblocking_full_suite_validation_todos() {
    let fixture = fixture(&["a.txt"], &["a.txt"]);
    let manifest = write_manifest(
        &fixture.tmpdir,
        &["make py-lint and make py-test (full suites) were not completed; focused tests passed"],
    );

    let (code, stdout) = run(
        &fixture,
        &[
            "compute",
            "--tmpdir",
            &fixture.tmpdir.display().to_string(),
            "--repo-root",
            &fixture.repo.display().to_string(),
            "--manifest-path",
            &manifest.display().to_string(),
        ],
    );

    assert_eq!(code, 0, "stdout: {stdout}");
    assert_eq!(kv(&stdout, "TODOS_LEFT_COUNT"), "0");
    assert_eq!(kv(&stdout, "PLAN_COVERAGE_DISPOSITION_REQUIRED"), "false");
    assert_eq!(
        fs::read_to_string(fixture.tmpdir.join("plan-coverage-todos-left.txt")).expect("todos"),
        ""
    );
}

#[test]
fn compute_requires_disposition_for_blocking_manifest_todos() {
    let fixture = fixture(&["a.txt"], &["a.txt"]);
    let manifest = write_manifest(&fixture.tmpdir, &["finish remaining docs edits"]);

    let (code, stdout) = run(
        &fixture,
        &[
            "compute",
            "--tmpdir",
            &fixture.tmpdir.display().to_string(),
            "--repo-root",
            &fixture.repo.display().to_string(),
            "--manifest-path",
            &manifest.display().to_string(),
        ],
    );

    assert_eq!(code, 0, "stdout: {stdout}");
    assert_eq!(kv(&stdout, "TODOS_LEFT_COUNT"), "1");
    assert_eq!(kv(&stdout, "PLAN_COVERAGE_DISPOSITION_REQUIRED"), "true");
    assert_eq!(
        fs::read_to_string(fixture.tmpdir.join("plan-coverage-todos-left.txt")).expect("todos"),
        "- finish remaining docs edits\n"
    );
}

#[test]
fn compute_excludes_may_update_headings_from_firm_scope() {
    let fixture = fixture(&["a.txt"], &["a.txt"]);
    fs::write(
        fixture.tmpdir.join("plan.txt"),
        "## Files\n### UPDATED: `a.txt`\n### MAY_UPDATE: `optional.md`\n",
    )
    .expect("plan");

    let (code, stdout) = compute(&fixture);

    assert_eq!(code, 0, "stdout: {stdout}");
    assert_eq!(kv(&stdout, "PLAN_COVERAGE_TOTAL"), "1");
    assert_eq!(kv(&stdout, "PLAN_COVERAGE_UNTOUCHED"), "0");
    assert_eq!(kv(&stdout, "PLAN_COVERAGE_BAND"), "advisory");
}

#[test]
fn compute_reports_middle_band_at_twenty_percent_untouched() {
    let fixture = fixture(
        &["a.txt", "b.txt", "c.txt", "d.txt", "e.txt"],
        &["a.txt", "b.txt", "c.txt", "d.txt"],
    );

    let (code, stdout) = compute(&fixture);

    assert_eq!(code, 0, "stdout: {stdout}");
    assert_eq!(kv(&stdout, "PLAN_COVERAGE_UNTOUCHED"), "1");
    assert_eq!(kv(&stdout, "PLAN_COVERAGE_UNTOUCHED_PERCENT"), "20");
    assert_eq!(kv(&stdout, "PLAN_COVERAGE_BAND"), "middle");
    assert_eq!(kv(&stdout, "PLAN_COVERAGE_DISPOSITION_REQUIRED"), "false");
    assert_eq!(kv(&stdout, "PLAN_FIDELITY_FORCED"), "true");
}

#[test]
fn record_bail_rescope_persists_without_followup_filing() {
    let fixture = fixture(&["a.txt", "b.txt"], &["a.txt"]);
    let (code, stdout) = compute(&fixture);
    assert_eq!(code, 0, "stdout: {stdout}");

    let (code, stdout) = run(
        &fixture,
        &[
            "record",
            "--tmpdir",
            &fixture.tmpdir.display().to_string(),
            "--repo-root",
            &fixture.repo.display().to_string(),
            "--disposition",
            "bail-rescope",
        ],
    );

    assert_eq!(code, 0, "stdout: {stdout}");
    assert_eq!(kv(&stdout, "SCOPE_DISPOSITION_RECORDED"), "true");
    assert_eq!(kv(&stdout, "SCOPE_DISPOSITION"), "bail-rescope");
    let body = fs::read_to_string(fixture.tmpdir.join("scope-disposition.json")).expect("record");
    assert!(body.contains("\"disposition\": \"bail-rescope\""));
    assert!(!body.contains("\"followup_issue_number\": \"1\""));

    let (code, stdout) = run(
        &fixture,
        &[
            "validate-ship",
            "--tmpdir",
            &fixture.tmpdir.display().to_string(),
            "--repo-root",
            &fixture.repo.display().to_string(),
        ],
    );
    assert_eq!(code, 3, "stdout: {stdout}");
    assert_eq!(
        kv(&stdout, "SCOPE_DISPOSITION_REASON"),
        "scope-disposition-bail-rescope"
    );
}

#[test]
fn compute_uses_live_merge_base_when_origin_head_resolves() {
    let fixture = fixture(&["a.txt"], &[]);
    let origin = fixture.root.path().join("origin.git");
    let status = Command::new("git")
        .args([
            "init",
            "--quiet",
            "--bare",
            "-b",
            "main",
            &origin.display().to_string(),
        ])
        .env("GIT_CONFIG_GLOBAL", "/dev/null")
        .env("GIT_CONFIG_SYSTEM", "/dev/null")
        .status()
        .expect("bare origin");
    assert!(status.success());
    git(
        &fixture.repo,
        &["remote", "add", "origin", &origin.display().to_string()],
    );
    git(&fixture.repo, &["push", "-q", "-u", "origin", "main"]);
    git(&origin, &["symbolic-ref", "HEAD", "refs/heads/main"]);
    git(&fixture.repo, &["remote", "set-head", "origin", "main"]);
    fs::write(fixture.repo.join("a.txt"), "touched\n").expect("touch");

    let (code, stdout) = compute(&fixture);

    assert_eq!(code, 0, "stdout: {stdout}");
    assert_eq!(kv(&stdout, "PLAN_COVERAGE_TOUCHED"), "1");
    assert_eq!(kv(&stdout, "PLAN_COVERAGE_BAND"), "advisory");
    assert!(
        !fixture
            .tmpdir
            .join("scope-fallback-provenance.json")
            .is_file()
    );
}

#[test]
fn summary_line_renders_live_coverage_when_repo_root_is_persisted() {
    let fixture = fixture(&["a.txt", "b.txt"], &["a.txt"]);
    let (code, stdout) = compute(&fixture);
    assert_eq!(code, 0, "stdout: {stdout}");
    fs::write(
        fixture.tmpdir.join("session-env.sh"),
        format!("REPO_ROOT={}\n", fixture.repo.display()),
    )
    .expect("session env");

    let (code, stdout) = run(
        &fixture,
        &[
            "summary-line",
            "--tmpdir",
            &fixture.tmpdir.display().to_string(),
        ],
    );

    assert_eq!(code, 0, "stdout: {stdout}");
    let line = kv(&stdout, "PLAN_COVERAGE_LINE");
    assert!(
        line.contains("1/2 firm headings") && line.contains("band: high"),
        "stdout: {stdout}"
    );
}

#[test]
fn proceed_partial_record_refuses_without_repo_and_tracking_issue() {
    let fixture = fixture(&["a.txt", "b.txt"], &["a.txt"]);
    let (code, stdout) = compute(&fixture);
    assert_eq!(code, 0, "stdout: {stdout}");

    let output = AssertCommand::cargo_bin("larch")
        .expect("larch binary")
        .args([
            "implement",
            "scope-disposition",
            "record",
            "--tmpdir",
            &fixture.tmpdir.display().to_string(),
            "--repo-root",
            &fixture.repo.display().to_string(),
            "--disposition",
            "proceed-partial",
        ])
        .current_dir(&fixture.repo)
        .output()
        .expect("record");
    let stderr = String::from_utf8_lossy(&output.stderr);

    assert_eq!(output.status.code(), Some(4), "stderr: {stderr}");
    assert!(
        stderr.contains("proceed-partial requires --repo and --tracking-issue"),
        "stderr: {stderr}"
    );
}

#[test]
fn validate_ship_allows_advisory_coverage_without_a_disposition() {
    let fixture = fixture(&["a.txt"], &["a.txt"]);
    let (code, stdout) = compute(&fixture);
    assert_eq!(code, 0, "stdout: {stdout}");

    let (code, stdout) = run(
        &fixture,
        &[
            "validate-ship",
            "--tmpdir",
            &fixture.tmpdir.display().to_string(),
            "--repo-root",
            &fixture.repo.display().to_string(),
        ],
    );

    assert_eq!(code, 0, "stdout: {stdout}");
    assert_eq!(kv(&stdout, "SCOPE_DISPOSITION_VALID"), "true");
    assert_eq!(kv(&stdout, "SCOPE_DISPOSITION_REQUIRED"), "false");
}
