//! The `/issue` filing tail: `create-one`, `write-sentinel`, and
//! `cleanup-failed`.
//!
//! These three verbs are what turns a vetted item into a live GitHub issue and
//! what cleans up after one that could not be finished. `create-one` files a
//! single issue and publishes its number, URL, and node id; `write-sentinel`
//! records that the whole run reached its end, which `verify skill-called`
//! later reads; and `cleanup-failed` closes the orphan a failed dependency
//! write left behind so a partial batch does not leak a half-filed issue.
//!
//! Every write goes through [`IssueMutationOwner`], so outbound redaction and
//! the live-mutation authorization gate sit on the same code path the issue
//! field mutations already use. Authorization is checked before any GitHub
//! contact, and creation redacts the title, body, and labels before the
//! request is built.
//!
//! Each verb keeps the hand-rolled option scanner its Python predecessor used,
//! because `/issue` branches on the exact rows and exit codes those scanners
//! produce, and they deliberately disagree: `create-one` reports a refusal as
//! `ISSUE_FAILED=true` on stdout with a per-class exit code, `write-sentinel`
//! reports one on stderr and exits `1`, and `cleanup-failed` reports every
//! outcome as a `CLOSED=` row and always exits `0`.

use crate::{
    argparse_compat::absolute_path,
    blocker_commands::resolve_repo_for,
    github_repository_resolution::repository_ref,
    github_service::{ServiceFailure, with_github_service},
    issue_mutation_support::{
        EXIT_MUTATION_REFUSED, MUTATION_REFUSAL_REASON, MUTATION_REFUSAL_STATUS,
        authorization_request, authorized, create_with_rollback, flat_error, sanitized_line,
    },
};
use chrono::Utc;
use larch_adapters::{
    PathIntent, TemporaryRoot, atomic_write_utf8, ensure_directory_chain,
    github::{IssueCreateFailure, IssueMutationOwner},
    runtime::Cancellation,
};
use larch_core::{
    CreatedIssue, GitHubRepositoryRef, GitHubService, IssueCreateRequest, emit_kv,
    normalize_title_prefix, redact_issue_text_outbound, unsigned_integer,
};
use std::{
    ffi::OsString,
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
};

/// The heading an OOS body opens with, which forces the `[OOS]` title prefix.
const OOS_BODY_HEADING: &str = "## Out-of-Scope Observation";
/// How many characters of a diagnostic survive into a contract row.
const ERROR_CHARS: usize = 500;
/// The sentinel is a run receipt in a session directory, so it is owner only.
/// Python inherited the same mode from `NamedTemporaryFile`.
const SENTINEL_MODE: u32 = 0o600;

// ------------------------------------------------------------ issue create-one

/// File one GitHub issue and publish its identity rows.
///
/// Exits `0` after a create or a dry run, `1` for an unusable command line or
/// a missing body file, `3` when redaction cannot prove a secret is gone, `5`
/// when live-mutation authorization refuses the create, and `2` for every
/// other refusal.
pub fn create_one(arguments: &[OsString]) -> ExitCode {
    let request = match parse_create_arguments(arguments) {
        Ok(request) => request,
        Err(message) => {
            eprintln!("{message}");
            return ExitCode::from(1);
        }
    };
    match plan_create(&request) {
        Err(failure) => failure.report(),
        Ok(CreatePlan::DryRun { title, labels }) => {
            emit_kv("DRY_RUN", "true");
            emit_kv("DRY_RUN_TITLE", &title);
            emit_kv("ISSUE_TITLE", &title);
            if !labels.is_empty() {
                emit_kv("DRY_RUN_LABELS", &labels.join(","));
            }
            ExitCode::SUCCESS
        }
        Ok(CreatePlan::Live(create)) => match file_issue(&create) {
            Err(failure) => failure.report(),
            Ok(created) => {
                emit_kv("ISSUE_NUMBER", &created.number.to_string());
                emit_kv("ISSUE_URL", &created.url);
                emit_kv("ISSUE_ID", &created.id.to_string());
                emit_kv("ISSUE_TITLE", &create.title);
                ExitCode::SUCCESS
            }
        },
    }
}

/// One usable `create-one` command line.
#[derive(Debug, Default, Eq, PartialEq)]
struct CreateArguments {
    title: String,
    title_prefix: String,
    labels: Vec<String>,
    body_file: String,
    repo: String,
    context_file: String,
    run_id: String,
    trusted_root: String,
    dry_run: bool,
    operator_invoked: bool,
}

/// What `create-one` decided to do once its inputs were resolved.
#[derive(Debug)]
enum CreatePlan {
    DryRun { title: String, labels: Vec<String> },
    Live(LiveCreate),
}

/// Everything the live path needs after authorization and repo resolution.
#[derive(Debug)]
struct LiveCreate {
    repository: GitHubRepositoryRef,
    repo: String,
    title: String,
    body: String,
    labels: Vec<String>,
    context_file: String,
    run_id: String,
    trusted_root: String,
    operator_invoked: bool,
}

/// One refused create, as the rows and exit code it publishes.
#[derive(Debug, Eq, PartialEq)]
struct CreateFailure {
    error: String,
    code: u8,
}

impl CreateFailure {
    /// Build a refusal, collapsing and redacting its diagnostic first.
    fn new(message: &str, code: u8) -> Self {
        Self {
            error: flat_error(message, ERROR_CHARS),
            code,
        }
    }

    fn report(self) -> ExitCode {
        if self.code == EXIT_MUTATION_REFUSED {
            emit_kv(MUTATION_REFUSAL_STATUS, "true");
        }
        emit_kv("ISSUE_FAILED", "true");
        emit_kv("ISSUE_ERROR", &self.error);
        ExitCode::from(self.code)
    }
}

/// Scan the `create-one` option pairs and flags.
///
/// A value-taking option that ends the line is its own refusal, and both it
/// and an unknown option print one stderr line and exit `1` with no rows.
fn parse_create_arguments(arguments: &[OsString]) -> Result<CreateArguments, String> {
    let mut parsed = CreateArguments::default();
    let mut index = 0;
    while index < arguments.len() {
        let token = arguments[index].to_string_lossy().into_owned();
        match token.as_str() {
            "--dry-run" => {
                parsed.dry_run = true;
                index += 1;
                continue;
            }
            "--operator-invoked" => {
                parsed.operator_invoked = true;
                index += 1;
                continue;
            }
            _ => {}
        }
        let target: &mut String = match token.as_str() {
            "--title" => &mut parsed.title,
            "--title-prefix" => &mut parsed.title_prefix,
            // Both spellings name the same file: `--body` never carried inline
            // text, and `/issue` passes a path through either.
            "--body" | "--body-file" => &mut parsed.body_file,
            "--repo" => &mut parsed.repo,
            "--context-file" => &mut parsed.context_file,
            "--run-id" => &mut parsed.run_id,
            "--trusted-root" => &mut parsed.trusted_root,
            "--label" => {
                let Some(value) = arguments.get(index + 1) else {
                    return Err(format!("{token} requires a value"));
                };
                parsed.labels.push(value.to_string_lossy().into_owned());
                index += 2;
                continue;
            }
            other => return Err(format!("Unknown option: {other}")),
        };
        let Some(value) = arguments.get(index + 1) else {
            return Err(format!("{token} requires a value"));
        };
        *target = value.to_string_lossy().into_owned();
        index += 2;
    }
    Ok(parsed)
}

/// Resolve the title, body, authorization, repository, and labels.
///
/// A dry run stops before the body is read, before authorization, and before
/// any GitHub contact, so it neither reads a file the caller named nor needs a
/// repository to succeed.
fn plan_create(arguments: &CreateArguments) -> Result<CreatePlan, CreateFailure> {
    if arguments.title.is_empty() {
        return Err(CreateFailure::new("--title is required", 1));
    }
    let title = redact_issue_text_outbound(&arguments.title)
        .map_err(|error| CreateFailure::new(&format!("redaction:{}", error.reason()), 3))?;
    let mut final_title = normalize_title_prefix(&title, &arguments.title_prefix);
    if arguments.dry_run {
        return Ok(CreatePlan::DryRun {
            title: final_title,
            labels: arguments.labels.clone(),
        });
    }
    let body = read_body(&arguments.body_file)?;
    // A caller that files an OOS body without naming a prefix still gets one,
    // so the `[OOS]` identity every consumer filters on cannot be forgotten.
    if arguments.title_prefix.is_empty() && is_oos_issue_body(&body) {
        final_title = normalize_title_prefix(&title, "[OOS]");
    }
    let authorization = authorization_request(
        &arguments.context_file,
        &arguments.run_id,
        &arguments.trusted_root,
        arguments.operator_invoked,
    );
    if let Err(reason) = authorized(&authorization) {
        return Err(CreateFailure::new(
            &format!("{MUTATION_REFUSAL_REASON}:{reason}"),
            EXIT_MUTATION_REFUSED,
        ));
    }
    let Some(repo) = resolve_repo_for((!arguments.repo.is_empty()).then_some(&arguments.repo))
    else {
        return Err(CreateFailure::new("could not determine repo", 2));
    };
    let Ok(repository) = repository_ref(&repo) else {
        return Err(CreateFailure::new(
            &format!("repository slug is invalid: {repo}"),
            2,
        ));
    };
    Ok(CreatePlan::Live(LiveCreate {
        repository,
        repo,
        title: final_title,
        body,
        labels: arguments.labels.clone(),
        context_file: arguments.context_file.clone(),
        run_id: arguments.run_id.clone(),
        trusted_root: arguments.trusted_root.clone(),
        operator_invoked: arguments.operator_invoked,
    }))
}

/// Read and redact the body file, treating an absent path as an empty body.
fn read_body(body_file: &str) -> Result<String, CreateFailure> {
    if body_file.is_empty() {
        return Ok(String::new());
    }
    let path = Path::new(body_file);
    if !path.is_file() {
        return Err(CreateFailure::new(
            &format!("body file not found: {body_file}"),
            1,
        ));
    }
    // Python read the body as strict UTF-8 and raised on anything else; an
    // unreadable body is reported here as the refusal it always was.
    let contents = fs::read_to_string(path)
        .map_err(|error| CreateFailure::new(&format!("body file is unreadable: {error}"), 1))?;
    redact_issue_text_outbound(&contents)
        .map_err(|error| CreateFailure::new(&format!("redaction:{}", error.reason()), 3))
}

/// Return whether a body is the OOS template rather than free prose.
fn is_oos_issue_body(body: &str) -> bool {
    body == OOS_BODY_HEADING || body.starts_with(&format!("{OOS_BODY_HEADING}\n"))
}

/// Keep only the labels the repository actually defines, warning about the rest.
///
/// A label the repository does not carry is dropped rather than failing the
/// create, exactly as the per-label `gh label list` probe behaved. One listing
/// answers every requested label where Python probed each one separately, and
/// a failed listing drops them all the same way, because an unproven label is
/// one GitHub would reject.
async fn existing_labels(
    service: &impl GitHubService,
    cancellation: &Cancellation,
    create: &LiveCreate,
) -> Vec<String> {
    if create.labels.is_empty() {
        return Vec::new();
    }
    let known: Vec<String> = service
        .list_labels(&create.repository, cancellation)
        .await
        .map(|labels| labels.into_iter().map(|label| label.name).collect())
        .unwrap_or_default();
    create
        .labels
        .iter()
        .filter(|label| {
            let present = known.iter().any(|name| name == *label);
            if !present {
                eprintln!(
                    "WARN: label '{label}' does not exist in {}, skipping",
                    create.repo
                );
            }
            present
        })
        .cloned()
        .collect()
}

/// Run the authorized create and close the orphan an unusable echo left.
///
/// The label probe, the create, and any rollback share one client, so a single
/// credential acquisition covers the whole filing.
fn file_issue(create: &LiveCreate) -> Result<CreatedIssue, CreateFailure> {
    let authorization = authorization_request(
        &create.context_file,
        &create.run_id,
        &create.trusted_root,
        create.operator_invoked,
    );
    let outcome = with_github_service(async |service, cancellation| {
        let request = IssueCreateRequest {
            repository: create.repository.clone(),
            title: create.title.clone(),
            body: create.body.clone(),
            labels: existing_labels(service, cancellation, create).await,
        };
        Ok(create_with_rollback(service, cancellation, &authorization, &request).await)
    });
    match outcome {
        Err(ServiceFailure::Setup(detail) | ServiceFailure::Operation(detail)) => {
            Err(CreateFailure::new(&detail, 2))
        }
        Ok(Ok(created)) => Ok(created),
        Ok(Err((failure, rollback))) => Err(create_refusal(&create.repo, &failure, rollback)),
    }
}

/// Shape one create refusal, reporting the orphan close it attempted.
fn create_refusal(
    repo: &str,
    failure: &IssueCreateFailure,
    rollback: Option<(u64, Result<(), String>)>,
) -> CreateFailure {
    match rollback {
        None => {}
        Some((orphan, Ok(()))) => {
            eprintln!("ROLLBACK: closed orphan issue #{orphan} after an unusable create response");
        }
        Some((orphan, Err(detail))) => {
            eprintln!(
                "ROLLBACK_FAILED: could not close orphan issue #{orphan} in {repo}: {}. Manually close.",
                flat_error(&detail, ERROR_CHARS)
            );
        }
    }
    let code = if failure.error.reason() == MUTATION_REFUSAL_REASON {
        EXIT_MUTATION_REFUSED
    } else if failure.error.reason() == "redaction-failed" {
        3
    } else {
        2
    };
    let message = if code == EXIT_MUTATION_REFUSED {
        format!("{MUTATION_REFUSAL_REASON}:{MUTATION_REFUSAL_REASON}")
    } else if code == 3 {
        format!("redaction:{}", failure.error.reason())
    } else {
        failure.message()
    };
    CreateFailure::new(&message, code)
}

/// One in-process create, as its caller composes it.
///
/// `create-one` is a command line; this is the same filing for a caller that
/// already holds the request. Both go through [`plan_create`] and
/// [`file_issue`], so redaction, the label probe, the live-mutation gate, and
/// the orphan rollback are the same code on both paths.
pub struct CreateSpec<'a> {
    pub title: &'a str,
    pub title_prefix: &'a str,
    pub body_file: &'a Path,
    pub labels: &'a [String],
    pub repo: &'a str,
    pub context_file: &'a str,
    pub run_id: &'a str,
    pub trusted_root: &'a str,
}

/// File one issue in process and report its identity or a flat refusal.
pub fn create_issue(spec: &CreateSpec<'_>) -> Result<CreatedIssue, String> {
    let arguments = CreateArguments {
        title: spec.title.to_owned(),
        title_prefix: spec.title_prefix.to_owned(),
        labels: spec.labels.to_vec(),
        body_file: spec.body_file.to_string_lossy().into_owned(),
        repo: spec.repo.to_owned(),
        context_file: spec.context_file.to_owned(),
        run_id: spec.run_id.to_owned(),
        trusted_root: spec.trusted_root.to_owned(),
        dry_run: false,
        operator_invoked: false,
    };
    match plan_create(&arguments).map_err(|failure| failure.error)? {
        CreatePlan::DryRun { .. } => Err("create refused: unexpected dry run".to_owned()),
        CreatePlan::Live(create) => file_issue(&create).map_err(|failure| failure.error),
    }
}

// -------------------------------------------------------- issue write-sentinel

/// Record that one `/issue` run reached its end, atomically.
///
/// Exits `1` for an unusable command line and `0` otherwise, whether or not a
/// sentinel was written: a dry run and a run with failures are both successful
/// non-writes, reported as `WROTE=false REASON=<reason>` on stderr.
pub fn write_sentinel(arguments: &[OsString]) -> ExitCode {
    let request = match parse_sentinel_arguments(arguments) {
        Ok(request) => request,
        Err(message) => return sentinel_error(&message),
    };
    if request.dry_run {
        eprintln!("WROTE=false REASON=dry_run");
        return ExitCode::SUCCESS;
    }
    if request.failed > 0 {
        eprintln!("WROTE=false REASON=failures");
        return ExitCode::SUCCESS;
    }
    let document = format!(
        "ISSUE_SENTINEL_VERSION=1\nISSUES_CREATED={}\nISSUES_DEDUPLICATED={}\nISSUES_FAILED={}\nTIMESTAMP={}\n",
        request.created,
        request.deduplicated,
        request.failed,
        Utc::now().format("%Y-%m-%dT%H:%M:%SZ")
    );
    if let Err(detail) = publish_sentinel(&request.path, &document) {
        return sentinel_error(&detail);
    }
    eprintln!("WROTE=true");
    ExitCode::SUCCESS
}

/// Publish one sentinel refusal on stderr, where every status row of this verb
/// goes so the `ISSUES_*` stdout grammar stays parseable.
///
/// The value is stripped of C0 controls and DEL, mirroring the sanitizing the
/// Python emitter applied, so a hostile `--path` cannot forge a second row.
fn sentinel_error(message: &str) -> ExitCode {
    eprintln!("ERROR={}", sanitized_line(message));
    ExitCode::from(1)
}

/// One usable `write-sentinel` command line.
#[derive(Debug, Eq, PartialEq)]
struct SentinelRequest {
    path: PathBuf,
    created: u64,
    deduplicated: u64,
    failed: u64,
    dry_run: bool,
}

/// Scan the four option pairs and the dry-run flag.
///
/// An option whose value is absent or empty is refused before any of the
/// value checks, so an empty counter never reads as zero.
fn parse_sentinel_arguments(arguments: &[OsString]) -> Result<SentinelRequest, String> {
    let mut path = String::new();
    let mut created = String::new();
    let mut deduplicated = String::new();
    let mut failed = String::new();
    let mut dry_run = false;
    let mut index = 0;
    while index < arguments.len() {
        let token = arguments[index].to_string_lossy().into_owned();
        if token == "--dry-run" {
            dry_run = true;
            index += 1;
            continue;
        }
        let target: &mut String = match token.as_str() {
            "--path" => &mut path,
            "--issues-created" => &mut created,
            "--issues-deduplicated" => &mut deduplicated,
            "--issues-failed" => &mut failed,
            other => return Err(format!("Unknown argument: {other}")),
        };
        match arguments.get(index + 1) {
            Some(value) if !value.is_empty() => {
                *target = value.to_string_lossy().into_owned();
            }
            _ => return Err(format!("Missing value for {token}")),
        }
        index += 2;
    }
    if path.is_empty() {
        return Err("Missing required argument: --path".to_owned());
    }
    if created.is_empty() || deduplicated.is_empty() || failed.is_empty() {
        return Err(
            "Missing required arguments: --issues-created, --issues-deduplicated, --issues-failed"
                .to_owned(),
        );
    }
    let target = PathBuf::from(&path);
    if !target.is_absolute() {
        return Err(format!("--path must be absolute: {path}"));
    }
    if target
        .components()
        .any(|component| component == std::path::Component::ParentDir)
    {
        return Err(format!("--path must not contain '..': {path}"));
    }
    // Python accepted any `str.isdigit()` spelling, including non-ASCII digits
    // and magnitudes no counter can reach. Only ASCII decimals that fit a
    // 64-bit unsigned integer are accepted here, through the same refusal.
    let (Some(created), Some(deduplicated), Some(failed)) = (
        unsigned_integer(&created),
        unsigned_integer(&deduplicated),
        unsigned_integer(&failed),
    ) else {
        return Err("Counter values must be non-negative integers".to_owned());
    };
    Ok(SentinelRequest {
        path: target,
        created,
        deduplicated,
        failed,
        dry_run,
    })
}

/// Publish the sentinel below a confined, non-symlinked parent directory.
fn publish_sentinel(target: &Path, document: &str) -> Result<(), String> {
    let absolute = absolute_path(target)
        .map_err(|error| format!("cannot resolve {}: {error}", target.display()))?;
    let (Some(parent), Some(name)) = (absolute.parent(), absolute.file_name()) else {
        return Err(format!(
            "{} is not a usable sentinel path",
            target.display()
        ));
    };
    let refusal =
        |error: &dyn std::fmt::Display| format!("cannot write {}: {error}", target.display());
    ensure_directory_chain(parent).map_err(|error| refusal(&error))?;
    let root = TemporaryRoot::resolve(Some(parent)).map_err(|error| refusal(&error))?;
    let confined = root
        .confine(name, PathIntent::Write)
        .map_err(|error| refusal(&error))?;
    atomic_write_utf8(&confined, document, SENTINEL_MODE).map_err(|error| refusal(&error))
}

// -------------------------------------------------------- issue cleanup-failed

/// Close one orphaned issue as not planned, best effort.
///
/// Always exits `0`: the caller has already counted the failure that produced
/// the orphan, and a failed cleanup is reported as `CLOSED=false` with the
/// reason rather than as a second failure to handle.
pub fn cleanup_failed(arguments: &[OsString]) -> ExitCode {
    let (issue, repo) = match parse_cleanup_arguments(arguments) {
        Ok(parsed) => parsed,
        Err((issue, message)) => {
            eprintln!("Unknown option: {message}");
            return emit_cleanup(&issue, false, &format!("unknown option: {message}"));
        }
    };
    let Some(number) = unsigned_integer(&issue) else {
        return emit_cleanup(&issue, false, "invalid or missing --issue-number");
    };
    let Some(repo) = resolve_repo_for((!repo.is_empty()).then_some(&repo)) else {
        return emit_cleanup(&issue, false, "could not determine repo");
    };
    let Ok(repository) = repository_ref(&repo) else {
        return emit_cleanup(&issue, false, "repository slug is invalid");
    };
    let closed = with_github_service(async |service, cancellation| {
        IssueMutationOwner::new(service)
            .close_not_planned(cancellation, &repository, number)
            .await
    });
    match closed {
        Ok(()) => emit_cleanup(&issue, true, ""),
        Err(ServiceFailure::Setup(detail) | ServiceFailure::Operation(detail)) => {
            emit_cleanup(&issue, false, &detail)
        }
    }
}

/// Scan the two option pairs, reporting the first unusable token.
///
/// The issue number scanned so far travels with the refusal so the `ISSUE`
/// row still names the subject when a later token is unusable.
fn parse_cleanup_arguments(arguments: &[OsString]) -> Result<(String, String), (String, String)> {
    let mut issue = String::new();
    let mut repo = String::new();
    let mut index = 0;
    while index < arguments.len() {
        let token = arguments[index].to_string_lossy().into_owned();
        let target: &mut String = match token.as_str() {
            "--issue-number" => &mut issue,
            "--repo" => &mut repo,
            _ => {
                return Err((
                    if issue.is_empty() {
                        "unknown".to_owned()
                    } else {
                        issue
                    },
                    token,
                ));
            }
        };
        let Some(value) = arguments.get(index + 1) else {
            // A value-taking option that ends the line reads as unknown, which
            // is how the legacy scanner reported it.
            return Err((
                if issue.is_empty() {
                    "unknown".to_owned()
                } else {
                    issue
                },
                token,
            ));
        };
        *target = value.to_string_lossy().into_owned();
        index += 2;
    }
    Ok((issue, repo))
}

/// Publish the cleanup envelope every `/issue` failure path parses.
fn emit_cleanup(issue: &str, closed: bool, error: &str) -> ExitCode {
    emit_kv("CLOSED", if closed { "true" } else { "false" });
    emit_kv("ISSUE", &flat_error(issue, ERROR_CHARS));
    if !error.is_empty() {
        emit_kv("ERROR", &flat_error(error, ERROR_CHARS));
    }
    ExitCode::SUCCESS
}

#[cfg(test)]
mod tests {
    use super::{
        CreateArguments, CreateFailure, SentinelRequest, is_oos_issue_body,
        parse_cleanup_arguments, parse_create_arguments, parse_sentinel_arguments,
        publish_sentinel, read_body,
    };
    use larch_core::normalize_title_prefix;
    use std::{ffi::OsString, fs, os::unix::fs::PermissionsExt as _, path::PathBuf};

    fn arguments(values: &[&str]) -> Vec<OsString> {
        values.iter().map(OsString::from).collect()
    }

    #[test]
    fn the_create_scanner_collects_repeated_labels_and_both_body_spellings() {
        let parsed = parse_create_arguments(&arguments(&[
            "--title",
            "Fix",
            "--title-prefix",
            "[OOS]",
            "--label",
            "one",
            "--label",
            "two",
            "--body",
            "/tmp/a",
            "--repo",
            "o/r",
            "--dry-run",
            "--operator-invoked",
        ]))
        .expect("a usable line");
        assert_eq!(
            parsed,
            CreateArguments {
                title: "Fix".to_owned(),
                title_prefix: "[OOS]".to_owned(),
                labels: vec!["one".to_owned(), "two".to_owned()],
                body_file: "/tmp/a".to_owned(),
                repo: "o/r".to_owned(),
                dry_run: true,
                operator_invoked: true,
                ..CreateArguments::default()
            }
        );
        // `--body-file` overwrites `--body`: both name the same field.
        let parsed = parse_create_arguments(&arguments(&[
            "--body",
            "/tmp/a",
            "--body-file",
            "/tmp/b",
            "--title",
            "T",
        ]))
        .expect("a usable line");
        assert_eq!(parsed.body_file, "/tmp/b");
        for (line, message) in [
            (&["--bogus", "x"][..], "Unknown option: --bogus"),
            (&["--title"][..], "--title requires a value"),
            (&["--label"][..], "--label requires a value"),
            (&["Fix"][..], "Unknown option: Fix"),
        ] {
            assert_eq!(
                parse_create_arguments(&arguments(line)).expect_err("a refusal"),
                message,
                "{line:?}"
            );
        }
    }

    #[test]
    fn a_missing_title_and_a_missing_body_file_carry_their_own_exit_codes() {
        assert_eq!(
            super::plan_create(&CreateArguments::default()).expect_err("no title"),
            CreateFailure {
                error: "--title is required".to_owned(),
                code: 1,
            }
        );
        let refusal = read_body("/nonexistent/body.md").expect_err("a missing body file");
        assert_eq!(refusal.code, 1);
        assert!(
            refusal.error.starts_with("body file not found: "),
            "{}",
            refusal.error
        );
        // An absent `--body-file` is an empty body, not a refusal.
        assert_eq!(read_body("").expect("no body file"), String::new());
    }

    #[test]
    fn a_dry_run_reports_the_prefixed_title_without_reading_the_body() {
        let plan = super::plan_create(&CreateArguments {
            title: "[oos] already tagged".to_owned(),
            title_prefix: "[OOS]".to_owned(),
            labels: vec!["one".to_owned()],
            body_file: "/nonexistent/body.md".to_owned(),
            dry_run: true,
            ..CreateArguments::default()
        })
        .expect("a dry run needs neither body nor authorization");
        match plan {
            super::CreatePlan::DryRun { title, labels } => {
                assert_eq!(title, "[OOS] already tagged");
                assert_eq!(labels, vec!["one".to_owned()]);
            }
            super::CreatePlan::Live { .. } => panic!("dry run must not reach the live path"),
        }
    }

    #[test]
    fn a_secret_in_a_title_is_redacted_before_it_can_be_filed() {
        let plan = super::plan_create(&CreateArguments {
            title: "leak ghp_abcdefghijklmnopqrstuvwxyz0123456789".to_owned(),
            dry_run: true,
            ..CreateArguments::default()
        })
        .expect("a dry run");
        match plan {
            super::CreatePlan::DryRun { title, .. } => {
                assert_eq!(title, "leak <REDACTED-TOKEN>");
            }
            super::CreatePlan::Live { .. } => panic!("dry run must not reach the live path"),
        }
    }

    #[test]
    fn the_title_prefix_is_case_insensitive_and_idempotent() {
        assert_eq!(normalize_title_prefix("Fix it", "[OOS]"), "[OOS] Fix it");
        assert_eq!(
            normalize_title_prefix("[OOS] Fix it", "[OOS]"),
            "[OOS] Fix it"
        );
        assert_eq!(
            normalize_title_prefix("[oos]   Fix it", "[OOS]"),
            "[OOS] Fix it"
        );
        assert_eq!(normalize_title_prefix("Fix it", ""), "Fix it");
    }

    #[test]
    fn only_the_oos_template_heading_forces_the_oos_prefix() {
        assert!(is_oos_issue_body("## Out-of-Scope Observation"));
        assert!(is_oos_issue_body("## Out-of-Scope Observation\nbody\n"));
        assert!(!is_oos_issue_body("## Out-of-Scope Observations\n"));
        assert!(!is_oos_issue_body("intro\n## Out-of-Scope Observation\n"));
        assert!(!is_oos_issue_body(""));
    }

    #[test]
    fn the_sentinel_scanner_refuses_relative_escaping_and_non_numeric_lines() {
        assert_eq!(
            parse_sentinel_arguments(&arguments(&[
                "--path",
                "/tmp/s.sentinel",
                "--issues-created",
                "2",
                "--issues-deduplicated",
                "1",
                "--issues-failed",
                "0",
                "--dry-run",
            ]))
            .expect("a usable line"),
            SentinelRequest {
                path: PathBuf::from("/tmp/s.sentinel"),
                created: 2,
                deduplicated: 1,
                failed: 0,
                dry_run: true,
            }
        );
        for (line, message) in [
            (&["--bogus"][..], "Unknown argument: --bogus"),
            (&["--path"][..], "Missing value for --path"),
            (&["--path", ""][..], "Missing value for --path"),
            (&[][..], "Missing required argument: --path"),
            (
                &["--path", "/tmp/s"][..],
                "Missing required arguments: --issues-created, --issues-deduplicated, --issues-failed",
            ),
            (
                &[
                    "--path",
                    "s",
                    "--issues-created",
                    "0",
                    "--issues-deduplicated",
                    "0",
                    "--issues-failed",
                    "0",
                ][..],
                "--path must be absolute: s",
            ),
            (
                &[
                    "--path",
                    "/tmp/../s",
                    "--issues-created",
                    "0",
                    "--issues-deduplicated",
                    "0",
                    "--issues-failed",
                    "0",
                ][..],
                "--path must not contain '..': /tmp/../s",
            ),
            (
                &[
                    "--path",
                    "/tmp/s",
                    "--issues-created",
                    "x",
                    "--issues-deduplicated",
                    "0",
                    "--issues-failed",
                    "0",
                ][..],
                "Counter values must be non-negative integers",
            ),
        ] {
            assert_eq!(
                parse_sentinel_arguments(&arguments(line)).expect_err("a refusal"),
                message,
                "{line:?}"
            );
        }
    }

    #[test]
    fn the_sentinel_is_published_atomically_and_owner_only() {
        let sandbox = tempfile::tempdir().expect("temporary directory");
        // A missing nested parent exercises the directory-chain creation the
        // legacy `mkdir(parents=True, exist_ok=True)` performed.
        let target = sandbox.path().join("run").join("issue.sentinel");
        publish_sentinel(&target, "ISSUE_SENTINEL_VERSION=1\n").expect("publication succeeds");

        assert_eq!(
            fs::read_to_string(&target).expect("sentinel"),
            "ISSUE_SENTINEL_VERSION=1\n"
        );
        assert_eq!(
            fs::metadata(&target)
                .expect("metadata")
                .permissions()
                .mode()
                & 0o777,
            0o600
        );

        let real = sandbox.path().join("real");
        fs::create_dir(&real).expect("real directory");
        let linked = sandbox.path().join("linked");
        std::os::unix::fs::symlink(&real, &linked).expect("symlink");
        let refusal = publish_sentinel(&linked.join("issue.sentinel"), "x\n")
            .expect_err("a symlinked parent must be refused");
        assert!(refusal.starts_with("cannot write "), "{refusal}");
        assert!(!real.join("issue.sentinel").exists());
    }

    #[test]
    fn the_cleanup_scanner_keeps_the_issue_it_already_read() {
        assert_eq!(
            parse_cleanup_arguments(&arguments(&["--issue-number", "42", "--repo", "o/r"]))
                .expect("a usable line"),
            ("42".to_owned(), "o/r".to_owned())
        );
        assert_eq!(
            parse_cleanup_arguments(&arguments(&[])).expect("an empty line"),
            (String::new(), String::new())
        );
        assert_eq!(
            parse_cleanup_arguments(&arguments(&["--bogus"])).expect_err("a refusal"),
            ("unknown".to_owned(), "--bogus".to_owned())
        );
        // The issue read before the unusable token still names the subject.
        assert_eq!(
            parse_cleanup_arguments(&arguments(&["--issue-number", "42", "--bogus"]))
                .expect_err("a refusal"),
            ("42".to_owned(), "--bogus".to_owned())
        );
        // A value-taking option that ends the line reads as unknown.
        assert_eq!(
            parse_cleanup_arguments(&arguments(&["--repo"])).expect_err("a refusal"),
            ("unknown".to_owned(), "--repo".to_owned())
        );
    }
}
