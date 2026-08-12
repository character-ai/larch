//! Read-only `issue migration-audit` compatibility command.
//!
//! The report and governance policy live in `larch-core`; this module is the
//! sole effect adapter. It gathers one bounded GitHub/Git snapshot, runs the
//! canonical in-process lint owners, and preserves the legacy Python command's
//! JSON, table, and exit-code contract.

use std::{
    collections::{BTreeMap, BTreeSet},
    env,
    ffi::OsString,
    fs,
    io::{self, Write as _},
    path::{Path, PathBuf},
    process::ExitCode,
    time::Duration,
};

use chrono::Utc;
use larch_adapters::{
    GixRepository, PathIntent, TemporaryRoot, assert_no_symlink_path_or_ancestors,
    atomic_write_utf8, github::OctocrabGitHubService, runtime::Cancellation,
};
use larch_core::{
    CommandAuditIssue, DependencySnapshot, GitHubIssue, GitHubIssueList, GitHubIssueListMode,
    GitHubIssueState, GitHubRepositoryRef, GitHubService, GitHubTransportPolicy, GitPath,
    MigrationAuditRequest, MigrationAuditSnapshot, MigrationIssueSnapshot, PlanAuditEvidence,
    RepositoryAuditFinding, RepositoryFindingSource, RepositoryRead, Revision, SafeText, ScopeFile,
    ScopeSnapshot, build_command_audit_issue, build_migration_audit_report, declared_scope_paths,
    issue_plan_marker_defect, parse_named_block, parse_native_blocker_refs, parse_owner_block,
    parse_receipt, python_int, render_command_audit_input, render_migration_audit_json,
    render_migration_audit_table, validate_plan_facets,
};
use regex::Regex;
use std::sync::LazyLock;

use crate::{
    argparse_compat::{
        ParsedCommandLine, missing, parse, resolve_option, split_inline_option, usage_error,
    },
    github_repository_resolution::repository_ref,
    github_service::{ServiceFailure, with_github_service_policy},
};

const USAGE: &str = "usage: larch issue migration-audit [-h] --repo REPO --chief CHIEF\n                                   [--output OUTPUT]\n                                   [--table-output {stderr,stdout,none}]";
const PROGRAM: &str = "larch issue migration-audit";
const HELP: &str = "usage: larch issue migration-audit [-h] --repo REPO --chief CHIEF\n                                   [--output OUTPUT]\n                                   [--table-output {stderr,stdout,none}]\n\noptions:\n  -h, --help            show this help message and exit\n  --repo REPO\n  --chief CHIEF\n  --output OUTPUT\n  --table-output {stderr,stdout,none}";
const MAX_SCOPE_FILES: usize = 20_000;

static REPOSITORY_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$").expect("repository expression is valid")
});
static LEAF_TITLE_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"\[leaf of [#]?[1-9][0-9]*\]").expect("leaf title expression is valid")
});
static CHIEF_DIRECT_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"chief[ \t]+umbrella:[ \t]*#([1-9][0-9]*)")
        .expect("chief direct expression is valid")
});
static CHIEF_REVERSED_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"#([1-9][0-9]*)[ \t]+chief[ \t]+umbrella")
        .expect("chief reversed expression is valid")
});
static PLAN_HEADING_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"^(?:##|###)[ \t]+(?P<kind>NEW|UPDATED|REWRITTEN|MAY_UPDATE)(?:[ \t]*:[ \t]*(?P<colon>.+?)|[ \t]+\[(?P<bracket>[^]\r\n]+)\][ \t]*:?)[ \t]*$",
    )
    .expect("plan heading expression is valid")
});

#[derive(Debug)]
struct Arguments {
    repository: String,
    chief_issue: u64,
    output: Option<PathBuf>,
    table_output: TableOutput,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum TableOutput {
    Stderr,
    Stdout,
    None,
}

impl TableOutput {
    fn parse(value: &str) -> Option<Self> {
        match value {
            "stderr" => Some(Self::Stderr),
            "stdout" => Some(Self::Stdout),
            "none" => Some(Self::None),
            _ => None,
        }
    }
}

#[derive(Debug)]
struct RemoteSnapshot {
    open_issues: Vec<MigrationIssueSnapshot>,
    closed_issues: Vec<MigrationIssueSnapshot>,
    referenced_issues: Vec<MigrationIssueSnapshot>,
    dependencies: Vec<DependencySnapshot>,
    open_pr_branches: Vec<String>,
}

/// Run the migration audit. Clean reports exit `0`, reports with findings exit
/// `1`, and unavailable or malformed evidence exits `2`.
pub fn run(arguments: &[OsString]) -> ExitCode {
    let arguments = match parse_arguments(arguments) {
        Ok(Some(arguments)) => arguments,
        Ok(None) => return ExitCode::SUCCESS,
        Err(()) => return ExitCode::from(2),
    };
    match run_audit(&arguments) {
        Ok(has_findings) => ExitCode::from(u8::from(has_findings)),
        Err(error) => {
            eprintln!("ERROR: migration-audit: {}", diagnostic_detail(&error));
            ExitCode::from(2)
        }
    }
}

fn diagnostic_detail(error: &str) -> String {
    SafeText::diagnostic(error)
        .as_str()
        .chars()
        .take(500)
        .collect()
}

fn parse_arguments(arguments: &[OsString]) -> Result<Option<Arguments>, ()> {
    if handle_help(arguments)? {
        return Ok(None);
    }
    let parsed = parse(
        arguments,
        &["--repo", "--chief", "--output", "--table-output"],
        0,
    );
    if let Some(error) = parsed.value_error() {
        let _ = usage_error(USAGE, PROGRAM, error, 2);
        return Err(());
    }
    validate_option_values(&parsed)?;
    let repo = parsed.value("--repo");
    let chief = parsed.value("--chief");
    if repo.is_none() || chief.is_none() {
        let _ = usage_error(
            USAGE,
            PROGRAM,
            &missing(&[("--repo", repo.is_some()), ("--chief", chief.is_some())]),
            2,
        );
        return Err(());
    }
    if let Some(error) = parsed.error() {
        let _ = usage_error(USAGE, PROGRAM, &error, 2);
        return Err(());
    }
    let repository = repo
        .expect("required option was checked")
        .to_string_lossy()
        .into_owned();
    let chief_issue = chief
        .expect("required option was checked")
        .to_string_lossy();
    let chief_issue = python_int(&chief_issue).expect("validated integer option");
    if !REPOSITORY_RE.is_match(&repository) {
        eprintln!("ERROR: migration-audit: --repo must be exactly owner/name");
        return Err(());
    }
    if chief_issue <= 0 {
        eprintln!("ERROR: migration-audit: --chief must be a positive issue number");
        return Err(());
    }
    let output = parsed.value("--output").map(PathBuf::from);
    let table_output = parsed
        .value("--table-output")
        .map_or(TableOutput::Stderr, |value| {
            TableOutput::parse(&value.to_string_lossy()).expect("validated choice")
        });
    if output.is_none() && table_output == TableOutput::Stdout {
        eprintln!(
            "ERROR: migration-audit: --table-output stdout requires --output so stdout stays machine-readable"
        );
        return Err(());
    }
    Ok(Some(Arguments {
        repository,
        chief_issue: u64::try_from(chief_issue).expect("positive chief issue fits u64"),
        output,
        table_output,
    }))
}

fn handle_help(arguments: &[OsString]) -> Result<bool, ()> {
    for argument in arguments {
        let text = argument.to_string_lossy();
        if text == "-h" {
            println!("{HELP}");
            return Ok(true);
        }
        let (name, inline) = split_inline_option(&text);
        if name == "-h" || resolve_option(name, &["--help"]).is_some() {
            if let Some(value) = inline {
                let _ = usage_error(
                    USAGE,
                    PROGRAM,
                    &format!("argument -h/--help: ignored explicit argument '{value}'"),
                    2,
                );
                return Err(());
            }
            println!("{HELP}");
            return Ok(true);
        }
    }
    Ok(false)
}

fn validate_option_values(parsed: &ParsedCommandLine) -> Result<(), ()> {
    for (name, value) in parsed.entries() {
        let value = value.to_string_lossy();
        if *name == "--chief" && python_int(&value).is_none() {
            let _ = usage_error(
                USAGE,
                PROGRAM,
                &format!("argument --chief: invalid int value: '{value}'"),
                2,
            );
            return Err(());
        }
        if *name == "--table-output" && TableOutput::parse(&value).is_none() {
            let _ = usage_error(
                USAGE,
                PROGRAM,
                &format!(
                    "argument --table-output: invalid choice: '{value}' (choose from 'stderr', 'stdout', 'none')"
                ),
                2,
            );
            return Err(());
        }
    }
    Ok(())
}

fn run_audit(arguments: &Arguments) -> Result<bool, String> {
    let current_dir = env::current_dir().map_err(|_| "repository root unavailable".to_owned())?;
    let repository = GixRepository::discover(&current_dir)
        .map_err(|_| "repository root unavailable".to_owned())?;
    let repo_root = worktree_root(&repository)?;
    let head = repository
        .resolve_revision(&Revision::new("HEAD"))
        .map_err(|_| "repository snapshot unavailable".to_owned())?;
    let head_sha = head.to_hex();
    if head_sha.len() != 40 {
        return Err("repository snapshot has invalid HEAD".to_owned());
    }
    let tracked_paths = tracked_paths(&repository)?;
    let github_repository = repository_ref(&arguments.repository)
        .map_err(|()| "--repo must be exactly owner/name".to_owned())?;
    let timestamp = Utc::now().format("%Y-%m-%dT%H:%M:%SZ").to_string();
    let transport_policy = GitHubTransportPolicy::migration_audit();
    let remote = with_github_service_policy(transport_policy, async |service, cancellation| {
        collect_remote_snapshot_with_deadline(
            service,
            cancellation,
            &github_repository,
            arguments.chief_issue,
            transport_policy.overall_timeout(),
        )
        .await
    })
    .map_err(ServiceFailure::into_detail)?;
    let snapshot = MigrationAuditSnapshot {
        repository: arguments.repository.clone(),
        chief_issue: arguments.chief_issue,
        snapshot_timestamp: timestamp,
        head_sha: head_sha.clone(),
        open_issues: remote.open_issues,
        referenced_issues: remote.referenced_issues,
        dependencies: remote.dependencies,
        open_pr_branches: remote.open_pr_branches,
        closed_issues: remote.closed_issues,
    };
    let plans = collect_plan_evidence(&snapshot, &repo_root, &repository, &tracked_paths, &head)?;
    let repository_findings = collect_repository_findings(&repo_root, &snapshot)?;
    let report = build_migration_audit_report(&MigrationAuditRequest {
        snapshot,
        plans,
        repository_findings,
    })
    .map_err(|error| error.to_string())?;
    let current_head = repository
        .resolve_revision(&Revision::new("HEAD"))
        .map_err(|_| "repository changed during audit".to_owned())?;
    if current_head.to_hex() != head_sha {
        return Err("repository changed during audit".to_owned());
    }
    let json = render_migration_audit_json(&report);
    if let Some(output) = &arguments.output {
        write_output(output, &json)?;
    } else {
        write_stdout(&json)?;
    }
    let table = render_migration_audit_table(&report);
    match arguments.table_output {
        TableOutput::Stderr => write_stderr(&table)?,
        TableOutput::Stdout => write_stdout(&table)?,
        TableOutput::None => {}
    }
    Ok(!report.findings.is_empty())
}

async fn collect_remote_snapshot(
    service: &OctocrabGitHubService,
    cancellation: &Cancellation,
    repository: &GitHubRepositoryRef,
    chief_issue: u64,
) -> Result<RemoteSnapshot, String> {
    let listed = service
        .list_issues(
            &GitHubIssueList {
                repo: repository.clone(),
                state: GitHubIssueState::All,
                labels: Vec::new(),
                limit: service.transport_policy().limits().items(),
                mode: GitHubIssueListMode::Exhaustive,
            },
            cancellation,
        )
        .await
        .map_err(|_| "issue snapshot unavailable".to_owned())?;
    let mut all = BTreeMap::new();
    for issue in listed.issues {
        let issue = migration_issue(&issue, "issue snapshot")?;
        if all.insert(issue.number, issue).is_some() {
            return Err("issue snapshot contains duplicates".to_owned());
        }
    }
    let open_issues = all
        .values()
        .filter(|issue| issue.state == "open")
        .cloned()
        .collect::<Vec<_>>();
    let closed_issues = all
        .values()
        .filter(|issue| issue.state == "closed")
        .cloned()
        .collect::<Vec<_>>();
    let mut dependencies = Vec::new();
    let mut references = BTreeSet::new();
    for leaf in open_issues
        .iter()
        .filter(|issue| executable_leaf(issue, chief_issue))
    {
        let blockers = service
            .list_blocked_by(
                cancellation,
                repository.owner(),
                repository.name(),
                leaf.number,
            )
            .await
            .map_err(|_| format!("issue #{}: blocked-by read failed", leaf.number))?;
        let mut blocker_numbers = BTreeSet::new();
        for blocker in blockers {
            let number = blocker.issue_number();
            if number == 0 || !blocker_numbers.insert(number) {
                return Err(format!("issue #{}: blocked-by row is invalid", leaf.number));
            }
        }
        references.extend(blocker_numbers.iter().copied());
        references.extend(parse_native_blocker_refs(&leaf.body));
        references.extend(reuse_source_refs(&leaf.body));
        dependencies.push(DependencySnapshot {
            issue: leaf.number,
            blockers: blocker_numbers.into_iter().collect(),
        });
    }
    let mut referenced_issues = Vec::new();
    for number in references {
        if all.contains_key(&number) {
            continue;
        }
        let issue = service
            .issue(repository, number, cancellation)
            .await
            .map_err(|_| format!("issue #{number}: required evidence unavailable"))?;
        referenced_issues.push(migration_issue(&issue, &format!("issue #{number}"))?);
    }
    let mut open_pr_branches = service
        .list_release_open_pull_requests(cancellation, repository.owner(), repository.name())
        .await
        .map_err(|_| "open pull request snapshot unavailable".to_owned())?
        .into_iter()
        .map(|pull_request| pull_request.head_ref)
        .collect::<BTreeSet<_>>();
    if open_pr_branches.iter().any(String::is_empty) {
        return Err("open pull request snapshot unavailable".to_owned());
    }
    dependencies.sort_by_key(|row| row.issue);
    referenced_issues.sort_by_key(|issue| issue.number);
    Ok(RemoteSnapshot {
        open_issues,
        closed_issues,
        referenced_issues,
        dependencies,
        open_pr_branches: std::mem::take(&mut open_pr_branches).into_iter().collect(),
    })
}

async fn collect_remote_snapshot_with_deadline(
    service: &OctocrabGitHubService,
    cancellation: &Cancellation,
    repository: &GitHubRepositoryRef,
    chief_issue: u64,
    deadline: Duration,
) -> Result<RemoteSnapshot, String> {
    tokio::time::timeout(
        deadline,
        collect_remote_snapshot(service, cancellation, repository, chief_issue),
    )
    .await
    .unwrap_or_else(|_| {
        cancellation.cancel();
        Err("issue snapshot unavailable".to_owned())
    })
}

fn migration_issue(issue: &GitHubIssue, context: &str) -> Result<MigrationIssueSnapshot, String> {
    if issue.number == 0 || issue.is_pull_request {
        return Err(format!("{context}: issue row is invalid"));
    }
    let state = match issue.state {
        GitHubIssueState::Open => "open",
        GitHubIssueState::Closed => "closed",
        GitHubIssueState::All => return Err(format!("{context}: issue row has invalid state")),
    };
    if issue.updated_at.is_empty() {
        return Err(format!("{context}: issue row omitted required fields"));
    }
    Ok(MigrationIssueSnapshot {
        number: issue.number,
        title: issue.title.clone(),
        state: state.to_owned(),
        body: issue.body.clone(),
        updated_at: issue.updated_at.clone(),
    })
}

fn collect_plan_evidence(
    snapshot: &MigrationAuditSnapshot,
    repo_root: &Path,
    repository: &GixRepository,
    tracked_paths: &[String],
    head: &larch_core::ObjectId,
) -> Result<Vec<PlanAuditEvidence>, String> {
    snapshot
        .open_issues
        .iter()
        .filter(|issue| executable_leaf(issue, snapshot.chief_issue))
        .map(|issue| {
            let plan = parse_named_block(&issue.body, larch_core::PLAN_MARKER)
                .ok()
                .flatten();
            let defects = plan.as_deref().map_or_else(
                || {
                    vec![
                        issue_plan_marker_defect(&issue.body)
                            .unwrap_or("missing-plan-block")
                            .to_owned(),
                    ]
                },
                |plan| validate_plan(repo_root, plan, tracked_paths),
            );
            let (base_scope, head_scope) = plan
                .as_deref()
                .and_then(|plan| receipt_scopes(&issue.body, plan, repository, head).ok())
                .unwrap_or((None, None));
            Ok(PlanAuditEvidence {
                issue: issue.number,
                defects,
                base_scope,
                head_scope,
            })
        })
        .collect()
}

fn receipt_scopes(
    body: &str,
    plan: &str,
    repository: &GixRepository,
    head: &larch_core::ObjectId,
) -> Result<(Option<ScopeSnapshot>, Option<ScopeSnapshot>), String> {
    let Some(receipt) = parse_receipt(body) else {
        return Ok((None, None));
    };
    let base = repository
        .resolve_revision(&Revision::new(receipt.base_sha.as_bytes()))
        .map_err(|_| "base scope unavailable".to_owned())?;
    if base.to_hex().len() != 40 {
        return Ok((None, None));
    }
    Ok((
        Some(scope_snapshot(repository, &base, plan)?),
        Some(scope_snapshot(repository, head, plan)?),
    ))
}

fn scope_snapshot(
    repository: &GixRepository,
    revision: &larch_core::ObjectId,
    plan: &str,
) -> Result<ScopeSnapshot, String> {
    let files = repository
        .files_at_commit(revision, MAX_SCOPE_FILES)
        .map_err(|_| "base scope unavailable".to_owned())?;
    let tracked = files
        .iter()
        .map(git_path_string)
        .collect::<Result<Vec<_>, _>>()?;
    let files = declared_scope_paths(plan, &tracked)
        .into_iter()
        .map(|path| {
            let object_id = repository
                .blob_id_at_commit(revision, &GitPath::new(path.as_bytes()))
                .map_err(|_| "base scope unavailable".to_owned())?
                .map_or_else(|| "MISSING".to_owned(), |object| object.to_hex());
            Ok(ScopeFile { path, object_id })
        })
        .collect::<Result<Vec<_>, String>>()?;
    Ok(ScopeSnapshot {
        sha: revision.to_hex(),
        files,
    })
}

fn collect_repository_findings(
    repo_root: &Path,
    snapshot: &MigrationAuditSnapshot,
) -> Result<Vec<RepositoryAuditFinding>, String> {
    let repository = larch_lint::Repository::discover(&larch_lint::GitCli, repo_root)
        .map_err(|_| "command registry evidence unavailable".to_owned())?;
    let registry_findings = lint_rule_findings(&repository, "command-registry")?;
    let runtime_findings = lint_rule_findings(&repository, "production-cargo-run")?;
    let selectors = larch_lint::command_audit_selectors(&repository)
        .map_err(|_| "command registry evidence unavailable".to_owned())?;
    let rows = snapshot
        .open_issues
        .iter()
        .chain(&snapshot.referenced_issues)
        .map(|issue| {
            build_command_audit_issue(
                issue,
                executable_leaf(issue, snapshot.chief_issue),
                &selectors,
            )
            .map_err(|error| error.to_string())
        })
        .collect::<Result<Vec<CommandAuditIssue>, _>>()?;
    let input = render_command_audit_input(&rows, true).map_err(|error| error.to_string())?;
    let issue_findings = larch_lint::audit_migration_issue_commands_content(&repository, &input)
        .map_err(|error| format!("migration-issue command audit: {error}"))?
        .findings()
        .iter()
        .map(ToString::to_string)
        .collect::<Vec<_>>();
    let mut findings = registry_findings
        .into_iter()
        .chain(issue_findings)
        .map(|reason| {
            Ok(RepositoryAuditFinding {
                source: RepositoryFindingSource::CommandRegistry,
                reason: safe_finding(&reason)?,
            })
        })
        .collect::<Result<Vec<_>, String>>()?;
    findings.extend(
        runtime_findings
            .into_iter()
            .map(|reason| {
                Ok(RepositoryAuditFinding {
                    source: RepositoryFindingSource::ProductionRuntime,
                    reason: safe_finding(&reason)?,
                })
            })
            .collect::<Result<Vec<_>, String>>()?,
    );
    Ok(findings)
}

fn lint_rule_findings(
    repository: &larch_lint::Repository,
    name: &str,
) -> Result<Vec<String>, String> {
    let rules = larch_lint::registered_rule_registry()
        .map_err(|_| format!("{name} audit: required evidence failed"))?;
    larch_lint::validate_migration_ledger(repository, &rules)
        .map_err(|_| format!("{name} audit: required evidence failed"))?;
    let rule = rules
        .get(name)
        .ok_or_else(|| format!("{name} audit: required evidence failed"))?;
    larch_lint::run(repository, [rule])
        .map_err(|_| format!("{name} audit: required evidence failed"))
        .map(|report| report.findings().iter().map(ToString::to_string).collect())
}

fn safe_finding(finding: &str) -> Result<String, String> {
    let safe = SafeText::diagnostic(finding).to_string();
    if safe.contains("[content truncated") {
        Err("repository audit: evidence redaction failed".to_owned())
    } else if safe.is_empty() {
        Err("repository audit: finding exit omitted findings".to_owned())
    } else {
        Ok(safe)
    }
}

fn validate_plan(repo_root: &Path, plan: &str, tracked_paths: &[String]) -> Vec<String> {
    let mut defects = validate_plan_facets(plan)
        .into_iter()
        .collect::<BTreeSet<_>>();
    defects.extend(plan_path_defects(repo_root, plan, tracked_paths));
    larch_core::PLAN_DEFECT_TOKENS
        .iter()
        .filter(|token| defects.contains(**token))
        .map(|token| (*token).to_owned())
        .collect()
}

fn plan_path_defects(repo_root: &Path, plan: &str, tracked_paths: &[String]) -> BTreeSet<String> {
    let mut defects = BTreeSet::new();
    let lines = plan
        .split('\n')
        .map(|line| line.trim_end_matches('\r'))
        .collect::<Vec<_>>();
    let fenced = larch_core::balanced_fence_line_indices(&lines);
    let tracked = tracked_paths.iter().cloned().collect::<BTreeSet<_>>();
    for (index, line) in lines.iter().enumerate() {
        if fenced.contains(&index) {
            continue;
        }
        let Some(captures) = PLAN_HEADING_RE.captures(line) else {
            continue;
        };
        let raw_path = captures
            .name("colon")
            .or_else(|| captures.name("bracket"))
            .map_or("", |capture| capture.as_str());
        let path = heading_path_token(raw_path);
        if unsafe_plan_path(&path) {
            let _ = defects.insert("unsafe-plan-path".to_owned());
            continue;
        }
        let leaf = repo_root.join(&path);
        if unsafe_filesystem_path(repo_root, &leaf, &path) {
            let _ = defects.insert("unsafe-plan-path".to_owned());
            continue;
        }
        let kind = captures.name("kind").map_or("", |capture| capture.as_str());
        if kind == "NEW" {
            if tracked.contains(&path) || leaf.exists() {
                let _ = defects.insert("existing-new-plan-path".to_owned());
            }
        } else if is_glob(&path) {
            let synthetic = format!("## UPDATED: {path}");
            if declared_scope_paths(&synthetic, tracked_paths).is_empty() {
                let _ = defects.insert("empty-plan-glob".to_owned());
            }
        } else if !tracked.contains(&path) {
            let _ = defects.insert("missing-updated-plan-path".to_owned());
        }
    }
    defects
}

fn heading_path_token(raw: &str) -> String {
    let raw = raw.trim();
    if let Some(start) = raw.find('`')
        && let Some(end) = raw[start + 1..].find('`')
    {
        return raw[start + 1..start + 1 + end].trim().to_owned();
    }
    raw.split_whitespace()
        .next()
        .unwrap_or_default()
        .split('(')
        .next()
        .unwrap_or_default()
        .trim()
        .to_owned()
}

fn unsafe_plan_path(path: &str) -> bool {
    path.is_empty()
        || path.trim() != path
        || path.starts_with('~')
        || Path::new(path).is_absolute()
        || Path::new(path)
            .components()
            .any(|part| matches!(part, std::path::Component::ParentDir))
}

fn is_glob(path: &str) -> bool {
    path.contains(['*', '?', '['])
}

fn unsafe_filesystem_path(root: &Path, leaf: &Path, path: &str) -> bool {
    if fs::symlink_metadata(leaf).is_ok_and(|metadata| metadata.file_type().is_symlink())
        && !path_inside(root, leaf)
    {
        return true;
    }
    let parts = Path::new(path).components().collect::<Vec<_>>();
    let mut current = root.to_path_buf();
    for part in &parts[..parts.len().saturating_sub(1)] {
        current.push(part.as_os_str());
        match fs::symlink_metadata(&current) {
            Ok(metadata) if metadata.file_type().is_symlink() || !metadata.is_dir() => return true,
            Ok(_) => {}
            Err(error) if error.kind() == io::ErrorKind::NotFound => return false,
            Err(_) => return true,
        }
        if !path_inside(root, &current) {
            return true;
        }
    }
    false
}

fn path_inside(root: &Path, candidate: &Path) -> bool {
    candidate
        .canonicalize()
        .is_ok_and(|candidate| candidate == root || candidate.starts_with(root))
}

fn executable_leaf(issue: &MigrationIssueSnapshot, chief_issue: u64) -> bool {
    if issue.state != "open" || !LEAF_TITLE_RE.is_match(&issue.title.to_ascii_lowercase()) {
        return false;
    }
    let body = issue.body.to_ascii_lowercase();
    [&*CHIEF_DIRECT_RE, &*CHIEF_REVERSED_RE]
        .iter()
        .any(|expression| {
            expression.captures_iter(&body).any(|captures| {
                captures
                    .get(1)
                    .and_then(|capture| capture.as_str().parse::<u64>().ok())
                    == Some(chief_issue)
            })
        })
}

fn reuse_source_refs(body: &str) -> BTreeSet<u64> {
    parse_owner_block(body)
        .raw_rows
        .into_iter()
        .filter_map(|row| {
            let parts = row.split('\t').collect::<Vec<_>>();
            (parts.len() == 4 && parts[0] == "REUSE")
                .then(|| parts[2].strip_prefix('#'))
                .flatten()
                .and_then(|number| number.parse().ok())
        })
        .collect()
}

fn worktree_root(repository: &GixRepository) -> Result<PathBuf, String> {
    let location = repository.location();
    let worktree = location
        .work_dir
        .ok_or_else(|| "repository root unavailable".to_owned())?;
    let path = std::str::from_utf8(worktree.as_bytes())
        .map_err(|_| "repository root unavailable".to_owned())?;
    fs::canonicalize(path).map_err(|_| "repository root unavailable".to_owned())
}

fn tracked_paths(repository: &GixRepository) -> Result<Vec<String>, String> {
    repository
        .tracked_paths()
        .map_err(|_| "repository snapshot unavailable".to_owned())?
        .iter()
        .map(git_path_string)
        .collect()
}

fn git_path_string(path: &GitPath) -> Result<String, String> {
    std::str::from_utf8(path.as_bytes())
        .map(str::to_owned)
        .map_err(|_| "repository snapshot unavailable".to_owned())
}

fn write_output(path: &Path, text: &str) -> Result<(), String> {
    let absolute = if path.is_absolute() {
        path.to_path_buf()
    } else {
        env::current_dir()
            .map_err(|_| "cannot write migration audit output".to_owned())?
            .join(path)
    };
    assert_no_symlink_path_or_ancestors(&absolute)
        .map_err(|_| "cannot write migration audit output".to_owned())?;
    let (Some(parent), Some(name)) = (absolute.parent(), absolute.file_name()) else {
        return Err("cannot write migration audit output".to_owned());
    };
    let root = output_root(parent)?;
    let output = root
        .confine(name, PathIntent::Write)
        .map_err(|_| "cannot write migration audit output".to_owned())?;
    atomic_write_utf8(&output, text, 0o600)
        .map_err(|_| "cannot write migration audit output".to_owned())
}

/// Bind a caller-selected report parent without weakening the legacy no-follow
/// output contract. macOS exposes `/tmp` as a root-owned platform alias, which
/// the Python command accepted; canonicalize only that trusted alias before
/// applying the normal temporary-root confinement.
fn output_root(parent: &Path) -> Result<TemporaryRoot, String> {
    let metadata = fs::symlink_metadata(parent)
        .map_err(|_| "cannot write migration audit output".to_owned())?;
    let root_parent = if metadata.file_type().is_symlink() {
        if !root_owned_platform_alias(&metadata) {
            return Err("cannot write migration audit output".to_owned());
        }
        fs::canonicalize(parent).map_err(|_| "cannot write migration audit output".to_owned())?
    } else {
        parent.to_path_buf()
    };
    TemporaryRoot::resolve(Some(&root_parent))
        .map_err(|_| "cannot write migration audit output".to_owned())
}

#[cfg(unix)]
fn root_owned_platform_alias(metadata: &fs::Metadata) -> bool {
    use std::os::unix::fs::MetadataExt as _;

    metadata.uid() == 0
}

#[cfg(not(unix))]
fn root_owned_platform_alias(_metadata: &fs::Metadata) -> bool {
    false
}

fn write_stdout(text: &str) -> Result<(), String> {
    io::stdout()
        .lock()
        .write_all(text.as_bytes())
        .map_err(|_| "cannot write migration audit output".to_owned())
}

fn write_stderr(text: &str) -> Result<(), String> {
    io::stderr()
        .lock()
        .write_all(text.as_bytes())
        .map_err(|_| "cannot write migration audit output".to_owned())
}

#[cfg(test)]
mod tests {
    use std::{fs, sync::Arc, time::Duration};

    use super::{
        TableOutput, collect_remote_snapshot, collect_remote_snapshot_with_deadline,
        diagnostic_detail, executable_leaf, heading_path_token, is_glob, unsafe_plan_path,
        write_output,
    };
    use crate::github_service::{with_github_service, with_test_github_service};
    use larch_adapters::github::OctocrabGitHubService;
    use larch_core::{GitHubRepositoryRef, MigrationIssueSnapshot};
    use larch_test_support::{HttpResponseBuilder, IssueServiceExchange, IssueServiceStub};
    use serde_json::{Value, json};

    fn fixture_issue(number: u64, title: &str, body: &str) -> Value {
        let mut issue: Value = serde_json::from_str(include_str!(
            "../../larch-adapters/fixtures/github_issue.json"
        ))
        .expect("valid GitHub issue fixture");
        issue["id"] = json!(number);
        issue["number"] = json!(number);
        issue["title"] = json!(title);
        issue["body"] = json!(body);
        issue
    }

    fn service_factory(
        server: &IssueServiceStub,
    ) -> Arc<dyn Fn() -> OctocrabGitHubService + Send + Sync> {
        let base = server.base_url().to_owned();
        Arc::new(move || OctocrabGitHubService::with_test_base(&base))
    }

    #[test]
    fn scope_path_tokens_follow_the_legacy_heading_rule() {
        assert_eq!(
            heading_path_token("`docs/a b.md` (generated)"),
            "docs/a b.md"
        );
        assert_eq!(
            heading_path_token("src/main.rs (entrypoint)"),
            "src/main.rs"
        );
        assert!(unsafe_plan_path("../outside"));
        assert!(unsafe_plan_path("~/outside"));
        assert!(is_glob("crates/**/*.rs"));
    }

    #[test]
    fn executable_leaf_requires_the_chief_reference() {
        let issue = MigrationIssueSnapshot {
            number: 1,
            title: "[LEAF OF 7687] Fixture".to_owned(),
            state: "open".to_owned(),
            body: "Chief umbrella: #7687".to_owned(),
            updated_at: "2026-01-01T00:00:00Z".to_owned(),
        };
        assert!(executable_leaf(&issue, 7687));
        assert!(!executable_leaf(&issue, 9999));
        assert_eq!(TableOutput::parse("none"), Some(TableOutput::None));
    }

    #[test]
    fn diagnostics_are_redacted_and_capped_like_the_legacy_command() {
        let detail = diagnostic_detail(&"x".repeat(600));

        assert_eq!(detail.chars().count(), 500);
        assert!(!diagnostic_detail(&format!("ghp_{}", "a".repeat(36))).contains("ghp_"));
    }

    #[test]
    fn output_write_is_atomic_and_confined_to_an_existing_parent() {
        let directory = tempfile::tempdir().expect("output parent");
        let output = directory.path().join("migration-audit.json");

        write_output(&output, "{\"schema\":2}\n").expect("publish report");

        assert_eq!(
            fs::read_to_string(output).expect("published report"),
            "{\"schema\":2}\n"
        );
    }

    #[cfg(unix)]
    #[test]
    fn output_write_rejects_a_user_owned_symlink_parent() {
        use std::os::unix::fs::symlink;

        let directory = tempfile::tempdir().expect("output fixture");
        let real_parent = directory.path().join("real");
        fs::create_dir(&real_parent).expect("real parent");
        let linked_parent = directory.path().join("linked");
        symlink(&real_parent, &linked_parent).expect("user symlink");

        assert!(write_output(&linked_parent.join("report.json"), "report\n").is_err());
        assert!(!real_parent.join("report.json").exists());

        let nested = real_parent.join("nested");
        fs::create_dir(&nested).expect("nested real parent");
        assert!(write_output(&linked_parent.join("nested/report.json"), "report\n").is_err());
        assert!(!nested.join("report.json").exists());
    }

    #[test]
    fn loopback_snapshot_uses_only_the_typed_read_service() {
        let issue = fixture_issue(71, "ordinary open issue", "no Chief umbrella reference");
        let server = IssueServiceStub::start([
            IssueServiceExchange::any_json(200, json!([issue]).to_string())
                .expect("issue-list exchange"),
            IssueServiceExchange::any_json(200, "[]").expect("pull-request exchange"),
        ])
        .expect("start loopback service");
        let service = service_factory(&server);
        let repository = GitHubRepositoryRef::new("o", "r").expect("valid repository");

        let snapshot = with_test_github_service(service, || {
            with_github_service(async |service, cancellation| {
                collect_remote_snapshot(service, cancellation, &repository, 7687).await
            })
            .expect("typed snapshot")
        });

        assert_eq!(snapshot.open_issues.len(), 1);
        assert!(snapshot.dependencies.is_empty());
        assert!(snapshot.open_pr_branches.is_empty());
        let requests = server.finish().expect("completed loopback requests");
        assert_eq!(requests.len(), 2);
        assert!(requests.iter().all(|request| request.method == "GET"));
    }

    #[test]
    fn loopback_snapshot_collects_dependency_and_reference_evidence_read_only() {
        let leaf = fixture_issue(
            71,
            "[LEAF OF 7687] fixture",
            "Chief umbrella: #7687\nNative blockers: #99",
        );
        let referenced = fixture_issue(99, "referenced issue", "evidence");
        let server = IssueServiceStub::start([
            IssueServiceExchange::any_json(200, json!([leaf]).to_string())
                .expect("issue-list exchange"),
            IssueServiceExchange::any_json(200, r#"[{"number":99,"id":199}]"#)
                .expect("dependency exchange"),
            IssueServiceExchange::any_json(200, referenced.to_string())
                .expect("referenced issue exchange"),
            IssueServiceExchange::any_json(200, "[]").expect("pull-request exchange"),
        ])
        .expect("start loopback service");
        let service = service_factory(&server);
        let repository = GitHubRepositoryRef::new("o", "r").expect("valid repository");

        let snapshot = with_test_github_service(service, || {
            with_github_service(async |service, cancellation| {
                collect_remote_snapshot(service, cancellation, &repository, 7687).await
            })
            .expect("typed snapshot")
        });

        assert_eq!(snapshot.dependencies.len(), 1);
        assert_eq!(snapshot.dependencies[0].issue, 71);
        assert_eq!(snapshot.dependencies[0].blockers, vec![99]);
        assert_eq!(snapshot.referenced_issues.len(), 1);
        assert_eq!(snapshot.referenced_issues[0].number, 99);
        let requests = server.finish().expect("completed loopback requests");
        assert_eq!(requests.len(), 4);
        assert!(requests.iter().all(|request| request.method == "GET"));
    }

    #[test]
    fn loopback_snapshot_rejects_malformed_dependency_evidence() {
        let leaf = fixture_issue(71, "[LEAF OF 7687] fixture", "Chief umbrella: #7687");
        let server = IssueServiceStub::start([
            IssueServiceExchange::any_json(200, json!([leaf]).to_string())
                .expect("issue-list exchange"),
            IssueServiceExchange::any_json(200, r#"[{"number":0,"id":199}]"#)
                .expect("dependency exchange"),
        ])
        .expect("start loopback service");
        let service = service_factory(&server);
        let repository = GitHubRepositoryRef::new("o", "r").expect("valid repository");

        let error = with_test_github_service(service, || {
            with_github_service(async |service, cancellation| {
                collect_remote_snapshot(service, cancellation, &repository, 7687).await
            })
            .expect_err("invalid dependency evidence must be rejected")
            .into_detail()
        });

        assert_eq!(error, "issue #71: blocked-by row is invalid");
        let requests = server.finish().expect("completed loopback requests");
        assert_eq!(requests.len(), 2);
        assert!(requests.iter().all(|request| request.method == "GET"));
    }

    #[test]
    fn loopback_snapshot_redacts_transport_failure() {
        let server = IssueServiceStub::start([
            IssueServiceExchange::any_json(500, "{}").expect("transport failure")
        ])
        .expect("start loopback service");
        let service = service_factory(&server);
        let repository = GitHubRepositoryRef::new("o", "r").expect("valid repository");

        let error = with_test_github_service(service, || {
            with_github_service(async |service, cancellation| {
                collect_remote_snapshot(service, cancellation, &repository, 7687).await
            })
            .expect_err("transport failure must be unavailable evidence")
            .into_detail()
        });

        assert_eq!(error, "issue snapshot unavailable");
        let requests = server.finish().expect("completed loopback requests");
        assert_eq!(requests.len(), 1);
        assert!(requests.iter().all(|request| request.method == "GET"));
    }

    #[test]
    fn aggregate_snapshot_deadline_is_fail_closed_and_redacted() {
        let retry_later = HttpResponseBuilder::new(429)
            .header("content-type", "application/json")
            .expect("valid content type")
            .header("retry-after", "1")
            .expect("valid retry delay")
            .body("{}")
            .build()
            .expect("valid rate-limit response");
        let server = IssueServiceStub::start([IssueServiceExchange::any(retry_later)])
            .expect("start loopback service");
        let service = service_factory(&server);
        let repository = GitHubRepositoryRef::new("o", "r").expect("valid repository");

        let error = with_test_github_service(service, || {
            with_github_service(async |service, cancellation| {
                collect_remote_snapshot_with_deadline(
                    service,
                    cancellation,
                    &repository,
                    7687,
                    Duration::from_millis(100),
                )
                .await
            })
            .expect_err("aggregate deadline must reject an incomplete snapshot")
            .into_detail()
        });

        assert_eq!(error, "issue snapshot unavailable");
        let requests = server.finish().expect("completed loopback request");
        assert_eq!(requests.len(), 1);
        assert!(requests.iter().all(|request| request.method == "GET"));
    }
}
