//! Rust composition root for `/complete-umbrella`.

use crate::{
    github_repository_resolution::repository_ref,
    github_service::{ServiceFailure, with_github_service},
};
use clap::{Args, Subcommand};
use larch_adapters::{
    ConfinedPath, PathIntent, TemporaryRoot, TokioProcessRunner, atomic_write_utf8,
    github::{
        DependencyEdge, IssueMutationOwner, LiveMutationRequest, SubIssueEdge,
        check_live_mutation_auth,
    },
    is_allowed_session_tmpdir, normalize_path, open_confined_read,
    runtime::{Cancellation, LarchRuntime},
};
use larch_core::{
    COMPLETE_UMBRELLA_CHILD_COMPLETE, ChildEnvironment, CompleteUmbrellaLeaf, CompleteUmbrellaNext,
    DONE_PREFIX, ExternalProcessRunner, ExternalProgram, GitHubCloseReason, GitHubIssue,
    GitHubIssueState, GitHubRepositoryRef, GitHubService, IMPLEMENTING_PREFIX, IssueMutationField,
    IssueMutationRequest, ProcessRequest, VendorLaunchRequest, VendorProgram,
    allowed_session_roots, build_claude_argv, complete_umbrella_child_prompt,
    complete_umbrella_done_title, complete_umbrella_start_title, emit_kv, has_umbrella_proposal,
    parse_claude_envelope, redact, redact_issue_mutation_request, select_complete_umbrella_leaf,
    umbrella_leaf_opening, umbrella_leaf_prefix, validate_complete_umbrella_leaf,
    validate_complete_umbrella_parent,
};
use serde::Serialize;
use std::{
    collections::BTreeSet,
    env,
    ffi::OsString,
    fs,
    io::Read as _,
    num::NonZeroUsize,
    path::{Path, PathBuf},
    process::ExitCode,
    time::Duration,
};

const MAX_DIRECT_LEAVES: usize = 100;
const CHILD_TIMEOUT: Duration = Duration::from_secs(24 * 60 * 60);
const CHILD_SHUTDOWN_GRACE: Duration = Duration::from_secs(10);
const CHILD_OUTPUT_LIMIT: usize = 4 * 1024 * 1024;

#[derive(Subcommand)]
pub enum CompleteUmbrellaCommand {
    /// Mark the parent active after validating its durable umbrella identity.
    Start(ParentMutationArguments),
    /// Fetch a fresh graph snapshot and select the next runnable leaf.
    Next(NextArguments),
    /// Run one leaf in the current Claude harness and model.
    #[command(name = "run-child")]
    RunChild(RunChildArguments),
    /// Prove that one child completed its remote lifecycle.
    #[command(name = "verify-child")]
    VerifyChild(LeafArguments),
    /// Validate caller-owned audit-gap files before public issue creation.
    #[command(name = "validate-gap")]
    ValidateGap(ValidateGapArguments),
    /// Attach one audit-created leaf through both native graph relations.
    #[command(name = "attach-leaf")]
    AttachLeaf(AttachLeafArguments),
    /// Mark the audited parent done and close it as completed.
    Finish(ParentMutationArguments),
}

#[derive(Args)]
pub struct ParentMutationArguments {
    #[arg(long)]
    repository: String,
    #[arg(long)]
    issue: u64,
    #[arg(long, action = clap::ArgAction::SetTrue)]
    operator_invoked: bool,
}

#[derive(Args)]
pub struct NextArguments {
    #[arg(long)]
    repository: String,
    #[arg(long)]
    issue: u64,
    #[arg(long)]
    output_root: PathBuf,
    #[arg(long)]
    output: PathBuf,
}

#[derive(Args)]
pub struct LeafArguments {
    #[arg(long)]
    repository: String,
    #[arg(long)]
    umbrella: u64,
    #[arg(long)]
    leaf: u64,
}

#[derive(Args)]
pub struct AttachLeafArguments {
    #[command(flatten)]
    leaf: LeafArguments,
    #[arg(long, action = clap::ArgAction::SetTrue)]
    operator_invoked: bool,
    #[command(flatten)]
    files: GapFileArguments,
}

#[derive(Args)]
pub struct ValidateGapArguments {
    #[arg(long)]
    umbrella: u64,
    #[command(flatten)]
    files: GapFileArguments,
}

#[derive(Args)]
pub struct GapFileArguments {
    #[arg(long = "expected-root")]
    root: PathBuf,
    #[arg(long = "expected-title-file")]
    title_file: PathBuf,
    #[arg(long = "expected-body-file")]
    body_file: PathBuf,
}

#[derive(Args)]
pub struct RunChildArguments {
    #[arg(long)]
    repository: String,
    #[arg(long)]
    repo_root: PathBuf,
    #[arg(long)]
    umbrella: u64,
    #[arg(long)]
    leaf: u64,
    #[arg(long)]
    model: String,
    #[arg(long)]
    output_root: PathBuf,
    #[arg(long)]
    output: PathBuf,
    #[arg(long)]
    result_env: PathBuf,
}

#[derive(Serialize)]
struct AuditIssue {
    number: u64,
    state: &'static str,
    url: String,
    title_untrusted: String,
    body_untrusted: String,
}

#[derive(Serialize)]
struct AuditLeaf {
    issue: AuditIssue,
    open_blockers: Vec<u64>,
}

#[derive(Serialize)]
struct AuditSnapshot {
    repository: String,
    umbrella: AuditIssue,
    leaves: Vec<AuditLeaf>,
}

struct LeafState {
    issue: GitHubIssue,
    open_blockers: Vec<u64>,
}

struct GraphState {
    parent: GitHubIssue,
    leaves: Vec<LeafState>,
}

struct ExpectedAuditLeaf {
    remote_title: String,
    body: String,
}

#[must_use]
pub fn run(command: CompleteUmbrellaCommand) -> ExitCode {
    let result = match command {
        CompleteUmbrellaCommand::Start(arguments) => start(&arguments),
        CompleteUmbrellaCommand::Next(arguments) => next(&arguments),
        CompleteUmbrellaCommand::RunChild(arguments) => run_child(&arguments),
        CompleteUmbrellaCommand::VerifyChild(arguments) => verify_child(&arguments),
        CompleteUmbrellaCommand::ValidateGap(arguments) => validate_gap(&arguments),
        CompleteUmbrellaCommand::AttachLeaf(arguments) => attach_leaf(&arguments),
        CompleteUmbrellaCommand::Finish(arguments) => finish(&arguments),
    };
    match result {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("complete-umbrella: {error}");
            ExitCode::FAILURE
        }
    }
}

fn start(arguments: &ParentMutationArguments) -> Result<(), String> {
    require_operator(arguments.operator_invoked)?;
    require_issue(arguments.issue, "--issue")?;
    let repository = parse_repository(&arguments.repository)?;
    with_github_service(async |service, cancellation| {
        let parent = service
            .issue(&repository, arguments.issue, cancellation)
            .await
            .map_err(|error| error.to_string())?;
        validate_complete_umbrella_parent(&parent, true)?;
        require_top_level_umbrella(service, cancellation, &repository, arguments.issue).await?;
        let owner = IssueMutationOwner::new(service);
        let before = owner
            .read_snapshot(&repository, arguments.issue, cancellation)
            .await
            .map_err(|error| error.to_string())?;
        if before.state != GitHubIssueState::Open || !has_umbrella_proposal(&before.body) {
            return Err("parent changed before the active-title mutation".to_owned());
        }
        let title = complete_umbrella_start_title(&before.title).map_err(str::to_owned)?;
        let request = exact_title_request(&before, title)?;
        let verified = owner
            .apply(cancellation, &operator_authorization(), &request)
            .await
            .map_err(|error| error.to_string())?;
        if verified.after.state != GitHubIssueState::Open
            || !verified.after.title.starts_with(IMPLEMENTING_PREFIX)
        {
            return Err("active parent title read-back failed".to_owned());
        }
        Ok(())
    })
    .map_err(ServiceFailure::into_detail)?;
    emit_kv("UMBRELLA_STARTED", "true");
    emit_kv("UMBRELLA_ISSUE", &arguments.issue.to_string());
    Ok(())
}

fn next(arguments: &NextArguments) -> Result<(), String> {
    require_issue(arguments.issue, "--issue")?;
    let repository = parse_repository(&arguments.repository)?;
    let graph = with_github_service(async |service, cancellation| {
        read_graph(service, cancellation, &repository, arguments.issue).await
    })
    .map_err(ServiceFailure::into_detail)?;
    if graph.parent.state != GitHubIssueState::Open
        || !graph.parent.title.starts_with(IMPLEMENTING_PREFIX)
    {
        return Err("parent must be open with the [IMPLEMENTING] prefix".to_owned());
    }
    let selection_input = graph
        .leaves
        .iter()
        .map(|leaf| CompleteUmbrellaLeaf {
            number: leaf.issue.number,
            open: leaf.issue.state == GitHubIssueState::Open,
            open_blockers: leaf.open_blockers.clone(),
        })
        .collect::<Vec<_>>();
    let selection = select_complete_umbrella_leaf(&selection_input);
    write_audit_snapshot(arguments, &graph)?;
    match &selection {
        CompleteUmbrellaNext::Launch(issue) => {
            emit_kv("NEXT_ACTION", "launch");
            emit_kv("NEXT_LEAF", &issue.to_string());
        }
        CompleteUmbrellaNext::Audit => emit_kv("NEXT_ACTION", "audit"),
        CompleteUmbrellaNext::Deadlocked(issues) => {
            emit_kv("NEXT_ACTION", "deadlock");
            emit_kv("BLOCKED_LEAVES", &join_numbers(issues));
        }
    }
    emit_kv("LEAF_COUNT", &graph.leaves.len().to_string());
    emit_kv(
        "OPEN_LEAF_COUNT",
        &selection_input
            .iter()
            .filter(|leaf| leaf.open)
            .count()
            .to_string(),
    );
    emit_kv("SNAPSHOT_WRITTEN", "true");
    Ok(())
}

fn run_child(arguments: &RunChildArguments) -> Result<(), String> {
    require_issue(arguments.umbrella, "--umbrella")?;
    require_issue(arguments.leaf, "--leaf")?;
    let repository = parse_repository(&arguments.repository)?;
    if arguments.model == "unknown"
        || arguments.model.is_empty()
        || arguments.model.chars().any(char::is_whitespace)
    {
        return Err("--model must be one resolved non-whitespace token".to_owned());
    }
    let repo_root = canonical_directory(&arguments.repo_root, "--repo-root")?;
    let output_root = temporary_root(&arguments.output_root, "--output-root")?;
    let prompt = complete_umbrella_child_prompt(
        &format!("{}/{}", repository.owner(), repository.name()),
        arguments.umbrella,
        arguments.leaf,
    );
    let repo_root_text = repo_root
        .to_str()
        .ok_or("--repo-root must be valid UTF-8")?
        .to_owned();
    let mut launch = VendorLaunchRequest::new(&repo_root_text, "", prompt.clone());
    launch.model.clone_from(&arguments.model);
    let argv = build_claude_argv("workflow-write", &launch).map_err(|error| error.to_string())?;
    let mut request = ProcessRequest::new(
        ExternalProgram::Vendor(VendorProgram::Claude),
        argv.arguments().iter().map(OsString::from),
        repo_root,
        CHILD_TIMEOUT,
        CHILD_SHUTDOWN_GRACE,
        NonZeroUsize::new(CHILD_OUTPUT_LIMIT).unwrap_or(NonZeroUsize::MIN),
    )
    .map_err(|error| error.to_string())?
    .with_stdin(prompt)
    .with_environment(ChildEnvironment::ClaudeSubprocessHookExempt, "1");
    for key in [
        ChildEnvironment::AnthropicApiKey,
        ChildEnvironment::ClaudePluginRoot,
        ChildEnvironment::ClaudePluginData,
        ChildEnvironment::GhConfigDir,
        ChildEnvironment::XdgConfigHome,
    ] {
        if let Some(value) = env::var_os(key.name()) {
            request = request.with_environment(key, value);
        }
    }
    let runtime = LarchRuntime::new().map_err(|error| error.to_string())?;
    let cancellation = Cancellation::new();
    let runner = TokioProcessRunner::default();
    let execution = runtime.block_on(runner.run(request, &cancellation));
    let execution = match execution {
        Ok(execution) => execution,
        Err(error) => {
            write_child_result(arguments, &output_root, arguments.leaf, false)?;
            return Err(format!("child process failed: {}", error.message()));
        }
    };
    let raw = String::from_utf8_lossy(execution.stdout()).into_owned();
    write_private_file(
        &arguments.output,
        &raw,
        &arguments.output_root,
        &output_root,
    )?;
    write_child_stderr(arguments, &output_root, &execution)?;
    let parsed = parse_claude_envelope(&raw);
    let marker_ok = parsed
        .text
        .lines()
        .rev()
        .find(|line| !line.trim().is_empty())
        .is_some_and(|line| line.trim() == COMPLETE_UMBRELLA_CHILD_COMPLETE);
    let success = execution.status().success()
        && !execution.stdout_truncated()
        && !execution.stderr_truncated()
        && marker_ok;
    write_child_result(arguments, &output_root, arguments.leaf, success)?;
    if !success {
        return Err("child did not return a complete, bounded success envelope".to_owned());
    }
    emit_kv("CHILD_STATUS", "complete");
    emit_kv("CHILD_ISSUE", &arguments.leaf.to_string());
    Ok(())
}

fn verify_child(arguments: &LeafArguments) -> Result<(), String> {
    require_issue(arguments.umbrella, "--umbrella")?;
    require_issue(arguments.leaf, "--leaf")?;
    let repository = parse_repository(&arguments.repository)?;
    with_github_service(async |service, cancellation| {
        let graph = read_graph(service, cancellation, &repository, arguments.umbrella).await?;
        let Some(leaf) = graph
            .leaves
            .iter()
            .find(|leaf| leaf.issue.number == arguments.leaf)
        else {
            return Err("child is not a direct leaf of the umbrella".to_owned());
        };
        let done_prefix = format!("{DONE_PREFIX}{}", umbrella_leaf_prefix(arguments.umbrella));
        if leaf.issue.state != GitHubIssueState::Closed
            || !leaf.issue.title.starts_with(&done_prefix)
        {
            return Err("child must be closed with the exact [DONE] leaf prefix".to_owned());
        }
        Ok(())
    })
    .map_err(ServiceFailure::into_detail)?;
    emit_kv("CHILD_VERIFIED", "true");
    emit_kv("CHILD_ISSUE", &arguments.leaf.to_string());
    Ok(())
}

fn attach_leaf(arguments: &AttachLeafArguments) -> Result<(), String> {
    require_operator(arguments.operator_invoked)?;
    require_issue(arguments.leaf.umbrella, "--umbrella")?;
    require_issue(arguments.leaf.leaf, "--leaf")?;
    let repository = parse_repository(&arguments.leaf.repository)?;
    let expected = read_expected_audit_leaf(arguments.leaf.umbrella, &arguments.files)?;
    with_github_service(async |service, cancellation| {
        attach_leaf_remote(
            service,
            cancellation,
            &repository,
            &arguments.leaf,
            &expected,
        )
        .await
    })
    .map_err(ServiceFailure::into_detail)?;
    emit_kv("LEAF_ATTACHED", "true");
    emit_kv("LEAF_ISSUE", &arguments.leaf.leaf.to_string());
    Ok(())
}

fn validate_gap(arguments: &ValidateGapArguments) -> Result<(), String> {
    require_issue(arguments.umbrella, "--umbrella")?;
    read_expected_audit_leaf(arguments.umbrella, &arguments.files)?;
    emit_kv("GAP_VALID", "true");
    emit_kv("UMBRELLA_ISSUE", &arguments.umbrella.to_string());
    Ok(())
}

fn read_expected_audit_leaf(
    umbrella: u64,
    arguments: &GapFileArguments,
) -> Result<ExpectedAuditLeaf, String> {
    let root = temporary_root(&arguments.root, "--expected-root")?;
    let expected_title = read_expected_file(
        &arguments.title_file,
        &arguments.root,
        &root,
        "--expected-title-file",
        256,
    )?;
    let expected_title = expected_title
        .strip_suffix('\n')
        .unwrap_or(expected_title.as_str());
    if expected_title.is_empty()
        || expected_title.len() > 80
        || expected_title.contains(['\r', '\n'])
        || expected_title.trim() != expected_title
        || expected_title.starts_with('-')
        || larch_core::has_managed_prefix(expected_title)
        || expected_title.starts_with(larch_core::UMBRELLA_PREFIX)
        || expected_title.starts_with("[LEAF OF ")
    {
        return Err(
            "expected leaf title must be one whitespace-trimmed, prefix-free, option-safe line of at most 80 bytes"
                .to_owned(),
        );
    }
    let expected_body = read_expected_file(
        &arguments.body_file,
        &arguments.root,
        &root,
        "--expected-body-file",
        64 * 1024,
    )?;
    if expected_body.is_empty() {
        return Err("expected leaf body must not be empty".to_owned());
    }
    if expected_body.lines().next() != Some(umbrella_leaf_opening(umbrella).as_str()) {
        return Err("expected leaf body lacks the exact umbrella opening".to_owned());
    }
    Ok(ExpectedAuditLeaf {
        remote_title: format!("{}{expected_title}", umbrella_leaf_prefix(umbrella)),
        body: expected_body,
    })
}

async fn attach_leaf_remote(
    service: &larch_adapters::github::OctocrabGitHubService,
    cancellation: &Cancellation,
    repository: &GitHubRepositoryRef,
    arguments: &LeafArguments,
    expected: &ExpectedAuditLeaf,
) -> Result<(), String> {
    let leaf = validate_attachment(service, cancellation, repository, arguments, expected).await?;
    apply_attachment(service, cancellation, repository, arguments, &leaf).await?;
    verify_attachment(service, cancellation, repository, arguments).await
}

async fn validate_attachment(
    service: &larch_adapters::github::OctocrabGitHubService,
    cancellation: &Cancellation,
    repository: &GitHubRepositoryRef,
    arguments: &LeafArguments,
    expected: &ExpectedAuditLeaf,
) -> Result<GitHubIssue, String> {
    let parent = service
        .issue(repository, arguments.umbrella, cancellation)
        .await
        .map_err(|error| error.to_string())?;
    validate_complete_umbrella_parent(&parent, true)?;
    require_top_level_umbrella(service, cancellation, repository, arguments.umbrella).await?;
    if !parent.title.starts_with(IMPLEMENTING_PREFIX) {
        return Err("parent is not active".to_owned());
    }
    let leaf = service
        .issue(repository, arguments.leaf, cancellation)
        .await
        .map_err(|error| error.to_string())?;
    if leaf.state != GitHubIssueState::Open {
        return Err("audit-created leaf must be open".to_owned());
    }
    validate_complete_umbrella_leaf(&leaf, arguments.umbrella)?;
    if leaf.title != expected.remote_title {
        return Err("audit-created leaf does not match the caller-owned title".to_owned());
    }
    if leaf.body != expected.body {
        return Err("audit-created leaf does not match the caller-owned body".to_owned());
    }
    if !service
        .list_sub_issues(
            cancellation,
            repository.owner(),
            repository.name(),
            leaf.number,
        )
        .await
        .map_err(|error| error.to_string())?
        .is_empty()
    {
        return Err("audit-created child is not a leaf".to_owned());
    }
    if service
        .parent_issue(
            cancellation,
            repository.owner(),
            repository.name(),
            leaf.number,
        )
        .await
        .map_err(|error| error.to_string())?
        .is_some_and(|parent| parent.issue_number() != arguments.umbrella)
    {
        return Err("audit-created child already belongs to another parent".to_owned());
    }
    Ok(leaf)
}

async fn apply_attachment(
    service: &larch_adapters::github::OctocrabGitHubService,
    cancellation: &Cancellation,
    repository: &GitHubRepositoryRef,
    arguments: &LeafArguments,
    leaf: &GitHubIssue,
) -> Result<(), String> {
    let authorization = operator_authorization();
    service
        .add_sub_issue(
            cancellation,
            &authorization,
            SubIssueEdge {
                owner: repository.owner(),
                repo: repository.name(),
                parent_issue: arguments.umbrella,
                sub_issue_id: leaf.id,
            },
        )
        .await
        .map_err(|error| error.to_string())?;
    let parent = service
        .issue(repository, arguments.umbrella, cancellation)
        .await
        .map_err(|error| error.to_string())?;
    validate_complete_umbrella_parent(&parent, true)?;
    service
        .add_blocked_by(
            cancellation,
            &authorization,
            DependencyEdge {
                owner: repository.owner(),
                repo: repository.name(),
                client_issue: arguments.umbrella,
                blocker_id: leaf.id,
                expected_updated_at: Some(&parent.updated_at),
            },
        )
        .await
        .map_err(|error| error.to_string())?;
    Ok(())
}

async fn verify_attachment(
    service: &larch_adapters::github::OctocrabGitHubService,
    cancellation: &Cancellation,
    repository: &GitHubRepositoryRef,
    arguments: &LeafArguments,
) -> Result<(), String> {
    let graph = read_graph(service, cancellation, repository, arguments.umbrella).await?;
    let attached = graph
        .leaves
        .iter()
        .any(|candidate| candidate.issue.number == arguments.leaf);
    let blocks_parent = service
        .list_blocked_by(
            cancellation,
            repository.owner(),
            repository.name(),
            arguments.umbrella,
        )
        .await
        .map_err(|error| error.to_string())?
        .iter()
        .any(|blocker| blocker.issue_number() == arguments.leaf);
    if attached && blocks_parent {
        Ok(())
    } else {
        Err("audit-created leaf graph read-back failed".to_owned())
    }
}

fn finish(arguments: &ParentMutationArguments) -> Result<(), String> {
    require_operator(arguments.operator_invoked)?;
    require_issue(arguments.issue, "--issue")?;
    let repository = parse_repository(&arguments.repository)?;
    with_github_service(async |service, cancellation| {
        let graph = read_graph(service, cancellation, &repository, arguments.issue).await?;
        if graph
            .leaves
            .iter()
            .any(|leaf| leaf.issue.state == GitHubIssueState::Open)
        {
            return Err("cannot finish while a direct leaf remains open".to_owned());
        }
        let done_title =
            complete_umbrella_done_title(&graph.parent.title).map_err(str::to_owned)?;
        if graph.parent.state == GitHubIssueState::Closed {
            if graph.parent.title != done_title {
                return Err("closed parent does not have the exact [DONE] title".to_owned());
            }
            return Ok(());
        }
        if graph.parent.state != GitHubIssueState::Open {
            return Err("parent lifecycle state is not concrete".to_owned());
        }
        let authorization = operator_authorization();
        if !check_live_mutation_auth(&authorization).is_authorized() {
            return Err("live mutation authorization was refused".to_owned());
        }
        let owner = IssueMutationOwner::new(service);
        let before = owner
            .read_snapshot(&repository, arguments.issue, cancellation)
            .await
            .map_err(|error| error.to_string())?;
        if before.state != GitHubIssueState::Open || !has_umbrella_proposal(&before.body) {
            return Err("parent changed before completion".to_owned());
        }
        let title = complete_umbrella_done_title(&before.title).map_err(str::to_owned)?;
        let request = exact_title_request(&before, title)?;
        owner
            .apply(cancellation, &authorization, &request)
            .await
            .map_err(|error| error.to_string())?;
        let before_close = read_graph(service, cancellation, &repository, arguments.issue).await?;
        if before_close
            .leaves
            .iter()
            .any(|leaf| leaf.issue.state == GitHubIssueState::Open)
            || before_close.parent.state != GitHubIssueState::Open
            || !before_close.parent.title.starts_with(DONE_PREFIX)
        {
            return Err("completion precondition changed before close".to_owned());
        }
        let closed = service
            .close_issue(
                &repository,
                arguments.issue,
                GitHubCloseReason::Completed,
                cancellation,
            )
            .await
            .map_err(|error| error.to_string())?;
        if closed.state != GitHubIssueState::Closed || !closed.title.starts_with(DONE_PREFIX) {
            return Err("parent close read-back failed".to_owned());
        }
        let final_graph = read_graph(service, cancellation, &repository, arguments.issue).await?;
        if final_graph.parent.state != GitHubIssueState::Closed
            || !final_graph.parent.title.starts_with(DONE_PREFIX)
            || final_graph
                .leaves
                .iter()
                .any(|leaf| leaf.issue.state == GitHubIssueState::Open)
        {
            return Err("final umbrella graph verification failed".to_owned());
        }
        Ok(())
    })
    .map_err(ServiceFailure::into_detail)?;
    emit_kv("UMBRELLA_FINISHED", "true");
    emit_kv("UMBRELLA_ISSUE", &arguments.issue.to_string());
    Ok(())
}

async fn read_graph(
    service: &larch_adapters::github::OctocrabGitHubService,
    cancellation: &Cancellation,
    repository: &GitHubRepositoryRef,
    umbrella: u64,
) -> Result<GraphState, String> {
    let parent = service
        .issue(repository, umbrella, cancellation)
        .await
        .map_err(|error| error.to_string())?;
    validate_complete_umbrella_parent(&parent, false)?;
    require_top_level_umbrella(service, cancellation, repository, umbrella).await?;
    let references = service
        .list_sub_issues(
            cancellation,
            repository.owner(),
            repository.name(),
            umbrella,
        )
        .await
        .map_err(|error| error.to_string())?;
    if references.len() > MAX_DIRECT_LEAVES {
        return Err(format!(
            "umbrella has more than {MAX_DIRECT_LEAVES} direct leaves"
        ));
    }
    let parent_blockers = service
        .list_blocked_by(
            cancellation,
            repository.owner(),
            repository.name(),
            umbrella,
        )
        .await
        .map_err(|error| error.to_string())?
        .into_iter()
        .map(|blocker| blocker.issue_number())
        .collect::<BTreeSet<_>>();
    if references
        .iter()
        .any(|leaf| !parent_blockers.contains(&leaf.issue_number()))
    {
        return Err("a direct leaf does not block its umbrella parent".to_owned());
    }
    let mut seen = BTreeSet::new();
    let mut leaves = Vec::with_capacity(references.len());
    for reference in references {
        if !seen.insert(reference.issue_number()) {
            return Err("GitHub returned a duplicate direct leaf".to_owned());
        }
        let issue = service
            .issue(repository, reference.issue_number(), cancellation)
            .await
            .map_err(|error| error.to_string())?;
        validate_complete_umbrella_leaf(&issue, umbrella)?;
        if issue.id != reference.issue_id() {
            return Err("direct leaf identity changed during graph read".to_owned());
        }
        if !service
            .list_sub_issues(
                cancellation,
                repository.owner(),
                repository.name(),
                issue.number,
            )
            .await
            .map_err(|error| error.to_string())?
            .is_empty()
        {
            return Err(format!("direct child #{} is not a leaf", issue.number));
        }
        let mut open_blockers = if issue.state == GitHubIssueState::Open {
            service
                .list_blocked_by(
                    cancellation,
                    repository.owner(),
                    repository.name(),
                    issue.number,
                )
                .await
                .map_err(|error| error.to_string())?
                .into_iter()
                .filter(larch_adapters::github::DependencyRef::is_open)
                .map(|blocker| blocker.issue_number())
                .collect::<Vec<_>>()
        } else {
            Vec::new()
        };
        open_blockers.sort_unstable();
        open_blockers.dedup();
        leaves.push(LeafState {
            issue,
            open_blockers,
        });
    }
    leaves.sort_by_key(|leaf| leaf.issue.number);
    Ok(GraphState { parent, leaves })
}

async fn require_top_level_umbrella(
    service: &larch_adapters::github::OctocrabGitHubService,
    cancellation: &Cancellation,
    repository: &GitHubRepositoryRef,
    umbrella: u64,
) -> Result<(), String> {
    if service
        .parent_issue(
            cancellation,
            repository.owner(),
            repository.name(),
            umbrella,
        )
        .await
        .map_err(|error| error.to_string())?
        .is_some()
    {
        return Err("nested umbrellas are not supported".to_owned());
    }
    Ok(())
}

fn exact_title_request(
    before: &larch_core::IssueMutationSnapshot,
    title: String,
) -> Result<IssueMutationRequest, String> {
    let request = IssueMutationRequest {
        repository: before.repository.clone(),
        issue: before.issue,
        expected_updated_at: before.updated_at.clone(),
        expected_state: before.state,
        fields: BTreeSet::from([IssueMutationField::Title]),
        title: Some(title),
        body: None,
        labels: None,
        marker: None,
        lease: None,
    };
    let redacted = redact_issue_mutation_request(&request).map_err(|error| error.to_string())?;
    if redacted.title != request.title {
        return Err("refusing a title transition that would alter title content".to_owned());
    }
    Ok(request)
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

fn require_operator(operator_invoked: bool) -> Result<(), String> {
    if operator_invoked {
        Ok(())
    } else {
        Err("--operator-invoked is required for live GitHub mutation".to_owned())
    }
}

fn require_issue(issue: u64, option: &str) -> Result<(), String> {
    if issue == 0 {
        Err(format!("{option} must be a positive integer"))
    } else {
        Ok(())
    }
}

fn parse_repository(value: &str) -> Result<GitHubRepositoryRef, String> {
    repository_ref(value).map_err(|()| "--repository must use valid OWNER/REPO form".to_owned())
}

fn canonical_directory(path: &Path, option: &str) -> Result<PathBuf, String> {
    let canonical = fs::canonicalize(path).map_err(|_| format!("{option} must exist"))?;
    let metadata = fs::symlink_metadata(path).map_err(|error| error.to_string())?;
    if metadata.file_type().is_symlink() || !canonical.is_dir() {
        return Err(format!("{option} must be a non-symlink directory"));
    }
    Ok(canonical)
}

fn temporary_root(path: &Path, option: &str) -> Result<TemporaryRoot, String> {
    if !path.is_absolute() {
        return Err(format!("{option} must be absolute"));
    }
    let root = TemporaryRoot::resolve(Some(path)).map_err(|error| format!("{option}: {error}"))?;
    let allowed = allowed_session_roots(
        env::var_os("XDG_CACHE_HOME").as_deref(),
        env::var_os("HOME").as_deref(),
    );
    if !is_allowed_session_tmpdir(root.path(), &allowed) {
        return Err(format!("{option} must be below an allowed session root"));
    }
    Ok(root)
}

fn confine_session_path(
    path: &Path,
    supplied_root: &Path,
    root: &TemporaryRoot,
    intent: PathIntent,
    option: &str,
) -> Result<ConfinedPath, String> {
    if !path.is_absolute() || !supplied_root.is_absolute() {
        return Err(format!("{option} must be absolute"));
    }
    let supplied_root = normalize_path(supplied_root).map_err(|error| error.to_string())?;
    let path = normalize_path(path).map_err(|error| error.to_string())?;
    let relative = path
        .strip_prefix(&supplied_root)
        .map_err(|_| format!("{option} escapes its trusted root"))?;
    if relative.as_os_str().is_empty() {
        return Err(format!("{option} must name a file below its trusted root"));
    }
    root.confine(relative, intent)
        .map_err(|error| format!("{option}: {error}"))
}

fn read_expected_file(
    path: &Path,
    supplied_root: &Path,
    root: &TemporaryRoot,
    option: &str,
    limit: u64,
) -> Result<String, String> {
    let confined = confine_session_path(path, supplied_root, root, PathIntent::Read, option)?;
    let file = open_confined_read(&confined).map_err(|error| error.to_string())?;
    let mut bytes = Vec::new();
    file.take(limit.saturating_add(1))
        .read_to_end(&mut bytes)
        .map_err(|error| error.to_string())?;
    if u64::try_from(bytes.len()).unwrap_or(u64::MAX) > limit {
        return Err(format!("{option} exceeds its byte limit"));
    }
    String::from_utf8(bytes).map_err(|_| format!("{option} must be valid UTF-8"))
}

fn write_audit_snapshot(arguments: &NextArguments, graph: &GraphState) -> Result<(), String> {
    let snapshot = AuditSnapshot {
        repository: arguments.repository.clone(),
        umbrella: audit_issue(&graph.parent),
        leaves: graph
            .leaves
            .iter()
            .map(|leaf| AuditLeaf {
                issue: audit_issue(&leaf.issue),
                open_blockers: leaf.open_blockers.clone(),
            })
            .collect(),
    };
    let text = serde_json::to_string_pretty(&snapshot).map_err(|error| error.to_string())?;
    let root = temporary_root(&arguments.output_root, "--output-root")?;
    write_private_file(
        &arguments.output,
        &format!("{text}\n"),
        &arguments.output_root,
        &root,
    )
}

fn audit_issue(issue: &GitHubIssue) -> AuditIssue {
    AuditIssue {
        number: issue.number,
        state: state_token(issue.state),
        url: redact(&issue.url).text().to_owned(),
        title_untrusted: redact(&issue.title).text().to_owned(),
        body_untrusted: redact(&issue.body).text().to_owned(),
    }
}

const fn state_token(state: GitHubIssueState) -> &'static str {
    match state {
        GitHubIssueState::Open => "open",
        GitHubIssueState::Closed => "closed",
        GitHubIssueState::All => "all",
    }
}

fn write_child_stderr(
    arguments: &RunChildArguments,
    root: &TemporaryRoot,
    execution: &larch_core::ProcessOutput,
) -> Result<(), String> {
    if execution.stderr().is_empty() {
        return Ok(());
    }
    let path = PathBuf::from(format!("{}.stderr", arguments.output.display()));
    let safe = execution.safe_stderr().to_string();
    write_private_file(&path, &safe, &arguments.output_root, root)
}

fn write_child_result(
    arguments: &RunChildArguments,
    root: &TemporaryRoot,
    leaf: u64,
    success: bool,
) -> Result<(), String> {
    let status = if success { "complete" } else { "failed" };
    let text = format!(
        "CHILD_STATUS={status}\nCHILD_ISSUE={leaf}\nCHILD_ENVELOPE_COMPLETE={}\n",
        if success { "true" } else { "false" }
    );
    write_private_file(&arguments.result_env, &text, &arguments.output_root, root)
}

fn write_private_file(
    path: &Path,
    text: &str,
    supplied_root: &Path,
    root: &TemporaryRoot,
) -> Result<(), String> {
    let confined = confine_session_path(path, supplied_root, root, PathIntent::Write, "output")?;
    atomic_write_utf8(&confined, text, 0o600).map_err(|error| error.to_string())
}

fn join_numbers(numbers: &[u64]) -> String {
    numbers
        .iter()
        .map(u64::to_string)
        .collect::<Vec<_>>()
        .join(" ")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn repository_and_positive_issue_inputs_fail_closed() {
        assert!(parse_repository("owner/repo").is_ok());
        assert!(parse_repository("../repo").is_err());
        assert!(require_issue(1, "--issue").is_ok());
        assert!(require_issue(0, "--issue").is_err());
        assert!(require_operator(false).is_err());
        assert!(temporary_root(Path::new("/"), "root").is_err());
    }

    #[cfg(unix)]
    #[test]
    fn expected_files_reject_symlinks_and_oversize_content() {
        use std::os::unix::fs::symlink;

        let directory = tempfile::tempdir().expect("temporary root");
        let root = temporary_root(directory.path(), "root").expect("trusted root");
        let real = directory.path().join("real.txt");
        fs::write(&real, "four").expect("fixture");
        let link = directory.path().join("link.txt");
        symlink(&real, &link).expect("symlink fixture");
        let real_directory = directory.path().join("real-directory");
        fs::create_dir(&real_directory).expect("directory fixture");
        fs::write(real_directory.join("nested.txt"), "four").expect("nested fixture");
        let linked_directory = directory.path().join("linked-directory");
        symlink(&real_directory, &linked_directory).expect("directory symlink fixture");
        let nested_link = linked_directory.join("nested.txt");

        assert!(read_expected_file(&link, directory.path(), &root, "file", 8).is_err());
        assert!(read_expected_file(&nested_link, directory.path(), &root, "file", 8).is_err());
        assert!(write_private_file(&link, "changed", directory.path(), &root).is_err());
        assert!(read_expected_file(&real, directory.path(), &root, "file", 3).is_err());
        assert_eq!(
            read_expected_file(&real, directory.path(), &root, "file", 4)
                .expect("bounded regular file"),
            "four"
        );
    }
}
