//! Fail-closed Rust CI selection and history helpers.
//!
//! The selector deliberately reads the candidate checkout only through the
//! typed repository port. Its result is a proposal: any unavailable, malformed,
//! or untrusted input chooses the existing full Rust lane.

use crate::html::{QuoteEscaping, escape_html};
use std::{
    collections::{BTreeMap, BTreeSet, VecDeque},
    fmt::Write as _,
    fs,
    io::Read as _,
    path::{Component, Path, PathBuf},
    process::ExitCode,
};

use cargo_metadata::{Metadata, MetadataCommand, Package, TargetKind};
use clap::{Args, Subcommand};
use larch_adapters::GixRepository;
use larch_core::{
    CandidateContract, CandidateRequest, ChangeKind, GitMode, GitPath, Head, ObjectId, ObjectKind,
    RepositoryRead, Revision, parse_maximum_bytes, parse_source, parse_tool_versions,
    promote_candidate, redact, redact_secrets, stage_candidate,
};
use serde::{Deserialize, Serialize};

const SCHEMA_VERSION: u64 = 2;
const MAX_CHANGED_PATHS: usize = 200;
const MAX_PATH_LENGTH: usize = 512;
const MAX_PUBLIC_TEXT_LENGTH: usize = 4 * 1024;
const MAX_RESULT_FILE_BYTES: u64 = 256 * 1024;
const MAX_SELECTION_COMMANDS: usize = 8;
const MAX_COMMAND_ARGUMENTS: usize = 256;
const REQUIRED_CONSUMER_PACKAGE_NAME: &str = "larch-cli";
const REDACTION_FAILURE_TRIGGER: &str = "public-output-redaction-failed";

const SKIP_EXACT_PATH_OWNERS: &[(&str, &str)] = &[
    (
        "AGENTS.md",
        "agent-lint plus trusted-main repository policy",
    ),
    (
        "ARCHITECTURAL_GUIDELINES.md",
        "agent-lint plus trusted-main repository policy",
    ),
    (
        "ARCHITECTURAL_INVARIANTS.md",
        "agent-lint plus trusted-main repository policy",
    ),
    (
        "BASH_AUTHORING.md",
        "agent-lint plus trusted-main repository policy",
    ),
    (
        "CLAUDE.md",
        "agent-lint plus trusted-main repository policy",
    ),
    (
        "KARPATHY_CLAUDE.md",
        "agent-lint plus trusted-main repository policy",
    ),
    (
        "README.md",
        "lint plus trusted-main repository policy and plugin validation",
    ),
    (
        "SECURITY.md",
        "lint plus trusted-main repository policy and plugin validation",
    ),
    (
        ".agnix.toml",
        "agent-lint plus trusted-main repository policy",
    ),
    (".gitleaks.toml", "lint plus trusted-main repository policy"),
    (
        ".markdownlint.json",
        "lint plus trusted-main repository policy",
    ),
    (
        ".markdownlintignore",
        "lint plus trusted-main repository policy",
    ),
    (
        "agent-lint.toml",
        "agent-lint plus trusted-main repository policy",
    ),
];

const SKIP_PREFIX_PATH_OWNERS: &[(&str, &str)] = &[
    (".claude/", "agent-lint plus trusted-main repository policy"),
    ("agents/", "agent-lint plus trusted-main repository policy"),
    (
        "docs/",
        "lint plus trusted-main repository policy and plugin validation",
    ),
    ("plugin/", "trusted-main plugin projection validation"),
    (
        "python/",
        "python-tests, python-pyright, and trusted-main repository policy",
    ),
    (
        "skills/",
        "agent-lint, lintlang, and trusted-main repository policy",
    ),
];

#[derive(Subcommand)]
pub enum CiCommand {
    /// Choose the next action from one CI status snapshot.
    #[command(disable_help_flag = true)]
    Decide(crate::ci_monitor_commands::Arguments),
    /// Read one pull request's CI, merge, and behind state.
    #[command(disable_help_flag = true)]
    Status(crate::ci_monitor_commands::Arguments),
    /// Poll pull-request CI until the next workflow action is known.
    #[command(disable_help_flag = true)]
    Wait(crate::ci_monitor_commands::Arguments),
    /// Classify one failed run's jobs into locally fixable repair inputs.
    #[command(name = "failed-jobs", disable_help_flag = true)]
    FailedJobs(crate::ci_failure_commands::Arguments),
    /// Write a bounded, redacted digest of one failed run's logs.
    #[command(name = "distill-log", disable_help_flag = true)]
    DistillLog(crate::ci_failure_commands::Arguments),
    /// Ask GitHub to rerun only the failed jobs of one workflow run.
    #[command(name = "rerun-failed", disable_help_flag = true)]
    RerunFailed(crate::ci_failure_commands::Arguments),
    /// Count how many base-branch commits the checkout is behind.
    #[command(name = "behind-count", disable_help_flag = true)]
    BehindCount(crate::ci_failure_commands::Arguments),
    /// Report the default branch's push CI health.
    #[command(name = "main-health", disable_help_flag = true)]
    MainHealth(crate::ci_failure_commands::Arguments),
    /// Propose a fail-closed Rust CI selection for a pull-request candidate.
    RustSelect(CiRustSelectArguments),
    /// Render the selector result as a bounded GitHub step summary.
    RustSelectSummary(CiRustSelectSummaryArguments),
    /// Resolve the history range base used by the gitleaks workflow.
    GitleaksBase(CiGitleaksBaseArguments),
    /// Stage a merge-group main-cache candidate artifact.
    #[command(name = "stage-main-cache-candidate")]
    StageMainCacheCandidate(StageMainCacheCandidateArguments),
    /// Verify and promote a merge-group main-cache candidate artifact.
    #[command(name = "verify-main-cache-candidate")]
    VerifyMainCacheCandidate(VerifyMainCacheCandidateArguments),
    /// Copy a coverage executable into a proven Rust integration artifact.
    #[command(name = "prepare-rust-integration-artifact")]
    PrepareRustIntegrationArtifact(
        crate::ci_policy_candidate_commands::PrepareRustIntegrationArtifactArgs,
    ),
    /// Stage and verify a Rust policy cache candidate under fixed provenance.
    #[command(name = "stage-rust-policy-candidate")]
    StageRustPolicyCandidate(crate::ci_policy_candidate_commands::StageRustPolicyCandidateArgs),
    /// Promote a verified merge-group bundle into trusted main provenance.
    #[command(name = "promote-rust-policy-candidate")]
    PromoteRustPolicyCandidate(crate::ci_policy_candidate_commands::PromoteRustPolicyCandidateArgs),
}

#[derive(Args)]
pub struct CiRustSelectArguments {
    #[arg(long, default_value = "unrecognized")]
    event_name: String,
    #[arg(long, default_value = "")]
    base_sha: String,
    #[arg(long, default_value = "")]
    head_sha: String,
    #[arg(long, default_value = ".")]
    repo_root: PathBuf,
}

#[derive(Args)]
pub struct CiRustSelectSummaryArguments {
    #[arg(long)]
    result_file: PathBuf,
}

#[derive(Args)]
pub struct CiGitleaksBaseArguments {
    #[arg(long, default_value = ".")]
    repo_root: PathBuf,
    #[arg(long, default_value = "origin/main")]
    base_ref: String,
}

#[derive(Args)]
pub struct StageMainCacheCandidateArguments {
    #[arg(long = "artifact-name")]
    artifact_name: String,
    #[arg(long = "cache-class")]
    cache_class: String,
    #[arg(long = "cache-key")]
    cache_key: String,
    #[arg(long = "candidate-dir")]
    candidate_dir: PathBuf,
    #[arg(long = "maximum-bytes")]
    maximum_bytes: String,
    #[arg(long = "producer-event")]
    producer_event: String,
    #[arg(long = "producer-job")]
    producer_job: String,
    #[arg(long = "producer-ref")]
    producer_ref: String,
    #[arg(long = "source-sha")]
    source_sha: String,
    #[arg(long = "source", required = true)]
    sources: Vec<String>,
    #[arg(long = "tool-version")]
    tool_versions: Vec<String>,
}

#[derive(Args)]
pub struct VerifyMainCacheCandidateArguments {
    #[arg(long = "artifact-name")]
    artifact_name: String,
    #[arg(long = "cache-class")]
    cache_class: String,
    #[arg(long = "cache-key")]
    cache_key: String,
    #[arg(long = "candidate-dir")]
    candidate_dir: PathBuf,
    #[arg(long = "maximum-bytes")]
    maximum_bytes: String,
    #[arg(long = "output-dir")]
    output_dir: PathBuf,
    #[arg(long = "producer-job")]
    producer_job: String,
    #[arg(long = "source-sha")]
    source_sha: String,
    #[arg(long = "expected-tool-version", required = true)]
    expected_tool_versions: Vec<String>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
struct ChangedPath {
    paths: Vec<String>,
    status: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
struct CommandPlan {
    argv: Vec<String>,
    name: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
struct DependencyPolicy {
    reason: String,
    required: bool,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
struct Selection {
    affected_packages: Vec<String>,
    base_sha: Option<String>,
    base_source: String,
    changed_paths: Vec<ChangedPath>,
    dependency_policy: DependencyPolicy,
    #[serde(default)]
    doctest_packages: Vec<String>,
    event_name: String,
    format_required: bool,
    full_run_trigger: Option<String>,
    head_sha: Option<String>,
    mode: String,
    partial_commands: Vec<CommandPlan>,
    reverse_dependents: Vec<String>,
    #[serde(default = "default_schema_version")]
    schema_version: u64,
    skip_proof: Option<String>,
    #[serde(default)]
    validation_owners: Vec<String>,
}

#[derive(Clone, Debug)]
struct WorkspacePackage {
    dependencies: Vec<Vec<String>>,
    has_library: bool,
    id: String,
    name: String,
    root: Vec<String>,
    source_roots: Vec<Vec<String>>,
}

pub fn run(command: CiCommand) -> ExitCode {
    match command {
        CiCommand::Decide(arguments) => crate::ci_monitor_commands::decide(&arguments),
        CiCommand::Status(arguments) => crate::ci_monitor_commands::status(&arguments),
        CiCommand::Wait(arguments) => crate::ci_monitor_commands::wait(&arguments),
        CiCommand::FailedJobs(arguments) => crate::ci_failure_commands::failed_jobs(&arguments),
        CiCommand::DistillLog(arguments) => crate::ci_failure_commands::distill_log(&arguments),
        CiCommand::RerunFailed(arguments) => crate::ci_failure_commands::rerun_failed(&arguments),
        CiCommand::BehindCount(arguments) => crate::ci_failure_commands::behind_count(&arguments),
        CiCommand::MainHealth(arguments) => crate::ci_failure_commands::main_health(&arguments),
        CiCommand::RustSelect(arguments) => {
            let selection = select(
                &arguments.event_name,
                &arguments.base_sha,
                &arguments.head_sha,
                &arguments.repo_root,
            );
            serde_json::to_string(&selection).map_or_else(
                |_| {
                    println!("{}", static_redaction_failure_json());
                    ExitCode::SUCCESS
                },
                |json| {
                    println!("{json}");
                    ExitCode::SUCCESS
                },
            )
        }
        CiCommand::RustSelectSummary(arguments) => {
            let selection = read_serialized_selection(&arguments.result_file).map_or_else(
                || {
                    full_selection(
                        "unrecognized",
                        None,
                        None,
                        "unavailable",
                        "selector-result-unavailable-or-invalid",
                        Vec::new(),
                    )
                },
                |selection| public_selection(&selection),
            );
            print!("{}", render_summary(&selection));
            ExitCode::SUCCESS
        }
        CiCommand::GitleaksBase(arguments) => gitleaks_base(&arguments),
        CiCommand::StageMainCacheCandidate(arguments) => stage_main_cache_candidate(&arguments),
        CiCommand::VerifyMainCacheCandidate(arguments) => verify_main_cache_candidate(&arguments),
        CiCommand::PrepareRustIntegrationArtifact(arguments) => ExitCode::from(
            crate::ci_policy_candidate_commands::prepare_rust_integration_artifact(&arguments),
        ),
        CiCommand::StageRustPolicyCandidate(arguments) => ExitCode::from(
            crate::ci_policy_candidate_commands::stage_rust_policy_candidate(&arguments),
        ),
        CiCommand::PromoteRustPolicyCandidate(arguments) => ExitCode::from(
            crate::ci_policy_candidate_commands::promote_rust_policy_candidate(&arguments),
        ),
    }
}

fn stage_main_cache_candidate(arguments: &StageMainCacheCandidateArguments) -> ExitCode {
    match stage_main_cache_candidate_inner(arguments) {
        Ok(verified) => {
            println!("CACHE_CLASS={}", verified.cache_class);
            println!("TOTAL_BYTES={}", verified.total_bytes);
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("Main cache candidate staging failed: {error}");
            ExitCode::from(1)
        }
    }
}

fn verify_main_cache_candidate(arguments: &VerifyMainCacheCandidateArguments) -> ExitCode {
    match verify_main_cache_candidate_inner(arguments) {
        Ok(verified) => {
            println!("CACHE_CLASS={}", verified.cache_class);
            println!("TOTAL_BYTES={}", verified.total_bytes);
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("Main cache candidate verification failed: {error}");
            ExitCode::from(1)
        }
    }
}

fn stage_main_cache_candidate_inner(
    arguments: &StageMainCacheCandidateArguments,
) -> Result<larch_core::VerifiedCandidate, larch_core::CandidateError> {
    let sources = arguments
        .sources
        .iter()
        .map(|value| parse_source(value))
        .collect::<Result<Vec<_>, _>>()?;
    let request = CandidateRequest {
        artifact_name: arguments.artifact_name.clone(),
        cache_class: arguments.cache_class.clone(),
        cache_key: arguments.cache_key.clone(),
        candidate_dir: arguments.candidate_dir.clone(),
        maximum_bytes: parse_maximum_bytes(&arguments.maximum_bytes)?,
        producer_event: arguments.producer_event.clone(),
        producer_job: arguments.producer_job.clone(),
        producer_ref: arguments.producer_ref.clone(),
        source_sha: arguments.source_sha.clone(),
        sources,
        tool_versions: parse_tool_versions(&arguments.tool_versions)?,
    };
    stage_candidate(&request)
}

fn verify_main_cache_candidate_inner(
    arguments: &VerifyMainCacheCandidateArguments,
) -> Result<larch_core::VerifiedCandidate, larch_core::CandidateError> {
    let contract = CandidateContract {
        artifact_name: arguments.artifact_name.clone(),
        cache_class: arguments.cache_class.clone(),
        cache_key: arguments.cache_key.clone(),
        maximum_bytes: parse_maximum_bytes(&arguments.maximum_bytes)?,
        producer_job: arguments.producer_job.clone(),
        source_sha: arguments.source_sha.clone(),
        expected_tool_versions: parse_tool_versions(&arguments.expected_tool_versions)?,
    };
    promote_candidate(&arguments.candidate_dir, &arguments.output_dir, &contract)
}

const fn default_schema_version() -> u64 {
    1
}

fn select(event_name: &str, base_sha: &str, head_sha: &str, repo_root: &Path) -> Selection {
    let event_name = safe_event_name(event_name);
    let base_sha = valid_sha(base_sha);
    let head_sha = valid_sha(head_sha);
    if event_name != "pull_request" {
        return public_selection(&full_selection(
            &event_name,
            base_sha,
            head_sha,
            "not-applicable",
            &format!("non-pull-request-event:{event_name}"),
            Vec::new(),
        ));
    }
    let Some(base_sha) = base_sha else {
        return public_selection(&full_selection(
            &event_name,
            None,
            head_sha,
            "unavailable",
            "missing-or-invalid-pr-base-sha",
            Vec::new(),
        ));
    };
    let Some(head_sha) = head_sha else {
        return public_selection(&full_selection(
            &event_name,
            Some(base_sha),
            None,
            "unavailable",
            "missing-or-invalid-pr-head-sha",
            Vec::new(),
        ));
    };
    let root = match repo_root.canonicalize() {
        Ok(root) if root.is_dir() => root,
        _ => {
            return public_selection(&full_selection(
                &event_name,
                Some(base_sha),
                Some(head_sha),
                "unavailable",
                "invalid-repository-root",
                Vec::new(),
            ));
        }
    };
    let selection =
        select_pull_request(&event_name, &base_sha, &head_sha, &root).unwrap_or_else(|reason| {
            full_selection(
                &event_name,
                Some(base_sha),
                Some(head_sha),
                "unavailable",
                &reason,
                Vec::new(),
            )
        });
    public_selection(&selection)
}

fn select_pull_request(
    event_name: &str,
    base_sha: &str,
    head_sha: &str,
    root: &Path,
) -> Result<Selection, String> {
    let repository = GixRepository::open(root).map_err(|_| "repository-open-failed".to_owned())?;
    let base = resolve_commit(&repository, base_sha, "base")?;
    let head = resolve_commit(&repository, head_sha, "head")?;
    let checked_out = checked_out_head(&repository)?;
    if checked_out != head {
        return Err("checked-out-head-does-not-match-pr-head".to_owned());
    }
    match repository.is_ancestor(&base, &head) {
        Ok(true) => {}
        Ok(false) => return Err("pr-base-is-not-an-ancestor-of-pr-head".to_owned()),
        Err(_) => return Err("merge-base-ancestry-verification-failed".to_owned()),
    }
    let changes = read_changes(&repository, &base, &head)?;
    let decision = select_from_changes(event_name, base_sha, head_sha, root, &changes);
    Ok(decision.unwrap_or_else(|reason| {
        full_selection(
            event_name,
            Some(base_sha.to_owned()),
            Some(head_sha.to_owned()),
            "github-pr-base",
            &reason,
            changes,
        )
    }))
}

fn resolve_commit(
    repository: &GixRepository,
    requested: &str,
    stage: &str,
) -> Result<ObjectId, String> {
    let id = repository
        .resolve_revision(&Revision::new(requested.as_bytes().to_vec()))
        .map_err(|_| format!("{stage}-commit-failed"))?;
    if id.to_hex() != requested {
        return Err(format!("{stage}-commit-does-not-match-requested-sha"));
    }
    match repository.object(&id) {
        Ok(Some(object)) if object.kind == ObjectKind::Commit => Ok(id),
        _ => Err(format!("{stage}-commit-failed")),
    }
}

fn checked_out_head(repository: &GixRepository) -> Result<ObjectId, String> {
    let head = match repository.head().map_err(|_| "checked-out-head-failed")? {
        Head::Detached { target } | Head::Symbolic { target, .. } => target,
        Head::Unborn { .. } => return Err("checked-out-head-failed".to_owned()),
    };
    match repository.object(&head) {
        Ok(Some(object)) if object.kind == ObjectKind::Commit => Ok(head),
        _ => Err("checked-out-head-failed".to_owned()),
    }
}

fn read_changes(
    repository: &GixRepository,
    base: &ObjectId,
    head: &ObjectId,
) -> Result<Vec<ChangedPath>, String> {
    let base_commit = repository
        .walk_commits(base, 1)
        .map_err(|_| "diff-failed")?
        .into_iter()
        .next()
        .filter(|commit| commit.id == *base)
        .ok_or_else(|| "diff-failed".to_owned())?;
    let head_commit = repository
        .walk_commits(head, 1)
        .map_err(|_| "diff-failed")?
        .into_iter()
        .next()
        .filter(|commit| commit.id == *head)
        .ok_or_else(|| "diff-failed".to_owned())?;
    let entries = repository
        .tree_changes(&base_commit.tree, &head_commit.tree)
        .map_err(|_| "diff-failed")?
        .entries()
        .to_vec();
    if entries.is_empty() {
        return Err("empty-diff".to_owned());
    }
    if entries.len() > MAX_CHANGED_PATHS {
        return Err("diff-exceeds-auditable-path-limit".to_owned());
    }
    let mut changes = Vec::with_capacity(entries.len());
    for entry in entries {
        if directory_tree_change(entry.old_mode, entry.new_mode) {
            continue;
        }
        let status = change_status(entry.kind).to_owned();
        let mut paths = Vec::new();
        if let Some(source) = entry.source_path {
            paths.push(normalize_path(&source)?);
        }
        paths.push(normalize_path(&entry.path)?);
        if matches!(entry.kind, ChangeKind::Renamed | ChangeKind::Copied) && paths.len() != 2 {
            return Err("unsupported-diff-status".to_owned());
        }
        changes.push(ChangedPath { paths, status });
    }
    if changes.is_empty() {
        return Err("empty-diff".to_owned());
    }
    changes.sort_by(|left, right| {
        left.status
            .cmp(&right.status)
            .then_with(|| left.paths.cmp(&right.paths))
    });
    Ok(changes)
}

fn directory_tree_change(old_mode: Option<GitMode>, new_mode: Option<GitMode>) -> bool {
    old_mode.is_none_or(tree_mode) && new_mode.is_none_or(tree_mode)
}

const fn tree_mode(mode: GitMode) -> bool {
    mode.raw() & 0o170_000 == 0o040_000
}

const fn change_status(kind: ChangeKind) -> &'static str {
    match kind {
        ChangeKind::Added => "A",
        ChangeKind::Deleted => "D",
        ChangeKind::Modified | ChangeKind::TypeChanged | ChangeKind::SubmoduleModified => "M",
        ChangeKind::Renamed => "R100",
        ChangeKind::Copied => "C100",
    }
}

fn normalize_path(path: &GitPath) -> Result<String, String> {
    let value = std::str::from_utf8(path.as_bytes())
        .map_err(|_| "unsafe-or-ambiguous-diff-path".to_owned())?;
    if value.is_empty()
        || value.len() > MAX_PATH_LENGTH
        || value.contains(['\n', '\r', '\u{fffd}'])
        || value.split('/').any(|part| matches!(part, "" | "." | ".."))
    {
        return Err("unsafe-or-ambiguous-diff-path".to_owned());
    }
    Ok(value.to_owned())
}

fn select_from_changes(
    event_name: &str,
    base_sha: &str,
    head_sha: &str,
    root: &Path,
    changes: &[ChangedPath],
) -> Result<Selection, String> {
    if let Some(owners) = skip_validation_owners(changes)? {
        return Ok(Selection {
            affected_packages: Vec::new(),
            base_sha: Some(base_sha.to_owned()),
            base_source: "github-pr-base".to_owned(),
            changed_paths: changes.to_vec(),
            dependency_policy: DependencyPolicy {
                reason: "supplementary-only diff proves no dependency-policy input changed"
                    .to_owned(),
                required: false,
            },
            doctest_packages: Vec::new(),
            event_name: event_name.to_owned(),
            format_required: false,
            full_run_trigger: None,
            head_sha: Some(head_sha.to_owned()),
            mode: "skip".to_owned(),
            partial_commands: Vec::new(),
            reverse_dependents: Vec::new(),
            schema_version: SCHEMA_VERSION,
            skip_proof: Some(
                "all changed paths have audited non-Rust validation owners".to_owned(),
            ),
            validation_owners: owners,
        });
    }
    require_rust_source_only(changes)?;
    let packages = workspace_packages(root)?;
    let changed_package_ids = changed_packages(changes, &packages)?;
    let closure = reverse_dependency_closure(&changed_package_ids, &packages)?;
    let all_ids: BTreeSet<String> = packages.iter().map(|package| package.id.clone()).collect();
    if !closure.iter().any(|id| {
        packages
            .iter()
            .find(|package| package.id == *id)
            .is_some_and(|package| package.name == REQUIRED_CONSUMER_PACKAGE_NAME)
    }) {
        return Err("partial-does-not-build-policy-consumer".to_owned());
    }
    if closure == all_ids {
        return Err("partial-closure-covers-entire-workspace".to_owned());
    }
    let by_id: BTreeMap<String, &WorkspacePackage> = packages
        .iter()
        .map(|package| (package.id.clone(), package))
        .collect();
    let mut affected_packages: Vec<String> = closure
        .iter()
        .filter_map(|id| by_id.get(id).map(|package| package.name.clone()))
        .collect();
    affected_packages.sort();
    let changed_names: BTreeSet<String> = changed_package_ids
        .iter()
        .filter_map(|id| by_id.get(id).map(|package| package.name.clone()))
        .collect();
    let reverse_dependents = affected_packages
        .iter()
        .filter(|name| !changed_names.contains(*name))
        .cloned()
        .collect();
    let (partial_commands, doctest_packages) =
        partial_commands(&affected_packages, &by_id, &closure)?;
    Ok(Selection {
        affected_packages,
        base_sha: Some(base_sha.to_owned()),
        base_source: "github-pr-base".to_owned(),
        changed_paths: changes.to_vec(),
        dependency_policy: DependencyPolicy {
            reason: "rust-source-only-diff-proves-no-dependency-policy-input".to_owned(),
            required: false,
        },
        doctest_packages,
        event_name: event_name.to_owned(),
        format_required: true,
        full_run_trigger: None,
        head_sha: Some(head_sha.to_owned()),
        mode: "partial".to_owned(),
        partial_commands,
        reverse_dependents,
        schema_version: SCHEMA_VERSION,
        skip_proof: None,
        validation_owners: vec![
            "rust-lint: workspace format plus selected-package Clippy".to_owned(),
            "rust-partial: selected tests, doctests, PR-built larch repository policy, plugin validation, and Python artifact".to_owned(),
        ],
    })
}

fn skip_validation_owners(changes: &[ChangedPath]) -> Result<Option<Vec<String>>, String> {
    let mut owners = BTreeSet::new();
    for change in changes {
        for path in &change.paths {
            if let Some(trigger) = global_input_trigger(path) {
                return Err(trigger.to_owned());
            }
            if is_rust_source(path) {
                return Ok(None);
            }
            let Some(owner) = skip_validation_owner(path) else {
                return Ok(None);
            };
            let _ = owners.insert(owner.to_owned());
        }
    }
    if owners.is_empty() {
        return Err("empty-supplementary-validation-owner-set".to_owned());
    }
    Ok(Some(owners.into_iter().collect()))
}

fn require_rust_source_only(changes: &[ChangedPath]) -> Result<(), String> {
    for change in changes {
        for path in &change.paths {
            if let Some(trigger) = global_input_trigger(path) {
                return Err(trigger.to_owned());
            }
            if !is_rust_source(path) {
                return Err("unknown-path-has-no-named-validation-owner".to_owned());
            }
        }
    }
    Ok(())
}

fn skip_validation_owner(path: &str) -> Option<&'static str> {
    SKIP_EXACT_PATH_OWNERS
        .iter()
        .find_map(|(candidate, owner)| (*candidate == path).then_some(*owner))
        .or_else(|| {
            SKIP_PREFIX_PATH_OWNERS
                .iter()
                .find_map(|(prefix, owner)| path.starts_with(prefix).then_some(*owner))
        })
}

fn is_rust_source(path: &str) -> bool {
    Path::new(path)
        .extension()
        .is_some_and(|extension| extension == "rs")
}

fn global_input_trigger(path: &str) -> Option<&'static str> {
    match path {
        "Cargo.lock" => Some("global-input:cargo-lock"),
        "rust-toolchain.toml" => Some("global-input:rust-toolchain"),
        "deny.toml" => Some("global-input:dependency-policy"),
        ".github/workflows/ci.yaml"
        | ".github/actions/rust-coverage/action.yaml"
        | "python/cli.py"
        | "python/larch/cli.py"
        | "crates/larch-cli/src/ci_policy_candidate_commands.rs" => {
            Some("global-input:rust-ci-workflow")
        }
        "crates/larch-cli/src/ci_selection.rs"
        | "crates/larch-cli/src/html.rs"
        | "crates/larch-cli/src/main.rs"
        | "crates/larch-core/src/redaction.rs" => Some("global-input:rust-selector"),
        _ if path == ".cargo" || path.starts_with(".cargo/") => {
            Some("global-input:cargo-configuration")
        }
        _ => match path.rsplit('/').next() {
            Some("Cargo.toml") => Some("global-input:cargo-manifest"),
            Some("Makefile") => Some("global-input:rust-makefile"),
            Some("build.rs") => Some("global-input:build-script"),
            Some("nextest.toml" | "rust-ci-profile.toml") => Some("global-input:test-profile"),
            _ => None,
        },
    }
}

fn workspace_packages(root: &Path) -> Result<Vec<WorkspacePackage>, String> {
    let manifest = root.join("Cargo.toml");
    if !manifest.is_file() {
        return Err("cargo-metadata-invalid-workspace-root".to_owned());
    }
    let metadata = MetadataCommand::new()
        .manifest_path(&manifest)
        .current_dir(root)
        .no_deps()
        .other_options(vec!["--locked".to_owned(), "--offline".to_owned()])
        .exec()
        .map_err(|_| "cargo-metadata-failed".to_owned())?;
    parse_workspace_packages(&metadata, root)
}

fn parse_workspace_packages(
    metadata: &Metadata,
    root: &Path,
) -> Result<Vec<WorkspacePackage>, String> {
    let workspace_root = metadata
        .workspace_root
        .as_std_path()
        .canonicalize()
        .map_err(|_| "cargo-metadata-invalid-workspace-root".to_owned())?;
    if workspace_root != root {
        return Err("cargo-metadata-workspace-root-mismatch".to_owned());
    }
    if metadata.workspace_members.is_empty() {
        return Err("cargo-metadata-invalid-workspace-members".to_owned());
    }
    let packages_by_id: BTreeMap<String, &Package> = metadata
        .packages
        .iter()
        .map(|package| (package.id.repr.clone(), package))
        .collect();
    if packages_by_id.len() != metadata.packages.len() {
        return Err("cargo-metadata-invalid-workspace-packages".to_owned());
    }
    let mut packages = Vec::with_capacity(metadata.workspace_members.len());
    let mut seen_members = BTreeSet::new();
    for member in &metadata.workspace_members {
        if !seen_members.insert(member.repr.clone()) {
            return Err("cargo-metadata-invalid-workspace-members".to_owned());
        }
        let package = packages_by_id
            .get(&member.repr)
            .ok_or_else(|| "cargo-metadata-invalid-workspace-packages".to_owned())?;
        packages.push(parse_workspace_package(package, root)?);
    }
    let names: BTreeSet<String> = packages
        .iter()
        .map(|package| package.name.clone())
        .collect();
    let roots: BTreeSet<Vec<String>> = packages
        .iter()
        .map(|package| package.root.clone())
        .collect();
    if names.len() != packages.len() || roots.len() != packages.len() {
        return Err("unsupported-workspace-package-identity".to_owned());
    }
    let known_roots: BTreeSet<Vec<String>> = packages
        .iter()
        .map(|package| package.root.clone())
        .collect();
    if packages.iter().any(|package| {
        package
            .dependencies
            .iter()
            .any(|dependency| !known_roots.contains(dependency))
    }) {
        return Err("unmapped-local-workspace-dependency".to_owned());
    }
    packages.sort_by(|left, right| left.name.cmp(&right.name));
    Ok(packages)
}

fn parse_workspace_package(package: &Package, root: &Path) -> Result<WorkspacePackage, String> {
    let name = package.name.to_string();
    if !valid_package_name(&name) {
        return Err("unsupported-workspace-package-name".to_owned());
    }
    let manifest = package.manifest_path.as_std_path();
    if manifest.file_name().is_none_or(|name| name != "Cargo.toml") {
        return Err("cargo-metadata-invalid-manifest-path".to_owned());
    }
    let package_root = manifest
        .parent()
        .ok_or_else(|| "cargo-metadata-invalid-manifest-path".to_owned())?;
    let root_parts = relative_parts(package_root, root, "cargo-metadata-invalid-manifest-path")?;
    if package.targets.is_empty() {
        return Err("cargo-metadata-invalid-targets".to_owned());
    }
    let mut has_library = false;
    let mut source_roots = BTreeSet::new();
    for target in &package.targets {
        if target.kind.is_empty() {
            return Err("cargo-metadata-invalid-targets".to_owned());
        }
        has_library |= target
            .kind
            .iter()
            .any(|kind| matches!(kind, TargetKind::Lib | TargetKind::ProcMacro));
        let source = target.src_path.as_std_path();
        if source.extension().is_none_or(|extension| extension != "rs") {
            return Err("unsupported-cargo-target-source".to_owned());
        }
        let source_parts =
            relative_parts(source, root, "cargo-metadata-target-outside-repository")?;
        if !starts_with(&source_parts, &root_parts) || source_parts.is_empty() {
            return Err("cargo-metadata-target-outside-package".to_owned());
        }
        let _ = source_roots.insert(source_parts[..source_parts.len() - 1].to_vec());
    }
    let mut dependencies = BTreeSet::new();
    for dependency in &package.dependencies {
        let Some(path) = &dependency.path else {
            continue;
        };
        let dependency_root = relative_parts(
            path.as_std_path(),
            root,
            "cargo-metadata-invalid-dependency-path",
        )?;
        let _ = dependencies.insert(dependency_root);
    }
    Ok(WorkspacePackage {
        dependencies: dependencies.into_iter().collect(),
        has_library,
        id: package.id.repr.clone(),
        name,
        root: root_parts,
        source_roots: source_roots.into_iter().collect(),
    })
}

fn relative_parts(path: &Path, root: &Path, reason: &str) -> Result<Vec<String>, String> {
    let canonical = path.canonicalize().map_err(|_| reason.to_owned())?;
    let relative = canonical
        .strip_prefix(root)
        .map_err(|_| reason.to_owned())?;
    relative
        .components()
        .map(|component| match component {
            Component::Normal(value) => value
                .to_str()
                .filter(|value| !value.is_empty())
                .map(str::to_owned)
                .ok_or_else(|| reason.to_owned()),
            _ => Err(reason.to_owned()),
        })
        .collect()
}

fn valid_package_name(value: &str) -> bool {
    let mut bytes = value.bytes();
    let Some(first) = bytes.next() else {
        return false;
    };
    first.is_ascii_alphanumeric()
        && bytes.all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'-' | b'_'))
}

fn changed_packages(
    changes: &[ChangedPath],
    packages: &[WorkspacePackage],
) -> Result<BTreeSet<String>, String> {
    let mut changed_ids = BTreeSet::new();
    for change in changes {
        for path in &change.paths {
            let package = package_for_path(path, packages)?;
            let _ = changed_ids.insert(package.id.clone());
        }
    }
    if changed_ids.is_empty() {
        return Err("empty-rust-package-selection".to_owned());
    }
    Ok(changed_ids)
}

fn package_for_path<'a>(
    path: &str,
    packages: &'a [WorkspacePackage],
) -> Result<&'a WorkspacePackage, String> {
    let parts: Vec<String> = path.split('/').map(str::to_owned).collect();
    let matches: Vec<&WorkspacePackage> = packages
        .iter()
        .filter(|package| {
            starts_with(&parts, &package.root)
                && package
                    .source_roots
                    .iter()
                    .any(|source_root| starts_with(&parts, source_root))
        })
        .collect();
    match matches.as_slice() {
        [package] => Ok(*package),
        [] if packages
            .iter()
            .any(|package| starts_with(&parts, &package.root)) =>
        {
            Err("rust-path-not-owned-by-workspace-target".to_owned())
        }
        [] => Err("rust-path-not-owned-by-workspace-package".to_owned()),
        _ => Err("ambiguous-workspace-package-ownership".to_owned()),
    }
}

fn starts_with(value: &[String], prefix: &[String]) -> bool {
    value.len() >= prefix.len() && value[..prefix.len()] == *prefix
}

fn reverse_dependency_closure(
    changed: &BTreeSet<String>,
    packages: &[WorkspacePackage],
) -> Result<BTreeSet<String>, String> {
    let roots: BTreeMap<Vec<String>, String> = packages
        .iter()
        .map(|package| (package.root.clone(), package.id.clone()))
        .collect();
    let mut reverse: BTreeMap<String, BTreeSet<String>> = packages
        .iter()
        .map(|package| (package.id.clone(), BTreeSet::new()))
        .collect();
    for package in packages {
        for dependency in &package.dependencies {
            let dependency_id = roots
                .get(dependency)
                .ok_or_else(|| "unmapped-local-workspace-dependency".to_owned())?;
            let dependents = reverse
                .get_mut(dependency_id)
                .ok_or_else(|| "unmapped-local-workspace-dependency".to_owned())?;
            let _ = dependents.insert(package.id.clone());
        }
    }
    let mut closure = changed.clone();
    let mut pending: VecDeque<String> = changed.iter().cloned().collect();
    while let Some(current) = pending.pop_front() {
        let dependents = reverse
            .get(&current)
            .ok_or_else(|| "unmapped-local-workspace-dependency".to_owned())?;
        for dependent in dependents {
            if closure.insert(dependent.clone()) {
                pending.push_back(dependent.clone());
            }
        }
    }
    Ok(closure)
}

fn partial_commands(
    affected_packages: &[String],
    by_id: &BTreeMap<String, &WorkspacePackage>,
    closure: &BTreeSet<String>,
) -> Result<(Vec<CommandPlan>, Vec<String>), String> {
    if affected_packages.is_empty() {
        return Err("empty-rust-package-selection".to_owned());
    }
    let package_arguments: Vec<String> = affected_packages
        .iter()
        .flat_map(|package| ["--package".to_owned(), package.clone()])
        .collect();
    let mut doctest_packages: Vec<String> = closure
        .iter()
        .filter_map(|id| by_id.get(id))
        .filter(|package| package.has_library)
        .map(|package| package.name.clone())
        .collect();
    doctest_packages.sort();
    let mut commands = vec![
        CommandPlan {
            argv: vec![
                "cargo".to_owned(),
                "fmt".to_owned(),
                "--all".to_owned(),
                "--check".to_owned(),
            ],
            name: "format".to_owned(),
        },
        CommandPlan {
            argv: [
                vec!["cargo".to_owned(), "clippy".to_owned()],
                package_arguments.clone(),
                vec![
                    "--all-targets".to_owned(),
                    "--all-features".to_owned(),
                    "--locked".to_owned(),
                    "--".to_owned(),
                    "-D".to_owned(),
                    "warnings".to_owned(),
                ],
            ]
            .concat(),
            name: "clippy".to_owned(),
        },
        CommandPlan {
            argv: [
                vec!["cargo".to_owned(), "test".to_owned()],
                package_arguments,
                vec![
                    "--all-targets".to_owned(),
                    "--all-features".to_owned(),
                    "--locked".to_owned(),
                ],
            ]
            .concat(),
            name: "test".to_owned(),
        },
    ];
    if !doctest_packages.is_empty() {
        let arguments: Vec<String> = doctest_packages
            .iter()
            .flat_map(|package| ["--package".to_owned(), package.clone()])
            .collect();
        commands.push(CommandPlan {
            argv: [
                vec!["cargo".to_owned(), "test".to_owned(), "--doc".to_owned()],
                arguments,
                vec!["--all-features".to_owned(), "--locked".to_owned()],
            ]
            .concat(),
            name: "doctests".to_owned(),
        });
    }
    Ok((commands, doctest_packages))
}

fn full_selection(
    event_name: &str,
    base_sha: Option<String>,
    head_sha: Option<String>,
    base_source: &str,
    reason: &str,
    changed_paths: Vec<ChangedPath>,
) -> Selection {
    Selection {
        affected_packages: Vec::new(),
        base_sha,
        base_source: base_source.to_owned(),
        changed_paths,
        dependency_policy: DependencyPolicy {
            reason: "full-mode-requires-the-existing-rust-deny-lane".to_owned(),
            required: true,
        },
        doctest_packages: Vec::new(),
        event_name: event_name.to_owned(),
        format_required: true,
        full_run_trigger: Some(reason.to_owned()),
        head_sha,
        mode: "full".to_owned(),
        partial_commands: Vec::new(),
        reverse_dependents: Vec::new(),
        schema_version: SCHEMA_VERSION,
        skip_proof: None,
        validation_owners: vec![
            "rust-lint: workspace format and Clippy".to_owned(),
            "rust-deny: dependency policy".to_owned(),
            "rust-coverage: sharded test coverage, parallel policy coverage, combined line gate, doctests, plugin validation, and Python artifact"
                .to_owned(),
        ],
    }
}

fn public_selection(selection: &Selection) -> Selection {
    redact_selection(selection).unwrap_or_else(|()| {
        full_selection(
            "unrecognized",
            None,
            None,
            "unavailable",
            REDACTION_FAILURE_TRIGGER,
            Vec::new(),
        )
    })
}

fn redact_selection(selection: &Selection) -> Result<Selection, ()> {
    Ok(Selection {
        affected_packages: redact_values(&selection.affected_packages)?,
        base_sha: redact_optional(selection.base_sha.as_deref())?,
        base_source: redact_value(&selection.base_source)?,
        changed_paths: selection
            .changed_paths
            .iter()
            .map(|change| {
                Ok(ChangedPath {
                    paths: redact_values(&change.paths)?,
                    status: redact_value(&change.status)?,
                })
            })
            .collect::<Result<Vec<_>, ()>>()?,
        dependency_policy: DependencyPolicy {
            reason: redact_value(&selection.dependency_policy.reason)?,
            required: selection.dependency_policy.required,
        },
        doctest_packages: redact_values(&selection.doctest_packages)?,
        event_name: redact_value(&selection.event_name)?,
        format_required: selection.format_required,
        full_run_trigger: redact_optional(selection.full_run_trigger.as_deref())?,
        head_sha: redact_optional(selection.head_sha.as_deref())?,
        mode: redact_value(&selection.mode)?,
        partial_commands: selection
            .partial_commands
            .iter()
            .map(|command| {
                Ok(CommandPlan {
                    argv: redact_values(&command.argv)?,
                    name: redact_value(&command.name)?,
                })
            })
            .collect::<Result<Vec<_>, ()>>()?,
        reverse_dependents: redact_values(&selection.reverse_dependents)?,
        schema_version: selection.schema_version,
        skip_proof: redact_optional(selection.skip_proof.as_deref())?,
        validation_owners: redact_values(&selection.validation_owners)?,
    })
}

fn redact_values(values: &[String]) -> Result<Vec<String>, ()> {
    values.iter().map(|value| redact_value(value)).collect()
}

fn redact_optional(value: Option<&str>) -> Result<Option<String>, ()> {
    value.map(redact_value).transpose()
}

fn redact_value(value: &str) -> Result<String, ()> {
    let value = redact(value).text().to_owned();
    if !redact_secrets(&value).findings().is_empty()
        || value.contains(['\r', '\n'])
        || value.contains("[content truncated")
    {
        return Err(());
    }
    Ok(value)
}

fn valid_serialized_selection(selection: &Selection) -> bool {
    matches!(selection.schema_version, 1 | SCHEMA_VERSION)
        && valid_event_name(&selection.event_name)
        && valid_public_text(&selection.base_source)
        && selection
            .base_sha
            .as_deref()
            .is_none_or(|value| valid_sha(value).as_deref() == Some(value))
        && selection
            .head_sha
            .as_deref()
            .is_none_or(|value| valid_sha(value).as_deref() == Some(value))
        && valid_changed_paths(&selection.changed_paths)
        && valid_package_names(&selection.affected_packages)
        && valid_package_names(&selection.reverse_dependents)
        && valid_package_names(&selection.doctest_packages)
        && valid_optional_public_text(selection.full_run_trigger.as_deref())
        && valid_optional_public_text(selection.skip_proof.as_deref())
        && valid_command_plans(&selection.partial_commands)
        && valid_public_text(&selection.dependency_policy.reason)
        && valid_public_texts(&selection.validation_owners)
        && valid_selection_mode(selection)
}

fn read_serialized_selection(path: &Path) -> Option<Selection> {
    let file = fs::File::open(path).ok()?;
    if !file.metadata().ok()?.is_file() {
        return None;
    }
    let mut contents = String::new();
    file.take(MAX_RESULT_FILE_BYTES.saturating_add(1))
        .read_to_string(&mut contents)
        .ok()?;
    if contents.len() as u64 > MAX_RESULT_FILE_BYTES {
        return None;
    }
    serde_json::from_str::<Selection>(&contents)
        .ok()
        .filter(valid_serialized_selection)
}

fn valid_event_name(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 64
        && value.bytes().all(|byte| {
            byte.is_ascii_lowercase() || byte.is_ascii_digit() || matches!(byte, b'_' | b'-')
        })
}

fn valid_public_text(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= MAX_PUBLIC_TEXT_LENGTH
        && !value.contains(['\r', '\n', '\0'])
}

fn valid_optional_public_text(value: Option<&str>) -> bool {
    value.is_none_or(valid_public_text)
}

fn valid_public_texts(values: &[String]) -> bool {
    values.len() <= MAX_CHANGED_PATHS && values.iter().all(|value| valid_public_text(value))
}

fn valid_package_names(values: &[String]) -> bool {
    values.len() <= MAX_CHANGED_PATHS
        && values
            .iter()
            .all(|value| valid_public_text(value) && valid_package_name(value))
}

fn valid_changed_paths(changes: &[ChangedPath]) -> bool {
    changes.len() <= MAX_CHANGED_PATHS
        && changes.iter().all(|change| {
            valid_change_status(&change.status)
                && change.paths.len()
                    == if change.status.starts_with(['R', 'C']) {
                        2
                    } else {
                        1
                    }
                && change.paths.iter().all(|path| valid_normalized_path(path))
        })
}

fn valid_change_status(value: &str) -> bool {
    matches!(value, "A" | "M" | "D")
        || value.strip_prefix(['R', 'C']).is_some_and(|score| {
            !score.is_empty() && score.bytes().all(|byte| byte.is_ascii_digit())
        })
}

fn valid_normalized_path(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= MAX_PATH_LENGTH
        && !value.contains(['\r', '\n', '\0', '\u{fffd}'])
        && value
            .split('/')
            .all(|part| !matches!(part, "" | "." | ".."))
}

fn valid_command_plans(commands: &[CommandPlan]) -> bool {
    commands.len() <= MAX_SELECTION_COMMANDS
        && commands.iter().all(|command| {
            valid_public_text(&command.name)
                && !command.argv.is_empty()
                && command.argv.len() <= MAX_COMMAND_ARGUMENTS
                && command
                    .argv
                    .iter()
                    .all(|argument| valid_public_text(argument))
        })
}

fn valid_selection_mode(selection: &Selection) -> bool {
    match selection.mode.as_str() {
        "full" => {
            selection.dependency_policy.required
                && selection
                    .full_run_trigger
                    .as_deref()
                    .is_some_and(valid_public_text)
                && selection.skip_proof.is_none()
                && selection.affected_packages.is_empty()
                && selection.reverse_dependents.is_empty()
                && selection.doctest_packages.is_empty()
                && selection.partial_commands.is_empty()
                && selection.format_required
                && !selection.validation_owners.is_empty()
        }
        "partial" => {
            !selection.dependency_policy.required
                && selection.base_sha.is_some()
                && selection.head_sha.is_some()
                && !selection.changed_paths.is_empty()
                && !selection.affected_packages.is_empty()
                && selection.full_run_trigger.is_none()
                && selection.skip_proof.is_none()
                && !selection.partial_commands.is_empty()
                && selection.format_required
                && !selection.validation_owners.is_empty()
        }
        "skip" => {
            !selection.dependency_policy.required
                && selection.base_sha.is_some()
                && selection.head_sha.is_some()
                && !selection.changed_paths.is_empty()
                && selection.affected_packages.is_empty()
                && selection.reverse_dependents.is_empty()
                && selection.doctest_packages.is_empty()
                && selection.full_run_trigger.is_none()
                && selection
                    .skip_proof
                    .as_deref()
                    .is_some_and(valid_public_text)
                && selection.partial_commands.is_empty()
                && !selection.format_required
                && !selection.validation_owners.is_empty()
        }
        _ => false,
    }
}

fn render_summary(selection: &Selection) -> String {
    let mode = html_code(&selection.mode);
    let base = html_code(selection.base_sha.as_deref().unwrap_or("unavailable"));
    let head = html_code(selection.head_sha.as_deref().unwrap_or("unavailable"));
    let mut result = format!(
        "## Rust CI selection\n\nProposed mode: {mode}. Non-full modes retain their named validation owners; the merge queue remains the full-run backstop.\n\n- Base: {base} ({})\n- Head: {head}\n- Dependency policy: {}\n",
        html_code(&selection.base_source),
        html_code(&selection.dependency_policy.reason),
    );
    if let Some(trigger) = &selection.full_run_trigger {
        let _ = writeln!(result, "- Full-run trigger: {}", html_code(trigger));
    }
    if let Some(proof) = &selection.skip_proof {
        let _ = writeln!(result, "- Skip proof: {}", html_code(proof));
    }
    if !selection.affected_packages.is_empty() {
        let _ = writeln!(
            result,
            "- Affected packages: {}",
            html_code(&selection.affected_packages.join(", "))
        );
    }
    if !selection.reverse_dependents.is_empty() {
        let _ = writeln!(
            result,
            "- Reverse dependents: {}",
            html_code(&selection.reverse_dependents.join(", "))
        );
    }
    if !selection.doctest_packages.is_empty() {
        let _ = writeln!(
            result,
            "- Doctest packages: {}",
            html_code(&selection.doctest_packages.join(", "))
        );
    }
    if !selection.validation_owners.is_empty() {
        result.push_str("\n<details><summary>Validation owners</summary>\n\n");
        for owner in &selection.validation_owners {
            let _ = writeln!(result, "- {}", html_code(owner));
        }
        result.push_str("\n</details>\n");
    }
    if selection.changed_paths.is_empty() {
        result.push_str("- Changed paths: unavailable because the selector chose full before a complete diff was proven.\n");
    } else {
        let _ = writeln!(
            result,
            "\n<details><summary>Changed paths ({})</summary>\n",
            selection.changed_paths.len()
        );
        for change in &selection.changed_paths {
            let paths = change
                .paths
                .iter()
                .map(|path| html_code(path))
                .collect::<Vec<_>>()
                .join(" → ");
            let _ = writeln!(result, "- {}: {paths}", html_code(&change.status));
        }
        result.push_str("\n</details>\n");
    }
    if !selection.partial_commands.is_empty() {
        result.push_str("\n<details><summary>Proposed partial commands</summary>\n\n");
        for command in &selection.partial_commands {
            let _ = writeln!(
                result,
                "- {}: {}",
                html_code(&command.name),
                html_code(&command.argv.join(" "))
            );
        }
        result.push_str("\n</details>\n");
    }
    result
}

fn html_code(value: &str) -> String {
    format!(
        "<code>{}</code>",
        escape_html(value, QuoteEscaping::Decimal)
    )
}

fn safe_event_name(value: &str) -> String {
    if valid_event_name(value) {
        value.to_owned()
    } else {
        "unrecognized".to_owned()
    }
}

fn valid_sha(value: &str) -> Option<String> {
    ((value.len() == 40 || value.len() == 64) && value.bytes().all(|byte| byte.is_ascii_hexdigit()))
        .then(|| value.to_ascii_lowercase())
}

fn gitleaks_base(arguments: &CiGitleaksBaseArguments) -> ExitCode {
    let result = resolve_gitleaks_base(&arguments.repo_root, &arguments.base_ref);
    match result {
        Ok(base) => {
            println!("{base}");
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("ERROR={error}");
            ExitCode::FAILURE
        }
    }
}

fn resolve_gitleaks_base(repo_root: &Path, base_ref: &str) -> Result<String, String> {
    let root = repo_root
        .canonicalize()
        .map_err(|_| "gitleaks repository root is unavailable".to_owned())?;
    let repository =
        GixRepository::open(root).map_err(|_| "gitleaks repository is unavailable".to_owned())?;
    let head = checked_out_head(&repository)
        .map_err(|_| "gitleaks checked-out head is unavailable".to_owned())?;
    if let Ok(base) = repository.resolve_revision(&Revision::new(base_ref.as_bytes().to_vec()))
        && matches!(repository.object(&base), Ok(Some(object)) if object.kind == ObjectKind::Commit)
        && let Ok(merge_base) = repository.merge_base(&head, &base)
    {
        return Ok(merge_base.to_hex());
    }
    let commits = repository
        .walk_commits(&head, 2)
        .map_err(|_| "gitleaks history base is unavailable".to_owned())?;
    commits
        .get(1)
        .map(|commit| commit.id.to_hex())
        .ok_or_else(|| "gitleaks history base is unavailable".to_owned())
}

fn static_redaction_failure_json() -> String {
    serde_json::to_string(&full_selection(
        "unrecognized",
        None,
        None,
        "unavailable",
        REDACTION_FAILURE_TRIGGER,
        Vec::new(),
    ))
    .unwrap_or_else(|_| String::from("{}"))
}

#[cfg(test)]
mod tests {
    use super::{
        ChangedPath, MAX_RESULT_FILE_BYTES, SCHEMA_VERSION, full_selection, global_input_trigger,
        html_code, public_selection, read_serialized_selection, render_summary,
        resolve_gitleaks_base, safe_event_name, select, valid_serialized_selection, valid_sha,
    };
    use std::{fs, path::Path, process::Command};
    use tempfile::TempDir;

    #[test]
    fn unsafe_events_and_revisions_are_never_accepted() {
        assert_eq!(safe_event_name("pull_request"), "pull_request");
        assert_eq!(safe_event_name("pull request"), "unrecognized");
        assert_eq!(valid_sha(&"a".repeat(40)), Some("a".repeat(40)));
        assert_eq!(valid_sha("not-a-commit"), None);
    }

    #[test]
    fn global_selector_sources_force_a_full_lane() {
        assert_eq!(
            global_input_trigger("crates/larch-cli/src/ci_selection.rs"),
            Some("global-input:rust-selector")
        );
        assert_eq!(
            global_input_trigger("crates/larch-cli/src/html.rs"),
            Some("global-input:rust-selector")
        );
        assert_eq!(
            global_input_trigger("crates/other/Cargo.toml"),
            Some("global-input:cargo-manifest")
        );
        assert_eq!(
            global_input_trigger("crates/larch-core/src/redaction.rs"),
            Some("global-input:rust-selector")
        );
    }

    #[test]
    fn rendered_summary_escapes_changed_paths() {
        let selection = full_selection(
            "pull_request",
            Some("a".repeat(40)),
            Some("b".repeat(40)),
            "github-pr-base",
            "unknown-path-has-no-named-validation-owner",
            vec![ChangedPath {
                paths: vec!["src/<untrusted>.rs".to_owned()],
                status: "M".to_owned(),
            }],
        );
        assert_eq!(selection.schema_version, SCHEMA_VERSION);
        assert_eq!(html_code("<value>"), "<code>&lt;value&gt;</code>");
    }

    #[test]
    fn malformed_repository_context_chooses_the_full_lane() {
        let temporary = tempfile::tempdir().expect("temporary root");
        let missing = temporary.path().join("missing");
        let selection = select("pull_request", &"a".repeat(40), &"b".repeat(40), &missing);

        assert_eq!(selection.mode, "full");
        assert_eq!(
            selection.full_run_trigger.as_deref(),
            Some("invalid-repository-root")
        );

        let non_repository = temporary.path().join("non-repository");
        fs::create_dir(&non_repository).expect("non-repository directory");
        let selection = select(
            "pull_request",
            &"a".repeat(40),
            &"b".repeat(40),
            &non_repository,
        );
        assert_eq!(selection.mode, "full");
        assert_eq!(
            selection.full_run_trigger.as_deref(),
            Some("repository-open-failed")
        );
        assert!(render_summary(&selection).contains("Changed paths: unavailable"));
    }

    #[test]
    fn selector_rejects_events_and_missing_revisions_before_reading_a_repository() {
        let missing = Path::new("/selector-test-repository-is-not-read");
        let head = "b".repeat(40);

        let non_pull_request = select("push", "", "", missing);
        assert_eq!(non_pull_request.mode, "full");
        assert_eq!(
            non_pull_request.full_run_trigger.as_deref(),
            Some("non-pull-request-event:push")
        );

        let missing_base = select("pull_request", "invalid", &head, missing);
        assert_eq!(
            missing_base.full_run_trigger.as_deref(),
            Some("missing-or-invalid-pr-base-sha")
        );

        let missing_head = select("pull_request", &"a".repeat(40), "invalid", missing);
        assert_eq!(
            missing_head.full_run_trigger.as_deref(),
            Some("missing-or-invalid-pr-head-sha")
        );
    }

    #[test]
    fn audited_supplementary_diffs_select_the_skip_lane() {
        let repository = fixture_repository();
        let base = git_output(repository.path(), &["rev-parse", "HEAD"]);
        commit_file(repository.path(), "docs/head.md", "head\n", "head");
        let head = git_output(repository.path(), &["rev-parse", "HEAD"]);

        let selection = select("pull_request", &base, &head, repository.path());

        assert_eq!(selection.mode, "skip", "{selection:#?}");
        assert_eq!(selection.changed_paths.len(), 1);
        assert_eq!(
            selection.skip_proof.as_deref(),
            Some("all changed paths have audited non-Rust validation owners")
        );
        assert_eq!(
            selection.validation_owners,
            vec!["lint plus trusted-main repository policy and plugin validation"]
        );
        assert!(valid_serialized_selection(&selection));
    }

    #[test]
    fn rust_diffs_select_policy_consumer_and_reverse_dependents() {
        let repository = workspace_fixture();
        let base = git_output(repository.path(), &["rev-parse", "HEAD"]);
        commit_file(
            repository.path(),
            "leaf/src/lib.rs",
            "pub fn value() -> u8 { 2 }\n",
            "change leaf",
        );
        let head = git_output(repository.path(), &["rev-parse", "HEAD"]);

        let selection = select("pull_request", &base, &head, repository.path());

        assert_eq!(selection.mode, "partial", "{selection:#?}");
        assert_eq!(
            selection.changed_paths,
            vec![ChangedPath {
                paths: vec!["leaf/src/lib.rs".to_owned()],
                status: "M".to_owned(),
            }]
        );
        assert_eq!(selection.affected_packages, vec!["larch-cli", "leaf"]);
        assert_eq!(selection.reverse_dependents, vec!["larch-cli"]);
        assert_eq!(selection.doctest_packages, vec!["larch-cli", "leaf"]);
        assert_eq!(
            selection
                .partial_commands
                .iter()
                .map(|command| command.name.as_str())
                .collect::<Vec<_>>(),
            vec!["format", "clippy", "test", "doctests"]
        );
        assert!(valid_serialized_selection(&selection));

        let result_file = repository.path().join("selector-result.json");
        fs::write(
            &result_file,
            serde_json::to_string(&selection).expect("selector result JSON"),
        )
        .expect("write selector result");
        let restored = read_serialized_selection(&result_file).expect("valid selector result");
        assert_eq!(restored, selection);

        let summary = render_summary(&restored);
        assert!(summary.contains("Proposed mode: <code>partial</code>"));
        assert!(summary.contains("Reverse dependents"));
        assert!(summary.contains("Proposed partial commands"));
    }

    #[test]
    fn rust_diffs_outside_the_policy_consumer_choose_the_full_lane() {
        let repository = workspace_fixture();
        let base = git_output(repository.path(), &["rev-parse", "HEAD"]);
        commit_file(
            repository.path(),
            "unused/src/lib.rs",
            "pub fn value() -> u8 { 2 }\n",
            "change unused",
        );
        let head = git_output(repository.path(), &["rev-parse", "HEAD"]);

        let selection = select("pull_request", &base, &head, repository.path());

        assert_eq!(selection.mode, "full", "{selection:#?}");
        assert_eq!(
            selection.full_run_trigger.as_deref(),
            Some("partial-does-not-build-policy-consumer"),
            "{selection:#?}"
        );
        assert!(valid_serialized_selection(&selection));
        assert!(render_summary(&selection).contains("Full-run trigger"));
    }

    #[test]
    fn unavailable_comparison_base_chooses_the_full_lane() {
        let repository = fixture_repository();
        let head = git_output(repository.path(), &["rev-parse", "HEAD"]);
        let selection = select("pull_request", &"a".repeat(40), &head, repository.path());

        assert_eq!(selection.mode, "full");
        assert_eq!(
            selection.full_run_trigger.as_deref(),
            Some("base-commit-failed")
        );
    }

    #[test]
    fn shallow_history_cannot_prove_a_comparison_base() {
        let upstream = fixture_repository();
        let base = git_output(upstream.path(), &["rev-parse", "HEAD"]);
        commit_file(upstream.path(), "docs/head.md", "head\n", "head");
        let head = git_output(upstream.path(), &["rev-parse", "HEAD"]);
        let clone_root = tempfile::tempdir().expect("clone root");
        let shallow = clone_root.path().join("shallow");
        let source = format!("file://{}", upstream.path().display());
        git_output(
            clone_root.path(),
            &["clone", "--quiet", "--depth", "1", &source, "shallow"],
        );

        let selection = select("pull_request", &base, &head, &shallow);

        assert_eq!(selection.mode, "full");
        assert_eq!(
            selection.full_run_trigger.as_deref(),
            Some("base-commit-failed")
        );
    }

    #[test]
    fn gitleaks_history_requires_a_merge_base_or_parent() {
        let repository = fixture_repository();
        assert_eq!(
            resolve_gitleaks_base(repository.path(), "origin/main"),
            Err("gitleaks history base is unavailable".to_owned())
        );
    }

    #[test]
    fn gitleaks_history_ignores_non_commit_base_references() {
        let repository = fixture_repository();
        let parent = git_output(repository.path(), &["rev-parse", "HEAD"]);
        commit_file(repository.path(), "docs/head.md", "head\n", "head");
        let blob = git_output(repository.path(), &["hash-object", "docs/base.md"]);
        git_output(
            repository.path(),
            &["update-ref", "refs/larch-tests/non-commit-base", &blob],
        );

        assert_eq!(
            resolve_gitleaks_base(repository.path(), "refs/larch-tests/non-commit-base"),
            Ok(parent)
        );
    }

    #[test]
    fn gitleaks_history_prefers_the_proven_merge_base() {
        let repository = fixture_repository();
        let base = git_output(repository.path(), &["rev-parse", "HEAD"]);
        commit_file(repository.path(), "docs/head.md", "head\n", "head");
        git_output(
            repository.path(),
            &["update-ref", "refs/remotes/origin/main", &base],
        );

        assert_eq!(
            resolve_gitleaks_base(repository.path(), "origin/main"),
            Ok(base)
        );
    }

    #[test]
    fn untrusted_candidate_changes_are_redacted_before_publication() {
        let secret = format!("ghp_{}", "a".repeat(32));
        let selection = public_selection(&full_selection(
            "pull_request",
            Some("a".repeat(40)),
            Some("b".repeat(40)),
            "github-pr-base",
            "unknown-path-has-no-named-validation-owner",
            vec![ChangedPath {
                paths: vec![format!("crates/larch-cli/src/{secret}.rs")],
                status: "A".to_owned(),
            }],
        ));
        let serialized = serde_json::to_string(&selection).expect("selector JSON");

        assert!(!serialized.contains(&secret));
        assert!(serialized.contains("<REDACTED-TOKEN>"));
    }

    #[test]
    fn summary_refuses_malformed_or_unbounded_candidate_results() {
        let mut malformed = full_selection(
            "pull_request",
            Some("a".repeat(40)),
            Some("b".repeat(40)),
            "github-pr-base",
            "unknown-path-has-no-named-validation-owner",
            vec![ChangedPath {
                paths: vec!["../untrusted.rs".to_owned()],
                status: "M".to_owned(),
            }],
        );

        assert!(!valid_serialized_selection(&malformed));
        malformed.changed_paths.clear();
        malformed.full_run_trigger = Some("trigger\nwith-line-break".to_owned());
        assert!(!valid_serialized_selection(&malformed));

        let temporary = tempfile::tempdir().expect("temporary result directory");
        let result = temporary.path().join("selector-result.json");
        let oversized_size = usize::try_from(MAX_RESULT_FILE_BYTES + 1)
            .expect("maximum selector result file size fits usize");
        fs::write(&result, "x".repeat(oversized_size)).expect("oversized selector result");

        assert!(read_serialized_selection(&result).is_none());
    }

    fn fixture_repository() -> TempDir {
        let repository = initialized_repository();
        commit_file(repository.path(), "docs/base.md", "base\n", "base");
        repository
    }

    fn workspace_fixture() -> TempDir {
        let repository = initialized_repository();
        write_file(
            repository.path(),
            "Cargo.toml",
            "[workspace]\nmembers = [\"leaf\", \"larch-cli\", \"unused\"]\nresolver = \"3\"\n",
        );
        write_file(
            repository.path(),
            "leaf/Cargo.toml",
            "[package]\nname = \"leaf\"\nversion = \"0.1.0\"\nedition = \"2024\"\n",
        );
        write_file(
            repository.path(),
            "leaf/src/lib.rs",
            "pub fn value() -> u8 { 1 }\n",
        );
        write_file(
            repository.path(),
            "larch-cli/Cargo.toml",
            "[package]\nname = \"larch-cli\"\nversion = \"0.1.0\"\nedition = \"2024\"\n\n[dependencies]\nleaf = { path = \"../leaf\" }\n",
        );
        write_file(
            repository.path(),
            "larch-cli/src/lib.rs",
            "pub fn value() -> u8 { leaf::value() }\n",
        );
        write_file(
            repository.path(),
            "unused/Cargo.toml",
            "[package]\nname = \"unused\"\nversion = \"0.1.0\"\nedition = \"2024\"\n",
        );
        write_file(
            repository.path(),
            "unused/src/lib.rs",
            "pub fn value() -> u8 { 1 }\n",
        );
        write_file(
            repository.path(),
            "Cargo.lock",
            concat!(
                "# This file is automatically @generated by Cargo.\n",
                "# It is not intended for manual editing.\n",
                "version = 4\n\n",
                "[[package]]\nname = \"larch-cli\"\nversion = \"0.1.0\"\n",
                "dependencies = [\n \"leaf\",\n]\n\n",
                "[[package]]\nname = \"leaf\"\nversion = \"0.1.0\"\n\n",
                "[[package]]\nname = \"unused\"\nversion = \"0.1.0\"\n"
            ),
        );
        commit_all(repository.path(), "base");
        repository
    }

    fn initialized_repository() -> TempDir {
        let repository = tempfile::tempdir().expect("repository");
        git_output(repository.path(), &["init", "--quiet"]);
        git_output(
            repository.path(),
            &["config", "user.email", "test@example.invalid"],
        );
        git_output(repository.path(), &["config", "user.name", "Larch test"]);
        repository
    }

    fn commit_file(repository: &Path, relative: &str, contents: &str, message: &str) {
        write_file(repository, relative, contents);
        commit_all(repository, message);
    }

    fn write_file(repository: &Path, relative: &str, contents: &str) {
        let path = repository.join(relative);
        fs::create_dir_all(path.parent().expect("fixture parent")).expect("fixture directory");
        fs::write(&path, contents).expect("fixture file");
    }

    fn commit_all(repository: &Path, message: &str) {
        git_output(repository, &["add", "--all"]);
        git_output(repository, &["commit", "--quiet", "-m", message]);
    }

    fn git_output(repository: &Path, arguments: &[&str]) -> String {
        let output = Command::new("git") // lint-subprocess-via-runner: ok test-only Git fixtures construct typed repository states
            .arg("-C")
            .arg(repository)
            .args(arguments)
            .output()
            .expect("run fixture git");
        assert!(
            output.status.success(),
            "fixture git command failed: {}",
            output.status
        );
        String::from_utf8(output.stdout)
            .expect("fixture Git output")
            .trim()
            .to_owned()
    }
}
