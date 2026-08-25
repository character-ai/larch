//! Cross-repository stall-report filing through typed GitHub operations.

use crate::{
    github_repository_resolution::repository_ref,
    github_service::{ServiceFailure, with_github_service},
    issue_mutation_support::{authorization_request, authorized, create_with_rollback},
};
use larch_adapters::{
    github::{IssueMutationOwner, OctocrabGitHubService},
    runtime::Cancellation,
    stall_recovery::{snapshot_public_file_contents, validate_public_snapshot_contents},
};
use larch_core::{
    BUG_TITLE_PREFIX, GitHubIssueBodyMode, GitHubIssueList, GitHubIssueState, GitHubRepositoryRef,
    GitHubService, ISSUE_DEDUP_LIMIT, IssueCreateRequest, redact,
};
use regex::Regex;
use std::{
    env,
    fmt::Write as _,
    fs::{self, File},
    path::{Path, PathBuf},
    process::ExitCode,
    sync::LazyLock,
};

const USAGE: &str = "Usage: larch stall-recovery file-report --repo OWNER/REPO --body-file PATH --title TITLE [--mutation-context PATH --run-id ID --trusted-root PATH] [--dedup-only] [--create-on-lookup-failure] [--attempts-file PATH] [--escalation-ledger-file PATH] [--root-cause-file PATH] [--sensitive-corpus-file PATH] [--publication-tier tier-a|tier-b] [--dry-run]";

static REPOSITORY_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$").expect("fixed repository regex")
});
static MARKER_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"<!-- larch-stall:signature=([0-9a-f]{64}) -->").expect("fixed report marker regex")
});
static UNSAFE_COMMENT_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"(?m)<!-- larch-stall:signature=|^### \[(?:BUG|Bug)\] /(?:implement|design)|^## /(?:implement|design) .* report$|^## Report metadata$|^## Sanitized stall report$|^## Validated failure-detail log$|^## Run-log pointer$",
    )
    .expect("fixed Tier B comment regex")
});

/// Arguments retained from the former cross-repository Bash helper.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct FileReportArguments {
    pub repo: String,
    pub body_file: PathBuf,
    pub title: String,
    pub dedup_only: bool,
    pub create_on_lookup_failure: bool,
    pub attempts_file: Option<PathBuf>,
    pub escalation_file: Option<PathBuf>,
    pub root_cause_file: Option<PathBuf>,
    pub sensitive_corpus_file: Option<PathBuf>,
    pub publication_tier: String,
    pub dry_run: bool,
    pub mutation_context: PathBuf,
    pub run_id: String,
    pub trusted_root: PathBuf,
}

impl Default for FileReportArguments {
    fn default() -> Self {
        Self {
            repo: String::new(),
            body_file: PathBuf::new(),
            title: String::new(),
            dedup_only: false,
            create_on_lookup_failure: false,
            attempts_file: None,
            escalation_file: None,
            root_cause_file: None,
            sensitive_corpus_file: None,
            publication_tier: "tier-a".to_owned(),
            dry_run: false,
            mutation_context: PathBuf::new(),
            run_id: String::new(),
            trusted_root: PathBuf::new(),
        }
    }
}

/// One frozen `FILE_FAILURE_REPORT_*` result.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct FileReportOutcome {
    status: &'static str,
    url: String,
    fallback_reason: String,
}

impl FileReportOutcome {
    const fn status(status: &'static str) -> Self {
        Self {
            status,
            url: String::new(),
            fallback_reason: String::new(),
        }
    }

    fn fallback(reason: impl Into<String>) -> Self {
        Self {
            status: "fallback-print-required",
            url: String::new(),
            fallback_reason: reason.into(),
        }
    }

    fn fail_open(reason: &'static str) -> Self {
        Self {
            status: "lookup-failed-open",
            url: String::new(),
            fallback_reason: reason.to_owned(),
        }
    }

    fn mutation_refused(reason: &'static str) -> Self {
        Self {
            status: "mutation-refused",
            url: String::new(),
            fallback_reason: format!("unauthorized-mutation:{reason}"),
        }
    }

    const fn success(status: &'static str, url: String) -> Self {
        Self {
            status,
            url,
            fallback_reason: String::new(),
        }
    }

    /// Render the machine stdout grammar consumed by report normalization.
    #[must_use]
    pub fn render(&self) -> String {
        let mut output = format!("FILE_FAILURE_REPORT_STATUS={}\n", self.status);
        if !self.url.is_empty() {
            let _ = writeln!(output, "FILE_FAILURE_REPORT_URL={}", self.url);
        }
        if !self.fallback_reason.is_empty() {
            let _ = writeln!(
                output,
                "FILE_FAILURE_REPORT_FALLBACK_REASON={}",
                self.fallback_reason
            );
        }
        output
    }

    fn emit(&self) {
        print!("{}", self.render());
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum PublicationTier {
    A,
    B,
}

struct PreparedReport {
    repository: GitHubRepositoryRef,
    body_file: PathBuf,
    body_snapshot: String,
    marker: String,
    title: String,
    dedup_only: bool,
    create_on_lookup_failure: bool,
    attempts_file: Option<PathBuf>,
    escalation_file: Option<PathBuf>,
    root_cause_file: Option<PathBuf>,
    sensitive_corpus_file: Option<PathBuf>,
    publication_tier: PublicationTier,
    source_root: PathBuf,
    mutation_context: String,
    run_id: String,
    trusted_root: String,
    _stage: tempfile::TempDir,
}

enum Preparation {
    Ready(Box<PreparedReport>),
    Complete(FileReportOutcome),
}

/// Parse and run `stall-recovery file-report`.
pub fn run(arguments: &[String]) -> ExitCode {
    let parsed = match parse_arguments(arguments) {
        Ok(Some(arguments)) => arguments,
        Ok(None) => {
            println!("{USAGE}");
            return ExitCode::SUCCESS;
        }
        Err(message) => {
            eprintln!("stall-recovery file-report: {message}");
            eprintln!("{USAGE}");
            return ExitCode::from(2);
        }
    };
    execute(parsed).emit();
    ExitCode::SUCCESS
}

/// Execute one parsed file-report request and return its stable envelope.
#[must_use]
pub fn execute(arguments: FileReportArguments) -> FileReportOutcome {
    let prepared = match prepare(arguments) {
        Preparation::Ready(prepared) => prepared,
        Preparation::Complete(outcome) => return outcome,
    };
    execute_prepared(&prepared)
}

fn execute_prepared(prepared: &PreparedReport) -> FileReportOutcome {
    let result = with_github_service(async |service, cancellation| {
        Ok(run_live_report(prepared, service, cancellation).await)
    });
    match result {
        Ok(outcome) => outcome,
        Err(ServiceFailure::Setup(detail) | ServiceFailure::Operation(detail)) => {
            print_service_failure(&detail);
            if prepared.create_on_lookup_failure {
                FileReportOutcome::fallback("create-failed")
            } else {
                lookup_failure(prepared.dedup_only)
            }
        }
    }
}

fn prepare(mut arguments: FileReportArguments) -> Preparation {
    if !REPOSITORY_RE.is_match(&arguments.repo) {
        return Preparation::Complete(FileReportOutcome::fallback("invalid-repo"));
    }
    let publication_tier = match arguments.publication_tier.as_str() {
        "tier-a" => PublicationTier::A,
        "tier-b" => PublicationTier::B,
        _ => {
            return Preparation::Complete(FileReportOutcome::fallback("invalid-publication-tier"));
        }
    };
    if arguments.create_on_lookup_failure
        && (arguments.dedup_only || publication_tier != PublicationTier::A)
    {
        return Preparation::Complete(FileReportOutcome::fallback("invalid-lookup-failure-create"));
    }
    if let Err(reason) = validate_and_absolutize_inputs(&mut arguments) {
        return Preparation::Complete(FileReportOutcome::fallback(reason));
    }

    let mutation_context = arguments.mutation_context.to_string_lossy().into_owned();
    let trusted_root = arguments.trusted_root.to_string_lossy().into_owned();
    if !arguments.dry_run {
        let authorization =
            authorization_request(&mutation_context, &arguments.run_id, &trusted_root, false);
        if let Err(reason) = authorized(&authorization) {
            let reason = match reason {
                "test-denied" => "test-denied",
                _ if mutation_context.is_empty() => "no-context-file",
                _ if arguments.run_id.is_empty() => "missing-run-id",
                _ if trusted_root.is_empty() => "missing-trusted-root",
                _ => "invalid-context-file",
            };
            return Preparation::Complete(FileReportOutcome::mutation_refused(reason));
        }
    }

    let source_root = match snapshot_source_root(&arguments) {
        Ok(root) => root,
        Err(reason) => return Preparation::Complete(FileReportOutcome::fallback(reason)),
    };
    let stage = match private_stage() {
        Ok(stage) => stage,
        Err(reason) => return Preparation::Complete(FileReportOutcome::fallback(reason)),
    };

    let Some(body_snapshot) =
        snapshot_public_file_contents(&source_root, &arguments.body_file, None, "")
    else {
        return Preparation::Complete(FileReportOutcome::fallback("invalid-body-snapshot"));
    };
    let Some(marker) = MARKER_RE
        .captures(&body_snapshot)
        .and_then(|captures| captures.get(1))
        .map(|capture| capture.as_str().to_owned())
    else {
        return Preparation::Complete(if arguments.dedup_only {
            FileReportOutcome::fail_open("missing-marker")
        } else {
            FileReportOutcome::fallback("missing-marker")
        });
    };
    if !arguments.dedup_only && arguments.title.is_empty() {
        return Preparation::Complete(FileReportOutcome::fallback("missing-title"));
    }
    let title = if arguments.dedup_only {
        String::new()
    } else {
        let Some(title) = report_title(&body_snapshot, publication_tier) else {
            return Preparation::Complete(FileReportOutcome::fallback("invalid-body-title"));
        };
        title
    };
    if arguments.dry_run {
        return Preparation::Complete(FileReportOutcome::status("dry-run"));
    }
    let Ok(repository) = repository_ref(&arguments.repo) else {
        return Preparation::Complete(FileReportOutcome::fallback("invalid-repo"));
    };

    Preparation::Ready(Box::new(PreparedReport {
        repository,
        body_file: arguments.body_file,
        body_snapshot,
        marker,
        title,
        dedup_only: arguments.dedup_only,
        create_on_lookup_failure: arguments.create_on_lookup_failure,
        attempts_file: arguments.attempts_file,
        escalation_file: arguments.escalation_file,
        root_cause_file: arguments.root_cause_file,
        sensitive_corpus_file: arguments.sensitive_corpus_file,
        publication_tier,
        source_root,
        mutation_context,
        run_id: arguments.run_id,
        trusted_root,
        _stage: stage,
    }))
}

async fn run_live_report(
    prepared: &PreparedReport,
    service: &OctocrabGitHubService,
    cancellation: &Cancellation,
) -> FileReportOutcome {
    let listed = service
        .list_issues(
            &GitHubIssueList::for_dedup(
                prepared.repository.clone(),
                GitHubIssueState::Open,
                GitHubIssueBodyMode::Include,
                service.transport_policy(),
            ),
            cancellation,
        )
        .await;
    let listed = match listed {
        Ok(listed) => listed,
        Err(error) if prepared.create_on_lookup_failure => {
            print_service_failure(&error.to_string());
            return create_report(prepared, service, cancellation).await;
        }
        Err(error) => {
            print_service_failure(&error.to_string());
            return lookup_failure(prepared.dedup_only);
        }
    };
    if listed.raw_rows_scanned >= ISSUE_DEDUP_LIMIT {
        eprintln!(
            "WARN: stall-report dedup reached the 100-record recent-open cap; older issues, if any, were omitted"
        );
    }
    let marker = format!("<!-- larch-stall:signature={} -->", prepared.marker);
    if let Some(issue) = listed
        .issues
        .iter()
        .find(|issue| issue.body.contains(&marker))
    {
        return comment_on_duplicate(prepared, service, cancellation, issue.number).await;
    }
    if prepared.dedup_only {
        FileReportOutcome::status("no-match")
    } else {
        create_report(prepared, service, cancellation).await
    }
}

async fn comment_on_duplicate(
    prepared: &PreparedReport,
    service: &OctocrabGitHubService,
    cancellation: &Cancellation,
    issue: u64,
) -> FileReportOutcome {
    let attempts = match snapshot_optional(prepared.attempts_file.as_deref(), prepared) {
        Ok(snapshot) => snapshot,
        Err(reason) => return FileReportOutcome::fallback(reason),
    };
    let escalation = match snapshot_optional(prepared.escalation_file.as_deref(), prepared) {
        Ok(snapshot) => snapshot,
        Err(reason) => return FileReportOutcome::fallback(reason),
    };
    let root_cause = match snapshot_optional(prepared.root_cause_file.as_deref(), prepared) {
        Ok(snapshot) => snapshot,
        Err(reason) => return FileReportOutcome::fallback(reason),
    };
    let comment = assemble_comment(
        attempts.as_deref(),
        escalation.as_deref(),
        root_cause.as_deref(),
    );
    let corpus =
        (prepared.publication_tier == PublicationTier::B).then(|| sensitive_corpus_path(prepared));
    let prefix = tier_b_artifact_prefix(prepared, corpus.as_deref());
    let Some(comment) = validate_public_snapshot_contents(
        &prepared.source_root,
        &comment,
        corpus.as_deref(),
        prefix,
    ) else {
        return FileReportOutcome::fallback(if prepared.publication_tier == PublicationTier::B {
            "unsafe-tier-b-comment"
        } else {
            "invalid-tier-a-comment"
        });
    };
    if prepared.publication_tier == PublicationTier::B && UNSAFE_COMMENT_RE.is_match(&comment) {
        return FileReportOutcome::fallback("unsafe-tier-b-comment");
    }
    let authorization = authorization_request(
        &prepared.mutation_context,
        &prepared.run_id,
        &prepared.trusted_root,
        false,
    );
    match IssueMutationOwner::new(service)
        .create_comment(
            cancellation,
            &authorization,
            &prepared.repository,
            issue,
            &comment,
        )
        .await
    {
        Ok(comment) => FileReportOutcome::success("dedup-comment", comment.url),
        Err(error) if error.reason() == "unauthorized-mutation" => {
            FileReportOutcome::mutation_refused("invalid-context-file")
        }
        Err(error) if error.reason() == "invalid-read-back" => {
            FileReportOutcome::fallback("comment-url-missing")
        }
        Err(error) => {
            print_service_failure(error.reason());
            FileReportOutcome::fallback("comment-failed")
        }
    }
}

async fn create_report(
    prepared: &PreparedReport,
    service: &OctocrabGitHubService,
    cancellation: &Cancellation,
) -> FileReportOutcome {
    let body = if prepared.publication_tier == PublicationTier::B {
        let corpus = sensitive_corpus_path(prepared);
        let prefix = tier_b_artifact_prefix(prepared, Some(&corpus));
        let Some(body) = validate_public_snapshot_contents(
            &prepared.source_root,
            &prepared.body_snapshot,
            Some(&corpus),
            prefix,
        ) else {
            return FileReportOutcome::fallback("unsafe-tier-b-body");
        };
        body
    } else {
        prepared.body_snapshot.clone()
    };
    let authorization = authorization_request(
        &prepared.mutation_context,
        &prepared.run_id,
        &prepared.trusted_root,
        false,
    );
    let request = IssueCreateRequest {
        repository: prepared.repository.clone(),
        title: prepared.title.clone(),
        body,
        assign_authenticated_user: false,
        labels: Vec::new(),
    };
    match create_with_rollback(service, cancellation, &authorization, &request).await {
        Ok(created) => FileReportOutcome::success("filed", created.url),
        Err((failure, _rollback)) if failure.error.reason() == "unauthorized-mutation" => {
            FileReportOutcome::mutation_refused("invalid-context-file")
        }
        Err((failure, _rollback))
            if failure.error.reason() == "invalid-read-back" && failure.orphan.is_none() =>
        {
            FileReportOutcome::fallback("create-url-missing")
        }
        Err((failure, _rollback)) => {
            print_service_failure(&failure.message());
            FileReportOutcome::fallback("create-failed")
        }
    }
}

fn snapshot_optional(
    path: Option<&Path>,
    prepared: &PreparedReport,
) -> Result<Option<String>, &'static str> {
    let Some(path) = path else {
        return Ok(None);
    };
    snapshot_public_file_contents(&prepared.source_root, path, None, "")
        .map(Some)
        .ok_or_else(|| optional_snapshot_reason(path, prepared))
}

fn optional_snapshot_reason(path: &Path, prepared: &PreparedReport) -> &'static str {
    if prepared.attempts_file.as_deref() == Some(path) {
        "invalid-attempts-file"
    } else if prepared.escalation_file.as_deref() == Some(path) {
        "invalid-escalation-ledger-file"
    } else {
        "invalid-root-cause-file"
    }
}

fn assemble_comment(
    attempts: Option<&str>,
    escalation: Option<&str>,
    root_cause: Option<&str>,
) -> String {
    let mut output = "+1 occurrence\n\n".to_owned();
    append_slice(&mut output, "Attempts", attempts);
    append_slice(&mut output, "Escalation evidence", escalation);
    append_slice(&mut output, "Root-cause finding", root_cause);
    output
}

fn append_slice(output: &mut String, title: &str, contents: Option<&str>) {
    let _ = writeln!(output, "## {title}\n");
    if let Some(contents) = contents.filter(|contents| !contents.is_empty()) {
        output.push_str(contents);
        output.push('\n');
    } else {
        let _ = writeln!(output, "_No {title} supplied for this occurrence._");
    }
    output.push('\n');
}

fn sensitive_corpus_path(prepared: &PreparedReport) -> PathBuf {
    prepared.sensitive_corpus_file.clone().unwrap_or_else(|| {
        prepared
            .body_file
            .parent()
            .unwrap_or(&prepared.source_root)
            .join(
                if prepared
                    .body_file
                    .file_name()
                    .and_then(|name| name.to_str())
                    .is_some_and(|name| name.starts_with("design-failure-"))
                {
                    "design-failure-sensitive-corpus.env"
                } else {
                    "stall-recovery-sensitive-corpus.env"
                },
            )
    })
}

fn tier_b_artifact_prefix(prepared: &PreparedReport, corpus: Option<&Path>) -> &'static str {
    let design_corpus = corpus
        .and_then(Path::file_name)
        .and_then(|name| name.to_str())
        .is_some_and(|name| name.starts_with("design-failure-"));
    let design_body = prepared
        .body_file
        .file_name()
        .and_then(|name| name.to_str())
        .is_some_and(|name| name.starts_with("design-failure-"));
    if design_corpus || design_body {
        "design-failure"
    } else {
        ""
    }
}

fn report_title(body: &str, publication_tier: PublicationTier) -> Option<String> {
    let mut title = body.split('\n').next()?.strip_prefix("### ")?.to_owned();
    if publication_tier == PublicationTier::A {
        let canonical_prefix = format!("{BUG_TITLE_PREFIX} ");
        let legacy_prefix = format!("{} ", BUG_TITLE_PREFIX.replacen("BUG", "Bug", 1));
        if let Some(prefix) = [canonical_prefix, legacy_prefix]
            .iter()
            .find(|prefix| title.starts_with(prefix.as_str()))
        {
            title.replace_range(..prefix.len(), "");
        }
    }
    (!title.is_empty()).then_some(title)
}

fn input_paths(arguments: &FileReportArguments) -> Vec<(&Path, &'static str)> {
    let mut paths = vec![(arguments.body_file.as_path(), "invalid-body-file")];
    for (path, reason) in [
        (&arguments.attempts_file, "invalid-attempts-file"),
        (&arguments.escalation_file, "invalid-escalation-ledger-file"),
        (&arguments.root_cause_file, "invalid-root-cause-file"),
        (
            &arguments.sensitive_corpus_file,
            "invalid-sensitive-corpus-file",
        ),
    ] {
        if let Some(path) = path {
            paths.push((path.as_path(), reason));
        }
    }
    paths
}

fn validate_and_absolutize_inputs(arguments: &mut FileReportArguments) -> Result<(), &'static str> {
    for (path, reason) in input_paths(arguments) {
        if !read_file_is_valid(path) {
            return Err(reason);
        }
    }
    arguments.body_file = absolute_path(&arguments.body_file).ok_or("invalid-body-file")?;
    for (path, reason) in [
        (&mut arguments.attempts_file, "invalid-attempts-file"),
        (
            &mut arguments.escalation_file,
            "invalid-escalation-ledger-file",
        ),
        (&mut arguments.root_cause_file, "invalid-root-cause-file"),
        (
            &mut arguments.sensitive_corpus_file,
            "invalid-sensitive-corpus-file",
        ),
    ] {
        if !absolutize_optional(path) {
            return Err(reason);
        }
    }
    Ok(())
}

fn snapshot_source_root(arguments: &FileReportArguments) -> Result<PathBuf, &'static str> {
    if arguments.dry_run {
        Ok(arguments
            .body_file
            .parent()
            .map(Path::to_path_buf)
            .unwrap_or_default())
    } else {
        absolute_path(&arguments.trusted_root).ok_or("invalid-trusted-root")
    }
}

fn private_stage() -> Result<tempfile::TempDir, &'static str> {
    let stage_parent = env::var_os("TMPDIR")
        .filter(|value| !value.is_empty())
        .map_or_else(|| PathBuf::from("/tmp"), PathBuf::from);
    let stage_parent = absolute_path(&stage_parent).ok_or("tempdir-failed")?;
    let stage = tempfile::Builder::new()
        .prefix("larch-file-failure-report.")
        .tempdir_in(stage_parent)
        .map_err(|_| "tempdir-failed")?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt as _;
        fs::set_permissions(stage.path(), fs::Permissions::from_mode(0o700))
            .map_err(|_| "tempdir-private-failed")?;
    }
    Ok(stage)
}

fn read_file_is_valid(path: &Path) -> bool {
    if path.as_os_str().is_empty() {
        return false;
    }
    fs::symlink_metadata(path).is_ok_and(|metadata| {
        metadata.is_file() && !metadata.file_type().is_symlink() && File::open(path).is_ok()
    })
}

fn absolute_path(path: &Path) -> Option<PathBuf> {
    if path.as_os_str().is_empty() {
        return None;
    }
    let name = path.file_name()?;
    let parent = path
        .parent()
        .filter(|parent| !parent.as_os_str().is_empty())
        .unwrap_or_else(|| Path::new("."));
    parent.canonicalize().ok().map(|parent| parent.join(name))
}

fn absolutize_optional(path: &mut Option<PathBuf>) -> bool {
    let Some(original) = path.as_ref() else {
        return true;
    };
    let Some(absolute) = absolute_path(original) else {
        return false;
    };
    *path = Some(absolute);
    true
}

fn lookup_failure(dedup_only: bool) -> FileReportOutcome {
    if dedup_only {
        FileReportOutcome::fail_open("lookup-failed")
    } else {
        FileReportOutcome::fallback("lookup-failed")
    }
}

fn print_service_failure(detail: &str) {
    let detail = redact(detail).text().trim().replace(['\r', '\n'], " ");
    if !detail.is_empty() {
        eprintln!("stall-recovery file-report: {detail}");
    }
}

fn parse_arguments(arguments: &[String]) -> Result<Option<FileReportArguments>, String> {
    let mut parsed = FileReportArguments::default();
    let mut index = 0;
    while index < arguments.len() {
        let option = arguments[index].as_str();
        match option {
            "-h" | "--help" => return Ok(None),
            "--dedup-only" => {
                parsed.dedup_only = true;
                index += 1;
            }
            "--create-on-lookup-failure" => {
                parsed.create_on_lookup_failure = true;
                index += 1;
            }
            "--dry-run" => {
                parsed.dry_run = true;
                index += 1;
            }
            "--repo"
            | "--body-file"
            | "--title"
            | "--attempts-file"
            | "--escalation-ledger-file"
            | "--root-cause-file"
            | "--sensitive-corpus-file"
            | "--publication-tier"
            | "--mutation-context"
            | "--run-id"
            | "--trusted-root" => {
                let Some(value) = arguments.get(index + 1) else {
                    return Err(format!("{option} requires a value"));
                };
                match option {
                    "--repo" => value.clone_into(&mut parsed.repo),
                    "--body-file" => parsed.body_file = PathBuf::from(value),
                    "--title" => value.clone_into(&mut parsed.title),
                    "--attempts-file" => parsed.attempts_file = Some(PathBuf::from(value)),
                    "--escalation-ledger-file" => {
                        parsed.escalation_file = Some(PathBuf::from(value));
                    }
                    "--root-cause-file" => {
                        parsed.root_cause_file = Some(PathBuf::from(value));
                    }
                    "--sensitive-corpus-file" => {
                        parsed.sensitive_corpus_file = Some(PathBuf::from(value));
                    }
                    "--publication-tier" => value.clone_into(&mut parsed.publication_tier),
                    "--mutation-context" => parsed.mutation_context = PathBuf::from(value),
                    "--run-id" => value.clone_into(&mut parsed.run_id),
                    "--trusted-root" => parsed.trusted_root = PathBuf::from(value),
                    _ => unreachable!("value-taking option is closed"),
                }
                index += 2;
            }
            _ => return Err(format!("unknown option: {option}")),
        }
    }
    Ok(Some(parsed))
}

#[cfg(test)]
mod tests {
    use super::{
        BUG_TITLE_PREFIX, FileReportArguments, FileReportOutcome, Preparation, PublicationTier,
        execute, execute_prepared, prepare,
    };
    use crate::github_service::with_test_github_service;
    use larch_adapters::github::OctocrabGitHubService;
    use larch_test_support::{IssueServiceExchange, IssueServiceRequest, IssueServiceStub};
    use serde_json::{Value, json};
    use std::{fs, io::Write as _, path::PathBuf, sync::Arc};

    const MARKER: &str = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";

    struct Fixture {
        _root: tempfile::TempDir,
        root: PathBuf,
        body: PathBuf,
        attempts: PathBuf,
        escalation: PathBuf,
        root_cause: PathBuf,
        corpus: PathBuf,
        context: PathBuf,
    }

    impl Fixture {
        fn new() -> Self {
            let temporary = tempfile::Builder::new()
                .prefix("claude-implement-file-report-")
                .tempdir_in("/tmp")
                .expect("session root");
            let root = temporary.path().canonicalize().expect("canonical root");
            let body = root.join("body.md");
            let attempts = root.join("attempts.md");
            let escalation = root.join("escalation.md");
            let root_cause = root.join("root.md");
            let corpus = root.join("stall-recovery-sensitive-corpus.env");
            let context = root.join("session-env.sh");
            fs::write(
                &body,
                format!(
                    "### [BUG] /implement terminal: fixture\n\n<!-- larch-stall:signature={MARKER} -->\n\nFull report body sentinel.\n"
                ),
            )
            .expect("body fixture");
            fs::write(
                &attempts,
                "| Attempt | Class |\n|---|---|\n| `1` | `transient-infra` |\n",
            )
            .expect("attempts fixture");
            fs::write(
                &escalation,
                "- site=`ship-pr` trigger=`main-agent-required`\n",
            )
            .expect("escalation fixture");
            fs::write(
                &root_cause,
                "verdict=larch-defect\nconfidence=high\nsummary=bounded finding\n\nBounded root-cause slice.\n",
            )
            .expect("root-cause fixture");
            fs::write(&corpus, "client-secret-token\n").expect("corpus fixture");
            fs::write(
                &context,
                "LARCH_LIVE_MUTATION_OK=true\nLARCH_RUN_ID=run-1\n",
            )
            .expect("context fixture");
            Self {
                _root: temporary,
                root,
                body,
                attempts,
                escalation,
                root_cause,
                corpus,
                context,
            }
        }

        fn arguments(&self, tier: &str) -> FileReportArguments {
            FileReportArguments {
                repo: "owner/repo".to_owned(),
                body_file: self.body.clone(),
                title: "Report title".to_owned(),
                publication_tier: tier.to_owned(),
                mutation_context: self.context.clone(),
                run_id: "run-1".to_owned(),
                trusted_root: self.root.clone(),
                ..FileReportArguments::default()
            }
        }

        fn arguments_with_slices(&self, tier: &str) -> FileReportArguments {
            FileReportArguments {
                attempts_file: Some(self.attempts.clone()),
                escalation_file: Some(self.escalation.clone()),
                root_cause_file: Some(self.root_cause.clone()),
                ..self.arguments(tier)
            }
        }
    }

    fn assert_outcome(outcome: &FileReportOutcome, status: &str, reason: &str) {
        assert_eq!(outcome.status, status);
        assert_eq!(outcome.fallback_reason, reason);
    }

    fn response(status: u16, body: impl Into<Vec<u8>>) -> IssueServiceExchange {
        IssueServiceExchange::any_json(status, body).expect("JSON response")
    }

    fn with_github(
        exchanges: impl IntoIterator<Item = IssueServiceExchange>,
        action: impl FnOnce() -> FileReportOutcome,
    ) -> (FileReportOutcome, Vec<IssueServiceRequest>) {
        let server = IssueServiceStub::start(exchanges).expect("loopback service");
        let base = server.base_url().to_owned();
        let factory: Arc<dyn Fn() -> OctocrabGitHubService + Send + Sync> =
            Arc::new(move || OctocrabGitHubService::with_test_base(&base));
        let outcome = with_test_github_service(factory, action);
        let requests = server.finish().expect("completed requests");
        (outcome, requests)
    }

    fn issue_json(number: u64, title: &str, body: &str, pull_request: bool) -> String {
        let mut issue: Value = serde_json::from_str(include_str!(
            "../../larch-adapters/fixtures/github_issue.json"
        ))
        .expect("issue fixture");
        issue["id"] = json!(number + 100);
        issue["number"] = json!(number);
        issue["title"] = json!(title);
        issue["body"] = json!(body);
        issue["html_url"] = json!(format!("https://github.com/owner/repo/issues/{number}"));
        issue["url"] = json!(api_url(&format!("/repos/owner/repo/issues/{number}")));
        issue["repository_url"] = json!(api_url("/repos/owner/repo"));
        issue["labels"] = json!([]);
        issue["assignees"] = json!([]);
        issue["assignee"] = Value::Null;
        issue["comments"] = json!(0);
        if pull_request {
            issue["pull_request"] = json!({
                "url": api_url(&format!("/repos/owner/repo/pulls/{number}")),
                "html_url": format!("https://github.com/owner/repo/pull/{number}"),
                "diff_url": format!("https://github.com/owner/repo/pull/{number}.diff"),
                "patch_url": format!("https://github.com/owner/repo/pull/{number}.patch")
            });
        }
        issue.to_string()
    }

    fn comment_json(id: u64, body: &str, include_url: bool) -> String {
        let issue: Value =
            serde_json::from_str(&issue_json(7, "T", "B", false)).expect("issue fixture");
        json!({
            "id": id,
            "node_id": format!("C_{id}"),
            "url": api_url(&format!("/repos/owner/repo/issues/comments/{id}")),
            "html_url": if include_url {
                format!("https://github.com/owner/repo/issues/7#issuecomment-{id}")
            } else {
                String::new()
            },
            "body": body,
            "user": issue["user"].clone(),
            "created_at": "2026-08-25T00:00:00Z",
            "updated_at": "2026-08-25T00:00:00Z"
        })
        .to_string()
    }

    fn api_url(path: &str) -> String {
        format!("https://api.{}{path}", "github.com")
    }

    fn creation_exchanges(title: &str, body: &str) -> Vec<IssueServiceExchange> {
        let issue = issue_json(42, title, body, false);
        vec![
            response(200, "[]"),
            response(201, issue.clone()),
            response(200, issue),
        ]
    }

    fn duplicate_exchanges(comment: &str) -> Vec<IssueServiceExchange> {
        let issue = issue_json(
            7,
            "existing",
            &format!("contains <!-- larch-stall:signature={MARKER} --> marker"),
            false,
        );
        let comment = comment_json(99, comment, true);
        vec![
            response(200, format!("[{issue}]")),
            response(201, comment.clone()),
            response(200, format!("[{comment}]")),
        ]
    }

    #[test]
    fn dry_run_preserves_the_exact_stdout_grammar_without_authorization() {
        let fixture = Fixture::new();
        let mut arguments = fixture.arguments("tier-a");
        arguments.dry_run = true;
        arguments.mutation_context = PathBuf::new();
        arguments.run_id.clear();
        arguments.trusted_root = PathBuf::new();
        let outcome = execute(arguments);
        assert_eq!(outcome.render(), "FILE_FAILURE_REPORT_STATUS=dry-run\n");
    }

    #[test]
    fn result_envelopes_preserve_field_order_and_optional_rows() {
        assert_eq!(
            FileReportOutcome::success("filed", "https://github.com/o/r/issues/1".to_owned())
                .render(),
            concat!(
                "FILE_FAILURE_REPORT_STATUS=filed\n",
                "FILE_FAILURE_REPORT_URL=https://github.com/o/r/issues/1\n",
            )
        );
        assert_eq!(
            FileReportOutcome::fallback("invalid-body-file").render(),
            concat!(
                "FILE_FAILURE_REPORT_STATUS=fallback-print-required\n",
                "FILE_FAILURE_REPORT_FALLBACK_REASON=invalid-body-file\n",
            )
        );
        assert_eq!(
            FileReportOutcome::fail_open("lookup-failed").render(),
            concat!(
                "FILE_FAILURE_REPORT_STATUS=lookup-failed-open\n",
                "FILE_FAILURE_REPORT_FALLBACK_REASON=lookup-failed\n",
            )
        );
    }

    #[test]
    fn comment_assembly_preserves_the_legacy_bytes() {
        assert_eq!(
            super::assemble_comment(Some("attempt\n"), Some("escalation"), None),
            concat!(
                "+1 occurrence\n\n",
                "## Attempts\n\n",
                "attempt\n\n\n",
                "## Escalation evidence\n\n",
                "escalation\n\n",
                "## Root-cause finding\n\n",
                "_No Root-cause finding supplied for this occurrence._\n\n",
            )
        );
    }

    #[test]
    fn report_titles_preserve_tier_specific_prefix_handling() {
        assert_eq!(
            super::report_title(
                "### [BUG] /implement terminal: current\n",
                PublicationTier::A
            ),
            Some("/implement terminal: current".to_owned())
        );
        assert_eq!(
            super::report_title(
                "### [Bug] /implement terminal: legacy\n",
                PublicationTier::A
            ),
            Some("/implement terminal: legacy".to_owned())
        );
        assert_eq!(
            super::report_title(
                "### [BUG] /implement terminal: public\n",
                PublicationTier::B
            ),
            Some(format!("{BUG_TITLE_PREFIX} /implement terminal: public"))
        );
    }

    #[test]
    fn input_refusals_keep_the_legacy_fallback_tokens() {
        let fixture = Fixture::new();
        let mut invalid_repo = fixture.arguments("tier-a");
        invalid_repo.repo = "owner".to_owned();
        assert_outcome(
            &execute(invalid_repo),
            "fallback-print-required",
            "invalid-repo",
        );

        let mut invalid_tier = fixture.arguments("unknown");
        invalid_tier.dry_run = true;
        assert_outcome(
            &execute(invalid_tier),
            "fallback-print-required",
            "invalid-publication-tier",
        );

        let mut invalid_lookup_create = fixture.arguments("tier-b");
        invalid_lookup_create.create_on_lookup_failure = true;
        assert_outcome(
            &execute(invalid_lookup_create),
            "fallback-print-required",
            "invalid-lookup-failure-create",
        );

        let mut missing_attempts = fixture.arguments("tier-a");
        missing_attempts.attempts_file = Some(fixture.root.join("missing.md"));
        assert_outcome(
            &execute(missing_attempts),
            "fallback-print-required",
            "invalid-attempts-file",
        );

        let mut missing_design_corpus = fixture.arguments("tier-b");
        missing_design_corpus.sensitive_corpus_file =
            Some(fixture.root.join("design-failure-sensitive-corpus.env"));
        assert_outcome(
            &execute(missing_design_corpus),
            "fallback-print-required",
            "invalid-sensitive-corpus-file",
        );

        let mut missing_title = fixture.arguments("tier-a");
        missing_title.title.clear();
        missing_title.dry_run = true;
        assert_outcome(
            &execute(missing_title),
            "fallback-print-required",
            "missing-title",
        );
    }

    #[cfg(unix)]
    #[test]
    fn a_symlinked_body_is_refused_before_snapshotting() {
        use std::os::unix::fs::symlink;

        let fixture = Fixture::new();
        let link = fixture.root.join("body-link.md");
        symlink(&fixture.body, &link).expect("body symlink");
        let mut arguments = fixture.arguments("tier-a");
        arguments.body_file = link;
        assert_outcome(
            &execute(arguments),
            "fallback-print-required",
            "invalid-body-file",
        );
    }

    #[test]
    fn marker_and_heading_refusals_preserve_dedup_fail_open_behavior() {
        let fixture = Fixture::new();
        fs::write(&fixture.body, "no marker\n").expect("markerless body");
        let mut dedup = fixture.arguments("tier-a");
        dedup.dedup_only = true;
        assert_outcome(&execute(dedup), "lookup-failed-open", "missing-marker");
        assert_outcome(
            &execute(fixture.arguments("tier-a")),
            "fallback-print-required",
            "missing-marker",
        );

        fs::write(
            &fixture.body,
            format!("not a heading\n<!-- larch-stall:signature={MARKER} -->\n"),
        )
        .expect("headingless body");
        assert_outcome(
            &execute(fixture.arguments("tier-a")),
            "fallback-print-required",
            "invalid-body-title",
        );
    }

    #[test]
    fn authorization_refusals_run_before_any_github_client() {
        let fixture = Fixture::new();
        let mut missing_context = fixture.arguments("tier-a");
        missing_context.mutation_context = PathBuf::new();
        assert_outcome(
            &execute(missing_context),
            "mutation-refused",
            "unauthorized-mutation:no-context-file",
        );

        let mut missing_run_id = fixture.arguments("tier-a");
        missing_run_id.run_id.clear();
        assert_outcome(
            &execute(missing_run_id),
            "mutation-refused",
            "unauthorized-mutation:missing-run-id",
        );

        let mut missing_root = fixture.arguments("tier-a");
        missing_root.trusted_root = PathBuf::new();
        assert_outcome(
            &execute(missing_root),
            "mutation-refused",
            "unauthorized-mutation:missing-trusted-root",
        );

        let wrong = fixture.root.join("wrong-context.sh");
        fs::write(&wrong, "LARCH_LIVE_MUTATION_OK=true\nLARCH_RUN_ID=wrong\n")
            .expect("wrong context");
        let mut invalid = fixture.arguments("tier-a");
        invalid.mutation_context = wrong;
        assert_outcome(
            &execute(invalid),
            "mutation-refused",
            "unauthorized-mutation:invalid-context-file",
        );
    }

    #[test]
    fn no_match_creates_from_the_approved_snapshot_and_heading_title() {
        let fixture = Fixture::new();
        let body = fs::read_to_string(&fixture.body).expect("body fixture");
        let (outcome, requests) = with_github(
            creation_exchanges("/implement terminal: fixture", &body),
            || execute(fixture.arguments("tier-a")),
        );
        assert_eq!(outcome.status, "filed");
        assert_eq!(outcome.url, "https://github.com/owner/repo/issues/42");
        let create: Value =
            serde_json::from_slice(&requests[1].body.bytes).expect("create request JSON");
        assert_eq!(create["title"], "/implement terminal: fixture");
        assert_eq!(create["body"], body);
        assert!(requests[0].path.contains("state=open"));
        assert!(requests[0].path.contains("sort=created"));
        assert!(requests[0].path.contains("direction=desc"));
        assert!(requests[0].path.contains("per_page=100"));
    }

    #[test]
    fn duplicate_posts_only_the_structured_occurrence_comment() {
        let fixture = Fixture::new();
        let expected = super::assemble_comment(
            Some(&fs::read_to_string(&fixture.attempts).expect("attempts")),
            Some(&fs::read_to_string(&fixture.escalation).expect("escalation")),
            Some(&fs::read_to_string(&fixture.root_cause).expect("root cause")),
        );
        let (outcome, requests) = with_github(duplicate_exchanges(&expected), || {
            execute(fixture.arguments_with_slices("tier-a"))
        });
        assert_eq!(outcome.status, "dedup-comment");
        assert_eq!(
            outcome.url,
            "https://github.com/owner/repo/issues/7#issuecomment-99"
        );
        let comment: Value =
            serde_json::from_slice(&requests[1].body.bytes).expect("comment request JSON");
        assert_eq!(comment["body"], expected);
        assert!(expected.contains("+1 occurrence"));
        assert!(expected.contains("Bounded root-cause slice."));
        assert!(!expected.contains("Full report body sentinel."));
    }

    #[test]
    fn dedup_only_no_match_and_lookup_failure_both_exit_zero_outcomes() {
        let fixture = Fixture::new();
        let mut arguments = fixture.arguments("tier-a");
        arguments.dedup_only = true;
        let (no_match, _) = with_github([response(200, "[]")], || execute(arguments.clone()));
        assert_outcome(&no_match, "no-match", "");

        let (failed, _) = with_github([response(403, r#"{"message":"lookup failed"}"#)], || {
            execute(arguments)
        });
        assert_outcome(&failed, "lookup-failed-open", "lookup-failed");
    }

    #[test]
    fn tier_a_lookup_failure_can_fail_open_into_creation() {
        let fixture = Fixture::new();
        let body = fs::read_to_string(&fixture.body).expect("body fixture");
        let issue = issue_json(42, "/implement terminal: fixture", &body, false);
        let exchanges = [
            response(403, r#"{"message":"lookup failed"}"#),
            response(201, issue.clone()),
            response(200, issue),
        ];
        let mut arguments = fixture.arguments("tier-a");
        arguments.create_on_lookup_failure = true;
        let (outcome, requests) = with_github(exchanges, || execute(arguments));
        assert_eq!(outcome.status, "filed");
        assert_eq!(requests[1].method, "POST");
    }

    #[test]
    fn comment_and_create_failures_keep_distinct_fallback_reasons() {
        let fixture = Fixture::new();
        let existing = issue_json(
            7,
            "existing",
            &format!("<!-- larch-stall:signature={MARKER} -->"),
            false,
        );
        let (comment_failed, _) = with_github(
            [
                response(200, format!("[{existing}]")),
                response(422, r#"{"message":"comment failed"}"#),
            ],
            || execute(fixture.arguments("tier-a")),
        );
        assert_outcome(&comment_failed, "fallback-print-required", "comment-failed");

        let fixture = Fixture::new();
        let (create_failed, _) = with_github(
            [
                response(200, "[]"),
                response(422, r#"{"message":"create failed"}"#),
            ],
            || execute(fixture.arguments("tier-a")),
        );
        assert_outcome(&create_failed, "fallback-print-required", "create-failed");
    }

    #[test]
    fn a_comment_success_without_a_valid_url_reports_url_missing() {
        let fixture = Fixture::new();
        let existing = issue_json(
            7,
            "existing",
            &format!("<!-- larch-stall:signature={MARKER} -->"),
            false,
        );
        let comment = super::assemble_comment(None, None, None);
        let (outcome, _) = with_github(
            [
                response(200, format!("[{existing}]")),
                response(201, comment_json(99, &comment, false)),
            ],
            || execute(fixture.arguments("tier-a")),
        );
        assert_outcome(&outcome, "fallback-print-required", "comment-url-missing");
        assert!(!outcome.render().contains("FILE_FAILURE_REPORT_URL="));
    }

    #[test]
    fn a_create_success_without_a_decodable_url_reports_url_missing() {
        let fixture = Fixture::new();
        let (outcome, requests) = with_github([response(200, "[]"), response(201, "{}")], || {
            execute(fixture.arguments("tier-a"))
        });
        assert_outcome(&outcome, "fallback-print-required", "create-url-missing");
        assert!(!outcome.render().contains("FILE_FAILURE_REPORT_URL="));
        assert_eq!(requests.len(), 2);
    }

    #[test]
    fn pull_requests_are_ignored_and_the_raw_page_is_bounded_at_one_hundred() {
        let fixture = Fixture::new();
        let body = fs::read_to_string(&fixture.body).expect("body fixture");
        let pulls = (1..=100)
            .map(|number| issue_json(number, "pull", "different", true))
            .collect::<Vec<_>>()
            .join(",");
        let issue = issue_json(42, "/implement terminal: fixture", &body, false);
        let (outcome, requests) = with_github(
            [
                response(200, format!("[{pulls}]")),
                response(201, issue.clone()),
                response(200, issue),
            ],
            || execute(fixture.arguments("tier-a")),
        );
        assert_eq!(outcome.status, "filed");
        assert_eq!(requests.len(), 3);
        assert!(requests[0].path.contains("per_page=100"));
        assert!(!requests[0].path.contains("page=2"));
    }

    #[test]
    fn tier_b_accepts_bounded_slices_and_rejects_raw_or_sensitive_comments() {
        let fixture = Fixture::new();
        let expected = super::assemble_comment(
            Some(&fs::read_to_string(&fixture.attempts).expect("attempts")),
            Some(&fs::read_to_string(&fixture.escalation).expect("escalation")),
            Some(&fs::read_to_string(&fixture.root_cause).expect("root cause")),
        );
        let (accepted, _) = with_github(duplicate_exchanges(&expected), || {
            execute(fixture.arguments_with_slices("tier-b"))
        });
        assert_eq!(accepted.status, "dedup-comment");

        for heading in [
            "### [BUG] /implement terminal: raw",
            "### [Bug] /implement terminal: raw",
            "### [BUG] /design terminal: raw",
            "### [Bug] /design terminal: raw",
        ] {
            fs::write(
                &fixture.root_cause,
                format!("{heading}\n\n<!-- larch-stall:signature={MARKER} -->\n"),
            )
            .expect("raw root-cause fixture");
            let existing = issue_json(
                7,
                "existing",
                &format!("<!-- larch-stall:signature={MARKER} -->"),
                false,
            );
            let (unsafe_comment, _) = with_github([response(200, format!("[{existing}]"))], || {
                execute(FileReportArguments {
                    root_cause_file: Some(fixture.root_cause.clone()),
                    ..fixture.arguments("tier-b")
                })
            });
            assert_outcome(
                &unsafe_comment,
                "fallback-print-required",
                "unsafe-tier-b-comment",
            );
        }

        fs::write(&fixture.root_cause, "client-secret-token\n")
            .expect("sensitive root-cause fixture");
        let existing = issue_json(
            7,
            "existing",
            &format!("<!-- larch-stall:signature={MARKER} -->"),
            false,
        );
        let (sensitive, _) = with_github([response(200, format!("[{existing}]"))], || {
            execute(FileReportArguments {
                root_cause_file: Some(fixture.root_cause.clone()),
                ..fixture.arguments("tier-b")
            })
        });
        assert_outcome(
            &sensitive,
            "fallback-print-required",
            "unsafe-tier-b-comment",
        );
    }

    #[test]
    fn tier_b_missing_corpus_and_sensitive_create_body_fail_before_mutation() {
        let fixture = Fixture::new();
        fs::remove_file(&fixture.corpus).expect("remove corpus");
        let existing = issue_json(
            7,
            "existing",
            &format!("<!-- larch-stall:signature={MARKER} -->"),
            false,
        );
        let (missing, requests) = with_github([response(200, format!("[{existing}]"))], || {
            execute(FileReportArguments {
                root_cause_file: Some(fixture.root_cause.clone()),
                ..fixture.arguments("tier-b")
            })
        });
        assert_outcome(&missing, "fallback-print-required", "unsafe-tier-b-comment");
        assert_eq!(requests.len(), 1);

        fs::write(&fixture.corpus, "client-secret-token\n").expect("restore corpus");
        fs::OpenOptions::new()
            .append(true)
            .open(&fixture.body)
            .expect("open body")
            .write_all(b"client-secret-token\n")
            .expect("append sensitive body");
        let (unsafe_body, requests) = with_github([response(200, "[]")], || {
            execute(fixture.arguments("tier-b"))
        });
        assert_outcome(
            &unsafe_body,
            "fallback-print-required",
            "unsafe-tier-b-body",
        );
        assert_eq!(requests.len(), 1);
    }

    #[test]
    fn design_prefixed_tier_b_uses_the_explicit_design_corpus() {
        let fixture = Fixture::new();
        let design_corpus = fixture.root.join("design-failure-sensitive-corpus.env");
        fs::write(&design_corpus, "design-only-secret\n").expect("design corpus");
        let expected = super::assemble_comment(
            Some(&fs::read_to_string(&fixture.attempts).expect("attempts")),
            Some(&fs::read_to_string(&fixture.escalation).expect("escalation")),
            Some(&fs::read_to_string(&fixture.root_cause).expect("root cause")),
        );
        let (outcome, _) = with_github(duplicate_exchanges(&expected), || {
            execute(FileReportArguments {
                sensitive_corpus_file: Some(design_corpus),
                ..fixture.arguments_with_slices("tier-b")
            })
        });
        assert_eq!(outcome.status, "dedup-comment");
    }

    #[test]
    fn approved_body_bytes_and_title_survive_later_source_replacement() {
        for (tier, expected_title) in [
            (PublicationTier::A, "/implement terminal: fixture"),
            (PublicationTier::B, "[BUG] /implement terminal: fixture"),
        ] {
            let fixture = Fixture::new();
            let tier_text = if tier == PublicationTier::A {
                "tier-a"
            } else {
                "tier-b"
            };
            let Preparation::Ready(prepared) = prepare(fixture.arguments(tier_text)) else {
                panic!("live request must prepare");
            };
            let approved_body = prepared.body_snapshot.clone();
            fs::write(&fixture.body, "late-public-secret\n").expect("replace source");
            let (outcome, requests) =
                with_github(creation_exchanges(expected_title, &approved_body), || {
                    execute_prepared(&prepared)
                });
            assert_eq!(outcome.status, "filed");
            let create: Value =
                serde_json::from_slice(&requests[1].body.bytes).expect("create JSON");
            assert_eq!(create["title"], expected_title);
            assert_eq!(create["body"], approved_body);
            assert!(
                !create["body"]
                    .as_str()
                    .expect("body string")
                    .contains("late-public-secret")
            );
        }
    }
}
