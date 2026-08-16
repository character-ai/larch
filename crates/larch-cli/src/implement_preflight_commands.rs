//! The `/implement` Preflight gate: admission, plan extraction, and health.
//!
//! Preflight only sequences commands that already own their policy. `admission
//! gate` decides admission, `plan-block read` and the shared plan grammar decide
//! the executable-plan contract, the still-Python `issue governance-gate`
//! decides migration governance, and the still-Python `ci main-health` decides
//! main's CI health. This module adds no policy of its own; it publishes one
//! self-validated machine envelope for the skill to parse.
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
    time::Duration,
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
    implement_commands::{kv_value, read_kv_first, write_atomic},
    python_verb::{publish_session_environment, run_python_verb},
    runtime_entrypoint::{plugin_root, run_verified_larch_with_environment},
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
/// Deadline for each still-Python sibling Preflight composes.
const PYTHON_SIBLING_TIMEOUT: Duration = Duration::from_secs(120);

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
    if !plugin_root().is_ok_and(|root| root.join("python").join("cli.py").is_file()) {
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

/// Consume the still-Python migration-governance verdict for this issue.
///
/// `issue governance-gate --preflight-envelope` keeps blocker, receipt, and
/// active-owner policy with its single Python owner; this reads that envelope
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
    let Ok(output) = run_python_verb(argv, PYTHON_SIBLING_TIMEOUT) else {
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
    // `ci main-health` remains Python-owned, so its status policy has one owner.
    let output = run_python_verb(
        [
            OsString::from("ci"),
            OsString::from("main-health"),
            OsString::from("--repo"),
            OsString::from(repo),
            OsString::from("--base-ref"),
            OsString::from("main"),
        ],
        PYTHON_SIBLING_TIMEOUT,
    );
    let Ok(output) = output else {
        return main_health_error("main-health probe failed: cannot start ci main-health");
    };
    let stdout = String::from_utf8_lossy(output.stdout()).into_owned();
    if !output.status().success() {
        let detail = String::from_utf8_lossy(output.stderr()).into_owned();
        let detail = if detail.trim().is_empty() {
            output.status().code().unwrap_or(1).to_string()
        } else {
            detail
        };
        return main_health_error(&format!("main-health probe failed: {detail}"));
    }
    if !MAIN_HEALTH_KEYS.iter().all(|key| {
        stdout
            .lines()
            .any(|line| line.starts_with(&format!("{key}=")))
    }) {
        return main_health_error("main-health probe omitted required keys");
    }
    MAIN_HEALTH_KEYS
        .iter()
        .map(|key| (*key, single_line(&kv_value(&stdout, key))))
        .collect()
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
    let result = run_verified_larch_with_environment(arguments, environment);
    let (code, stdout, stderr) = match &result {
        Ok(output) => (
            output.status().code().unwrap_or(1),
            String::from_utf8_lossy(output.stdout()).into_owned(),
            String::from_utf8_lossy(output.stderr()).into_owned(),
        ),
        Err(detail) => (1, String::new(), format!("{detail}\n")),
    };
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

/// Assemble the still-Python `issue governance-gate` command line.
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
        MAIN_HEALTH_DETAIL_MAX_CHARS, envelope_error, main_health_error,
        malformed_terminal_metadata, sha1_hex,
    };
    use std::path::Path;

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

    #[test]
    fn only_a_recognized_prefix_above_diff_lines_reads_as_malformed() {
        let malformed = "### NEW: a\ndifficulty: NOPE!!\ndiff_lines: 10\n";

        assert_eq!(
            malformed_terminal_metadata(malformed),
            Some("difficulty: NOPE!!".to_owned())
        );
        assert_eq!(
            malformed_terminal_metadata("### NEW: a\ndifficulty: TRIVIAL\ndiff_lines: 10\n"),
            None
        );
        assert_eq!(malformed_terminal_metadata("### NEW: a\n"), None);
    }

    #[test]
    fn a_health_probe_failure_degrades_to_a_bounded_error_row() {
        let rows = main_health_error(&"detail ".repeat(200));

        assert_eq!(rows[0], ("MAIN_CI_STATUS", "error".to_owned()));
        assert!(rows[3].1.len() <= MAIN_HEALTH_DETAIL_MAX_CHARS);
    }
}
