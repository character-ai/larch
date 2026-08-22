//! The `/implement` Preflight gate: admission, plan extraction, and health.
//!
//! Preflight only sequences commands that already own their policy. `admission
//! gate` decides admission, `plan-block read` and the shared plan grammar decide
//! the executable-plan contract, the Rust `issue governance-gate`
//! decides migration governance, and `ci main-health` decides main's CI health.
//! This module adds no policy of its own; it publishes one self-validated
//! machine envelope for the skill to parse.
//!
//! Issue snapshots come from the Octocrab-backed `GitHubService` whose sole
//! credential is `gh auth token` (issue #7672), and the declared base scope is
//! resolved through `gix` (issue #7671) rather than a Git subprocess.

use std::{
    collections::HashSet,
    env,
    ffi::OsString,
    fmt::Write as _,
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
};

use larch_adapters::GixRepository;
use larch_core::{
    ChildEnvironment, FORCE_PLAN_CONTRACT_ERROR, GitHubIssue, GitHubIssueState,
    GitHubRepositoryRef, GitHubService as _, REASON_STALE_PLAN_BODY, RepositoryRead as _,
    TRAILER_KEYS, TrailerKey, issue_plan_marker_defect, match_trailer_line, parse_final_trailers,
    parse_named_block, parse_receipt, single_line, tier_valid, validate_plan_contract,
};

use crate::{
    argparse_compat::parse_required_with_help,
    blocker_commands::resolve_repo_for,
    github_service::{ServiceFailure, with_github_service},
    implement_bootstrap_continuation::resolve_revision_sha,
    implement_child_seam::{child_streams, delegate_larch_with_environment, resolve_plugin_root},
    implement_commands::{kv_value, read_kv_first, write_atomic},
    python_verb::publish_session_environment,
};

const PROGRAM: &str = "cli.py implement preflight";
const USAGE: &str =
    "usage: cli.py implement preflight --issue N [--repo R] [--force] --preflight-tmpdir D";
const HELP: &str = concat!(
    "usage: cli.py implement preflight --issue N [--repo R] [--force] --preflight-tmpdir D\n",
    "\n",
    "options:\n",
    "  -h, --help            show this help message and exit\n",
    "  --issue ISSUE\n",
    "  --repo REPO\n",
    "  --force, -f\n",
    "  --preflight-tmpdir PREFLIGHT_TMPDIR",
);
const OPTIONS: [&str; 3] = ["--issue", "--repo", "--preflight-tmpdir"];
const FLAGS: [&str; 2] = ["--force", "-f"];

/// The envelope keys, in the exact order the skill parses them.
const SUCCESS_ENVELOPE_KEYS: [&str; 15] = [
    "ADMISSION_RESULT",
    "RESUME",
    "TITLE",
    "BLOCK_PRESENT",
    "PLAN_PATH",
    "ISSUE_JSON_PATH",
    "BYPASS_COUNT",
    "PLAN_RECEIPT_SCOPE_REVALIDATION",
    "PLAN_RECEIPT_PREVIOUS_BASE_SHA",
    "PLAN_RECEIPT_TARGET_BASE_SHA",
    "DESIGN_DIFFICULTY",
    "MAIN_CI_STATUS",
    "MAIN_FAILED_RUN_ID",
    "MAIN_HEALTH_HEAD_SHA",
    "MAIN_HEALTH_DETAIL",
];
const MAIN_HEALTH_KEYS: [&str; 4] = [
    "MAIN_CI_STATUS",
    "MAIN_FAILED_RUN_ID",
    "MAIN_HEALTH_HEAD_SHA",
    "MAIN_HEALTH_DETAIL",
];
/// Statuses `ci main-health` may report, in its own declared order.
const MAIN_HEALTH_STATUS_ORDER: [&str; 5] = ["pass", "fail", "pending", "error", "skip"];
/// Ceiling `ci main-health` applies to its single-line detail.
const MAIN_HEALTH_DETAIL_MAX_CHARS: usize = 240;

#[cfg(test)]
std::thread_local! {
    /// A declared substitute for the repository root the base scope resolves in.
    static TEST_REPO_ROOT: std::cell::RefCell<Option<PathBuf>> = const { std::cell::RefCell::new(None) };
}

/// Verify admission, extract the plan, and probe main's CI health.
pub fn preflight(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_required_with_help(
        arguments,
        PROGRAM,
        USAGE,
        HELP,
        &OPTIONS,
        &FLAGS,
        &["--issue", "--preflight-tmpdir"],
    ) {
        Ok(parsed) => parsed,
        Err(code) => return code,
    };
    let issue = parsed
        .value("--issue")
        .unwrap_or_default()
        .to_string_lossy()
        .into_owned();
    if issue.is_empty()
        || !issue.bytes().all(|byte| byte.is_ascii_digit())
        || issue.parse::<u64>().is_ok_and(|number| number == 0)
    {
        eprintln!("{USAGE}");
        return ExitCode::from(2);
    }
    let request = Request {
        issue,
        repo: parsed
            .value("--repo")
            .unwrap_or_default()
            .to_string_lossy()
            .into_owned(),
        force: parsed.flag("--force") || parsed.flag("-f"),
        tmpdir: PathBuf::from(parsed.value("--preflight-tmpdir").unwrap_or_default()),
    };
    run(&request)
}

/// One validated Preflight command line.
struct Request {
    issue: String,
    repo: String,
    force: bool,
    tmpdir: PathBuf,
}

impl Request {
    /// Return the `--repo R` pair a composed child needs, or nothing.
    fn repo_arguments(&self) -> Vec<OsString> {
        if self.repo.is_empty() {
            Vec::new()
        } else {
            vec![OsString::from("--repo"), OsString::from(&self.repo)]
        }
    }
}

fn run(request: &Request) -> ExitCode {
    if fs::create_dir_all(&request.tmpdir).is_err() {
        return refuse("cannot create preflight tmpdir.");
    }
    let probe = request.tmpdir.join(".write-test");
    if fs::write(&probe, "").is_err() {
        return refuse("preflight tmpdir is not writable.");
    }
    let _removed = fs::remove_file(&probe);
    if !resolve_plugin_root().is_ok_and(|root| root.join("python").join("cli.py").is_file()) {
        return refuse("cannot resolve CLAUDE_PLUGIN_ROOT/python/cli.py.");
    }
    let environment = session_environment();
    let admission = match admit(request, &environment) {
        Ok(admission) => admission,
        Err(code) => return code,
    };
    let issue_json_path = request.tmpdir.join("issue.json");
    let snapshot = match materialize_issue(request, &issue_json_path) {
        Ok(snapshot) => snapshot,
        Err(code) => return code,
    };
    let plan_path = request.tmpdir.join("plan-from-issue.txt");
    if let Err(code) = read_plan_block(request, &environment, &plan_path) {
        return code;
    }
    let repo_root = repo_root();
    let tracked = match load_tracked_paths(&repo_root) {
        Ok(tracked) => tracked,
        Err(detail) => return refuse(&format!("cannot read repository index: {detail}")),
    };
    let plan = match extract_plan(request, &snapshot.body, &repo_root, &tracked, &plan_path) {
        Ok(plan) => plan,
        Err(code) => return code,
    };
    let scope = match governance(request, &snapshot.body, &repo_root) {
        Ok(scope) => scope,
        Err(code) => return code,
    };
    let difficulty = match plan_metadata(request, &plan) {
        Ok(difficulty) => difficulty,
        Err(code) => return code,
    };
    let values = [
        ("ADMISSION_RESULT", admission.result),
        ("RESUME", admission.resume),
        ("TITLE", single_line(&snapshot.title)),
        ("BLOCK_PRESENT", "true".to_owned()),
        ("PLAN_PATH", plan_path.to_string_lossy().into_owned()),
        (
            "ISSUE_JSON_PATH",
            issue_json_path.to_string_lossy().into_owned(),
        ),
        ("BYPASS_COUNT", bypass_count(&request.tmpdir).to_string()),
        (
            "PLAN_RECEIPT_SCOPE_REVALIDATION",
            scope.revalidation.to_string(),
        ),
        ("PLAN_RECEIPT_PREVIOUS_BASE_SHA", scope.previous_base_sha),
        ("PLAN_RECEIPT_TARGET_BASE_SHA", scope.target_base_sha),
        ("DESIGN_DIFFICULTY", difficulty),
    ];
    let mut rows: Vec<(&str, String)> = values.into();
    rows.extend(main_health_rows(request));
    emit_success_envelope(&rows, &plan_path, &issue_json_path)
}

/// Print one Preflight refusal in the retired owner's exact wording.
fn refuse(message: &str) -> ExitCode {
    println!("**❌ /implement preflight: {message}**");
    ExitCode::from(2)
}

/// Publish the session identity every composed child must observe.
///
/// `scripts/larch.sh` forwards the reviewed context allowlist, which does not
/// carry `RUN_ID`. The retired owner learned that identity from the resumed
/// session's own sentinel, so it is forwarded explicitly here instead.
fn session_environment() -> Vec<(ChildEnvironment, OsString)> {
    let mut rows = vec![(ChildEnvironment::LarchQuietDisable, OsString::from("1"))];
    let run_id = env::var("RUN_ID").unwrap_or_default();
    let run_id = if run_id.is_empty() {
        env::var("IMPLEMENT_TMPDIR")
            .ok()
            .filter(|value| !value.is_empty())
            .map(|tmpdir| read_kv_first(&Path::new(&tmpdir).join("parent-issue.md"), "RUN_ID"))
            .unwrap_or_default()
    } else {
        run_id
    };
    if !run_id.is_empty() {
        let row = (ChildEnvironment::RunId, OsString::from(run_id));
        rows.push(row.clone());
        publish_session_environment(vec![row]);
    }
    rows
}

/// What `admission gate` decided about this issue.
struct Admission {
    result: String,
    resume: String,
}

fn admit(
    request: &Request,
    environment: &[(ChildEnvironment, OsString)],
) -> Result<Admission, ExitCode> {
    let mut arguments = vec![OsString::from("admission"), OsString::from("gate")];
    arguments.extend([OsString::from("--issue"), OsString::from(&request.issue)]);
    arguments.extend(request.repo_arguments());
    // The gate's refusal text is the operator's only diagnostic here, so quiet
    // mode must not swallow it.
    let mut gate_environment = environment.to_vec();
    gate_environment.push((ChildEnvironment::LarchQuietDisable, OsString::from("1")));
    let (code, stdout) = capture(request, &arguments, &gate_environment, "admission");
    let result = kv_value(&stdout, "ADMISSION_RESULT");
    if code != 0 {
        if result != "missing-designed-prefix" || !request.force {
            print_admission_refusal(&stdout);
            return Err(ExitCode::from(2));
        }
        println!(
            "**⚠ /implement --force: admission gate blocked on missing [DESIGNED] prefix for issue #{} (title: {}); bypassing and proceeding.**",
            request.issue,
            kv_value(&stdout, "TITLE")
        );
        if append_bypass(&request.tmpdir, "missing-designed-prefix", &request.issue).is_err() {
            return Err(refuse("cannot append force bypass log."));
        }
    } else if result != "pass" {
        print_admission_refusal(&stdout);
        return Err(ExitCode::from(2));
    }
    Ok(Admission {
        resume: if kv_value(&stdout, "RESUME") == "true" {
            "true".to_owned()
        } else {
            "false".to_owned()
        },
        result,
    })
}

/// Report the admission refusal, then only the field that refusal explains.
fn print_admission_refusal(stdout: &str) {
    let error = kv_value(stdout, "ADMISSION_ERROR");
    if !error.is_empty() {
        println!("**❌ /implement preflight: admission blocked: `ADMISSION_ERROR={error}`**");
        return;
    }
    let mut result = kv_value(stdout, "ADMISSION_RESULT");
    if result.is_empty() {
        "missing".clone_into(&mut result);
    }
    println!("**❌ /implement preflight: admission blocked: `ADMISSION_RESULT={result}`**");
    let echo = |key: &str| {
        let value = kv_value(stdout, key);
        if !value.is_empty() {
            println!("{key}={value}");
        }
    };
    match result.as_str() {
        "missing-designed-prefix" | "managed-prefix" | "report-title" => echo("TITLE"),
        "has-blockers" => echo("BLOCKERS"),
        _other => (),
    }
}

/// The issue identity Preflight freezes for every later step.
struct IssueSnapshot {
    title: String,
    body: String,
}

/// Freeze the issue snapshot the tracking lease later re-checks byte for byte.
fn materialize_issue(request: &Request, path: &Path) -> Result<IssueSnapshot, ExitCode> {
    let stderr_path = request.tmpdir.join("gh-issue-view.stderr");
    let read = read_issue(&request.repo, &request.issue);
    let (json, detail) = match &read {
        Ok(issue) => (render_issue_json(issue), String::new()),
        Err(detail) => (String::new(), format!("{detail}\n")),
    };
    if write_atomic(path, &json).is_err() || write_atomic(&stderr_path, &detail).is_err() {
        return Err(refuse("cannot write issue view artifacts."));
    }
    match read {
        Ok(issue) => Ok(IssueSnapshot {
            title: issue.title,
            body: issue.body,
        }),
        Err(_detail) => {
            println!(
                "**❌ /implement preflight: gh issue view failed for issue #{}.**",
                request.issue
            );
            Err(ExitCode::from(2))
        }
    }
}

/// Read one issue through the hardened Octocrab service (issue #7672).
fn read_issue(repo: &str, issue: &str) -> Result<GitHubIssue, String> {
    let slug =
        resolve_repo_for(Some(repo)).ok_or_else(|| "cannot resolve repository".to_owned())?;
    let (owner, name) = slug
        .split_once('/')
        .ok_or_else(|| format!("repository slug must be owner/name: {slug}"))?;
    let reference = GitHubRepositoryRef::new(owner, name).map_err(|error| error.to_string())?;
    let number: u64 = issue
        .parse()
        .map_err(|_error| format!("issue must be a number: {issue}"))?;
    with_github_service(async |service, cancellation| {
        service
            .issue(&reference, number, cancellation)
            .await
            .map_err(|error| error.to_string())
    })
    .map_err(ServiceFailure::into_detail)
}

/// Render the exact `gh issue view --json` field set later steps re-read.
fn render_issue_json(issue: &GitHubIssue) -> String {
    let labels: Vec<serde_json::Value> = issue
        .labels
        .iter()
        .map(|label| {
            serde_json::json!({
                "id": label.id,
                "name": label.name,
                "description": label.description,
                "color": label.color,
            })
        })
        .collect();
    let state = match issue.state {
        GitHubIssueState::Closed => "CLOSED",
        GitHubIssueState::Open | GitHubIssueState::All => "OPEN",
    };
    let document = serde_json::json!({
        "body": issue.body,
        "labels": labels,
        "number": issue.number,
        "state": state,
        "title": issue.title,
        "updatedAt": issue.updated_at,
    });
    format!("{document}\n")
}

/// Let `plan-block read` publish its own diagnostics before local extraction.
fn read_plan_block(
    request: &Request,
    environment: &[(ChildEnvironment, OsString)],
    plan_path: &Path,
) -> Result<(), ExitCode> {
    let mut arguments = vec![OsString::from("plan-block"), OsString::from("read")];
    arguments.extend([OsString::from("--issue"), OsString::from(&request.issue)]);
    arguments.extend([OsString::from("--output"), plan_path.as_os_str().to_owned()]);
    arguments.extend(request.repo_arguments());
    let (code, stdout) = capture(request, &arguments, environment, "plan-block");
    // A malformed block is a contract defect the shared grammar reports below,
    // not a failed read.
    let malformed_block = code == 1 && !kv_value(&stdout, "MALFORMED").is_empty();
    if code != 0 && !malformed_block {
        println!(
            "**❌ /implement preflight: plan-block read failed for issue #{}.**",
            request.issue
        );
        return Err(ExitCode::from(2));
    }
    Ok(())
}

/// Load the tracked-path set the plan-contract M2 checks require.
///
/// An empty set makes every `### UPDATED:` path look missing, so Preflight
/// must read the live index through `gix` (#7671) before validating.
fn load_tracked_paths(repo_root: &Path) -> Result<HashSet<String>, String> {
    let repository = GixRepository::open(repo_root).map_err(|error| error.to_string())?;
    let mut tracked = HashSet::new();
    for path in repository
        .tracked_paths()
        .map_err(|error| error.to_string())?
    {
        let text = std::str::from_utf8(path.as_bytes()).map_err(|error| error.to_string())?;
        tracked.insert(text.to_owned());
    }
    Ok(tracked)
}

/// Validate the issue's executable-plan contract, then freeze the plan text.
fn extract_plan(
    request: &Request,
    body: &str,
    repo_root: &Path,
    tracked: &HashSet<String>,
    plan_path: &Path,
) -> Result<String, ExitCode> {
    if let Some(defect) = issue_plan_marker_defect(body) {
        return Err(refuse_plan_contract(request, &[defect]));
    }
    let Ok(Some(inner)) = parse_named_block(body, "plan") else {
        return Err(refuse_plan_contract(request, &["missing-plan-block"]));
    };
    let contract = validate_plan_contract(&inner, repo_root, tracked);
    if !contract.defects.is_empty() {
        return Err(refuse_plan_contract(request, &contract.defects));
    }
    if write_atomic(plan_path, &inner).is_err() {
        return Err(refuse("cannot write extracted plan."));
    }
    Ok(inner)
}

fn refuse_plan_contract(request: &Request, defects: &[&str]) -> ExitCode {
    let tokens = defects.join(",");
    if request.force {
        println!(
            "**❌ /implement --force: issue #{} failed executable-plan admission: `{tokens}`.**",
            request.issue
        );
        println!("{FORCE_PLAN_CONTRACT_ERROR}");
    } else {
        println!(
            "**❌ Issue #{issue} failed executable-plan admission: `{tokens}`. Run /design {issue} to repair the plan block before retrying /implement.**",
            issue = request.issue
        );
    }
    ExitCode::from(2)
}

/// The conditional receipt refresh a successful Preflight authorizes.
#[derive(Default)]
struct ReceiptScope {
    revalidation: bool,
    previous_base_sha: String,
    target_base_sha: String,
}

/// Consume the Rust migration-governance verdict for this issue.
///
/// `issue governance-gate --preflight-envelope` keeps blocker, receipt, and
/// active-owner policy with its single Rust owner; this reads that envelope
/// and prints the operator prose it implies.
fn governance(request: &Request, body: &str, repo_root: &Path) -> Result<ReceiptScope, ExitCode> {
    let Some(gate_repo) = resolve_repo_for(Some(&request.repo)) else {
        return Err(refuse("repository slug required for migration governance."));
    };
    let base_target = if request.repo.is_empty() {
        "origin/main"
    } else {
        "upstream/main"
    };
    let base_target_sha = match resolve_revision_sha(repo_root, base_target) {
        Ok(sha) => sha,
        Err(detail) => return Err(refuse_governance_read(&detail)),
    };
    let body_file = request.tmpdir.join("governance-body.md");
    if write_atomic(&body_file, body).is_err() {
        return Err(refuse("cannot write migration governance body."));
    }
    let mut argv = governance_gate_argv(
        &request.issue,
        &gate_repo,
        &body_file,
        repo_root,
        &base_target_sha,
    );
    argv.push(OsString::from("--preflight-envelope"));
    let Ok(output) = delegate_larch_with_environment(&argv, &[]) else {
        return Err(refuse_governance_read("cannot start issue governance-gate"));
    };
    let envelope = String::from_utf8_lossy(output.stdout()).into_owned();
    let error = kv_value(&envelope, "ENVELOPE_ERROR");
    if !error.is_empty() {
        return Err(refuse_governance_read(&error));
    }
    if !output.status().success() {
        let refusal = kv_value(&envelope, "REFUSAL_TEXT");
        if refusal.is_empty() {
            return Err(refuse_governance_read(
                "governance gate produced no verdict",
            ));
        }
        println!("{refusal}");
        print_governance_remediation(request, &kv_value(&envelope, "BLOCKING_REASONS"));
        return Err(ExitCode::from(2));
    }
    let mut scope = ReceiptScope::default();
    for token in kv_value(&envelope, "SEMANTIC_REASONS")
        .split(',')
        .filter(|token| !token.is_empty())
    {
        println!(
            "**⚠ /implement preflight: `{token}`; semantic materiality must revalidate plan-cited paths and symbols before refreshing the receipt.**"
        );
        let Some(receipt) = parse_receipt(body) else {
            return Err(refuse(
                "receipt identity unavailable for semantic revalidation.",
            ));
        };
        scope = ReceiptScope {
            revalidation: true,
            previous_base_sha: receipt.base_sha,
            target_base_sha: base_target_sha.clone(),
        };
    }
    print_report_only_warnings(&envelope);
    Ok(scope)
}

fn refuse_governance_read(detail: &str) -> ExitCode {
    refuse(&format!("migration governance read failed: {detail}."))
}

fn print_governance_remediation(request: &Request, blocking_reasons: &str) {
    let reasons: Vec<&str> = blocking_reasons.split(',').collect();
    if reasons.contains(&REASON_STALE_PLAN_BODY) {
        println!(
            "**→ Remediation: re-run `/design {}` to repair or replace the plan. A `[DESIGNED]` issue with a plan enters the replace flow directly.**",
            request.issue
        );
    } else if reasons.contains(&"plan-base-scope-unavailable") {
        println!(
            "**→ Remediation: retry `/implement` when the declared base scope is readable; do not refresh the receipt manually.**"
        );
    }
}

fn print_report_only_warnings(envelope: &str) {
    let count: usize = kv_value(envelope, "REPORT_ONLY_COUNT").parse().unwrap_or(0);
    for index in 0..count {
        let token = kv_value(envelope, &format!("REPORT_ONLY_{index}"));
        let command = kv_value(envelope, &format!("CLEANUP_{index}"));
        println!("**⚠ /implement preflight: `{token}`. Cleanup: `{command}`.**");
    }
}

/// Refuse an unreviewed or malformed plan, then return its difficulty prior.
fn plan_metadata(request: &Request, plan: &str) -> Result<String, ExitCode> {
    if let Some(malformed) = malformed_terminal_metadata(plan) {
        let (key, value) = malformed
            .split_once(':')
            .unwrap_or((malformed.as_str(), ""));
        return Err(refuse_plan_metadata(
            request,
            &format!("malformed plan review metadata: `{key}={}`", value.trim()),
        ));
    }
    let review_status = trailer_value(plan, TrailerKey::ReviewStatus);
    if review_status == "panel-init-failed" || review_status == "panel-skipped" {
        return Err(refuse_plan_metadata(
            request,
            &format!("plan review did not run: `review_status={review_status}`"),
        ));
    }
    let rounds = trailer_value(plan, TrailerKey::RoundsCompleted);
    if !rounds.is_empty() {
        if !rounds.bytes().all(|byte| byte.is_ascii_digit()) {
            return Err(refuse_plan_metadata(
                request,
                &format!("malformed plan review metadata: `rounds_completed={rounds}`"),
            ));
        }
        if rounds.parse::<u64>().unwrap_or(0) == 0 {
            return Err(refuse_plan_metadata(
                request,
                "plan review did not run: `rounds_completed=0`",
            ));
        }
    }
    let tier = trailer_value(plan, TrailerKey::Difficulty);
    if tier.is_empty() || tier_valid(&tier) {
        return Ok(tier);
    }
    let message = format!("malformed difficulty metadata: `difficulty={tier}`");
    if request.force {
        println!(
            "**⚠ /implement --force: {message}; ignoring the design prior for issue #{}.**",
            request.issue
        );
        return Ok(String::new());
    }
    Err(refuse_plan_metadata(request, &message))
}

fn refuse_plan_metadata(request: &Request, message: &str) -> ExitCode {
    println!(
        "**❌ /implement preflight: {message}. Re-run /design {} before retrying /implement.**",
        request.issue
    );
    ExitCode::from(2)
}

/// Return one terminal trailer's raw value, or nothing when absent.
fn trailer_value(plan: &str, key: TrailerKey) -> String {
    let trailers = parse_final_trailers(plan, true);
    if trailers.matches.is_empty() {
        return String::new();
    }
    trailers
        .get(key)
        .map(|item| item.value.clone())
        .unwrap_or_default()
}

/// Return the first malformed recognized trailer adjacent to terminal metadata.
fn malformed_terminal_metadata(plan: &str) -> Option<String> {
    let mut lines: Vec<&str> = plan.lines().collect();
    while lines.last().is_some_and(|line| line.trim().is_empty()) {
        lines.pop();
    }
    let last = match_trailer_line(lines.last()?)?;
    if last.key != TrailerKey::DiffLines {
        return None;
    }
    for line in lines.iter().rev() {
        if !TRAILER_KEYS
            .iter()
            .any(|key| line.starts_with(&format!("{key}:")))
        {
            break;
        }
        if match_trailer_line(line).is_none() {
            return Some((*line).to_owned());
        }
    }
    None
}

/// Probe main's CI health, degrading every failure to an `error` verdict.
fn main_health_rows(request: &Request) -> Vec<(&'static str, String)> {
    let rows = read_main_health(request);
    let text = MAIN_HEALTH_KEYS
        .iter()
        .fold(String::new(), |mut text, key| {
            let value = rows.iter().find(|(name, _value)| name == key);
            let _row = writeln!(
                text,
                "{key}={}",
                value.map_or("", |(_name, value)| value.as_str())
            );
            text
        });
    if write_atomic(&request.tmpdir.join("main-health.env"), &text).is_err() {
        return main_health_error("cannot write main-health.env");
    }
    rows
}

fn read_main_health(request: &Request) -> Vec<(&'static str, String)> {
    let Some(repo) = resolve_repo_for(Some(&request.repo)) else {
        return main_health_error("repo resolution failed");
    };
    match crate::ci_failure_commands::preflight_main_health(&repo, "main") {
        Ok(status) => vec![
            ("MAIN_CI_STATUS", single_line(&status.status)),
            ("MAIN_FAILED_RUN_ID", single_line(&status.failed_run_id)),
            ("MAIN_HEALTH_HEAD_SHA", single_line(&status.head_sha)),
            ("MAIN_HEALTH_DETAIL", single_line(&status.detail)),
        ],
        Err(detail) => main_health_error(&format!("main-health probe failed: {detail}")),
    }
}

fn main_health_error(detail: &str) -> Vec<(&'static str, String)> {
    vec![
        ("MAIN_CI_STATUS", "error".to_owned()),
        ("MAIN_FAILED_RUN_ID", String::new()),
        ("MAIN_HEALTH_HEAD_SHA", String::new()),
        (
            "MAIN_HEALTH_DETAIL",
            detail
                .split_whitespace()
                .collect::<Vec<_>>()
                .join(" ")
                .chars()
                .take(MAIN_HEALTH_DETAIL_MAX_CHARS)
                .collect(),
        ),
    ]
}

/// Publish the envelope only after it satisfies its own declared contract.
fn emit_success_envelope(
    rows: &[(&str, String)],
    plan_path: &Path,
    issue_json_path: &Path,
) -> ExitCode {
    if let Some(error) = envelope_error(rows, plan_path, issue_json_path) {
        println!("**❌ /implement preflight: malformed success envelope: {error}.**");
        return ExitCode::from(2);
    }
    for key in SUCCESS_ENVELOPE_KEYS {
        println!("{key}={}", envelope_value(rows, key));
    }
    ExitCode::SUCCESS
}

fn envelope_value(rows: &[(&str, String)], key: &str) -> String {
    rows.iter()
        .find(|(name, _value)| *name == key)
        .map(|(_name, value)| value.clone())
        .unwrap_or_default()
}

fn envelope_error(
    rows: &[(&str, String)],
    plan_path: &Path,
    issue_json_path: &Path,
) -> Option<String> {
    let mut seen: Vec<&str> = Vec::new();
    for (key, _value) in rows {
        if seen.contains(key) {
            return Some(format!("duplicate key {key}"));
        }
        seen.push(key);
    }
    if let Some(missing) = SUCCESS_ENVELOPE_KEYS
        .iter()
        .find(|key| !seen.contains(*key))
    {
        return Some(format!("missing key {missing}"));
    }
    let value = |key: &str| envelope_value(rows, key);
    if !["true", "false"].contains(&value("RESUME").as_str()) {
        return Some("RESUME must be true or false".to_owned());
    }
    if value("TITLE").contains(['\n', '\r']) {
        return Some("TITLE must be single-line".to_owned());
    }
    if value("PLAN_PATH") != plan_path.to_string_lossy() {
        return Some("PLAN_PATH must match preflight tmpdir".to_owned());
    }
    if value("ISSUE_JSON_PATH") != issue_json_path.to_string_lossy() {
        return Some("ISSUE_JSON_PATH must match preflight tmpdir".to_owned());
    }
    if !plan_path.is_file() {
        return Some("PLAN_PATH must be readable".to_owned());
    }
    if !issue_json_path.is_file() {
        return Some("ISSUE_JSON_PATH must be readable".to_owned());
    }
    let bypass = value("BYPASS_COUNT");
    if bypass.is_empty() || !bypass.bytes().all(|byte| byte.is_ascii_digit()) {
        return Some("BYPASS_COUNT must be numeric".to_owned());
    }
    let revalidation = value("PLAN_RECEIPT_SCOPE_REVALIDATION");
    if !["true", "false"].contains(&revalidation.as_str()) {
        return Some("PLAN_RECEIPT_SCOPE_REVALIDATION must be true or false".to_owned());
    }
    let previous = value("PLAN_RECEIPT_PREVIOUS_BASE_SHA");
    let target = value("PLAN_RECEIPT_TARGET_BASE_SHA");
    if revalidation == "true" {
        if !sha1_hex(&previous) || !sha1_hex(&target) {
            return Some("receipt scope revalidation requires two SHA values".to_owned());
        }
    } else if !previous.is_empty() || !target.is_empty() {
        return Some("receipt scope SHA values require revalidation".to_owned());
    }
    if !MAIN_HEALTH_STATUS_ORDER.contains(&value("MAIN_CI_STATUS").as_str()) {
        let (last, leading) = MAIN_HEALTH_STATUS_ORDER
            .split_last()
            .expect("the status order is never empty");
        return Some(format!(
            "MAIN_CI_STATUS must be {}, or {last}",
            leading.join(", ")
        ));
    }
    MAIN_HEALTH_KEYS
        .iter()
        .find(|key| value(key).contains(['\n', '\r']))
        .map(|key| format!("{key} must be single-line"))
}

fn sha1_hex(value: &str) -> bool {
    value.len() == 40
        && value
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
}

/// Run one already-owned command, persisting its streams as diagnostics.
fn capture(
    request: &Request,
    arguments: &[OsString],
    environment: &[(ChildEnvironment, OsString)],
    name: &str,
) -> (i32, String) {
    let (code, stdout, stderr) =
        child_streams(&delegate_larch_with_environment(arguments, environment));
    let _stdout = write_atomic(&request.tmpdir.join(format!("{name}.stdout")), &stdout);
    let _stderr = write_atomic(&request.tmpdir.join(format!("{name}.stderr")), &stderr);
    (code, stdout)
}

/// Append one force-bypass record for the envelope's `BYPASS_COUNT`.
fn append_bypass(tmpdir: &Path, kind: &str, issue: &str) -> Result<(), String> {
    let path = tmpdir.join("force-bypass.log");
    let mut existing = fs::read_to_string(&path).unwrap_or_default();
    let _record = writeln!(existing, "BYPASS kind={kind} issue={issue}");
    write_atomic(&path, &existing)
}

fn bypass_count(tmpdir: &Path) -> usize {
    fs::read_to_string(tmpdir.join("force-bypass.log"))
        .map(|text| text.lines().count())
        .unwrap_or(0)
}

/// Assemble the Rust `issue governance-gate` command line.
///
/// Preflight and the Step 0 bootstrap continuation both consult the same gate,
/// so its argv has one owner and only the trailing envelope flag differs.
pub fn governance_gate_argv(
    issue: &str,
    repository: &str,
    body_file: &Path,
    repo_root: &Path,
    head_sha: &str,
) -> Vec<OsString> {
    vec![
        OsString::from("issue"),
        OsString::from("governance-gate"),
        OsString::from("--issue"),
        OsString::from(issue),
        OsString::from("--repo"),
        OsString::from(repository),
        OsString::from("--body-file"),
        body_file.as_os_str().to_owned(),
        OsString::from("--repo-root"),
        repo_root.as_os_str().to_owned(),
        OsString::from("--head-sha"),
        OsString::from(head_sha),
    ]
}

/// Discover the consumer repository root, matching the retired owner's probe.
fn repo_root() -> PathBuf {
    use std::os::unix::ffi::OsStringExt as _;

    #[cfg(test)]
    if let Some(root) = TEST_REPO_ROOT.with(|slot| slot.borrow().clone()) {
        return root;
    }
    let cwd = env::current_dir().unwrap_or_default();
    GixRepository::discover(&cwd)
        .ok()
        .and_then(|repository| repository.location().work_dir)
        .and_then(|work_dir| {
            let bytes = work_dir.as_bytes().to_vec();
            (!bytes.contains(&0)).then(|| PathBuf::from(OsString::from_vec(bytes)))
        })
        .unwrap_or(cwd)
}

#[cfg(test)]
mod tests {
    use super::{
        MAIN_HEALTH_DETAIL_MAX_CHARS, Request, TEST_REPO_ROOT, admit, append_bypass, bypass_count,
        bypass_count as bypass_records, capture, emit_success_envelope, envelope_error,
        envelope_value, extract_plan, governance, governance_gate_argv, load_tracked_paths,
        main_health_error, main_health_rows, malformed_terminal_metadata, materialize_issue,
        plan_metadata, preflight, read_main_health, read_plan_block, refuse, repo_root, run,
        sha1_hex, trailer_value,
    };
    use crate::{
        github_service::with_test_github_service,
        implement_child_seam::{declare_plugin_root, install_larch},
    };
    use larch_adapters::github::OctocrabGitHubService;
    use larch_core::{ProcessOutput, ProcessStatus, TrailerKey};
    use larch_test_support::{GitFixture, GitRepository, IssueServiceExchange, IssueServiceStub};
    use serde_json::{Value, json};
    use std::{
        collections::HashSet,
        ffi::OsString,
        fs,
        path::{Path, PathBuf},
        process::ExitCode,
        sync::Arc,
    };
    use tempfile::TempDir;

    /// The plan text every plan-contract fixture in this module reuses.
    const VALID_PLAN: &str = concat!(
        "## Plan\n\n",
        "### Closed decisions and ownership\n\n",
        "- Extend preflight only.\n\n",
        "### Ordered implementation\n\n",
        "1. Validate the contract.\n",
        "2. Wire callers.\n\n",
        "## Files to modify/create\n\n",
        "### UPDATED: Cargo.toml\n\n",
        "## Acceptance\n\n",
        "- Contract holds.\n\n",
        "## Breaking changes and migration\n\n",
        "None.\n\n",
        "difficulty: HARD\n",
        "diff_lines: 42\n",
    );

    /// Read the exit code one refusing Preflight step published.
    ///
    /// Several steps return a success value that does not implement `Debug`,
    /// so the shared `expect_err` spelling is unavailable here.
    trait Refusal {
        fn refusal(self) -> ExitCode;
    }

    impl<T> Refusal for Result<T, ExitCode> {
        fn refusal(self) -> ExitCode {
            match self {
                Ok(_value) => panic!("the step must refuse"),
                Err(code) => code,
            }
        }
    }

    fn plan_body(plan: &str) -> String {
        format!("Preamble.\n\n<!-- larch:plan:start -->\n{plan}<!-- larch:plan:end -->\n")
    }

    fn receipt_line() -> String {
        format!(
            "<!-- larch:plan-receipt v1 plan_sha256={} base_sha={} blockers_sha256={} owners_sha256={} -->",
            "a".repeat(64),
            "b".repeat(40),
            "c".repeat(64),
            "d".repeat(64)
        )
    }

    fn output(code: i32, stdout: &str, stderr: &str) -> ProcessOutput {
        ProcessOutput::new(
            ProcessStatus::new(code == 0, Some(code)),
            stdout.as_bytes().to_vec(),
            stderr.as_bytes().to_vec(),
            false,
            false,
        )
    }

    fn declare_repo_root(root: &Path) {
        TEST_REPO_ROOT.with(|slot| *slot.borrow_mut() = Some(root.to_path_buf()));
    }

    fn clear_hooks() {
        crate::implement_child_seam::clear_hooks();
        TEST_REPO_ROOT.with(|slot| *slot.borrow_mut() = None);
    }

    fn workspace_root() -> PathBuf {
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
    }

    fn request(tmpdir: &Path, force: bool) -> Request {
        Request {
            issue: "12".to_owned(),
            repo: "owner/repo".to_owned(),
            force,
            tmpdir: tmpdir.to_path_buf(),
        }
    }

    fn arguments(values: &[&str]) -> Vec<OsString> {
        values.iter().map(OsString::from).collect()
    }

    /// Build one complete typed issue response for the loopback GitHub service.
    fn issue_response(number: u64, title: &str, body: &str) -> Value {
        let mut value: Value = serde_json::from_str(include_str!(
            "../../larch-adapters/fixtures/github_issue.json"
        ))
        .expect("valid issue fixture");
        value["id"] = json!(number * 10);
        value["number"] = json!(number);
        value["title"] = json!(title);
        value["body"] = json!(body);
        value["state"] = json!("open");
        value["url"] = json!(format!(
            "https://example.test/repos/owner/repo/issues/{number}"
        ));
        value["repository_url"] = json!("https://example.test/repos/owner/repo");
        value["html_url"] = json!(format!("https://github.com/owner/repo/issues/{number}"));
        value["labels"] = json!([]);
        value["updated_at"] = json!("2026-08-03T00:00:00Z");
        value
    }

    /// Start one loopback-only typed GitHub service for a command unit test.
    fn service(
        exchanges: impl IntoIterator<Item = IssueServiceExchange>,
    ) -> (
        Arc<dyn Fn() -> OctocrabGitHubService + Send + Sync>,
        IssueServiceStub,
    ) {
        let server = IssueServiceStub::start(exchanges).expect("start issue service stub");
        let base_url = server.base_url().to_owned();
        let factory: Arc<dyn Fn() -> OctocrabGitHubService + Send + Sync> =
            Arc::new(move || OctocrabGitHubService::with_test_base(&base_url));
        (factory, server)
    }

    /// Build a repository whose declared upstream base scope is readable.
    fn upstream_repository() -> GitRepository {
        let repository = GitRepository::builder(GitFixture::Refs)
            .build()
            .expect("git refs fixture");
        let updated = repository
            .git(["update-ref", "refs/remotes/upstream/main", "HEAD"])
            .expect("update upstream ref");
        assert!(updated.success(), "upstream ref must be created");
        repository
    }

    #[test]
    fn the_command_line_admits_only_a_positive_issue_number() {
        assert_eq!(preflight(&arguments(&["--help"])), ExitCode::SUCCESS);
        assert_eq!(preflight(&[]), ExitCode::from(2));
        assert_eq!(preflight(&arguments(&["--issue", "12"])), ExitCode::from(2));
        for issue in ["0", "abc", "-1", ""] {
            assert_eq!(
                preflight(&arguments(&[
                    "--issue",
                    issue,
                    "--preflight-tmpdir",
                    "/tmp/preflight"
                ])),
                ExitCode::from(2),
                "{issue}"
            );
        }
    }

    #[test]
    fn an_unusable_tmpdir_or_plugin_root_refuses_before_any_child() {
        clear_hooks();
        let root = TempDir::new().expect("temp");
        let blocker = root.path().join("blocker");
        fs::write(&blocker, "").expect("blocker");
        install_larch(|_arguments, _environment| panic!("a refusal must not compose a child"));

        assert_eq!(
            run(&request(&blocker.join("nested"), false)),
            ExitCode::from(2)
        );
        declare_plugin_root(root.path());
        assert_eq!(
            run(&request(&root.path().join("preflight"), false)),
            ExitCode::from(2)
        );
        assert_eq!(refuse("message."), ExitCode::from(2));
        clear_hooks();
    }

    #[test]
    fn a_passing_gate_reports_its_resume_state() {
        clear_hooks();
        let root = TempDir::new().expect("temp");
        install_larch(|arguments, _environment| {
            assert_eq!(arguments[0], OsString::from("admission"));
            Ok(output(0, "ADMISSION_RESULT=pass\nRESUME=true\n", ""))
        });

        let admission = admit(&request(root.path(), false), &[]).expect("admitted");

        assert_eq!(admission.result, "pass");
        assert_eq!(admission.resume, "true");
        assert!(root.path().join("admission.stdout").is_file());
        assert!(root.path().join("admission.stderr").is_file());
        clear_hooks();
    }

    #[test]
    fn every_refused_admission_reports_the_field_its_refusal_explains() {
        for stdout in [
            "ADMISSION_ERROR=gh unavailable\n",
            "ADMISSION_RESULT=missing-designed-prefix\nTITLE=Fix the gate\n",
            "ADMISSION_RESULT=managed-prefix\nTITLE=Umbrella leaf\n",
            "ADMISSION_RESULT=report-title\nTITLE=Report\n",
            "ADMISSION_RESULT=has-blockers\nBLOCKERS=7,8\n",
            "ADMISSION_RESULT=closed\n",
            "",
        ] {
            clear_hooks();
            let root = TempDir::new().expect("temp");
            let body = stdout.to_owned();
            install_larch(move |_arguments, _environment| Ok(output(1, &body, "")));

            let refused = admit(&request(root.path(), false), &[]).refusal();

            assert_eq!(refused, ExitCode::from(2), "{stdout}");
            clear_hooks();
        }
    }

    #[test]
    fn a_passing_gate_with_a_non_pass_result_still_refuses() {
        clear_hooks();
        let root = TempDir::new().expect("temp");
        install_larch(|_arguments, _environment| Ok(output(0, "ADMISSION_RESULT=resume\n", "")));

        assert_eq!(
            admit(&request(root.path(), false), &[]).refusal(),
            ExitCode::from(2)
        );
        clear_hooks();
    }

    #[test]
    fn force_bypasses_only_a_missing_designed_prefix() {
        clear_hooks();
        let root = TempDir::new().expect("temp");
        install_larch(|_arguments, _environment| {
            Ok(output(
                1,
                "ADMISSION_RESULT=missing-designed-prefix\nTITLE=Fix the gate\nRESUME=false\n",
                "",
            ))
        });

        let admission = admit(&request(root.path(), true), &[]).expect("bypassed");

        assert_eq!(admission.result, "missing-designed-prefix");
        assert_eq!(admission.resume, "false");
        assert_eq!(bypass_count(root.path()), 1);
        clear_hooks();
    }

    #[test]
    fn an_unwritable_bypass_log_refuses_the_forced_run() {
        clear_hooks();
        let root = TempDir::new().expect("temp");
        fs::create_dir(root.path().join("force-bypass.log")).expect("blocking directory");
        install_larch(|_arguments, _environment| {
            Ok(output(1, "ADMISSION_RESULT=missing-designed-prefix\n", ""))
        });

        assert_eq!(
            admit(&request(root.path(), true), &[]).refusal(),
            ExitCode::from(2)
        );
        clear_hooks();
    }

    #[test]
    fn a_bypass_log_counts_only_the_records_it_holds() {
        let root = TempDir::new().expect("temp");

        assert_eq!(bypass_records(root.path()), 0);
        append_bypass(root.path(), "missing-designed-prefix", "12").expect("first");
        append_bypass(root.path(), "missing-designed-prefix", "13").expect("second");
        assert_eq!(bypass_records(root.path()), 2);
        let log = fs::read_to_string(root.path().join("force-bypass.log")).expect("log");
        assert!(log.contains("BYPASS kind=missing-designed-prefix issue=13\n"));
    }

    #[test]
    fn an_unstartable_child_is_captured_as_a_failed_diagnostic() {
        clear_hooks();
        let root = TempDir::new().expect("temp");
        install_larch(|_arguments, _environment| Err("cannot start verified larch".to_owned()));

        let (code, stdout) = capture(
            &request(root.path(), false),
            &arguments(&["admission", "gate"]),
            &[],
            "admission",
        );

        assert_eq!(code, 1);
        assert!(stdout.is_empty());
        assert!(
            fs::read_to_string(root.path().join("admission.stderr"))
                .expect("stderr")
                .contains("cannot start verified larch")
        );
        clear_hooks();
    }

    #[test]
    fn a_malformed_plan_block_read_is_a_contract_defect_not_a_failed_read() {
        clear_hooks();
        let root = TempDir::new().expect("temp");
        let plan = root.path().join("plan-from-issue.txt");

        install_larch(|_arguments, _environment| Ok(output(0, "BLOCK_PRESENT=true\n", "")));
        read_plan_block(&request(root.path(), false), &[], &plan).expect("read");

        install_larch(|_arguments, _environment| Ok(output(1, "MALFORMED=unbalanced\n", "")));
        read_plan_block(&request(root.path(), false), &[], &plan).expect("malformed is a defect");

        install_larch(|_arguments, _environment| Ok(output(2, "", "boom\n")));
        assert_eq!(
            read_plan_block(&request(root.path(), false), &[], &plan).refusal(),
            ExitCode::from(2)
        );
        clear_hooks();
    }

    #[test]
    fn the_issue_snapshot_is_frozen_before_any_later_step() {
        clear_hooks();
        let root = TempDir::new().expect("temp");
        let path = root.path().join("issue.json");
        let title = "[DESIGNED] Fix the gate";
        let (github, server) = service([IssueServiceExchange::json(
            "GET",
            "/repos/owner/repo/issues/12",
            200,
            serde_json::to_vec(&issue_response(12, title, "Body text.")).expect("issue body"),
        )
        .expect("issue response")]);

        let snapshot = with_test_github_service(github, || {
            materialize_issue(&request(root.path(), false), &path)
        })
        .expect("snapshot");

        assert_eq!(snapshot.title, title);
        assert_eq!(snapshot.body, "Body text.");
        let rendered = fs::read_to_string(&path).expect("issue json");
        assert!(rendered.contains("\"number\":12"));
        assert!(rendered.ends_with('\n'));
        server.join().expect("one issue read");
        clear_hooks();
    }

    #[test]
    fn an_unreadable_issue_refuses_after_persisting_its_diagnostic() {
        clear_hooks();
        let root = TempDir::new().expect("temp");
        let path = root.path().join("issue.json");
        let (github, server) = service([IssueServiceExchange::json(
            "GET",
            "/repos/owner/repo/issues/12",
            404,
            b"{\"message\":\"Not Found\"}".to_vec(),
        )
        .expect("missing issue response")]);

        let refused = with_test_github_service(github, || {
            materialize_issue(&request(root.path(), false), &path)
        })
        .refusal();

        assert_eq!(refused, ExitCode::from(2));
        assert!(
            !fs::read_to_string(root.path().join("gh-issue-view.stderr"))
                .expect("stderr")
                .is_empty()
        );
        let _ = server.join();
        clear_hooks();
    }

    #[test]
    fn a_closed_issue_renders_its_state_and_labels() {
        clear_hooks();
        let root = TempDir::new().expect("temp");
        let path = root.path().join("issue.json");
        let mut response = issue_response(12, "[DESIGNED] Fix", "Body.");
        response["state"] = json!("closed");
        response["labels"] = json!([{
            "id": 1,
            "node_id": "L_1",
            "url": "https://example.test/repos/owner/repo/labels/bug",
            "name": "bug",
            "description": "A defect",
            "color": "ff0000",
            "default": false,
        }]);
        let (github, server) = service([IssueServiceExchange::json(
            "GET",
            "/repos/owner/repo/issues/12",
            200,
            serde_json::to_vec(&response).expect("issue body"),
        )
        .expect("issue response")]);

        with_test_github_service(github, || {
            materialize_issue(&request(root.path(), false), &path)
        })
        .expect("snapshot");

        let rendered = fs::read_to_string(&path).expect("issue json");
        assert!(rendered.contains("\"state\":\"CLOSED\""));
        assert!(rendered.contains("\"name\":\"bug\""));
        server.join().expect("one issue read");
        clear_hooks();
    }

    #[test]
    fn the_tracked_path_set_comes_from_the_live_index() {
        let root = repo_root();
        let tracked = load_tracked_paths(&root).expect("tracked paths");

        assert!(tracked.contains("Cargo.toml"));
        assert!(load_tracked_paths(Path::new("/nonexistent-preflight-repo")).is_err());
    }

    #[test]
    fn only_a_contract_clean_plan_block_is_frozen() {
        let root = TempDir::new().expect("temp");
        let repository = repo_root();
        let tracked = load_tracked_paths(&repository).expect("tracked paths");
        let plan_path = root.path().join("plan-from-issue.txt");
        let subject = request(root.path(), false);

        let extracted = extract_plan(
            &subject,
            &plan_body(VALID_PLAN),
            &repository,
            &tracked,
            &plan_path,
        )
        .expect("extracted");
        assert_eq!(extracted, VALID_PLAN);
        assert_eq!(
            fs::read_to_string(&plan_path).expect("frozen plan"),
            VALID_PLAN
        );

        for body in [
            "no plan block here".to_owned(),
            plan_body("### UPDATED: Cargo.toml\n"),
            "<!-- larch:plan:start -->\nunterminated\n".to_owned(),
        ] {
            assert_eq!(
                extract_plan(&subject, &body, &repository, &tracked, &plan_path).refusal(),
                ExitCode::from(2),
                "{body}"
            );
        }
        assert_eq!(
            extract_plan(
                &request(root.path(), true),
                "no plan block here",
                &repository,
                &tracked,
                &plan_path
            )
            .refusal(),
            ExitCode::from(2)
        );
        let unwritable = HashSet::from(["Cargo.toml".to_owned()]);
        assert_eq!(
            extract_plan(
                &subject,
                &plan_body(VALID_PLAN),
                &repository,
                &unwritable,
                root.path()
            )
            .refusal(),
            ExitCode::from(2)
        );
    }

    #[test]
    fn an_unreadable_base_scope_refuses_migration_governance() {
        clear_hooks();
        let root = TempDir::new().expect("temp");
        install_larch(|_arguments, _environment| {
            panic!("an unreadable base scope must not reach the gate")
        });

        assert_eq!(
            governance(&request(root.path(), false), "body", root.path()).refusal(),
            ExitCode::from(2)
        );
        clear_hooks();
    }

    #[test]
    fn a_clean_governance_verdict_reports_its_report_only_warnings() {
        clear_hooks();
        let root = TempDir::new().expect("temp");
        let repository = upstream_repository();
        install_larch(|arguments, _environment| {
            assert!(arguments.contains(&OsString::from("--preflight-envelope")));
            Ok(output(
                0,
                "SEMANTIC_REASONS=\nREPORT_ONLY_COUNT=1\nREPORT_ONLY_0=stale-owner-row\nCLEANUP_0=larch deps prune\n",
                "",
            ))
        });

        let scope = governance(&request(root.path(), false), "body", repository.root())
            .expect("clean verdict");

        assert!(!scope.revalidation);
        assert!(scope.previous_base_sha.is_empty());
        assert!(root.path().join("governance-body.md").is_file());
        clear_hooks();
    }

    #[test]
    fn a_semantic_reason_authorizes_a_scoped_receipt_refresh() {
        clear_hooks();
        let root = TempDir::new().expect("temp");
        let repository = upstream_repository();
        install_larch(|_arguments, _environment| {
            Ok(output(0, "SEMANTIC_REASONS=plan-paths-moved\n", ""))
        });
        let body = format!("Preamble.\n{}\n", receipt_line());

        let scope = governance(&request(root.path(), false), &body, repository.root())
            .expect("semantic verdict");

        assert!(scope.revalidation);
        assert_eq!(scope.previous_base_sha, "b".repeat(40));
        assert_eq!(scope.target_base_sha.len(), 40);

        assert_eq!(
            governance(
                &request(root.path(), false),
                "no receipt",
                repository.root()
            )
            .refusal(),
            ExitCode::from(2)
        );
        clear_hooks();
    }

    #[test]
    fn a_blocking_governance_verdict_prints_its_remediation() {
        for reasons in [
            larch_core::REASON_STALE_PLAN_BODY,
            "plan-base-scope-unavailable",
            "unmapped-reason",
        ] {
            clear_hooks();
            let root = TempDir::new().expect("temp");
            let repository = upstream_repository();
            let envelope = format!("REFUSAL_TEXT=**❌ blocked.**\nBLOCKING_REASONS={reasons}\n");
            install_larch(move |_arguments, _environment| Ok(output(1, &envelope, "")));

            assert_eq!(
                governance(&request(root.path(), false), "body", repository.root()).refusal(),
                ExitCode::from(2),
                "{reasons}"
            );
            clear_hooks();
        }
    }

    #[test]
    fn an_unreadable_governance_envelope_refuses() {
        for envelope in [("ENVELOPE_ERROR=gate crashed\n", 0), ("", 1)] {
            clear_hooks();
            let root = TempDir::new().expect("temp");
            let repository = upstream_repository();
            let (stdout, code) = envelope;
            let body = stdout.to_owned();
            install_larch(move |_arguments, _environment| Ok(output(code, &body, "")));

            assert_eq!(
                governance(&request(root.path(), false), "body", repository.root()).refusal(),
                ExitCode::from(2),
                "{stdout}"
            );
            clear_hooks();
        }

        clear_hooks();
        let root = TempDir::new().expect("temp");
        let repository = upstream_repository();
        install_larch(|_arguments, _environment| {
            Err("cannot start issue governance-gate".to_owned())
        });
        assert_eq!(
            governance(&request(root.path(), false), "body", repository.root()).refusal(),
            ExitCode::from(2)
        );
        clear_hooks();
    }

    #[test]
    fn the_governance_gate_argv_names_every_declared_input() {
        let argv = governance_gate_argv(
            "12",
            "owner/repo",
            Path::new("/tmp/body.md"),
            Path::new("/repo"),
            "abc123",
        );

        assert_eq!(
            argv,
            arguments(&[
                "issue",
                "governance-gate",
                "--issue",
                "12",
                "--repo",
                "owner/repo",
                "--body-file",
                "/tmp/body.md",
                "--repo-root",
                "/repo",
                "--head-sha",
                "abc123",
            ])
        );
    }

    #[test]
    fn plan_metadata_refuses_an_unreviewed_or_malformed_plan() {
        let root = TempDir::new().expect("temp");
        let subject = request(root.path(), false);

        assert_eq!(plan_metadata(&subject, VALID_PLAN).expect("tier"), "HARD");
        assert_eq!(
            plan_metadata(&subject, "### NEW: a\ndiff_lines: 10\n").expect("no tier"),
            ""
        );
        for plan in [
            "### NEW: a\ndifficulty: NOPE!!\ndiff_lines: 10\n",
            "### NEW: a\nreview_status: panel-init-failed\ndiff_lines: 10\n",
            "### NEW: a\nreview_status: panel-skipped\ndiff_lines: 10\n",
            "### NEW: a\nrounds_completed: 0\ndiff_lines: 10\n",
        ] {
            assert_eq!(
                plan_metadata(&subject, plan).refusal(),
                ExitCode::from(2),
                "{plan}"
            );
        }
        assert_eq!(
            plan_metadata(
                &subject,
                "### NEW: a\nrounds_completed: 2\ndiff_lines: 10\n"
            )
            .expect("reviewed"),
            ""
        );
        assert_eq!(trailer_value("### NEW: a\n", TrailerKey::Difficulty), "");
    }

    #[test]
    fn a_recognized_prefix_above_diff_lines_reads_as_malformed() {
        assert_eq!(
            malformed_terminal_metadata("### NEW: a\ndifficulty: NOPE!!\ndiff_lines: 10\n"),
            Some("difficulty: NOPE!!".to_owned())
        );
        assert_eq!(
            malformed_terminal_metadata("### NEW: a\ndifficulty: TRIVIAL\ndiff_lines: 10\n"),
            None
        );
        assert_eq!(malformed_terminal_metadata("### NEW: a\n"), None);
        assert_eq!(malformed_terminal_metadata(""), None);
    }

    /// Answer every `main-health` read with one completed `CI` push run.
    fn health_service(
        conclusion: &str,
    ) -> (
        Arc<dyn Fn() -> OctocrabGitHubService + Send + Sync>,
        IssueServiceStub,
    ) {
        let runs = json!({"workflow_runs": [{
            "id": 91,
            "status": "completed",
            "conclusion": conclusion,
            "head_sha": "abc",
            "event": "push",
            "name": "CI",
            "run_attempt": 1,
        }]});
        service([IssueServiceExchange::any_json(
            200,
            serde_json::to_vec(&runs).expect("runs body"),
        )
        .expect("runs response")])
    }

    #[test]
    fn main_health_reports_the_typed_services_verdict() {
        clear_hooks();
        let root = TempDir::new().expect("temp");
        let (github, server) = health_service("success");

        let rows =
            with_test_github_service(github, || main_health_rows(&request(root.path(), false)));

        assert_eq!(rows[0], ("MAIN_CI_STATUS", "pass".to_owned()));
        assert_eq!(rows[2], ("MAIN_HEALTH_HEAD_SHA", "abc".to_owned()));
        assert_eq!(
            fs::read_to_string(root.path().join("main-health.env")).expect("env"),
            "MAIN_CI_STATUS=pass\nMAIN_FAILED_RUN_ID=\nMAIN_HEALTH_HEAD_SHA=abc\nMAIN_HEALTH_DETAIL=run 91 completed successfully\n"
        );
        drop(server);
        clear_hooks();
    }

    #[test]
    fn every_main_health_failure_degrades_to_one_error_row() {
        clear_hooks();
        let root = TempDir::new().expect("temp");
        let subject = request(root.path(), false);

        let (github, server) = health_service("failure");
        let failed = with_test_github_service(github, || read_main_health(&subject));
        assert_eq!(failed[0], ("MAIN_CI_STATUS", "fail".to_owned()));
        assert_eq!(failed[1], ("MAIN_FAILED_RUN_ID", "91".to_owned()));
        drop(server);

        let (refusing, refusing_server) =
            service([
                IssueServiceExchange::any_json(500, b"{}".to_vec()).expect("refusal response")
            ]);
        let refused = with_test_github_service(refusing, || read_main_health(&subject));
        assert_eq!(refused[0], ("MAIN_CI_STATUS", "error".to_owned()));
        assert!(!refused[3].1.is_empty());
        drop(refusing_server);

        let unresolvable = Request {
            repo: "not a repo".to_owned(),
            ..request(root.path(), false)
        };
        assert_eq!(
            read_main_health(&unresolvable)[3],
            (
                "MAIN_HEALTH_DETAIL",
                "main-health probe failed: --repo must be owner/name".to_owned()
            )
        );
        clear_hooks();
    }

    #[test]
    fn an_unwritable_health_file_degrades_the_probe() {
        clear_hooks();
        let root = TempDir::new().expect("temp");
        fs::create_dir(root.path().join("main-health.env")).expect("blocking directory");
        let (github, server) = health_service("success");

        let rows =
            with_test_github_service(github, || main_health_rows(&request(root.path(), false)));

        assert_eq!(rows[0], ("MAIN_CI_STATUS", "error".to_owned()));
        assert!(rows[3].1.contains("cannot write main-health.env"));
        drop(server);
        clear_hooks();
    }

    #[test]
    fn a_health_probe_failure_degrades_to_a_bounded_error_row() {
        let rows = main_health_error(&"detail ".repeat(200));

        assert_eq!(rows[0], ("MAIN_CI_STATUS", "error".to_owned()));
        assert!(rows[3].1.len() <= MAIN_HEALTH_DETAIL_MAX_CHARS);
    }

    #[test]
    fn a_contract_clean_envelope_is_published_in_its_declared_order() {
        let root = TempDir::new().expect("temp");
        let plan = root.path().join("plan-from-issue.txt");
        let issue_json = root.path().join("issue.json");
        fs::write(&plan, VALID_PLAN).expect("plan");
        fs::write(&issue_json, "{}\n").expect("issue json");
        let published = rows(&[
            ("PLAN_PATH", &plan.to_string_lossy()),
            ("ISSUE_JSON_PATH", &issue_json.to_string_lossy()),
        ]);

        assert_eq!(
            emit_success_envelope(&published, &plan, &issue_json),
            ExitCode::SUCCESS
        );
        assert_eq!(envelope_value(&published, "MAIN_CI_STATUS"), "pass");
        assert_eq!(envelope_value(&published, "ABSENT"), "");

        let revalidated = rows(&[
            ("PLAN_PATH", &plan.to_string_lossy()),
            ("ISSUE_JSON_PATH", &issue_json.to_string_lossy()),
            ("PLAN_RECEIPT_SCOPE_REVALIDATION", "true"),
            ("PLAN_RECEIPT_PREVIOUS_BASE_SHA", &"a".repeat(40)),
            ("PLAN_RECEIPT_TARGET_BASE_SHA", &"b".repeat(40)),
        ]);
        assert_eq!(
            emit_success_envelope(&revalidated, &plan, &issue_json),
            ExitCode::SUCCESS
        );
        assert_eq!(
            emit_success_envelope(&rows(&[]), &plan, &issue_json),
            ExitCode::from(2)
        );
    }

    #[test]
    fn the_envelope_self_check_reports_every_broken_rule() {
        let root = TempDir::new().expect("temp");
        let plan = root.path().join("plan-from-issue.txt");
        let issue_json = root.path().join("issue.json");
        fs::write(&plan, VALID_PLAN).expect("plan");
        let readable = |overrides: &[(&str, &str)]| {
            let mut base = vec![
                ("PLAN_PATH", plan.to_string_lossy().into_owned()),
                ("ISSUE_JSON_PATH", issue_json.to_string_lossy().into_owned()),
            ];
            base.extend(
                overrides
                    .iter()
                    .map(|(key, value)| (*key, (*value).to_owned())),
            );
            let pairs: Vec<(&str, &str)> = base
                .iter()
                .map(|(key, value)| (*key, value.as_str()))
                .collect();
            rows(&pairs)
        };

        assert_eq!(
            envelope_error(&readable(&[]), &plan, &issue_json),
            Some("ISSUE_JSON_PATH must be readable".to_owned())
        );
        fs::write(&issue_json, "{}\n").expect("issue json");
        assert_eq!(envelope_error(&readable(&[]), &plan, &issue_json), None);

        let mut duplicated = readable(&[]);
        duplicated.push(("RESUME", "true".to_owned()));
        assert_eq!(
            envelope_error(&duplicated, &plan, &issue_json),
            Some("duplicate key RESUME".to_owned())
        );
        let short: Vec<(&str, String)> = readable(&[])
            .into_iter()
            .filter(|(key, _value)| *key != "DESIGN_DIFFICULTY")
            .collect();
        assert_eq!(
            envelope_error(&short, &plan, &issue_json),
            Some("missing key DESIGN_DIFFICULTY".to_owned())
        );

        for (overrides, expected) in [
            (vec![("BYPASS_COUNT", "")], "BYPASS_COUNT must be numeric"),
            (
                vec![("BYPASS_COUNT", "many")],
                "BYPASS_COUNT must be numeric",
            ),
            (
                vec![("PLAN_RECEIPT_SCOPE_REVALIDATION", "maybe")],
                "PLAN_RECEIPT_SCOPE_REVALIDATION must be true or false",
            ),
            (
                vec![("PLAN_RECEIPT_SCOPE_REVALIDATION", "true")],
                "receipt scope revalidation requires two SHA values",
            ),
            (
                vec![("PLAN_RECEIPT_PREVIOUS_BASE_SHA", "abc")],
                "receipt scope SHA values require revalidation",
            ),
            (
                vec![("MAIN_CI_STATUS", "unknown")],
                "MAIN_CI_STATUS must be pass, fail, pending, error, or skip",
            ),
            (
                vec![("MAIN_HEALTH_DETAIL", "line\nbreak")],
                "MAIN_HEALTH_DETAIL must be single-line",
            ),
        ] {
            assert_eq!(
                envelope_error(&readable(&overrides), &plan, &issue_json),
                Some(expected.to_owned()),
                "{overrides:?}"
            );
        }
        assert_eq!(
            envelope_error(
                &readable(&[]),
                Path::new("/elsewhere/plan.txt"),
                &issue_json
            ),
            Some("PLAN_PATH must match preflight tmpdir".to_owned())
        );
        assert_eq!(
            envelope_error(&readable(&[]), &plan, Path::new("/elsewhere/issue.json")),
            Some("ISSUE_JSON_PATH must match preflight tmpdir".to_owned())
        );
    }

    #[test]
    fn preflight_refuses_an_issue_whose_plan_block_is_absent() {
        clear_hooks();
        let root = TempDir::new().expect("temp");
        declare_plugin_root(&workspace_root());
        install_larch(|_arguments, _environment| {
            Ok(output(0, "ADMISSION_RESULT=pass\nRESUME=false\n", ""))
        });
        let (github, server) = service([IssueServiceExchange::json(
            "GET",
            "/repos/owner/repo/issues/12",
            200,
            serde_json::to_vec(&issue_response(12, "[DESIGNED] Fix", "No plan block."))
                .expect("issue body"),
        )
        .expect("issue response")]);

        let code = with_test_github_service(github, || {
            run(&request(&root.path().join("preflight"), false))
        });

        assert_eq!(code, ExitCode::from(2));
        assert!(root.path().join("preflight").join("issue.json").is_file());
        server.join().expect("one issue read");
        clear_hooks();
    }

    #[test]
    fn a_clean_preflight_publishes_its_whole_success_envelope() {
        clear_hooks();
        let root = TempDir::new().expect("temp");
        let repository = upstream_repository();
        let tmpdir = root.path().join("preflight");
        declare_plugin_root(&workspace_root());
        declare_repo_root(repository.root());
        install_larch(|arguments, _environment| {
            if arguments.starts_with(&["issue".into(), "governance-gate".into()]) {
                Ok(output(0, "SEMANTIC_REASONS=\nREPORT_ONLY_COUNT=0\n", ""))
            } else {
                Ok(output(0, "ADMISSION_RESULT=pass\nRESUME=false\n", ""))
            }
        });
        let plan = VALID_PLAN.replace("Cargo.toml", "tracked.txt");
        let (github, server) = service([
            IssueServiceExchange::json(
                "GET",
                "/repos/owner/repo/issues/12",
                200,
                serde_json::to_vec(&issue_response(
                    12,
                    "[DESIGNED] Fix the gate",
                    &plan_body(&plan),
                ))
                .expect("issue body"),
            )
            .expect("issue response"),
            IssueServiceExchange::any_json(200, br#"{"workflow_runs":[]}"#.to_vec())
                .expect("runs response"),
        ]);

        let code = with_test_github_service(github, || run(&request(&tmpdir, false)));

        assert_eq!(code, ExitCode::SUCCESS);
        assert_eq!(
            fs::read_to_string(tmpdir.join("plan-from-issue.txt")).expect("frozen plan"),
            plan
        );
        assert!(tmpdir.join("main-health.env").is_file());
        server.join().expect("the issue and main-health reads");
        clear_hooks();
    }

    #[test]
    fn a_validated_command_line_reaches_the_preflight_run() {
        clear_hooks();
        let root = TempDir::new().expect("temp");
        declare_plugin_root(root.path());

        assert_eq!(
            preflight(&arguments(&[
                "--issue",
                "12",
                "--repo",
                "owner/repo",
                "--force",
                "--preflight-tmpdir",
                root.path().join("preflight").to_str().expect("utf8"),
            ])),
            ExitCode::from(2)
        );
        clear_hooks();
    }

    #[test]
    fn an_unwritable_tmpdir_refuses_each_artifact_it_cannot_publish() {
        clear_hooks();
        let root = TempDir::new().expect("temp");
        let blocker = root.path().join("blocker");
        fs::write(&blocker, "").expect("blocker");
        let subject = request(&blocker.join("nested"), false);
        let repository = upstream_repository();
        let (github, server) = service([IssueServiceExchange::json(
            "GET",
            "/repos/owner/repo/issues/12",
            200,
            serde_json::to_vec(&issue_response(12, "Title", "Body.")).expect("issue body"),
        )
        .expect("issue response")]);

        let refused = with_test_github_service(github, || {
            materialize_issue(&subject, &blocker.join("nested").join("issue.json"))
        })
        .refusal();

        assert_eq!(refused, ExitCode::from(2));
        assert_eq!(
            governance(&subject, "body", repository.root()).refusal(),
            ExitCode::from(2)
        );
        server.join().expect("one issue read");
        clear_hooks();
    }

    #[test]
    fn a_child_without_a_declared_repository_omits_the_repo_pair() {
        clear_hooks();
        let root = TempDir::new().expect("temp");
        let subject = Request {
            issue: "12".to_owned(),
            repo: String::new(),
            force: false,
            tmpdir: root.path().to_path_buf(),
        };
        install_larch(|arguments, _environment| {
            assert!(!arguments.contains(&OsString::from("--repo")));
            Ok(output(0, "BLOCK_PRESENT=true\n", ""))
        });

        read_plan_block(&subject, &[], &root.path().join("plan-from-issue.txt")).expect("read");
        assert!(subject.repo_arguments().is_empty());
        clear_hooks();
    }

    fn rows(overrides: &[(&str, &str)]) -> Vec<(&'static str, String)> {
        let mut rows: Vec<(&'static str, String)> = super::SUCCESS_ENVELOPE_KEYS
            .iter()
            .map(|key| {
                let value = match *key {
                    "RESUME" | "BLOCK_PRESENT" => "true",
                    "PLAN_RECEIPT_SCOPE_REVALIDATION" => "false",
                    "BYPASS_COUNT" => "0",
                    "MAIN_CI_STATUS" => "pass",
                    _other => "",
                };
                (*key, value.to_owned())
            })
            .collect();
        for (key, value) in overrides {
            if let Some(row) = rows.iter_mut().find(|(name, _value)| name == key) {
                row.1 = (*value).to_owned();
            }
        }
        rows
    }

    #[test]
    fn the_envelope_self_check_reports_the_first_broken_rule() {
        let plan = Path::new("/nonexistent-preflight/plan-from-issue.txt");
        let issue_json = Path::new("/nonexistent-preflight/issue.json");

        assert_eq!(
            envelope_error(&rows(&[("RESUME", "yes")]), plan, issue_json),
            Some("RESUME must be true or false".to_owned())
        );
        assert_eq!(
            envelope_error(&rows(&[("TITLE", "a\nb")]), plan, issue_json),
            Some("TITLE must be single-line".to_owned())
        );
        assert_eq!(
            envelope_error(&rows(&[]), plan, issue_json),
            Some("PLAN_PATH must match preflight tmpdir".to_owned())
        );
        assert_eq!(
            envelope_error(
                &rows(&[
                    ("PLAN_PATH", "/nonexistent-preflight/plan-from-issue.txt"),
                    ("ISSUE_JSON_PATH", "/nonexistent-preflight/issue.json"),
                    ("PLAN_RECEIPT_SCOPE_REVALIDATION", "true"),
                ]),
                plan,
                issue_json
            ),
            Some("PLAN_PATH must be readable".to_owned())
        );
    }

    #[test]
    fn a_receipt_scope_requires_two_shas_or_neither() {
        assert!(sha1_hex(&"a".repeat(40)));
        assert!(!sha1_hex(&"A".repeat(40)));
        assert!(!sha1_hex("abc"));
    }
}
