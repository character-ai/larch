#[rustfmt::skip]
mod compact {
use super::super::{body_update, checks, closes_issue, create, create_branch, create_pull_request,
    github_pr_url_number, open_pull_request, pull_request_for_head, qualify_github_head, resolve_pr_selector,
    update_pull_request_body};
use crate::{github_service::with_test_github_service, implement_scope_disposition_commands::{PrMutationScopeGate, validate_pr_mutation_scope}, push_network};
use larch_adapters::github::OctocrabGitHubService;
use larch_test_support::{IssueServiceExchange, IssueServiceStub};
use serde_json::{Value, json};
use std::{env, ffi::OsString, fs, path::Path, process::{Command, ExitCode}, sync::Arc};
use tempfile::TempDir;
const CHILD: &str = "LARCH_PR_LIFECYCLE_COVERAGE_CHILD";
const BRANCH: &str = "ada-lovelace/issue-8790";

#[test]
fn lifecycle_commands_cover_git_and_github_success_paths() {
    if env::var_os(CHILD).is_none() { spawn_child(); } else if env::var_os("LARCH_PR_SCOPE_ONLY").is_some() { run_scope_error(); } else { run_scenarios(); }
}

fn spawn_child() {
    let repository = TempDir::new().expect("repository fixture"); let remote = TempDir::new().expect("remote fixture");
    command("git", &["init", "-q", "-b", "main"], repository.path());
    git(repository.path(), &["config", "user.name", "Ada Lovelace"]); git(repository.path(), &["config", "user.email", "ada@example.test"]);
    fs::write(repository.path().join("base.txt"), "base\n").expect("base file"); git(repository.path(), &["add", "."]); git(repository.path(), &["commit", "-q", "-m", "base"]);
    command("git", &["init", "-q", "--bare"], remote.path()); git(repository.path(), &["remote", "add", "origin", text(remote.path())]); git(repository.path(), &["push", "-q", "origin", "main"]);
    let status = Command::new(env::current_exe().expect("test executable"))
        .args(["--exact", "pr_commands::coverage_tests::compact::lifecycle_commands_cover_git_and_github_success_paths", "--nocapture"])
        .current_dir(repository.path()).env(CHILD, "1").env("LARCH_PR_TEST_REMOTE", remote.path())
        .env_remove("IMPLEMENT_TMPDIR").env_remove("SHIP_PR_STATE_FILE").status().expect("isolated test child");
    assert!(status.success(), "isolated lifecycle child failed: {status}");
    scope_child(repository.path(), &repository.path().join("missing"), false); scope_child(repository.path(), &repository.path().join("base.txt"), false); scope_child(repository.path(), repository.path(), true);
}

fn run_scenarios() {
    assert_eq!(create_branch(&args(&["--branch", BRANCH])), ExitCode::SUCCESS); assert_eq!(create_branch(&args(&["--check"])), ExitCode::SUCCESS);
    assert!(push_network::push_for_pr(BRANCH, false)); assert_eq!(create_branch(&args(&["--branch", BRANCH])), ExitCode::from(1)); assert_eq!(create_branch(&args(&["--branch", "wrong/issue-8790"])), ExitCode::from(2)); assert_eq!(create_branch(&args(&["--branch", "ada-lovelace/fetch-fail", "--base-remote", "missing"])), ExitCode::from(2));
    let competing = TempDir::new().expect("competing clone"); command("git", &["clone", "-q", &env::var("LARCH_PR_TEST_REMOTE").expect("remote"), "."], competing.path());
    git(competing.path(), &["config", "user.name", "Remote User"]); git(competing.path(), &["config", "user.email", "remote@example.test"]); git(competing.path(), &["checkout", "-q", BRANCH]);
    git(competing.path(), &["commit", "--allow-empty", "-q", "-m", "remote"]); git(competing.path(), &["push", "-q", "origin", BRANCH]);
    assert!(!push_network::push_for_pr(BRANCH, false)); assert!(push_network::push_for_pr(BRANCH, true)); assert!(!push_network::push_for_pr("other/branch", false));
    let body_dir = TempDir::new().expect("body fixture"); let body_file = body_dir.path().join("body.md"); fs::write(&body_file, "Body\n\nCloses #12\n").expect("body file");
    exercise_create(&body_file); exercise_update(&body_file); exercise_checks(); exercise_closes(&body_file);
}

fn run_scope_error() { let result = validate_pr_mutation_scope(Path::new(".")); if env::var_os("LARCH_PR_SCOPE_ALLOWED").is_some() { assert_eq!(result, Ok(PrMutationScopeGate::Allowed)); } else { assert!(result.is_err()); assert_eq!(body_update(&args(&["--pr", "12", "--repo", "owner/repo", "--body-file", "base.txt"])), ExitCode::from(2)); assert_eq!(create(&args(&["--repo", "owner/repo", "--title", "T", "--body-file", "base.txt"])), ExitCode::from(2)); } }

fn exercise_create(body_file: &Path) {
    let body = text(body_file); assert_eq!(create(&args(&["--repo", "bad", "--title", "T", "--body-file", body])), ExitCode::from(2)); assert_eq!(create(&args(&["--repo", "owner/repo", "--title", "T", "--body-file", "missing"])), ExitCode::from(2)); fs::write("dirty.tmp", "dirty").expect("dirty file"); assert_eq!(create(&args(&["--repo", "owner/repo", "--title", "T", "--body-file", body])), ExitCode::from(1)); fs::remove_file("dirty.tmp").expect("dirty cleanup");
    assert_eq!(create(&args(&["--repo", "owner/repo", "--branch", "other", "--title", "T", "--body-file", body])), ExitCode::from(2));
    let pull = pull_json(12, "Body\n\nCloses #12\n"); let mut issue: Value = serde_json::from_str(include_str!("../../../larch-adapters/fixtures/github_issue.json")).expect("issue fixture");
    issue["number"] = json!(12); let user = issue["user"].clone(); issue["assignee"] = user.clone(); issue["assignees"] = json!([user]); let assigned = issue.to_string();
    let created = github([response(200, "[]"), response(200, repository_json()), response(200, "[]"), response(201, pull.clone()), response(200, issue["user"].to_string()), response(200, assigned.clone()), response(200, assigned)],
        || create(&args(&["--repo", "owner/repo", "--title", "Requested title", "--body-file", body, "--draft"]))); assert_eq!(created, ExitCode::SUCCESS);
    assert_eq!(github([response(200, format!("[{pull}]"))], || create(&args(&["--repo", "owner/repo", "--title", "Requested title", "--body-file", body]))), ExitCode::SUCCESS);
    assert_eq!(github([response(500, r#"{"message":"refused"}"#)], || create(&args(&["--repo", "owner/repo", "--title", "Requested title", "--body-file", body]))), ExitCode::from(2));
    git(Path::new("."), &["remote", "set-url", "origin", "missing"]); assert_eq!(github([response(200, "[]")], || create(&args(&["--repo", "owner/repo", "--title", "T", "--body-file", body]))), ExitCode::from(1)); git(Path::new("."), &["remote", "set-url", "origin", &env::var("LARCH_PR_TEST_REMOTE").expect("remote")]);
}

fn exercise_update(body_file: &Path) {
    assert_eq!(body_update(&args(&["--pr", "12", "--repo", "bad", "--body-file", text(body_file)])), ExitCode::from(2)); assert_eq!(body_update(&args(&["--pr", "", "--repo", "owner/repo", "--body-file", text(body_file)])), ExitCode::from(2));
    let body = text(body_file); assert_eq!(github([response(200, pull_json(12, "Body\n\nCloses #12\n"))], || body_update(&args(&["--pr", "12", "--repo", "owner/repo", "--body-file", body]))), ExitCode::SUCCESS);
    let pull = pull_json(12, "Body\n\nCloses #12\n"); assert_eq!(github([response(200, format!("[{pull}]")), response(200, pull)], || body_update(&args(&["--pr", BRANCH, "--repo", "owner/repo", "--body-file", body]))), ExitCode::SUCCESS);
    assert_eq!(github([response(200, pull_json(12, "different"))], || body_update(&args(&["--pr", "https://github.com/owner/repo/pull/12", "--repo", "owner/repo", "--body-file", body]))), ExitCode::from(2));
    assert!(create_pull_request("bad", BRANCH, "T", "B", "main", false).is_err()); assert!(update_pull_request_body("bad", 12, "B").is_err()); assert!(open_pull_request("bad", BRANCH).is_err()); assert!(pull_request_for_head("bad", BRANCH).is_err());
    assert_eq!(resolve_pr_selector("owner/repo", ""), None); assert_eq!(github_pr_url_number("owner/repo", "https://github.com/owner/repo/pull/12/files"), None); assert_eq!(qualify_github_head("owner/repo", Some("invalid"), "feature"), "feature"); assert_eq!(body_update(&args(&["--pr", "12", "--body-file", body])), ExitCode::from(2));
}

fn exercise_checks() {
    assert_eq!(checks(&args(&["--pr", "x", "--repo", "owner/repo"])), ExitCode::from(1)); assert_eq!(checks(&args(&["--pr", "1", "--repo", "bad"])), ExitCode::from(2));
    for (state, status, conclusion, code) in [("success", "completed", Some("success"), 0), ("pending", "in_progress", None, 8), ("failure", "completed", Some("failure"), 1), ("success", "completed", Some("skipped"), 0)] {
        let statuses = format!(r#"{{"state":"{state}","total_count":1,"statuses":[{{"context":"status","state":"{state}","target_url":null,"description":null}}]}}"#);
        let runs = format!(r#"{{"check_runs":[{{"name":"build","status":"{status}","conclusion":{},"details_url":null,"started_at":null,"completed_at":null}}]}}"#, serde_json::to_string(&conclusion).expect("conclusion"));
        assert_eq!(github([response(200, statuses), response(200, runs)], || checks(&args(&["--pr", "7", "--repo", "owner/repo"]))), ExitCode::from(code));
    }
    assert_eq!(github([response(200, r#"{"state":"success","total_count":0,"statuses":[]}"#), response(200, r#"{"check_runs":[]}"#)], || checks(&args(&["--pr", "7", "--repo", "owner/repo"]))), ExitCode::from(1));
    assert_eq!(github([response(400, r#"{"message":"refused"}"#)], || checks(&args(&["--pr", "7", "--repo", "owner/repo"]))), ExitCode::from(1));
}

fn exercise_closes(body_file: &Path) {
    assert_eq!(closes_issue(&args(&["--body-file", text(body_file)])), ExitCode::SUCCESS); assert_eq!(closes_issue(&args(&["--repo", "bad"])), ExitCode::from(2));
    assert_eq!(closes_issue(&args(&[])), ExitCode::SUCCESS);
    assert_eq!(github([response(200, format!("[{}]", pull_json(12, "Closes #12")))], || closes_issue(&args(&["--repo", "owner/repo"]))), ExitCode::SUCCESS);
}

fn github<T>(exchanges: impl IntoIterator<Item = IssueServiceExchange>, action: impl FnOnce() -> T) -> T {
    let server = IssueServiceStub::start(exchanges).expect("loopback service"); let base = server.base_url().to_owned(); let factory = Arc::new(move || OctocrabGitHubService::with_test_base(&base));
    let result = with_test_github_service(factory, action); server.finish().expect("completed requests"); result
}

fn response(status: u16, body: impl Into<Vec<u8>>) -> IssueServiceExchange { IssueServiceExchange::any_json(status, body).expect("JSON response") }
fn pull_json(number: u64, body: &str) -> String { json!({"number":number,"state":"open","title":"Requested title","body":body,"head":{"ref":BRANCH,"label":format!("owner:{BRANCH}"),"sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},"base":{"ref":"main"},"draft":false,"merged":false,"merge_commit_sha":null}).to_string() }
fn repository_json() -> String { json!({"id":1,"name":"repo","full_name":"owner/repo","private":false,"html_url":"https://github.com/owner/repo","url":"https://example.invalid/repos/owner/repo","default_branch":"main"}).to_string() }
fn args(values: &[&str]) -> Vec<OsString> { values.iter().map(OsString::from).collect() }
fn text(path: &Path) -> &str { path.to_str().expect("UTF-8 fixture path") }
fn git(root: &Path, values: &[&str]) { command("git", values, root); }
fn scope_child(root: &Path, tmpdir: &Path, allowed: bool) { let mut child = Command::new(env::current_exe().expect("test executable")); child.args(["--exact", "pr_commands::coverage_tests::compact::lifecycle_commands_cover_git_and_github_success_paths", "--nocapture"]).current_dir(root).env(CHILD, "1").env("LARCH_PR_SCOPE_ONLY", "1").env("IMPLEMENT_TMPDIR", tmpdir); if allowed { child.env("LARCH_PR_SCOPE_ALLOWED", "1"); } let status = child.status().expect("scope test child"); assert!(status.success(), "isolated scope child failed: {status}"); }
fn command(program: &str, values: &[&str], root: &Path) { let output = Command::new(program).args(values).current_dir(root).output().expect("fixture command"); assert!(output.status.success(), "{program} {values:?}: {}", String::from_utf8_lossy(&output.stderr)); }
}
