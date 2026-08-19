//! Rust composition root for `/complete-umbrella`.

use crate::{
    git_command_runtime::GitCommandRuntime,
    github_repository_resolution::repository_ref,
    github_service::{ServiceFailure, with_github_service},
    session_artifact_support::{
        canonical_directory, confine_session_path, read_expected_file, temporary_root,
        write_private_file,
    },
};
use clap::{Args, Subcommand};
use larch_adapters::{
    FetchRequest, GitRef, GitRefspec, GitRemote, GixRepository, PathIntent, RebaseRequest,
    TemporaryRoot, TokioProcessRunner,
    github::{
        DependencyEdge, IssueMutationOwner, LiveMutationRequest, SubIssueEdge,
        check_live_mutation_auth,
    },
    runtime::{Cancellation, LarchRuntime},
};
use larch_core::{
    COMPLETE_UMBRELLA_CHILD_COMPLETE, COMPLETE_UMBRELLA_CHILD_FAILURE_NEEDS_DESIGN,
    COMPLETE_UMBRELLA_CHILD_FAILURE_TRANSIENT_API, COMPLETE_UMBRELLA_CHILD_NEEDS_DESIGN,
    ChildEnvironment, CompleteUmbrellaLeaf, CompleteUmbrellaNext, DONE_PREFIX, DuplicatePolicy,
    EnvFile, ExternalProcessRunner, ExternalProgram, GitHubCloseReason, GitHubIssue,
    GitHubIssueState, GitHubRepositoryRef, GitHubService, Head, IMPLEMENTING_PREFIX,
    IssueMutationField, IssueMutationRequest, KvDocument, ParseOptions, ProcessRequest,
    RepositoryRead, StatusOptions, VendorLaunchRequest, VendorProgram, build_claude_argv,
    complete_umbrella_child_prompt, complete_umbrella_done_title, complete_umbrella_relaunch_title,
    complete_umbrella_start_title, emit_kv, has_umbrella_proposal, is_controlling_umbrella_title,
    is_transient_claude_api_error, parse_claude_envelope, redact, redact_issue_mutation_request,
    select_complete_umbrella_leaf, single_line, umbrella_leaf_opening, umbrella_leaf_prefix,
    validate_complete_umbrella_leaf, validate_complete_umbrella_parent,
};
use serde::Serialize;
#[cfg(test)]
use std::fs;
use std::{
    collections::BTreeSet,
    env,
    ffi::OsString,
    fmt::Write as _,
    num::NonZeroUsize,
    path::{Path, PathBuf},
    process::ExitCode,
    time::Duration,
};

const MAX_DIRECT_LEAVES: usize = 100;
const CHILD_TIMEOUT: Duration = Duration::from_secs(24 * 60 * 60);
const CHILD_SHUTDOWN_GRACE: Duration = Duration::from_secs(10);
const CHILD_OUTPUT_LIMIT: usize = 4 * 1024 * 1024;
const MAX_TRANSIENT_CHILD_RETRIES: u8 = 2;
const RUN_LEAVES_STEP: &str = "complete-umbrella-leaves";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum ChildResultStatus {
    Complete,
    NeedsDesign,
    Failed,
}

impl ChildResultStatus {
    const fn value(self) -> &'static str {
        match self {
            Self::Complete => "complete",
            Self::NeedsDesign => "needs-design",
            Self::Failed => "failed",
        }
    }

    const fn envelope_complete(self) -> bool {
        matches!(self, Self::Complete)
    }
}

fn child_terminal_status(text: &str) -> Option<ChildResultStatus> {
    let marker = text
        .lines()
        .rev()
        .find(|line| !line.trim().is_empty())?
        .trim();
    match marker {
        COMPLETE_UMBRELLA_CHILD_COMPLETE => Some(ChildResultStatus::Complete),
        COMPLETE_UMBRELLA_CHILD_NEEDS_DESIGN => Some(ChildResultStatus::NeedsDesign),
        _ => None,
    }
}

#[derive(Subcommand)]
pub enum CompleteUmbrellaCommand {
    /// Mark the parent active after validating its durable umbrella identity.
    Start(ParentMutationArguments),
    /// Fetch a fresh graph snapshot and select the next runnable leaf.
    Next(NextArguments),
    /// Run the deterministic leaf-selection, synchronization, child, and verification loop.
    #[command(name = "run-leaves")]
    RunLeaves(RunLeavesArguments),
    /// Run one leaf in the current Claude harness and model.
    #[command(name = "run-child")]
    RunChild(RunChildArguments),
    /// Prove that one child completed its remote lifecycle.
    #[command(name = "verify-child")]
    VerifyChild(LeafArguments),
    /// Recover an orphaned bgjob only when its exact leaf is already done.
    #[command(name = "recover-orphaned-child")]
    RecoverOrphanedChild(RecoverOrphanedChildArguments),
    /// Strip a stale `[IMPLEMENTING]` leaf prefix so selection can relaunch it.
    #[command(name = "reset-leaf")]
    ResetLeaf(ResetLeafArguments),
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
pub struct ResetLeafArguments {
    #[command(flatten)]
    leaf: LeafArguments,
    #[arg(long, action = clap::ArgAction::SetTrue)]
    operator_invoked: bool,
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
pub struct RunLeavesArguments {
    #[arg(long)]
    repository: String,
    #[arg(long)]
    repo_root: PathBuf,
    #[arg(long)]
    umbrella: u64,
    #[arg(long)]
    model: String,
    #[arg(long)]
    output_root: PathBuf,
    #[arg(long)]
    output: PathBuf,
    #[arg(long)]
    result_env: PathBuf,
    #[arg(long, action = clap::ArgAction::SetTrue)]
    operator_invoked: bool,
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
pub struct RecoverOrphanedChildArguments {
    #[command(flatten)]
    leaf: LeafArguments,
    #[arg(long = "expected-root")]
    root: PathBuf,
    #[arg(long = "result-env")]
    result_env: PathBuf,
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
    open_orphan_blockers: Vec<u64>,
}

struct ExpectedAuditLeaf {
    remote_title: String,
    body: String,
}

#[derive(Clone, Debug, Eq, PartialEq)]
enum ChildAttempt {
    Complete,
    NeedsDesign,
    TransientApi(String),
    Failed(String),
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct RunLeavesFailure {
    next_action: &'static str,
    step: &'static str,
    leaf: Option<u64>,
    reason: String,
}

impl RunLeavesFailure {
    fn failed(step: &'static str, leaf: Option<u64>, reason: impl AsRef<str>) -> Self {
        Self::new("failed", step, leaf, reason)
    }

    fn needs_design(leaf: u64) -> Self {
        Self::new(
            "needs-design",
            "run-child",
            Some(leaf),
            format!("leaf #{leaf} requires /design before implementation"),
        )
    }

    fn new(
        next_action: &'static str,
        step: &'static str,
        leaf: Option<u64>,
        reason: impl AsRef<str>,
    ) -> Self {
        let redacted = redact(reason.as_ref());
        let reason = single_line(redacted.text());
        Self {
            next_action,
            step,
            leaf,
            reason: if reason.is_empty() {
                "unspecified failure".to_owned()
            } else {
                reason
            },
        }
    }

    fn diagnostic(&self) -> String {
        self.leaf.map_or_else(
            || format!("failed at {}: {}", self.step, self.reason),
            |leaf| format!("failed at {} for leaf #{leaf}: {}", self.step, self.reason),
        )
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
enum RunLeavesEnvelope {
    Progress {
        action: &'static str,
        leaf: u64,
        completed: usize,
    },
    Audit {
        completed: usize,
    },
    Failure(RunLeavesFailure),
}

impl RunLeavesEnvelope {
    fn render(&self) -> Result<String, String> {
        const KEYS: &[&str] = &[
            "COMPLETED_LEAF_COUNT",
            "CURRENT_LEAF",
            "FAILED_LEAF",
            "FAILED_STEP",
            "FAILURE_REASON",
            "NEXT_ACTION",
            "OPEN_LEAF_COUNT",
            "SNAPSHOT_WRITTEN",
        ];
        let rows = match self {
            Self::Progress {
                action,
                leaf,
                completed,
            } => vec![
                ("NEXT_ACTION", (*action).to_owned()),
                ("CURRENT_LEAF", leaf.to_string()),
                ("COMPLETED_LEAF_COUNT", completed.to_string()),
            ],
            Self::Audit { completed } => vec![
                ("NEXT_ACTION", "audit".to_owned()),
                ("COMPLETED_LEAF_COUNT", completed.to_string()),
                ("OPEN_LEAF_COUNT", "0".to_owned()),
                ("SNAPSHOT_WRITTEN", "true".to_owned()),
            ],
            Self::Failure(failure) => vec![
                ("NEXT_ACTION", failure.next_action.to_owned()),
                ("FAILED_STEP", failure.step.to_owned()),
                (
                    "FAILED_LEAF",
                    failure
                        .leaf
                        .map_or_else(|| "0".to_owned(), |leaf| leaf.to_string()),
                ),
                ("FAILURE_REASON", failure.reason.clone()),
            ],
        };
        let borrowed = rows
            .iter()
            .map(|(key, value)| (*key, value.as_str()))
            .collect::<Vec<_>>();
        let mut environment = EnvFile::empty();
        environment
            .apply_guarded(&borrowed, KEYS)
            .map_err(|error| error.to_string())?;
        environment.render().map_err(|error| error.to_string())
    }
}

trait RunLeavesOperations {
    fn read_graph(&mut self) -> Result<GraphState, String>;
    fn write_snapshot(&mut self, graph: &GraphState) -> Result<(), String>;
    fn sync_main(&mut self) -> Result<(), String>;
    fn run_child(&mut self, leaf: u64) -> ChildAttempt;
    fn reset_leaf(&mut self, leaf: u64) -> Result<(), String>;
    fn write_result(&mut self, envelope: &RunLeavesEnvelope) -> Result<(), String>;
}

#[must_use]
pub fn run(command: CompleteUmbrellaCommand) -> ExitCode {
    let result = match command {
        CompleteUmbrellaCommand::Start(arguments) => start(&arguments),
        CompleteUmbrellaCommand::Next(arguments) => next(&arguments),
        CompleteUmbrellaCommand::RunLeaves(arguments) => run_leaves(&arguments),
        CompleteUmbrellaCommand::RunChild(arguments) => run_child(&arguments),
        CompleteUmbrellaCommand::VerifyChild(arguments) => verify_child(&arguments),
        CompleteUmbrellaCommand::RecoverOrphanedChild(arguments) => {
            recover_orphaned_child(&arguments)
        }
        CompleteUmbrellaCommand::ResetLeaf(arguments) => reset_leaf(&arguments),
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
        start_remote(service, cancellation, &repository, arguments.issue).await
    })
    .map_err(ServiceFailure::into_detail)?;
    emit_kv("UMBRELLA_STARTED", "true");
    emit_kv("UMBRELLA_ISSUE", &arguments.issue.to_string());
    Ok(())
}

async fn start_remote(
    service: &larch_adapters::github::OctocrabGitHubService,
    cancellation: &Cancellation,
    repository: &GitHubRepositoryRef,
    issue: u64,
) -> Result<(), String> {
    // Read the full leaf graph and confirm the umbrella is runnable before any
    // title mutation. A blocked (open non-leaf parent blocker) or deadlocked
    // (every open leaf blocked) umbrella keeps its plain [UMBRELLA] title
    // instead of stranding [IMPLEMENTING] with zero work and no active run
    // (#8663). read_graph also rejects nested umbrellas, subsuming the standalone
    // require_top_level_umbrella pre-check.
    let graph = read_graph(service, cancellation, repository, issue).await?;
    if graph.parent.state != GitHubIssueState::Open {
        return Err("umbrella target is not open".to_owned());
    }
    require_runnable_umbrella(&graph)?;
    let owner = IssueMutationOwner::new(service);
    let before = owner
        .read_snapshot(repository, issue, cancellation)
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
}

fn next(arguments: &NextArguments) -> Result<(), String> {
    require_issue(arguments.issue, "--issue")?;
    let repository = parse_repository(&arguments.repository)?;
    let graph = with_github_service(async |service, cancellation| {
        read_graph(service, cancellation, &repository, arguments.issue).await
    })
    .map_err(ServiceFailure::into_detail)?;
    emit_next(arguments, &graph)
}

fn run_leaves(arguments: &RunLeavesArguments) -> Result<(), String> {
    require_operator(arguments.operator_invoked)?;
    require_issue(arguments.umbrella, "--umbrella")?;
    validate_child_model(&arguments.model)?;
    let mut operations = LiveRunLeavesOperations::new(arguments)?;
    match execute_run_leaves(&mut operations) {
        Ok(completed) => {
            emit_kv("NEXT_ACTION", "audit");
            emit_kv("COMPLETED_LEAF_COUNT", &completed.to_string());
            emit_kv("OPEN_LEAF_COUNT", "0");
            emit_kv("SNAPSHOT_WRITTEN", "true");
            Ok(())
        }
        Err(failure) => Err(failure.diagnostic()),
    }
}

fn execute_run_leaves(
    operations: &mut impl RunLeavesOperations,
) -> Result<usize, RunLeavesFailure> {
    match drive_run_leaves(operations) {
        Ok(completed) => {
            let envelope = RunLeavesEnvelope::Audit { completed };
            operations
                .write_result(&envelope)
                .map_err(|error| RunLeavesFailure::failed("write-result", None, error))?;
            Ok(completed)
        }
        Err(failure) => {
            let envelope = RunLeavesEnvelope::Failure(failure.clone());
            if let Err(error) = operations.write_result(&envelope) {
                return Err(RunLeavesFailure::failed(
                    "write-result",
                    failure.leaf,
                    format!("{error}; original failure: {}", failure.diagnostic()),
                ));
            }
            Err(failure)
        }
    }
}

fn drive_run_leaves(operations: &mut impl RunLeavesOperations) -> Result<usize, RunLeavesFailure> {
    let mut pending_verification = None;
    let mut completed = 0;
    loop {
        let graph = operations
            .read_graph()
            .map_err(|error| RunLeavesFailure::failed("read-graph", pending_verification, error))?;
        if let Some(leaf) = pending_verification.take() {
            verify_child_in_graph(&graph, leaf)
                .map_err(|error| RunLeavesFailure::failed("verify-child", Some(leaf), error))?;
            completed += 1;
        }
        let Some(leaf) = select_run_leaves_leaf(operations, &graph)? else {
            return Ok(completed);
        };
        run_selected_leaf(operations, leaf, completed)?;
        pending_verification = Some(leaf);
    }
}

fn select_run_leaves_leaf(
    operations: &mut impl RunLeavesOperations,
    graph: &GraphState,
) -> Result<Option<u64>, RunLeavesFailure> {
    require_active_parent(graph)
        .map_err(|error| RunLeavesFailure::failed("select-leaf", None, error))?;
    let selection = select_complete_umbrella_leaf(
        &selection_leaves(&graph.leaves),
        &graph.open_orphan_blockers,
    );
    let selected_leaf = match &selection {
        CompleteUmbrellaNext::Launch(leaf) => Some(*leaf),
        CompleteUmbrellaNext::Deadlocked(leaves) => leaves.first().copied(),
        CompleteUmbrellaNext::Audit | CompleteUmbrellaNext::OrphanBlocked(_) => None,
    };
    operations
        .write_snapshot(graph)
        .map_err(|error| RunLeavesFailure::failed("write-snapshot", selected_leaf, error))?;
    match selection {
        CompleteUmbrellaNext::Launch(leaf) => Ok(Some(leaf)),
        CompleteUmbrellaNext::Audit => Ok(None),
        CompleteUmbrellaNext::OrphanBlocked(issues) => Err(RunLeavesFailure::failed(
            "select-leaf",
            None,
            format!(
                "open non-leaf parent blockers remain: {}",
                join_numbers(&issues)
            ),
        )),
        CompleteUmbrellaNext::Deadlocked(issues) => Err(RunLeavesFailure::failed(
            "select-leaf",
            issues.first().copied(),
            format!(
                "all open leaves are blocked or active: {}",
                join_numbers(&issues)
            ),
        )),
    }
}

fn run_selected_leaf(
    operations: &mut impl RunLeavesOperations,
    leaf: u64,
    completed: usize,
) -> Result<(), RunLeavesFailure> {
    write_run_leaves_progress(operations, "launch", leaf, completed)?;
    operations
        .sync_main()
        .map_err(|error| RunLeavesFailure::failed("sync-before-child", Some(leaf), error))?;
    run_child_attempts(operations, leaf, completed)?;
    operations
        .sync_main()
        .map_err(|error| RunLeavesFailure::failed("sync-after-child", Some(leaf), error))?;
    write_run_leaves_progress(operations, "verify", leaf, completed)
}

fn run_child_attempts(
    operations: &mut impl RunLeavesOperations,
    leaf: u64,
    completed: usize,
) -> Result<(), RunLeavesFailure> {
    let mut transient_retries = 0;
    loop {
        match operations.run_child(leaf) {
            ChildAttempt::Complete => return Ok(()),
            ChildAttempt::NeedsDesign => {
                operations.reset_leaf(leaf).map_err(|error| {
                    RunLeavesFailure::failed(
                        "reset-leaf",
                        Some(leaf),
                        format!("needs-design reset failed: {error}"),
                    )
                })?;
                return Err(RunLeavesFailure::needs_design(leaf));
            }
            ChildAttempt::TransientApi(_reason)
                if transient_retries < MAX_TRANSIENT_CHILD_RETRIES =>
            {
                transient_retries += 1;
                operations.reset_leaf(leaf).map_err(|error| {
                    RunLeavesFailure::failed(
                        "reset-leaf",
                        Some(leaf),
                        format!("transient child reset failed: {error}"),
                    )
                })?;
                write_run_leaves_progress(operations, "launch", leaf, completed)?;
                operations.sync_main().map_err(|error| {
                    RunLeavesFailure::failed("sync-before-retry", Some(leaf), error)
                })?;
            }
            ChildAttempt::TransientApi(reason) => {
                operations.reset_leaf(leaf).map_err(|error| {
                    RunLeavesFailure::failed(
                        "reset-leaf",
                        Some(leaf),
                        format!("exhausted transient child reset failed: {error}"),
                    )
                })?;
                return Err(RunLeavesFailure::failed(
                    "run-child",
                    Some(leaf),
                    format!(
                        "transient Claude API failure persisted after {} attempts: {reason}",
                        MAX_TRANSIENT_CHILD_RETRIES + 1
                    ),
                ));
            }
            ChildAttempt::Failed(reason) => {
                return Err(RunLeavesFailure::failed("run-child", Some(leaf), reason));
            }
        }
    }
}

fn write_run_leaves_progress(
    operations: &mut impl RunLeavesOperations,
    action: &'static str,
    leaf: u64,
    completed: usize,
) -> Result<(), RunLeavesFailure> {
    operations
        .write_result(&RunLeavesEnvelope::Progress {
            action,
            leaf,
            completed,
        })
        .map_err(|error| RunLeavesFailure::failed("write-result", Some(leaf), error))
}

struct LiveRunLeavesOperations<'a> {
    arguments: &'a RunLeavesArguments,
    repository: GitHubRepositoryRef,
    repo_root: PathBuf,
    output_root: TemporaryRoot,
    driver_root: PathBuf,
}

impl<'a> LiveRunLeavesOperations<'a> {
    fn new(arguments: &'a RunLeavesArguments) -> Result<Self, String> {
        let repository = parse_repository(&arguments.repository)?;
        let repo_root = canonical_directory(&arguments.repo_root, "--repo-root")?;
        let output_root = temporary_root(&arguments.output_root, "--output-root")?;
        let output = confine_session_path(
            &arguments.output,
            &arguments.output_root,
            &output_root,
            PathIntent::Write,
            "--output",
        )?;
        let result_env = confine_session_path(
            &arguments.result_env,
            &arguments.output_root,
            &output_root,
            PathIntent::Write,
            "--result-env",
        )?;
        if output.path() == result_env.path() {
            return Err("--output and --result-env must be different files".to_owned());
        }
        let driver_root = output_root
            .ensure_directory("complete-umbrella-run-leaves")
            .map_err(|error| format!("could not create run-leaves state root: {error}"))?;
        if output.path().starts_with(&driver_root) || result_env.path().starts_with(&driver_root) {
            return Err("caller-owned output files must not overlap run-leaves state".to_owned());
        }
        Ok(Self {
            arguments,
            repository,
            repo_root,
            output_root,
            driver_root,
        })
    }

    fn child_arguments(&self, leaf: u64) -> RunChildArguments {
        RunChildArguments {
            repository: self.arguments.repository.clone(),
            repo_root: self.repo_root.clone(),
            umbrella: self.arguments.umbrella,
            leaf,
            model: self.arguments.model.clone(),
            output_root: self.arguments.output_root.clone(),
            output: self.driver_root.join(format!("child-{leaf}.json")),
            result_env: self.driver_root.join(format!("child-{leaf}.env")),
        }
    }
}

impl RunLeavesOperations for LiveRunLeavesOperations<'_> {
    fn read_graph(&mut self) -> Result<GraphState, String> {
        with_github_service(async |service, cancellation| {
            read_graph(
                service,
                cancellation,
                &self.repository,
                self.arguments.umbrella,
            )
            .await
        })
        .map_err(ServiceFailure::into_detail)
    }

    fn write_snapshot(&mut self, graph: &GraphState) -> Result<(), String> {
        write_audit_snapshot_to(
            &self.arguments.repository,
            &self.arguments.output_root,
            &self.arguments.output,
            graph,
        )
    }

    fn sync_main(&mut self) -> Result<(), String> {
        synchronize_main(&self.repo_root)
    }

    fn run_child(&mut self, leaf: u64) -> ChildAttempt {
        let arguments = self.child_arguments(leaf);
        if let Err(error) = write_private_file(
            &arguments.result_env,
            "",
            &arguments.output_root,
            &self.output_root,
        ) {
            return ChildAttempt::Failed(format!(
                "could not clear the prior child result before launch: {error}"
            ));
        }
        let execution = run_child(&arguments);
        let result = read_expected_file(
            &arguments.result_env,
            &arguments.output_root,
            &self.output_root,
            "child result env",
            64 * 1024,
        );
        classify_child_attempt(leaf, execution, result)
    }

    fn reset_leaf(&mut self, leaf: u64) -> Result<(), String> {
        let arguments = LeafArguments {
            repository: self.arguments.repository.clone(),
            umbrella: self.arguments.umbrella,
            leaf,
        };
        with_github_service(async |service, cancellation| {
            reset_leaf_remote(service, cancellation, &self.repository, &arguments).await
        })
        .map_err(ServiceFailure::into_detail)
    }

    fn write_result(&mut self, envelope: &RunLeavesEnvelope) -> Result<(), String> {
        let text = envelope.render()?;
        write_private_file(
            &self.arguments.result_env,
            &text,
            &self.arguments.output_root,
            &self.output_root,
        )
    }
}

fn classify_child_attempt(
    leaf: u64,
    execution: Result<(), String>,
    result: Result<String, String>,
) -> ChildAttempt {
    let execution_error = execution.err();
    let text = match result {
        Ok(text) => text,
        Err(error) => {
            return ChildAttempt::Failed(execution_error.map_or_else(
                || format!("child result env is unavailable: {error}"),
                |process_error| {
                    format!("{process_error}; child result env is unavailable: {error}")
                },
            ));
        }
    };
    let environment = match EnvFile::parse(&text) {
        Ok(environment) => environment,
        Err(error) => {
            return ChildAttempt::Failed(execution_error.map_or_else(
                || format!("child result env is malformed: {error}"),
                |process_error| format!("{process_error}; child result env is malformed: {error}"),
            ));
        }
    };
    let values = environment.values();
    let expected_leaf = leaf.to_string();
    if values.get("CHILD_ISSUE") != Some(&expected_leaf) {
        return ChildAttempt::Failed("child result carries another leaf identity".to_owned());
    }
    let status = values.get("CHILD_STATUS").map(String::as_str);
    let complete = values.get("CHILD_ENVELOPE_COMPLETE").map(String::as_str);
    let class = values.get("CHILD_FAILURE_CLASS").map(String::as_str);
    match (execution_error, status, complete, class) {
        (None, Some("complete"), Some("true"), None) => ChildAttempt::Complete,
        (
            None,
            Some("needs-design"),
            Some("false"),
            Some(COMPLETE_UMBRELLA_CHILD_FAILURE_NEEDS_DESIGN),
        ) => ChildAttempt::NeedsDesign,
        (
            Some(reason),
            Some("failed"),
            Some("false"),
            Some(COMPLETE_UMBRELLA_CHILD_FAILURE_TRANSIENT_API),
        ) => ChildAttempt::TransientApi(reason),
        (Some(reason), Some("failed"), Some("false"), None) => ChildAttempt::Failed(reason),
        (Some(reason), _, _, _) => ChildAttempt::Failed(format!(
            "{reason}; child result env has an invalid failure shape"
        )),
        (None, _, _, _) => {
            ChildAttempt::Failed("child result env has an invalid success shape".to_owned())
        }
    }
}

fn synchronize_main(repo_root: &Path) -> Result<(), String> {
    require_clean_main(repo_root, "before synchronization")?;
    let remote = GitRemote::new("origin").map_err(|error| error.to_string())?;
    let refspec = GitRefspec::new("refs/heads/main:refs/remotes/origin/main")
        .map_err(|error| error.to_string())?;
    let upstream = GitRef::new("origin/main").map_err(|error| error.to_string())?;
    let runtime = GitCommandRuntime::for_repository(repo_root)?;
    runtime
        .runtime
        .block_on(runtime.git_cli().fetch(
            FetchRequest {
                remote,
                refspec: Some(refspec),
                quiet: true,
                no_tags: true,
            },
            &runtime.cancellation,
        ))
        .map_err(|error| format!("git fetch origin/main failed: {error}"))?;
    if let Err(error) = runtime.runtime.block_on(runtime.git_cli().rebase(
        RebaseRequest::Start {
            onto: None,
            upstream,
            branch: None,
        },
        &runtime.cancellation,
    )) {
        let abort = runtime
            .runtime
            .block_on(
                runtime
                    .git_cli()
                    .rebase(RebaseRequest::Abort, &runtime.cancellation),
            )
            .map_or_else(
                |abort_error| format!("rebase abort failed: {abort_error}"),
                |_output| "rebase aborted".to_owned(),
            );
        return Err(format!("git rebase origin/main failed: {error}; {abort}"));
    }
    require_clean_main(repo_root, "after synchronization")?;
    let repository = GixRepository::open(repo_root)
        .map_err(|error| format!("cannot reopen repository after synchronization: {error}"))?;
    let head = repository
        .resolve_revision(&larch_core::Revision::new("HEAD"))
        .map_err(|error| format!("cannot resolve HEAD after synchronization: {error}"))?;
    let origin = repository
        .resolve_revision(&larch_core::Revision::new("origin/main"))
        .map_err(|error| format!("cannot resolve origin/main after synchronization: {error}"))?;
    if head != origin {
        return Err("HEAD does not equal origin/main after synchronization".to_owned());
    }
    Ok(())
}

fn require_clean_main(repo_root: &Path, phase: &str) -> Result<(), String> {
    let repository = GixRepository::open(repo_root)
        .map_err(|error| format!("cannot open repository {phase}: {error}"))?;
    let head = repository
        .head()
        .map_err(|error| format!("cannot read HEAD {phase}: {error}"))?;
    let Head::Symbolic { name, .. } = head else {
        return Err(format!("repository is not on branch main {phase}"));
    };
    if name.as_bytes() != b"refs/heads/main" {
        return Err(format!("repository is not on branch main {phase}"));
    }
    let status = repository
        .local_status(&StatusOptions::default())
        .map_err(|error| format!("cannot read working-tree status {phase}: {error}"))?;
    if status.is_dirty() {
        return Err(format!("working tree is not clean {phase}"));
    }
    Ok(())
}

fn emit_next(arguments: &NextArguments, graph: &GraphState) -> Result<(), String> {
    require_active_parent(graph)?;
    let selection_input = selection_leaves(&graph.leaves);
    let selection = select_complete_umbrella_leaf(&selection_input, &graph.open_orphan_blockers);
    write_audit_snapshot(arguments, graph)?;
    for (key, value) in next_action_fields(&selection) {
        emit_kv(key, &value);
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

fn selection_leaves(leaves: &[LeafState]) -> Vec<CompleteUmbrellaLeaf> {
    leaves
        .iter()
        .map(|leaf| CompleteUmbrellaLeaf {
            number: leaf.issue.number,
            open: leaf.issue.state == GitHubIssueState::Open,
            implementing: leaf.issue.title.starts_with(IMPLEMENTING_PREFIX),
            open_blockers: leaf.open_blockers.clone(),
        })
        .collect()
}

fn require_active_parent(graph: &GraphState) -> Result<(), String> {
    if graph.parent.state == GitHubIssueState::Open
        && graph.parent.title.starts_with(IMPLEMENTING_PREFIX)
    {
        Ok(())
    } else {
        Err("parent must be open with the [IMPLEMENTING] prefix".to_owned())
    }
}

fn verify_child_in_graph(graph: &GraphState, leaf_number: u64) -> Result<(), String> {
    let Some(leaf) = graph
        .leaves
        .iter()
        .find(|leaf| leaf.issue.number == leaf_number)
    else {
        return Err("child is not a direct leaf of the umbrella".to_owned());
    };
    let done_prefix = format!("{DONE_PREFIX}{}", umbrella_leaf_prefix(graph.parent.number));
    if leaf.issue.state == GitHubIssueState::Closed && leaf.issue.title.starts_with(&done_prefix) {
        Ok(())
    } else {
        Err("child must be closed with the exact [DONE] leaf prefix".to_owned())
    }
}

fn next_action_fields(selection: &CompleteUmbrellaNext) -> Vec<(&'static str, String)> {
    match selection {
        CompleteUmbrellaNext::Launch(issue) => vec![
            ("NEXT_ACTION", "launch".to_owned()),
            ("NEXT_LEAF", issue.to_string()),
        ],
        CompleteUmbrellaNext::Audit => vec![("NEXT_ACTION", "audit".to_owned())],
        CompleteUmbrellaNext::OrphanBlocked(issues) => vec![
            ("NEXT_ACTION", "orphan-blocker".to_owned()),
            ("ORPHAN_BLOCKERS", join_numbers(issues)),
        ],
        CompleteUmbrellaNext::Deadlocked(issues) => vec![
            ("NEXT_ACTION", "deadlock".to_owned()),
            ("BLOCKED_LEAVES", join_numbers(issues)),
        ],
    }
}

fn run_child(arguments: &RunChildArguments) -> Result<(), String> {
    require_issue(arguments.umbrella, "--umbrella")?;
    require_issue(arguments.leaf, "--leaf")?;
    let repository = parse_repository(&arguments.repository)?;
    validate_child_model(&arguments.model)?;
    let repo_root = canonical_directory(&arguments.repo_root, "--repo-root")?;
    let output_root = temporary_root(&arguments.output_root, "--output-root")?;
    let handoff_root = output_root
        .ensure_directory(format!("complete-umbrella-leaf-{}", arguments.leaf))
        .map_err(|error| format!("could not create leaf handoff root: {error}"))?;
    let handoff_root_text = handoff_root
        .to_str()
        .ok_or("leaf handoff root must be valid UTF-8")?;
    if handoff_root_text
        .chars()
        .any(|character| matches!(character, '\n' | '\r'))
    {
        return Err("leaf handoff root must not contain line breaks".to_owned());
    }
    let prompt = complete_umbrella_child_prompt(
        &format!("{}/{}", repository.owner(), repository.name()),
        arguments.umbrella,
        arguments.leaf,
        handoff_root_text,
    );
    let repo_root_text = repo_root
        .to_str()
        .ok_or("--repo-root must be valid UTF-8")?
        .to_owned();
    let mut launch = VendorLaunchRequest::new(&repo_root_text, "", prompt.clone());
    launch.model.clone_from(&arguments.model);
    let argv = build_claude_argv("workflow-write-orchestrator", &launch)
        .map_err(|error| error.to_string())?;
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
    .with_environment(ChildEnvironment::ClaudeSubprocessHookExempt, "1")
    .with_environment(ChildEnvironment::ClaudeProjectDir, repo_root_text)
    .with_environment(ChildEnvironment::SessionTmpdir, handoff_root);
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
            write_child_result(
                arguments,
                &output_root,
                arguments.leaf,
                ChildResultStatus::Failed,
                None,
            )?;
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
    finish_child_envelope(arguments, &output_root, &execution, &raw)
}

fn validate_child_model(model: &str) -> Result<(), String> {
    if model == "unknown" || model.is_empty() || model.chars().any(char::is_whitespace) {
        Err("--model must be one resolved non-whitespace token".to_owned())
    } else {
        Ok(())
    }
}

fn finish_child_envelope(
    arguments: &RunChildArguments,
    output_root: &TemporaryRoot,
    execution: &larch_core::ProcessOutput,
    raw: &str,
) -> Result<(), String> {
    let parsed = parse_claude_envelope(raw);
    let result_status = child_terminal_status(&parsed.text);
    let has_bounded_status = matches!(
        result_status,
        Some(ChildResultStatus::Complete | ChildResultStatus::NeedsDesign)
    );
    let bounded = execution.status().success()
        && !execution.stdout_truncated()
        && !execution.stderr_truncated()
        && has_bounded_status;
    let result_status = result_status.unwrap_or(ChildResultStatus::Failed);
    let failure_class = if bounded && result_status == ChildResultStatus::NeedsDesign {
        Some(COMPLETE_UMBRELLA_CHILD_FAILURE_NEEDS_DESIGN)
    } else if bounded {
        None
    } else if is_transient_claude_api_error(&parsed) {
        Some(COMPLETE_UMBRELLA_CHILD_FAILURE_TRANSIENT_API)
    } else {
        None
    };
    write_child_result(
        arguments,
        output_root,
        arguments.leaf,
        result_status,
        failure_class,
    )?;
    if !bounded {
        return Err(if failure_class.is_some() {
            "child ended on a transient Claude API failure".to_owned()
        } else {
            "child did not return a complete, bounded success envelope".to_owned()
        });
    }
    emit_kv("CHILD_STATUS", result_status.value());
    emit_kv("CHILD_ISSUE", &arguments.leaf.to_string());
    Ok(())
}

fn verify_child(arguments: &LeafArguments) -> Result<(), String> {
    require_issue(arguments.umbrella, "--umbrella")?;
    require_issue(arguments.leaf, "--leaf")?;
    let repository = parse_repository(&arguments.repository)?;
    with_github_service(async |service, cancellation| {
        verify_child_remote(service, cancellation, &repository, arguments).await
    })
    .map_err(ServiceFailure::into_detail)?;
    emit_kv("CHILD_VERIFIED", "true");
    emit_kv("CHILD_ISSUE", &arguments.leaf.to_string());
    Ok(())
}

fn recover_orphaned_child(arguments: &RecoverOrphanedChildArguments) -> Result<(), String> {
    require_issue(arguments.leaf.umbrella, "--umbrella")?;
    require_issue(arguments.leaf.leaf, "--leaf")?;
    let repository = parse_repository(&arguments.leaf.repository)?;
    let root = temporary_root(&arguments.root, "--expected-root")?;
    let result = read_expected_file(
        &arguments.result_env,
        &arguments.root,
        &root,
        "--result-env",
        64 * 1024,
    )?;
    with_github_service(async |service, cancellation| {
        recover_orphaned_child_remote(service, cancellation, &repository, &arguments.leaf, &result)
            .await
    })
    .map_err(ServiceFailure::into_detail)?;
    emit_kv("CHILD_RECOVERED", "true");
    emit_kv("CHILD_ISSUE", &arguments.leaf.leaf.to_string());
    Ok(())
}

async fn recover_orphaned_child_remote(
    service: &larch_adapters::github::OctocrabGitHubService,
    cancellation: &Cancellation,
    repository: &GitHubRepositoryRef,
    arguments: &LeafArguments,
    result: &str,
) -> Result<(), String> {
    validate_orphaned_child_result(result, arguments.leaf)?;
    verify_child_remote(service, cancellation, repository, arguments).await
}

fn validate_orphaned_child_result(text: &str, leaf: u64) -> Result<(), String> {
    let document = KvDocument::parse(text, ParseOptions::environment())
        .map_err(|error| format!("orphaned child result is malformed: {error}"))?;
    let values = document.select(DuplicatePolicy::Last);
    if values.get("BGJOB_RC").map(String::as_str) != Some("orphaned") {
        return Err("child recovery requires BGJOB_RC=orphaned".to_owned());
    }
    let expected_leaf = leaf.to_string();
    if values
        .get("CHILD_ISSUE")
        .is_some_and(|issue| issue != &expected_leaf)
    {
        return Err("orphaned child result carries another leaf identity".to_owned());
    }
    let legacy_step = format!("complete-umbrella-leaf-{leaf}");
    if values.get("STEP") == Some(&legacy_step) {
        return Ok(());
    }
    if values.get("STEP").map(String::as_str) != Some(RUN_LEAVES_STEP) {
        return Err("orphaned child result does not match the leaf driver step".to_owned());
    }
    if values.get("CURRENT_LEAF") != Some(&expected_leaf) {
        return Err("orphaned leaf driver result carries another current leaf".to_owned());
    }
    match values.get("NEXT_ACTION").map(String::as_str) {
        Some("launch" | "verify") => Ok(()),
        _ => Err("orphaned leaf driver result has no recoverable child action".to_owned()),
    }
}

fn reset_leaf(arguments: &ResetLeafArguments) -> Result<(), String> {
    require_operator(arguments.operator_invoked)?;
    require_issue(arguments.leaf.umbrella, "--umbrella")?;
    require_issue(arguments.leaf.leaf, "--leaf")?;
    let repository = parse_repository(&arguments.leaf.repository)?;
    with_github_service(async |service, cancellation| {
        reset_leaf_remote(service, cancellation, &repository, &arguments.leaf).await
    })
    .map_err(ServiceFailure::into_detail)?;
    emit_kv("LEAF_RESET", "true");
    emit_kv("LEAF_ISSUE", &arguments.leaf.leaf.to_string());
    Ok(())
}

async fn reset_leaf_remote(
    service: &larch_adapters::github::OctocrabGitHubService,
    cancellation: &Cancellation,
    repository: &GitHubRepositoryRef,
    arguments: &LeafArguments,
) -> Result<(), String> {
    let graph = read_graph(service, cancellation, repository, arguments.umbrella).await?;
    let Some(leaf) = graph
        .leaves
        .iter()
        .find(|leaf| leaf.issue.number == arguments.leaf)
    else {
        return Err("child is not a direct leaf of the umbrella".to_owned());
    };
    if leaf.issue.state != GitHubIssueState::Open {
        return Err("leaf must be open to reset its active title".to_owned());
    }
    validate_complete_umbrella_leaf(&leaf.issue, arguments.umbrella)?;
    let title = complete_umbrella_relaunch_title(&leaf.issue.title, arguments.umbrella)
        .map_err(str::to_owned)?;
    if title == leaf.issue.title {
        return Ok(());
    }
    let owner = IssueMutationOwner::new(service);
    let before = owner
        .read_snapshot(repository, arguments.leaf, cancellation)
        .await
        .map_err(|error| error.to_string())?;
    if before.state != GitHubIssueState::Open {
        return Err("leaf changed before the relaunch-title mutation".to_owned());
    }
    let expected = complete_umbrella_relaunch_title(&before.title, arguments.umbrella)
        .map_err(str::to_owned)?;
    if expected != title {
        return Err("leaf title changed before the relaunch-title mutation".to_owned());
    }
    let request = exact_title_request(&before, title.clone())?;
    let verified = owner
        .apply(cancellation, &operator_authorization(), &request)
        .await
        .map_err(|error| error.to_string())?;
    if verified.after.state != GitHubIssueState::Open || verified.after.title != title {
        return Err("idle leaf title read-back failed".to_owned());
    }
    Ok(())
}

async fn verify_child_remote(
    service: &larch_adapters::github::OctocrabGitHubService,
    cancellation: &Cancellation,
    repository: &GitHubRepositoryRef,
    arguments: &LeafArguments,
) -> Result<(), String> {
    let graph = read_graph(service, cancellation, repository, arguments.umbrella).await?;
    verify_child_in_graph(&graph, arguments.leaf)
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
    if !parent.title.starts_with(IMPLEMENTING_PREFIX) {
        return Err("parent changed before dependency attachment".to_owned());
    }
    service
        .add_blocked_by(
            cancellation,
            &authorization,
            DependencyEdge {
                owner: repository.owner(),
                repo: repository.name(),
                client_issue: arguments.umbrella,
                blocker_id: leaf.id,
                expected_updated_at: None,
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
        finish_remote(service, cancellation, &repository, arguments.issue).await
    })
    .map_err(ServiceFailure::into_detail)?;
    emit_kv("UMBRELLA_FINISHED", "true");
    emit_kv("UMBRELLA_ISSUE", &arguments.issue.to_string());
    Ok(())
}

async fn finish_remote(
    service: &larch_adapters::github::OctocrabGitHubService,
    cancellation: &Cancellation,
    repository: &GitHubRepositoryRef,
    issue: u64,
) -> Result<(), String> {
    let graph = read_graph(service, cancellation, repository, issue).await?;
    require_no_open_orphan_blockers(&graph)?;
    if graph
        .leaves
        .iter()
        .any(|leaf| leaf.issue.state == GitHubIssueState::Open)
    {
        return Err("cannot finish while a direct leaf remains open".to_owned());
    }
    let done_title = complete_umbrella_done_title(&graph.parent.title).map_err(str::to_owned)?;
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
        .read_snapshot(repository, issue, cancellation)
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
    let before_close = read_graph(service, cancellation, repository, issue).await?;
    require_no_open_orphan_blockers(&before_close)?;
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
            repository,
            issue,
            GitHubCloseReason::Completed,
            cancellation,
        )
        .await
        .map_err(|error| error.to_string())?;
    if closed.state != GitHubIssueState::Closed || !closed.title.starts_with(DONE_PREFIX) {
        return Err("parent close read-back failed".to_owned());
    }
    let final_graph = read_graph(service, cancellation, repository, issue).await?;
    require_no_open_orphan_blockers(&final_graph)?;
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
    let open_orphan_blockers =
        read_open_orphan_blockers(service, cancellation, repository, umbrella, &references).await?;
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
        if is_controlling_umbrella_title(&issue.title) {
            return Err("nested umbrellas are not supported".to_owned());
        }
        // Closed leaves are already resolved: exclude them from candidacy and
        // do not fail closed on lifecycle-title drift. Strict [DONE] identity
        // remains on verify-child for the leaf this run just shipped, and on
        // open-leaf validation below.
        if issue.state == GitHubIssueState::Open {
            validate_complete_umbrella_leaf(&issue, umbrella)?;
        } else if issue.is_pull_request {
            return Err(format!("direct child #{} is a pull request", issue.number));
        }
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
    Ok(GraphState {
        parent,
        leaves,
        open_orphan_blockers,
    })
}

async fn read_open_orphan_blockers(
    service: &larch_adapters::github::OctocrabGitHubService,
    cancellation: &Cancellation,
    repository: &GitHubRepositoryRef,
    umbrella: u64,
    references: &[larch_adapters::github::SubIssueRef],
) -> Result<Vec<u64>, String> {
    let parent_blockers = service
        .list_blocked_by(
            cancellation,
            repository.owner(),
            repository.name(),
            umbrella,
        )
        .await
        .map_err(|error| error.to_string())?;
    let parent_blocker_numbers = parent_blockers
        .iter()
        .map(larch_adapters::github::DependencyRef::issue_number)
        .collect::<BTreeSet<_>>();
    let direct_leaf_numbers = references
        .iter()
        .map(larch_adapters::github::SubIssueRef::issue_number)
        .collect::<BTreeSet<_>>();
    if references
        .iter()
        .any(|leaf| !parent_blocker_numbers.contains(&leaf.issue_number()))
    {
        return Err("a direct leaf does not block its umbrella parent".to_owned());
    }
    Ok(parent_blockers
        .iter()
        .filter(|blocker| {
            blocker.is_open() && !direct_leaf_numbers.contains(&blocker.issue_number())
        })
        .map(larch_adapters::github::DependencyRef::issue_number)
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect())
}

fn require_runnable_umbrella(graph: &GraphState) -> Result<(), String> {
    match select_complete_umbrella_leaf(
        &selection_leaves(&graph.leaves),
        &graph.open_orphan_blockers,
    ) {
        CompleteUmbrellaNext::Launch(_) | CompleteUmbrellaNext::Audit => Ok(()),
        CompleteUmbrellaNext::OrphanBlocked(issues) => Err(format!(
            "cannot start while open non-leaf parent blockers remain: {}",
            join_numbers(&issues)
        )),
        CompleteUmbrellaNext::Deadlocked(issues) => Err(format!(
            "cannot start a deadlocked umbrella while every open leaf is blocked: {}",
            join_numbers(&issues)
        )),
    }
}

fn require_no_open_orphan_blockers(graph: &GraphState) -> Result<(), String> {
    if graph.open_orphan_blockers.is_empty() {
        Ok(())
    } else {
        Err(format!(
            "cannot finish while open non-leaf parent blockers remain: {}",
            join_numbers(&graph.open_orphan_blockers)
        ))
    }
}

async fn require_top_level_umbrella(
    service: &larch_adapters::github::OctocrabGitHubService,
    cancellation: &Cancellation,
    repository: &GitHubRepositoryRef,
    umbrella: u64,
) -> Result<(), String> {
    let references = service
        .list_sub_issues(
            cancellation,
            repository.owner(),
            repository.name(),
            umbrella,
        )
        .await
        .map_err(|error| error.to_string())?;
    for reference in references {
        let child = service
            .issue(repository, reference.issue_number(), cancellation)
            .await
            .map_err(|error| error.to_string())?;
        if is_controlling_umbrella_title(&child.title) {
            return Err("nested umbrellas are not supported".to_owned());
        }
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

fn write_audit_snapshot(arguments: &NextArguments, graph: &GraphState) -> Result<(), String> {
    write_audit_snapshot_to(
        &arguments.repository,
        &arguments.output_root,
        &arguments.output,
        graph,
    )
}

fn write_audit_snapshot_to(
    repository: &str,
    output_root: &Path,
    output: &Path,
    graph: &GraphState,
) -> Result<(), String> {
    let snapshot = AuditSnapshot {
        repository: repository.to_owned(),
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
    let root = temporary_root(output_root, "--output-root")?;
    write_private_file(output, &format!("{text}\n"), output_root, &root)
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
    status: ChildResultStatus,
    failure_class: Option<&str>,
) -> Result<(), String> {
    let mut text = format!(
        "CHILD_STATUS={status}\nCHILD_ISSUE={leaf}\nCHILD_ENVELOPE_COMPLETE={}\n",
        if status.envelope_complete() {
            "true"
        } else {
            "false"
        },
        status = status.value(),
    );
    if let Some(class) = failure_class {
        let _ = writeln!(text, "CHILD_FAILURE_CLASS={class}");
    }
    write_private_file(&arguments.result_env, &text, &arguments.output_root, root)
}

fn join_numbers(numbers: &[u64]) -> String {
    numbers
        .iter()
        .map(u64::to_string)
        .collect::<Vec<_>>()
        .join(" ")
}

#[cfg(test)]
#[path = "../tests/support/complete_umbrella_commands.rs"]
mod tests;
