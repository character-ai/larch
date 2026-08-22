//! Rust composition root for `/audit-umbrella`.
//!
//! The skill performs the evidence review inline. This module owns the
//! bounded GitHub/Git snapshot, durable artifacts, and every live graph
//! mutation so model-authored data cannot turn into an unchecked public write.

use crate::{
    git_command_runtime::GitCommandRuntime,
    github_repository_resolution::repository_ref,
    github_service::{
        ServiceFailure, list_exhaustive_issues, list_exhaustive_issues_for_state,
        with_github_service, with_github_service_policy,
    },
    issue_mutation_support::create_with_rollback,
    session_artifact_support::{
        canonical_directory, confine_session_path, read_expected_file, temporary_root,
        write_private_file,
    },
};
use clap::{Args, Subcommand};
use larch_adapters::git::WorktreePath;
use larch_adapters::{
    FetchRequest, GitRef, GitRefspec, GitRemote, GixRepository, PathIntent, TemporaryRoot,
    WorktreeRequest,
    github::{
        DependencyEdge, DependencySecurityCheck, GitHubOperationError, LiveMutationRequest,
        OctocrabGitHubService, SubIssueEdge, check_live_mutation_auth,
    },
    runtime::Cancellation,
};
use larch_core::{
    AUDIT_PROPOSAL_VERSION, AuditDependency, AuditDependencyNode, AuditGraphState, AuditIssue,
    AuditIssueFingerprint, AuditLeafState, AuditLedger, AuditLedgerViolation, AuditProposal,
    AuditProposalDraft, AuditProposalViolation, AuditSnapshot, AuditSource, DONE_PREFIX,
    GitHubIssue, GitHubIssueState, GitHubRepositoryRef, GitHubService, GitHubTransportPolicy,
    IMPLEMENTING_PREFIX, IssueCreateRequest, MAX_AUDIT_LEAVES, MAX_AUDIT_SOURCES, RepositoryRead,
    Revision, audit_issue_fingerprint, audit_leaf_prefix, audit_proposal_existing_numbers,
    audit_snapshot_sha256, diagnose_audit_ledger, diagnose_audit_proposal, emit_kv,
    has_umbrella_proposal, is_controlling_umbrella_title, mark_audit_graph_in_flight,
    mark_audit_leaf_in_flight, mark_audit_proposal_complete, parse_audit_ledger,
    parse_audit_proposal, parse_audit_snapshot, record_audit_leaf_resolved, render_audit_proposal,
    render_audit_snapshot, replace_audit_issue_fingerprints, umbrella_leaf_opening,
    validate_audit_proposal_binding,
};
use regex::Regex;
use std::{
    collections::{BTreeMap, BTreeSet},
    fmt::Write as _,
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
    sync::LazyLock,
};

const FILE_LIMIT: u64 = larch_core::MAX_AUDIT_ARTIFACT_BYTES as u64;

static ISSUE_REFERENCE_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?m)(?:^|[^[:alnum:]_])#(0*[1-9][0-9]*)\b")
        .expect("fixed issue-reference expression is valid")
});

/// The typed verbs behind the public audit skill.
#[derive(Subcommand)]
pub enum AuditUmbrellaCommand {
    /// Parse the public skill's one issue-number argument without shell policy.
    Parse(ParseArguments),
    /// Compute a proposal-safe identity from confined leaf title and body files.
    #[command(name = "leaf-identity")]
    LeafIdentity(LeafIdentityArguments),
    /// Build one immutable default-branch and issue-history snapshot.
    Snapshot(SnapshotArguments),
    /// Verify that the inline audit accounted for every immutable source item.
    #[command(name = "validate-ledger")]
    ValidateLedger(ValidateLedgerArguments),
    /// Bind a complete corrective batch before its first public mutation.
    #[command(name = "persist-proposal")]
    PersistProposal(PersistProposalArguments),
    /// Revalidate and apply one persisted corrective batch.
    Apply(ApplyArguments),
    /// Remove the detached audit worktree after the audit reaches a terminal state.
    #[command(name = "remove-worktree")]
    RemoveWorktree(RemoveWorktreeArguments),
}

#[derive(Args)]
pub struct ParseArguments {
    #[arg(long)]
    arguments: String,
}

#[derive(Args)]
pub struct LeafIdentityArguments {
    #[arg(long)]
    root: PathBuf,
    #[arg(long)]
    title: PathBuf,
    #[arg(long)]
    body: PathBuf,
}

#[derive(Args)]
pub struct SnapshotArguments {
    #[arg(long)]
    repository: String,
    #[arg(long)]
    issue: u64,
    #[arg(long)]
    repo_root: PathBuf,
    #[arg(long)]
    output_root: PathBuf,
    #[arg(long)]
    output: PathBuf,
    #[arg(long)]
    worktree: PathBuf,
}

#[derive(Args)]
pub struct ValidateLedgerArguments {
    #[arg(long)]
    root: PathBuf,
    #[arg(long)]
    snapshot: PathBuf,
    #[arg(long)]
    ledger: PathBuf,
}

#[derive(Args)]
pub struct PersistProposalArguments {
    #[arg(long)]
    repository: String,
    #[arg(long)]
    repo_root: PathBuf,
    #[arg(long)]
    root: PathBuf,
    #[arg(long)]
    snapshot: PathBuf,
    #[arg(long)]
    ledger: PathBuf,
    #[arg(long)]
    proposal_input: PathBuf,
    #[arg(long)]
    proposal: PathBuf,
}

#[derive(Args)]
pub struct ApplyArguments {
    #[arg(long)]
    repository: String,
    #[arg(long)]
    repo_root: PathBuf,
    #[arg(long)]
    root: PathBuf,
    #[arg(long)]
    snapshot: PathBuf,
    #[arg(long)]
    ledger: PathBuf,
    #[arg(long)]
    proposal: PathBuf,
    #[arg(long, action = clap::ArgAction::SetTrue)]
    operator_invoked: bool,
}

#[derive(Args)]
pub struct RemoveWorktreeArguments {
    #[arg(long)]
    repo_root: PathBuf,
    #[arg(long)]
    root: PathBuf,
    #[arg(long)]
    worktree: PathBuf,
}

#[must_use]
pub fn run(command: AuditUmbrellaCommand) -> ExitCode {
    let result = match command {
        AuditUmbrellaCommand::Parse(arguments) => parse(&arguments),
        AuditUmbrellaCommand::LeafIdentity(arguments) => leaf_identity(&arguments),
        AuditUmbrellaCommand::Snapshot(arguments) => snapshot(&arguments),
        AuditUmbrellaCommand::ValidateLedger(arguments) => validate_ledger(&arguments),
        AuditUmbrellaCommand::PersistProposal(arguments) => persist_proposal(&arguments),
        AuditUmbrellaCommand::Apply(arguments) => apply(&arguments),
        AuditUmbrellaCommand::RemoveWorktree(arguments) => remove_worktree(&arguments),
    };
    match result {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("audit-umbrella: {error}");
            ExitCode::FAILURE
        }
    }
}

fn parse(arguments: &ParseArguments) -> Result<(), String> {
    let issue = parse_umbrella_argument(&arguments.arguments)?;
    emit_kv("AUDIT_UMBRELLA", &issue.to_string());
    Ok(())
}

fn leaf_identity(arguments: &LeafIdentityArguments) -> Result<(), String> {
    let root = temporary_root(&arguments.root, "--root")?;
    let title = read_expected_file(
        &arguments.title,
        &arguments.root,
        &root,
        "--title",
        FILE_LIMIT,
    )?;
    let body = read_expected_file(
        &arguments.body,
        &arguments.root,
        &root,
        "--body",
        FILE_LIMIT,
    )?;
    if title.is_empty() || body.is_empty() {
        return Err("leaf identity inputs must not be empty".to_owned());
    }
    emit_kv(
        "AUDIT_LEAF_IDENTITY",
        &larch_core::audit_leaf_identity(&title, &body),
    );
    Ok(())
}

fn snapshot(arguments: &SnapshotArguments) -> Result<(), String> {
    require_issue(arguments.issue, "--issue")?;
    let repository = parse_repository(&arguments.repository)?;
    let repo_root = canonical_directory(&arguments.repo_root, "--repo-root")?;
    let root = temporary_root(&arguments.output_root, "--output-root")?;
    ensure_snapshot_paths_are_disjoint(
        &arguments.output,
        &arguments.worktree,
        &arguments.output_root,
        &root,
    )?;

    let default_branch = with_github_service(async |service, cancellation| {
        service
            .repository(&repository, cancellation)
            .await
            .map(|remote| remote.default_branch)
            .map_err(|_error| "cannot read repository default branch".to_owned())
    })
    .map_err(ServiceFailure::into_detail)?;
    let audited_sha = fetch_default_sha(&repo_root, &default_branch)?;
    let audited_commit = resolve_object_id(&repo_root, &audited_sha)?;
    let audit = with_github_service_policy(
        GitHubTransportPolicy::migration_audit(),
        async |service, cancellation| {
            collect_snapshot_remote(
                service,
                cancellation,
                &repository,
                arguments.issue,
                &default_branch,
                &audited_sha,
            )
            .await
        },
    )
    .map_err(ServiceFailure::into_detail)?;
    let snapshot_text = render_audit_snapshot(&audit).map_err(|error| error.reason().to_owned())?;

    create_detached_worktree(
        &repo_root,
        &root,
        &arguments.output_root,
        &arguments.worktree,
        &audited_sha,
    )?;
    verify_worktree_matches_audit(&arguments.worktree, &audited_commit)?;
    write_private_file(
        &arguments.output,
        &snapshot_text,
        &arguments.output_root,
        &root,
    )?;
    emit_kv("AUDIT_SNAPSHOT_WRITTEN", "true");
    emit_kv("AUDIT_SNAPSHOT_SHA256", &audit_snapshot_sha256(&audit));
    emit_kv("AUDIT_DEFAULT_SHA", &audited_sha);
    emit_kv("AUDIT_WORKTREE", &arguments.worktree.display().to_string());
    Ok(())
}

fn verify_worktree_matches_audit(
    worktree: &Path,
    audited_commit: &larch_core::ObjectId,
) -> Result<(), String> {
    let repository = GixRepository::open(worktree)
        .map_err(|_error| "cannot open detached audit worktree".to_owned())?;
    let head = repository
        .head()
        .map_err(|_error| "cannot read detached audit worktree HEAD".to_owned())?;
    let larch_core::Head::Detached { target: actual } = head else {
        return Err("audit worktree must remain detached".to_owned());
    };
    if actual != *audited_commit {
        return Err("audit worktree does not match the fetched default branch SHA".to_owned());
    }
    Ok(())
}

fn validate_ledger(arguments: &ValidateLedgerArguments) -> Result<(), String> {
    let root = temporary_root(&arguments.root, "--root")?;
    let snapshot = read_snapshot(&arguments.snapshot, &arguments.root, &root)?;
    let ledger = read_ledger(&arguments.ledger, &arguments.root, &root)?;
    let summary = match diagnose_audit_ledger(&snapshot, &ledger) {
        Ok(summary) => summary,
        Err(violation) => {
            let entry = violation
                .entry_id()
                .map(|id| format!(" entry={}", sanitize_entry_id(id)))
                .unwrap_or_default();
            let coverage = match violation {
                AuditLedgerViolation::Coverage { uncovered, unknown } => {
                    format!(" uncovered={uncovered} unknown={unknown}")
                }
                _ => String::new(),
            };
            eprintln!(
                "audit-umbrella: ledger-violation constraint={}{entry}{coverage}",
                violation.constraint()
            );
            return Err(violation.refusal().reason().to_owned());
        }
    };
    emit_kv("AUDIT_LEDGER_VALID", "true");
    emit_kv("AUDIT_REQUIREMENT_COUNT", &summary.total.to_string());
    emit_kv("AUDIT_GAP_COUNT", &summary.gaps.to_string());
    emit_kv("AUDIT_BLOCKED_COUNT", &summary.blocked.to_string());
    Ok(())
}

/// Bound an untrusted entry id to printable ASCII before it reaches a log line.
fn sanitize_entry_id(id: &str) -> String {
    id.chars()
        .filter(char::is_ascii_graphic)
        .take(128)
        .collect()
}

fn proposal_violation_diagnostic(violation: &AuditProposalViolation) -> String {
    let mut detail = format!("proposal-violation constraint={}", violation.constraint());
    if let AuditProposalViolation::Ledger { violation } = violation {
        let _ = write!(detail, " ledger_constraint={}", violation.constraint());
        if let Some(entry) = violation.entry_id() {
            let _ = write!(detail, " entry={}", sanitize_entry_id(entry));
        }
        if let AuditLedgerViolation::Coverage { uncovered, unknown } = violation {
            let _ = write!(detail, " uncovered={uncovered} unknown={unknown}");
        }
    }
    if let Some(leaf) = violation.leaf_index() {
        let _ = write!(detail, " leaf={leaf}");
    }
    if let Some(title) = violation.leaf_title() {
        let _ = write!(detail, " title={}", diagnostic_json(title, 160));
    }
    if let Some(section) = violation.section() {
        let _ = write!(detail, " section={}", diagnostic_json(section, 64));
    }
    if let Some(gap_id) = violation.gap_id() {
        let _ = write!(detail, " gap_id={}", diagnostic_json(gap_id, 128));
    }
    if let Some((dependency, removal)) = violation.dependency() {
        let kind = if removal { "removal" } else { "addition" };
        let _ = write!(detail, " dependency={dependency} kind={kind}");
    }
    detail
}

fn diagnostic_json(value: &str, limit: usize) -> String {
    let bounded = value
        .chars()
        .map(|character| {
            if character.is_ascii() && (character == ' ' || character.is_ascii_graphic()) {
                character
            } else {
                '?'
            }
        })
        .take(limit)
        .collect::<String>();
    serde_json::to_string(&bounded).unwrap_or_else(|_error| "\"<invalid>\"".to_owned())
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum AuditBaselineAction {
    Current,
    Rebaseline,
    ResumeTransaction,
}

fn audit_baseline_action(
    snapshot: &AuditSnapshot,
    proposal: &AuditProposal,
    current_sha: &str,
) -> Result<AuditBaselineAction, String> {
    if proposal.audited_sha != snapshot.audited_sha {
        return Err("proposal audited SHA does not match the audit snapshot".to_owned());
    }
    if current_sha == snapshot.audited_sha {
        return Ok(AuditBaselineAction::Current);
    }
    let mutation_started = proposal.complete
        || proposal.graph_state != AuditGraphState::Pending
        || proposal
            .leaves
            .iter()
            .any(|leaf| leaf.state != AuditLeafState::Pending);
    if mutation_started {
        Ok(AuditBaselineAction::ResumeTransaction)
    } else {
        Ok(AuditBaselineAction::Rebaseline)
    }
}

fn emit_audit_rebaseline(stage: &str, previous_sha: &str, current_sha: &str) {
    emit_kv("AUDIT_REBASELINE_REQUIRED", "true");
    emit_kv("AUDIT_REBASELINE_STAGE", stage);
    emit_kv("AUDIT_REBASELINE_FROM_SHA", previous_sha);
    emit_kv("AUDIT_REBASELINE_TO_SHA", current_sha);
}

fn persist_proposal(arguments: &PersistProposalArguments) -> Result<(), String> {
    let repository = parse_repository(&arguments.repository)?;
    let repo_root = canonical_directory(&arguments.repo_root, "--repo-root")?;
    let root = temporary_root(&arguments.root, "--root")?;
    let snapshot = read_snapshot(&arguments.snapshot, &arguments.root, &root)?;
    if snapshot.repository != arguments.repository {
        return Err("audit snapshot does not match --repository".to_owned());
    }
    let current_sha = fetch_default_sha(&repo_root, &snapshot.default_branch)?;
    if current_sha != snapshot.audited_sha {
        emit_audit_rebaseline("persist-proposal", &snapshot.audited_sha, &current_sha);
        return Ok(());
    }
    let ledger = read_ledger(&arguments.ledger, &arguments.root, &root)?;
    let draft_text = read_expected_file(
        &arguments.proposal_input,
        &arguments.root,
        &root,
        "--proposal-input",
        FILE_LIMIT,
    )?;
    let draft = parse_proposal_draft(&draft_text)?;
    let mut proposal = match diagnose_audit_proposal(&snapshot, &ledger, &draft) {
        Ok(proposal) => proposal,
        Err(violation) => {
            eprintln!(
                "audit-umbrella: {}",
                proposal_violation_diagnostic(&violation)
            );
            return Err(violation.refusal().reason().to_owned());
        }
    };
    if proposal.repository != arguments.repository {
        return Err("proposal repository does not match --repository".to_owned());
    }

    let (current, open_history) = with_github_service_policy(
        GitHubTransportPolicy::migration_audit(),
        async |service, cancellation| {
            eprintln!("audit-umbrella: persist-proposal verifying snapshot");
            verify_snapshot_unchanged(service, cancellation, &repository, &snapshot).await?;
            eprintln!("audit-umbrella: persist-proposal reading live proposal issues");
            let current =
                read_live_proposal_issues(service, cancellation, &repository, &proposal).await?;
            eprintln!("audit-umbrella: persist-proposal listing open issue history for dedup");
            let history = list_all_issues(service, cancellation, &repository).await?;
            Ok((current, history))
        },
    )
    .map_err(ServiceFailure::into_detail)?;
    verify_snapshot_sources_fresh(&snapshot, &current)?;
    let reused = count_open_duplicate_leaves(&proposal, &open_history)?;
    replace_audit_issue_fingerprints(&mut proposal, fingerprints(&current))
        .map_err(|error| error.reason().to_owned())?;
    validate_audit_proposal_binding(&proposal, &snapshot, &ledger)
        .map_err(|error| error.reason().to_owned())?;
    write_proposal(&arguments.proposal, &arguments.root, &root, &proposal)?;
    emit_kv("AUDIT_PROPOSAL_PERSISTED", "true");
    emit_kv(
        "AUDIT_PROPOSAL_VERSION",
        &AUDIT_PROPOSAL_VERSION.to_string(),
    );
    emit_kv(
        "AUDIT_PROPOSAL_LEAF_COUNT",
        &proposal.leaves.len().to_string(),
    );
    emit_kv("AUDIT_REUSED_LEAF_COUNT", &reused.to_string());
    Ok(())
}

fn apply(arguments: &ApplyArguments) -> Result<(), String> {
    require_operator(arguments.operator_invoked)?;
    let authorization = operator_authorization();
    if !check_live_mutation_auth(&authorization).is_authorized() {
        return Err("live mutation authorization was refused".to_owned());
    }
    let repository = parse_repository(&arguments.repository)?;
    let repo_root = canonical_directory(&arguments.repo_root, "--repo-root")?;
    let root = temporary_root(&arguments.root, "--root")?;
    let snapshot = read_snapshot(&arguments.snapshot, &arguments.root, &root)?;
    let ledger = read_ledger(&arguments.ledger, &arguments.root, &root)?;
    let mut proposal = read_proposal(&arguments.proposal, &arguments.root, &root)?;
    validate_audit_proposal_binding(&proposal, &snapshot, &ledger)
        .map_err(|error| error.reason().to_owned())?;
    if proposal.repository != arguments.repository || snapshot.repository != arguments.repository {
        return Err("audit artifacts do not match --repository".to_owned());
    }
    let current_sha = fetch_default_sha(&repo_root, &snapshot.default_branch)?;
    if audit_baseline_action(&snapshot, &proposal, &current_sha)? == AuditBaselineAction::Rebaseline
    {
        emit_audit_rebaseline("apply", &snapshot.audited_sha, &current_sha);
        return Ok(());
    }

    with_github_service_policy(
        GitHubTransportPolicy::migration_audit(),
        async |service, cancellation| {
            let context = ApplyContext {
                service,
                cancellation,
                repository: &repository,
                snapshot: &snapshot,
                ledger: &ledger,
                proposal_path: &arguments.proposal,
                supplied_root: &arguments.root,
                root: &root,
                authorization: &authorization,
            };
            apply_remote(&context, &mut proposal).await
        },
    )
    .map_err(ServiceFailure::into_detail)?;
    emit_kv("AUDIT_APPLIED", "true");
    emit_kv("AUDIT_UMBRELLA", &proposal.umbrella.to_string());
    emit_kv("AUDIT_LEAF_COUNT", &proposal.leaves.len().to_string());
    Ok(())
}

fn remove_worktree(arguments: &RemoveWorktreeArguments) -> Result<(), String> {
    let repo_root = canonical_directory(&arguments.repo_root, "--repo-root")?;
    let root = temporary_root(&arguments.root, "--root")?;
    let confined = confine_session_path(
        &arguments.worktree,
        &arguments.root,
        &root,
        PathIntent::Cleanup,
        "--worktree",
    )?;
    let path = confined.path().to_path_buf();
    if fs::symlink_metadata(&path).is_ok_and(|metadata| metadata.file_type().is_symlink()) {
        return Err("--worktree must not be a symbolic link".to_owned());
    }
    let worktree = WorktreePath::new(&path).map_err(|error| error.to_string())?;
    run_worktree_request(
        &repo_root,
        WorktreeRequest::Remove {
            force: true,
            path: worktree,
        },
    )?;
    if fs::symlink_metadata(&path).is_ok() {
        return Err("detached worktree removal did not remove its directory".to_owned());
    }
    emit_kv("AUDIT_WORKTREE_REMOVED", "true");
    Ok(())
}

async fn collect_snapshot_remote(
    service: &OctocrabGitHubService,
    cancellation: &Cancellation,
    repository: &GitHubRepositoryRef,
    umbrella: u64,
    expected_branch: &str,
    audited_sha: &str,
) -> Result<AuditSnapshot, String> {
    let remote = service
        .repository(repository, cancellation)
        .await
        .map_err(|_error| "cannot read repository default branch".to_owned())?;
    if remote.default_branch != expected_branch {
        return Err("repository default branch changed during snapshot".to_owned());
    }
    let parent = service
        .issue(repository, umbrella, cancellation)
        .await
        .map_err(|_error| "cannot read umbrella issue".to_owned())?;
    validate_audit_parent(&parent)?;
    let direct = service
        .list_sub_issues(
            cancellation,
            repository.owner(),
            repository.name(),
            umbrella,
        )
        .await
        .map_err(|_error| "cannot read direct native leaf graph".to_owned())?;
    if direct.len() > MAX_AUDIT_LEAVES {
        return Err("umbrella has too many direct leaves for one audit".to_owned());
    }
    let mut direct_numbers = BTreeSet::new();
    for reference in direct {
        if !direct_numbers.insert(reference.issue_number()) {
            return Err("GitHub returned duplicate direct leaf identities".to_owned());
        }
    }
    let referenced_numbers = issue_references(&parent.body);
    if referenced_numbers.len() > MAX_AUDIT_SOURCES {
        return Err("umbrella has too many issue references for one audit".to_owned());
    }
    let explicit_numbers = explicit_leaf_references(&parent.body);
    let listed = list_exhaustive_issues(service, cancellation, repository)
        .await
        .map_err(|error| format!("cannot read exhaustive issue history: {error}"))?;
    let mut issues = BTreeMap::new();
    for issue in listed {
        if issues.insert(issue.number, issue).is_some() {
            return Err("issue history contains duplicate issue numbers".to_owned());
        }
    }
    match issues.insert(parent.number, parent.clone()) {
        Some(previous) if previous != parent => {
            return Err("umbrella changed during issue-history snapshot".to_owned());
        }
        _ => {}
    }
    let required = direct_numbers
        .iter()
        .chain(referenced_numbers.iter())
        .copied()
        .filter(|number| *number != umbrella)
        .collect::<BTreeSet<_>>();
    let missing_references = required
        .into_iter()
        .filter(|number| !issues.contains_key(number))
        .collect::<Vec<_>>();
    for number in missing_references {
        let issue = service
            .issue(repository, number, cancellation)
            .await
            .map_err(|_error| "cannot read referenced issue".to_owned())?;
        if issues.insert(number, issue).is_some() {
            return Err("referenced issue identity was duplicated".to_owned());
        }
    }
    require_no_nested_umbrella_children(&issues, &direct_numbers)?;
    build_snapshot(SnapshotSelection {
        repository,
        default_branch: &remote.default_branch,
        audited_sha,
        parent: &parent,
        issues: &issues,
        direct_numbers: &direct_numbers,
        explicit_numbers: &explicit_numbers,
        referenced_numbers: &referenced_numbers,
    })
}

/// Re-discover the complete live issue graph before the batch's first public
/// mutation. Session artifacts are model-authored and therefore cannot be the
/// authority for a historical leaf or controlling-source set on their own.
async fn verify_snapshot_unchanged(
    service: &OctocrabGitHubService,
    cancellation: &Cancellation,
    repository: &GitHubRepositoryRef,
    snapshot: &AuditSnapshot,
) -> Result<(), String> {
    let live = collect_snapshot_remote(
        service,
        cancellation,
        repository,
        snapshot.umbrella.number,
        &snapshot.default_branch,
        &snapshot.audited_sha,
    )
    .await?;
    if live == *snapshot {
        Ok(())
    } else {
        Err("audit snapshot changed before public mutation".to_owned())
    }
}

#[derive(Clone, Copy)]
struct SnapshotSelection<'a> {
    repository: &'a GitHubRepositoryRef,
    default_branch: &'a str,
    audited_sha: &'a str,
    parent: &'a GitHubIssue,
    issues: &'a BTreeMap<u64, GitHubIssue>,
    direct_numbers: &'a BTreeSet<u64>,
    explicit_numbers: &'a BTreeSet<u64>,
    referenced_numbers: &'a BTreeSet<u64>,
}

fn build_snapshot(selection: SnapshotSelection<'_>) -> Result<AuditSnapshot, String> {
    let SnapshotSelection {
        repository,
        default_branch,
        audited_sha,
        parent,
        issues,
        direct_numbers,
        explicit_numbers,
        referenced_numbers,
    } = selection;
    let opening = umbrella_leaf_opening(parent.number);
    let mut roles = BTreeMap::<u64, BTreeSet<String>>::new();
    let _ = roles
        .entry(parent.number)
        .or_default()
        .insert("umbrella".to_owned());
    let mut historical = BTreeSet::new();
    let mut controls = BTreeSet::new();
    for (number, issue) in issues {
        if *number == parent.number {
            continue;
        }
        let is_control = referenced_numbers.contains(number) && is_controlling_umbrella(issue);
        if is_control {
            let _ = controls.insert(*number);
            let _ = roles
                .entry(*number)
                .or_default()
                .insert("control".to_owned());
            continue;
        }
        if direct_numbers.contains(number) {
            let _ = historical.insert(*number);
            let _ = roles
                .entry(*number)
                .or_default()
                .insert("native".to_owned());
        }
        if explicit_numbers.contains(number) {
            let _ = historical.insert(*number);
            let _ = roles
                .entry(*number)
                .or_default()
                .insert("explicit".to_owned());
        }
        if has_exact_leaf_title(&issue.title, parent.number) {
            let _ = historical.insert(*number);
            let _ = roles.entry(*number).or_default().insert("title".to_owned());
        }
        if issue.body.lines().next() == Some(opening.as_str()) {
            let _ = historical.insert(*number);
            let _ = roles
                .entry(*number)
                .or_default()
                .insert("backlink".to_owned());
        }
    }
    if historical.len() > MAX_AUDIT_SOURCES
        || roles.len() > MAX_AUDIT_SOURCES
        || controls.len() > MAX_AUDIT_SOURCES
    {
        return Err("audit history exceeds the bounded source contract".to_owned());
    }
    let mut sources = Vec::with_capacity(roles.len());
    for (number, source_roles) in roles {
        let issue = issues
            .get(&number)
            .ok_or_else(|| "selected audit source disappeared".to_owned())?;
        let source_id = if number == parent.number {
            format!("umbrella:{number}")
        } else if historical.contains(&number) {
            format!("leaf:{number}")
        } else {
            format!("control:{number}")
        };
        sources.push(AuditSource {
            id: source_id,
            roles: source_roles.into_iter().collect(),
            issue: audit_issue(issue)?,
        });
    }
    sources.sort_by(|left, right| left.id.cmp(&right.id));
    let snapshot = AuditSnapshot {
        version: larch_core::AUDIT_SNAPSHOT_VERSION,
        repository: format!("{}/{}", repository.owner(), repository.name()),
        default_branch: default_branch.to_owned(),
        audited_sha: audited_sha.to_owned(),
        umbrella: audit_issue(parent)?,
        sources,
        historical_leaf_numbers: historical.into_iter().collect(),
    };
    render_audit_snapshot(&snapshot).map_err(|error| error.reason().to_owned())?;
    Ok(snapshot)
}

fn issue_references(body: &str) -> BTreeSet<u64> {
    ISSUE_REFERENCE_RE
        .captures_iter(body)
        .filter_map(|capture| capture.get(1))
        .filter_map(|capture| capture.as_str().parse::<u64>().ok())
        .collect()
}

/// Select exact issue references that the umbrella presents as leaf-list
/// entries. Generic prose references remain available for control-context
/// discovery, but never become relationship-mutation targets.
fn explicit_leaf_references(body: &str) -> BTreeSet<u64> {
    let mut in_leaf_section = false;
    let mut values = BTreeSet::new();
    for line in body.lines() {
        let trimmed = line.trim_start();
        let heading = trimmed.trim_start_matches('#');
        if heading.len() != trimmed.len() && heading.chars().next().is_some_and(char::is_whitespace)
        {
            let heading = heading.trim().to_ascii_lowercase();
            in_leaf_section = heading.contains("leaf");
            continue;
        }
        if in_leaf_section && trimmed.starts_with('#') {
            values.extend(issue_references(trimmed));
            continue;
        }
        let Some(item) = trimmed
            .strip_prefix("- ")
            .or_else(|| trimmed.strip_prefix("* "))
            .or_else(|| trimmed.strip_prefix("+ "))
        else {
            continue;
        };
        let checklist = item
            .strip_prefix("[ ] ")
            .or_else(|| item.strip_prefix("[x] "))
            .or_else(|| item.strip_prefix("[X] "));
        if checklist.is_some() || (in_leaf_section && item.starts_with('#')) {
            values.extend(issue_references(item));
        }
    }
    values
}

fn has_exact_leaf_title(title: &str, umbrella: u64) -> bool {
    let title = title
        .strip_prefix(IMPLEMENTING_PREFIX)
        .or_else(|| title.strip_prefix(DONE_PREFIX))
        .unwrap_or(title);
    let prefix = audit_leaf_prefix(umbrella);
    title
        .strip_prefix(&prefix)
        .is_some_and(|rest| !rest.trim().is_empty())
}

fn is_controlling_umbrella(issue: &GitHubIssue) -> bool {
    is_controlling_umbrella_title(&issue.title)
}

/// Refuse an audit target whose direct native children are themselves umbrellas.
///
/// Having a parent (for example the chief program umbrella) is allowed. A tree
/// whose direct leaves carry `[UMBRELLA]` or `[CHIEF UMBRELLA]` titles is not.
fn require_no_nested_umbrella_children(
    issues: &BTreeMap<u64, GitHubIssue>,
    direct_numbers: &BTreeSet<u64>,
) -> Result<(), String> {
    for number in direct_numbers {
        let Some(child) = issues.get(number) else {
            return Err(format!(
                "direct child #{number} is missing from the audit snapshot"
            ));
        };
        if is_controlling_umbrella(child) {
            return Err("nested umbrellas are not supported".to_owned());
        }
    }
    Ok(())
}

fn audit_issue_title<'a>(
    number: u64,
    snapshot: &'a AuditSnapshot,
    current: &'a BTreeMap<u64, AuditIssue>,
) -> Option<&'a str> {
    if let Some(issue) = current.get(&number) {
        return Some(issue.title.as_str());
    }
    if snapshot.umbrella.number == number {
        return Some(snapshot.umbrella.title.as_str());
    }
    snapshot
        .sources
        .iter()
        .find(|source| source.issue.number == number)
        .map(|source| source.issue.title.as_str())
}

fn require_no_nested_umbrella_titles(
    snapshot: &AuditSnapshot,
    current: &BTreeMap<u64, AuditIssue>,
    direct_numbers: &BTreeSet<u64>,
) -> Result<(), String> {
    for number in direct_numbers {
        let Some(title) = audit_issue_title(*number, snapshot, current) else {
            return Err(format!(
                "direct child #{number} is missing from the audit binding"
            ));
        };
        if is_controlling_umbrella_title(title) {
            return Err("umbrella became nested after the audit snapshot".to_owned());
        }
    }
    Ok(())
}

fn validate_audit_parent(parent: &GitHubIssue) -> Result<(), String> {
    if parent.is_pull_request {
        return Err("umbrella target is a pull request".to_owned());
    }
    if parent.state != GitHubIssueState::Open {
        return Err("umbrella target is not open".to_owned());
    }
    let title = parent
        .title
        .strip_prefix(IMPLEMENTING_PREFIX)
        .or_else(|| parent.title.strip_prefix(DONE_PREFIX))
        .unwrap_or(&parent.title);
    if !title.starts_with("[UMBRELLA] ")
        || !(has_umbrella_proposal(&parent.body) || is_legacy_managed_umbrella(&parent.body))
    {
        return Err("umbrella target is not a managed umbrella".to_owned());
    }
    Ok(())
}

/// Older managed umbrellas predate the durable proposal marker, but still
/// carry the convention's explicit leaf section.  A title alone is never an
/// authority to mutate an issue graph.
fn is_legacy_managed_umbrella(body: &str) -> bool {
    body.lines().any(|line| {
        let trimmed = line.trim_start();
        let heading = trimmed.trim_start_matches('#');
        heading.len() != trimmed.len()
            && heading.chars().next().is_some_and(char::is_whitespace)
            && heading.trim().eq_ignore_ascii_case("leaf issues")
    }) && !explicit_leaf_references(body).is_empty()
}

fn audit_issue(issue: &GitHubIssue) -> Result<AuditIssue, String> {
    if issue.is_pull_request {
        return Err("audit sources cannot be pull requests".to_owned());
    }
    let state = match issue.state {
        GitHubIssueState::Open => "open",
        GitHubIssueState::Closed => "closed",
        GitHubIssueState::All => return Err("issue snapshot has an unconstrained state".to_owned()),
    };
    Ok(AuditIssue {
        number: issue.number,
        id: issue.id,
        title: issue.title.clone(),
        body: issue.body.clone(),
        state: state.to_owned(),
        updated_at: issue.updated_at.clone(),
        url: issue.url.clone(),
    })
}

async fn read_live_proposal_issues(
    service: &OctocrabGitHubService,
    cancellation: &Cancellation,
    repository: &GitHubRepositoryRef,
    proposal: &AuditProposal,
) -> Result<BTreeMap<u64, AuditIssue>, String> {
    let mut current = BTreeMap::new();
    for number in audit_proposal_existing_numbers(proposal) {
        let issue = service
            .issue(repository, number, cancellation)
            .await
            .map_err(|_error| "cannot re-read an audit-bound issue".to_owned())?;
        let issue = audit_issue(&issue)?;
        if current.insert(number, issue).is_some() {
            return Err("audit-bound issue numbers are not unique".to_owned());
        }
    }
    Ok(current)
}

struct ApplyContext<'a> {
    service: &'a OctocrabGitHubService,
    cancellation: &'a Cancellation,
    repository: &'a GitHubRepositoryRef,
    snapshot: &'a AuditSnapshot,
    ledger: &'a AuditLedger,
    proposal_path: &'a Path,
    supplied_root: &'a Path,
    root: &'a TemporaryRoot,
    authorization: &'a LiveMutationRequest<'static>,
}

async fn apply_remote(
    context: &ApplyContext<'_>,
    proposal: &mut AuditProposal,
) -> Result<(), String> {
    let current = prepare_remote_apply(context, proposal).await?;
    if proposal.complete {
        return verify_final_graph(
            context.service,
            context.cancellation,
            context.repository,
            context.snapshot,
            proposal,
            &current,
        )
        .await;
    }
    reconcile_audit_leaves(context, proposal).await?;
    enter_graph_reconciliation(context, proposal).await?;
    reconcile_leaf_relationships(context, proposal).await?;
    finish_graph_reconciliation(context, proposal).await
}

async fn prepare_remote_apply(
    context: &ApplyContext<'_>,
    proposal: &AuditProposal,
) -> Result<BTreeMap<u64, AuditIssue>, String> {
    let created_leaf_exists = proposal.leaves.iter().any(|leaf| {
        leaf.state != AuditLeafState::Pending
            && !context
                .snapshot
                .historical_leaf_numbers
                .contains(&leaf.number)
    });
    if proposal.graph_state == AuditGraphState::Pending && !created_leaf_exists {
        verify_snapshot_unchanged(
            context.service,
            context.cancellation,
            context.repository,
            context.snapshot,
        )
        .await?;
    }
    let current = read_live_proposal_issues(
        context.service,
        context.cancellation,
        context.repository,
        proposal,
    )
    .await?;
    if proposal.complete {
        return Ok(current);
    }
    let graph_in_flight = proposal.graph_state == AuditGraphState::InFlight;
    if graph_in_flight {
        verify_snapshot_source_content(context.snapshot, &current)?;
    } else {
        verify_snapshot_sources_fresh(context.snapshot, &current)?;
        verify_expected_fingerprints(proposal, &current)?;
    }
    verify_live_umbrella(
        context.service,
        context.cancellation,
        context.repository,
        context.snapshot,
        proposal,
        &current,
        !graph_in_flight,
    )
    .await?;
    Ok(current)
}

async fn enter_graph_reconciliation(
    context: &ApplyContext<'_>,
    proposal: &mut AuditProposal,
) -> Result<(), String> {
    if proposal.graph_state != AuditGraphState::Pending {
        return Ok(());
    }
    let current = read_live_proposal_issues(
        context.service,
        context.cancellation,
        context.repository,
        proposal,
    )
    .await?;
    verify_snapshot_sources_fresh(context.snapshot, &current)?;
    verify_expected_fingerprints(proposal, &current)?;
    verify_live_umbrella(
        context.service,
        context.cancellation,
        context.repository,
        context.snapshot,
        proposal,
        &current,
        true,
    )
    .await?;
    mark_audit_graph_in_flight(proposal).map_err(|error| error.reason().to_owned())?;
    write_proposal(
        context.proposal_path,
        context.supplied_root,
        context.root,
        proposal,
    )
}

async fn reconcile_leaf_relationships(
    context: &ApplyContext<'_>,
    proposal: &mut AuditProposal,
) -> Result<(), String> {
    for number in historical_direct_leaf_numbers(context.snapshot) {
        let current = read_live_proposal_issues(
            context.service,
            context.cancellation,
            context.repository,
            proposal,
        )
        .await?;
        let old_leaf = current
            .get(&number)
            .ok_or_else(|| "an old audit leaf is missing from the live binding".to_owned())?;
        attach_issue(
            context.service,
            context.cancellation,
            context.repository,
            proposal.umbrella,
            old_leaf.number,
            old_leaf.id,
            context.authorization,
        )
        .await?;
        persist_refreshed_proposal(context, proposal).await?;
    }
    for leaf in proposal.leaves.clone() {
        attach_leaf(
            context.service,
            context.cancellation,
            context.repository,
            proposal.umbrella,
            &leaf,
            context.authorization,
        )
        .await?;
        persist_refreshed_proposal(context, proposal).await?;
    }
    apply_dependencies(
        context.service,
        context.cancellation,
        context.repository,
        proposal,
        context.authorization,
    )
    .await
}

async fn finish_graph_reconciliation(
    context: &ApplyContext<'_>,
    proposal: &mut AuditProposal,
) -> Result<(), String> {
    let current = persist_refreshed_proposal(context, proposal).await?;
    verify_final_graph(
        context.service,
        context.cancellation,
        context.repository,
        context.snapshot,
        proposal,
        &current,
    )
    .await?;
    validate_audit_proposal_binding(proposal, context.snapshot, context.ledger)
        .map_err(|error| error.reason().to_owned())?;
    mark_audit_proposal_complete(proposal).map_err(|error| error.reason().to_owned())?;
    write_proposal(
        context.proposal_path,
        context.supplied_root,
        context.root,
        proposal,
    )
}

async fn persist_refreshed_proposal(
    context: &ApplyContext<'_>,
    proposal: &mut AuditProposal,
) -> Result<BTreeMap<u64, AuditIssue>, String> {
    let current = refresh_fingerprints(
        context.service,
        context.cancellation,
        context.repository,
        proposal,
    )
    .await?;
    write_proposal(
        context.proposal_path,
        context.supplied_root,
        context.root,
        proposal,
    )?;
    Ok(current)
}

async fn reconcile_audit_leaves(
    context: &ApplyContext<'_>,
    proposal: &mut AuditProposal,
) -> Result<(), String> {
    for leaf in proposal.leaves.clone() {
        match leaf.state {
            AuditLeafState::Pending => reconcile_pending_leaf(context, proposal, &leaf).await?,
            AuditLeafState::InFlight => reconcile_in_flight_leaf(context, proposal, &leaf).await?,
            AuditLeafState::Resolved => verify_resolved_leaf(context, &leaf).await?,
        }
    }
    Ok(())
}

async fn reconcile_pending_leaf(
    context: &ApplyContext<'_>,
    proposal: &mut AuditProposal,
    leaf: &larch_core::AuditLeaf,
) -> Result<(), String> {
    let listed = list_all_issues(context.service, context.cancellation, context.repository).await?;
    let matching = exact_open_leaf_matches(&leaf.title, &leaf.body, &listed);
    if matching.len() > 1 {
        return Err("exact audit-leaf reuse is ambiguous after proposal persistence".to_owned());
    }
    if let Some(existing) = matching.first() {
        let number = existing.number;
        let issue_id = existing.id;
        let url = existing.url.clone();
        mark_audit_leaf_in_flight(proposal, &leaf.identity)
            .map_err(|error| error.reason().to_owned())?;
        return persist_leaf_resolution(context, proposal, &leaf.identity, number, issue_id, &url)
            .await;
    }
    mark_audit_leaf_in_flight(proposal, &leaf.identity)
        .map_err(|error| error.reason().to_owned())?;
    write_proposal(
        context.proposal_path,
        context.supplied_root,
        context.root,
        proposal,
    )?;
    let created = create_with_rollback(
        context.service,
        context.cancellation,
        context.authorization,
        &IssueCreateRequest {
            repository: context.repository.clone(),
            title: leaf.title.clone(),
            body: leaf.body.clone(),
            assign_authenticated_user: false,
            labels: Vec::new(),
        },
    )
    .await
    .map_err(|_failure| {
        "audit leaf creation was not proven; the durable proposal remains in-flight".to_owned()
    })?;
    persist_leaf_resolution(
        context,
        proposal,
        &leaf.identity,
        created.number,
        created.id,
        &created.url,
    )
    .await
}

async fn reconcile_in_flight_leaf(
    context: &ApplyContext<'_>,
    proposal: &mut AuditProposal,
    leaf: &larch_core::AuditLeaf,
) -> Result<(), String> {
    let listed = list_all_issues(context.service, context.cancellation, context.repository).await?;
    let matching = exact_open_leaf_matches(&leaf.title, &leaf.body, &listed);
    let [resolved] = matching.as_slice() else {
        return Err(
            "in-flight audit leaf cannot be reconciled to exactly one public issue".to_owned(),
        );
    };
    let number = resolved.number;
    let issue_id = resolved.id;
    let url = resolved.url.clone();
    persist_leaf_resolution(context, proposal, &leaf.identity, number, issue_id, &url).await
}

async fn persist_leaf_resolution(
    context: &ApplyContext<'_>,
    proposal: &mut AuditProposal,
    identity: &str,
    number: u64,
    issue_id: u64,
    url: &str,
) -> Result<(), String> {
    record_audit_leaf_resolved(proposal, identity, number, issue_id, url)
        .map_err(|error| error.reason().to_owned())?;
    let _ = refresh_fingerprints(
        context.service,
        context.cancellation,
        context.repository,
        proposal,
    )
    .await?;
    write_proposal(
        context.proposal_path,
        context.supplied_root,
        context.root,
        proposal,
    )
}

async fn verify_resolved_leaf(
    context: &ApplyContext<'_>,
    leaf: &larch_core::AuditLeaf,
) -> Result<(), String> {
    let resolved = context
        .service
        .issue(context.repository, leaf.number, context.cancellation)
        .await
        .map_err(|_error| "cannot re-read resolved audit leaf".to_owned())?;
    let expected_issue_id = leaf.issue_id;
    let exact_identity = resolved.id == expected_issue_id
        && resolved.url == leaf.url
        && resolved.state == GitHubIssueState::Open
        && resolved.title == leaf.title
        && resolved.body == leaf.body;
    if exact_identity {
        Ok(())
    } else {
        Err("resolved audit leaf no longer has its exact identity".to_owned())
    }
}

async fn list_all_issues(
    service: &OctocrabGitHubService,
    cancellation: &Cancellation,
    repository: &GitHubRepositoryRef,
) -> Result<Vec<GitHubIssue>, String> {
    list_exhaustive_issues_for_state(service, cancellation, repository, GitHubIssueState::Open)
        .await
        .map_err(|error| format!("cannot reconcile open issue history: {error}"))
}

/// Count exact open matches without advancing durable transaction state.
///
/// Exact title and body equality includes the required fixed opening, so this
/// never turns a similar issue into a heuristic reuse. Apply binds the identity
/// only after its default-branch freshness check. More than one matching issue
/// is ambiguous and must stop the batch before mutation.
fn count_open_duplicate_leaves(
    proposal: &AuditProposal,
    issues: &[GitHubIssue],
) -> Result<usize, String> {
    let mut reused = 0;
    for leaf in &proposal.leaves {
        if leaf.state != AuditLeafState::Pending {
            continue;
        }
        let matching = exact_open_leaf_matches(&leaf.title, &leaf.body, issues);
        match matching.as_slice() {
            [] => {}
            [_existing] => reused += 1,
            _ => {
                return Err("exact audit-leaf reuse is ambiguous".to_owned());
            }
        }
    }
    Ok(reused)
}

fn exact_open_leaf_matches<'issues>(
    title: &str,
    body: &str,
    issues: &'issues [GitHubIssue],
) -> Vec<&'issues GitHubIssue> {
    issues
        .iter()
        .filter(|issue| {
            !issue.is_pull_request
                && issue.state == GitHubIssueState::Open
                && issue.title == title
                && issue.body == body
        })
        .collect()
}

async fn refresh_fingerprints(
    service: &OctocrabGitHubService,
    cancellation: &Cancellation,
    repository: &GitHubRepositoryRef,
    proposal: &mut AuditProposal,
) -> Result<BTreeMap<u64, AuditIssue>, String> {
    let current = read_live_proposal_issues(service, cancellation, repository, proposal).await?;
    replace_audit_issue_fingerprints(proposal, fingerprints(&current))
        .map_err(|error| error.reason().to_owned())?;
    Ok(current)
}

async fn verify_live_umbrella(
    service: &OctocrabGitHubService,
    cancellation: &Cancellation,
    repository: &GitHubRepositoryRef,
    snapshot: &AuditSnapshot,
    proposal: &AuditProposal,
    current: &BTreeMap<u64, AuditIssue>,
    require_fresh_fingerprints: bool,
) -> Result<(), String> {
    let parent = service
        .issue(repository, proposal.umbrella, cancellation)
        .await
        .map_err(|_error| "cannot re-read umbrella before mutation".to_owned())?;
    validate_audit_parent(&parent)?;
    let current_parent = current
        .get(&proposal.umbrella)
        .ok_or_else(|| "umbrella is missing from the audit binding".to_owned())?;
    if audit_issue(&parent)? != *current_parent {
        return Err("umbrella changed during the pre-mutation graph check".to_owned());
    }
    let native = native_leaf_numbers(snapshot);
    let historical_direct = historical_direct_leaf_numbers(snapshot);
    let direct = service
        .list_sub_issues(
            cancellation,
            repository.owner(),
            repository.name(),
            proposal.umbrella,
        )
        .await
        .map_err(|_error| "cannot re-read direct native leaf graph".to_owned())?
        .into_iter()
        .map(|reference| reference.issue_number())
        .collect::<BTreeSet<_>>();
    let mut allowed_direct = historical_direct;
    for leaf in &proposal.leaves {
        if leaf.state == AuditLeafState::Resolved {
            let _ = allowed_direct.insert(leaf.number);
        }
    }
    if !native.is_subset(&direct) || !direct.is_subset(&allowed_direct) {
        return Err(
            "direct native leaf graph changed outside the persisted audit batch".to_owned(),
        );
    }
    require_no_nested_umbrella_titles(snapshot, current, &direct)?;
    if require_fresh_fingerprints && fingerprints(current) != proposal.expected_issues {
        return Err("audit-bound issue changed before mutation".to_owned());
    }
    Ok(())
}

async fn attach_leaf(
    service: &OctocrabGitHubService,
    cancellation: &Cancellation,
    repository: &GitHubRepositoryRef,
    umbrella: u64,
    leaf: &larch_core::AuditLeaf,
    authorization: &LiveMutationRequest<'_>,
) -> Result<(), String> {
    if leaf.state != AuditLeafState::Resolved {
        return Err("cannot attach an unresolved audit leaf".to_owned());
    }
    attach_issue(
        service,
        cancellation,
        repository,
        umbrella,
        leaf.number,
        leaf.issue_id,
        authorization,
    )
    .await
}

async fn attach_issue(
    service: &OctocrabGitHubService,
    cancellation: &Cancellation,
    repository: &GitHubRepositoryRef,
    umbrella: u64,
    leaf_number: u64,
    leaf_id: u64,
    authorization: &LiveMutationRequest<'_>,
) -> Result<(), String> {
    let parent = service
        .parent_issue(
            cancellation,
            repository.owner(),
            repository.name(),
            leaf_number,
        )
        .await
        .map_err(|_error| "cannot check audit leaf parent relation".to_owned())?;
    if parent.is_some_and(|parent| parent.issue_number() != umbrella) {
        return Err("audit leaf already belongs to another umbrella".to_owned());
    }
    service
        .add_sub_issue(
            cancellation,
            authorization,
            SubIssueEdge {
                owner: repository.owner(),
                repo: repository.name(),
                parent_issue: umbrella,
                sub_issue_id: leaf_id,
            },
        )
        .await
        .map_err(|_error| "cannot attach audit leaf as a native sub-issue".to_owned())?;
    service
        .add_blocked_by(
            cancellation,
            authorization,
            DependencyEdge {
                owner: repository.owner(),
                repo: repository.name(),
                client_issue: umbrella,
                blocker_id: leaf_id,
                expected_updated_at: None,
                security_check: DependencySecurityCheck::SkipKeywordTriage,
            },
        )
        .await
        .map_err(|_error| "cannot attach audit leaf as an umbrella blocker".to_owned())?;
    Ok(())
}

async fn apply_dependencies(
    service: &OctocrabGitHubService,
    cancellation: &Cancellation,
    repository: &GitHubRepositoryRef,
    proposal: &AuditProposal,
    authorization: &LiveMutationRequest<'_>,
) -> Result<(), String> {
    let mut node_map = BTreeMap::new();
    for fingerprint in &proposal.expected_issues {
        let _ = node_map.insert(
            format!("existing:{}", fingerprint.number),
            (fingerprint.number, fingerprint.id),
        );
    }
    for leaf in &proposal.leaves {
        if leaf.state != AuditLeafState::Resolved {
            return Err("cannot wire an unresolved audit leaf".to_owned());
        }
        let _ = node_map.insert(
            format!("new:{}", leaf.identity),
            (leaf.number, leaf.issue_id),
        );
    }
    for dependency in &proposal.remove_dependencies {
        mutate_dependency(
            service,
            cancellation,
            repository,
            &DependencyMutation {
                node_map: &node_map,
                umbrella: proposal.umbrella,
                dependency,
                authorization,
                add: false,
            },
        )
        .await?;
    }
    for dependency in &proposal.dependencies {
        // Native attach already wires umbrella <- every direct leaf and
        // verify_parent_blockers re-proves those edges. Skipping them here
        // keeps resume idempotent on managed umbrellas that the operator-
        // facing protected-target mutator would otherwise refuse forever.
        if is_native_owned_umbrella_blocker(proposal, dependency) {
            continue;
        }
        mutate_dependency(
            service,
            cancellation,
            repository,
            &DependencyMutation {
                node_map: &node_map,
                umbrella: proposal.umbrella,
                dependency,
                authorization,
                add: true,
            },
        )
        .await?;
    }
    Ok(())
}

/// Declared edges whose dependent is the audited umbrella and whose
/// prerequisite is a direct audit leaf. The native-graph phase owns these.
fn is_native_owned_umbrella_blocker(
    proposal: &AuditProposal,
    dependency: &AuditDependency,
) -> bool {
    match &dependency.dependent {
        AuditDependencyNode::Existing { number } if *number == proposal.umbrella => {}
        _ => return false,
    }
    match &dependency.prerequisite {
        AuditDependencyNode::Existing { number } => {
            proposal.historical_leaf_numbers.contains(number)
                || proposal.direct_leaf_numbers.contains(number)
                || proposal
                    .leaves
                    .iter()
                    .any(|leaf| leaf.number == *number && leaf.state == AuditLeafState::Resolved)
        }
        AuditDependencyNode::New { identity } => proposal
            .leaves
            .iter()
            .any(|leaf| leaf.identity == *identity),
    }
}

struct DependencyMutation<'a> {
    node_map: &'a BTreeMap<String, (u64, u64)>,
    umbrella: u64,
    dependency: &'a AuditDependency,
    authorization: &'a LiveMutationRequest<'a>,
    add: bool,
}

async fn mutate_dependency(
    service: &OctocrabGitHubService,
    cancellation: &Cancellation,
    repository: &GitHubRepositoryRef,
    mutation: &DependencyMutation<'_>,
) -> Result<(), String> {
    let dependent = resolve_node(mutation.node_map, &mutation.dependency.dependent)?;
    let prerequisite = resolve_node(mutation.node_map, &mutation.dependency.prerequisite)?;
    let current = service
        .issue(repository, dependent.0, cancellation)
        .await
        .map_err(|_error| "cannot read dependency target before mutation".to_owned())?;
    if current.id != dependent.1 || current.state != GitHubIssueState::Open {
        return Err("dependency target changed before mutation".to_owned());
    }
    // Audit-internal mutations on the audited umbrella use the same trusted
    // path as attach_issue (`expected_updated_at: None`). Managed umbrellas
    // always carry lifecycle titles and larch HTML markers, so the operator-
    // facing protected-target precondition would refuse both fresh adds and
    // AlreadyInDesiredState resumes.
    let expected_updated_at = if dependent.0 == mutation.umbrella {
        None
    } else {
        Some(current.updated_at.as_str())
    };
    let edge = DependencyEdge {
        owner: repository.owner(),
        repo: repository.name(),
        client_issue: dependent.0,
        blocker_id: prerequisite.1,
        expected_updated_at,
        security_check: DependencySecurityCheck::SkipKeywordTriage,
    };
    let result = if mutation.add {
        service
            .add_blocked_by(cancellation, mutation.authorization, edge)
            .await
    } else {
        service
            .remove_blocked_by(cancellation, mutation.authorization, edge)
            .await
    };
    result.map_err(dependency_mutation_error)?;
    Ok(())
}

fn dependency_mutation_error(error: GitHubOperationError) -> String {
    match error {
        GitHubOperationError::ProtectedDependencyTarget => {
            "dependency mutation refused: protected dependency target".to_owned()
        }
        GitHubOperationError::StaleDependencyTarget => {
            "dependency mutation refused: stale dependency target".to_owned()
        }
        GitHubOperationError::SecuritySensitiveDependencyTarget => {
            "dependency mutation refused: security-sensitive dependency target".to_owned()
        }
        GitHubOperationError::Malformed(field)
            if field.contains("read-back") || field.contains("not reflected") =>
        {
            "dependency mutation was not proven by read-back".to_owned()
        }
        other => format!("dependency mutation failed: {other}"),
    }
}

fn resolve_node(
    node_map: &BTreeMap<String, (u64, u64)>,
    node: &AuditDependencyNode,
) -> Result<(u64, u64), String> {
    let key = match node {
        AuditDependencyNode::Existing { number } => format!("existing:{number}"),
        AuditDependencyNode::New { identity } => format!("new:{identity}"),
    };
    node_map
        .get(&key)
        .copied()
        .ok_or_else(|| "proposal dependency references an unbound issue".to_owned())
}

async fn verify_final_graph(
    service: &OctocrabGitHubService,
    cancellation: &Cancellation,
    repository: &GitHubRepositoryRef,
    snapshot: &AuditSnapshot,
    proposal: &AuditProposal,
    current: &BTreeMap<u64, AuditIssue>,
) -> Result<(), String> {
    let parent = service
        .issue(repository, proposal.umbrella, cancellation)
        .await
        .map_err(|_error| "cannot read umbrella during final verification".to_owned())?;
    validate_audit_parent(&parent)?;
    verify_snapshot_source_content(snapshot, current)?;
    verify_expected_fingerprints(proposal, current)?;

    let mut expected_direct = historical_direct_leaf_numbers(snapshot);
    for leaf in &proposal.leaves {
        if leaf.state != AuditLeafState::Resolved {
            return Err("final graph contains unresolved audit leaves".to_owned());
        }
        let _ = expected_direct.insert(leaf.number);
        let live = service
            .issue(repository, leaf.number, cancellation)
            .await
            .map_err(|_error| "cannot read audit leaf during final verification".to_owned())?;
        if live.id != leaf.issue_id
            || live.state != GitHubIssueState::Open
            || live.title != leaf.title
            || live.body != leaf.body
        {
            return Err("audit leaf identity changed before final verification".to_owned());
        }
        let leaf_parent = service
            .parent_issue(
                cancellation,
                repository.owner(),
                repository.name(),
                leaf.number,
            )
            .await
            .map_err(|_error| {
                "cannot read audit leaf parent during final verification".to_owned()
            })?;
        if leaf_parent.is_none_or(|relation| relation.issue_number() != proposal.umbrella) {
            return Err("audit leaf is not a direct native child of its umbrella".to_owned());
        }
    }
    let direct = service
        .list_sub_issues(
            cancellation,
            repository.owner(),
            repository.name(),
            proposal.umbrella,
        )
        .await
        .map_err(|_error| "cannot read final native sub-issue graph".to_owned())?
        .into_iter()
        .map(|reference| reference.issue_number())
        .collect::<BTreeSet<_>>();
    if direct != expected_direct {
        return Err("final native sub-issue graph differs from the persisted batch".to_owned());
    }
    verify_parent_blockers(
        service,
        cancellation,
        repository,
        proposal.umbrella,
        &expected_direct,
    )
    .await?;
    verify_proposal_dependencies(service, cancellation, repository, proposal).await?;
    verify_independent_new_roots(service, cancellation, repository, proposal).await?;
    verify_dependency_graph_is_acyclic(service, cancellation, repository, proposal).await
}

async fn verify_parent_blockers(
    service: &OctocrabGitHubService,
    cancellation: &Cancellation,
    repository: &GitHubRepositoryRef,
    umbrella: u64,
    expected_direct: &BTreeSet<u64>,
) -> Result<(), String> {
    let blockers = service
        .list_blocked_by(
            cancellation,
            repository.owner(),
            repository.name(),
            umbrella,
        )
        .await
        .map_err(|_error| "cannot read umbrella blockers".to_owned())?
        .into_iter()
        .map(|reference| reference.issue_number())
        .collect::<BTreeSet<_>>();
    if !expected_direct.is_subset(&blockers) {
        return Err("every direct audit leaf must block its umbrella".to_owned());
    }
    Ok(())
}

async fn verify_proposal_dependencies(
    service: &OctocrabGitHubService,
    cancellation: &Cancellation,
    repository: &GitHubRepositoryRef,
    proposal: &AuditProposal,
) -> Result<(), String> {
    let node_map = proposal_node_map(proposal)?;
    for (dependency, expected_present) in proposal
        .remove_dependencies
        .iter()
        .map(|edge| (edge, false))
        .chain(proposal.dependencies.iter().map(|edge| (edge, true)))
    {
        let dependent = resolve_node(&node_map, &dependency.dependent)?;
        let prerequisite = resolve_node(&node_map, &dependency.prerequisite)?;
        let blockers = service
            .list_blocked_by(
                cancellation,
                repository.owner(),
                repository.name(),
                dependent.0,
            )
            .await
            .map_err(|_error| "cannot read dependency relation after mutation".to_owned())?;
        let present = blockers
            .iter()
            .any(|blocker| blocker.issue_id() == prerequisite.1);
        if present != expected_present {
            return Err(
                "proposal dependency read-back differs from the persisted graph".to_owned(),
            );
        }
    }
    Ok(())
}

async fn verify_independent_new_roots(
    service: &OctocrabGitHubService,
    cancellation: &Cancellation,
    repository: &GitHubRepositoryRef,
    proposal: &AuditProposal,
) -> Result<(), String> {
    let dependent_new = proposal
        .dependencies
        .iter()
        .filter_map(|dependency| match &dependency.dependent {
            AuditDependencyNode::New { identity } => Some(identity.as_str()),
            AuditDependencyNode::Existing { .. } => None,
        })
        .collect::<BTreeSet<_>>();
    for leaf in &proposal.leaves {
        if leaf.state != AuditLeafState::Resolved || dependent_new.contains(leaf.identity.as_str())
        {
            continue;
        }
        let blockers = service
            .list_blocked_by(
                cancellation,
                repository.owner(),
                repository.name(),
                leaf.number,
            )
            .await
            .map_err(|_error| "cannot read an independent audit leaf's blockers".to_owned())?;
        if !blockers.is_empty() {
            return Err(
                "an intentionally independent audit leaf has an incoming blocker".to_owned(),
            );
        }
    }
    Ok(())
}

async fn verify_dependency_graph_is_acyclic(
    service: &OctocrabGitHubService,
    cancellation: &Cancellation,
    repository: &GitHubRepositoryRef,
    proposal: &AuditProposal,
) -> Result<(), String> {
    let node_map = proposal_node_map(proposal)?;
    let known = node_map
        .values()
        .map(|(number, _id)| *number)
        .collect::<BTreeSet<_>>();
    let mut graph = BTreeMap::<u64, BTreeSet<u64>>::new();
    for number in &known {
        let blockers = service
            .list_blocked_by(cancellation, repository.owner(), repository.name(), *number)
            .await
            .map_err(|_error| "cannot read dependency graph for cycle verification".to_owned())?;
        for blocker in blockers {
            if known.contains(&blocker.issue_number()) {
                let _ = graph
                    .entry(blocker.issue_number())
                    .or_default()
                    .insert(*number);
            }
        }
        let _ = graph.entry(*number).or_default();
    }
    if number_graph_has_cycle(&graph) {
        Err("final audit dependency graph contains a cycle".to_owned())
    } else {
        Ok(())
    }
}

fn proposal_node_map(proposal: &AuditProposal) -> Result<BTreeMap<String, (u64, u64)>, String> {
    let mut node_map = BTreeMap::new();
    for fingerprint in &proposal.expected_issues {
        if node_map
            .insert(
                format!("existing:{}", fingerprint.number),
                (fingerprint.number, fingerprint.id),
            )
            .is_some()
        {
            return Err("proposal has duplicate existing issue identities".to_owned());
        }
    }
    for leaf in &proposal.leaves {
        if leaf.state != AuditLeafState::Resolved
            || node_map
                .insert(
                    format!("new:{}", leaf.identity),
                    (leaf.number, leaf.issue_id),
                )
                .is_some()
        {
            return Err("proposal has invalid resolved audit leaf identities".to_owned());
        }
    }
    Ok(node_map)
}

fn number_graph_has_cycle(graph: &BTreeMap<u64, BTreeSet<u64>>) -> bool {
    let mut visiting = BTreeSet::new();
    let mut visited = BTreeSet::new();
    graph
        .keys()
        .any(|number| number_graph_cycle_at(*number, graph, &mut visiting, &mut visited))
}

fn number_graph_cycle_at(
    number: u64,
    graph: &BTreeMap<u64, BTreeSet<u64>>,
    visiting: &mut BTreeSet<u64>,
    visited: &mut BTreeSet<u64>,
) -> bool {
    if visited.contains(&number) {
        return false;
    }
    if !visiting.insert(number) {
        return true;
    }
    let cycle = graph.get(&number).is_some_and(|children| {
        children
            .iter()
            .any(|child| number_graph_cycle_at(*child, graph, visiting, visited))
    });
    let _ = visiting.remove(&number);
    let _ = visited.insert(number);
    cycle
}

fn native_leaf_numbers(snapshot: &AuditSnapshot) -> BTreeSet<u64> {
    snapshot
        .sources
        .iter()
        .filter(|source| source.roles.iter().any(|role| role == "native"))
        .map(|source| source.issue.number)
        .collect()
}

fn historical_direct_leaf_numbers(snapshot: &AuditSnapshot) -> BTreeSet<u64> {
    snapshot.historical_leaf_numbers.iter().copied().collect()
}

fn fingerprints(issues: &BTreeMap<u64, AuditIssue>) -> Vec<AuditIssueFingerprint> {
    issues.values().map(audit_issue_fingerprint).collect()
}

fn verify_snapshot_sources_fresh(
    snapshot: &AuditSnapshot,
    current: &BTreeMap<u64, AuditIssue>,
) -> Result<(), String> {
    for source in &snapshot.sources {
        let Some(live) = current.get(&source.issue.number) else {
            return Err("an audit source is no longer available".to_owned());
        };
        if audit_issue_fingerprint(live) != audit_issue_fingerprint(&source.issue) {
            return Err("an audit source changed after the snapshot".to_owned());
        }
    }
    Ok(())
}

fn verify_snapshot_source_content(
    snapshot: &AuditSnapshot,
    current: &BTreeMap<u64, AuditIssue>,
) -> Result<(), String> {
    for source in &snapshot.sources {
        let Some(live) = current.get(&source.issue.number) else {
            return Err("an audit source is no longer available".to_owned());
        };
        if live.id != source.issue.id
            || live.title != source.issue.title
            || live.body != source.issue.body
            || live.state != source.issue.state
        {
            return Err("an audit source content changed during mutation".to_owned());
        }
    }
    Ok(())
}

fn verify_expected_fingerprints(
    proposal: &AuditProposal,
    current: &BTreeMap<u64, AuditIssue>,
) -> Result<(), String> {
    if proposal.expected_issues == fingerprints(current) {
        Ok(())
    } else {
        Err("an audit-bound issue changed after proposal persistence".to_owned())
    }
}

fn parse_proposal_draft(text: &str) -> Result<AuditProposalDraft, String> {
    larch_core::OrderedJson::parse_unique(text)
        .map_err(|_error| "proposal input must be strict JSON without duplicate keys".to_owned())?;
    serde_json::from_str(text).map_err(|_error| "proposal input has an invalid shape".to_owned())
}

fn read_snapshot(
    path: &Path,
    supplied_root: &Path,
    root: &TemporaryRoot,
) -> Result<AuditSnapshot, String> {
    let text = read_expected_file(path, supplied_root, root, "--snapshot", FILE_LIMIT)?;
    parse_audit_snapshot(&text).map_err(|error| error.reason().to_owned())
}

fn read_ledger(
    path: &Path,
    supplied_root: &Path,
    root: &TemporaryRoot,
) -> Result<AuditLedger, String> {
    let text = read_expected_file(path, supplied_root, root, "--ledger", FILE_LIMIT)?;
    parse_audit_ledger(&text).map_err(|error| error.reason().to_owned())
}

fn read_proposal(
    path: &Path,
    supplied_root: &Path,
    root: &TemporaryRoot,
) -> Result<AuditProposal, String> {
    let text = read_expected_file(path, supplied_root, root, "--proposal", FILE_LIMIT)?;
    parse_audit_proposal(&text).map_err(|error| error.reason().to_owned())
}

fn write_proposal(
    path: &Path,
    supplied_root: &Path,
    root: &TemporaryRoot,
    proposal: &AuditProposal,
) -> Result<(), String> {
    let text = render_audit_proposal(proposal).map_err(|error| error.reason().to_owned())?;
    write_private_file(path, &text, supplied_root, root)
}

fn require_operator(operator_invoked: bool) -> Result<(), String> {
    if operator_invoked {
        Ok(())
    } else {
        Err("--operator-invoked is required for live GitHub mutation".to_owned())
    }
}

const fn operator_authorization() -> LiveMutationRequest<'static> {
    LiveMutationRequest {
        context_file: None,
        operator_mode: true,
        run_id: "",
        trusted_root: None,
        test_deny: false,
    }
}

fn require_issue(issue: u64, option: &str) -> Result<(), String> {
    if issue == 0 {
        Err(format!("{option} must be a positive integer"))
    } else {
        Ok(())
    }
}

fn parse_umbrella_argument(value: &str) -> Result<u64, String> {
    let number = value.strip_prefix('#').unwrap_or(value);
    if number.is_empty() || !number.bytes().all(|byte| byte.is_ascii_digit()) {
        return Err("expected exactly one positive umbrella issue number".to_owned());
    }
    let issue = number
        .parse::<u64>()
        .map_err(|_error| "expected exactly one positive umbrella issue number".to_owned())?;
    if issue == 0 {
        Err("expected exactly one positive umbrella issue number".to_owned())
    } else {
        Ok(issue)
    }
}

fn parse_repository(value: &str) -> Result<GitHubRepositoryRef, String> {
    repository_ref(value).map_err(|()| "--repository must use valid OWNER/REPO form".to_owned())
}

/// The snapshot artifact must never be written inside the detached worktree.
///
/// Both paths are model-facing command inputs, so containment beneath the same
/// session root alone is not enough: an overlapping file would turn an audit
/// artifact write into a source-tree edit.
fn ensure_snapshot_paths_are_disjoint(
    output: &Path,
    worktree: &Path,
    supplied_root: &Path,
    root: &TemporaryRoot,
) -> Result<(), String> {
    let output = confine_session_path(output, supplied_root, root, PathIntent::Write, "--output")?;
    let worktree = confine_session_path(
        worktree,
        supplied_root,
        root,
        PathIntent::Write,
        "--worktree",
    )?;
    if paths_overlap(output.path(), worktree.path()) {
        return Err("--output and --worktree must not overlap".to_owned());
    }
    Ok(())
}

fn paths_overlap(left: &Path, right: &Path) -> bool {
    left.starts_with(right) || right.starts_with(left)
}

fn fetch_default_sha(repo_root: &Path, default_branch: &str) -> Result<String, String> {
    let remote = GitRemote::new("origin").map_err(|error| error.to_string())?;
    let refspec = GitRefspec::new(format!(
        "refs/heads/{default_branch}:refs/remotes/origin/{default_branch}"
    ))
    .map_err(|error| error.to_string())?;
    let runtime = GitCommandRuntime::for_repository(repo_root)?;
    runtime
        .runtime
        .block_on(async {
            runtime
                .git_cli()
                .fetch(
                    FetchRequest {
                        remote,
                        refspec: Some(refspec),
                        quiet: true,
                        no_tags: true,
                        mode: larch_adapters::FetchMode::Standard,
                    },
                    &runtime.cancellation,
                )
                .await
        })
        .map_err(|_error| "cannot fetch the default branch".to_owned())?;
    let repository = GixRepository::open(repo_root)
        .map_err(|_error| "cannot open repository after default-branch fetch".to_owned())?;
    let revision = Revision::new(format!("origin/{default_branch}"));
    let sha = repository
        .resolve_revision(&revision)
        .map_err(|_error| "cannot resolve fetched default branch".to_owned())?
        .to_hex();
    if !matches!(sha.len(), 40 | 64)
        || !sha
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
    {
        return Err("fetched default branch has an invalid object identity".to_owned());
    }
    Ok(sha)
}

fn resolve_object_id(repo_root: &Path, revision: &str) -> Result<larch_core::ObjectId, String> {
    let repository = GixRepository::open(repo_root)
        .map_err(|_error| "cannot open repository after default-branch fetch".to_owned())?;
    repository
        .resolve_revision(&Revision::new(revision))
        .map_err(|_error| "cannot resolve fetched default branch object".to_owned())
}

fn create_detached_worktree(
    repo_root: &Path,
    root: &TemporaryRoot,
    supplied_root: &Path,
    worktree: &Path,
    audited_sha: &str,
) -> Result<(), String> {
    let confined = confine_session_path(
        worktree,
        supplied_root,
        root,
        PathIntent::Write,
        "--worktree",
    )?;
    let path = confined.path().to_path_buf();
    if fs::symlink_metadata(&path).is_ok() {
        return Err("--worktree already exists".to_owned());
    }
    let worktree = WorktreePath::new(path).map_err(|error| error.to_string())?;
    let start_point = GitRef::new(audited_sha).map_err(|error| error.to_string())?;
    run_worktree_request(
        repo_root,
        WorktreeRequest::Add {
            branch: None,
            detach: true,
            path: worktree,
            start_point: Some(start_point),
        },
    )
}

fn run_worktree_request(repo_root: &Path, request: WorktreeRequest) -> Result<(), String> {
    let runtime = GitCommandRuntime::for_repository(repo_root)?;
    runtime
        .runtime
        .block_on(async {
            runtime
                .git_cli()
                .worktree(request, &runtime.cancellation)
                .await
        })
        .map(|_result| ())
        .map_err(|_error| "detached audit worktree operation failed".to_owned())
}

#[cfg(test)]
mod tests {
    use super::{
        ApplyArguments, ApplyContext, AuditBaselineAction, AuditUmbrellaCommand,
        LeafIdentityArguments, ParseArguments, PersistProposalArguments, RemoveWorktreeArguments,
        SnapshotArguments, SnapshotSelection, ValidateLedgerArguments, apply_dependencies,
        apply_remote, audit_baseline_action, audit_issue, build_snapshot, collect_snapshot_remote,
        count_open_duplicate_leaves, dependency_mutation_error, exact_open_leaf_matches,
        explicit_leaf_references, fingerprints, has_exact_leaf_title,
        historical_direct_leaf_numbers, is_controlling_umbrella, is_legacy_managed_umbrella,
        is_native_owned_umbrella_blocker, issue_references, native_leaf_numbers,
        number_graph_has_cycle, operator_authorization, parse_proposal_draft, parse_repository,
        parse_umbrella_argument, paths_overlap, persist_refreshed_proposal, prepare_remote_apply,
        proposal_node_map, proposal_violation_diagnostic, reconcile_audit_leaves,
        reconcile_leaf_relationships, require_issue, require_operator, resolve_node, run,
        temporary_root, validate_audit_parent, verify_expected_fingerprints, verify_final_graph,
        verify_snapshot_source_content, verify_snapshot_sources_fresh,
    };
    use larch_adapters::{
        github::{GitHubOperationError, OctocrabGitHubService},
        runtime::Cancellation,
    };
    use larch_core::{
        AUDIT_LEDGER_VERSION, AUDIT_PROPOSAL_VERSION, AuditDependency, AuditDependencyNode,
        AuditGraphState, AuditIssue, AuditLeaf, AuditLeafDraft, AuditLeafState, AuditLedger,
        AuditLedgerEntry, AuditLedgerViolation, AuditProposal, AuditProposalDraft,
        AuditProposalViolation, AuditSnapshot, GitHubIssue, GitHubIssueState, GitHubLabel,
        GitHubRepositoryRef, RequirementStatus, audit_issue_fingerprint, audit_leaf_identity,
        audit_snapshot_sha256, audit_source_items, build_audit_proposal,
        mark_audit_graph_in_flight, mark_audit_leaf_in_flight, mark_audit_proposal_complete,
        record_audit_leaf_resolved, umbrella_leaf_opening,
    };
    use larch_test_support::{
        GitFixture, GitFixtureError, GitRepository, HttpResponseBuilder, IssueServiceExchange,
        IssueServiceStub,
    };
    use serde_json::{Value, json};
    use std::{
        collections::{BTreeMap, BTreeSet},
        path::{Path, PathBuf},
        process::ExitCode,
    };

    fn issue(number: u64, title: &str, body: &str, state: GitHubIssueState) -> GitHubIssue {
        GitHubIssue {
            id: number + 100,
            number,
            title: title.to_owned(),
            body: body.to_owned(),
            state,
            state_reason: String::new(),
            url: format!("https://github.com/o/r/issues/{number}"),
            author: "octo".to_owned(),
            assignees: Vec::new(),
            labels: Vec::<GitHubLabel>::new(),
            comments: 0,
            created_at: "2026-08-01T00:00:00Z".to_owned(),
            closed_at: String::new(),
            updated_at: "2026-08-11T00:00:00Z".to_owned(),
            is_pull_request: false,
        }
    }

    fn pending_proposal(title: &str, body: &str) -> AuditProposal {
        let parent = AuditIssue {
            number: 10,
            id: 110,
            title: "[UMBRELLA] Fixture".to_owned(),
            body: "#### Leaf issues\n\n- #11\n".to_owned(),
            state: "open".to_owned(),
            updated_at: "2026-08-11T00:00:00Z".to_owned(),
            url: "https://github.com/o/r/issues/10".to_owned(),
        };
        AuditProposal {
            version: AUDIT_PROPOSAL_VERSION,
            repository: "o/r".to_owned(),
            umbrella: 10,
            audited_sha: "a".repeat(40),
            snapshot_sha256: "b".repeat(64),
            ledger_sha256: "c".repeat(64),
            historical_leaf_numbers: Vec::new(),
            direct_leaf_numbers: Vec::new(),
            expected_issues: vec![audit_issue_fingerprint(&parent)],
            leaves: vec![AuditLeaf {
                identity: audit_leaf_identity(title, body),
                title: title.to_owned(),
                body: body.to_owned(),
                gap_ids: vec!["R-1".to_owned()],
                state: AuditLeafState::Pending,
                number: 0,
                issue_id: 0,
                url: String::new(),
            }],
            dependencies: Vec::new(),
            remove_dependencies: Vec::new(),
            graph_state: AuditGraphState::Pending,
            complete: false,
        }
    }

    fn audit_snapshot() -> AuditSnapshot {
        let parent = issue(
            10,
            "[UMBRELLA] Fixture",
            "<!-- larch:umbrella-proposal v1 -->\n\n#### Leaf issues\n\n- #11\n\nRead #12 for program context.\n",
            GitHubIssueState::Open,
        );
        let mut issues = BTreeMap::new();
        let _ = issues.insert(parent.number, parent.clone());
        let _ = issues.insert(
            11,
            issue(
                11,
                "[LEAF OF 10] Existing leaf",
                &format!("{}\n\nExisting scope.\n", umbrella_leaf_opening(10)),
                GitHubIssueState::Open,
            ),
        );
        let _ = issues.insert(
            12,
            issue(
                12,
                "[CHIEF UMBRELLA] Program context",
                "## Program requirements\n\n- Preserve the contract.\n",
                GitHubIssueState::Open,
            ),
        );
        let repository = GitHubRepositoryRef::new("o", "r").expect("repository");
        let direct = BTreeSet::from([11]);
        let explicit = explicit_leaf_references(&parent.body);
        let referenced = issue_references(&parent.body);
        build_snapshot(SnapshotSelection {
            repository: &repository,
            default_branch: "main",
            audited_sha: &"a".repeat(40),
            parent: &parent,
            issues: &issues,
            direct_numbers: &direct,
            explicit_numbers: &explicit,
            referenced_numbers: &referenced,
        })
        .expect("audit snapshot")
    }

    fn current_snapshot_sources(snapshot: &AuditSnapshot) -> BTreeMap<u64, AuditIssue> {
        snapshot
            .sources
            .iter()
            .map(|source| (source.issue.number, source.issue.clone()))
            .collect()
    }

    fn repository() -> GitHubRepositoryRef {
        GitHubRepositoryRef::new("o", "r").expect("repository")
    }

    fn service(exchanges: Vec<IssueServiceExchange>) -> (OctocrabGitHubService, IssueServiceStub) {
        let server = IssueServiceStub::start(exchanges).expect("start issue service stub");
        let service = OctocrabGitHubService::with_test_base(server.base_url());
        (service, server)
    }

    fn response(status: u16, body: impl AsRef<[u8]>) -> IssueServiceExchange {
        IssueServiceExchange::any_json(status, body.as_ref().to_vec())
            .expect("valid issue service response")
    }

    fn paginated_response(
        status: u16,
        body: impl AsRef<[u8]>,
        continuation: &str,
    ) -> IssueServiceExchange {
        let response = HttpResponseBuilder::new(status)
            .header("content-type", "application/json")
            .expect("content type")
            .header("link", &format!("<{continuation}>; rel=\"next\""))
            .expect("pagination link")
            .body(body.as_ref().to_vec())
            .build()
            .expect("valid paginated response");
        IssueServiceExchange::any(response)
    }

    fn issue_json(number: u64, id: u64, title: &str, body: &str, state: &str) -> String {
        issue_json_at(number, id, title, body, state, "2026-08-11T00:00:00Z")
    }

    fn issue_json_at(
        number: u64,
        id: u64,
        title: &str,
        body: &str,
        state: &str,
        updated_at: &str,
    ) -> String {
        let mut issue: Value = serde_json::from_str(include_str!(
            "../../larch-adapters/fixtures/github_issue.json"
        ))
        .expect("valid issue fixture");
        issue["id"] = json!(id);
        issue["number"] = json!(number);
        issue["title"] = json!(title);
        issue["body"] = json!(body);
        issue["state"] = json!(state);
        issue["url"] = json!(format!("https://example.invalid/repos/o/r/issues/{number}"));
        issue["html_url"] = json!(format!("https://github.com/o/r/issues/{number}"));
        issue["labels"] = json!([]);
        issue["updated_at"] = json!(updated_at);
        issue.to_string()
    }

    fn repository_json(default_branch: &str) -> String {
        json!({
            "id": 1,
            "name": "r",
            "full_name": "o/r",
            "private": false,
            "html_url": "https://github.com/o/r",
            "url": "https://example.invalid/repos/o/r",
            "default_branch": default_branch,
        })
        .to_string()
    }

    fn refs(values: &[(u64, u64, &str)]) -> String {
        Value::Array(
            values
                .iter()
                .map(|(number, id, state)| json!({ "number": number, "id": id, "state": state }))
                .collect(),
        )
        .to_string()
    }

    fn remote_parent() -> String {
        issue_json(
            10,
            110,
            "[UMBRELLA] Fixture",
            "<!-- larch:umbrella-proposal v1 -->\n\n#### Leaf issues\n\n- #11\n\nRead #12 for program context.\n",
            "open",
        )
    }

    fn remote_leaf() -> String {
        remote_leaf_at("2026-08-11T00:00:00Z")
    }

    fn remote_leaf_at(updated_at: &str) -> String {
        issue_json_at(
            11,
            111,
            "[LEAF OF 10] Existing leaf",
            &format!("{}\n\nExisting scope.\n", umbrella_leaf_opening(10)),
            "open",
            updated_at,
        )
    }

    fn remote_control() -> String {
        issue_json(
            12,
            112,
            "[CHIEF UMBRELLA] Program context",
            "## Program requirements\n\n- Preserve the contract.\n",
            "open",
        )
    }

    fn snapshot_exchanges(parent: &str, leaf: &str, control: &str) -> Vec<IssueServiceExchange> {
        vec![
            response(200, repository_json("main")),
            response(200, parent),
            response(200, refs(&[(11, 111, "open")])),
            response(200, format!("[{parent},{leaf},{control}]")),
        ]
    }

    fn gap_ledger(snapshot: &AuditSnapshot) -> AuditLedger {
        AuditLedger {
            version: AUDIT_LEDGER_VERSION,
            snapshot_sha256: audit_snapshot_sha256(snapshot),
            entries: audit_source_items(snapshot)
                .into_iter()
                .enumerate()
                .map(|(index, item)| AuditLedgerEntry {
                    id: format!("R-{:04}", index + 1),
                    source_id: item.id,
                    requirement: "Account for the immutable source item".to_owned(),
                    status: RequirementStatus::Gap,
                    code_evidence: vec!["src/lib.rs:1".to_owned()],
                    test_evidence: vec!["tests/audit.rs:1".to_owned()],
                    reason: String::new(),
                })
                .collect(),
        }
    }

    fn satisfied_ledger(snapshot: &AuditSnapshot) -> AuditLedger {
        let mut ledger = gap_ledger(snapshot);
        for entry in &mut ledger.entries {
            entry.status = RequirementStatus::Satisfied;
        }
        ledger
    }

    fn gap_proposal(snapshot: &AuditSnapshot, ledger: &AuditLedger) -> AuditProposal {
        let body = format!(
            "{}\n\n## Program context\n\nEvidence at {}.\n\n## Problem\n\nA gap remains.\n\n## Scope\n\n1. Repair the audited boundary.\n\n## Acceptance\n\n- The audit gap is covered.\n",
            umbrella_leaf_opening(snapshot.umbrella.number),
            snapshot.audited_sha,
        );
        let draft = AuditProposalDraft {
            version: AUDIT_PROPOSAL_VERSION,
            leaves: vec![AuditLeafDraft {
                title: format!(
                    "[LEAF OF {}] Repair the audit gap",
                    snapshot.umbrella.number
                ),
                body,
                gap_ids: ledger
                    .entries
                    .iter()
                    .map(|entry| entry.id.clone())
                    .collect(),
            }],
            dependencies: Vec::new(),
            remove_dependencies: Vec::new(),
        };
        build_audit_proposal(snapshot, ledger, &draft).expect("gap proposal")
    }

    fn complete_proposal(snapshot: &AuditSnapshot, ledger: &AuditLedger) -> AuditProposal {
        let draft = AuditProposalDraft {
            version: AUDIT_PROPOSAL_VERSION,
            leaves: Vec::new(),
            dependencies: Vec::new(),
            remove_dependencies: Vec::new(),
        };
        let mut proposal = build_audit_proposal(snapshot, ledger, &draft).expect("proposal");
        mark_audit_graph_in_flight(&mut proposal).expect("graph in flight");
        mark_audit_proposal_complete(&mut proposal).expect("complete proposal");
        proposal
    }

    #[test]
    fn historical_discovery_accepts_only_the_exact_leaf_prefix() {
        assert!(has_exact_leaf_title("[LEAF OF 72] Fix the gap", 72));
        assert!(has_exact_leaf_title(
            "[IMPLEMENTING] [LEAF OF 72] Fix the gap",
            72
        ));
        assert!(!has_exact_leaf_title("[LEAF OF #72] Fix the gap", 72));
        assert!(!has_exact_leaf_title("[LEAF OF 720] Fix the gap", 72));
    }

    #[test]
    fn explicit_reference_scan_rejects_zero_and_embedded_words() {
        assert_eq!(
            issue_references("#2, #003, thing#4 and #0"),
            BTreeSet::from([2, 3])
        );
    }

    #[test]
    fn leaf_section_accepts_a_plain_issue_reference_without_confusing_it_for_a_heading() {
        assert_eq!(
            explicit_leaf_references("## Leaf issues\n\n#12\n\n## Context\n#13\n"),
            BTreeSet::from([12])
        );
    }

    #[test]
    fn title_only_umbrella_is_not_a_managed_audit_target() {
        let parent = issue(
            10,
            "[UMBRELLA] Ordinary tracking issue",
            "This issue has no durable managed-umbrella identity.",
            GitHubIssueState::Open,
        );
        assert!(validate_audit_parent(&parent).is_err());
    }

    #[test]
    fn pull_requests_cannot_enter_an_audit_snapshot() {
        let mut pull_request = issue(
            10,
            "[LEAF OF 9] Pull request",
            "This is a leaf of umbrella #9. Read the umbrella in full before acting.",
            GitHubIssueState::Open,
        );
        pull_request.is_pull_request = true;
        assert!(audit_issue(&pull_request).is_err());
    }

    #[test]
    fn exact_open_duplicates_are_detected_without_suppressing_distinct_scope() {
        let existing = issue(
            11,
            "[LEAF OF 10] Repair the audit gap",
            "exact corrective scope",
            GitHubIssueState::Open,
        );
        assert_eq!(
            exact_open_leaf_matches(
                "[LEAF OF 10] Repair the audit gap",
                "exact corrective scope",
                std::slice::from_ref(&existing),
            )
            .len(),
            1
        );
        assert!(
            exact_open_leaf_matches(
                "[LEAF OF 10] Repair the audit gap",
                "remaining distinct scope",
                &[existing],
            )
            .is_empty()
        );
    }

    #[test]
    fn persist_counts_exact_open_leaf_without_advancing_transaction_state() {
        let title = "[LEAF OF 10] Repair the audit gap";
        let body = format!(
            "This is a leaf of umbrella #10. Read the umbrella in full before acting.\n\n## Program context\n\nEvidence at {}.\n\n## Problem\n\nThe boundary is uncovered.\n\n## Scope\n\n1. Repair the boundary.\n\n## Acceptance\n\n- The boundary is covered.\n",
            "a".repeat(40)
        );
        let proposal = pending_proposal(title, &body);
        let existing = issue(11, title, &body, GitHubIssueState::Open);

        assert_eq!(
            count_open_duplicate_leaves(&proposal, &[existing]).expect("exact reuse candidate"),
            1
        );
        assert_eq!(proposal.leaves[0].state, AuditLeafState::Pending);
        assert_eq!(proposal.leaves[0].number, 0);
        assert_eq!(proposal.leaves[0].issue_id, 0);
        assert_eq!(
            audit_baseline_action(&audit_snapshot(), &proposal, &"b".repeat(40)),
            Ok(AuditBaselineAction::Rebaseline)
        );
    }

    #[test]
    fn snapshot_artifact_cannot_overlap_the_detached_worktree() {
        assert!(paths_overlap(
            Path::new("/tmp/session/worktree"),
            Path::new("/tmp/session/worktree/snapshot.json"),
        ));
        assert!(!paths_overlap(
            Path::new("/tmp/session/snapshot.json"),
            Path::new("/tmp/session/worktree"),
        ));
    }

    #[test]
    fn explicit_leaf_rows_exclude_generic_references_and_include_legacy_context() {
        let parent = issue(
            10,
            "[UMBRELLA] Fixture",
            "Read #90 before working.\n\n#### Leaf issues\n\n- [ ] #11, closed leaf\n- #12, legacy leaf\n\nIssue #91 is only background context.\n",
            GitHubIssueState::Open,
        );
        assert!(validate_audit_parent(&parent).is_ok());
        assert_eq!(
            explicit_leaf_references(&parent.body),
            BTreeSet::from([11, 12])
        );
        let direct = BTreeSet::from([11]);
        let mut by_number = std::collections::BTreeMap::new();
        let _ = by_number.insert(parent.number, parent.clone());
        let _ = by_number.insert(
            11,
            issue(
                11,
                "[DONE] [LEAF OF 10] Closed fixture leaf",
                "closed leaf requirements\n",
                GitHubIssueState::Closed,
            ),
        );
        let _ = by_number.insert(
            12,
            issue(
                12,
                "Historical fixture leaf",
                "This is a leaf of umbrella #10. Read the umbrella in full before acting.\nlegacy requirements\n",
                GitHubIssueState::Closed,
            ),
        );
        let _ = by_number.insert(
            90,
            issue(
                90,
                "[CHIEF UMBRELLA] Fixture program",
                "#### Program requirements\n\n- preserve the durable wire contract\n",
                GitHubIssueState::Open,
            ),
        );
        let _ = by_number.insert(
            91,
            issue(
                91,
                "[BUG] Background",
                "not an audit leaf\n",
                GitHubIssueState::Closed,
            ),
        );
        let repository = GitHubRepositoryRef::new("o", "r").expect("repository");
        let audited_sha = "a".repeat(40);
        let explicit = explicit_leaf_references(&parent.body);
        let referenced = issue_references(&parent.body);
        let snapshot = build_snapshot(SnapshotSelection {
            repository: &repository,
            default_branch: "main",
            audited_sha: &audited_sha,
            parent: &parent,
            issues: &by_number,
            direct_numbers: &direct,
            explicit_numbers: &explicit,
            referenced_numbers: &referenced,
        })
        .expect("snapshot");

        assert_eq!(snapshot.historical_leaf_numbers, vec![11, 12]);
        assert!(
            snapshot
                .sources
                .iter()
                .any(|source| source.id == "control:90")
        );
        assert!(
            !snapshot
                .sources
                .iter()
                .any(|source| source.issue.number == 91)
        );
    }

    #[test]
    fn public_argument_accepts_one_positive_number_and_optional_hash() {
        assert_eq!(parse_umbrella_argument("72"), Ok(72));
        assert_eq!(parse_umbrella_argument("#72"), Ok(72));
        assert!(parse_umbrella_argument("72 extra").is_err());
        assert!(parse_umbrella_argument("#0").is_err());
        assert!(parse_umbrella_argument("#-72").is_err());
    }

    #[test]
    fn command_dispatch_rejects_each_untrusted_input_before_remote_work() {
        assert_eq!(
            run(AuditUmbrellaCommand::Parse(ParseArguments {
                arguments: "not-an-issue".to_owned(),
            })),
            ExitCode::FAILURE
        );
        assert_eq!(
            run(AuditUmbrellaCommand::LeafIdentity(LeafIdentityArguments {
                root: PathBuf::from("relative"),
                title: PathBuf::from("title"),
                body: PathBuf::from("body"),
            })),
            ExitCode::FAILURE
        );
        assert_eq!(
            run(AuditUmbrellaCommand::Snapshot(SnapshotArguments {
                repository: "o/r".to_owned(),
                issue: 0,
                repo_root: PathBuf::from("missing"),
                output_root: PathBuf::from("relative"),
                output: PathBuf::from("snapshot.json"),
                worktree: PathBuf::from("worktree"),
            })),
            ExitCode::FAILURE
        );
        assert_eq!(
            run(AuditUmbrellaCommand::ValidateLedger(
                ValidateLedgerArguments {
                    root: PathBuf::from("relative"),
                    snapshot: PathBuf::from("snapshot.json"),
                    ledger: PathBuf::from("ledger.json"),
                }
            )),
            ExitCode::FAILURE
        );
        assert_eq!(
            run(AuditUmbrellaCommand::PersistProposal(
                PersistProposalArguments {
                    repository: "not/a/valid/repository".to_owned(),
                    repo_root: PathBuf::from("missing"),
                    root: PathBuf::from("relative"),
                    snapshot: PathBuf::from("snapshot.json"),
                    ledger: PathBuf::from("ledger.json"),
                    proposal_input: PathBuf::from("draft.json"),
                    proposal: PathBuf::from("proposal.json"),
                }
            )),
            ExitCode::FAILURE
        );
        assert_eq!(
            run(AuditUmbrellaCommand::Apply(ApplyArguments {
                repository: "o/r".to_owned(),
                repo_root: PathBuf::from("missing"),
                root: PathBuf::from("relative"),
                snapshot: PathBuf::from("snapshot.json"),
                ledger: PathBuf::from("ledger.json"),
                proposal: PathBuf::from("proposal.json"),
                operator_invoked: false,
            })),
            ExitCode::FAILURE
        );
        assert_eq!(
            run(AuditUmbrellaCommand::RemoveWorktree(
                RemoveWorktreeArguments {
                    repo_root: PathBuf::from("missing"),
                    root: PathBuf::from("relative"),
                    worktree: PathBuf::from("worktree"),
                }
            )),
            ExitCode::FAILURE
        );
    }

    #[test]
    fn managed_parent_and_source_helpers_fail_closed() {
        let managed = issue(
            10,
            "[IMPLEMENTING] [UMBRELLA] Fixture",
            "<!-- larch:umbrella-proposal v1 -->",
            GitHubIssueState::Open,
        );
        assert!(validate_audit_parent(&managed).is_ok());
        assert!(is_controlling_umbrella(&managed));
        assert!(is_controlling_umbrella(&issue(
            12,
            "[DONE] [CHIEF UMBRELLA] Program",
            "context",
            GitHubIssueState::Open,
        )));
        assert!(is_legacy_managed_umbrella("## Leaf issues\n\n- #11\n"));
        assert!(!is_legacy_managed_umbrella("## Context\n\n- #11\n"));

        let mut closed = managed.clone();
        closed.state = GitHubIssueState::Closed;
        assert!(validate_audit_parent(&closed).is_err());
        let mut pull_request = managed.clone();
        pull_request.is_pull_request = true;
        assert!(validate_audit_parent(&pull_request).is_err());
        let mut security_terms = issue(
            10,
            "[UMBRELLA] Vulnerability audit",
            "<!-- larch:umbrella-proposal v1 -->\n\nPreserve secret-scrub guarantees.",
            GitHubIssueState::Open,
        );
        security_terms.labels.push(GitHubLabel {
            id: 1,
            name: "security".to_owned(),
            color: "000000".to_owned(),
            description: "Security-related work".to_owned(),
        });
        assert!(validate_audit_parent(&security_terms).is_ok());

        assert!(parse_repository("owner/repository").is_ok());
        assert!(parse_repository("owner/repository/extra").is_err());
        assert!(require_issue(1, "--issue").is_ok());
        assert!(require_issue(0, "--issue").is_err());
        assert!(require_operator(true).is_ok());
        assert!(require_operator(false).is_err());
        let mut unconstrained = managed;
        unconstrained.state = GitHubIssueState::All;
        assert!(audit_issue(&unconstrained).is_err());
    }

    #[test]
    fn persisted_snapshot_helpers_detect_freshness_and_content_changes() {
        let snapshot = audit_snapshot();
        let current = current_snapshot_sources(&snapshot);
        assert!(verify_snapshot_sources_fresh(&snapshot, &current).is_ok());
        assert!(verify_snapshot_source_content(&snapshot, &current).is_ok());
        assert_eq!(native_leaf_numbers(&snapshot), BTreeSet::from([11]));
        assert_eq!(
            historical_direct_leaf_numbers(&snapshot),
            BTreeSet::from([11])
        );

        let mut missing = current.clone();
        let _ = missing.remove(&11);
        assert!(verify_snapshot_sources_fresh(&snapshot, &missing).is_err());
        assert!(verify_snapshot_source_content(&snapshot, &missing).is_err());

        let mut changed = current.clone();
        changed
            .get_mut(&11)
            .expect("source")
            .title
            .push_str(" changed");
        assert!(verify_snapshot_sources_fresh(&snapshot, &changed).is_err());
        assert!(verify_snapshot_source_content(&snapshot, &changed).is_err());

        let mut proposal = pending_proposal(
            "[LEAF OF 10] Repair the audit gap",
            &format!("{}\n\nScope.\n", umbrella_leaf_opening(10)),
        );
        proposal.expected_issues = fingerprints(&current);
        assert!(verify_expected_fingerprints(&proposal, &current).is_ok());
        assert!(verify_expected_fingerprints(&proposal, &changed).is_err());
    }

    #[test]
    fn proposal_graph_helpers_require_resolved_unique_nodes() {
        let body = format!("{}\n\nScope.\n", umbrella_leaf_opening(10));
        let mut proposal = pending_proposal("[LEAF OF 10] Repair the audit gap", &body);
        assert!(proposal_node_map(&proposal).is_err());
        proposal.leaves[0].state = AuditLeafState::Resolved;
        proposal.leaves[0].number = 13;
        proposal.leaves[0].issue_id = 113;
        proposal.leaves[0].url = "https://github.com/o/r/issues/13".to_owned();
        let nodes = proposal_node_map(&proposal).expect("resolved nodes");
        assert_eq!(
            resolve_node(
                &nodes,
                &larch_core::AuditDependencyNode::Existing { number: 10 }
            ),
            Ok((10, 110))
        );
        assert_eq!(
            resolve_node(
                &nodes,
                &larch_core::AuditDependencyNode::New {
                    identity: proposal.leaves[0].identity.clone(),
                },
            ),
            Ok((13, 113))
        );
        assert!(
            resolve_node(
                &nodes,
                &larch_core::AuditDependencyNode::Existing { number: 999 }
            )
            .is_err()
        );

        let mut duplicate = proposal.clone();
        duplicate
            .expected_issues
            .push(duplicate.expected_issues[0].clone());
        assert!(proposal_node_map(&duplicate).is_err());

        let acyclic = BTreeMap::from([
            (1, BTreeSet::from([2])),
            (2, BTreeSet::from([3])),
            (3, BTreeSet::new()),
        ]);
        assert!(!number_graph_has_cycle(&acyclic));
        let cyclic = BTreeMap::from([(1, BTreeSet::from([2])), (2, BTreeSet::from([1]))]);
        assert!(number_graph_has_cycle(&cyclic));
    }

    #[test]
    fn proposal_draft_parser_rejects_duplicate_and_malformed_json() {
        let draft = AuditProposalDraft {
            version: AUDIT_PROPOSAL_VERSION,
            leaves: vec![AuditLeafDraft {
                title: "[LEAF OF 10] Repair the audit gap".to_owned(),
                body: format!("{}\n\nScope.\n", umbrella_leaf_opening(10)),
                gap_ids: vec!["R-1".to_owned()],
            }],
            dependencies: Vec::new(),
            remove_dependencies: Vec::new(),
        };
        let text = serde_json::to_string(&draft).expect("serialize draft");
        assert_eq!(parse_proposal_draft(&text), Ok(draft));
        assert!(parse_proposal_draft(r#"{"version":1,"version":1}"#).is_err());
        assert!(parse_proposal_draft("not json").is_err());
    }

    #[test]
    fn proposal_diagnostic_names_leaf_title_and_gap_id_on_one_line() {
        let violation = AuditProposalViolation::UnknownGapId {
            leaf: 2,
            title: "[LEAF OF 10] Repair the audit gap".to_owned(),
            gap_id: "leaf:11:body:5".to_owned(),
        };
        assert_eq!(
            proposal_violation_diagnostic(&violation),
            "proposal-violation constraint=unknown-gap-id leaf=2 title=\"[LEAF OF 10] Repair the audit gap\" gap_id=\"leaf:11:body:5\""
        );
    }

    #[test]
    fn proposal_diagnostic_formats_nested_ledger_section_and_dependency_context() {
        assert_eq!(
            proposal_violation_diagnostic(&AuditProposalViolation::Ledger {
                violation: AuditLedgerViolation::MalformedEntryId {
                    id: "bad id\n".to_owned(),
                },
            }),
            "proposal-violation constraint=ledger ledger_constraint=malformed-entry-id entry=badid"
        );
        assert_eq!(
            proposal_violation_diagnostic(&AuditProposalViolation::Ledger {
                violation: AuditLedgerViolation::Coverage {
                    uncovered: 2,
                    unknown: 1,
                },
            }),
            "proposal-violation constraint=ledger ledger_constraint=coverage uncovered=2 unknown=1"
        );
        assert_eq!(
            proposal_violation_diagnostic(&AuditProposalViolation::LeafSection {
                leaf: 3,
                title: "unsafe\né".to_owned(),
                section: "## Scope",
            }),
            "proposal-violation constraint=leaf-section leaf=3 title=\"unsafe??\" section=\"## Scope\""
        );
        assert_eq!(
            proposal_violation_diagnostic(&AuditProposalViolation::DependencySelf {
                dependency: 4,
                removal: true,
            }),
            "proposal-violation constraint=dependency-self dependency=4 kind=removal"
        );
    }

    #[test]
    fn default_branch_drift_reaudits_only_before_a_public_transaction_starts() {
        let snapshot = audit_snapshot();
        let ledger = gap_ledger(&snapshot);
        let mut proposal = gap_proposal(&snapshot, &ledger);
        let advanced = "b".repeat(40);

        assert_eq!(
            audit_baseline_action(&snapshot, &proposal, &snapshot.audited_sha),
            Ok(AuditBaselineAction::Current)
        );
        assert_eq!(
            audit_baseline_action(&snapshot, &proposal, &advanced),
            Ok(AuditBaselineAction::Rebaseline)
        );

        let identity = proposal.leaves[0].identity.clone();
        mark_audit_leaf_in_flight(&mut proposal, &identity).expect("in-flight transaction");
        assert_eq!(
            audit_baseline_action(&snapshot, &proposal, &advanced),
            Ok(AuditBaselineAction::ResumeTransaction)
        );
    }

    #[tokio::test]
    async fn remote_snapshot_discovery_reads_the_complete_audit_history() {
        let parent = remote_parent();
        let leaf = remote_leaf();
        let control = remote_control();
        let (service, server) = service(snapshot_exchanges(&parent, &leaf, &control));
        let cancellation = Cancellation::new();
        let snapshot = collect_snapshot_remote(
            &service,
            &cancellation,
            &repository(),
            10,
            "main",
            &"a".repeat(40),
        )
        .await
        .expect("remote snapshot");

        assert_eq!(snapshot, audit_snapshot());
        assert_eq!(server.finish().expect("stub completed").len(), 4);
    }

    #[tokio::test]
    async fn remote_snapshot_refuses_direct_umbrella_children() {
        let parent = remote_parent();
        let nested = issue_json(
            11,
            111,
            "[UMBRELLA] Nested child",
            "<!-- larch:umbrella-proposal v1 -->\n\n#### Leaf issues\n\n- None yet.\n",
            "open",
        );
        let control = remote_control();
        let (service, server) = service(vec![
            response(200, repository_json("main")),
            response(200, &parent),
            response(200, refs(&[(11, 111, "open")])),
            response(200, format!("[{parent},{nested},{control}]")),
        ]);
        let cancellation = Cancellation::new();
        let error = collect_snapshot_remote(
            &service,
            &cancellation,
            &repository(),
            10,
            "main",
            &"a".repeat(40),
        )
        .await
        .expect_err("umbrella children must refuse");
        assert_eq!(error, "nested umbrellas are not supported");
        assert_eq!(server.finish().expect("stub completed").len(), 4);
    }

    #[tokio::test]
    async fn remote_dependency_pagination_stays_on_the_adapter_loopback_transport() {
        let (service, server) = service(vec![
            paginated_response(
                200,
                refs(&[(11, 111, "open")]),
                "/repos/o/r/issues/10/dependencies/blocked_by?page=2",
            ),
            response(200, refs(&[(12, 112, "open")])),
        ]);

        let dependencies = service
            .list_blocked_by(&Cancellation::new(), "o", "r", 10)
            .await
            .expect("loopback pagination");
        assert_eq!(
            dependencies
                .iter()
                .map(larch_adapters::github::DependencyRef::issue_number)
                .collect::<Vec<_>>(),
            [11, 12]
        );

        let requests = server.finish().expect("stub completed");
        assert_eq!(requests.len(), 2);
        assert_eq!(
            requests[1].path,
            "/repos/o/r/issues/10/dependencies/blocked_by?page=2"
        );
    }

    #[tokio::test]
    async fn remote_snapshot_fetches_required_sources_missing_from_history() {
        let parent = remote_parent();
        let leaf = remote_leaf();
        let control = remote_control();
        let exchanges = vec![
            response(200, repository_json("main")),
            response(200, &parent),
            response(200, refs(&[(11, 111, "open")])),
            response(200, format!("[{parent}]")),
            response(200, &leaf),
            response(200, &control),
        ];
        let (service, server) = service(exchanges);
        let cancellation = Cancellation::new();
        let snapshot = collect_snapshot_remote(
            &service,
            &cancellation,
            &repository(),
            10,
            "main",
            &"a".repeat(40),
        )
        .await
        .expect("missing sources read individually");

        assert_eq!(snapshot, audit_snapshot());
        assert_eq!(server.finish().expect("stub completed").len(), 6);
    }

    #[tokio::test]
    async fn remote_snapshot_stops_when_the_default_branch_changes() {
        let (service, server) = service(vec![response(200, repository_json("release"))]);
        let cancellation = Cancellation::new();
        assert!(
            collect_snapshot_remote(
                &service,
                &cancellation,
                &repository(),
                10,
                "main",
                &"a".repeat(40),
            )
            .await
            .is_err()
        );
        assert_eq!(server.finish().expect("stub completed").len(), 1);
    }

    #[tokio::test]
    async fn remote_preparation_rechecks_the_snapshot_before_a_pending_batch() {
        let snapshot = audit_snapshot();
        let ledger = gap_ledger(&snapshot);
        let proposal = gap_proposal(&snapshot, &ledger);
        let parent = remote_parent();
        let leaf = remote_leaf();
        let control = remote_control();
        let mut exchanges = snapshot_exchanges(&parent, &leaf, &control);
        exchanges.extend([
            response(200, &parent),
            response(200, &leaf),
            response(200, &control),
            response(200, &parent),
            response(200, refs(&[(11, 111, "open")])),
        ]);
        let (service, server) = service(exchanges);
        let temporary = tempfile::tempdir().expect("temporary root");
        let root = temporary_root(temporary.path(), "--root").expect("trusted root");
        let proposal_path = temporary.path().join("proposal.json");
        let cancellation = Cancellation::new();
        let repository = repository();
        let authorization = operator_authorization();
        let context = ApplyContext {
            service: &service,
            cancellation: &cancellation,
            repository: &repository,
            snapshot: &snapshot,
            ledger: &ledger,
            proposal_path: &proposal_path,
            supplied_root: temporary.path(),
            root: &root,
            authorization: &authorization,
        };

        let current = prepare_remote_apply(&context, &proposal)
            .await
            .expect("fresh remote proposal");
        assert_eq!(current, current_snapshot_sources(&snapshot));
        assert_eq!(server.finish().expect("stub completed").len(), 9);
    }

    #[tokio::test]
    async fn remote_preparation_resumes_an_inflight_graph_with_content_checks() {
        let snapshot = audit_snapshot();
        let ledger = satisfied_ledger(&snapshot);
        let draft = AuditProposalDraft {
            version: AUDIT_PROPOSAL_VERSION,
            leaves: Vec::new(),
            dependencies: Vec::new(),
            remove_dependencies: Vec::new(),
        };
        let mut proposal = build_audit_proposal(&snapshot, &ledger, &draft).expect("proposal");
        mark_audit_graph_in_flight(&mut proposal).expect("graph in flight");
        let parent = remote_parent();
        let leaf = remote_leaf();
        let control = remote_control();
        let (service, server) = service(vec![
            response(200, &parent),
            response(200, &leaf),
            response(200, &control),
            response(200, &parent),
            response(200, refs(&[(11, 111, "open")])),
        ]);
        let temporary = tempfile::tempdir().expect("temporary root");
        let root = temporary_root(temporary.path(), "--root").expect("trusted root");
        let proposal_path = temporary.path().join("proposal.json");
        let cancellation = Cancellation::new();
        let repository = repository();
        let authorization = operator_authorization();
        let context = ApplyContext {
            service: &service,
            cancellation: &cancellation,
            repository: &repository,
            snapshot: &snapshot,
            ledger: &ledger,
            proposal_path: &proposal_path,
            supplied_root: temporary.path(),
            root: &root,
            authorization: &authorization,
        };

        assert!(prepare_remote_apply(&context, &proposal).await.is_ok());
        assert_eq!(server.finish().expect("stub completed").len(), 5);
    }

    #[tokio::test]
    async fn remote_leaf_reconciliation_creates_and_proves_exactly_one_leaf() {
        let snapshot = audit_snapshot();
        let ledger = gap_ledger(&snapshot);
        let mut proposal = gap_proposal(&snapshot, &ledger);
        let created = issue_json(
            13,
            113,
            &proposal.leaves[0].title,
            &proposal.leaves[0].body,
            "open",
        );
        let parent = remote_parent();
        let leaf = remote_leaf();
        let control = remote_control();
        let (service, server) = service(vec![
            response(200, "[]"),
            response(201, &created),
            response(200, &created),
            response(200, &parent),
            response(200, &leaf),
            response(200, &control),
            response(200, &created),
        ]);
        let temporary = tempfile::tempdir().expect("temporary root");
        let root = temporary_root(temporary.path(), "--root").expect("trusted root");
        let proposal_path = temporary.path().join("proposal.json");
        let cancellation = Cancellation::new();
        let repository = repository();
        let authorization = operator_authorization();
        let context = ApplyContext {
            service: &service,
            cancellation: &cancellation,
            repository: &repository,
            snapshot: &snapshot,
            ledger: &ledger,
            proposal_path: &proposal_path,
            supplied_root: temporary.path(),
            root: &root,
            authorization: &authorization,
        };

        reconcile_audit_leaves(&context, &mut proposal)
            .await
            .expect("leaf creation");
        assert_eq!(proposal.leaves[0].state, AuditLeafState::Resolved);
        assert_eq!(proposal.leaves[0].number, 13);
        let requests = server.finish().expect("stub completed");
        assert_eq!(requests.len(), 7);
        assert!(requests.iter().any(|request| {
            request.method == "POST"
                && request.path.ends_with("/repos/o/r/issues")
                && String::from_utf8_lossy(&request.body.bytes)
                    .contains("[LEAF OF 10] Repair the audit gap")
        }));
    }

    #[tokio::test]
    async fn remote_leaf_reconciliation_resumes_a_prior_inflight_creation() {
        let snapshot = audit_snapshot();
        let ledger = gap_ledger(&snapshot);
        let mut proposal = gap_proposal(&snapshot, &ledger);
        let identity = proposal.leaves[0].identity.clone();
        mark_audit_leaf_in_flight(&mut proposal, &identity).expect("in flight");
        let created = issue_json(
            13,
            113,
            &proposal.leaves[0].title,
            &proposal.leaves[0].body,
            "open",
        );
        let parent = remote_parent();
        let leaf = remote_leaf();
        let control = remote_control();
        let (service, server) = service(vec![
            response(200, format!("[{created}]")),
            response(200, &parent),
            response(200, &leaf),
            response(200, &control),
            response(200, &created),
        ]);
        let temporary = tempfile::tempdir().expect("temporary root");
        let root = temporary_root(temporary.path(), "--root").expect("trusted root");
        let proposal_path = temporary.path().join("proposal.json");
        let cancellation = Cancellation::new();
        let repository = repository();
        let authorization = operator_authorization();
        let context = ApplyContext {
            service: &service,
            cancellation: &cancellation,
            repository: &repository,
            snapshot: &snapshot,
            ledger: &ledger,
            proposal_path: &proposal_path,
            supplied_root: temporary.path(),
            root: &root,
            authorization: &authorization,
        };

        reconcile_audit_leaves(&context, &mut proposal)
            .await
            .expect("in-flight leaf read-back");
        assert_eq!(proposal.leaves[0].state, AuditLeafState::Resolved);
        assert_eq!(server.finish().expect("stub completed").len(), 5);
    }

    #[tokio::test]
    async fn remote_final_verification_proves_the_completed_native_graph() {
        let snapshot = audit_snapshot();
        let ledger = satisfied_ledger(&snapshot);
        let proposal = complete_proposal(&snapshot, &ledger);
        let parent = remote_parent();
        let (service, server) = service(vec![
            response(200, &parent),
            response(200, refs(&[(11, 111, "open")])),
            response(200, refs(&[(11, 111, "open")])),
            response(200, "[]"),
            response(200, "[]"),
            response(200, "[]"),
        ]);
        let cancellation = Cancellation::new();
        let repository = repository();

        verify_final_graph(
            &service,
            &cancellation,
            &repository,
            &snapshot,
            &proposal,
            &current_snapshot_sources(&snapshot),
        )
        .await
        .expect("final graph");
        assert_eq!(server.finish().expect("stub completed").len(), 6);
    }

    #[tokio::test]
    async fn remote_apply_reconciles_an_idempotent_historical_leaf_graph() {
        let snapshot = audit_snapshot();
        let ledger = satisfied_ledger(&snapshot);
        let draft = AuditProposalDraft {
            version: AUDIT_PROPOSAL_VERSION,
            leaves: Vec::new(),
            dependencies: Vec::new(),
            remove_dependencies: Vec::new(),
        };
        let mut proposal = build_audit_proposal(&snapshot, &ledger, &draft).expect("proposal");
        let parent = remote_parent();
        let leaf = remote_leaf();
        let control = remote_control();
        let direct = refs(&[(11, 111, "open")]);
        let mut exchanges = snapshot_exchanges(&parent, &leaf, &control);
        exchanges.extend([
            response(200, &parent),
            response(200, &leaf),
            response(200, &control),
            response(200, &parent),
            response(200, &direct),
            response(200, &parent),
            response(200, &leaf),
            response(200, &control),
            response(200, &parent),
            response(200, &direct),
            response(200, &parent),
            response(200, &leaf),
            response(200, &control),
            response(404, "{}"),
            response(200, &direct),
            response(200, &direct),
            response(200, &parent),
            response(200, &leaf),
            response(200, &control),
            response(200, &parent),
            response(200, &leaf),
            response(200, &control),
            response(200, &parent),
            response(200, &direct),
            response(200, &direct),
            response(200, "[]"),
            response(200, "[]"),
            response(200, "[]"),
        ]);
        let (service, server) = service(exchanges);
        let temporary = tempfile::tempdir().expect("temporary root");
        let root = temporary_root(temporary.path(), "--root").expect("trusted root");
        let proposal_path = temporary.path().join("proposal.json");
        let cancellation = Cancellation::new();
        let repository = repository();
        let authorization = operator_authorization();
        let context = ApplyContext {
            service: &service,
            cancellation: &cancellation,
            repository: &repository,
            snapshot: &snapshot,
            ledger: &ledger,
            proposal_path: &proposal_path,
            supplied_root: temporary.path(),
            root: &root,
            authorization: &authorization,
        };

        apply_remote(&context, &mut proposal)
            .await
            .expect("idempotent graph reconciliation");
        assert!(proposal.complete);
        assert_eq!(proposal.graph_state, AuditGraphState::Verified);
        assert!(proposal_path.is_file());
        assert_eq!(server.finish().expect("stub completed").len(), 32);
    }

    #[allow(clippy::too_many_lines)] // One ordered exchange sequence proves the graph's remote mutation and read-back.
    #[tokio::test]
    async fn remote_relationship_reconciliation_proves_new_leaf_dependencies() {
        let snapshot = audit_snapshot();
        let ledger = gap_ledger(&snapshot);
        let mut proposal = gap_proposal(&snapshot, &ledger);
        let identity = proposal.leaves[0].identity.clone();
        mark_audit_leaf_in_flight(&mut proposal, &identity).expect("in flight");
        record_audit_leaf_resolved(
            &mut proposal,
            &identity,
            13,
            113,
            "https://github.com/o/r/issues/13",
        )
        .expect("resolved");
        proposal.dependencies = vec![AuditDependency {
            dependent: AuditDependencyNode::Existing { number: 11 },
            prerequisite: AuditDependencyNode::New {
                identity: identity.clone(),
            },
        }];

        let parent = remote_parent();
        let leaf = remote_leaf();
        let updated_leaf = remote_leaf_at("2026-08-11T00:01:00Z");
        let control = remote_control();
        let created = issue_json(
            13,
            113,
            &proposal.leaves[0].title,
            &proposal.leaves[0].body,
            "open",
        );
        let direct = refs(&[(11, 111, "open"), (13, 113, "open")]);
        let parent_blockers = refs(&[(11, 111, "open"), (13, 113, "open")]);
        let dependency_blocker = refs(&[(13, 113, "open")]);
        let parent_ref = json!({ "number": 10, "id": 110, "state": "open" }).to_string();
        let exchanges = vec![
            response(200, &parent),
            response(200, &leaf),
            response(200, &control),
            response(200, &created),
            response(404, "{}"),
            response(200, &direct),
            response(200, &parent_blockers),
            response(200, &parent),
            response(200, &leaf),
            response(200, &control),
            response(200, &created),
            response(200, &parent_ref),
            response(200, &direct),
            response(200, &parent_blockers),
            response(200, &parent),
            response(200, &leaf),
            response(200, &control),
            response(200, &created),
            response(200, &leaf),
            response(200, &leaf),
            response(200, "[]"),
            response(200, &leaf),
            response(201, "{}"),
            response(200, &dependency_blocker),
            response(200, &updated_leaf),
            response(200, &parent),
            response(200, &updated_leaf),
            response(200, &control),
            response(200, &created),
            response(200, &parent),
            response(200, &created),
            response(200, &parent_ref),
            response(200, &direct),
            response(200, &parent_blockers),
            response(200, &dependency_blocker),
            response(200, "[]"),
            response(200, "[]"),
            response(200, &dependency_blocker),
            response(200, "[]"),
            response(200, "[]"),
        ];
        let (service, server) = service(exchanges);
        let temporary = tempfile::tempdir().expect("temporary root");
        let root = temporary_root(temporary.path(), "--root").expect("trusted root");
        let proposal_path = temporary.path().join("proposal.json");
        let cancellation = Cancellation::new();
        let repository = repository();
        let authorization = operator_authorization();
        let context = ApplyContext {
            service: &service,
            cancellation: &cancellation,
            repository: &repository,
            snapshot: &snapshot,
            ledger: &ledger,
            proposal_path: &proposal_path,
            supplied_root: temporary.path(),
            root: &root,
            authorization: &authorization,
        };

        reconcile_leaf_relationships(&context, &mut proposal)
            .await
            .expect("relationship reconciliation");
        let current = persist_refreshed_proposal(&context, &mut proposal)
            .await
            .expect("refresh mutated fingerprints");
        verify_final_graph(
            &service,
            &cancellation,
            &repository,
            &snapshot,
            &proposal,
            &current,
        )
        .await
        .expect("new leaf graph read-back");
        let requests = server.finish().expect("stub completed");
        assert_eq!(requests.len(), 40);
        let dependency_writes = requests
            .iter()
            .filter(|request| request.method == "POST")
            .count();
        assert_eq!(dependency_writes, 1);
        assert!(requests.iter().any(|request| {
            request.method == "POST"
                && request
                    .path
                    .ends_with("/repos/o/r/issues/11/dependencies/blocked_by")
                && String::from_utf8_lossy(&request.body.bytes).contains("\"issue_id\":113")
        }));
    }

    #[test]
    fn native_owned_umbrella_blockers_are_skipped_from_declared_edges() {
        let snapshot = audit_snapshot();
        let ledger = gap_ledger(&snapshot);
        let mut proposal = gap_proposal(&snapshot, &ledger);
        let identity = proposal.leaves[0].identity.clone();
        proposal.leaves[0].state = AuditLeafState::Resolved;
        proposal.leaves[0].number = 13;
        proposal.leaves[0].issue_id = 113;
        proposal.leaves[0].url = "https://github.com/o/r/issues/13".to_owned();

        let umbrella_to_new = AuditDependency {
            dependent: AuditDependencyNode::Existing { number: 10 },
            prerequisite: AuditDependencyNode::New {
                identity: identity.clone(),
            },
        };
        let umbrella_to_old = AuditDependency {
            dependent: AuditDependencyNode::Existing { number: 10 },
            prerequisite: AuditDependencyNode::Existing { number: 11 },
        };
        let leaf_to_leaf = AuditDependency {
            dependent: AuditDependencyNode::Existing { number: 11 },
            prerequisite: AuditDependencyNode::New { identity },
        };
        assert!(is_native_owned_umbrella_blocker(
            &proposal,
            &umbrella_to_new
        ));
        assert!(is_native_owned_umbrella_blocker(
            &proposal,
            &umbrella_to_old
        ));
        assert!(!is_native_owned_umbrella_blocker(&proposal, &leaf_to_leaf));
    }

    #[test]
    fn dependency_mutation_errors_preserve_refusal_kinds() {
        assert_eq!(
            dependency_mutation_error(GitHubOperationError::ProtectedDependencyTarget),
            "dependency mutation refused: protected dependency target"
        );
        assert_eq!(
            dependency_mutation_error(GitHubOperationError::StaleDependencyTarget),
            "dependency mutation refused: stale dependency target"
        );
        assert_eq!(
            dependency_mutation_error(GitHubOperationError::SecuritySensitiveDependencyTarget),
            "dependency mutation refused: security-sensitive dependency target"
        );
        assert_eq!(
            dependency_mutation_error(GitHubOperationError::Malformed(
                "dependency mutation not reflected in read-back"
            )),
            "dependency mutation was not proven by read-back"
        );
        assert!(
            dependency_mutation_error(GitHubOperationError::RateLimited)
                .starts_with("dependency mutation failed:")
        );
    }

    #[tokio::test]
    async fn declared_umbrella_blockers_are_idempotent_on_managed_umbrellas() {
        // Reproduces #8560: a managed umbrella carries a lifecycle title and
        // larch HTML marker, so the operator-facing protected-target mutator
        // refuses both fresh adds and AlreadyInDesiredState resumes. Declared
        // umbrella <- direct-leaf edges must therefore be owned by native
        // attach and skipped here.
        let snapshot = audit_snapshot();
        let ledger = gap_ledger(&snapshot);
        let mut proposal = gap_proposal(&snapshot, &ledger);
        let identity = proposal.leaves[0].identity.clone();
        proposal.leaves[0].state = AuditLeafState::Resolved;
        proposal.leaves[0].number = 13;
        proposal.leaves[0].issue_id = 113;
        proposal.leaves[0].url = "https://github.com/o/r/issues/13".to_owned();
        proposal.dependencies = vec![
            AuditDependency {
                dependent: AuditDependencyNode::Existing { number: 10 },
                prerequisite: AuditDependencyNode::Existing { number: 11 },
            },
            AuditDependency {
                dependent: AuditDependencyNode::Existing { number: 10 },
                prerequisite: AuditDependencyNode::New {
                    identity: identity.clone(),
                },
            },
        ];
        // No remote exchanges: skipped edges must not touch GitHub at all.
        let (service, server) = service(Vec::new());
        let cancellation = Cancellation::new();
        let repository = repository();
        let authorization = operator_authorization();

        apply_dependencies(
            &service,
            &cancellation,
            &repository,
            &proposal,
            &authorization,
        )
        .await
        .expect("native-owned declared umbrella blockers skip without remote work");
        assert_eq!(server.finish().expect("stub completed").len(), 0);
    }

    #[tokio::test]
    async fn audit_umbrella_dependency_removals_use_the_trusted_mutation_path() {
        let snapshot = audit_snapshot();
        let ledger = satisfied_ledger(&snapshot);
        let draft = AuditProposalDraft {
            version: AUDIT_PROPOSAL_VERSION,
            leaves: Vec::new(),
            dependencies: Vec::new(),
            remove_dependencies: vec![AuditDependency {
                dependent: AuditDependencyNode::Existing { number: 10 },
                prerequisite: AuditDependencyNode::Existing { number: 11 },
            }],
        };
        let proposal = build_audit_proposal(&snapshot, &ledger, &draft).expect("proposal");
        let managed_parent = issue_json(
            10,
            110,
            "[IMPLEMENTING] [UMBRELLA] Fixture",
            "<!-- larch:umbrella-proposal v1 -->\n\n#### Leaf issues\n\n- #11\n",
            "open",
        );
        let present = refs(&[(11, 111, "open")]);
        let (service, server) = service(vec![
            response(200, &managed_parent),
            response(200, &present),
            response(204, "{}"),
            response(200, "[]"),
        ]);
        let cancellation = Cancellation::new();
        let repository = repository();
        let authorization = operator_authorization();

        apply_dependencies(
            &service,
            &cancellation,
            &repository,
            &proposal,
            &authorization,
        )
        .await
        .expect("audit-owned umbrella removals bypass protected-target rules");
        let requests = server.finish().expect("stub completed");
        assert_eq!(requests.len(), 4);
        assert!(requests.iter().any(|request| {
            request.method == "DELETE"
                && request
                    .path
                    .ends_with("/repos/o/r/issues/10/dependencies/blocked_by/111")
        }));
    }

    #[tokio::test]
    async fn leaf_dependency_mutations_surface_protected_target_refusals() {
        let snapshot = audit_snapshot();
        let ledger = gap_ledger(&snapshot);
        let mut proposal = gap_proposal(&snapshot, &ledger);
        let identity = proposal.leaves[0].identity.clone();
        proposal.leaves[0].state = AuditLeafState::Resolved;
        proposal.leaves[0].number = 13;
        proposal.leaves[0].issue_id = 113;
        proposal.leaves[0].url = "https://github.com/o/r/issues/13".to_owned();
        proposal.dependencies = vec![AuditDependency {
            dependent: AuditDependencyNode::Existing { number: 11 },
            prerequisite: AuditDependencyNode::New { identity },
        }];
        let protected_leaf = issue_json(
            11,
            111,
            "[IMPLEMENTING] [LEAF OF 10] Existing leaf",
            &format!(
                "<!-- larch:plan -->\n{}\n\nExisting scope.\n",
                umbrella_leaf_opening(10)
            ),
            "open",
        );
        let (service, server) = service(vec![
            response(200, &protected_leaf),
            response(200, &protected_leaf),
        ]);
        let cancellation = Cancellation::new();
        let repository = repository();
        let authorization = operator_authorization();

        let error = apply_dependencies(
            &service,
            &cancellation,
            &repository,
            &proposal,
            &authorization,
        )
        .await
        .expect_err("protected leaf targets must refuse loudly");
        assert_eq!(
            error,
            "dependency mutation refused: protected dependency target"
        );
        assert_eq!(server.finish().expect("stub completed").len(), 2);
    }

    #[tokio::test]
    async fn leaf_dependency_mutations_skip_security_keyword_triage() {
        let snapshot = audit_snapshot();
        let ledger = gap_ledger(&snapshot);
        let mut proposal = gap_proposal(&snapshot, &ledger);
        let identity = proposal.leaves[0].identity.clone();
        proposal.leaves[0].state = AuditLeafState::Resolved;
        proposal.leaves[0].number = 13;
        proposal.leaves[0].issue_id = 113;
        proposal.leaves[0].url = "https://github.com/o/r/issues/13".to_owned();
        proposal.dependencies = vec![AuditDependency {
            dependent: AuditDependencyNode::Existing { number: 11 },
            prerequisite: AuditDependencyNode::New { identity },
        }];
        let security_leaf = issue_json(
            11,
            111,
            "[LEAF OF 10] Preserve secret-scrub guarantees",
            &format!(
                "{}\n\nDocument credential redaction.\n",
                umbrella_leaf_opening(10)
            ),
            "open",
        );
        let updated_security_leaf = issue_json_at(
            11,
            111,
            "[LEAF OF 10] Preserve secret-scrub guarantees",
            &format!(
                "{}\n\nDocument credential redaction.\n",
                umbrella_leaf_opening(10)
            ),
            "open",
            "2026-08-11T00:01:00Z",
        );
        let dependency_blocker = refs(&[(13, 113, "open")]);
        let (service, server) = service(vec![
            response(200, &security_leaf),
            response(200, &security_leaf),
            response(200, "[]"),
            response(200, &security_leaf),
            response(201, "{}"),
            response(200, &dependency_blocker),
            response(200, &updated_security_leaf),
        ]);
        let cancellation = Cancellation::new();
        let repository = repository();
        let authorization = operator_authorization();

        apply_dependencies(
            &service,
            &cancellation,
            &repository,
            &proposal,
            &authorization,
        )
        .await
        .expect("audit dependency wiring ignores security keywords");
        let requests = server.finish().expect("stub completed");
        assert_eq!(requests.len(), 7);
        assert!(
            requests
                .iter()
                .all(|request| !request.path.contains("/comments"))
        );
        assert!(requests.iter().any(|request| {
            request.method == "POST"
                && request
                    .path
                    .ends_with("/repos/o/r/issues/11/dependencies/blocked_by")
        }));
    }

    #[test]
    fn remove_worktree_deletes_a_real_detached_worktree_directory() {
        let repository = match GitRepository::builder(GitFixture::Refs).build() {
            Ok(repository) => repository,
            Err(GitFixtureError::Skip(skip)) => {
                eprintln!("explicit capability skip: {skip}");
                return;
            }
            Err(error) => panic!("git fixture failed: {error}"),
        };

        let session_root = tempfile::tempdir().expect("session root");
        let worktree = session_root.path().join("worktree");
        let worktree_arg = worktree
            .to_str()
            .expect("worktree path is valid UTF-8")
            .to_owned();

        let added = repository
            .git(["worktree", "add", "--detach", &worktree_arg, "HEAD"])
            .expect("run worktree add");
        assert!(added.success(), "worktree add must succeed");
        assert!(worktree.is_dir(), "worktree directory must exist");

        super::remove_worktree(&RemoveWorktreeArguments {
            repo_root: repository.root().to_path_buf(),
            root: session_root.path().to_path_buf(),
            worktree: worktree.clone(),
        })
        .expect("remove_worktree removes an existing directory worktree");

        assert!(
            std::fs::symlink_metadata(&worktree).is_err(),
            "worktree directory must be gone after removal"
        );
    }
}
