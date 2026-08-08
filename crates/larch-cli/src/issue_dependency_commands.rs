//! The issue-graph write verbs: `issue add-blocked-by`, `issue add-sub-issue`,
//! and the two `/block-issue` dependency mutations.
//!
//! All four wire one edge into GitHub's native issue graph and prove it by a
//! fresh read-back. They differ only in what they publish: the two `issue`
//! verbs report a `KEY=value` envelope `/issue` branches on, while
//! `/block-issue` reports a human line plus a distinct exit code per refusal
//! class, which `/triage` reads before it advances its compare-and-swap
//! timestamp.
//!
//! Every read and write goes through the typed GitHub adapter, so the
//! live-mutation gate, the triage freshness precondition, the idempotent
//! pre-read, and the exact read-back are the ones the adapter owns. What lives
//! here is the retry contract the documented command surface promises: three
//! attempts with 10-second and 30-second pre-retry sleeps, for transient
//! transport failures only. A deterministic refusal — an absent feature, a
//! rejected precondition, a read-back that disagrees — is never retried,
//! because a second identical request cannot change it.

use crate::{
    blocker_commands::resolve_repo_for,
    github_repository_resolution::repository_ref,
    github_service::{ServiceFailure, with_github_service},
    issue_mutation_support::{
        EXIT_MUTATION_REFUSED, MUTATION_REFUSAL_REASON, MUTATION_REFUSAL_STATUS,
        authorization_request, authorized, flat_error,
    },
};
use chrono::DateTime;
use larch_adapters::{
    github::{DependencyEdge, GitHubOperationError, OctocrabGitHubService, SubIssueEdge},
    runtime::Cancellation,
};
use larch_core::{GitHubRepositoryRef, GitHubService, emit_kv, positive_integer};
use std::{ffi::OsString, process::ExitCode, time::Duration};

/// How many characters of a diagnostic survive into a contract row.
const ERROR_CHARS: usize = 500;
/// How many characters of a `/block-issue` diagnostic survive its stderr row.
const BLOCK_ISSUE_ERROR_CHARS: usize = 1000;
/// How many times a transient transport failure is retried, in total attempts.
const ATTEMPTS: usize = 3;
/// Pre-retry pauses before the second and third attempts.
const RETRY_PAUSES: [Duration; 2] = [Duration::from_secs(10), Duration::from_secs(30)];

// ------------------------------------------------------------------- shared

/// One refused issue-graph write, as the diagnostic and exit code it publishes.
#[derive(Debug, Eq, PartialEq)]
struct EdgeFailure {
    error: String,
    code: u8,
}

impl EdgeFailure {
    /// Build a refusal, collapsing and redacting its diagnostic first.
    fn new(message: &str, code: u8) -> Self {
        Self {
            error: flat_error(message, ERROR_CHARS),
            code,
        }
    }

    /// Build the refusal a failed authorization check publishes.
    fn refused(reason: &str) -> Self {
        Self::new(
            &format!("{MUTATION_REFUSAL_REASON}:{reason}"),
            EXIT_MUTATION_REFUSED,
        )
    }
}

/// Classify one adapter error into the refusal an `issue` verb publishes.
///
/// Only the live-mutation gate earns its own exit code; every other failure is
/// the generic refusal, which is what the Python entrypoints reported for the
/// whole class.
fn edge_failure_from(error: &GitHubOperationError) -> EdgeFailure {
    match error {
        GitHubOperationError::MutationRefused(reason) => EdgeFailure::refused(reason),
        GitHubOperationError::DependencyFeatureUnavailable
        | GitHubOperationError::SubIssueFeatureUnavailable => {
            EdgeFailure::new(&format!("feature-unavailable: {error}"), 2)
        }
        other => EdgeFailure::new(&other.to_string(), 2),
    }
}

/// Report whether one adapter error is worth a second identical request.
///
/// Only transport-class failures are: a rate limit, an unreachable API, and a
/// server error whose outcome reconciliation could not settle. Everything else
/// — an absent feature, a refused authorization, a rejected precondition, a
/// read-back that disagrees — is deterministic, so retrying it would only
/// spend the caller's sleep budget to reach the same answer.
const fn transient(error: &GitHubOperationError) -> bool {
    matches!(
        error,
        GitHubOperationError::RateLimited
            | GitHubOperationError::Transport(_)
            | GitHubOperationError::AmbiguousMutation
    )
}

/// Pause before `attempt`, which is zero for the first try.
async fn pause_before(attempt: usize) {
    if let Some(pause) = attempt
        .checked_sub(1)
        .and_then(|index| RETRY_PAUSES.get(index))
    {
        tokio::time::sleep(*pause).await;
    }
}

/// Run one idempotent issue-graph write under the documented retry contract.
///
/// The adapter operations are idempotent by construction — each pre-reads the
/// live edge set and returns `AlreadyInDesiredState` when the edge already
/// matches — so a retry after a transport failure that did land converges on
/// the same graph rather than duplicating an edge.
async fn with_retries<T, F>(mut operation: impl FnMut() -> F) -> Result<T, GitHubOperationError>
where
    F: Future<Output = Result<T, GitHubOperationError>>,
{
    let mut last = GitHubOperationError::Malformed("no attempt was made");
    for attempt in 0..ATTEMPTS {
        pause_before(attempt).await;
        match operation().await {
            Ok(value) => return Ok(value),
            Err(error) if transient(&error) => last = error,
            Err(error) => return Err(error),
        }
    }
    Err(last)
}

/// Resolve the numeric database id GitHub's issue-graph endpoints require.
///
/// A caller that already holds the id passes it and skips this round-trip,
/// which is what `/issue` does for a batch sibling it has just filed.
async fn resolve_issue_id(
    service: &OctocrabGitHubService,
    cancellation: &Cancellation,
    repository: &GitHubRepositoryRef,
    number: u64,
    cached: Option<u64>,
    label: &str,
) -> Result<u64, EdgeFailure> {
    if let Some(identifier) = cached {
        return Ok(identifier);
    }
    service
        .issue(repository, number, cancellation)
        .await
        .map(|issue| issue.id)
        .map_err(|error| {
            EdgeFailure::new(&format!("{label} lookup failed for #{number}: {error}"), 2)
        })
}

// ------------------------------------------------------------- shared scanner

/// One usable command line for either `issue` issue-graph verb.
///
/// The two verbs name their subject and object differently — `--client-issue`
/// and `--blocker-issue` against `--parent-issue` and `--child-issue` — so the
/// scanner is told which pair to read and stores both as `subject` and
/// `object`.
#[derive(Debug, Default, Eq, PartialEq)]
struct EdgeArguments {
    subject: String,
    object: String,
    object_id: String,
    repo: String,
    context_file: String,
    run_id: String,
    trusted_root: String,
    operator_invoked: bool,
}

/// The option names one `issue` issue-graph verb reads.
#[derive(Clone, Copy)]
struct EdgeOptions {
    subject: &'static str,
    object: &'static str,
    object_id: &'static str,
    usage: &'static str,
}

const BLOCKED_BY_OPTIONS: EdgeOptions = EdgeOptions {
    subject: "--client-issue",
    object: "--blocker-issue",
    object_id: "--blocker-id",
    usage: "Usage: add-blocked-by --client-issue N --blocker-issue M [--blocker-id ID] [--repo OWNER/REPO] [--operator-invoked | --context-file PATH --run-id ID --trusted-root PATH]",
};

const SUB_ISSUE_OPTIONS: EdgeOptions = EdgeOptions {
    subject: "--parent-issue",
    object: "--child-issue",
    object_id: "--child-id",
    usage: "Usage: add-sub-issue --parent-issue N --child-issue M [--child-id ID] [--repo OWNER/REPO]",
};

/// Scan one `issue` issue-graph command line.
///
/// A value-taking option that ends the line reads as an unknown option, which
/// is how the legacy scanner reported it, and an unknown option prints one
/// stderr line and exits `1` with no rows at all.
fn parse_edge_arguments(
    arguments: &[OsString],
    options: EdgeOptions,
) -> Result<EdgeArguments, String> {
    let mut parsed = EdgeArguments::default();
    let mut index = 0;
    while index < arguments.len() {
        let token = arguments[index].to_string_lossy().into_owned();
        if token == "--operator-invoked" {
            parsed.operator_invoked = true;
            index += 1;
            continue;
        }
        let target: Option<&mut String> = match token.as_str() {
            value if value == options.subject => Some(&mut parsed.subject),
            value if value == options.object => Some(&mut parsed.object),
            value if value == options.object_id => Some(&mut parsed.object_id),
            "--repo" => Some(&mut parsed.repo),
            "--context-file" => Some(&mut parsed.context_file),
            "--run-id" => Some(&mut parsed.run_id),
            "--trusted-root" => Some(&mut parsed.trusted_root),
            _ => None,
        };
        match (target, arguments.get(index + 1)) {
            (Some(target), Some(value)) => {
                *target = value.to_string_lossy().into_owned();
                index += 2;
            }
            _ => return Err(format!("Unknown option: {token}")),
        }
    }
    Ok(parsed)
}

/// Everything the live path needs after validation and repository resolution.
#[derive(Debug)]
struct LiveEdge {
    repository: GitHubRepositoryRef,
    subject: u64,
    object: u64,
    object_id: Option<u64>,
    context_file: String,
    run_id: String,
    trusted_root: String,
    operator_invoked: bool,
}

/// Validate one scanned command line and resolve its repository.
///
/// The order is the one the Python entrypoints used and `/issue` depends on:
/// the numeric checks refuse before authorization is consulted, and
/// authorization refuses before any repository is resolved or contacted.
fn plan_edge(arguments: &EdgeArguments, options: EdgeOptions) -> Result<LiveEdge, EdgeFailure> {
    let (Some(subject), Some(object)) = (
        positive_integer(&arguments.subject),
        positive_integer(&arguments.object),
    ) else {
        return Err(EdgeFailure::new(
            &format!(
                "{} and {} must be positive integers",
                options.subject.trim_start_matches("--"),
                options.object.trim_start_matches("--")
            ),
            1,
        ));
    };
    let object_id = if arguments.object_id.is_empty() {
        None
    } else {
        match positive_integer(&arguments.object_id) {
            Some(identifier) => Some(identifier),
            None => {
                return Err(EdgeFailure::new(
                    &format!(
                        "{} must be a positive integer when provided",
                        options.object_id.trim_start_matches("--")
                    ),
                    1,
                ));
            }
        }
    };
    let authorization = authorization_request(
        &arguments.context_file,
        &arguments.run_id,
        &arguments.trusted_root,
        arguments.operator_invoked,
    );
    if let Err(reason) = authorized(&authorization) {
        return Err(EdgeFailure::refused(reason));
    }
    let Some(repo) = resolve_repo_for((!arguments.repo.is_empty()).then_some(&arguments.repo))
    else {
        return Err(EdgeFailure::new("could not determine repo", 2));
    };
    let Ok(repository) = repository_ref(&repo) else {
        return Err(EdgeFailure::new(
            &format!("repository slug is invalid: {repo}"),
            2,
        ));
    };
    Ok(LiveEdge {
        repository,
        subject,
        object,
        object_id,
        context_file: arguments.context_file.clone(),
        run_id: arguments.run_id.clone(),
        trusted_root: arguments.trusted_root.clone(),
        operator_invoked: arguments.operator_invoked,
    })
}

/// Publish one `issue` issue-graph envelope and return its exit code.
fn report_edge(
    outcome: &Result<(), EdgeFailure>,
    added_row: &str,
    failed_row: &str,
    subject: (&str, &str),
    object: (&str, &str),
) -> ExitCode {
    match outcome {
        Ok(()) => emit_kv(added_row, "true"),
        Err(failure) => {
            if failure.code == EXIT_MUTATION_REFUSED {
                emit_kv(MUTATION_REFUSAL_STATUS, "true");
            }
            emit_kv(failed_row, "true");
        }
    }
    emit_kv(subject.0, &flat_error(subject.1, ERROR_CHARS));
    emit_kv(object.0, &flat_error(object.1, ERROR_CHARS));
    match outcome {
        Ok(()) => ExitCode::SUCCESS,
        Err(failure) => {
            if !failure.error.is_empty() {
                emit_kv("ERROR", &failure.error);
            }
            ExitCode::from(failure.code)
        }
    }
}

// ------------------------------------------------------------ issue add-blocked-by

/// Record one issue as blocked by another and prove the edge by read-back.
///
/// Exits `0` once the edge is present, `1` for an unusable command line, `5`
/// when live-mutation authorization refuses the write, and `2` for every other
/// refusal.
pub fn add_blocked_by(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_edge_arguments(arguments, BLOCKED_BY_OPTIONS) {
        Ok(parsed) => parsed,
        Err(message) => {
            eprintln!("{message}");
            return ExitCode::from(1);
        }
    };
    if parsed.subject.is_empty() || parsed.object.is_empty() {
        eprintln!("{}", BLOCKED_BY_OPTIONS.usage);
        return ExitCode::from(1);
    }
    let outcome = plan_edge(&parsed, BLOCKED_BY_OPTIONS).and_then(|edge| apply_blocked_by(&edge));
    report_edge(
        &outcome,
        "BLOCKED_BY_ADDED",
        "BLOCKED_BY_FAILED",
        ("CLIENT", &parsed.subject),
        ("BLOCKER", &parsed.object),
    )
}

/// Add the dependency edge, resolving the blocker's database id when needed.
fn apply_blocked_by(edge: &LiveEdge) -> Result<(), EdgeFailure> {
    let authorization = authorization_request(
        &edge.context_file,
        &edge.run_id,
        &edge.trusted_root,
        edge.operator_invoked,
    );
    run_edge(async |service, cancellation| {
        let blocker_id = resolve_issue_id(
            service,
            cancellation,
            &edge.repository,
            edge.object,
            edge.object_id,
            "blocker-id",
        )
        .await?;
        let dependency = DependencyEdge {
            owner: edge.repository.owner(),
            repo: edge.repository.name(),
            client_issue: edge.subject,
            blocker_id,
            expected_updated_at: None,
        };
        with_retries(|| service.add_blocked_by(cancellation, &authorization, dependency))
            .await
            .map(|_receipt| ())
            .map_err(|error| edge_failure_from(&error))
    })
}

// -------------------------------------------------------------- issue add-sub-issue

/// Attach one direct native sub-issue and prove the relation by read-back.
///
/// Exits `0` once the relation is present, `1` for an unusable command line,
/// `5` when live-mutation authorization refuses the write, and `2` otherwise.
pub fn add_sub_issue(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_edge_arguments(arguments, SUB_ISSUE_OPTIONS) {
        Ok(parsed) => parsed,
        Err(message) => {
            eprintln!("{message}");
            return ExitCode::from(1);
        }
    };
    if parsed.subject.is_empty() || parsed.object.is_empty() {
        eprintln!("{}", SUB_ISSUE_OPTIONS.usage);
        return ExitCode::from(1);
    }
    let outcome = plan_edge(&parsed, SUB_ISSUE_OPTIONS).and_then(|edge| apply_sub_issue(&edge));
    report_edge(
        &outcome,
        "SUB_ISSUE_ADDED",
        "SUB_ISSUE_FAILED",
        ("PARENT", &parsed.subject),
        ("CHILD", &parsed.object),
    )
}

/// Add the sub-issue relation, resolving the child's database id when needed.
fn apply_sub_issue(edge: &LiveEdge) -> Result<(), EdgeFailure> {
    let authorization = authorization_request(
        &edge.context_file,
        &edge.run_id,
        &edge.trusted_root,
        edge.operator_invoked,
    );
    run_edge(async |service, cancellation| {
        let sub_issue_id = resolve_issue_id(
            service,
            cancellation,
            &edge.repository,
            edge.object,
            edge.object_id,
            "child-id",
        )
        .await?;
        let relation = SubIssueEdge {
            owner: edge.repository.owner(),
            repo: edge.repository.name(),
            parent_issue: edge.subject,
            sub_issue_id,
        };
        with_retries(|| service.add_sub_issue(cancellation, &authorization, relation))
            .await
            .map(|_receipt| ())
            .map_err(|error| edge_failure_from(&error))
    })
}

/// Run one issue-graph write against a freshly built GitHub service.
///
/// A client that cannot be built is the same generic refusal every other
/// GitHub-backed failure produces, so the caller reports one envelope shape.
fn run_edge(
    operation: impl AsyncFnOnce(&OctocrabGitHubService, &Cancellation) -> Result<(), EdgeFailure>,
) -> Result<(), EdgeFailure> {
    match with_github_service(async |service, cancellation| {
        Ok(operation(service, cancellation).await)
    }) {
        Ok(result) => result,
        Err(ServiceFailure::Setup(detail) | ServiceFailure::Operation(detail)) => {
            Err(EdgeFailure::new(&detail, 2))
        }
    }
}

// ------------------------------------------------------ block-issue add/remove

/// Exit code for an unusable `/block-issue` command line.
const BLOCK_ISSUE_EXIT_USAGE: u8 = 2;
/// Exit code for a `/block-issue` live-mutation authorization refusal.
const BLOCK_ISSUE_EXIT_UNAUTHORIZED: u8 = 3;
/// Exit code for a failed `/block-issue` triage precondition.
const BLOCK_ISSUE_EXIT_PRECONDITION: u8 = 4;
/// Exit code for a `/block-issue` transport or lookup failure.
const BLOCK_ISSUE_EXIT_TRANSPORT: u8 = 7;
/// Exit code for a `/block-issue` postcondition that could not be proven.
const BLOCK_ISSUE_EXIT_POSTCONDITION: u8 = 8;

/// Validated `/block-issue` dependency mutation arguments.
#[derive(Debug, Default, Eq, PartialEq)]
struct BlockIssueArguments {
    issue: u64,
    blocker: u64,
    repo: String,
    triage_controlled: bool,
    expected_updated_at: String,
}

/// Add one operator-invoked `ISSUE_A` blocked-by `ISSUE_B` relationship.
pub fn block_issue_add(arguments: &[OsString]) -> ExitCode {
    run_block_issue(arguments, false)
}

/// Remove one operator-invoked `ISSUE_A` blocked-by `ISSUE_B` relationship.
pub fn block_issue_remove(arguments: &[OsString]) -> ExitCode {
    run_block_issue(arguments, true)
}

/// Drive one `/block-issue` mutation and publish its verified receipt.
///
/// Success is three stdout rows and a human line; every refusal is one
/// `ERROR=` stderr row and the exit code that names its class, which is what
/// `/triage` branches on before it advances its snapshot timestamp.
fn run_block_issue(arguments: &[OsString], remove: bool) -> ExitCode {
    let verb = if remove {
        "remove-blocked-by"
    } else {
        "add-blocked-by"
    };
    let (parsed, repository) =
        match parse_block_issue_arguments(arguments, verb).and_then(resolve_block_issue_repo) {
            Ok(resolved) => resolved,
            Err(failure) => return report_block_issue_failure(&failure),
        };
    match mutate_block_issue(&parsed, &repository, remove) {
        Err(failure) => report_block_issue_failure(&failure),
        Ok(updated_at) => {
            emit_kv("SUCCESS", "true");
            emit_kv("RELATION_VERIFIED", "true");
            if let Some(updated_at) = updated_at {
                emit_kv("UPDATED_AT", &updated_at);
            }
            let state = if remove {
                "is no longer blocked by"
            } else {
                "is now blocked by"
            };
            println!("✓ #{} {state} #{}", parsed.issue, parsed.blocker);
            ExitCode::SUCCESS
        }
    }
}

/// Publish one `/block-issue` refusal on stderr and return its exit code.
fn report_block_issue_failure(failure: &EdgeFailure) -> ExitCode {
    eprintln!("ERROR={}", failure.error);
    ExitCode::from(failure.code)
}

/// Scan the two positional issue numbers and the four `/block-issue` options.
///
/// Every refusal here is exit `2`: an unusable command line is a usage error,
/// not a mutation outcome, so no row is published on stdout.
fn parse_block_issue_arguments(
    arguments: &[OsString],
    verb: &str,
) -> Result<BlockIssueArguments, EdgeFailure> {
    let usage = || {
        EdgeFailure::new(
            &format!(
                "Usage: {verb} <ISSUE_A> <ISSUE_B> [--repo owner/name] --operator-invoked [--triage-controlled --expected-updated-at TIMESTAMP]"
            ),
            BLOCK_ISSUE_EXIT_USAGE,
        )
    };
    let mut positional: Vec<String> = Vec::new();
    let mut repo = String::new();
    let mut expected = String::new();
    let mut operator_invoked = false;
    let mut triage_controlled = false;
    let mut index = 0;
    while index < arguments.len() {
        let token = arguments[index].to_string_lossy().into_owned();
        match token.as_str() {
            "--repo" | "--expected-updated-at" => {
                let value = arguments
                    .get(index + 1)
                    .map(|value| value.to_string_lossy().into_owned())
                    .filter(|value| !value.is_empty())
                    .ok_or_else(|| {
                        EdgeFailure::new(
                            &format!("{token} requires a value"),
                            BLOCK_ISSUE_EXIT_USAGE,
                        )
                    })?;
                if token == "--repo" {
                    repo = value;
                } else {
                    expected = value;
                }
                index += 2;
            }
            "--operator-invoked" => {
                operator_invoked = true;
                index += 1;
            }
            "--triage-controlled" => {
                triage_controlled = true;
                index += 1;
            }
            other if other.starts_with('-') => {
                return Err(EdgeFailure::new(
                    &format!("Unknown flag: {other}"),
                    BLOCK_ISSUE_EXIT_USAGE,
                ));
            }
            _ => {
                positional.push(token);
                index += 1;
            }
        }
    }
    if positional.len() != 2 {
        return Err(usage());
    }
    let (Some(issue), Some(blocker)) = (
        positive_integer(&positional[0]),
        positive_integer(&positional[1]),
    ) else {
        return Err(EdgeFailure::new(
            "Issue numbers must be positive integers (>=1)",
            BLOCK_ISSUE_EXIT_USAGE,
        ));
    };
    if !operator_invoked {
        return Err(EdgeFailure::new(
            "live mutation authorization refused: --operator-invoked is required",
            BLOCK_ISSUE_EXIT_USAGE,
        ));
    }
    if triage_controlled && !is_rfc3339_timestamp(&expected) {
        return Err(EdgeFailure::new(
            "triage-controlled mutation requires a valid --expected-updated-at",
            BLOCK_ISSUE_EXIT_USAGE,
        ));
    }
    if !expected.is_empty() && !triage_controlled {
        return Err(EdgeFailure::new(
            "--expected-updated-at requires --triage-controlled",
            BLOCK_ISSUE_EXIT_USAGE,
        ));
    }
    if !repo.is_empty() && repository_ref(&repo).is_err() {
        return Err(EdgeFailure::new(
            "--repo must be exactly owner/name",
            BLOCK_ISSUE_EXIT_USAGE,
        ));
    }
    Ok(BlockIssueArguments {
        issue,
        blocker,
        repo,
        triage_controlled,
        expected_updated_at: expected,
    })
}

/// Resolve the repository the command line named, or the ambient one.
///
/// The reference travels with the arguments so the mutation never re-parses a
/// slug that has already been validated here.
fn resolve_block_issue_repo(
    arguments: BlockIssueArguments,
) -> Result<(BlockIssueArguments, GitHubRepositoryRef), EdgeFailure> {
    let resolved = if arguments.repo.is_empty() {
        resolve_repo_for(None).and_then(|detected| repository_ref(&detected).ok())
    } else {
        // The scanner already refused an unusable explicit slug.
        repository_ref(&arguments.repo).ok()
    };
    resolved
        .map(|repository| (arguments, repository))
        .ok_or_else(|| {
            EdgeFailure::new(
                "Could not determine repository: pass --repo owner/name",
                BLOCK_ISSUE_EXIT_USAGE,
            )
        })
}

/// Accept only the exact `updatedAt` spelling GitHub publishes.
///
/// The Python entrypoint pinned the same shape with a regular expression, and
/// the adapter re-validates it before it reads the target, so an unusable
/// timestamp is refused at the command line rather than at the first request.
fn is_rfc3339_timestamp(value: &str) -> bool {
    value.ends_with('Z') && DateTime::parse_from_rfc3339(value).is_ok()
}

/// Apply one `/block-issue` mutation and return the fresh target timestamp.
///
/// The timestamp is published only for a triage-controlled mutation, which is
/// the one caller that compares snapshots across calls. The retry contract of
/// the `issue` verbs deliberately does not apply: `/triage` compares and swaps
/// one snapshot timestamp per call, so a silent second attempt would report a
/// receipt for a target the caller never proved fresh.
fn mutate_block_issue(
    arguments: &BlockIssueArguments,
    repository: &GitHubRepositoryRef,
    remove: bool,
) -> Result<Option<String>, EdgeFailure> {
    let authorization = authorization_request("", "", "", true);
    if let Err(reason) = authorized(&authorization) {
        return Err(EdgeFailure::new(
            &format!("live mutation authorization refused: {reason}"),
            BLOCK_ISSUE_EXIT_UNAUTHORIZED,
        ));
    }
    let expected = arguments
        .triage_controlled
        .then(|| arguments.expected_updated_at.clone());
    let outcome = with_github_service(async |service, cancellation| {
        let blocker = match service
            .issue(repository, arguments.blocker, cancellation)
            .await
        {
            Ok(blocker) => blocker,
            Err(error) => {
                return Ok(Err(EdgeFailure::new(
                    &format!("blocker lookup failed for #{}: {error}", arguments.blocker),
                    BLOCK_ISSUE_EXIT_TRANSPORT,
                )));
            }
        };
        let edge = DependencyEdge {
            owner: repository.owner(),
            repo: repository.name(),
            client_issue: arguments.issue,
            blocker_id: blocker.id,
            expected_updated_at: expected.as_deref(),
        };
        let receipt = if remove {
            service
                .remove_blocked_by(cancellation, &authorization, edge)
                .await
        } else {
            service
                .add_blocked_by(cancellation, &authorization, edge)
                .await
        };
        Ok(receipt
            .map(|receipt| receipt.updated_at().map(str::to_owned))
            .map_err(|error| block_issue_failure_from(&error)))
    });
    match outcome {
        Err(ServiceFailure::Setup(detail) | ServiceFailure::Operation(detail)) => {
            Err(EdgeFailure::new(&detail, BLOCK_ISSUE_EXIT_TRANSPORT))
        }
        Ok(result) => result,
    }
}

/// Classify one adapter error into the `/block-issue` exit code it names.
fn block_issue_failure_from(error: &GitHubOperationError) -> EdgeFailure {
    let code = match error {
        GitHubOperationError::MutationRefused(_) => BLOCK_ISSUE_EXIT_UNAUTHORIZED,
        GitHubOperationError::StaleDependencyTarget
        | GitHubOperationError::ProtectedDependencyTarget
        | GitHubOperationError::SecuritySensitiveDependencyTarget => BLOCK_ISSUE_EXIT_PRECONDITION,
        GitHubOperationError::Malformed(_)
        | GitHubOperationError::GraphqlErrors
        | GitHubOperationError::AmbiguousMutation => BLOCK_ISSUE_EXIT_POSTCONDITION,
        _ => BLOCK_ISSUE_EXIT_TRANSPORT,
    };
    EdgeFailure {
        error: flat_error(&error.to_string(), BLOCK_ISSUE_ERROR_CHARS),
        code,
    }
}

#[cfg(test)]
mod tests {
    use super::{
        BLOCKED_BY_OPTIONS, BlockIssueArguments, EdgeArguments, EdgeFailure, RETRY_PAUSES,
        SUB_ISSUE_OPTIONS, block_issue_failure_from, edge_failure_from,
        parse_block_issue_arguments, parse_edge_arguments, pause_before, plan_edge, transient,
        with_retries,
    };
    use larch_adapters::github::GitHubOperationError;
    use std::{cell::Cell, ffi::OsString, time::Duration};
    use tokio::time::Instant;

    fn arguments(values: &[&str]) -> Vec<OsString> {
        values.iter().map(OsString::from).collect()
    }

    #[test]
    fn the_edge_scanner_reads_each_verbs_own_option_names() {
        let parsed = parse_edge_arguments(
            &arguments(&[
                "--client-issue",
                "10",
                "--blocker-issue",
                "11",
                "--blocker-id",
                "9001",
                "--repo",
                "o/r",
                "--operator-invoked",
            ]),
            BLOCKED_BY_OPTIONS,
        )
        .expect("a usable line");
        assert_eq!(
            parsed,
            EdgeArguments {
                subject: "10".to_owned(),
                object: "11".to_owned(),
                object_id: "9001".to_owned(),
                repo: "o/r".to_owned(),
                operator_invoked: true,
                ..EdgeArguments::default()
            }
        );
        // The sub-issue verb reads a different pair, so the blocked-by names
        // are unknown options there and vice versa.
        assert_eq!(
            parse_edge_arguments(&arguments(&["--client-issue", "10"]), SUB_ISSUE_OPTIONS)
                .expect_err("a refusal"),
            "Unknown option: --client-issue"
        );
        assert_eq!(
            parse_edge_arguments(&arguments(&["--parent-issue", "1"]), BLOCKED_BY_OPTIONS)
                .expect_err("a refusal"),
            "Unknown option: --parent-issue"
        );
        // A value-taking option that ends the line reads as unknown.
        assert_eq!(
            parse_edge_arguments(&arguments(&["--repo"]), BLOCKED_BY_OPTIONS)
                .expect_err("a refusal"),
            "Unknown option: --repo"
        );
        assert_eq!(
            parse_edge_arguments(&arguments(&["12"]), BLOCKED_BY_OPTIONS).expect_err("a refusal"),
            "Unknown option: 12"
        );
    }

    #[test]
    fn the_session_authorization_options_are_scanned_as_a_group() {
        let parsed = parse_edge_arguments(
            &arguments(&[
                "--parent-issue",
                "1",
                "--child-issue",
                "2",
                "--context-file",
                "/tmp/source-env.sh",
                "--run-id",
                "run-1",
                "--trusted-root",
                "/tmp/session",
            ]),
            SUB_ISSUE_OPTIONS,
        )
        .expect("a usable line");
        assert_eq!(parsed.context_file, "/tmp/source-env.sh");
        assert_eq!(parsed.run_id, "run-1");
        assert_eq!(parsed.trusted_root, "/tmp/session");
        assert!(!parsed.operator_invoked);
    }

    #[test]
    fn non_numeric_issue_numbers_refuse_before_authorization_is_consulted() {
        let refusal = plan_edge(
            &EdgeArguments {
                subject: "0".to_owned(),
                object: "2".to_owned(),
                ..EdgeArguments::default()
            },
            BLOCKED_BY_OPTIONS,
        )
        .expect_err("a refusal");
        assert_eq!(
            refusal,
            EdgeFailure {
                error: "client-issue and blocker-issue must be positive integers".to_owned(),
                code: 1,
            }
        );
        let refusal = plan_edge(
            &EdgeArguments {
                subject: "1".to_owned(),
                object: "2".to_owned(),
                object_id: "x".to_owned(),
                ..EdgeArguments::default()
            },
            SUB_ISSUE_OPTIONS,
        )
        .expect_err("a refusal");
        assert_eq!(
            refusal,
            EdgeFailure {
                error: "child-id must be a positive integer when provided".to_owned(),
                code: 1,
            }
        );
    }

    #[test]
    fn an_unauthorized_line_refuses_with_the_reserved_mutation_code() {
        let refusal = plan_edge(
            &EdgeArguments {
                subject: "1".to_owned(),
                object: "2".to_owned(),
                repo: "o/r".to_owned(),
                ..EdgeArguments::default()
            },
            BLOCKED_BY_OPTIONS,
        )
        .expect_err("an unauthorized line");
        assert_eq!(refusal.code, 5);
        assert!(
            refusal.error.starts_with("unauthorized-mutation:"),
            "{}",
            refusal.error
        );
    }

    #[test]
    fn only_transport_class_failures_are_worth_a_second_attempt() {
        assert!(transient(&GitHubOperationError::RateLimited));
        assert!(transient(&GitHubOperationError::AmbiguousMutation));
        for deterministic in [
            GitHubOperationError::DependencyFeatureUnavailable,
            GitHubOperationError::SubIssueFeatureUnavailable,
            GitHubOperationError::SubIssuePreconditionFailed,
            GitHubOperationError::Unauthorized,
            GitHubOperationError::MutationRefused("denied"),
            GitHubOperationError::StaleDependencyTarget,
            GitHubOperationError::Malformed("dependency mutation not reflected in read-back"),
        ] {
            assert!(!transient(&deterministic), "{deterministic}");
        }
    }

    #[tokio::test(start_paused = true)]
    async fn a_transient_failure_is_retried_exactly_three_times_then_reported() {
        let attempts = Cell::new(0_usize);
        let outcome: Result<(), GitHubOperationError> = with_retries(|| {
            attempts.set(attempts.get() + 1);
            async { Err(GitHubOperationError::RateLimited) }
        })
        .await;

        assert_eq!(attempts.get(), 3, "three attempts, then exhaustion");
        assert_eq!(
            outcome.expect_err("exhausted"),
            GitHubOperationError::RateLimited
        );
    }

    #[tokio::test(start_paused = true)]
    async fn a_deterministic_failure_stops_after_its_only_attempt() {
        let attempts = Cell::new(0_usize);
        let outcome: Result<(), GitHubOperationError> = with_retries(|| {
            attempts.set(attempts.get() + 1);
            async { Err(GitHubOperationError::DependencyFeatureUnavailable) }
        })
        .await;

        assert_eq!(attempts.get(), 1, "a 404-class refusal is never retried");
        assert_eq!(
            outcome.expect_err("refused"),
            GitHubOperationError::DependencyFeatureUnavailable
        );
    }

    #[tokio::test(start_paused = true)]
    async fn a_recovered_attempt_reports_success_without_exhausting_the_budget() {
        let attempts = Cell::new(0_usize);
        let outcome: Result<u8, GitHubOperationError> = with_retries(|| {
            attempts.set(attempts.get() + 1);
            let first = attempts.get() == 1;
            async move {
                if first {
                    Err(GitHubOperationError::AmbiguousMutation)
                } else {
                    Ok(7)
                }
            }
        })
        .await;

        assert_eq!(attempts.get(), 2);
        assert_eq!(outcome.expect("the second attempt settled"), 7);
    }

    #[tokio::test(start_paused = true)]
    async fn the_pre_retry_pauses_are_ten_and_thirty_seconds_and_stop_there() {
        assert_eq!(
            RETRY_PAUSES,
            [Duration::from_secs(10), Duration::from_secs(30)]
        );
        let start = Instant::now();
        pause_before(0).await;
        assert_eq!(start.elapsed(), Duration::ZERO, "the first try never waits");
        pause_before(1).await;
        pause_before(2).await;
        assert_eq!(start.elapsed(), Duration::from_secs(40));
        // No fourth attempt exists, so no fourth pause is defined either.
        pause_before(3).await;
        assert_eq!(start.elapsed(), Duration::from_secs(40));
    }

    #[test]
    fn every_adapter_error_maps_to_one_issue_verb_refusal_class() {
        assert_eq!(
            edge_failure_from(&GitHubOperationError::MutationRefused("denied")).code,
            5
        );
        let unavailable = edge_failure_from(&GitHubOperationError::SubIssueFeatureUnavailable);
        assert_eq!(unavailable.code, 2);
        assert!(
            unavailable.error.starts_with("feature-unavailable: "),
            "{}",
            unavailable.error
        );
        assert_eq!(
            edge_failure_from(&GitHubOperationError::SubIssuePreconditionFailed).code,
            2
        );
    }

    #[test]
    fn the_block_issue_scanner_enforces_its_whole_flag_contract() {
        assert_eq!(
            parse_block_issue_arguments(
                &arguments(&[
                    "101",
                    "99",
                    "--repo",
                    "o/r",
                    "--operator-invoked",
                    "--triage-controlled",
                    "--expected-updated-at",
                    "2026-08-07T01:02:03Z",
                ]),
                "add-blocked-by"
            )
            .expect("a usable line"),
            BlockIssueArguments {
                issue: 101,
                blocker: 99,
                repo: "o/r".to_owned(),
                triage_controlled: true,
                expected_updated_at: "2026-08-07T01:02:03Z".to_owned(),
            }
        );
        for (line, message) in [
            (&["1"][..], "Usage: add-blocked-by <ISSUE_A> <ISSUE_B>"),
            (&["1", "2", "3"][..], "Usage: add-blocked-by <ISSUE_A>"),
            (&["--bogus"][..], "Unknown flag: --bogus"),
            (&["--repo"][..], "--repo requires a value"),
            (&["--repo", ""][..], "--repo requires a value"),
            (
                &["0", "2", "--operator-invoked"][..],
                "Issue numbers must be positive integers (>=1)",
            ),
            (
                &["1", "2"][..],
                "live mutation authorization refused: --operator-invoked is required",
            ),
            (
                &["1", "2", "--operator-invoked", "--triage-controlled"][..],
                "triage-controlled mutation requires a valid --expected-updated-at",
            ),
            (
                &[
                    "1",
                    "2",
                    "--operator-invoked",
                    "--triage-controlled",
                    "--expected-updated-at",
                    "yesterday",
                ][..],
                "triage-controlled mutation requires a valid --expected-updated-at",
            ),
            (
                &[
                    "1",
                    "2",
                    "--operator-invoked",
                    "--expected-updated-at",
                    "2026-08-07T01:02:03Z",
                ][..],
                "--expected-updated-at requires --triage-controlled",
            ),
            (
                &["1", "2", "--operator-invoked", "--repo", "not-a-slug"][..],
                "--repo must be exactly owner/name",
            ),
        ] {
            let refusal = parse_block_issue_arguments(&arguments(line), "add-blocked-by")
                .expect_err("a refusal");
            assert_eq!(refusal.code, 2, "{line:?}");
            assert!(
                refusal.error.starts_with(message),
                "{line:?}: {}",
                refusal.error
            );
        }
    }

    #[test]
    fn every_adapter_error_maps_to_one_block_issue_exit_class() {
        for (error, code) in [
            (GitHubOperationError::MutationRefused("denied"), 3),
            (GitHubOperationError::StaleDependencyTarget, 4),
            (GitHubOperationError::ProtectedDependencyTarget, 4),
            (GitHubOperationError::SecuritySensitiveDependencyTarget, 4),
            (GitHubOperationError::Unauthorized, 7),
            (GitHubOperationError::RateLimited, 7),
            (GitHubOperationError::DependencyFeatureUnavailable, 7),
            (GitHubOperationError::AmbiguousMutation, 8),
            (GitHubOperationError::GraphqlErrors, 8),
            (
                GitHubOperationError::Malformed("dependency mutation not reflected in read-back"),
                8,
            ),
        ] {
            assert_eq!(block_issue_failure_from(&error).code, code, "{error}");
        }
    }
}
